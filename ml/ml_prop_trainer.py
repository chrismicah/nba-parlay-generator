#!/usr/bin/env python3
"""
Historical Prop Trainer - ML-PROP-001

XGBoost-based trainer for NBA and NFL player prop predictions.
Handles separate datasets for each sport with sport-specific features.
Integrates with ParlayBuilder for EV-based leg ranking.
"""

import logging
import numpy as np
import pandas as pd
import pickle
from typing import Dict, List, Any, Tuple, Optional, Union
from pathlib import Path
from datetime import datetime

# ML imports
import xgboost as xgb
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.preprocessing import StandardScaler, LabelEncoder, OneHotEncoder
from sklearn.metrics import roc_auc_score, log_loss, classification_report, confusion_matrix
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

logger = logging.getLogger(__name__)


class HistoricalPropTrainer:
    """
    XGBoost-based trainer for NBA and NFL player prop predictions.
    
    Handles separate datasets for each sport with sport-specific feature engineering.
    Predicts 'hit_prop' binary labels (1 if over/under hit, 0 if missed).
    """
    
    def __init__(self, sport: str, model_params: Optional[Dict] = None):
        """
        Initialize trainer for specific sport.
        
        Args:
            sport: "nba" or "nfl"
            model_params: Optional XGBoost parameters
        """
        if sport.lower() not in ['nba', 'nfl']:
            raise ValueError("Sport must be 'nba' or 'nfl'")
            
        self.sport = sport.lower()
        self.model = None
        self.preprocessor = None
        self.feature_names = []
        self.is_trained = False
        
        # Sport-specific configurations
        self._setup_sport_config()
        
        # XGBoost parameters optimized for prop prediction
        self.default_params = {
            'objective': 'binary:logistic',
            'eval_metric': 'logloss',
            'max_depth': 6,
            'learning_rate': 0.1,
            'n_estimators': 300,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'random_state': 42,
            'n_jobs': -1,
            'scale_pos_weight': 1.0
        }
        
        self.params = model_params or self.default_params
        
        # Model storage
        self.model_dir = Path(f"models/prop_predictor_{sport}")
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized HistoricalPropTrainer for {sport.upper()}")
    
    def _setup_sport_config(self):
        """Configure sport-specific features and expected columns."""
        if self.sport == 'nba':
            self.expected_columns = [
                'player_id', 'game_date', 'points_scored', 'rebounds', 'assists',
                'opponent_def_rating', 'minutes_played', 'field_goal_attempts',
                'three_point_attempts', 'free_throw_attempts', 'turnovers',
                'home_away', 'days_rest', 'season_avg_points', 'last_5_avg_points',
                'opponent_points_allowed', 'pace', 'usage_rate', 'hit_prop'
            ]
            
            self.categorical_features = ['home_away']
            self.numerical_features = [
                'points_scored', 'rebounds', 'assists', 'opponent_def_rating',
                'minutes_played', 'field_goal_attempts', 'three_point_attempts',
                'free_throw_attempts', 'turnovers', 'days_rest', 'season_avg_points',
                'last_5_avg_points', 'opponent_points_allowed', 'pace', 'usage_rate'
            ]
            
        else:  # NFL
            self.expected_columns = [
                'player_id', 'game_date', 'passing_yards', 'rushing_yards', 'receiving_yards',
                'passing_touchdowns', 'rushing_touchdowns', 'receptions', 'targets',
                'opponent_def_rating', 'weather_conditions', 'dome_game', 'position',
                'home_away', 'division_game', 'season_avg_yards', 'last_4_avg_yards',
                'opponent_yards_allowed', 'snap_count', 'red_zone_targets', 'hit_prop'
            ]
            
            self.categorical_features = ['weather_conditions', 'position', 'home_away']
            self.numerical_features = [
                'passing_yards', 'rushing_yards', 'receiving_yards', 'passing_touchdowns',
                'rushing_touchdowns', 'receptions', 'targets', 'opponent_def_rating',
                'dome_game', 'division_game', 'season_avg_yards', 'last_4_avg_yards',
                'opponent_yards_allowed', 'snap_count', 'red_zone_targets'
            ]
    
    def load_data(self, csv_path: str) -> pd.DataFrame:
        """
        Load and validate sport-specific CSV data.
        
        Args:
            csv_path: Path to CSV file with historical prop data
            
        Returns:
            Validated DataFrame
        """
        try:
            df = pd.read_csv(csv_path)
            logger.info(f"Loaded {len(df)} rows from {csv_path}")
            
            # Validate required columns
            missing_cols = set(self.expected_columns) - set(df.columns)
            if missing_cols:
                logger.warning(f"Missing expected columns for {self.sport}: {missing_cols}")
            
            # Ensure hit_prop column exists and is binary
            if 'hit_prop' not in df.columns:
                raise ValueError("CSV must contain 'hit_prop' column with binary labels (0/1)")
            
            # Convert hit_prop to binary if needed
            df['hit_prop'] = df['hit_prop'].astype(int)
            
            # Basic data validation
            prop_dist = df['hit_prop'].value_counts()
            logger.info(f"Prop hit distribution - Hit: {prop_dist.get(1, 0)}, Miss: {prop_dist.get(0, 0)}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error loading data from {csv_path}: {e}")
            raise
    
    def preprocess_features(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Preprocess features with sport-specific transformations.
        
        Args:
            df: Raw DataFrame
            
        Returns:
            Tuple of (X_processed, y)
        """
        # Separate features and target
        available_features = [col for col in self.numerical_features + self.categorical_features 
                            if col in df.columns]
        
        X = df[available_features].copy()
        y = df['hit_prop'].values
        
        # Handle missing values separately for numeric and categorical columns
        for col in X.columns:
            if X[col].dtype in ['object', 'category']:
                # Fill categorical columns with mode
                mode_value = X[col].mode().iloc[0] if not X[col].mode().empty else 'Unknown'
                X[col] = X[col].fillna(mode_value)
            else:
                # Fill numeric columns with median
                X[col] = X[col].fillna(X[col].median())
        
        # Create preprocessing pipeline
        numeric_transformer = StandardScaler()
        categorical_transformer = OneHotEncoder(drop='first', sparse_output=False, handle_unknown='ignore')
        
        # Get actual categorical and numerical columns present in data
        categorical_cols = [col for col in self.categorical_features if col in X.columns]
        numerical_cols = [col for col in self.numerical_features if col in X.columns]
        
        self.preprocessor = ColumnTransformer(
            transformers=[
                ('num', numeric_transformer, numerical_cols),
                ('cat', categorical_transformer, categorical_cols)
            ]
        )
        
        # Fit and transform
        X_processed = self.preprocessor.fit_transform(X)
        
        # Store feature names for interpretability
        if categorical_cols:
            cat_feature_names = self.preprocessor.named_transformers_['cat'].get_feature_names_out(categorical_cols)
            self.feature_names = numerical_cols + list(cat_feature_names)
        else:
            self.feature_names = numerical_cols
        
        logger.info(f"Preprocessed {X_processed.shape[1]} features for {len(X)} samples")
        logger.info(f"Feature names: {self.feature_names[:10]}..." if len(self.feature_names) > 10 else f"Feature names: {self.feature_names}")
        
        return X_processed, y
    
    def train(self, csv_path: str, test_size: float = 0.2, cv_folds: int = 5) -> Dict[str, Any]:
        """
        Train XGBoost model with cross-validation.
        
        Args:
            csv_path: Path to training CSV
            test_size: Proportion for test split
            cv_folds: Number of CV folds
            
        Returns:
            Training metrics
        """
        logger.info(f"Training {self.sport.upper()} prop predictor...")
        
        # Load and preprocess data
        df = self.load_data(csv_path)
        X, y = self.preprocess_features(df)
        
        # Adjust for class imbalance
        pos_count = np.sum(y)
        neg_count = len(y) - pos_count
        if pos_count > 0:
            scale_pos_weight = neg_count / pos_count
            self.params['scale_pos_weight'] = scale_pos_weight
            logger.info(f"Adjusted scale_pos_weight to {scale_pos_weight:.2f}")
        
        # Train-test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )
        
        # Initialize and train model
        self.model = xgb.XGBClassifier(**self.params)
        
        # Train model
        self.model.fit(X_train, y_train)
        
        # Predictions
        y_train_proba = self.model.predict_proba(X_train)[:, 1]
        y_test_proba = self.model.predict_proba(X_test)[:, 1]
        y_train_pred = (y_train_proba > 0.5).astype(int)
        y_test_pred = (y_test_proba > 0.5).astype(int)
        
        # Calculate metrics
        train_auc = roc_auc_score(y_train, y_train_proba)
        test_auc = roc_auc_score(y_test, y_test_proba)
        train_logloss = log_loss(y_train, y_train_proba)
        test_logloss = log_loss(y_test, y_test_proba)
        
        # Cross-validation
        cv_scores = self._cross_validate(X, y, cv_folds)
        
        # Training results
        metrics = {
            'sport': self.sport,
            'train_auc': train_auc,
            'test_auc': test_auc,
            'train_logloss': train_logloss,
            'test_logloss': test_logloss,
            'cv_auc_mean': cv_scores['auc_mean'],
            'cv_auc_std': cv_scores['auc_std'],
            'cv_logloss_mean': cv_scores['logloss_mean'],
            'cv_logloss_std': cv_scores['logloss_std'],
            'feature_importance': dict(zip(self.feature_names, self.model.feature_importances_)),
            'training_samples': len(X_train),
            'test_samples': len(X_test),
            'positive_rate': pos_count / len(y)
        }
        
        self.is_trained = True
        
        # Save model
        self._save_model()
        
        logger.info(f"Training complete - Test AUC: {test_auc:.4f}, Test LogLoss: {test_logloss:.4f}")
        
        return metrics
    
    def _cross_validate(self, X: np.ndarray, y: np.ndarray, cv_folds: int) -> Dict[str, float]:
        """Perform cross-validation."""
        skf = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)
        
        auc_scores = []
        logloss_scores = []
        
        for train_idx, val_idx in skf.split(X, y):
            X_fold_train, X_fold_val = X[train_idx], X[val_idx]
            y_fold_train, y_fold_val = y[train_idx], y[val_idx]
            
            # Train fold model
            fold_model = xgb.XGBClassifier(**self.params)
            fold_model.fit(X_fold_train, y_fold_train, verbose=False)
            
            # Predictions
            y_val_proba = fold_model.predict_proba(X_fold_val)[:, 1]
            
            # Metrics
            auc_scores.append(roc_auc_score(y_fold_val, y_val_proba))
            logloss_scores.append(log_loss(y_fold_val, y_val_proba))
        
        return {
            'auc_mean': np.mean(auc_scores),
            'auc_std': np.std(auc_scores),
            'logloss_mean': np.mean(logloss_scores),
            'logloss_std': np.std(logloss_scores)
        }
    
    def predict(self, features: Dict[str, Any]) -> float:
        """
        Predict probability that a prop will hit.
        
        Args:
            features: Dictionary of feature values
            
        Returns:
            Probability of prop hitting (0.0 to 1.0)
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        # Convert to DataFrame for preprocessing
        df = pd.DataFrame([features])
        
        # Ensure all expected features are present
        for feature in self.numerical_features + self.categorical_features:
            if feature not in df.columns:
                # Use sport-specific defaults
                if feature in self.categorical_features:
                    df[feature] = 'Unknown' if self.sport == 'nba' else 'Other'
                else:
                    df[feature] = 0.0
        
        # Preprocess
        X_processed = self.preprocessor.transform(df[self.numerical_features + self.categorical_features])
        
        # Predict
        probability = self.model.predict_proba(X_processed)[0, 1]
        
        return float(probability)
    
    def evaluate(self, csv_path: str) -> Dict[str, Any]:
        """
        Evaluate model on new dataset.
        
        Args:
            csv_path: Path to evaluation CSV
            
        Returns:
            Evaluation metrics
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before evaluation")
        
        # Load and preprocess evaluation data
        df = self.load_data(csv_path)
        X, y = self.preprocess_features(df)
        
        # Predictions
        y_proba = self.model.predict_proba(X)[:, 1]
        y_pred = (y_proba > 0.5).astype(int)
        
        # Metrics
        auc = roc_auc_score(y, y_proba)
        logloss = log_loss(y, y_proba)
        
        return {
            'auc': auc,
            'logloss': logloss,
            'classification_report': classification_report(y, y_pred, output_dict=True),
            'confusion_matrix': confusion_matrix(y, y_pred).tolist(),
            'samples': len(y)
        }
    
    def _save_model(self):
        """Save trained model and preprocessor."""
        if self.is_trained:
            # Save XGBoost model
            model_path = self.model_dir / f"{self.sport}_prop_model.pkl"
            with open(model_path, 'wb') as f:
                pickle.dump(self.model, f)
            
            # Save preprocessor
            preprocessor_path = self.model_dir / f"{self.sport}_preprocessor.pkl"
            with open(preprocessor_path, 'wb') as f:
                pickle.dump(self.preprocessor, f)
            
            # Save feature names
            features_path = self.model_dir / f"{self.sport}_features.pkl"
            with open(features_path, 'wb') as f:
                pickle.dump(self.feature_names, f)
            
            logger.info(f"Model saved to {self.model_dir}")
    
    def load_model(self):
        """Load pre-trained model."""
        try:
            # Load XGBoost model
            model_path = self.model_dir / f"{self.sport}_prop_model.pkl"
            with open(model_path, 'rb') as f:
                self.model = pickle.load(f)
            
            # Load preprocessor
            preprocessor_path = self.model_dir / f"{self.sport}_preprocessor.pkl"
            with open(preprocessor_path, 'rb') as f:
                self.preprocessor = pickle.load(f)
            
            # Load feature names
            features_path = self.model_dir / f"{self.sport}_features.pkl"
            with open(features_path, 'rb') as f:
                self.feature_names = pickle.load(f)
            
            self.is_trained = True
            logger.info(f"Model loaded from {self.model_dir}")
            
        except FileNotFoundError as e:
            logger.error(f"Model files not found: {e}")
            raise


def create_sample_data():
    """Create sample CSV files for testing."""
    import random
    from datetime import datetime, timedelta
    
    # NBA sample data
    nba_data = []
    nba_players = [f"nba_player_{i}" for i in range(100)]
    
    for i in range(1000):
        points = random.randint(5, 45)
        nba_data.append({
            'player_id': random.choice(nba_players),
            'game_date': (datetime.now() - timedelta(days=random.randint(1, 365))).strftime('%Y-%m-%d'),
            'points_scored': points,
            'rebounds': random.randint(0, 15),
            'assists': random.randint(0, 12),
            'opponent_def_rating': random.uniform(100, 120),
            'minutes_played': random.randint(20, 45),
            'field_goal_attempts': random.randint(8, 25),
            'three_point_attempts': random.randint(0, 12),
            'free_throw_attempts': random.randint(0, 10),
            'turnovers': random.randint(0, 6),
            'home_away': random.choice(['home', 'away']),
            'days_rest': random.randint(0, 4),
            'season_avg_points': points + random.uniform(-5, 5),
            'last_5_avg_points': points + random.uniform(-3, 3),
            'opponent_points_allowed': random.uniform(100, 130),
            'pace': random.uniform(95, 105),
            'usage_rate': random.uniform(15, 35),
            'hit_prop': 1 if points > 20 else 0  # Simple rule for demo
        })
    
    nba_df = pd.DataFrame(nba_data)
    nba_df.to_csv('data/nba_prop_training_data.csv', index=False)
    
    # NFL sample data
    nfl_data = []
    nfl_players = [f"nfl_player_{i}" for i in range(100)]
    positions = ['QB', 'RB', 'WR', 'TE']
    
    for i in range(800):
        passing_yards = random.randint(0, 400) if random.random() > 0.7 else 0
        rushing_yards = random.randint(0, 150)
        receiving_yards = random.randint(0, 150) if random.random() > 0.5 else 0
        
        nfl_data.append({
            'player_id': random.choice(nfl_players),
            'game_date': (datetime.now() - timedelta(days=random.randint(1, 365))).strftime('%Y-%m-%d'),
            'passing_yards': passing_yards,
            'rushing_yards': rushing_yards,
            'receiving_yards': receiving_yards,
            'passing_touchdowns': random.randint(0, 4),
            'rushing_touchdowns': random.randint(0, 3),
            'receptions': random.randint(0, 12),
            'targets': random.randint(0, 15),
            'opponent_def_rating': random.uniform(80, 120),
            'weather_conditions': random.choice(['clear', 'rain', 'snow', 'wind']),
            'dome_game': random.choice([0, 1]),
            'position': random.choice(positions),
            'home_away': random.choice(['home', 'away']),
            'division_game': random.choice([0, 1]),
            'season_avg_yards': (passing_yards + rushing_yards + receiving_yards) + random.uniform(-20, 20),
            'last_4_avg_yards': (passing_yards + rushing_yards + receiving_yards) + random.uniform(-15, 15),
            'opponent_yards_allowed': random.uniform(300, 450),
            'snap_count': random.randint(30, 70),
            'red_zone_targets': random.randint(0, 5),
            'hit_prop': 1 if (passing_yards + rushing_yards + receiving_yards) > 80 else 0
        })
    
    nfl_df = pd.DataFrame(nfl_data)
    nfl_df.to_csv('data/nfl_prop_training_data.csv', index=False)
    
    print("✅ Sample CSV files created:")
    print(f"   - data/nba_prop_training_data.csv ({len(nba_df)} rows)")
    print(f"   - data/nfl_prop_training_data.csv ({len(nfl_df)} rows)")


if __name__ == "__main__":
    # Demo usage
    logging.basicConfig(level=logging.INFO)
    
    print("🏀🏈 Historical Prop Trainer Demo")
    print("=" * 50)
    
    # Create sample data
    create_sample_data()
    
    # Train NBA model
    print("\n🏀 Training NBA Prop Predictor...")
    nba_trainer = HistoricalPropTrainer("nba")
    nba_metrics = nba_trainer.train("data/nba_prop_training_data.csv")
    
    print(f"NBA Results:")
    print(f"  Test AUC: {nba_metrics['test_auc']:.4f}")
    print(f"  Test LogLoss: {nba_metrics['test_logloss']:.4f}")
    print(f"  CV AUC: {nba_metrics['cv_auc_mean']:.4f} ± {nba_metrics['cv_auc_std']:.4f}")
    
    # Test NBA prediction
    nba_sample = {
        'points_scored': 25,
        'rebounds': 8,
        'assists': 5,
        'opponent_def_rating': 110,
        'minutes_played': 35,
        'home_away': 'home',
        'season_avg_points': 22
    }
    nba_prob = nba_trainer.predict(nba_sample)
    print(f"  Sample prediction probability: {nba_prob:.4f}")
    
    # Train NFL model
    print("\n🏈 Training NFL Prop Predictor...")
    nfl_trainer = HistoricalPropTrainer("nfl")
    nfl_metrics = nfl_trainer.train("data/nfl_prop_training_data.csv")
    
    print(f"NFL Results:")
    print(f"  Test AUC: {nfl_metrics['test_auc']:.4f}")
    print(f"  Test LogLoss: {nfl_metrics['test_logloss']:.4f}")
    print(f"  CV AUC: {nfl_metrics['cv_auc_mean']:.4f} ± {nfl_metrics['cv_auc_std']:.4f}")
    
    # Test NFL prediction
    nfl_sample = {
        'passing_yards': 250,
        'rushing_yards': 0,
        'receiving_yards': 0,
        'position': 'QB',
        'opponent_def_rating': 95,
        'weather_conditions': 'clear',
        'home_away': 'home'
    }
    nfl_prob = nfl_trainer.predict(nfl_sample)
    print(f"  Sample prediction probability: {nfl_prob:.4f}")
    
    print("\n✅ Demo complete! Models saved in models/ directory")
