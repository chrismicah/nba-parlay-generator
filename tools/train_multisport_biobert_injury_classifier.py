#!/usr/bin/env python3
"""
Multi-Sport BioBERT Injury Severity Classification Model

This script fine-tunes BioBERT on combined NBA + NFL injury data to classify 
injury severity with sport-aware features, timestamp weighting, author credibility,
and confidence thresholding for uncertain predictions.
"""

import os
import pandas as pd
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoTokenizer, AutoModelForSequenceClassification,
    TrainingArguments, Trainer, EarlyStoppingCallback
)
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import json
from datetime import datetime, timedelta
import logging
import argparse

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MultiSportInjuryDataset(Dataset):
    """Custom dataset for multi-sport injury severity classification with enhanced features"""
    
    def __init__(self, texts, labels, sports, credibility_scores, timestamp_weights, tokenizer, max_length=512):
        self.texts = texts
        self.labels = labels
        self.sports = sports
        self.credibility_scores = credibility_scores
        self.timestamp_weights = timestamp_weights
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = self.labels[idx]
        sport = self.sports[idx]
        credibility = self.credibility_scores[idx]
        timestamp_weight = self.timestamp_weights[idx]
        
        # Enhance text with sport context
        enhanced_text = f"[{sport.upper()}] {text}"
        
        # Tokenize the enhanced text
        encoding = self.tokenizer(
            enhanced_text,
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.long),
            'sport': sport,
            'credibility': torch.tensor(credibility, dtype=torch.float),
            'timestamp_weight': torch.tensor(timestamp_weight, dtype=torch.float)
        }

