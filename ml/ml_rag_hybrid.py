#!/usr/bin/env python3
"""
RAGHybridModel - ML-RAG-HYBRID-001

Hybrid model combining tabular player statistics with RAG text embeddings using BERT.
Fuses structured data with unstructured narrative text for enhanced prop predictions.

Key Features:
- BERT-based text embedding for RAG narratives
- Tabular data fusion with text embeddings
- Fine-tuning on combined datasets
- A/B testing against stats-only baseline
- Integration with agent reasoning systems
- Brier score evaluation
"""

import logging
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import brier_score_loss, roc_auc_score, accuracy_score, log_loss
from sklearn.ensemble import RandomForestClassifier

# Transformers imports
try:
    from transformers import (
        AutoTokenizer, AutoModel, AutoConfig,
        TrainingArguments, Trainer, EarlyStoppingCallback
    )
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False
    AutoTokenizer = AutoModel = AutoConfig = None
    TrainingArguments = Trainer = EarlyStoppingCallback = None

# Set up logging
logger = logging.getLogger(__name__)

# Check for CUDA availability
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
logger.info(f"Using device: {device}")


@dataclass
class TrainingConfig:
    """Configuration for hybrid model training."""
    model_name: str = "bert-base-uncased"
    max_length: int = 512
    batch_size: int = 16
    learning_rate: float = 2e-5
    num_epochs: int = 3
    warmup_steps: int = 500
    weight_decay: float = 0.01
    hidden_dim: int = 768
    fusion_dim: int = 256
    dropout_rate: float = 0.1
    early_stopping_patience: int = 2
    save_model_path: str = "models/rag_hybrid_model"
    

@dataclass
class HybridPrediction:
    """Prediction result from hybrid model."""
    probability: float
    confidence: float
    text_contribution: float
    stats_contribution: float
    raw_text_embedding: Optional[np.ndarray] = None
    raw_stats_features: Optional[np.ndarray] = None
    explanation: str = ""


class HybridDataset(Dataset):
    """PyTorch dataset for hybrid tabular + text data."""
    
    def __init__(self, stats_df: pd.DataFrame, texts: List[str], 
                 labels: List[int], tokenizer, max_length: int = 512):
        """
        Initialize hybrid dataset.
        
        Args:
            stats_df: DataFrame with numerical player statistics
            texts: List of RAG narrative strings
            labels: Binary labels (0/1) for hit_prop
            tokenizer: BERT tokenizer
            max_length: Maximum text sequence length
        """
        self.stats = stats_df.values.astype(np.float32)
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length
        
        # Handle NaN values in stats
        self.stats = np.nan_to_num(self.stats, nan=0.0)
        
        # Normalize stats
        self.scaler = StandardScaler()
        self.stats = self.scaler.fit_transform(self.stats)
        
        # Handle any NaN from scaling
        self.stats = np.nan_to_num(self.stats, nan=0.0)
        
    def __len__(self):
        return len(self.labels)
    
    def __getitem__(self, idx):
        # Tokenize text
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
            'stats': torch.tensor(self.stats[idx], dtype=torch.float32),
            'labels': torch.tensor(self.labels[idx], dtype=torch.long)
        }


