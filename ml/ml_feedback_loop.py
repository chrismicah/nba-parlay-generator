#!/usr/bin/env python3
"""
ML Feedback Loop System - ML-FEEDBACK-LOOP-001

Automated feedback loop system that collects parlay outcomes, detects data drift,
triggers model retraining, and tracks experiments with MLflow. Integrates with
the existing parlay prediction system for continuous improvement.

Key Features:
- Outcome collection from APIs and databases
- Data drift detection using Kolmogorov-Smirnov test
- Automated XGBoost model retraining
- MLflow experiment tracking and artifact management
- Scheduled daily/weekly execution
- API cost-aware retraining decisions
- Integration with existing prediction models
"""

import logging
import numpy as np
import pandas as pd
import sqlite3
import json
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
import schedule
import time
import warnings
from scipy import stats

# MLflow imports
try:
    import mlflow
    import mlflow.sklearn
    import mlflow.xgboost
    HAS_MLFLOW = True
except ImportError:
    HAS_MLFLOW = False
    mlflow = None

# XGBoost imports
try:
    import xgboost as xgb
    from xgboost import XGBClassifier
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False
    xgb = XGBClassifier = None

# Scikit-learn imports
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, roc_auc_score, brier_score_loss, log_loss
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier

# Set up logging
logger = logging.getLogger(__name__)

# Suppress warnings
warnings.filterwarnings('ignore', category=UserWarning)


@dataclass
class DriftDetectionResult:
    """Result of data drift detection analysis."""
    has_drift: bool
    drift_score: float
    p_value: float
    drift_features: List[str]
    drift_magnitude: str  # 'low', 'medium', 'high'
    detection_method: str = "kolmogorov_smirnov"
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class RetrainingResult:
    """Result of model retraining process."""
    success: bool
    model_name: str
    old_performance: Dict[str, float]
    new_performance: Dict[str, float]
    performance_improvement: Dict[str, float]
    training_samples: int
    mlflow_run_id: Optional[str] = None
    model_path: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class FeedbackConfig:
    """Configuration for feedback loop system."""
    # Data collection settings
    outcome_lookback_days: int = 7
    min_samples_for_retraining: int = 100
    drift_detection_threshold: float = 0.05
    
    # Model settings
    model_type: str = "xgboost"  # or "random_forest"
    test_size: float = 0.2
    random_state: int = 42
    
    # MLflow settings
    experiment_name: str = "parlay_feedback_loop"
    model_registry_name: str = "parlay_predictor"
    tracking_uri: str = "sqlite:///mlflow.db"
    
    # Scheduling settings
    daily_schedule_time: str = "06:00"  # 6 AM
    weekly_schedule_day: str = "monday"
    weekly_schedule_time: str = "06:00"
    
    # API cost settings
    max_daily_api_cost: float = 10.0  # USD
    retraining_api_cost: float = 2.5   # USD per retraining
    
    # File paths
    training_data_path: str = "data/ml_training/parlay_training_data.csv"
    model_save_path: str = "models/feedback_retrained"
    drift_log_path: str = "data/feedback_reports/drift_detection.json"
    
    # Sport-specific settings
    sport: str = "nba"  # or "nfl"


