#!/usr/bin/env python3
"""
RoBERTa Parlay Confidence Classifier Training - JIRA-019

Fine-tunes RoBERTa on parlay reasoning data to predict parlay confidence.
Implements the classification task to predict if a parlay is "high confidence" 
or "low confidence" based on the ParlayStrategistAgent's textual rationale.
"""

import json
import logging
import os
import random
from pathlib import Path
from typing import List, Dict, Any, Tuple

import torch
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoTokenizer, 
    AutoModelForSequenceClassification, 
    Trainer, 
    TrainingArguments,
    EarlyStoppingCallback
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ParlayReasoningDataset(Dataset):
    """Dataset class for parlay reasoning classification."""
    
    def __init__(self, samples: List[Dict[str, Any]], tokenizer, max_length: int = 512):
        """
        Initialize the dataset.
        
        Args:
            samples: List of parlay reasoning samples
            tokenizer: RoBERTa tokenizer
            max_length: Maximum sequence length
        """
        self.samples = samples
        self.tokenizer = tokenizer
        self.max_length = max_length
        
        # Label mapping
        self.label2id = {"low_confidence": 0, "high_confidence": 1}
        self.id2label = {0: "low_confidence", 1: "high_confidence"}
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        sample = self.samples[idx]
        text = sample["reasoning"]
        label = self.label2id[sample["confidence_label"]]
        
        # Tokenize the reasoning text
        encoding = self.tokenizer(
            text,
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors="pt",
        )
        
        item = {k: v.squeeze(0) for k, v in encoding.items()}
        item["labels"] = torch.tensor(label, dtype=torch.long)
        
        return item


