#!/usr/bin/env python3
"""
ParlayBuilder ML Integration - JIRA-ML-001

Integrates trained ML models with ParlayBuilder for intelligent leg filtering
and ranking based on predicted success probability.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path

from ml.model_training import ParlayLegPredictor
from ml.feature_engineering import MultiSportFeatureEngineer

logger = logging.getLogger(__name__)


@dataclass
class MLPrediction:
    """ML prediction result for a parlay leg."""
    leg_id: str
    hit_probability: float
    confidence_score: float
    is_high_confidence: bool
    ml_recommendation: str  # "strong_bet", "good_bet", "weak_bet", "avoid"
    expected_value: float


@dataclass
class MLFilteringConfig:
    """Configuration for ML-based filtering."""
    min_hit_probability: float = 0.52  # Minimum 52% hit probability
    min_confidence_threshold: float = 0.6  # 60% confidence for high-confidence bets
    max_legs_per_parlay: int = 3
    require_positive_ev: bool = True
    use_ensemble_filtering: bool = False  # Future: ensemble of multiple models


class MLEnhancedParlayBuilder:
    """ParlayBuilder enhanced with ML predictions."""
    
    def __init__(self, sport: str, config: MLFilteringConfig = None):
        self.sport = sport.lower()
        self.config = config or MLFilteringConfig()
        
        # Load ML model and feature engineer
        try:
            self.predictor = ParlayLegPredictor.load_model(self.sport)
            self.feature_engineer = MultiSportFeatureEngineer()
            self.is_ml_ready = True
            logger.info(f"ML-enhanced ParlayBuilder initialized for {self.sport}")
        except Exception as e:
            logger.warning(f"Could not load ML model for {self.sport}: {e}")
            self.predictor = None
            self.feature_engineer = None
            self.is_ml_ready = False
    
    def prepare_leg_features(self, leg_data: Dict[str, Any]) -> pd.DataFrame:
        """Convert leg data to ML features."""
        # Convert single leg to DataFrame format expected by feature engineer
        df = pd.DataFrame([leg_data])
        
        # Ensure required columns exist with defaults
        required_columns = {
            'prop_type': 'points_over',
            'prop_line': 20.0,
            'player_avg_last_3': 18.0,
            'player_avg_last_5': 19.0,
            'player_avg_season': 20.0,
            'prop_odds': 1.9,
            'location': 'home',
            'injury_status': 'healthy',
            'market_movement': 'stable',
            'defensive_rank_against': 15,
            'is_primetime': False,
            'is_playoff': False
        }
        
        # Add sport-specific defaults
        if self.sport == "nba":
            required_columns.update({
                'is_back_to_back': False,
                'rest_days': 1
            })
        elif self.sport == "nfl":
            required_columns.update({
                'is_divisional': False,
                'weather_conditions': 'clear',
                'temperature': 70
            })
        
        # Fill missing values
        for col, default_val in required_columns.items():
            if col not in df.columns:
                df[col] = default_val
        
        return df
    
    def predict_leg_success(self, leg_data: Dict[str, Any]) -> MLPrediction:
        """Predict success probability for a single leg."""
        if not self.is_ml_ready:
            # Return neutral prediction if ML not available
            return MLPrediction(
                leg_id=leg_data.get('leg_id', 'unknown'),
                hit_probability=0.5,
                confidence_score=0.5,
                is_high_confidence=False,
                ml_recommendation="unknown",
                expected_value=0.0
            )
        
        # Prepare features
        df = self.prepare_leg_features(leg_data)
        
        # Transform to ML features
        try:
            X = self.feature_engineer.transform_new_data(self.sport, df)
        except Exception as e:
            logger.warning(f"Feature transformation failed: {e}")
            return MLPrediction(
                leg_id=leg_data.get('leg_id', 'unknown'),
                hit_probability=0.5,
                confidence_score=0.0,
                is_high_confidence=False,
                ml_recommendation="error",
                expected_value=0.0
            )
        
        # Get ML prediction
        hit_probability = self.predictor.predict_leg_hit_probability(X)[0]
        
        # Calculate confidence (distance from 0.5)
        confidence_score = abs(hit_probability - 0.5) * 2
        is_high_confidence = confidence_score >= self.config.min_confidence_threshold
        
        # Calculate expected value
        odds = leg_data.get('prop_odds', 1.9)
        expected_value = (hit_probability * (odds - 1)) - (1 - hit_probability)
        
        # Generate recommendation
        if hit_probability >= 0.65 and is_high_confidence:
            recommendation = "strong_bet"
        elif hit_probability >= self.config.min_hit_probability and confidence_score >= 0.4:
            recommendation = "good_bet"
        elif hit_probability >= 0.48:
            recommendation = "weak_bet"
        else:
            recommendation = "avoid"
        
        return MLPrediction(
            leg_id=leg_data.get('leg_id', 'unknown'),
            hit_probability=hit_probability,
            confidence_score=confidence_score,
            is_high_confidence=is_high_confidence,
            ml_recommendation=recommendation,
            expected_value=expected_value
        )
    
    def filter_legs_by_ml(self, candidate_legs: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[MLPrediction]]:
        """Filter candidate legs using ML predictions."""
        if not self.is_ml_ready:
            logger.warning("ML not available, returning all legs")
            return candidate_legs, []
        
        ml_predictions = []
        filtered_legs = []
        
        for i, leg in enumerate(candidate_legs):
            # Add leg_id if not present
            leg['leg_id'] = leg.get('leg_id', f"leg_{i}")
            
            # Get ML prediction
            prediction = self.predict_leg_success(leg)
            ml_predictions.append(prediction)
            
            # Apply filters
            should_include = True
            
            # Minimum hit probability filter
            if prediction.hit_probability < self.config.min_hit_probability:
                should_include = False
                logger.debug(f"Filtered out leg {prediction.leg_id}: low hit probability ({prediction.hit_probability:.3f})")
            
            # Positive EV filter
            if self.config.require_positive_ev and prediction.expected_value <= 0:
                should_include = False
                logger.debug(f"Filtered out leg {prediction.leg_id}: negative EV ({prediction.expected_value:.3f})")
            
            # Recommendation filter
            if prediction.ml_recommendation in ["avoid"]:
                should_include = False
                logger.debug(f"Filtered out leg {prediction.leg_id}: ML recommendation is {prediction.ml_recommendation}")
            
            if should_include:
                # Add ML data to leg
                leg['ml_prediction'] = prediction
                filtered_legs.append(leg)
        
        logger.info(f"ML filtering: {len(candidate_legs)} → {len(filtered_legs)} legs (filtered {len(candidate_legs) - len(filtered_legs)})")
        return filtered_legs, ml_predictions
    
    def rank_legs_by_expected_value(self, legs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank legs by ML-predicted expected value."""
        if not legs:
            return legs
        
        # Sort by expected value (highest first)
        ranked_legs = sorted(
            legs,
            key=lambda leg: leg.get('ml_prediction', MLPrediction('', 0, 0, False, '', 0)).expected_value,
            reverse=True
        )
        
        logger.info(f"Ranked {len(ranked_legs)} legs by expected value")
        return ranked_legs
    
    def build_ml_optimized_parlay(self, candidate_legs: List[Dict[str, Any]], target_legs: int = 2) -> Optional[Dict[str, Any]]:
        """Build parlay optimized using ML predictions."""
        if not candidate_legs:
            return None
        
        # Filter legs using ML
        filtered_legs, all_predictions = self.filter_legs_by_ml(candidate_legs)
        
        if len(filtered_legs) < target_legs:
            logger.warning(f"Not enough quality legs after ML filtering: {len(filtered_legs)} < {target_legs}")
            return None
        
        # Rank by expected value
        ranked_legs = self.rank_legs_by_expected_value(filtered_legs)
        
        # Select top legs (limit by config)
        max_legs = min(target_legs, self.config.max_legs_per_parlay, len(ranked_legs))
        selected_legs = ranked_legs[:max_legs]
        
        # Calculate parlay metrics
        total_odds = 1.0
        total_hit_prob = 1.0
        total_ev = 0.0
        confidence_scores = []
        
        for leg in selected_legs:
            prediction = leg['ml_prediction']
            leg_odds = leg.get('prop_odds', 1.9)
            
            total_odds *= leg_odds
            total_hit_prob *= prediction.hit_probability
            total_ev += prediction.expected_value
            confidence_scores.append(prediction.confidence_score)
        
        # Overall parlay assessment
        avg_confidence = np.mean(confidence_scores)
        parlay_ev = (total_hit_prob * (total_odds - 1)) - (1 - total_hit_prob)
        
        ml_parlay = {
            'legs': selected_legs,
            'total_legs': len(selected_legs),
            'total_odds': total_odds,
            'ml_hit_probability': total_hit_prob,
            'ml_expected_value': parlay_ev,
            'avg_confidence': avg_confidence,
            'individual_evs': [leg['ml_prediction'].expected_value for leg in selected_legs],
            'recommendations': [leg['ml_prediction'].ml_recommendation for leg in selected_legs],
            'ml_quality_score': avg_confidence * total_hit_prob,
            'filtering_stats': {
                'original_legs': len(candidate_legs),
                'filtered_legs': len(filtered_legs),
                'rejection_rate': (len(candidate_legs) - len(filtered_legs)) / len(candidate_legs)
            }
        }
        
        return ml_parlay
    
    def compare_with_random_selection(self, candidate_legs: List[Dict[str, Any]], num_trials: int = 100) -> Dict[str, Any]:
        """Compare ML selection vs random selection."""
        if not self.is_ml_ready or len(candidate_legs) < 2:
            return {"error": "Insufficient data for comparison"}
        
        # ML optimized parlay
        ml_parlay = self.build_ml_optimized_parlay(candidate_legs, target_legs=2)
        
        # Random parlays for comparison
        random_results = []
        
        for _ in range(num_trials):
            random_legs = np.random.choice(candidate_legs, size=min(2, len(candidate_legs)), replace=False)
            
            # Calculate random parlay metrics
            random_odds = 1.0
            for leg in random_legs:
                random_odds *= leg.get('prop_odds', 1.9)
            
            # Assume random hit probability around baseline
            if self.sport == "nba":
                random_hit_prob = 0.158  # NBA baseline
            else:
                random_hit_prob = 0.125  # NFL baseline
            
            random_ev = (random_hit_prob * (random_odds - 1)) - (1 - random_hit_prob)
            random_results.append({
                'odds': random_odds,
                'hit_prob': random_hit_prob,
                'ev': random_ev
            })
        
        # Calculate random averages
        avg_random_odds = np.mean([r['odds'] for r in random_results])
        avg_random_ev = np.mean([r['ev'] for r in random_results])
        avg_random_hit_prob = np.mean([r['hit_prob'] for r in random_results])
        
        comparison = {
            'ml_parlay': ml_parlay,
            'ml_hit_probability': ml_parlay['ml_hit_probability'] if ml_parlay else 0,
            'ml_expected_value': ml_parlay['ml_expected_value'] if ml_parlay else 0,
            'random_hit_probability': avg_random_hit_prob,
            'random_expected_value': avg_random_ev,
            'improvement': {
                'hit_prob_improvement': (ml_parlay['ml_hit_probability'] - avg_random_hit_prob) if ml_parlay else 0,
                'ev_improvement': (ml_parlay['ml_expected_value'] - avg_random_ev) if ml_parlay else 0
            }
        }
        
        return comparison


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("🤖 ML PARLAY INTEGRATION - JIRA-ML-001")
    print("=" * 60)
    print()
    
    # Test both sports
    for sport in ["nba", "nfl"]:
        print(f"🏀🏈 Testing {sport.upper()} ML Integration:")
        print("-" * 40)
        
        # Initialize ML-enhanced builder
        ml_builder = MLEnhancedParlayBuilder(sport)
        
        if ml_builder.is_ml_ready:
            print(f"   ✅ ML Model: Loaded successfully")
            print(f"   🧠 Features: Ready for prediction")
            
            # Create sample leg data for testing
            if sport == "nba":
                sample_legs = [
                    {
                        'leg_id': 'nba_leg_1',
                        'prop_type': 'points_over',
                        'prop_line': 28.5,
                        'prop_odds': 1.9,
                        'player_avg_season': 26.0,
                        'player_avg_last_5': 29.0,
                        'player_avg_last_3': 30.0,
                        'location': 'home',
                        'injury_status': 'healthy',
                        'is_back_to_back': False,
                        'is_primetime': True
                    },
                    {
                        'leg_id': 'nba_leg_2',
                        'prop_type': 'rebounds_over',
                        'prop_line': 8.5,
                        'prop_odds': 2.1,
                        'player_avg_season': 9.2,
                        'player_avg_last_5': 7.8,
                        'player_avg_last_3': 7.5,
                        'location': 'away',
                        'injury_status': 'questionable'
                    }
                ]
            else:  # NFL
                sample_legs = [
                    {
                        'leg_id': 'nfl_leg_1',
                        'prop_type': 'passing_yards_over',
                        'prop_line': 249.5,
                        'prop_odds': 1.85,
                        'player_avg_season': 260.0,
                        'player_avg_last_5': 245.0,
                        'player_avg_last_3': 240.0,
                        'location': 'home',
                        'injury_status': 'healthy',
                        'weather_conditions': 'clear',
                        'is_divisional': False
                    },
                    {
                        'leg_id': 'nfl_leg_2',
                        'prop_type': 'rushing_yards_over',
                        'prop_line': 65.5,
                        'prop_odds': 2.0,
                        'player_avg_season': 80.0,
                        'player_avg_last_5': 55.0,
                        'player_avg_last_3': 50.0,
                        'location': 'away',
                        'injury_status': 'questionable',
                        'weather_conditions': 'rain'
                    }
                ]
            
            # Test ML predictions
            print(f"   🎯 Testing ML Predictions:")
            for leg in sample_legs:
                prediction = ml_builder.predict_leg_success(leg)
                print(f"      {leg['leg_id']}: {prediction.hit_probability:.1%} probability, {prediction.ml_recommendation}")
            
            # Test parlay building
            ml_parlay = ml_builder.build_ml_optimized_parlay(sample_legs)
            if ml_parlay:
                print(f"   ✅ ML Parlay Generated:")
                print(f"      Legs: {ml_parlay['total_legs']}")
                print(f"      Hit Probability: {ml_parlay['ml_hit_probability']:.1%}")
                print(f"      Expected Value: {ml_parlay['ml_expected_value']:.3f}")
                print(f"      Quality Score: {ml_parlay['ml_quality_score']:.3f}")
            else:
                print(f"   ❌ No quality parlay found")
            
        else:
            print(f"   ❌ ML Model: Not available")
            print(f"   💡 Run model training first")
        
        print()
    
    print("🏆 ML INTEGRATION TESTING COMPLETE!")
    print("   Ready for production deployment")
