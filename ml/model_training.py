#!/usr/bin/env python3
"""
ML Model Training - JIRA-ML-001

Trains XGBoost models for NBA and NFL parlay leg prediction.
Uses stratified k-fold cross-validation and saves models for production use.
"""

import logging
import numpy as np
import pandas as pd
import json
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path
import pickle
from datetime import datetime

# ML imports
import xgboost as xgb
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, 
    roc_auc_score, classification_report, confusion_matrix
)
import matplotlib.pyplot as plt
import seaborn as sns

from ml.feature_engineering import MultiSportFeatureEngineer

logger = logging.getLogger(__name__)


class ParlayLegPredictor:
    """XGBoost model for predicting parlay leg success."""
    
    def __init__(self, sport: str, model_params: Optional[Dict] = None):
        self.sport = sport.lower()
        self.model = None
        self.is_trained = False
        self.feature_importance = None
        self.training_metrics = {}
        
        # Default XGBoost parameters optimized for parlay prediction
        self.default_params = {
            'objective': 'binary:logistic',
            'eval_metric': 'logloss',
            'max_depth': 6,
            'learning_rate': 0.1,
            'n_estimators': 200,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'random_state': 42,
            'n_jobs': -1,
            'scale_pos_weight': 1.0  # Adjust based on class imbalance
        }
        
        self.params = model_params or self.default_params
        
        # Output directories
        self.model_dir = Path(f"models/parlay_predictor_{sport}")
        self.model_dir.mkdir(parents=True, exist_ok=True)
    
    def adjust_for_class_imbalance(self, y: np.ndarray):
        """Adjust model parameters for class imbalance."""
        pos_count = np.sum(y)
        neg_count = len(y) - pos_count
        
        if pos_count > 0:
            scale_pos_weight = neg_count / pos_count
            self.params['scale_pos_weight'] = scale_pos_weight
            logger.info(f"Adjusted scale_pos_weight to {scale_pos_weight:.2f} for {self.sport}")
    
    def train(self, X: np.ndarray, y: np.ndarray, validation_split: float = 0.2) -> Dict[str, Any]:
        """Train the XGBoost model with validation."""
        logger.info(f"Training {self.sport} parlay predictor...")
        
        # Adjust for class imbalance
        self.adjust_for_class_imbalance(y)
        
        # Split data
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=validation_split, random_state=42, stratify=y
        )
        
        # Initialize model
        self.model = xgb.XGBClassifier(**self.params)
        
        # Train with early stopping
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_train, y_train), (X_val, y_val)],
            eval_metric='logloss',
            early_stopping_rounds=20,
            verbose=False
        )
        
        # Predictions
        y_train_pred = self.model.predict(X_train)
        y_train_proba = self.model.predict_proba(X_train)[:, 1]
        y_val_pred = self.model.predict(X_val)
        y_val_proba = self.model.predict_proba(X_val)[:, 1]
        
        # Calculate metrics
        self.training_metrics = {
            'train': {
                'accuracy': accuracy_score(y_train, y_train_pred),
                'precision': precision_score(y_train, y_train_pred),
                'recall': recall_score(y_train, y_train_pred),
                'f1': f1_score(y_train, y_train_pred),
                'auc': roc_auc_score(y_train, y_train_proba)
            },
            'validation': {
                'accuracy': accuracy_score(y_val, y_val_pred),
                'precision': precision_score(y_val, y_val_pred),
                'recall': recall_score(y_val, y_val_pred),
                'f1': f1_score(y_val, y_val_pred),
                'auc': roc_auc_score(y_val, y_val_proba)
            }
        }
        
        # Feature importance
        self.feature_importance = self.model.feature_importances_
        
        self.is_trained = True
        logger.info(f"Training complete for {self.sport}. Validation accuracy: {self.training_metrics['validation']['accuracy']:.3f}")
        
        return self.training_metrics
    
    def cross_validate(self, X: np.ndarray, y: np.ndarray, cv_folds: int = 5) -> Dict[str, Any]:
        """Perform stratified k-fold cross-validation."""
        logger.info(f"Performing {cv_folds}-fold cross-validation for {self.sport}...")
        
        if not self.is_trained:
            self.adjust_for_class_imbalance(y)
            self.model = xgb.XGBClassifier(**self.params)
        
        # Stratified k-fold
        skf = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)
        
        # Cross-validation metrics
        cv_scores = {
            'accuracy': cross_val_score(self.model, X, y, cv=skf, scoring='accuracy'),
            'precision': cross_val_score(self.model, X, y, cv=skf, scoring='precision'),
            'recall': cross_val_score(self.model, X, y, cv=skf, scoring='recall'),
            'f1': cross_val_score(self.model, X, y, cv=skf, scoring='f1'),
            'roc_auc': cross_val_score(self.model, X, y, cv=skf, scoring='roc_auc')
        }
        
        # Calculate mean and std
        cv_results = {}
        for metric, scores in cv_scores.items():
            cv_results[metric] = {
                'mean': scores.mean(),
                'std': scores.std(),
                'scores': scores.tolist()
            }
        
        logger.info(f"CV Results for {self.sport}: Accuracy {cv_results['accuracy']['mean']:.3f} ± {cv_results['accuracy']['std']:.3f}")
        
        return cv_results
    
    def predict_leg_hit_probability(self, X: np.ndarray) -> np.ndarray:
        """Predict hit probability for parlay legs."""
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        return self.model.predict_proba(X)[:, 1]
    
    def predict_with_confidence(self, X: np.ndarray, confidence_threshold: float = 0.6) -> Tuple[np.ndarray, np.ndarray]:
        """Predict with confidence filtering."""
        probabilities = self.predict_leg_hit_probability(X)
        
        # Binary predictions
        predictions = (probabilities > 0.5).astype(int)
        
        # Confidence mask (predictions with high or low confidence)
        high_confidence = (probabilities >= confidence_threshold) | (probabilities <= (1 - confidence_threshold))
        
        return predictions, high_confidence
    
    def save_model(self) -> str:
        """Save the trained model and metadata."""
        if not self.is_trained:
            raise ValueError("Model must be trained before saving")
        
        # Save model
        model_path = self.model_dir / f"{self.sport}_parlay_predictor.pkl"
        with open(model_path, 'wb') as f:
            pickle.dump(self.model, f)
        
        # Save metadata
        metadata = {
            'sport': self.sport,
            'model_type': 'XGBClassifier',
            'parameters': self.params,
            'training_metrics': self.training_metrics,
            'feature_importance': self.feature_importance.tolist() if self.feature_importance is not None else None,
            'trained_at': datetime.now().isoformat(),
            'model_version': '1.0'
        }
        
        metadata_path = self.model_dir / f"{self.sport}_model_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Saved {self.sport} model to {model_path}")
        return str(model_path)
    
    @classmethod
    def load_model(cls, sport: str) -> 'ParlayLegPredictor':
        """Load a trained model."""
        model_dir = Path(f"models/parlay_predictor_{sport}")
        model_path = model_dir / f"{sport}_parlay_predictor.pkl"
        metadata_path = model_dir / f"{sport}_model_metadata.json"
        
        if not model_path.exists():
            raise FileNotFoundError(f"No saved model found for {sport}")
        
        # Load model
        with open(model_path, 'rb') as f:
            model = pickle.load(f)
        
        # Load metadata
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        # Create predictor instance
        predictor = cls(sport, metadata['parameters'])
        predictor.model = model
        predictor.is_trained = True
        predictor.training_metrics = metadata.get('training_metrics', {})
        predictor.feature_importance = np.array(metadata['feature_importance']) if metadata.get('feature_importance') else None
        
        logger.info(f"Loaded {sport} model from {model_path}")
        return predictor
    
    def plot_feature_importance(self, feature_names: List[str], top_n: int = 20):
        """Plot feature importance."""
        if self.feature_importance is None:
            logger.warning("No feature importance data available")
            return
        
        # Get top features
        importance_df = pd.DataFrame({
            'feature': feature_names,
            'importance': self.feature_importance
        }).sort_values('importance', ascending=False).head(top_n)
        
        # Plot
        plt.figure(figsize=(10, 8))
        sns.barplot(data=importance_df, x='importance', y='feature')
        plt.title(f'Top {top_n} Feature Importance - {self.sport.upper()} Parlay Predictor')
        plt.xlabel('Importance Score')
        plt.tight_layout()
        
        # Save plot
        plot_path = self.model_dir / f"{self.sport}_feature_importance.png"
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Saved feature importance plot to {plot_path}")


