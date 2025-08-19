#!/usr/bin/env python3
"""
Enhanced Multi-Sport Tweet Classifier - JIRA-NFL-003
Fine-tunes RoBERTa on combined NBA/NFL dataset with sport as a feature
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoTokenizer, 
    AutoModelForSequenceClassification, 
    TrainingArguments, 
    Trainer,
    EarlyStoppingCallback
)
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import argparse

# Labels for classification
LABELS = ["injury_news", "lineup_news", "general_commentary", "irrelevant"]
LABEL_TO_ID = {label: i for i, label in enumerate(LABELS)}
ID_TO_LABEL = {i: label for label, i in LABEL_TO_ID.items()}

class MultiSportTweetDataset(Dataset):
    """Dataset class for multi-sport tweet classification"""
    
    def __init__(self, texts: List[str], sports: List[str], labels: List[int], tokenizer, max_length: int = 128):
        self.texts = texts
        self.sports = sports
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length
        
        # Create sport feature mapping
        self.sport_to_id = {"nba": 0, "nfl": 1}
    
    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, idx):
        text = str(self.texts[idx])
        sport = str(self.sports[idx])
        label = self.labels[idx]
        
        # Add sport context to text
        sport_prefix = f"[{sport.upper()}] "
        enhanced_text = sport_prefix + text
        
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
            'sport_id': torch.tensor(self.sport_to_id.get(sport, 0), dtype=torch.long)
        }

class MultiSportTweetClassifier:
    """Enhanced tweet classifier supporting both NBA and NFL"""
    
    def __init__(self, model_name: str = "roberta-base"):
        self.model_name = model_name
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = None
        self.labels = LABELS
        
        # Add special tokens if needed
        if "[NBA]" not in self.tokenizer.vocab:
            self.tokenizer.add_tokens(["[NBA]", "[NFL]"])
    
    def load_training_data(self) -> Tuple[List[str], List[str], List[int]]:
        """Load combined NBA and NFL training data"""
        texts, sports, labels = [], [], []
        
        # Load NFL data
        nfl_file = Path("data/nfl_tweets_labeled_training.csv")
        if nfl_file.exists():
            nfl_df = pd.read_csv(nfl_file)
            texts.extend(nfl_df['text'].tolist())
            sports.extend(nfl_df['sport'].tolist())
            nfl_labels = [LABEL_TO_ID[label] for label in nfl_df['label'].tolist()]
            labels.extend(nfl_labels)
            print(f"📊 Loaded {len(nfl_df)} NFL tweets")
        
        # Load NBA data (if exists)
        nba_file = Path("data/nba_tweets_labeled_training.csv")
        if nba_file.exists():
            nba_df = pd.read_csv(nba_file)
            texts.extend(nba_df['text'].tolist())
            sports.extend(nba_df['sport'].tolist())
            nba_labels = [LABEL_TO_ID[label] for label in nba_df['label'].tolist()]
            labels.extend(nba_labels)
            print(f"📊 Loaded {len(nba_df)} NBA tweets")
        else:
            # Create sample NBA data for balanced training
            nba_sample_data = self._create_sample_nba_data()
            nba_df = pd.DataFrame(nba_sample_data)
            nba_df.to_csv(nba_file, index=False)
            
            texts.extend(nba_df['text'].tolist())
            sports.extend(nba_df['sport'].tolist())
            nba_labels = [LABEL_TO_ID[label] for label in nba_df['label'].tolist()]
            labels.extend(nba_labels)
            print(f"📊 Created and loaded {len(nba_df)} sample NBA tweets")
        
        print(f"📈 Total training data: {len(texts)} tweets")
        print(f"🏀 NBA: {sports.count('nba')} tweets")
        print(f"🏈 NFL: {sports.count('nfl')} tweets")
        
        return texts, sports, labels
    
    def _create_sample_nba_data(self) -> List[Dict]:
        """Create sample NBA data for balanced training"""
        return [
            # Injury News
            {"text": "Lakers star LeBron James out 1-2 weeks with ankle sprain", "label": "injury_news", "sport": "nba"},
            {"text": "Warriors guard Stephen Curry questionable for tonight with knee soreness", "label": "injury_news", "sport": "nba"},
            {"text": "Celtics forward Jayson Tatum ruled OUT for Friday's game with back injury", "label": "injury_news", "sport": "nba"},
            
            # Lineup News
            {"text": "Heat starting lineup: Butler, Adebayo, Herro confirmed for tonight", "label": "lineup_news", "sport": "nba"},
            {"text": "Nuggets start Jokic at center with Murray getting bulk of PG minutes", "label": "lineup_news", "sport": "nba"},
            {"text": "Bucks expected to start Giannis, Dame, Middleton in key playoff matchup", "label": "lineup_news", "sport": "nba"},
            
            # General Commentary
            {"text": "Suns offense has been exceptional despite Kevin Durant's recent struggles", "label": "general_commentary", "sport": "nba"},
            {"text": "Clippers defense showing remarkable improvement in perimeter defense metrics", "label": "general_commentary", "sport": "nba"},
            {"text": "Kings pace of play has increased dramatically with De'Aaron Fox's leadership", "label": "general_commentary", "sport": "nba"},
            
            # Irrelevant
            {"text": "Join our $10K NBA DFS contest this weekend! Use promo code HOOPS", "label": "irrelevant", "sport": "nba"},
            {"text": "Check out our NHL playoff predictions and Stanley Cup odds!", "label": "irrelevant", "sport": "nba"},
            {"text": "Follow us on TikTok for exclusive NBA behind-the-scenes content", "label": "irrelevant", "sport": "nba"}
        ]
    
    def fine_tune(self, output_dir: str = "models/multi_sport_tweet_classifier", num_epochs: int = 3):
        """Fine-tune RoBERTa on combined NBA/NFL dataset"""
        
        print("🤖 Loading training data...")
        texts, sports, labels = self.load_training_data()
        
        # Split data
        train_texts, val_texts, train_sports, val_sports, train_labels, val_labels = train_test_split(
            texts, sports, labels, test_size=0.2, random_state=42, stratify=labels
        )
        
        print(f"📊 Training set: {len(train_texts)} tweets")
        print(f"📊 Validation set: {len(val_texts)} tweets")
        
        # Initialize model
        self.model = AutoModelForSequenceClassification.from_pretrained(
            self.model_name,
            num_labels=len(LABELS)
        )
        
        # Resize token embeddings if we added new tokens
        self.model.resize_token_embeddings(len(self.tokenizer))
        
        # Create datasets
        train_dataset = MultiSportTweetDataset(train_texts, train_sports, train_labels, self.tokenizer)
        val_dataset = MultiSportTweetDataset(val_texts, val_sports, val_labels, self.tokenizer)
        
        # Training arguments
        training_args = TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=num_epochs,
            per_device_train_batch_size=16,
            per_device_eval_batch_size=16,
            warmup_steps=100,
            weight_decay=0.01,
            logging_dir=f"{output_dir}/logs",
            logging_steps=10,
            evaluation_strategy="epoch",
            save_strategy="epoch",
            load_best_model_at_end=True,
            metric_for_best_model="eval_accuracy",
            greater_is_better=True
        )
        
        # Define compute metrics function
        def compute_metrics(eval_pred):
            predictions, labels = eval_pred
            predictions = np.argmax(predictions, axis=1)
            accuracy = accuracy_score(labels, predictions)
            return {"accuracy": accuracy}
        
        # Initialize trainer
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
            compute_metrics=compute_metrics,
            callbacks=[EarlyStoppingCallback(early_stopping_patience=2)]
        )
        
        print("🏋️ Starting fine-tuning...")
        trainer.train()
        
        # Save model and tokenizer
        trainer.save_model()
        self.tokenizer.save_pretrained(output_dir)
        
        print(f"✅ Model saved to {output_dir}")
        
        # Evaluate on validation set
        print("\n📊 Final Evaluation:")
        eval_results = trainer.evaluate()
        print(f"Validation Accuracy: {eval_results['eval_accuracy']:.3f}")
        
        return output_dir
    
    def classify_tweet(self, text: str, sport: str, model_dir: str = "models/multi_sport_tweet_classifier") -> Dict:
        """Classify a single tweet with sport context"""
        
        # Load model if not already loaded
        if self.model is None:
            self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_dir)
        
        # Add sport context
        sport_prefix = f"[{sport.upper()}] "
        enhanced_text = sport_prefix + text
        
        # Tokenize
        encoding = self.tokenizer(
            enhanced_text,
            truncation=True,
            padding=True,
            max_length=128,
            return_tensors='pt'
        )
        
        # Predict
        with torch.no_grad():
            outputs = self.model(**encoding)
            predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
            confidence, predicted_id = torch.max(predictions, dim=-1)
        
        predicted_label = ID_TO_LABEL[predicted_id.item()]
        confidence_score = confidence.item()
        
        return {
            "text": text,
            "sport": sport,
            "predicted_label": predicted_label,
            "confidence": confidence_score,
            "all_probabilities": {
                label: predictions[0][i].item() 
                for i, label in enumerate(LABELS)
            }
        }


def main():
    """Main function for training and testing the multi-sport classifier"""
    parser = argparse.ArgumentParser(description="Multi-Sport Tweet Classifier")
    parser.add_argument("--train", action="store_true", help="Train the model")
    parser.add_argument("--test", action="store_true", help="Test the model")
    parser.add_argument("--text", type=str, help="Text to classify")
    parser.add_argument("--sport", type=str, choices=["nba", "nfl"], default="nba", help="Sport context")
    parser.add_argument("--model-dir", default="models/multi_sport_tweet_classifier", help="Model directory")
    args = parser.parse_args()
    
    classifier = MultiSportTweetClassifier()
    
    if args.train:
        print("🤖 Training Multi-Sport Tweet Classifier...")
        model_dir = classifier.fine_tune(output_dir=args.model_dir)
        print(f"✅ Training complete! Model saved to {model_dir}")
    
    if args.test or args.text:
        print("🧪 Testing Multi-Sport Tweet Classifier...")
        
        if args.text:
            # Test single tweet
            result = classifier.classify_tweet(args.text, args.sport, args.model_dir)
            print(f"\nInput: {result['text']}")
            print(f"Sport: {result['sport'].upper()}")
            print(f"Predicted: {result['predicted_label']}")
            print(f"Confidence: {result['confidence']:.3f}")
            print("\nAll probabilities:")
            for label, prob in result['all_probabilities'].items():
                print(f"  {label}: {prob:.3f}")
        else:
            # Test sample tweets
            test_tweets = [
                ("Chiefs QB Mahomes out with ankle injury", "nfl"),
                ("Lakers star LeBron questionable for tonight", "nba"),
                ("Bills starting lineup: Allen, Diggs confirmed", "nfl"),
                ("Warriors start Curry, Thompson, Green tonight", "nba"),
                ("Join our $5K fantasy contest!", "nfl"),
                ("Cowboys defense impressive despite injuries", "nfl")
            ]
            
            for text, sport in test_tweets:
                result = classifier.classify_tweet(text, sport, args.model_dir)
                print(f"\n{sport.upper()}: {text}")
                print(f"→ {result['predicted_label']} ({result['confidence']:.3f})")


if __name__ == "__main__":
    main()
