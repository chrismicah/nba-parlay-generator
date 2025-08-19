#!/usr/bin/env python3
"""
NFL Injury Severity Classifier Training Script
Trains a specialized RoBERTa classifier for injury severity classification
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


class InjuryDataset(Dataset):
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


class InjurySeverityClassifier:
    def __init__(self, model_path='models/nfl_injury_severity_classifier'):
        self.model_path = model_path
        # Injury severity labels from your data
        self.labels = ['unconfirmed', 'out_for_season', 'day_to_day', 'minor']
        self.label_to_id = {label: idx for idx, label in enumerate(self.labels)}
        self.id_to_label = {idx: label for idx, label in enumerate(self.labels)}
        
        self.tokenizer = RobertaTokenizer.from_pretrained('roberta-base')
        self.model = None
        
    def load_training_data(self):
        """Load the combined NFL injury severity dataset"""
        print("📥 Loading NFL injury severity data...")
        
        # Load the combined labeled dataset
        df = pd.read_csv('data/nfl_injury_tweets_labeled_combined.csv')
        
        print(f"   ✅ Loaded {len(df)} NFL injury tweets")
        print(f"\n📊 Injury Severity Distribution:")
        print(df['injury_severity_label'].value_counts())
        
        # Clean and validate labels
        valid_labels = set(self.labels)
        df = df[df['injury_severity_label'].isin(valid_labels)]
        
        # Use the 'text' column for training
        df['training_text'] = df['text'].fillna('')
        
        return df
    
    def prepare_data(self, df):
        """Prepare data for training"""
        print("\n🔧 Preparing data for training...")
        
        # Convert labels to IDs
        df['label_id'] = df['injury_severity_label'].map(self.label_to_id)
        
        # Split data - stratified to maintain label distribution
        train_df, test_df = train_test_split(
            df, test_size=0.2, random_state=42, stratify=df['injury_severity_label']
        )
        
        # Create datasets
        train_dataset = InjuryDataset(
            train_df['training_text'].tolist(),
            train_df['label_id'].tolist(),
            self.tokenizer
        )
        
        test_dataset = InjuryDataset(
            test_df['training_text'].tolist(),
            test_df['label_id'].tolist(),
            self.tokenizer
        )
        
        print(f"   ✅ Training set: {len(train_dataset)} samples")
        print(f"   ✅ Test set: {len(test_dataset)} samples")
        
        return train_dataset, test_dataset, train_df, test_df
    
    def train_model(self, train_dataset, test_dataset, epochs=3, batch_size=8):
        """Train the RoBERTa model for injury severity classification"""
        print(f"\n🏋️ Training NFL injury severity classifier...")
        
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
            warmup_steps=100,
            weight_decay=0.01,
            logging_dir=f'{self.model_path}/logs',
            logging_steps=50,
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
        print("\n📊 Evaluating injury severity classifier...")
        
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
        
        # Confusion matrix
        print("\n📈 Confusion Matrix:")
        cm = confusion_matrix(true_labels, pred_labels, labels=self.labels)
        print("Predicted:")
        print(f"{'':>12}", " ".join(f"{label:>10}" for label in self.labels))
        for i, true_label in enumerate(self.labels):
            print(f"{true_label:>12}", " ".join(f"{cm[i][j]:>10}" for j in range(len(self.labels))))
        
        return accuracy, pred_labels, true_labels
    
    def classify_injury(self, text):
        """Classify injury severity for a single tweet"""
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
        
        predicted_severity = self.id_to_label[predicted_class_id]
        
        return {
            'severity': predicted_severity,
            'confidence': confidence,
            'all_probabilities': {
                self.id_to_label[i]: float(predictions[0][i]) 
                for i in range(len(self.labels))
            }
        }


def main():
    parser = argparse.ArgumentParser(description="Train NFL Injury Severity Classifier")
    parser.add_argument('--epochs', type=int, default=3, help='Number of training epochs')
    parser.add_argument('--batch-size', type=int, default=8, help='Batch size')
    parser.add_argument('--test-only', action='store_true', help='Only test existing model')
    args = parser.parse_args()
    
    # Initialize classifier
    classifier = InjurySeverityClassifier()
    
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
    
    # Test with sample injury tweets
    print("\n🧪 Testing with sample injury tweets:")
    
    sample_tweets = [
        "Player X is out for the season with a torn ACL",
        "QB questionable to return with ankle injury", 
        "RB listed as day-to-day with minor hamstring strain",
        "WR dealing with undisclosed injury, status unclear",
        "TE placed on injured reserve with knee injury"
    ]
    
    for text in sample_tweets:
        result = classifier.classify_injury(text)
        print(f"   Text: '{text}'")
        print(f"   → {result['severity']} ({result['confidence']:.3f})")
        print()


if __name__ == "__main__":
    main()