class ParlayConfidenceClassifier:
    """RoBERTa-based parlay confidence classifier."""
    
    def __init__(self, model_name: str = "roberta-base", 
                 model_save_path: str = "models/parlay_confidence_classifier"):
        """
        Initialize the classifier.
        
        Args:
            model_name: Pre-trained model name
            model_save_path: Path to save the trained model
        """
        self.model_name = model_name
        self.model_save_path = Path(model_save_path)
        self.model_save_path.mkdir(parents=True, exist_ok=True)
        
        # Label mapping
        self.label2id = {"low_confidence": 0, "high_confidence": 1}
        self.id2label = {0: "low_confidence", 1: "high_confidence"}
        
        # Initialize tokenizer and model
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = None
        
        logger.info(f"Initialized ParlayConfidenceClassifier with {model_name}")
    
    def load_dataset(self, dataset_path: str) -> List[Dict[str, Any]]:
        """
        Load the parlay reasoning dataset.
        
        Args:
            dataset_path: Path to the JSONL dataset file
            
        Returns:
            List of parlay reasoning samples
        """
        dataset_path = Path(dataset_path)
        
        if not dataset_path.exists():
            raise FileNotFoundError(f"Dataset not found: {dataset_path}")
        
        samples = []
        with open(dataset_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    sample = json.loads(line)
                    # Ensure required fields exist
                    if 'reasoning' in sample and 'confidence_label' in sample:
                        samples.append(sample)
        
        logger.info(f"Loaded {len(samples)} samples from {dataset_path}")
        return samples
    
    def prepare_data(self, samples: List[Dict[str, Any]], 
                    test_size: float = 0.2, 
                    val_size: float = 0.1) -> Tuple[Dataset, Dataset, Dataset]:
        """
        Prepare train, validation, and test datasets.
        
        Args:
            samples: List of parlay reasoning samples
            test_size: Proportion of data for testing
            val_size: Proportion of training data for validation
            
        Returns:
            Tuple of (train_dataset, val_dataset, test_dataset)
        """
        # Split into train and test
        train_samples, test_samples = train_test_split(
            samples, 
            test_size=test_size, 
            random_state=42,
            stratify=[s['confidence_label'] for s in samples]
        )
        
        # Split train into train and validation
        train_samples, val_samples = train_test_split(
            train_samples,
            test_size=val_size,
            random_state=42,
            stratify=[s['confidence_label'] for s in train_samples]
        )
        
        # Create datasets
        train_dataset = ParlayReasoningDataset(train_samples, self.tokenizer)
        val_dataset = ParlayReasoningDataset(val_samples, self.tokenizer)
        test_dataset = ParlayReasoningDataset(test_samples, self.tokenizer)
        
        logger.info(f"Data split: {len(train_samples)} train, {len(val_samples)} val, {len(test_samples)} test")
        
        return train_dataset, val_dataset, test_dataset
    
    def train(self, train_dataset: Dataset, val_dataset: Dataset,
              epochs: int = 3, batch_size: int = 8, learning_rate: float = 2e-5) -> Dict[str, Any]:
        """
        Train the RoBERTa confidence classifier.
        
        Args:
            train_dataset: Training dataset
            val_dataset: Validation dataset
            epochs: Number of training epochs
            batch_size: Training batch size
            learning_rate: Learning rate
            
        Returns:
            Training history and metrics
        """
        # Initialize model
        self.model = AutoModelForSequenceClassification.from_pretrained(
            self.model_name,
            num_labels=len(self.label2id),
            id2label=self.id2label,
            label2id=self.label2id
        )
        
        # Training arguments
        training_args = TrainingArguments(
            output_dir=str(self.model_save_path / "training_runs"),
            num_train_epochs=epochs,
            per_device_train_batch_size=batch_size,
            per_device_eval_batch_size=batch_size,
            learning_rate=learning_rate,
            weight_decay=0.01,
            logging_dir=str(self.model_save_path / "logs"),
            logging_steps=50,
            eval_strategy="steps",  # Updated parameter name
            eval_steps=100,
            save_strategy="steps",
            save_steps=100,
            load_best_model_at_end=True,
            metric_for_best_model="eval_loss",
            greater_is_better=False,
            save_total_limit=3,
            seed=42,
            push_to_hub=False,
            report_to=[]  # Empty list instead of None
        )
        
        # Initialize trainer
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
            tokenizer=self.tokenizer,
            callbacks=[EarlyStoppingCallback(early_stopping_patience=3)]
        )
        
        # Train the model
        logger.info("Starting training...")
        train_result = trainer.train()
        
        # Save the final model
        trainer.save_model(self.model_save_path)
        self.tokenizer.save_pretrained(self.model_save_path)
        
        # Save training metadata
        training_metadata = {
            "model_name": self.model_name,
            "epochs": epochs,
            "batch_size": batch_size,
            "learning_rate": learning_rate,
            "train_samples": len(train_dataset),
            "val_samples": len(val_dataset),
            "label2id": self.label2id,
            "id2label": self.id2label,
            "final_train_loss": train_result.training_loss,
            "training_steps": train_result.global_step
        }
        
        with open(self.model_save_path / "training_metadata.json", 'w') as f:
            json.dump(training_metadata, f, indent=2)
        
        logger.info(f"Training completed. Model saved to {self.model_save_path}")
        
        return training_metadata
    
    def evaluate(self, test_dataset: Dataset) -> Dict[str, Any]:
        """
        Evaluate the trained model on test data.
        
        Args:
            test_dataset: Test dataset
            
        Returns:
            Evaluation metrics
        """
        if self.model is None:
            raise ValueError("Model not trained yet. Call train() first.")
        
        # Set model to evaluation mode
        self.model.eval()
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(device)
        
        # Create data loader
        test_loader = DataLoader(test_dataset, batch_size=16, shuffle=False)
        
        all_predictions = []
        all_labels = []
        all_probabilities = []
        
        with torch.no_grad():
            for batch in test_loader:
                # Move batch to device
                input_ids = batch['input_ids'].to(device)
                attention_mask = batch['attention_mask'].to(device)
                labels = batch['labels'].to(device)
                
                # Forward pass
                outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
                logits = outputs.logits
                
                # Get predictions and probabilities
                probabilities = torch.softmax(logits, dim=-1)
                predictions = torch.argmax(logits, dim=-1)
                
                all_predictions.extend(predictions.cpu().numpy())
                all_labels.extend(labels.cpu().numpy())
                all_probabilities.extend(probabilities.cpu().numpy())
        
        # Calculate metrics
        accuracy = accuracy_score(all_labels, all_predictions)
        precision, recall, f1, _ = precision_recall_fscore_support(all_labels, all_predictions, average='weighted')
        cm = confusion_matrix(all_labels, all_predictions)
        
        # Calculate per-class metrics
        precision_per_class, recall_per_class, f1_per_class, _ = precision_recall_fscore_support(
            all_labels, all_predictions, average=None
        )
        
        evaluation_results = {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "confusion_matrix": cm.tolist(),
            "per_class_metrics": {
                "low_confidence": {
                    "precision": precision_per_class[0],
                    "recall": recall_per_class[0],
                    "f1_score": f1_per_class[0]
                },
                "high_confidence": {
                    "precision": precision_per_class[1],
                    "recall": recall_per_class[1],
                    "f1_score": f1_per_class[1]
                }
            },
            "test_samples": len(test_dataset)
        }
        
        logger.info(f"Evaluation Results:")
        logger.info(f"Accuracy: {accuracy:.4f}")
        logger.info(f"Precision: {precision:.4f}")
        logger.info(f"Recall: {recall:.4f}")
        logger.info(f"F1 Score: {f1:.4f}")
        
        # Save evaluation results
        with open(self.model_save_path / "evaluation_results.json", 'w') as f:
            json.dump(evaluation_results, f, indent=2)
        
        return evaluation_results
    
    def predict_confidence(self, reasoning_text: str) -> Dict[str, Any]:
        """
        Predict confidence for a single parlay reasoning text.
        
        Args:
            reasoning_text: Parlay reasoning text
            
        Returns:
            Prediction results with confidence scores
        """
        if self.model is None:
            raise ValueError("Model not trained yet. Call train() first or load a trained model.")
        
        # Tokenize input
        inputs = self.tokenizer(
            reasoning_text,
            truncation=True,
            max_length=512,
            padding=True,
            return_tensors="pt"
        )
        
        # Set model to evaluation mode
        self.model.eval()
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(device)
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probabilities = torch.softmax(logits, dim=-1)
            prediction = torch.argmax(logits, dim=-1)
        
        predicted_label = self.id2label[prediction.item()]
        confidence_scores = {
            "low_confidence": probabilities[0][0].item(),
            "high_confidence": probabilities[0][1].item()
        }
        
        return {
            "predicted_confidence": predicted_label,
            "confidence_scores": confidence_scores,
            "max_confidence": max(confidence_scores.values())
        }
    
    def load_trained_model(self, model_path: str = None) -> None:
        """
        Load a previously trained model.
        
        Args:
            model_path: Path to the trained model (uses default if None)
        """
        if model_path is None:
            model_path = self.model_save_path
        
        model_path = Path(model_path)
        
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")
        
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
        
        logger.info(f"Loaded trained model from {model_path}")