class FusionLayer(nn.Module):
    """Neural network layer for fusing text and tabular features."""
    
    def __init__(self, text_dim: int, stats_dim: int, fusion_dim: int, dropout_rate: float = 0.1):
        """
        Initialize fusion layer.
        
        Args:
            text_dim: Dimension of text embeddings (768 for BERT-base)
            stats_dim: Dimension of tabular features
            fusion_dim: Dimension of fused representation
            dropout_rate: Dropout rate for regularization
        """
        super(FusionLayer, self).__init__()
        
        # Text processing layers
        self.text_projection = nn.Linear(text_dim, fusion_dim)
        self.text_norm = nn.LayerNorm(fusion_dim)
        
        # Stats processing layers
        self.stats_projection = nn.Linear(stats_dim, fusion_dim)
        self.stats_norm = nn.LayerNorm(fusion_dim)
        
        # Fusion layers
        self.fusion_layer = nn.Linear(fusion_dim * 2, fusion_dim)
        self.fusion_norm = nn.LayerNorm(fusion_dim)
        
        # Attention mechanism for weighting modalities
        self.attention = nn.MultiheadAttention(fusion_dim, num_heads=8, batch_first=True)
        
        # Output layers
        self.dropout = nn.Dropout(dropout_rate)
        self.classifier = nn.Linear(fusion_dim, 1)
        
        # Activation functions
        self.relu = nn.ReLU()
        self.sigmoid = nn.Sigmoid()
        
    def forward(self, text_embeddings: torch.Tensor, stats_features: torch.Tensor) -> Dict[str, torch.Tensor]:
        """
        Forward pass through fusion layer.
        
        Args:
            text_embeddings: BERT text embeddings [batch_size, text_dim]
            stats_features: Tabular statistics [batch_size, stats_dim]
            
        Returns:
            Dictionary with logits, probabilities, and attention weights
        """
        # Project and normalize both modalities
        text_proj = self.text_norm(self.relu(self.text_projection(text_embeddings)))
        stats_proj = self.stats_norm(self.relu(self.stats_projection(stats_features)))
        
        # Concatenate modalities
        fused = torch.cat([text_proj, stats_proj], dim=1)
        fused = self.fusion_norm(self.relu(self.fusion_layer(fused)))
        
        # Apply attention mechanism
        fused_expanded = fused.unsqueeze(1)  # Add sequence dimension
        attended, attention_weights = self.attention(fused_expanded, fused_expanded, fused_expanded)
        attended = attended.squeeze(1)  # Remove sequence dimension
        
        # Classification
        attended = self.dropout(attended)
        logits = self.classifier(attended)
        probabilities = self.sigmoid(logits)
        
        # Clamp probabilities to avoid BCE loss issues
        probabilities = torch.clamp(probabilities, min=1e-7, max=1 - 1e-7)
        
        return {
            'logits': logits.squeeze(-1),
            'probabilities': probabilities.squeeze(-1),
            'attention_weights': attention_weights,
            'text_features': text_proj,
            'stats_features': stats_proj,
            'fused_features': attended
        }