class MultiSportModelTrainer:
    """Manages training for multiple sport models."""
    
    def __init__(self):
        self.predictors = {}
        self.feature_engineer = MultiSportFeatureEngineer()
    
    def train_sport_model(self, sport: str, csv_path: str, cv_folds: int = 5) -> Dict[str, Any]:
        """Train a model for a specific sport."""
        logger.info(f"Training {sport} model...")
        
        # Prepare data
        X, y, feature_cols = self.feature_engineer.prepare_sport_data(sport, csv_path)
        
        # Initialize predictor
        predictor = ParlayLegPredictor(sport)
        
        # Cross-validation
        cv_results = predictor.cross_validate(X, y, cv_folds)
        
        # Full training
        training_metrics = predictor.train(X, y)
        
        # Save model
        model_path = predictor.save_model()
        
        # Plot feature importance
        predictor.plot_feature_importance(feature_cols)
        
        # Store predictor
        self.predictors[sport] = predictor
        
        results = {
            'sport': sport,
            'data_shape': X.shape,
            'hit_rate': y.mean(),
            'cv_results': cv_results,
            'training_metrics': training_metrics,
            'model_path': model_path
        }
        
        return results
    
    def train_all_models(self) -> Dict[str, Any]:
        """Train models for all sports."""
        results = {}
        
        for sport in ["nba", "nfl"]:
            csv_path = f"data/ml_training/{sport}_parlay_training_data.csv"
            
            try:
                results[sport] = self.train_sport_model(sport, csv_path)
            except FileNotFoundError:
                logger.error(f"Dataset not found for {sport}: {csv_path}")
                results[sport] = {'error': 'Dataset not found'}
        
        return results
    
    def evaluate_models(self) -> Dict[str, Any]:
        """Evaluate all trained models."""
        evaluation = {}
        
        for sport, predictor in self.predictors.items():
            if predictor.is_trained:
                metrics = predictor.training_metrics
                evaluation[sport] = {
                    'validation_accuracy': metrics['validation']['accuracy'],
                    'validation_auc': metrics['validation']['auc'],
                    'validation_f1': metrics['validation']['f1'],
                    'model_ready': True
                }
            else:
                evaluation[sport] = {'model_ready': False}
        
        return evaluation


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("🤖 ML MODEL TRAINING - JIRA-ML-001")
    print("=" * 60)
    print()
    
    # Initialize trainer
    trainer = MultiSportModelTrainer()
    
    # Train all models
    print("🏋️ Training XGBoost models for both sports...")
    results = trainer.train_all_models()
    
    print("\n📊 TRAINING RESULTS:")
    print("=" * 40)
    
    for sport, result in results.items():
        if 'error' in result:
            print(f"❌ {sport.upper()}: {result['error']}")
        else:
            print(f"✅ {sport.upper()}:")
            print(f"   Dataset: {result['data_shape'][0]:,} examples, {result['data_shape'][1]:,} features")
            print(f"   Hit Rate: {result['hit_rate']:.1%}")
            print(f"   CV Accuracy: {result['cv_results']['accuracy']['mean']:.3f} ± {result['cv_results']['accuracy']['std']:.3f}")
            print(f"   Validation Accuracy: {result['training_metrics']['validation']['accuracy']:.3f}")
            print(f"   Validation AUC: {result['training_metrics']['validation']['auc']:.3f}")
            print(f"   Model: {result['model_path']}")
    
    # Evaluate models
    print("\n🎯 MODEL EVALUATION:")
    print("=" * 40)
    
    evaluation = trainer.evaluate_models()
    
    for sport, eval_data in evaluation.items():
        if eval_data.get('model_ready'):
            print(f"✅ {sport.upper()} Model Ready:")
            print(f"   Accuracy: {eval_data['validation_accuracy']:.1%}")
            print(f"   AUC: {eval_data['validation_auc']:.3f}")
            print(f"   F1 Score: {eval_data['validation_f1']:.3f}")
        else:
            print(f"❌ {sport.upper()} Model Not Ready")
    
    print("\n🏆 ML MODELS TRAINING COMPLETE!")
    print("   Next: Integration with ParlayBuilder")