def main():
    """Main function for training and evaluation."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        print("🤖 RoBERTa Parlay Confidence Classifier Training - JIRA-019")
        print("=" * 70)
        
        # Initialize classifier
        classifier = ParlayConfidenceClassifier()
        
        # Load dataset
        dataset_path = "data/parlay_reasoning_dataset.jsonl"
        print(f"📊 Loading dataset from {dataset_path}...")
        
        try:
            samples = classifier.load_dataset(dataset_path)
        except FileNotFoundError:
            print(f"⚠️ Dataset not found. Generating dataset first...")
            from tools.generate_parlay_reasoning_dataset import ParlayReasoningDatasetGenerator
            
            generator = ParlayReasoningDatasetGenerator(dataset_path)
            generator.generate_dataset(num_samples=1000)
            samples = classifier.load_dataset(dataset_path)
        
        print(f"✅ Loaded {len(samples)} samples")
        
        # Show dataset statistics
        high_conf = len([s for s in samples if s['confidence_label'] == 'high_confidence'])
        low_conf = len([s for s in samples if s['confidence_label'] == 'low_confidence'])
        print(f"📈 Dataset composition: {high_conf} high confidence, {low_conf} low confidence")
        
        # Prepare data
        print("🔄 Preparing training data...")
        train_dataset, val_dataset, test_dataset = classifier.prepare_data(samples)
        
        # Train model
        print("🚀 Training RoBERTa classifier...")
        training_results = classifier.train(
            train_dataset=train_dataset,
            val_dataset=val_dataset,
            epochs=3,
            batch_size=8,
            learning_rate=2e-5
        )
        
        print(f"✅ Training completed!")
        print(f"Final training loss: {training_results['final_train_loss']:.4f}")
        
        # Evaluate model
        print("📊 Evaluating model on test set...")
        evaluation_results = classifier.evaluate(test_dataset)
        
        print(f"\n🎯 Final Evaluation Results:")
        print(f"Accuracy: {evaluation_results['accuracy']:.4f}")
        print(f"Precision: {evaluation_results['precision']:.4f}")
        print(f"Recall: {evaluation_results['recall']:.4f}")
        print(f"F1 Score: {evaluation_results['f1_score']:.4f}")
        
        # Test prediction on sample
        print(f"\n🧪 Testing prediction on sample reasoning...")
        sample_reasoning = samples[0]['reasoning']
        prediction = classifier.predict_confidence(sample_reasoning)
        
        print(f"Sample reasoning (first 200 chars): {sample_reasoning[:200]}...")
        print(f"Predicted confidence: {prediction['predicted_confidence']}")
        print(f"Confidence scores: {prediction['confidence_scores']}")
        print(f"Actual label: {samples[0]['confidence_label']}")
        
        print(f"\n✅ JIRA-019 Implementation Complete!")
        print(f"🎯 RoBERTa confidence classifier trained and ready for use")
        print(f"📁 Model saved to: {classifier.model_save_path}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
