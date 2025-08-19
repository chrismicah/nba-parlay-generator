#!/usr/bin/env python3
"""
Multi-Sport Tweet Classifier Training Script
Combines NBA and NFL labeled data to train a RoBERTa classifier
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from transformers import (
    RobertaTokenizer, RobertaForSequenceClassification,
    TrainingArguments, Trainer, DataCollatorWithPadding
)
import torch
from torch.utils.data import Dataset
import json
import os
from datetime import datetime
import argparse


class TweetDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_length=512):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = str(self.texts[idx])
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
            'labels': torch.tensor(self.labels[idx], dtype=torch.long)
        }


class MultiSportTweetClassifier:
    def __init__(self, model_path='models/multi_sport_tweet_classifier'):
        self.model_path = model_path
        self.labels = ['injury_news', 'lineup_news', 'general_commentary', 'irrelevant']
        self.label_to_id = {label: idx for idx, label in enumerate(self.labels)}
        self.id_to_label = {idx: label for idx, label in enumerate(self.labels)}
        
        self.tokenizer = RobertaTokenizer.from_pretrained('roberta-base')
        self.model = None
        
    def load_training_data(self):
        """Load and combine NBA and NFL labeled datasets"""
        print("📥 Loading training data...")
        
        # Load NFL data
        print("   Loading NFL tweets...")
        nfl_df = pd.read_csv('data/labeled_nfl_tweets.csv')
        nfl_df['sport'] = 'nfl'
        print(f"   ✅ Loaded {len(nfl_df)} NFL tweets")
        
        # Load NBA data (if exists)
        nba_df = None
        nba_files = [
            'data/tweets/labeled_tweets.jsonl',
            'data/labeled_nba_tweets.csv'
        ]
        
        for file_path in nba_files:
            if os.path.exists(file_path):
                print(f"   Loading NBA tweets from {file_path}...")
                if file_path.endswith('.jsonl'):
                    nba_df = pd.read_json(file_path, lines=True)
                else:
                    nba_df = pd.read_csv(file_path)
                nba_df['sport'] = 'nba'
                print(f"   ✅ Loaded {len(nba_df)} NBA tweets")
                break
        
        # Combine datasets
        if nba_df is not None:
            # Ensure consistent column names
            common_cols = ['text', 'label', 'sport']
            if 'author' in nfl_df.columns and 'author' in nba_df.columns:
                common_cols.append('author')
            
            combined_df = pd.concat([
                nfl_df[common_cols],
                nba_df[common_cols]
            ], ignore_index=True)
            print(f"   ✅ Combined dataset: {len(combined_df)} tweets")
        else:
            print("   ⚠️  No NBA data found, using NFL data only")
            combined_df = nfl_df[['text', 'label', 'sport', 'author']]
        
        # Clean and validate labels
        valid_labels = set(self.labels)
        combined_df = combined_df[combined_df['label'].isin(valid_labels)]
        
        print(f"\n📊 Label Distribution:")
        print(combined_df['label'].value_counts())
        print(f"\n🏈🏀 Sport Distribution:")
        print(combined_df['sport'].value_counts())
        
        return combined_df
    
    def prepare_data(self, df):
        """Prepare data for training"""
        print("\n🔧 Preparing data for training...")
        
        # Convert labels to IDs
        df['label_id'] = df['label'].map(self.label_to_id)
        
        # Split data
        train_df, test_df = train_test_split(
            df, test_size=0.2, random_state=42, stratify=df['label']
        )
        
        # Create datasets
        train_dataset = TweetDataset(
            train_df['text'].tolist(),
            train_df['label_id'].tolist(),
            self.tokenizer
        )
        
        test_dataset = TweetDataset(
            test_df['text'].tolist(),
            test_df['label_id'].tolist(),
            self.tokenizer
        )
        
        print(f"   ✅ Training set: {len(train_dataset)} samples")
        print(f"   ✅ Test set: {len(test_dataset)} samples")
        
        return train_dataset, test_dataset, train_df, test_df
    
    def train_model(self, train_dataset, test_dataset, epochs=3, batch_size=16):
        """Train the RoBERTa model"""
        print(f"\n🏋️ Training multi-sport classifier...")
        
        # Initialize model
        self.model = RobertaForSequenceClassification.from_pretrained(
            'roberta-base',
            num_labels=len(self.labels),
            problem_type="single_label_classification"
        )
        
        # Training arguments
        training_args = TrainingArguments(
            output_dir=self.model_path,
            num_train_epochs=epochs,
            per_device_train_batch_size=batch_size,
            per_device_eval_batch_size=batch_size,
            warmup_steps=500,
            weight_decay=0.01,
            logging_dir=f'{self.model_path}/logs',
            logging_steps=100,
            eval_strategy="epoch",
            save_strategy="epoch",
            load_best_model_at_end=True,
            metric_for_best_model="eval_loss",
            greater_is_better=False,
        )
        
        # Data collator
        data_collator = DataCollatorWithPadding(tokenizer=self.tokenizer)
        
        # Trainer
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=test_dataset,
            tokenizer=self.tokenizer,
            data_collator=data_collator,
        )
        
        # Train
        trainer.train()
        
        # Save model
        trainer.save_model()
        self.tokenizer.save_pretrained(self.model_path)
        
        # Save label mappings
        with open(f'{self.model_path}/label_mappings.json', 'w') as f:
            json.dump({
                'labels': self.labels,
                'label_to_id': self.label_to_id,
                'id_to_label': self.id_to_label
            }, f, indent=2)
        
        print(f"   ✅ Model saved to {self.model_path}")
        
        return trainer
    
    def evaluate_model(self, trainer, test_dataset, test_df):
        """Evaluate the trained model"""
        print("\n📊 Evaluating model performance...")
        
        # Get predictions
        predictions = trainer.predict(test_dataset)
        y_pred = np.argmax(predictions.predictions, axis=1)
        y_true = predictions.label_ids
        
        # Convert back to labels
        pred_labels = [self.id_to_label[pred] for pred in y_pred]
        true_labels = [self.id_to_label[true] for true in y_true]
        
        # Calculate metrics
        accuracy = accuracy_score(true_labels, pred_labels)
        print(f"\n✅ Overall Accuracy: {accuracy:.4f}")
        
        # Detailed classification report
        print("\n📋 Classification Report:")
        print(classification_report(true_labels, pred_labels))
        
        # Sport-specific evaluation
        test_df_eval = test_df.copy()
        test_df_eval['predicted_label'] = pred_labels
        
        print("\n🏈 NFL Performance:")
        nfl_mask = test_df_eval['sport'] == 'nfl'
        if nfl_mask.sum() > 0:
            nfl_accuracy = accuracy_score(
                test_df_eval[nfl_mask]['label'],
                test_df_eval[nfl_mask]['predicted_label']
            )
            print(f"   Accuracy: {nfl_accuracy:.4f}")
        
        print("\n🏀 NBA Performance:")
        nba_mask = test_df_eval['sport'] == 'nba'
        if nba_mask.sum() > 0:
            nba_accuracy = accuracy_score(
                test_df_eval[nba_mask]['label'],
                test_df_eval[nba_mask]['predicted_label']
            )
            print(f"   Accuracy: {nba_accuracy:.4f}")
        
        return accuracy, pred_labels, true_labels
    
    def classify_tweet(self, text, sport=None):
        """Classify a single tweet"""
        if self.model is None:
            self.model = RobertaForSequenceClassification.from_pretrained(self.model_path)
        
        # Tokenize
        inputs = self.tokenizer(
            text,
            truncation=True,
            padding=True,
            max_length=512,
            return_tensors='pt'
        )
        
        # Predict
        with torch.no_grad():
            outputs = self.model(**inputs)
            predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
            predicted_class_id = predictions.argmax().item()
            confidence = predictions.max().item()
        
        predicted_label = self.id_to_label[predicted_class_id]
        
        return {
            'label': predicted_label,
            'confidence': confidence,
            'sport': sport or 'unknown'
        }


def main():
    parser = argparse.ArgumentParser(description="Train Multi-Sport Tweet Classifier")
    parser.add_argument('--epochs', type=int, default=3, help='Number of training epochs')
    parser.add_argument('--batch-size', type=int, default=16, help='Batch size')
    parser.add_argument('--test-only', action='store_true', help='Only test existing model')
    args = parser.parse_args()
    
    # Initialize classifier
    classifier = MultiSportTweetClassifier()
    
    if not args.test_only:
        # Load and prepare data
        df = classifier.load_training_data()
        train_dataset, test_dataset, train_df, test_df = classifier.prepare_data(df)
        
        # Train model
        trainer = classifier.train_model(train_dataset, test_dataset, args.epochs, args.batch_size)
        
        # Evaluate
        accuracy, pred_labels, true_labels = classifier.evaluate_model(trainer, test_dataset, test_df)
        
        # Save training summary
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_samples': len(df),
            'training_samples': len(train_dataset),
            'test_samples': len(test_dataset),
            'accuracy': float(accuracy),
            'labels': classifier.labels,
            'epochs': args.epochs,
            'batch_size': args.batch_size
        }
        
        with open(f'{classifier.model_path}/training_summary.json', 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n🎉 Training complete! Summary saved to {classifier.model_path}/training_summary.json")
    
    # Test with sample tweets
    print("\n🧪 Testing with sample tweets:")
    
    sample_tweets = [
        ("Patrick Mahomes dealing with ankle injury, questionable for Sunday", "nfl"),
        ("LeBron James scores 30 points in Lakers victory", "nba"),
        ("Weather update for today's game", "nfl"),
        ("Trade rumors swirling around star quarterback", "nfl")
    ]
    
    for text, sport in sample_tweets:
        result = classifier.classify_tweet(text, sport)
        print(f"   Text: '{text[:50]}...'")
        print(f"   → {result['label']} ({result['confidence']:.3f}) [{sport}]")


if __name__ == "__main__":
    main()