class MultiSportBioBERTInjuryClassifier:
    """Multi-sport BioBERT-based injury severity classifier with enhanced features"""
    
    def __init__(self, model_name="dmis-lab/biobert-base-cased-v1.1", confidence_threshold=0.8):
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.tokenizer = None
        self.model = None
        self.label_encoder = {}
        self.label_decoder = {}
        self.sport_encoder = {"nba": 0, "nfl": 1}
        self.sport_decoder = {0: "nba", 1: "nfl"}
        
    def calculate_timestamp_weight(self, timestamp_str, current_time=None):
        """Calculate timestamp weight based on recency"""
        if current_time is None:
            current_time = datetime.now()
        
        try:
            # Parse timestamp
            tweet_time = datetime.strptime(timestamp_str.replace('+0000 ', ''), '%a %b %d %H:%M:%S %Y')
            days_diff = (current_time - tweet_time).days
            
            # More recent tweets get higher weights (exponential decay)
            weight = np.exp(-days_diff / 30.0)  # 30-day half-life
            return min(max(weight, 0.1), 1.0)  # Clamp between 0.1 and 1.0
        except:
            return 0.5  # Default weight for unparseable timestamps
    
    def get_author_credibility(self, author):
        """Get credibility score for author"""
        credibility_scores = {
            # NFL accounts
            'AdamSchefter': 1.0,
            'RapSheet': 1.0,
            'MikeGarafolo': 0.9,
            'NFLInjuryNws': 0.9,
            'ESPNNFL': 0.8,
            'NFL': 0.8,
            'FieldYates': 0.8,
            'nflnetwork': 0.8,
            'ProFootballTalk': 0.7,
            'CBSSportsNFL': 0.7,
            # NBA accounts
            'ShamsCharania': 1.0,
            'wojespn': 1.0,
            'ChrisBHaynes': 0.8,
            'Rotoworld_BK': 0.8,
            'FantasyLabsNBA': 0.8,
            'InStreetClothes': 0.7,
            'NBAInjuryNws': 0.9,
            'espn': 0.8
        }
        return credibility_scores.get(author, 0.5)  # Default credibility
    
    def prepare_combined_data(self, nfl_csv_path, nba_csv_path=None):
        """Load and prepare combined NFL + NBA injury severity dataset"""
        logger.info("Loading combined NFL + NBA injury data...")
        
        # Load NFL data
        nfl_df = pd.read_csv(nfl_csv_path)
        nfl_df['sport'] = 'nfl'
        
        # Load NBA data (if available)
        if nba_csv_path and os.path.exists(nba_csv_path):
            nba_df = pd.read_csv(nba_csv_path)
            nba_df['sport'] = 'nba'
            
            # Combine datasets
            combined_df = pd.concat([nfl_df, nba_df], ignore_index=True)
            logger.info(f"Combined dataset: {len(nfl_df)} NFL + {len(nba_df)} NBA = {len(combined_df)} total")
        else:
            combined_df = nfl_df
            logger.info(f"Using NFL data only: {len(combined_df)} samples")
        
        # Filter out rows with missing text or labels
        combined_df = combined_df.dropna(subset=['text', 'injury_severity_label'])
        
        # Add enhanced features
        current_time = datetime.now()
        combined_df['author_credibility'] = combined_df['author'].apply(self.get_author_credibility)
        combined_df['timestamp_weight'] = combined_df['timestamp'].apply(
            lambda x: self.calculate_timestamp_weight(x, current_time)
        )
        
        # Create label mappings (use existing BioBERT labels)
        self.label_encoder = {
            "day_to_day": 0,
            "minor": 1, 
            "out_for_season": 2,
            "unconfirmed": 3
        }
        self.label_decoder = {idx: label for label, idx in self.label_encoder.items()}
        
        logger.info(f"Label mappings: {self.label_encoder}")
        
        # Encode labels
        combined_df['encoded_labels'] = combined_df['injury_severity_label'].map(self.label_encoder)
        
        # Check for unmapped labels
        unmapped = combined_df[combined_df['encoded_labels'].isna()]
        if len(unmapped) > 0:
            logger.warning(f"Found {len(unmapped)} unmapped labels: {unmapped['injury_severity_label'].unique()}")
            combined_df = combined_df.dropna(subset=['encoded_labels'])
        
        # Display distribution by sport and label
        print("\n📊 Dataset Distribution:")
        print("=" * 50)
        print(f"Total samples: {len(combined_df)}")
        print(f"\nBy sport:")
        print(combined_df['sport'].value_counts())
        print(f"\nBy injury severity:")
        print(combined_df['injury_severity_label'].value_counts())
        print(f"\nBy sport and severity:")
        print(combined_df.groupby(['sport', 'injury_severity_label']).size().unstack(fill_value=0))
        
        # Split the data
        X_train, X_test, y_train, y_test = train_test_split(
            combined_df[['text', 'sport', 'author_credibility', 'timestamp_weight']],
            combined_df['encoded_labels'],
            test_size=0.2,
            random_state=42,
            stratify=combined_df[['sport', 'encoded_labels']].apply(lambda x: f"{x.sport}_{x.encoded_labels}", axis=1)
        )
        
        # Further split training data for validation  
        X_train, X_val, y_train, y_val = train_test_split(
            X_train, y_train,
            test_size=0.2,
            random_state=42,
            stratify=X_train['sport'] + '_' + y_train.astype(str)
        )
        
        logger.info(f"Training samples: {len(X_train)}")
        logger.info(f"Validation samples: {len(X_val)}")
        logger.info(f"Test samples: {len(X_test)}")
        
        return (X_train, X_val, X_test), (y_train, y_val, y_test)
    
    def initialize_model(self, num_labels):
        """Initialize BioBERT model and tokenizer"""
        logger.info(f"Initializing BioBERT model: {self.model_name}")
        
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            self.model_name,
            num_labels=num_labels,
            problem_type="single_label_classification"
        )
        
        logger.info("Model and tokenizer initialized successfully")
    
    def create_datasets(self, data_splits, label_splits):
        """Create PyTorch datasets with enhanced features"""
        X_train, X_val, X_test = data_splits
        y_train, y_val, y_test = label_splits
        
        train_dataset = MultiSportInjuryDataset(
            X_train['text'].tolist(),
            y_train.tolist(),
            X_train['sport'].tolist(),
            X_train['author_credibility'].tolist(),
            X_train['timestamp_weight'].tolist(),
            self.tokenizer
        )
        
        val_dataset = MultiSportInjuryDataset(
            X_val['text'].tolist(),
            y_val.tolist(),
            X_val['sport'].tolist(),
            X_val['author_credibility'].tolist(),
            X_val['timestamp_weight'].tolist(),
            self.tokenizer
        )
        
        test_dataset = MultiSportInjuryDataset(
            X_test['text'].tolist(),
            y_test.tolist(),
            X_test['sport'].tolist(),
            X_test['author_credibility'].tolist(),
            X_test['timestamp_weight'].tolist(),
            self.tokenizer
        )
        
        return train_dataset, val_dataset, test_dataset
    
    def compute_metrics(self, eval_pred):
        """Compute metrics for evaluation"""
        predictions, labels = eval_pred
        predictions = np.argmax(predictions, axis=1)
        return {'accuracy': accuracy_score(labels, predictions)}
    
    def train(self, train_dataset, val_dataset, output_dir="models/multisport_biobert_injury_classifier"):
        """Train the Multi-Sport BioBERT model"""
        logger.info("Starting multi-sport model training...")
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Training arguments optimized for multi-sport learning
        training_args = TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=5,
            per_device_train_batch_size=4,  # Smaller batch for enhanced features
            per_device_eval_batch_size=4,
            warmup_steps=100,
            weight_decay=0.01,
            learning_rate=2e-5,  # Lower learning rate for BioBERT
            logging_dir=f'{output_dir}/logs',
            logging_steps=10,
            eval_strategy="steps",
            eval_steps=50,
            save_strategy="steps",
            save_steps=50,
            load_best_model_at_end=True,
            metric_for_best_model="accuracy",
            greater_is_better=True,
            save_total_limit=2,
            report_to=None,
            dataloader_drop_last=False,
            group_by_length=True  # Group similar length sequences
        )
        
        # Initialize trainer
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
            compute_metrics=self.compute_metrics,
            callbacks=[EarlyStoppingCallback(early_stopping_patience=3)]
        )
        
        # Train the model
        trainer.train()
        
        # Save the model and tokenizer
        trainer.save_model(output_dir)
        self.tokenizer.save_pretrained(output_dir)
        
        # Save enhanced label mappings
        with open(f"{output_dir}/label_mappings.json", "w") as f:
            json.dump({
                "label_encoder": self.label_encoder,
                "label_decoder": self.label_decoder,
                "sport_encoder": self.sport_encoder,
                "sport_decoder": self.sport_decoder,
                "confidence_threshold": self.confidence_threshold,
                "features": ["sport_context", "author_credibility", "timestamp_weight"]
            }, f, indent=2)
        
        logger.info(f"Multi-sport model saved to {output_dir}")
        return trainer
    
    def predict_with_confidence(self, texts, sports=None, authors=None, timestamps=None, 
                              model_path="models/multisport_biobert_injury_classifier"):
        """Make predictions with confidence scores and enhanced features"""
        # Load model if not already loaded
        if self.model is None:
            self.load_model(model_path)
        
        # Set defaults for missing features
        if sports is None:
            sports = ["nfl"] * len(texts)
        if authors is None:
            authors = ["unknown"] * len(texts)
        if timestamps is None:
            timestamps = [datetime.now().strftime('%a %b %d %H:%M:%S +0000 %Y')] * len(texts)
        
        # Calculate enhanced features
        current_time = datetime.now()
        credibility_scores = [self.get_author_credibility(author) for author in authors]
        timestamp_weights = [self.calculate_timestamp_weight(ts, current_time) for ts in timestamps]
        
        # Enhance texts with sport context
        enhanced_texts = [f"[{sport.upper()}] {text}" for text, sport in zip(texts, sports)]
        
        # Move model to CPU to avoid MPS issues
        device = torch.device('cpu')
        self.model = self.model.to(device)
        
        # Tokenize inputs
        inputs = self.tokenizer(
            enhanced_texts,
            truncation=True,
            padding=True,
            max_length=512,
            return_tensors="pt"
        )
        
        # Move inputs to CPU
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        # Get predictions
        self.model.eval()
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            
            # Apply softmax to get probabilities
            probabilities = torch.softmax(logits, dim=-1)
            
            # Get predicted classes and confidence scores
            confidence_scores_tensor, predicted_classes = torch.max(probabilities, dim=-1)
            
        results = []
        for i, text in enumerate(texts):
            pred_class = predicted_classes[i].item()
            confidence = confidence_scores_tensor[i].item()
            predicted_label = self.label_decoder[pred_class]
            
            # Apply credibility and timestamp weighting to confidence
            adjusted_confidence = confidence * credibility_scores[i] * timestamp_weights[i]
            
            # Determine if prediction meets confidence threshold
            is_confident = adjusted_confidence >= self.confidence_threshold
            
            results.append({
                'text': text,
                'sport': sports[i],
                'author': authors[i],
                'predicted_label': predicted_label,
                'raw_confidence': confidence,
                'adjusted_confidence': adjusted_confidence,
                'author_credibility': credibility_scores[i],
                'timestamp_weight': timestamp_weights[i],
                'is_confident': is_confident,
                'needs_review': not is_confident,
                'all_probabilities': {
                    self.label_decoder[j]: probabilities[i][j].item() 
                    for j in range(len(self.label_decoder))
                }
            })
        
        return results
    
    def load_model(self, model_path):
        """Load a trained multi-sport model"""
        logger.info(f"Loading multi-sport model from {model_path}")
        
        # Load label mappings
        with open(f"{model_path}/label_mappings.json", "r") as f:
            mappings = json.load(f)
            self.label_encoder = mappings["label_encoder"]
            self.label_decoder = {int(k): v for k, v in mappings["label_decoder"].items()}
            self.sport_encoder = mappings.get("sport_encoder", {"nba": 0, "nfl": 1})
            self.sport_decoder = mappings.get("sport_decoder", {"0": "nba", "1": "nfl"})
            self.confidence_threshold = mappings.get("confidence_threshold", 0.8)
        
        # Load model and tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
        
        logger.info("Multi-sport model loaded successfully")
    
    def evaluate_by_sport(self, test_dataset, model_path="models/multisport_biobert_injury_classifier"):
        """Evaluate the model on test data with sport-specific metrics"""
        if self.model is None:
            self.load_model(model_path)
        
        # Move model to CPU to avoid MPS issues
        device = torch.device('cpu')
        self.model = self.model.to(device)
        
        # Create data loader
        test_loader = DataLoader(test_dataset, batch_size=4, shuffle=False)
        
        all_predictions = []
        all_labels = []
        all_confidences = []
        all_sports = []
        all_credibilities = []
        all_timestamp_weights = []
        
        self.model.eval()
        with torch.no_grad():
            for batch in test_loader:
                # Move batch to CPU
                batch_device = {k: v.to(device) if isinstance(v, torch.Tensor) else v for k, v in batch.items()}
                
                outputs = self.model(
                    input_ids=batch_device['input_ids'],
                    attention_mask=batch_device['attention_mask']
                )
                
                logits = outputs.logits
                probabilities = torch.softmax(logits, dim=-1)
                confidence_scores, predicted_classes = torch.max(probabilities, dim=-1)
                
                all_predictions.extend(predicted_classes.cpu().numpy())
                all_labels.extend(batch_device['labels'].cpu().numpy())
                all_confidences.extend(confidence_scores.cpu().numpy())
                all_sports.extend(batch['sport'])
                all_credibilities.extend(batch_device['credibility'].cpu().numpy())
                all_timestamp_weights.extend(batch_device['timestamp_weight'].cpu().numpy())
        
        # Calculate overall metrics
        overall_accuracy = accuracy_score(all_labels, all_predictions)
        
        # Calculate sport-specific metrics
        results = {'overall_accuracy': overall_accuracy}
        
        for sport in ['nfl', 'nba']:
            sport_mask = [s == sport for s in all_sports]
            if any(sport_mask):
                sport_predictions = [p for p, m in zip(all_predictions, sport_mask) if m]
                sport_labels = [l for l, m in zip(all_labels, sport_mask) if m]
                sport_accuracy = accuracy_score(sport_labels, sport_predictions)
                results[f'{sport}_accuracy'] = sport_accuracy
                
                logger.info(f"{sport.upper()} Accuracy: {sport_accuracy:.4f}")
        
        # Calculate confidence-based metrics with credibility weighting
        adjusted_confidences = [
            c * cred * tw for c, cred, tw in 
            zip(all_confidences, all_credibilities, all_timestamp_weights)
        ]
        
        confident_predictions = [p for p, c in zip(all_predictions, adjusted_confidences) 
                               if c >= self.confidence_threshold]
        confident_labels = [l for l, c in zip(all_labels, adjusted_confidences) 
                          if c >= self.confidence_threshold]
        
        confident_accuracy = accuracy_score(confident_labels, confident_predictions) if confident_predictions else 0
        coverage = len(confident_predictions) / len(all_predictions)
        
        logger.info(f"Overall Accuracy: {overall_accuracy:.4f}")
        logger.info(f"Confident Predictions Accuracy: {confident_accuracy:.4f}")
        logger.info(f"Coverage (% above threshold): {coverage:.4f}")
        logger.info(f"Predictions needing review: {1-coverage:.4f}")
        
        # Detailed classification report
        target_names = [self.label_decoder[i] for i in range(len(self.label_decoder))]
        print("\nOverall Classification Report:")
        print(classification_report(all_labels, all_predictions, target_names=target_names))
        
        results.update({
            'confident_accuracy': confident_accuracy,
            'coverage': coverage,
            'predictions': all_predictions,
            'labels': all_labels,
            'confidences': all_confidences,
            'sports': all_sports
        })
        
        return results

