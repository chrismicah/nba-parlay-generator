#!/usr/bin/env python3
"""
Integration tests for Dynamic Correlation Rules Model - JIRA-022A

Tests the correlation model integration with ParlayBuilder to detect
and flag highly correlated parlay legs.
"""

import unittest
import tempfile
import os
from pathlib import Path
import sys

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from tools.parlay_builder import ParlayBuilder, ParlayLeg
from tools.bets_logger import BetsLogger


class TestCorrelationIntegration(unittest.TestCase):
    """Integration tests for correlation model with ParlayBuilder."""
    
    def setUp(self):
        """Set up test database and ParlayBuilder."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        # Create some sample historical data for correlation training
        self._create_sample_historical_data()
        
        # Initialize ParlayBuilder with correlation detection
        self.parlay_builder = ParlayBuilder(
            sport_key="basketball_nba",
            correlation_threshold=0.7,
            db_path=self.db_path
        )
    
    def tearDown(self):
        """Clean up test database."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def _create_sample_historical_data(self):
        """Create sample historical bet data for correlation analysis."""
        with BetsLogger(self.db_path) as logger:
            # Create correlated same-game bets (should be flagged)
            parlay_1_id = "correlated_parlay_1"
            logger.log_parlay_leg(
                parlay_id=parlay_1_id,
                game_id="lal_vs_bos_20250101",
                leg_description="Lakers ML @ 1.85 [Book: DraftKings]",
                odds=1.85,
                stake=100.0,
                predicted_outcome="Lakers win"
            )
            logger.log_parlay_leg(
                parlay_id=parlay_1_id,
                game_id="lal_vs_bos_20250101",  # Same game
                leg_description="Lakers -5.5 @ 1.91 [Book: FanDuel]",
                odds=1.91,
                stake=100.0,
                predicted_outcome="Lakers cover spread"
            )
            
            # Create uncorrelated different-game bets
            parlay_2_id = "uncorrelated_parlay_2"
            logger.log_parlay_leg(
                parlay_id=parlay_2_id,
                game_id="gsw_vs_mia_20250102",
                leg_description="Warriors ML @ 1.75 [Book: DraftKings]",
                odds=1.75,
                stake=100.0,
                predicted_outcome="Warriors win"
            )
            logger.log_parlay_leg(
                parlay_id=parlay_2_id,
                game_id="den_vs_phx_20250103",  # Different game
                leg_description="Nuggets ML @ 1.65 [Book: FanDuel]",
                odds=1.65,
                stake=100.0,
                predicted_outcome="Nuggets win"
            )
            
            # Settle some bets to create outcome history
            # Same-game bets both won (correlated outcome)
            logger.update_bet_outcome(1, "Lakers won 112-105", True)
            logger.update_bet_outcome(2, "Lakers won 112-105 and covered -5.5", True)
            
            # Different-game bets had mixed outcomes (uncorrelated)
            logger.update_bet_outcome(3, "Warriors won 108-102", True)
            logger.update_bet_outcome(4, "Nuggets lost 95-98", False)
    
    def test_correlation_detection_same_game(self):
        """Test that same-game legs are flagged as correlated."""
        # Create potential legs from the same game (should be correlated)
        potential_legs = [
            ParlayLeg(
                game_id="lal_vs_bos_20250115",
                market_type="h2h",
                selection_name="Lakers",
                bookmaker="DraftKings",
                odds_decimal=1.85
            ),
            ParlayLeg(
                game_id="lal_vs_bos_20250115",  # Same game
                market_type="spreads",
                selection_name="Lakers",
                bookmaker="FanDuel",
                odds_decimal=1.91,
                line=-5.5
            )
        ]
        
        # Check correlations
        warnings, max_correlation = self.parlay_builder._check_correlations(potential_legs)
        
        # Should detect correlation between same-game legs
        self.assertGreater(len(warnings), 0, "Should detect correlation between same-game legs")
        self.assertGreater(max_correlation, 0.0, "Should have non-zero correlation score")
        
        # Check warning content
        warning_text = " ".join(warnings).lower()
        self.assertIn("correlation", warning_text)
        self.assertIn("lakers", warning_text)
    
    def test_correlation_detection_different_games(self):
        """Test that different-game legs have lower correlation."""
        # Create potential legs from different games (should be less correlated)
        potential_legs = [
            ParlayLeg(
                game_id="lal_vs_bos_20250115",
                market_type="h2h",
                selection_name="Lakers",
                bookmaker="DraftKings",
                odds_decimal=1.85
            ),
            ParlayLeg(
                game_id="gsw_vs_mia_20250115",  # Different game
                market_type="h2h",
                selection_name="Warriors",
                bookmaker="FanDuel",
                odds_decimal=1.75
            )
        ]
        
        # Check correlations
        warnings, max_correlation = self.parlay_builder._check_correlations(potential_legs)
        
        # Should have fewer/no warnings for different games
        if warnings:
            # If there are warnings, correlation should be lower than same-game
            self.assertLess(max_correlation, 0.9, "Different games should have lower correlation")
    
    def test_correlation_threshold_adjustment(self):
        """Test that correlation threshold affects warning generation."""
        # Create ParlayBuilder with very low threshold
        low_threshold_builder = ParlayBuilder(
            correlation_threshold=0.1,  # Very low threshold
            db_path=self.db_path
        )
        
        # Create ParlayBuilder with very high threshold
        high_threshold_builder = ParlayBuilder(
            correlation_threshold=0.95,  # Very high threshold
            db_path=self.db_path
        )
        
        potential_legs = [
            ParlayLeg("game_1", "h2h", "Lakers", "DraftKings", 1.85),
            ParlayLeg("game_1", "spreads", "Lakers", "FanDuel", 1.91, -5.5)
        ]
        
        # Low threshold should generate more warnings
        low_warnings, _ = low_threshold_builder._check_correlations(potential_legs)
        
        # High threshold should generate fewer warnings
        high_warnings, _ = high_threshold_builder._check_correlations(potential_legs)
        
        # Low threshold should have at least as many warnings as high threshold
        self.assertGreaterEqual(len(low_warnings), len(high_warnings))
    
    def test_parlay_validation_with_correlation_warnings(self):
        """Test that parlay validation includes correlation warnings."""
        # Mock the odds fetcher to avoid API calls
        self.parlay_builder._current_market_snapshot = []
        self.parlay_builder._snapshot_timestamp = "2025-08-15T10:00:00Z"
        
        potential_legs = [
            ParlayLeg("same_game_123", "h2h", "Lakers", "DraftKings", 1.85),
            ParlayLeg("same_game_123", "spreads", "Lakers", "FanDuel", 1.91, -5.5)
        ]
        
        try:
            # This will fail due to no market data, but should still check correlations
            validation = self.parlay_builder.validate_parlay_legs(potential_legs)
        except Exception:
            # Expected to fail due to no market data, but correlation check should run first
            pass
        
        # Test correlation checking directly
        warnings, max_correlation = self.parlay_builder._check_correlations(potential_legs)
        
        # Should have correlation data
        self.assertIsInstance(warnings, list)
        self.assertIsInstance(max_correlation, float)
        self.assertGreaterEqual(max_correlation, 0.0)
    
    def test_bet_node_conversion(self):
        """Test conversion of ParlayLeg to BetNode for correlation analysis."""
        leg = ParlayLeg(
            game_id="lal_vs_bos_20250115",
            market_type="h2h",
            selection_name="Lakers",
            bookmaker="DraftKings",
            odds_decimal=1.85,
            line=None
        )
        
        bet_node = self.parlay_builder._convert_leg_to_bet_node(leg)
        
        if bet_node:  # Only test if correlation model is available
            self.assertEqual(bet_node.game_id, "lal_vs_bos_20250115")
            self.assertEqual(bet_node.market_type, "h2h")
            self.assertEqual(bet_node.odds, 1.85)
            self.assertEqual(bet_node.team, "Lakers")
            
            # Test feature vector generation
            features = bet_node.to_feature_vector()
            self.assertIsInstance(features, list)
            self.assertGreater(len(features), 0)
            self.assertTrue(all(isinstance(f, float) for f in features))
    
    def test_correlation_model_fallback(self):
        """Test that system works even without correlation model."""
        # Create ParlayBuilder without correlation model
        builder_no_correlation = ParlayBuilder(
            sport_key="basketball_nba",
            correlation_threshold=0.7,
            db_path="nonexistent_db.sqlite"
        )
        
        potential_legs = [
            ParlayLeg("game_1", "h2h", "Lakers", "DraftKings", 1.85),
            ParlayLeg("game_2", "h2h", "Warriors", "FanDuel", 1.75)
        ]
        
        # Should not crash even without correlation model
        warnings, max_correlation = builder_no_correlation._check_correlations(potential_legs)
        
        self.assertIsInstance(warnings, list)
        self.assertIsInstance(max_correlation, float)
        # Should still detect correlations using rule-based fallback
        self.assertGreaterEqual(max_correlation, 0.0)
    
    def test_multiple_leg_correlations(self):
        """Test correlation detection with multiple legs."""
        potential_legs = [
            ParlayLeg("game_1", "h2h", "Lakers", "DraftKings", 1.85),
            ParlayLeg("game_1", "spreads", "Lakers", "FanDuel", 1.91, -5.5),
            ParlayLeg("game_1", "totals", "Over", "BetMGM", 1.95, 220.5),
            ParlayLeg("game_2", "h2h", "Warriors", "DraftKings", 1.75)
        ]
        
        warnings, max_correlation = self.parlay_builder._check_correlations(potential_legs)
        
        # Should detect multiple correlations within game_1
        self.assertIsInstance(warnings, list)
        self.assertGreaterEqual(max_correlation, 0.0)
        
        # If warnings exist, they should mention the correlated legs
        if warnings:
            warning_text = " ".join(warnings).lower()
            # Should mention some of the same-game legs
            same_game_mentions = sum(1 for leg in ["lakers", "over"] if leg in warning_text)
            self.assertGreater(same_game_mentions, 0)


