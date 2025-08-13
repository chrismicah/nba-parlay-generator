#!/usr/bin/env python3
"""
BioBERT-based Injury Severity Classification Model

This script fine-tunes BioBERT on sports injury data to classify injury severity
with confidence thresholding for uncertain predictions.
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
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InjuryDataset(Dataset):
    """Custom dataset for injury severity classification"""
    
    def __init__(self, texts, labels, tokenizer, max_length=512):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = self.labels[idx]
        
        # Tokenize the text
        encoding = self.tokenizer(
            text,
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.long)
        }

class BioBERTInjuryClassifier:
    """BioBERT-based injury severity classifier with confidence thresholding"""
    
    def __init__(self, model_name="dmis-lab/biobert-base-cased-v1.1", confidence_threshold=0.8):
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.tokenizer = None
        self.model = None
        self.label_encoder = {}
        self.label_decoder = {}
        
    def prepare_data(self, csv_path):
        """Load and prepare the injury severity dataset"""
        logger.info(f"Loading data from {csv_path}")
        
        # Load the dataset
        df = pd.read_csv(csv_path)
        
        # Filter out rows with missing text or labels
        df = df.dropna(subset=['text', 'injury_severity'])
        
        # Create label mappings
        unique_labels = sorted(df['injury_severity'].unique())
        self.label_encoder = {label: idx for idx, label in enumerate(unique_labels)}
        self.label_decoder = {idx: label for label, idx in self.label_encoder.items()}
        
        logger.info(f"Label mappings: {self.label_encoder}")
        
        # Encode labels
        df['encoded_labels'] = df['injury_severity'].map(self.label_encoder)
        
        # Split the data
        X_train, X_test, y_train, y_test = train_test_split(
            df['text'].tolist(),
            df['encoded_labels'].tolist(),
            test_size=0.2,
            random_state=42,
            stratify=df['encoded_labels']
        )
        
        # Further split training data for validation
        X_train, X_val, y_train, y_val = train_test_split(
            X_train, y_train,
            test_size=0.2,
            random_state=42,
            stratify=y_train
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
    
    def create_datasets(self, texts, labels):
        """Create PyTorch datasets"""
        X_train, X_val, X_test = texts
        y_train, y_val, y_test = labels
        
        train_dataset = InjuryDataset(X_train, y_train, self.tokenizer)
        val_dataset = InjuryDataset(X_val, y_val, self.tokenizer)
        test_dataset = InjuryDataset(X_test, y_test, self.tokenizer)
        
        return train_dataset, val_dataset, test_dataset
    
    def compute_metrics(self, eval_pred):
        """Compute metrics for evaluation"""
        predictions, labels = eval_pred
        predictions = np.argmax(predictions, axis=1)
        return {'accuracy': accuracy_score(labels, predictions)}
    
    def train(self, train_dataset, val_dataset, output_dir="models/biobert_injury_classifier"):
        """Train the BioBERT model"""
        logger.info("Starting model training...")
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Training arguments
        training_args = TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=5,
            per_device_train_batch_size=8,
            per_device_eval_batch_size=8,
            warmup_steps=100,
            weight_decay=0.01,
            logging_dir=f'{output_dir}/logs',
            logging_steps=10,
            eval_strategy="steps",  # Updated parameter name
            eval_steps=50,
            save_strategy="steps",
            save_steps=50,
            load_best_model_at_end=True,
            metric_for_best_model="accuracy",
            greater_is_better=True,
            save_total_limit=2,
            report_to=None  # Disable wandb/tensorboard
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
        
        # Save label mappings
        with open(f"{output_dir}/label_mappings.json", "w") as f:
            json.dump({
                "label_encoder": self.label_encoder,
                "label_decoder": self.label_decoder,
                "confidence_threshold": self.confidence_threshold
            }, f, indent=2)
        
        logger.info(f"Model saved to {output_dir}")
        return trainer
    
    def predict_with_confidence(self, texts, model_path="models/biobert_injury_classifier"):
        """Make predictions with confidence scores"""
        # Load model if not already loaded
        if self.model is None:
            self.load_model(model_path)
        
        # Move model to CPU to avoid MPS issues
        device = torch.device('cpu')
        self.model = self.model.to(device)
        
        # Tokenize inputs
        inputs = self.tokenizer(
            texts,
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
            confidence_scores, predicted_classes = torch.max(probabilities, dim=-1)
            
        results = []
        for i, text in enumerate(texts):
            pred_class = predicted_classes[i].item()
            confidence = confidence_scores[i].item()
            predicted_label = self.label_decoder[pred_class]
            
            # Determine if prediction meets confidence threshold
            is_confident = confidence >= self.confidence_threshold
            
            results.append({
                'text': text,
                'predicted_label': predicted_label,
                'confidence': confidence,
                'is_confident': is_confident,
                'needs_review': not is_confident,
                'all_probabilities': {
                    self.label_decoder[j]: probabilities[i][j].item() 
                    for j in range(len(self.label_decoder))
                }
            })
        
        return results
    
    def load_model(self, model_path):
        """Load a trained model"""
        logger.info(f"Loading model from {model_path}")
        
        # Load label mappings
        with open(f"{model_path}/label_mappings.json", "r") as f:
            mappings = json.load(f)
            self.label_encoder = mappings["label_encoder"]
            self.label_decoder = {int(k): v for k, v in mappings["label_decoder"].items()}
            self.confidence_threshold = mappings.get("confidence_threshold", 0.8)
        
        # Load model and tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
        
        logger.info("Model loaded successfully")
    
    def evaluate(self, test_dataset, model_path="models/biobert_injury_classifier"):
        """Evaluate the model on test data"""
        if self.model is None:
            self.load_model(model_path)
        
        # Move model to CPU to avoid MPS issues
        device = torch.device('cpu')
        self.model = self.model.to(device)
        
        # Create data loader
        test_loader = DataLoader(test_dataset, batch_size=8, shuffle=False)
        
        all_predictions = []
        all_labels = []
        all_confidences = []
        
        self.model.eval()
        with torch.no_grad():
            for batch in test_loader:
                # Move batch to CPU
                batch = {k: v.to(device) for k, v in batch.items()}
                
                outputs = self.model(
                    input_ids=batch['input_ids'],
                    attention_mask=batch['attention_mask']
                )
                
                logits = outputs.logits
                probabilities = torch.softmax(logits, dim=-1)
                confidence_scores, predicted_classes = torch.max(probabilities, dim=-1)
                
                all_predictions.extend(predicted_classes.cpu().numpy())
                all_labels.extend(batch['labels'].cpu().numpy())
                all_confidences.extend(confidence_scores.cpu().numpy())
        
        # Calculate metrics
        accuracy = accuracy_score(all_labels, all_predictions)
        
        # Calculate confidence-based metrics
        confident_predictions = [p for p, c in zip(all_predictions, all_confidences) 
                               if c >= self.confidence_threshold]
        confident_labels = [l for l, c in zip(all_labels, all_confidences) 
                          if c >= self.confidence_threshold]
        
        confident_accuracy = accuracy_score(confident_labels, confident_predictions) if confident_predictions else 0
        coverage = len(confident_predictions) / len(all_predictions)
        
        logger.info(f"Overall Accuracy: {accuracy:.4f}")
        logger.info(f"Confident Predictions Accuracy: {confident_accuracy:.4f}")
        logger.info(f"Coverage (% above threshold): {coverage:.4f}")
        logger.info(f"Predictions needing review: {1-coverage:.4f}")
        
        # Detailed classification report
        target_names = [self.label_decoder[i] for i in range(len(self.label_decoder))]
        print("\nClassification Report:")
        print(classification_report(all_labels, all_predictions, target_names=target_names))
        
        return {
            'accuracy': accuracy,
            'confident_accuracy': confident_accuracy,
            'coverage': coverage,
            'predictions': all_predictions,
            'labels': all_labels,
            'confidences': all_confidences
        }

def main():
    """Main training function"""
    # Initialize classifier
    classifier = BioBERTInjuryClassifier(confidence_threshold=0.8)
    
    # Prepare data
    data_path = "data/tweets/nba_reporters_expanded_injury_severity_filtered.csv"
    texts, labels = classifier.prepare_data(data_path)
    
    # Initialize model
    num_labels = len(classifier.label_encoder)
    classifier.initialize_model(num_labels)
    
    # Create datasets
    train_dataset, val_dataset, test_dataset = classifier.create_datasets(texts, labels)
    
    # Train model
    trainer = classifier.train(train_dataset, val_dataset)
    
    # Evaluate model
    logger.info("Evaluating model on test set...")
    results = classifier.evaluate(test_dataset)
    
    # Test some sample predictions
    logger.info("Testing sample predictions with confidence scores...")
    sample_texts = [
        "LeBron James is out with a torn ACL and will miss the rest of the season",
        "Steph Curry is questionable for tonight's game with a minor ankle sprain",
        "The Lakers signed a new player to a contract",
        "Kawhi Leonard underwent surgery and is expected to be out 6-8 months"
    ]
    
    predictions = classifier.predict_with_confidence(sample_texts)
    
    print("\n" + "="*80)
    print("SAMPLE PREDICTIONS WITH CONFIDENCE SCORES")
    print("="*80)
    
    for pred in predictions:
        print(f"\nText: {pred['text']}")
        print(f"Predicted: {pred['predicted_label']}")
        print(f"Confidence: {pred['confidence']:.4f}")
        print(f"Meets threshold: {pred['is_confident']}")
        print(f"Needs review: {pred['needs_review']}")
        print("All probabilities:")
        for label, prob in pred['all_probabilities'].items():
            print(f"  {label}: {prob:.4f}")
    
    logger.info("Training and evaluation completed successfully!")

if __name__ == "__main__":
    main()
