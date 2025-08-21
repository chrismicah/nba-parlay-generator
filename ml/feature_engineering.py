#!/usr/bin/env python3
"""
Feature Engineering Pipeline - JIRA-ML-001

Transforms raw parlay leg data into ML-ready features for both NBA and NFL.
Implements shared feature engineering logic with sport-specific adaptations.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional
from sklearn.preprocessing import StandardScaler, LabelEncoder, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
import pickle
from pathlib import Path

logger = logging.getLogger(__name__)


class SportFeatureEngineer:
    """Feature engineering pipeline for sports betting data."""
    
    def __init__(self, sport: str):
        self.sport = sport.lower()
        self.scaler = StandardScaler()
        self.encoders = {}
        self.feature_columns = []
        self.is_fitted = False
        
        # Sport-specific configurations
        self.sport_configs = {
            "nba": {
                "numerical_features": [
                    "prop_line", "player_avg_last_3", "player_avg_last_5", 
                    "player_avg_season", "line_delta", "prop_odds",
                    "defensive_rank_against", "rest_days"
                ],
                "categorical_features": [
                    "prop_type", "location", "injury_status", "market_movement"
                ],
                "boolean_features": [
                    "is_primetime", "is_back_to_back", "is_playoff"
                ],
                "derived_features": [
                    "form_trend", "line_value_ratio", "fatigue_factor", "matchup_difficulty"
                ]
            },
            "nfl": {
                "numerical_features": [
                    "prop_line", "player_avg_last_3", "player_avg_last_5",
                    "player_avg_season", "line_delta", "prop_odds", 
                    "defensive_rank_against", "temperature"
                ],
                "categorical_features": [
                    "prop_type", "location", "injury_status", "weather_conditions", "market_movement"
                ],
                "boolean_features": [
                    "is_primetime", "is_divisional", "is_playoff"
                ],
                "derived_features": [
                    "form_trend", "line_value_ratio", "weather_impact", "divisional_factor"
                ]
            }
        }
    
    def create_derived_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create sport-specific derived features."""
        df = df.copy()
        
        # Universal derived features
        df['form_trend'] = (df['player_avg_last_3'] - df['player_avg_last_5']) / df['player_avg_season']
        df['line_value_ratio'] = df['prop_line'] / df['player_avg_season']
        df['recent_vs_season'] = (df['player_avg_last_5'] - df['player_avg_season']) / df['player_avg_season']
        df['consistency_score'] = 1.0 / (1.0 + abs(df['player_avg_last_3'] - df['player_avg_last_5']))
        
        # Line difficulty categories
        df['line_difficulty'] = pd.cut(
            df['line_delta'], 
            bins=[-float('inf'), -10, -2, 2, 10, float('inf')],
            labels=['very_easy', 'easy', 'fair', 'hard', 'very_hard']
        )
        
        if self.sport == "nba":
            # NBA-specific features
            df['fatigue_factor'] = df['is_back_to_back'].astype(int) * 0.8 + (1 - df['rest_days'] / 2.0)
            df['matchup_difficulty'] = df['defensive_rank_against'] / 30.0  # Normalize to 0-1
            df['primetime_home'] = df['is_primetime'] & (df['location'] == 'home')
            
            # Performance vs expectation
            df['overperforming'] = (df['player_avg_last_5'] > df['player_avg_season']).astype(int)
            
        elif self.sport == "nfl":
            # NFL-specific features
            weather_impact_map = {'clear': 0, 'rain': -0.1, 'wind': -0.05, 'snow': -0.15, 'indoor': 0}
            df['weather_impact'] = df['weather_conditions'].map(weather_impact_map).fillna(0)
            
            df['divisional_factor'] = df['is_divisional'].astype(float) * 0.1  # Divisional games are tighter
            df['cold_weather'] = ((df['temperature'].fillna(70) < 40) & (df['weather_conditions'] != 'indoor')).astype(int)
            
            # Position-based adjustments
            df['is_qb_prop'] = df['prop_type'].str.contains('passing').astype(int)
            df['is_skill_position'] = df['prop_type'].str.contains('receiving|rushing').astype(int)
            
            # Temperature impact on performance (NFL only)
            df['temperature_factor'] = np.where(
                df['temperature'].notna(),
                np.clip((df['temperature'] - 40) / 40, -0.2, 0.1),  # Optimal around 70-80F
                0
            )
        
        # Injury impact scoring
        injury_impact_map = {'healthy': 0, 'questionable': -0.15, 'doubtful': -0.35}
        df['injury_impact'] = df['injury_status'].map(injury_impact_map)
        
        # Market movement impact
        movement_impact_map = {'up': 0.05, 'stable': 0, 'down': -0.05}
        df['movement_impact'] = df['market_movement'].map(movement_impact_map)
        
        # Odds value assessment
        df['implied_probability'] = 1.0 / df['prop_odds']
        df['odds_value'] = np.where(df['implied_probability'] < 0.5, 'good_value', 'poor_value')
        
        logger.info(f"Created {len([c for c in df.columns if c not in self.sport_configs[self.sport]['numerical_features'] + self.sport_configs[self.sport]['categorical_features'] + self.sport_configs[self.sport]['boolean_features']])} derived features for {self.sport}")
        
        return df
    
    def encode_features(self, df: pd.DataFrame, fit: bool = True) -> pd.DataFrame:
        """Encode categorical and boolean features."""
        df = df.copy()
        config = self.sport_configs[self.sport]
        
        # Handle boolean features
        for col in config['boolean_features']:
            if col in df.columns:
                df[col] = df[col].astype(int)
        
        # Handle categorical features with one-hot encoding
        categorical_cols = [col for col in config['categorical_features'] if col in df.columns]
        categorical_cols.extend(['line_difficulty', 'odds_value'])  # Add derived categorical features
        
        if fit:
            # Fit encoders
            self.categorical_encoder = OneHotEncoder(drop='first', sparse_output=False, handle_unknown='ignore')
            encoded_features = self.categorical_encoder.fit_transform(df[categorical_cols])
            feature_names = self.categorical_encoder.get_feature_names_out(categorical_cols)
        else:
            # Transform using fitted encoders
            encoded_features = self.categorical_encoder.transform(df[categorical_cols])
            feature_names = self.categorical_encoder.get_feature_names_out(categorical_cols)
        
        # Create DataFrame with encoded features
        encoded_df = pd.DataFrame(encoded_features, columns=feature_names, index=df.index)
        
        # Drop original categorical columns and concatenate encoded ones
        df = df.drop(columns=categorical_cols)
        df = pd.concat([df, encoded_df], axis=1)
        
        return df
    
    def scale_features(self, df: pd.DataFrame, fit: bool = True) -> pd.DataFrame:
        """Scale numerical features."""
        df = df.copy()
        config = self.sport_configs[self.sport]
        
        # Get numerical columns (including derived numerical features)
        numerical_cols = [col for col in df.columns if df[col].dtype in ['int64', 'float64']]
        
        # Exclude target variable and IDs
        exclude_cols = ['actual_result', 'actual_value', 'player_id']
        numerical_cols = [col for col in numerical_cols if col not in exclude_cols]
        
        if fit:
            df[numerical_cols] = self.scaler.fit_transform(df[numerical_cols])
        else:
            df[numerical_cols] = self.scaler.transform(df[numerical_cols])
        
        return df
    
    def engineer_features(self, df: pd.DataFrame, fit: bool = True) -> Tuple[pd.DataFrame, List[str]]:
        """Complete feature engineering pipeline."""
        logger.info(f"Engineering features for {self.sport} data: {len(df)} examples")
        
        # Create derived features
        df = self.create_derived_features(df)
        
        # Encode categorical features
        df = self.encode_features(df, fit=fit)
        
        # Scale numerical features
        df = self.scale_features(df, fit=fit)
        
        # Get final feature columns (exclude target and metadata)
        exclude_cols = [
            'actual_result', 'actual_value', 'player_id', 'player_name', 
            'team', 'opponent', 'game_date'
        ]
        feature_cols = [col for col in df.columns if col not in exclude_cols]
        
        if fit:
            self.feature_columns = feature_cols
            self.is_fitted = True
        
        logger.info(f"Final feature count for {self.sport}: {len(feature_cols)}")
        return df, feature_cols
    
    def save_pipeline(self, filepath: str):
        """Save the fitted feature engineering pipeline."""
        if not self.is_fitted:
            raise ValueError("Pipeline must be fitted before saving")
        
        pipeline_data = {
            'sport': self.sport,
            'scaler': self.scaler,
            'categorical_encoder': self.categorical_encoder,
            'feature_columns': self.feature_columns,
            'sport_configs': self.sport_configs
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(pipeline_data, f)
        
        logger.info(f"Saved {self.sport} feature pipeline to {filepath}")
    
    @classmethod
    def load_pipeline(cls, filepath: str) -> 'SportFeatureEngineer':
        """Load a fitted feature engineering pipeline."""
        with open(filepath, 'rb') as f:
            pipeline_data = pickle.load(f)
        
        engineer = cls(pipeline_data['sport'])
        engineer.scaler = pipeline_data['scaler']
        engineer.categorical_encoder = pipeline_data['categorical_encoder']
        engineer.feature_columns = pipeline_data['feature_columns']
        engineer.sport_configs = pipeline_data['sport_configs']
        engineer.is_fitted = True
        
        logger.info(f"Loaded {engineer.sport} feature pipeline from {filepath}")
        return engineer


class MultiSportFeatureEngineer:
    """Manages feature engineering for multiple sports."""
    
    def __init__(self):
        self.engineers = {}
        self.output_dir = Path("models/feature_pipelines")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def prepare_sport_data(self, sport: str, csv_path: str) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """Prepare features and targets for a specific sport."""
        logger.info(f"Preparing {sport} data from {csv_path}")
        
        # Load data
        df = pd.read_csv(csv_path)
        
        # Initialize feature engineer
        engineer = SportFeatureEngineer(sport)
        
        # Engineer features
        df_engineered, feature_cols = engineer.engineer_features(df, fit=True)
        
        # Extract features and targets
        X = df_engineered[feature_cols].values
        y = df_engineered['actual_result'].values
        
        # Save the fitted pipeline
        pipeline_path = self.output_dir / f"{sport}_feature_pipeline.pkl"
        engineer.save_pipeline(str(pipeline_path))
        
        # Store engineer
        self.engineers[sport] = engineer
        
        logger.info(f"Prepared {sport} data: {X.shape[0]} examples, {X.shape[1]} features")
        return X, y, feature_cols
    
    def transform_new_data(self, sport: str, df: pd.DataFrame) -> np.ndarray:
        """Transform new data using fitted pipeline."""
        if sport not in self.engineers:
            # Try to load pipeline
            pipeline_path = self.output_dir / f"{sport}_feature_pipeline.pkl"
            if pipeline_path.exists():
                self.engineers[sport] = SportFeatureEngineer.load_pipeline(str(pipeline_path))
            else:
                raise ValueError(f"No fitted pipeline found for {sport}")
        
        engineer = self.engineers[sport]
        df_engineered, _ = engineer.engineer_features(df, fit=False)
        
        return df_engineered[engineer.feature_columns].values
    
    def get_feature_importance_names(self, sport: str) -> List[str]:
        """Get feature names for importance analysis."""
        if sport not in self.engineers:
            pipeline_path = self.output_dir / f"{sport}_feature_pipeline.pkl"
            self.engineers[sport] = SportFeatureEngineer.load_pipeline(str(pipeline_path))
        
        return self.engineers[sport].feature_columns


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("🧠 FEATURE ENGINEERING PIPELINE - JIRA-ML-001")
    print("=" * 60)
    print()
    
    # Initialize multi-sport feature engineer
    multi_engineer = MultiSportFeatureEngineer()
    
    # Process both sports
    for sport in ["nba", "nfl"]:
        csv_path = f"data/ml_training/{sport}_parlay_training_data.csv"
        
        try:
            X, y, feature_cols = multi_engineer.prepare_sport_data(sport, csv_path)
            
            print(f"📊 {sport.upper()} FEATURE ENGINEERING:")
            print(f"   Examples: {X.shape[0]:,}")
            print(f"   Features: {X.shape[1]:,}")
            print(f"   Hit Rate: {y.mean():.1%}")
            print(f"   Feature Pipeline: Saved to models/feature_pipelines/{sport}_feature_pipeline.pkl")
            print()
            
        except FileNotFoundError:
            print(f"❌ {sport.upper()} dataset not found at {csv_path}")
            print("   Run dataset_preparation.py first")
            print()
    
    print("✅ FEATURE ENGINEERING COMPLETE!")
    print("   Next: Model training with XGBoost")