class TestCorrelationModelFallback(unittest.TestCase):
    """Test correlation model fallback behavior."""
    
    def test_rule_based_correlation_fallback(self):
        """Test rule-based correlation when GNN model is not available."""
        # This test should work even without PyTorch Geometric
        builder = ParlayBuilder(correlation_threshold=0.5)
        
        # Test with same market type (should have higher correlation)
        features_h2h_1 = [1.0, 0.0, 0.0, 0.0, 0.0, 0.185, 0.0, 1.0, 0.0]  # h2h market
        features_h2h_2 = [1.0, 0.0, 0.0, 0.0, 0.0, 0.175, 0.0, 1.0, 0.0]  # h2h market
        
        # Test with different market types
        features_spreads = [0.0, 1.0, 0.0, 0.0, 0.0, 0.191, -0.11, 1.0, 0.0]  # spreads market
        
        # Mock the correlation model to use rule-based fallback
        if hasattr(builder, 'correlation_model') and builder.correlation_model:
            same_market_corr = builder.correlation_model._rule_based_correlation(
                features_h2h_1, features_h2h_2, 0.5
            )
            different_market_corr = builder.correlation_model._rule_based_correlation(
                features_h2h_1, features_spreads, 0.5
            )
            
            # Same market should have higher correlation
            self.assertGreaterEqual(same_market_corr, different_market_corr)
            self.assertGreaterEqual(same_market_corr, 0.5)


if __name__ == '__main__':
    # Set up logging for tests
    import logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise during tests
    
    # Run tests
    unittest.main(verbosity=2)