class OutcomeCollector:
    """Collects parlay outcomes from various sources."""
    
    def __init__(self, config: FeedbackConfig):
        """Initialize outcome collector."""
        self.config = config
        self.db_path = "data/parlays.sqlite"
        
    def collect_recent_outcomes(self, days_back: int = None) -> pd.DataFrame:
        """
        Collect recent parlay outcomes from the database.
        
        Args:
            days_back: Number of days to look back (uses config default if None)
            
        Returns:
            DataFrame with parlay outcomes and features
        """
        if days_back is None:
            days_back = self.config.outcome_lookback_days
            
        try:
            # Connect to SQLite database
            conn = sqlite3.connect(self.db_path)
            
            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=days_back)
            cutoff_str = cutoff_date.strftime("%Y-%m-%d")
            
            # Query for recent parlays with outcomes
            query = """
            SELECT 
                id,
                sport,
                legs_count,
                total_odds,
                expected_value,
                confidence_score,
                result,
                actual_payout,
                bet_amount,
                created_at,
                legs_json
            FROM bets 
            WHERE created_at >= ? 
            AND result IS NOT NULL
            AND sport = ?
            ORDER BY created_at DESC
            """
            
            df = pd.read_sql_query(query, conn, params=[cutoff_str, self.config.sport])
            conn.close()
            
            if df.empty:
                logger.warning(f"No recent outcomes found for {self.config.sport} in last {days_back} days")
                return pd.DataFrame()
            
            # Parse legs and extract features
            df = self._extract_features_from_outcomes(df)
            
            logger.info(f"Collected {len(df)} recent outcomes for {self.config.sport}")
            return df
            
        except Exception as e:
            logger.error(f"Error collecting outcomes: {e}")
            return pd.DataFrame()
    
    def _extract_features_from_outcomes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract features from parlay outcome data."""
        try:
            # Add basic features
            df['hit'] = (df['result'] == 'WIN').astype(int)
            df['datetime'] = pd.to_datetime(df['created_at'])
            df['day_of_week'] = df['datetime'].dt.dayofweek
            df['hour'] = df['datetime'].dt.hour
            
            # Extract leg features
            leg_features = []
            for idx, row in df.iterrows():
                try:
                    legs = json.loads(row['legs_json']) if row['legs_json'] else []
                    
                    # Calculate aggregate leg features
                    avg_odds = np.mean([leg.get('odds', 1.0) for leg in legs]) if legs else 1.0
                    max_odds = max([leg.get('odds', 1.0) for leg in legs]) if legs else 1.0
                    min_odds = min([leg.get('odds', 1.0) for leg in legs]) if legs else 1.0
                    
                    # Market type distribution
                    markets = [leg.get('market_type', '') for leg in legs]
                    unique_markets = len(set(markets))
                    
                    leg_features.append({
                        'avg_leg_odds': avg_odds,
                        'max_leg_odds': max_odds,
                        'min_leg_odds': min_odds,
                        'unique_markets': unique_markets,
                        'has_player_props': int(any('player' in str(leg.get('market_type', '')).lower() for leg in legs))
                    })
                    
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Error parsing legs for parlay {row['id']}: {e}")
                    leg_features.append({
                        'avg_leg_odds': 1.0,
                        'max_leg_odds': 1.0,
                        'min_leg_odds': 1.0,
                        'unique_markets': 0,
                        'has_player_props': 0
                    })
            
            # Add leg features to dataframe
            leg_df = pd.DataFrame(leg_features)
            df = pd.concat([df.reset_index(drop=True), leg_df], axis=1)
            
            return df
            
        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            return df
    
    def simulate_api_outcomes(self, n_samples: int = 50) -> pd.DataFrame:
        """
        Simulate API outcome collection for testing.
        
        Args:
            n_samples: Number of samples to simulate
            
        Returns:
            DataFrame with simulated outcomes
        """
        np.random.seed(42)
        
        # Simulate parlay data
        data = {
            'id': range(1, n_samples + 1),
            'sport': [self.config.sport] * n_samples,
            'legs_count': np.random.randint(2, 6, n_samples),
            'total_odds': np.random.uniform(2.0, 15.0, n_samples),
            'expected_value': np.random.uniform(-0.1, 0.2, n_samples),
            'confidence_score': np.random.uniform(0.3, 0.9, n_samples),
            'bet_amount': np.random.uniform(10, 100, n_samples),
            'created_at': [(datetime.now() - timedelta(days=np.random.randint(0, 7))).strftime("%Y-%m-%d %H:%M:%S") 
                          for _ in range(n_samples)]
        }
        
        df = pd.DataFrame(data)
        
        # Simulate win/loss based on expected value and confidence
        win_prob = 0.5 + df['expected_value'] * 0.3 + (df['confidence_score'] - 0.6) * 0.2
        win_prob = np.clip(win_prob, 0.1, 0.9)
        df['hit'] = np.random.binomial(1, win_prob)
        df['result'] = df['hit'].map({1: 'WIN', 0: 'LOSS'})
        
        # Add leg features
        df['avg_leg_odds'] = df['total_odds'] / df['legs_count'] + np.random.normal(0, 0.1, n_samples)
        df['max_leg_odds'] = df['avg_leg_odds'] * np.random.uniform(1.2, 2.0, n_samples)
        df['min_leg_odds'] = df['avg_leg_odds'] * np.random.uniform(0.8, 1.0, n_samples)
        df['unique_markets'] = np.random.randint(1, df['legs_count'] + 1, n_samples)
        df['has_player_props'] = np.random.binomial(1, 0.6, n_samples)
        
        # Add time-based features
        df['datetime'] = pd.to_datetime(df['created_at'])
        df['day_of_week'] = df['datetime'].dt.dayofweek
        df['hour'] = df['datetime'].dt.hour
        
        logger.info(f"Simulated {n_samples} API outcomes with {df['hit'].mean():.1%} win rate")
        return df


class DriftDetector:
    """Detects data drift in parlay features and outcomes."""
    
    def __init__(self, config: FeedbackConfig):
        """Initialize drift detector."""
        self.config = config
        
    def detect_drift(self, historical_data: pd.DataFrame, 
                    recent_data: pd.DataFrame) -> DriftDetectionResult:
        """
        Detect data drift between historical and recent data.
        
        Args:
            historical_data: Historical training data
            recent_data: Recent outcome data
            
        Returns:
            DriftDetectionResult with drift analysis
        """
        try:
            # Get common feature columns
            feature_cols = self._get_common_features(historical_data, recent_data)
            
            if not feature_cols:
                logger.warning("No common features found for drift detection")
                return DriftDetectionResult(
                    has_drift=False,
                    drift_score=0.0,
                    p_value=1.0,
                    drift_features=[],
                    drift_magnitude="none"
                )
            
            # Perform KS test for each feature
            drift_results = {}
            drift_features = []
            
            for col in feature_cols:
                try:
                    hist_values = historical_data[col].dropna()
                    recent_values = recent_data[col].dropna()
                    
                    if len(hist_values) < 10 or len(recent_values) < 10:
                        continue
                    
                    # Kolmogorov-Smirnov test
                    ks_stat, p_value = stats.ks_2samp(hist_values, recent_values)
                    
                    drift_results[col] = {
                        'ks_statistic': ks_stat,
                        'p_value': p_value,
                        'has_drift': p_value < self.config.drift_detection_threshold
                    }
                    
                    if p_value < self.config.drift_detection_threshold:
                        drift_features.append(col)
                        
                except Exception as e:
                    logger.warning(f"Error testing drift for feature {col}: {e}")
                    continue
            
            # Calculate overall drift metrics
            if drift_results:
                avg_ks_stat = np.mean([r['ks_statistic'] for r in drift_results.values()])
                min_p_value = min([r['p_value'] for r in drift_results.values()])
                
                # Determine drift magnitude
                if avg_ks_stat > 0.3:
                    magnitude = "high"
                elif avg_ks_stat > 0.15:
                    magnitude = "medium"
                elif avg_ks_stat > 0.05:
                    magnitude = "low"
                else:
                    magnitude = "none"
                
                has_drift = len(drift_features) > 0
                
            else:
                avg_ks_stat = 0.0
                min_p_value = 1.0
                magnitude = "none"
                has_drift = False
            
            result = DriftDetectionResult(
                has_drift=has_drift,
                drift_score=avg_ks_stat,
                p_value=min_p_value,
                drift_features=drift_features,
                drift_magnitude=magnitude
            )
            
            logger.info(f"Drift detection: {'DRIFT DETECTED' if has_drift else 'NO DRIFT'} "
                       f"(score: {avg_ks_stat:.3f}, features: {len(drift_features)})")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in drift detection: {e}")
            return DriftDetectionResult(
                has_drift=False,
                drift_score=0.0,
                p_value=1.0,
                drift_features=[],
                drift_magnitude="error"
            )
    
    def _get_common_features(self, df1: pd.DataFrame, df2: pd.DataFrame) -> List[str]:
        """Get common numerical features between two dataframes."""
        # Define target feature columns for drift detection
        target_features = [
            'legs_count', 'total_odds', 'expected_value', 'confidence_score',
            'avg_leg_odds', 'max_leg_odds', 'min_leg_odds', 'unique_markets',
            'day_of_week', 'hour'
        ]
        
        common_features = []
        for col in target_features:
            if col in df1.columns and col in df2.columns:
                # Check if column is numeric
                if df1[col].dtype in ['int64', 'float64'] and df2[col].dtype in ['int64', 'float64']:
                    common_features.append(col)
        
        return common_features


class ModelRetrainer:
    """Handles model retraining with new data."""
    
    def __init__(self, config: FeedbackConfig):
        """Initialize model retrainer."""
        self.config = config
        self.scaler = StandardScaler()
        
    def retrain_model(self, historical_data: pd.DataFrame, 
                     new_data: pd.DataFrame) -> RetrainingResult:
        """
        Retrain model with combined historical and new data.
        
        Args:
            historical_data: Existing training data
            new_data: New outcome data to append
            
        Returns:
            RetrainingResult with performance metrics
        """
        try:
            # Combine datasets
            combined_data = pd.concat([historical_data, new_data], ignore_index=True)
            
            logger.info(f"Retraining with {len(combined_data)} samples "
                       f"({len(new_data)} new, {len(historical_data)} historical)")
            
            # Prepare features and target
            X, y = self._prepare_training_data(combined_data)
            
            if len(X) < self.config.min_samples_for_retraining:
                raise ValueError(f"Insufficient samples for retraining: {len(X)} < {self.config.min_samples_for_retraining}")
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=self.config.test_size, 
                random_state=self.config.random_state, stratify=y
            )
            
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Get baseline performance (if model exists)
            old_performance = self._get_current_model_performance(X_test_scaled, y_test)
            
            # Train new model
            if self.config.model_type == "xgboost" and HAS_XGBOOST:
                model = self._train_xgboost_model(X_train_scaled, y_train)
            else:
                model = self._train_fallback_model(X_train_scaled, y_train)
            
            # Evaluate new model
            new_performance = self._evaluate_model(model, X_test_scaled, y_test)
            
            # Calculate performance improvement
            improvement = {}
            for metric in new_performance:
                old_val = old_performance.get(metric, 0.5)  # Default to neutral performance
                new_val = new_performance[metric]
                
                if metric == 'brier_score':  # Lower is better
                    improvement[metric] = old_val - new_val
                else:  # Higher is better
                    improvement[metric] = new_val - old_val
            
            # Save model and scaler
            model_path = self._save_model(model, self.scaler)
            
            # Save updated training data
            self._save_training_data(combined_data)
            
            result = RetrainingResult(
                success=True,
                model_name=f"{self.config.model_type}_{self.config.sport}",
                old_performance=old_performance,
                new_performance=new_performance,
                performance_improvement=improvement,
                training_samples=len(combined_data),
                model_path=model_path
            )
            
            logger.info(f"Retraining successful: AUC {new_performance['auc']:.3f} "
                       f"(+{improvement.get('auc', 0):.3f})")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in model retraining: {e}")
            return RetrainingResult(
                success=False,
                model_name=f"{self.config.model_type}_{self.config.sport}",
                old_performance={},
                new_performance={},
                performance_improvement={},
                training_samples=0
            )
    
    def _prepare_training_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare features and target for training."""
        # Select feature columns
        feature_cols = [
            'legs_count', 'total_odds', 'expected_value', 'confidence_score',
            'avg_leg_odds', 'max_leg_odds', 'min_leg_odds', 'unique_markets',
            'has_player_props', 'day_of_week', 'hour'
        ]
        
        # Filter to available columns
        available_cols = [col for col in feature_cols if col in df.columns]
        
        X = df[available_cols].copy()
        y = df['hit'].copy()
        
        # Handle missing values
        X = X.fillna(X.median())
        
        logger.debug(f"Prepared training data: {X.shape[0]} samples, {X.shape[1]} features")
        return X, y
    
    def _train_xgboost_model(self, X: np.ndarray, y: np.ndarray) -> XGBClassifier:
        """Train XGBoost model."""
        model = XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=self.config.random_state,
            eval_metric='logloss'
        )
        
        model.fit(X, y)
        logger.info("XGBoost model trained successfully")
        return model
    
    def _train_fallback_model(self, X: np.ndarray, y: np.ndarray) -> RandomForestClassifier:
        """Train fallback Random Forest model."""
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=self.config.random_state
        )
        
        model.fit(X, y)
        logger.info("Random Forest fallback model trained successfully")
        return model
    
    def _evaluate_model(self, model, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, float]:
        """Evaluate model performance."""
        try:
            y_pred = model.predict(X_test)
            y_proba = model.predict_proba(X_test)[:, 1]
            
            metrics = {
                'accuracy': accuracy_score(y_test, y_pred),
                'auc': roc_auc_score(y_test, y_proba),
                'brier_score': brier_score_loss(y_test, y_proba),
                'log_loss': log_loss(y_test, y_proba)
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error evaluating model: {e}")
            return {'accuracy': 0.5, 'auc': 0.5, 'brier_score': 0.25, 'log_loss': 1.0}
    
    def _get_current_model_performance(self, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, float]:
        """Get performance of current model if it exists."""
        try:
            model_path = Path(self.config.model_save_path) / f"{self.config.sport}_model.pkl"
            scaler_path = Path(self.config.model_save_path) / f"{self.config.sport}_scaler.pkl"
            
            if model_path.exists() and scaler_path.exists():
                # Load existing model
                with open(model_path, 'rb') as f:
                    model = pickle.load(f)
                
                return self._evaluate_model(model, X_test, y_test)
            else:
                logger.info("No existing model found - using baseline performance")
                return {'accuracy': 0.5, 'auc': 0.5, 'brier_score': 0.25, 'log_loss': 1.0}
                
        except Exception as e:
            logger.warning(f"Error loading current model: {e}")
            return {'accuracy': 0.5, 'auc': 0.5, 'brier_score': 0.25, 'log_loss': 1.0}
    
    def _save_model(self, model, scaler) -> str:
        """Save trained model and scaler."""
        save_dir = Path(self.config.model_save_path)
        save_dir.mkdir(parents=True, exist_ok=True)
        
        model_path = save_dir / f"{self.config.sport}_model.pkl"
        scaler_path = save_dir / f"{self.config.sport}_scaler.pkl"
        
        # Save model
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        
        # Save scaler
        with open(scaler_path, 'wb') as f:
            pickle.dump(scaler, f)
        
        logger.info(f"Model saved to {model_path}")
        return str(model_path)
    
    def _save_training_data(self, df: pd.DataFrame):
        """Save updated training data."""
        save_path = Path(self.config.training_data_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        df.to_csv(save_path, index=False)
        logger.info(f"Training data saved to {save_path} ({len(df)} samples)")


class MLflowTracker:
    """Handles MLflow experiment tracking and model registry."""
    
    def __init__(self, config: FeedbackConfig):
        """Initialize MLflow tracker."""
        self.config = config
        
        if not HAS_MLFLOW:
            logger.warning("MLflow not available - experiment tracking disabled")
            return
        
        # Set tracking URI
        mlflow.set_tracking_uri(config.tracking_uri)
        
        # Set or create experiment
        try:
            mlflow.set_experiment(config.experiment_name)
            logger.info(f"MLflow experiment: {config.experiment_name}")
        except Exception as e:
            logger.warning(f"Error setting MLflow experiment: {e}")
    
    def log_feedback_run(self, drift_result: DriftDetectionResult,
                        retrain_result: RetrainingResult,
                        outcome_data: pd.DataFrame) -> Optional[str]:
        """Log complete feedback loop run to MLflow."""
        if not HAS_MLFLOW:
            return None
        
        try:
            with mlflow.start_run(run_name=f"feedback_loop_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
                # Log parameters
                mlflow.log_param("sport", self.config.sport)
                mlflow.log_param("model_type", self.config.model_type)
                mlflow.log_param("outcome_samples", len(outcome_data))
                mlflow.log_param("drift_threshold", self.config.drift_detection_threshold)
                
                # Log drift detection results
                mlflow.log_metric("drift_score", drift_result.drift_score)
                mlflow.log_metric("drift_p_value", drift_result.p_value)
                mlflow.log_metric("drift_features_count", len(drift_result.drift_features))
                mlflow.log_param("has_drift", drift_result.has_drift)
                mlflow.log_param("drift_magnitude", drift_result.drift_magnitude)
                
                # Log retraining results if successful
                if retrain_result.success:
                    mlflow.log_metric("training_samples", retrain_result.training_samples)
                    
                    # Log performance metrics
                    for metric, value in retrain_result.new_performance.items():
                        mlflow.log_metric(f"new_{metric}", value)
                    
                    for metric, value in retrain_result.old_performance.items():
                        mlflow.log_metric(f"old_{metric}", value)
                    
                    for metric, value in retrain_result.performance_improvement.items():
                        mlflow.log_metric(f"improvement_{metric}", value)
                    
                    # Log model if available
                    if retrain_result.model_path and Path(retrain_result.model_path).exists():
                        mlflow.log_artifact(retrain_result.model_path, "model")
                
                # Log drift detection details
                drift_log = {
                    "timestamp": drift_result.timestamp.isoformat(),
                    "has_drift": drift_result.has_drift,
                    "drift_features": drift_result.drift_features,
                    "drift_magnitude": drift_result.drift_magnitude
                }
                
                mlflow.log_dict(drift_log, "drift_detection.json")
                
                # Log outcome data summary
                outcome_summary = {
                    "total_samples": len(outcome_data),
                    "win_rate": outcome_data['hit'].mean() if 'hit' in outcome_data.columns else 0,
                    "avg_odds": outcome_data['total_odds'].mean() if 'total_odds' in outcome_data.columns else 0,
                    "date_range": {
                        "start": outcome_data['created_at'].min() if 'created_at' in outcome_data.columns else "",
                        "end": outcome_data['created_at'].max() if 'created_at' in outcome_data.columns else ""
                    }
                }
                
                mlflow.log_dict(outcome_summary, "outcome_summary.json")
                
                run_id = mlflow.active_run().info.run_id
                logger.info(f"MLflow run logged: {run_id}")
                return run_id
                
        except Exception as e:
            logger.error(f"Error logging to MLflow: {e}")
            return None


class FeedbackLoop:
    """Main feedback loop coordinator."""
    
    def __init__(self, config: FeedbackConfig = None):
        """Initialize feedback loop system."""
        self.config = config or FeedbackConfig()
        
        # Initialize components
        self.outcome_collector = OutcomeCollector(self.config)
        self.drift_detector = DriftDetector(self.config)
        self.model_retrainer = ModelRetrainer(self.config)
        self.mlflow_tracker = MLflowTracker(self.config)
        
        # State tracking
        self.last_run_time = None
        self.total_api_cost_today = 0.0
        
        logger.info(f"FeedbackLoop initialized for {self.config.sport}")
    
    def run_feedback_cycle(self, force_retrain: bool = False) -> Dict[str, Any]:
        """
        Execute complete feedback loop cycle.
        
        Args:
            force_retrain: Force retraining regardless of drift detection
            
        Returns:
            Dictionary with cycle results
        """
        try:
            logger.info("🔄 Starting feedback loop cycle...")
            
            # Check API cost limits
            if not self._check_api_cost_limits():
                return {"success": False, "reason": "API cost limit exceeded"}
            
            # Step 1: Collect recent outcomes
            logger.info("📊 Collecting recent parlay outcomes...")
            recent_outcomes = self.outcome_collector.collect_recent_outcomes()
            
            if recent_outcomes.empty:
                logger.warning("No recent outcomes available - using simulated data")
                recent_outcomes = self.outcome_collector.simulate_api_outcomes(50)
            
            # Step 2: Load historical training data
            historical_data = self._load_historical_data()
            
            # Step 3: Detect data drift
            logger.info("🔍 Detecting data drift...")
            drift_result = self.drift_detector.detect_drift(historical_data, recent_outcomes)
            
            # Step 4: Decide on retraining
            should_retrain = force_retrain or drift_result.has_drift or len(recent_outcomes) > 100
            
            retrain_result = None
            if should_retrain:
                logger.info("🚀 Triggering model retraining...")
                
                # Check API cost for retraining
                if self.total_api_cost_today + self.config.retraining_api_cost > self.config.max_daily_api_cost:
                    logger.warning("Skipping retraining due to API cost limits")
                else:
                    retrain_result = self.model_retrainer.retrain_model(historical_data, recent_outcomes)
                    self.total_api_cost_today += self.config.retraining_api_cost
            else:
                logger.info("📋 No retraining needed (no significant drift detected)")
                retrain_result = RetrainingResult(
                    success=False,
                    model_name=f"{self.config.model_type}_{self.config.sport}",
                    old_performance={},
                    new_performance={},
                    performance_improvement={},
                    training_samples=0
                )
            
            # Step 5: Log to MLflow
            if HAS_MLFLOW:
                logger.info("📝 Logging results to MLflow...")
                mlflow_run_id = self.mlflow_tracker.log_feedback_run(
                    drift_result, retrain_result, recent_outcomes
                )
                if retrain_result:
                    retrain_result.mlflow_run_id = mlflow_run_id
            
            # Step 6: Save drift detection log
            self._save_drift_log(drift_result, retrain_result)
            
            # Update last run time
            self.last_run_time = datetime.now()
            
            # Prepare results summary
            results = {
                "success": True,
                "timestamp": self.last_run_time.isoformat(),
                "drift_detected": drift_result.has_drift,
                "drift_magnitude": drift_result.drift_magnitude,
                "retrained": retrain_result.success if retrain_result else False,
                "outcome_samples": len(recent_outcomes),
                "api_cost_used": self.config.retraining_api_cost if should_retrain else 0.0,
                "mlflow_run_id": retrain_result.mlflow_run_id if retrain_result else None
            }
            
            if retrain_result and retrain_result.success:
                results["performance_improvement"] = retrain_result.performance_improvement
                results["new_auc"] = retrain_result.new_performance.get("auc", 0.0)
            
            logger.info(f"✅ Feedback cycle completed successfully")
            logger.info(f"   • Drift detected: {drift_result.has_drift}")
            logger.info(f"   • Model retrained: {retrain_result.success if retrain_result else False}")
            logger.info(f"   • Outcome samples: {len(recent_outcomes)}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error in feedback cycle: {e}")
            return {"success": False, "error": str(e)}
    
    def schedule_jobs(self):
        """Schedule daily and weekly feedback loop jobs."""
        # Schedule daily checks
        schedule.every().day.at(self.config.daily_schedule_time).do(
            self._scheduled_daily_check
        )
        
        # Schedule weekly full retraining
        getattr(schedule.every(), self.config.weekly_schedule_day.lower()).at(
            self.config.weekly_schedule_time
        ).do(self._scheduled_weekly_retrain)
        
        logger.info(f"Scheduled jobs:")
        logger.info(f"  • Daily check: {self.config.daily_schedule_time}")
        logger.info(f"  • Weekly retrain: {self.config.weekly_schedule_day} {self.config.weekly_schedule_time}")
    
    def run_scheduler(self):
        """Run the scheduler loop."""
        logger.info("🕐 Starting feedback loop scheduler...")
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except KeyboardInterrupt:
                logger.info("Scheduler stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in scheduler: {e}")
                time.sleep(300)  # Wait 5 minutes before retrying
    
    def _scheduled_daily_check(self):
        """Scheduled daily drift check."""
        logger.info("🌅 Running scheduled daily feedback check...")
        results = self.run_feedback_cycle(force_retrain=False)
        
        if results.get("drift_detected"):
            logger.warning("⚠️ Data drift detected in daily check!")
    
    def _scheduled_weekly_retrain(self):
        """Scheduled weekly forced retraining."""
        logger.info("📅 Running scheduled weekly retraining...")
        results = self.run_feedback_cycle(force_retrain=True)
        
        if results.get("success"):
            logger.info("✅ Weekly retraining completed successfully")
    
    def _check_api_cost_limits(self) -> bool:
        """Check if API cost limits allow operation."""
        # Reset daily cost tracking if it's a new day
        today = datetime.now().date()
        if not hasattr(self, '_last_cost_reset_date') or self._last_cost_reset_date != today:
            self.total_api_cost_today = 0.0
            self._last_cost_reset_date = today
        
        return self.total_api_cost_today < self.config.max_daily_api_cost
    
    def _load_historical_data(self) -> pd.DataFrame:
        """Load historical training data."""
        try:
            if Path(self.config.training_data_path).exists():
                df = pd.read_csv(self.config.training_data_path)
                logger.info(f"Loaded {len(df)} historical training samples")
                return df
            else:
                logger.warning("No historical training data found - creating sample data")
                return self._create_sample_historical_data()
                
        except Exception as e:
            logger.error(f"Error loading historical data: {e}")
            return self._create_sample_historical_data()
    
    def _create_sample_historical_data(self) -> pd.DataFrame:
        """Create sample historical training data."""
        # Use outcome collector to simulate historical data
        collector = OutcomeCollector(self.config)
        return collector.simulate_api_outcomes(200)
    
    def _save_drift_log(self, drift_result: DriftDetectionResult, 
                       retrain_result: RetrainingResult):
        """Save drift detection log."""
        try:
            log_path = Path(self.config.drift_log_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Load existing logs
            if log_path.exists():
                with open(log_path, 'r') as f:
                    logs = json.load(f)
            else:
                logs = []
            
            # Add new log entry
            log_entry = {
                "timestamp": drift_result.timestamp.isoformat(),
                "sport": self.config.sport,
                "drift_detected": drift_result.has_drift,
                "drift_score": drift_result.drift_score,
                "drift_magnitude": drift_result.drift_magnitude,
                "drift_features": drift_result.drift_features,
                "retrained": retrain_result.success if retrain_result else False,
                "performance_improvement": retrain_result.performance_improvement if retrain_result else {}
            }
            
            logs.append(log_entry)
            
            # Keep only last 100 entries
            logs = logs[-100:]
            
            # Save updated logs
            with open(log_path, 'w') as f:
                json.dump(logs, f, indent=2)
            
            logger.debug(f"Drift log saved to {log_path}")
            
        except Exception as e:
            logger.warning(f"Error saving drift log: {e}")


if __name__ == "__main__":
    # Demo usage
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🔄 ML Feedback Loop Demo")
    print("=" * 50)
    
    # Test configuration
    config = FeedbackConfig(
        sport="nba",
        outcome_lookback_days=7,
        experiment_name="feedback_loop_demo",
        model_type="xgboost" if HAS_XGBOOST else "random_forest"
    )
    
    # Initialize feedback loop
    print("🏗️ Initializing feedback loop...")
    feedback_loop = FeedbackLoop(config)
    
    # Run single cycle
    print("🚀 Running feedback cycle...")
    results = feedback_loop.run_feedback_cycle()
    
    print("\n📊 Results Summary:")
    print(f"  • Success: {results.get('success', False)}")
    print(f"  • Drift detected: {results.get('drift_detected', False)}")
    print(f"  • Model retrained: {results.get('retrained', False)}")
    print(f"  • Outcome samples: {results.get('outcome_samples', 0)}")
    
    if results.get('performance_improvement'):
        print("  • Performance improvements:")
        for metric, improvement in results['performance_improvement'].items():
            print(f"    - {metric}: {improvement:+.3f}")
    
    print("\n✅ Demo completed successfully!")
    print("🕐 To run scheduler: feedback_loop.schedule_jobs() and feedback_loop.run_scheduler()")