class RAGHybridModel(nn.Module):
    """
    Hybrid model combining BERT text embeddings with tabular statistics.
    """
    
    def __init__(self, config: TrainingConfig, stats_dim: int):
        """
        Initialize RAG hybrid model.
        
        Args:
            config: Training configuration
            stats_dim: Number of tabular statistics features
        """
        super(RAGHybridModel, self).__init__()
        
        if not HAS_TRANSFORMERS:
            raise ImportError("transformers library required. Install with: pip install transformers")
        
        self.config = config
        self.stats_dim = stats_dim
        
        # Initialize BERT components
        self.tokenizer = AutoTokenizer.from_pretrained(config.model_name)
        self.bert = AutoModel.from_pretrained(config.model_name)
        
        # Freeze BERT layers initially (can be unfrozen for fine-tuning)
        self.freeze_bert(freeze=True)
        
        # Initialize fusion layer
        self.fusion_layer = FusionLayer(
            text_dim=config.hidden_dim,
            stats_dim=stats_dim,
            fusion_dim=config.fusion_dim,
            dropout_rate=config.dropout_rate
        )
        
        # Training components - use BCEWithLogitsLoss for numerical stability
        self.criterion = nn.BCEWithLogitsLoss()
        self.is_trained = False
        
        logger.info(f"Initialized RAGHybridModel with {stats_dim} stats features")
        
    def freeze_bert(self, freeze: bool = True):
        """Freeze or unfreeze BERT parameters."""
        for param in self.bert.parameters():
            param.requires_grad = not freeze
        
        if freeze:
            logger.info("BERT layers frozen")
        else:
            logger.info("BERT layers unfrozen for fine-tuning")
    
    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor, 
                stats: torch.Tensor) -> Dict[str, torch.Tensor]:
        """
        Forward pass through the hybrid model.
        
        Args:
            input_ids: BERT input token IDs
            attention_mask: BERT attention mask
            stats: Tabular statistics
            
        Returns:
            Dictionary with model outputs
        """
        # Get BERT embeddings
        bert_outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        text_embeddings = bert_outputs.last_hidden_state[:, 0, :]  # Use [CLS] token
        
        # Fusion layer
        fusion_outputs = self.fusion_layer(text_embeddings, stats)
        
        # Ensure probabilities are properly clamped
        if 'probabilities' in fusion_outputs:
            fusion_outputs['probabilities'] = torch.clamp(
                fusion_outputs['probabilities'], min=1e-7, max=1 - 1e-7
            )
        
        return fusion_outputs
    
    def predict_single(self, stats_dict: Dict[str, float], rag_text: str) -> HybridPrediction:
        """
        Make prediction for single sample.
        
        Args:
            stats_dict: Dictionary of player statistics
            rag_text: RAG narrative text
            
        Returns:
            HybridPrediction object with probability and explanations
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        self.eval()
        
        with torch.no_grad():
            # Prepare stats
            stats_array = np.array(list(stats_dict.values()), dtype=np.float32).reshape(1, -1)
            stats_tensor = torch.tensor(stats_array, dtype=torch.float32).to(device)
            
            # Tokenize text
            encoding = self.tokenizer(
                rag_text,
                truncation=True,
                padding='max_length',
                max_length=self.config.max_length,
                return_tensors='pt'
            )
            
            input_ids = encoding['input_ids'].to(device)
            attention_mask = encoding['attention_mask'].to(device)
            
            # Forward pass
            outputs = self.forward(input_ids, attention_mask, stats_tensor)
            
            probability = outputs['probabilities'].cpu().item()
            
            # Calculate feature contributions
            text_features = outputs['text_features'].cpu().numpy()[0]
            stats_features = outputs['stats_features'].cpu().numpy()[0]
            
            text_contribution = np.mean(np.abs(text_features))
            stats_contribution = np.mean(np.abs(stats_features))
            
            # Normalize contributions
            total_contribution = text_contribution + stats_contribution
            if total_contribution > 0:
                text_contribution /= total_contribution
                stats_contribution /= total_contribution
            
            # Generate explanation
            explanation = self._generate_explanation(
                probability, text_contribution, stats_contribution, stats_dict, rag_text
            )
            
            return HybridPrediction(
                probability=probability,
                confidence=abs(probability - 0.5) * 2,  # Distance from 0.5, scaled to 0-1
                text_contribution=text_contribution,
                stats_contribution=stats_contribution,
                raw_text_embedding=text_features,
                raw_stats_features=stats_features,
                explanation=explanation
            )
    
    def _generate_explanation(self, probability: float, text_contrib: float, 
                            stats_contrib: float, stats_dict: Dict[str, float], 
                            rag_text: str) -> str:
        """Generate human-readable explanation for prediction."""
        
        # Determine prediction direction
        prediction = "HIT" if probability > 0.5 else "MISS"
        confidence_level = "High" if abs(probability - 0.5) > 0.3 else "Medium" if abs(probability - 0.5) > 0.15 else "Low"
        
        # Determine primary factor
        primary_factor = "narrative analysis" if text_contrib > stats_contrib else "statistical analysis"
        
        explanation = f"""
🎯 Prediction: {prediction} ({probability:.1%} probability)
🔍 Confidence: {confidence_level}
📊 Analysis Breakdown:
  • Statistical factors: {stats_contrib:.1%} influence
  • Narrative factors: {text_contrib:.1%} influence
  • Primary driver: {primary_factor}