def main():
    """Main training function"""
    parser = argparse.ArgumentParser(description='Train Multi-Sport BioBERT Injury Classifier')
    parser.add_argument('--nfl-data', default='data/nfl_injury_tweets_labeled_combined.csv',
                        help='Path to NFL injury labeled data')
    parser.add_argument('--nba-data', default=None,
                        help='Path to NBA injury labeled data (optional)')
    parser.add_argument('--epochs', type=int, default=3,
                        help='Number of training epochs')
    parser.add_argument('--batch-size', type=int, default=4,
                        help='Training batch size')
    parser.add_argument('--confidence-threshold', type=float, default=0.8,
                        help='Confidence threshold for predictions')
    
    args = parser.parse_args()
    
    # Initialize classifier
    classifier = MultiSportBioBERTInjuryClassifier(confidence_threshold=args.confidence_threshold)
    
    # Prepare data
    data_splits, label_splits = classifier.prepare_combined_data(args.nfl_data, args.nba_data)
    
    # Initialize model
    num_labels = len(classifier.label_encoder)
    classifier.initialize_model(num_labels)
    
    # Create datasets
    train_dataset, val_dataset, test_dataset = classifier.create_datasets(data_splits, label_splits)
    
    # Train model
    trainer = classifier.train(train_dataset, val_dataset)
    
    # Evaluate model
    logger.info("Evaluating multi-sport model on test set...")
    results = classifier.evaluate_by_sport(test_dataset)
    
    # Save training summary
    training_summary = {
        'model_type': 'MultiSport BioBERT Injury Classifier',
        'training_date': datetime.now().isoformat(),
        'overall_accuracy': results['overall_accuracy'],
        'confident_accuracy': results['confident_accuracy'],
        'coverage': results['coverage'],
        'nfl_accuracy': results.get('nfl_accuracy', 'N/A'),
        'nba_accuracy': results.get('nba_accuracy', 'N/A'),
        'confidence_threshold': args.confidence_threshold,
        'features': ['sport_context', 'author_credibility', 'timestamp_weight'],
        'label_distribution': dict(classifier.label_encoder)
    }
    
    with open('models/multisport_biobert_injury_classifier/training_summary.json', 'w') as f:
        json.dump(training_summary, f, indent=2)
    
    # Test sample predictions
    logger.info("Testing sample predictions with enhanced features...")
    sample_data = [
        ("Patrick Mahomes is out with a torn ACL and will miss the rest of the season", "nfl", "AdamSchefter"),
        ("Aaron Rodgers is questionable for Sunday's game with a minor ankle sprain", "nfl", "RapSheet"),
        ("LeBron James underwent surgery and is expected to be out 6-8 months", "nba", "ShamsCharania"),
        ("Steph Curry is day-to-day with a minor wrist injury", "nba", "wojespn")
    ]
    
    texts = [d[0] for d in sample_data]
    sports = [d[1] for d in sample_data]
    authors = [d[2] for d in sample_data]
    
    predictions = classifier.predict_with_confidence(texts, sports, authors)
    
    print("\n" + "="*80)
    print("SAMPLE MULTI-SPORT PREDICTIONS WITH ENHANCED FEATURES")
    print("="*80)
    
    for pred in predictions:
        print(f"\nText: {pred['text']}")
        print(f"Sport: {pred['sport'].upper()}")
        print(f"Author: {pred['author']}")
        print(f"Predicted: {pred['predicted_label']}")
        print(f"Raw Confidence: {pred['raw_confidence']:.4f}")
        print(f"Adjusted Confidence: {pred['adjusted_confidence']:.4f}")
        print(f"Author Credibility: {pred['author_credibility']:.2f}")
        print(f"Timestamp Weight: {pred['timestamp_weight']:.2f}")
        print(f"Meets threshold: {pred['is_confident']}")
        print(f"Needs review: {pred['needs_review']}")
    
    logger.info("Multi-sport training and evaluation completed successfully!")

if __name__ == "__main__":
    main()