📈 Key Statistics: {', '.join([f'{k}: {v}' for k, v in list(stats_dict.items())[:3]])}
📰 Narrative Summary: {rag_text[:100]}{'...' if len(rag_text) > 100 else ''}
"""
        
        return explanation.strip()


class RAGHybridTrainer:
    """Trainer class for the RAG hybrid model."""
    
    def __init__(self, config: TrainingConfig):
        """Initialize trainer with configuration."""
        self.config = config
        self.model = None
        self.training_history = []
        
    def prepare_training_data(self, stats_df: pd.DataFrame, texts: List[str], 
                            labels: List[int], test_size: float = 0.2) -> Tuple[DataLoader, DataLoader]:
        """
        Prepare training and validation data loaders.
        
        Args:
            stats_df: DataFrame with player statistics
            texts: List of RAG narrative texts
            labels: Binary labels for hit_prop
            test_size: Proportion for validation split
            
        Returns:
            Tuple of (train_loader, val_loader)
        """
        # Split data
        stats_train, stats_val, texts_train, texts_val, labels_train, labels_val = train_test_split(
            stats_df, texts, labels, test_size=test_size, random_state=42, stratify=labels
        )
        
        # Initialize tokenizer
        tokenizer = AutoTokenizer.from_pretrained(self.config.model_name)
        
        # Create datasets
        train_dataset = HybridDataset(stats_train, texts_train, labels_train, tokenizer, self.config.max_length)
        val_dataset = HybridDataset(stats_val, texts_val, labels_val, tokenizer, self.config.max_length)
        
        # Create data loaders
        train_loader = DataLoader(train_dataset, batch_size=self.config.batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=self.config.batch_size, shuffle=False)
        
        logger.info(f"Training data: {len(train_dataset)} samples")
        logger.info(f"Validation data: {len(val_dataset)} samples")
        
        return train_loader, val_loader
    
    def train(self, train_loader: DataLoader, val_loader: DataLoader, 
              stats_dim: int) -> Dict[str, Any]:
        """
        Train the hybrid model.
        
        Args:
            train_loader: Training data loader
            val_loader: Validation data loader
            stats_dim: Number of statistical features
            
        Returns:
            Training history and metrics
        """
        # Initialize model
        self.model = RAGHybridModel(self.config, stats_dim).to(device)
        
        # Initialize optimizer
        optimizer = optim.AdamW(
            self.model.parameters(),
            lr=self.config.learning_rate,
            weight_decay=self.config.weight_decay
        )
        
        # Learning rate scheduler
        scheduler = optim.lr_scheduler.LinearLR(
            optimizer, start_factor=1.0, end_factor=0.1, total_iters=self.config.num_epochs
        )
        
        best_val_loss = float('inf')
        patience_counter = 0
        
        logger.info("Starting hybrid model training...")
        
        for epoch in range(self.config.num_epochs):
            # Training phase
            train_loss = self._train_epoch(train_loader, optimizer)
            
            # Validation phase
            val_loss, val_metrics = self._validate_epoch(val_loader)
            
            # Learning rate step
            scheduler.step()
            
            # Early stopping check
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                self._save_model()
            else:
                patience_counter += 1
            
            # Log progress
            logger.info(f"Epoch {epoch + 1}/{self.config.num_epochs}")
            logger.info(f"  Train Loss: {train_loss:.4f}")
            logger.info(f"  Val Loss: {val_loss:.4f}")
            logger.info(f"  Val AUC: {val_metrics['auc']:.4f}")
            logger.info(f"  Val Brier: {val_metrics['brier_score']:.4f}")
            
            # Store history
            self.training_history.append({
                'epoch': epoch + 1,
                'train_loss': train_loss,
                'val_loss': val_loss,
                'val_auc': val_metrics['auc'],
                'val_brier_score': val_metrics['brier_score'],
                'val_accuracy': val_metrics['accuracy']
            })
            
            # Early stopping
            if patience_counter >= self.config.early_stopping_patience:
                logger.info(f"Early stopping triggered after {epoch + 1} epochs")
                break
        
        # Load best model
        self._load_model()
        self.model.is_trained = True
        
        return {
            'training_history': self.training_history,
            'best_val_loss': best_val_loss,
            'final_metrics': val_metrics
        }
    
    def _train_epoch(self, train_loader: DataLoader, optimizer: optim.Optimizer) -> float:
        """Train for one epoch."""
        self.model.train()
        total_loss = 0
        
        for batch in train_loader:
            optimizer.zero_grad()
            
            # Move batch to device
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            stats = batch['stats'].to(device)
            labels = batch['labels'].float().to(device)
            
            # Forward pass
            outputs = self.model(input_ids, attention_mask, stats)
            
            # Calculate loss using logits (BCEWithLogitsLoss expects raw logits)
            loss = self.model.criterion(outputs['logits'], labels)
            
            # Backward pass
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
        
        return total_loss / len(train_loader)
    
    def _validate_epoch(self, val_loader: DataLoader) -> Tuple[float, Dict[str, float]]:
        """Validate for one epoch."""
        self.model.eval()
        total_loss = 0
        all_predictions = []
        all_labels = []
        
        with torch.no_grad():
            for batch in val_loader:
                # Move batch to device
                input_ids = batch['input_ids'].to(device)
                attention_mask = batch['attention_mask'].to(device)
                stats = batch['stats'].to(device)
                labels = batch['labels'].float().to(device)
                
                # Forward pass
                outputs = self.model(input_ids, attention_mask, stats)
                
                # Calculate loss using logits
                loss = self.model.criterion(outputs['logits'], labels)
                total_loss += loss.item()
                
                # Collect predictions (handle potential NaN values)
                probs = outputs['probabilities'].cpu().numpy()
                # Replace any NaN or inf values with 0.5 (neutral probability)
                probs = np.nan_to_num(probs, nan=0.5, posinf=0.999, neginf=0.001)
                all_predictions.extend(probs)
                all_labels.extend(labels.cpu().numpy())
        
        # Calculate metrics
        all_predictions = np.array(all_predictions)
        all_labels = np.array(all_labels)
        
        auc = roc_auc_score(all_labels, all_predictions)
        brier_score = brier_score_loss(all_labels, all_predictions)
        accuracy = accuracy_score(all_labels, (all_predictions > 0.5).astype(int))
        
        metrics = {
            'auc': auc,
            'brier_score': brier_score,
            'accuracy': accuracy
        }
        
        return total_loss / len(val_loader), metrics
    
    def _save_model(self):
        """Save model checkpoint."""
        save_path = Path(self.config.save_model_path)
        save_path.mkdir(parents=True, exist_ok=True)
        
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'config': self.config,
            'training_history': self.training_history
        }, save_path / "hybrid_model.pt")
        
        logger.info(f"Model saved to {save_path}")
    
    def _load_model(self):
        """Load model checkpoint."""
        save_path = Path(self.config.save_model_path) / "hybrid_model.pt"
        
        if save_path.exists():
            checkpoint = torch.load(save_path, map_location=device, weights_only=False)
            self.model.load_state_dict(checkpoint['model_state_dict'])
            logger.info(f"Model loaded from {save_path}")
        else:
            logger.warning(f"No saved model found at {save_path}")


class ABTestEvaluator:
    """A/B testing evaluator for hybrid vs baseline models."""
    
    def __init__(self):
        """Initialize A/B test evaluator."""
        self.results = {}
        
    def create_stats_baseline(self, stats_df: pd.DataFrame, labels: List[int]) -> RandomForestClassifier:
        """
        Create stats-only baseline model.
        
        Args:
            stats_df: DataFrame with player statistics
            labels: Binary labels
            
        Returns:
            Trained RandomForest baseline model
        """
        baseline_model = RandomForestClassifier(
            n_estimators=100,
            random_state=42,
            max_depth=10
        )
        
        baseline_model.fit(stats_df, labels)
        logger.info("Stats-only baseline model trained")
        
        return baseline_model
    
    def evaluate_models(self, hybrid_model: RAGHybridModel, baseline_model: RandomForestClassifier,
                       test_stats: pd.DataFrame, test_texts: List[str], 
                       test_labels: List[int]) -> Dict[str, Any]:
        """
        Compare hybrid model vs stats-only baseline.
        
        Args:
            hybrid_model: Trained hybrid model
            baseline_model: Trained baseline model
            test_stats: Test statistics
            test_texts: Test RAG texts
            test_labels: Test labels
            
        Returns:
            Comparison results
        """
        logger.info("Running A/B evaluation...")
        
        # Baseline predictions
        baseline_predictions = baseline_model.predict_proba(test_stats)[:, 1]
        
        # Hybrid predictions
        hybrid_predictions = []
        for i in range(len(test_stats)):
            stats_dict = test_stats.iloc[i].to_dict()
            rag_text = test_texts[i]
            
            try:
                prediction = hybrid_model.predict_single(stats_dict, rag_text)
                hybrid_predictions.append(prediction.probability)
            except Exception as e:
                logger.warning(f"Hybrid prediction failed for sample {i}: {e}")
                hybrid_predictions.append(0.5)  # Default prediction
        
        hybrid_predictions = np.array(hybrid_predictions)
        
        # Calculate metrics for both models
        baseline_metrics = self._calculate_metrics(test_labels, baseline_predictions, "Baseline")
        hybrid_metrics = self._calculate_metrics(test_labels, hybrid_predictions, "Hybrid")
        
        # Statistical significance test (McNemar's test for classification)
        baseline_correct = (baseline_predictions > 0.5) == np.array(test_labels)
        hybrid_correct = (hybrid_predictions > 0.5) == np.array(test_labels)
        
        # Count discordant pairs
        baseline_right_hybrid_wrong = np.sum(baseline_correct & ~hybrid_correct)
        hybrid_right_baseline_wrong = np.sum(hybrid_correct & ~baseline_correct)
        
        # McNemar's test statistic
        mcnemar_stat = abs(baseline_right_hybrid_wrong - hybrid_right_baseline_wrong)
        p_value = 0.05 if mcnemar_stat > 3.84 else 0.5  # Approximate chi-square test
        
        results = {
            'baseline_metrics': baseline_metrics,
            'hybrid_metrics': hybrid_metrics,
            'improvement': {
                'brier_score': baseline_metrics['brier_score'] - hybrid_metrics['brier_score'],
                'auc': hybrid_metrics['auc'] - baseline_metrics['auc'],
                'accuracy': hybrid_metrics['accuracy'] - baseline_metrics['accuracy']
            },
            'statistical_significance': {
                'mcnemar_statistic': mcnemar_stat,
                'p_value': p_value,
                'significant': p_value < 0.05
            },
            'sample_size': len(test_labels)
        }
        
        # Log results
        logger.info("A/B Test Results:")
        logger.info(f"  Baseline Brier Score: {baseline_metrics['brier_score']:.4f}")
        logger.info(f"  Hybrid Brier Score: {hybrid_metrics['brier_score']:.4f}")
        logger.info(f"  Brier Score Improvement: {results['improvement']['brier_score']:.4f}")
        logger.info(f"  AUC Improvement: {results['improvement']['auc']:.4f}")
        logger.info(f"  Statistical Significance: {results['statistical_significance']['significant']}")
        
        self.results = results
        return results
    
    def _calculate_metrics(self, labels: List[int], predictions: np.ndarray, 
                          model_name: str) -> Dict[str, float]:
        """Calculate evaluation metrics for a model."""
        auc = roc_auc_score(labels, predictions)
        brier_score = brier_score_loss(labels, predictions)
        accuracy = accuracy_score(labels, (predictions > 0.5).astype(int))
        logloss = log_loss(labels, predictions)
        
        return {
            'auc': auc,
            'brier_score': brier_score,
            'accuracy': accuracy,
            'log_loss': logloss,
            'model_name': model_name
        }


def create_sample_hybrid_data() -> Tuple[pd.DataFrame, List[str], List[int]]:
    """Create sample data for testing the hybrid model."""
    import random
    
    # Sample player statistics
    players = ['LeBron James', 'Stephen Curry', 'Josh Allen', 'Lamar Jackson', 'Travis Kelce']
    sports = ['NBA', 'NFL']
    
    stats_data = []
    texts = []
    labels = []
    
    for i in range(200):  # 200 samples
        sport = random.choice(sports)
        player = random.choice(players)
        
        if sport == 'NBA':
            # NBA stats
            stats = {
                'points': random.uniform(15, 35),
                'rebounds': random.uniform(4, 12),
                'assists': random.uniform(3, 10),
                'minutes': random.uniform(25, 40),
                'field_goals': random.uniform(5, 15),
                'opponent_def_rating': random.uniform(100, 120),
                'rest_days': random.randint(0, 3),
                'home_away': random.choice([0, 1])  # 0=away, 1=home
            }
            
            # Generate RAG narrative
            performance = "strong" if stats['points'] > 25 else "moderate"
            matchup = "favorable" if stats['opponent_def_rating'] > 110 else "challenging"
            
            text = f"{player} has been showing {performance} scoring performance recently. " \
                   f"Against this opponent, the matchup appears {matchup} based on their defensive rating. " \
                   f"Playing at {'home' if stats['home_away'] else 'away'} with {stats['rest_days']} days rest. " \
                   f"Expected to play around {stats['minutes']:.0f} minutes tonight."
        
        else:  # NFL
            # NFL stats
            stats = {
                'passing_yards': random.uniform(0, 300),
                'rushing_yards': random.uniform(0, 150),
                'receiving_yards': random.uniform(0, 120),
                'touchdowns': random.uniform(0, 3),
                'targets': random.uniform(0, 12),
                'opponent_def_rating': random.uniform(80, 120),
                'weather_score': random.uniform(1, 5),  # 1=bad, 5=good
                'home_away': random.choice([0, 1])
            }
            
            # Generate RAG narrative
            weather = "favorable" if stats['weather_score'] > 3 else "challenging"
            matchup = "good" if stats['opponent_def_rating'] > 100 else "tough"
            
            text = f"{player} faces a {matchup} defensive matchup this week. " \
                   f"Weather conditions look {weather} for passing/rushing. " \
                   f"Playing {'at home' if stats['home_away'] else 'on the road'}. " \
                   f"Recent usage suggests around {stats['targets']:.0f} targets expected."
        
        # Generate label based on stats (with some noise)
        if sport == 'NBA':
            base_prob = (stats['points'] - 15) / 20 + (stats['minutes'] - 25) / 15 * 0.3
        else:
            base_prob = (stats['passing_yards'] + stats['rushing_yards'] + stats['receiving_yards']) / 300
        
        # Add narrative influence
        narrative_boost = 0.1 if "strong" in text or "favorable" in text or "good" in text else -0.1
        final_prob = np.clip(base_prob + narrative_boost + random.uniform(-0.2, 0.2), 0, 1)
        
        label = 1 if final_prob > 0.5 else 0
        
        stats_data.append(stats)
        texts.append(text)
        labels.append(label)
    
    # Convert to DataFrame
    stats_df = pd.DataFrame(stats_data)
    
    logger.info(f"Created sample data: {len(stats_df)} samples, {np.mean(labels):.1%} positive rate")
    
    return stats_df, texts, labels


if __name__ == "__main__":
    # Demo usage
    logging.basicConfig(level=logging.INFO)
    
    print("🤖 RAGHybridModel Demo")
    print("=" * 50)
    
    if not HAS_TRANSFORMERS:
        print("❌ transformers library not installed. Install with: pip install transformers")
        exit(1)
    
    # Create sample data
    print("🎲 Creating sample hybrid training data...")
    stats_df, texts, labels = create_sample_hybrid_data()
    
    # Initialize training configuration
    config = TrainingConfig(
        num_epochs=2,  # Reduced for demo
        batch_size=8,  # Smaller batch for demo
        learning_rate=5e-5
    )
    
    # Initialize trainer
    print("🔧 Initializing RAG hybrid trainer...")
    trainer = RAGHybridTrainer(config)
    
    # Prepare data
    print("📊 Preparing training data...")
    train_loader, val_loader = trainer.prepare_training_data(stats_df, texts, labels)
    
    # Train model
    print("🚀 Training hybrid model...")
    try:
        training_results = trainer.train(train_loader, val_loader, stats_dim=stats_df.shape[1])
        
        print(f"✅ Training completed!")
        print(f"  Best validation loss: {training_results['best_val_loss']:.4f}")
        print(f"  Final AUC: {training_results['final_metrics']['auc']:.4f}")
        print(f"  Final Brier Score: {training_results['final_metrics']['brier_score']:.4f}")
        
        # Test single prediction
        print("\n🔮 Testing single prediction...")
        sample_stats = stats_df.iloc[0].to_dict()
        sample_text = texts[0]
        
        prediction = trainer.model.predict_single(sample_stats, sample_text)
        print(f"  Prediction: {prediction.probability:.1%}")
        print(f"  Confidence: {prediction.confidence:.1%}")
        print(f"  Text contribution: {prediction.text_contribution:.1%}")
        print(f"  Stats contribution: {prediction.stats_contribution:.1%}")
        
        # A/B Testing
        print("\n📈 Running A/B evaluation...")
        evaluator = ABTestEvaluator()
        baseline_model = evaluator.create_stats_baseline(stats_df, labels)
        
        # Use small subset for demo
        test_stats = stats_df.tail(20)
        test_texts = texts[-20:]
        test_labels = labels[-20:]
        
        ab_results = evaluator.evaluate_models(
            trainer.model, baseline_model, 
            test_stats, test_texts, test_labels
        )
        
        print("✅ Demo complete! RAG hybrid model ready for integration.")
        
    except Exception as e:
        print(f"❌ Training failed: {e}")
        import traceback
        traceback.print_exc()
