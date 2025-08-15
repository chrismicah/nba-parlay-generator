#!/usr/bin/env python3
"""
Comprehensive tests for ParlayBuilder - JIRA-021

Tests the ParlayBuilder tool's ability to validate parlay legs against
current market availability, including both active season and off-season scenarios.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from datetime import datetime, timezone

# Add tools directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'tools'))

from parlay_builder import (
    ParlayBuilder, ParlayLeg, ValidationResult, ParlayValidation,
    ParlayBuilderError, create_sample_legs
)
from odds_fetcher_tool import GameOdds, BookOdds, Selection


class TestParlayLeg(unittest.TestCase):
    """Test ParlayLeg data class."""
    
    def test_valid_parlay_leg_creation(self):
        """Test creating a valid ParlayLeg."""
        leg = ParlayLeg(
            game_id="game_123",
            market_type="h2h",
            selection_name="Lakers",
            bookmaker="DraftKings",
            odds_decimal=1.85
        )
        
        self.assertEqual(leg.game_id, "game_123")
        self.assertEqual(leg.market_type, "h2h")
        self.assertEqual(leg.selection_name, "Lakers")
        self.assertEqual(leg.bookmaker, "DraftKings")
        self.assertEqual(leg.odds_decimal, 1.85)
        self.assertIsNone(leg.line)
    
    def test_parlay_leg_with_line(self):
        """Test creating a ParlayLeg with a line."""
        leg = ParlayLeg(
            game_id="game_123",
            market_type="spreads",
            selection_name="Celtics",
            bookmaker="FanDuel",
            odds_decimal=1.91,
            line=-5.5
        )
        
        self.assertEqual(leg.line, -5.5)
    
    def test_invalid_parlay_leg_empty_game_id(self):
        """Test that empty game_id raises ValueError."""
        with self.assertRaises(ValueError):
            ParlayLeg(
                game_id="",
                market_type="h2h",
                selection_name="Lakers",
                bookmaker="DraftKings",
                odds_decimal=1.85
            )
    
    def test_invalid_parlay_leg_low_odds(self):
        """Test that odds <= 1.0 raises ValueError."""
        with self.assertRaises(ValueError):
            ParlayLeg(
                game_id="game_123",
                market_type="h2h",
                selection_name="Lakers",
                bookmaker="DraftKings",
                odds_decimal=0.95
            )
    
    def test_parlay_leg_serialization(self):
        """Test ParlayLeg to_dict and from_dict methods."""
        original_leg = ParlayLeg(
            game_id="game_123",
            market_type="spreads",
            selection_name="Warriors",
            bookmaker="BetMGM",
            odds_decimal=2.10,
            line=3.5
        )
        
        # Convert to dict
        leg_dict = original_leg.to_dict()
        
        # Convert back to ParlayLeg
        restored_leg = ParlayLeg.from_dict(leg_dict)
        
        # Verify they're equal
        self.assertEqual(original_leg.game_id, restored_leg.game_id)
        self.assertEqual(original_leg.market_type, restored_leg.market_type)
        self.assertEqual(original_leg.selection_name, restored_leg.selection_name)
        self.assertEqual(original_leg.bookmaker, restored_leg.bookmaker)
        self.assertEqual(original_leg.odds_decimal, restored_leg.odds_decimal)
        self.assertEqual(original_leg.line, restored_leg.line)


class TestParlayValidation(unittest.TestCase):
    """Test ParlayValidation data class."""
    
    def setUp(self):
        """Set up test data."""
        self.sample_legs = [
            ParlayLeg("game_1", "h2h", "Lakers", "DraftKings", 1.85),
            ParlayLeg("game_2", "spreads", "Celtics", "FanDuel", 1.91, -5.5),
            ParlayLeg("game_3", "totals", "Over", "BetMGM", 1.95, 220.5)
        ]
    
    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        validation = ParlayValidation(
            original_legs=self.sample_legs,
            valid_legs=self.sample_legs[:2],  # 2 out of 3 valid
            invalid_legs=[],
            total_odds=3.54,
            validation_timestamp="2025-08-13T10:00:00Z",
            market_snapshot_games=5
        )
        
        self.assertAlmostEqual(validation.success_rate(), 66.67, places=1)
    
    def test_success_rate_empty_legs(self):
        """Test success rate with no legs."""
        validation = ParlayValidation(
            original_legs=[],
            valid_legs=[],
            invalid_legs=[],
            total_odds=1.0,
            validation_timestamp="2025-08-13T10:00:00Z",
            market_snapshot_games=0
        )
        
        self.assertEqual(validation.success_rate(), 0.0)
    
    def test_is_viable(self):
        """Test parlay viability check."""
        validation = ParlayValidation(
            original_legs=self.sample_legs,
            valid_legs=self.sample_legs[:2],  # 2 valid legs
            invalid_legs=[],
            total_odds=3.54,
            validation_timestamp="2025-08-13T10:00:00Z",
            market_snapshot_games=5
        )
        
        self.assertTrue(validation.is_viable(min_legs=2))
        self.assertFalse(validation.is_viable(min_legs=3))


class TestParlayBuilder(unittest.TestCase):
    """Test ParlayBuilder main functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.builder = ParlayBuilder()
        
        # Create mock game odds data
        self.mock_selection_lakers = Selection(name="Los Angeles Lakers", price_decimal=1.85)
        self.mock_selection_celtics = Selection(name="Boston Celtics", price_decimal=1.91, line=-5.5)
        self.mock_selection_over = Selection(name="Over", price_decimal=1.95, line=220.5)
        
        self.mock_book_dk = BookOdds(
            bookmaker="DraftKings",
            market="h2h",
            selections=[self.mock_selection_lakers]
        )
        
        self.mock_book_fd = BookOdds(
            bookmaker="FanDuel", 
            market="spreads",
            selections=[self.mock_selection_celtics]
        )
        
        self.mock_book_mgm = BookOdds(
            bookmaker="BetMGM",
            market="totals",
            selections=[self.mock_selection_over]
        )
        
        self.mock_game_odds = [
            GameOdds(
                sport_key="basketball_nba",
                game_id="game_1",
                commence_time="2025-01-15T20:00:00Z",
                books=[self.mock_book_dk]
            ),
            GameOdds(
                sport_key="basketball_nba", 
                game_id="game_2",
                commence_time="2025-01-15T20:30:00Z",
                books=[self.mock_book_fd]
            ),
            GameOdds(
                sport_key="basketball_nba",
                game_id="game_3", 
                commence_time="2025-01-15T21:00:00Z",
                books=[self.mock_book_mgm]
            )
        ]
    
    def test_initialization(self):
        """Test ParlayBuilder initialization."""
        builder = ParlayBuilder("basketball_nba")
        self.assertEqual(builder.sport_key, "basketball_nba")
        self.assertIsNotNone(builder.odds_fetcher)
        self.assertIsNone(builder._current_market_snapshot)
    
    @patch('tools.parlay_builder.OddsFetcherTool')
    def test_get_fresh_market_snapshot_success(self, mock_odds_fetcher_class):
        """Test successful market snapshot fetch."""
        # Setup mock
        mock_odds_fetcher = Mock()
        mock_odds_fetcher.get_game_odds.return_value = self.mock_game_odds
        mock_odds_fetcher_class.return_value = mock_odds_fetcher
        
        builder = ParlayBuilder()
        builder.odds_fetcher = mock_odds_fetcher
        
        # Test
        result = builder._get_fresh_market_snapshot()
        
        # Verify
        self.assertEqual(result, self.mock_game_odds)
        self.assertEqual(builder._current_market_snapshot, self.mock_game_odds)
        self.assertIsNotNone(builder._snapshot_timestamp)
        mock_odds_fetcher.get_game_odds.assert_called_once()
    
    @patch('tools.parlay_builder.OddsFetcherTool')
    def test_get_fresh_market_snapshot_failure(self, mock_odds_fetcher_class):
        """Test market snapshot fetch failure."""
        # Setup mock to raise exception
        mock_odds_fetcher = Mock()
        mock_odds_fetcher.get_game_odds.side_effect = Exception("API Error")
        mock_odds_fetcher_class.return_value = mock_odds_fetcher
        
        builder = ParlayBuilder()
        builder.odds_fetcher = mock_odds_fetcher
        
        # Test
        with self.assertRaises(ParlayBuilderError):
            builder._get_fresh_market_snapshot()
    
    def test_selection_matches_exact(self):
        """Test exact selection matching."""
        leg = ParlayLeg("game_1", "h2h", "Los Angeles Lakers", "DraftKings", 1.85)
        selection = Selection("Los Angeles Lakers", 1.85)
        
        self.assertTrue(self.builder._selection_matches(selection, leg))
    
    def test_selection_matches_case_insensitive(self):
        """Test case-insensitive selection matching."""
        leg = ParlayLeg("game_1", "h2h", "los angeles lakers", "DraftKings", 1.85)
        selection = Selection("Los Angeles Lakers", 1.85)
        
        self.assertTrue(self.builder._selection_matches(selection, leg))
    
    def test_selection_matches_with_line(self):
        """Test selection matching with line."""
        leg = ParlayLeg("game_2", "spreads", "Boston Celtics", "FanDuel", 1.91, -5.5)
        selection = Selection("Boston Celtics", 1.91, -5.5)
        
        self.assertTrue(self.builder._selection_matches(selection, leg))
    
    def test_selection_matches_line_tolerance(self):
        """Test selection matching with line tolerance."""
        leg = ParlayLeg("game_2", "spreads", "Boston Celtics", "FanDuel", 1.91, -5.5)
        selection = Selection("Boston Celtics", 1.91, -5.0)  # 0.5 point difference
        
        self.assertTrue(self.builder._selection_matches(selection, leg))
    
    def test_selection_no_match_line_too_different(self):
        """Test selection not matching when line difference is too large."""
        leg = ParlayLeg("game_2", "spreads", "Boston Celtics", "FanDuel", 1.91, -5.5)
        selection = Selection("Boston Celtics", 1.91, -4.0)  # 1.5 point difference
        
        self.assertFalse(self.builder._selection_matches(selection, leg))
    
    def test_find_matching_selection_success(self):
        """Test finding a matching selection."""
        leg = ParlayLeg("game_1", "h2h", "Los Angeles Lakers", "DraftKings", 1.85)
        game_odds = self.mock_game_odds[0]
        
        result = self.builder._find_matching_selection(leg, game_odds)
        
        self.assertIsNotNone(result)
        book_odds, selection = result
        self.assertEqual(book_odds.bookmaker, "DraftKings")
        self.assertEqual(selection.name, "Los Angeles Lakers")
    
    def test_find_matching_selection_wrong_bookmaker(self):
        """Test not finding selection with wrong bookmaker."""
        leg = ParlayLeg("game_1", "h2h", "Los Angeles Lakers", "FanDuel", 1.85)  # Wrong bookmaker
        game_odds = self.mock_game_odds[0]
        
        result = self.builder._find_matching_selection(leg, game_odds)
        
        self.assertIsNone(result)
    
    def test_find_alternative_bookmakers(self):
        """Test finding alternative bookmakers."""
        # Add multiple bookmakers for same game
        alt_book = BookOdds(
            bookmaker="FanDuel",
            market="h2h", 
            selections=[Selection("Los Angeles Lakers", 1.90)]
        )
        
        game_odds = GameOdds(
            sport_key="basketball_nba",
            game_id="game_1",
            commence_time="2025-01-15T20:00:00Z",
            books=[self.mock_book_dk, alt_book]
        )
        
        leg = ParlayLeg("game_1", "h2h", "Los Angeles Lakers", "DraftKings", 1.85)
        
        alternatives = self.builder._find_alternative_bookmakers(leg, game_odds)
        
        self.assertIn("FanDuel", alternatives)
        self.assertNotIn("DraftKings", alternatives)  # Original bookmaker excluded
    
    @patch.object(ParlayBuilder, '_get_fresh_market_snapshot')
    def test_validate_parlay_legs_success(self, mock_snapshot):
        """Test successful parlay leg validation."""
        mock_snapshot.return_value = self.mock_game_odds
        
        legs = [
            ParlayLeg("game_1", "h2h", "Los Angeles Lakers", "DraftKings", 1.85),
            ParlayLeg("game_2", "spreads", "Boston Celtics", "FanDuel", 1.91, -5.5)
        ]
        
        result = self.builder.validate_parlay_legs(legs)
        
        self.assertIsInstance(result, ParlayValidation)
        self.assertEqual(len(result.valid_legs), 2)
        self.assertEqual(len(result.invalid_legs), 0)
        self.assertAlmostEqual(result.total_odds, 1.85 * 1.91, places=2)
        self.assertTrue(result.is_viable())
    
    @patch.object(ParlayBuilder, '_get_fresh_market_snapshot')
    def test_validate_parlay_legs_game_not_found(self, mock_snapshot):
        """Test validation with game not in current markets."""
        mock_snapshot.return_value = self.mock_game_odds
        
        legs = [
            ParlayLeg("nonexistent_game", "h2h", "Lakers", "DraftKings", 1.85)
        ]
        
        result = self.builder.validate_parlay_legs(legs)
        
        self.assertEqual(len(result.valid_legs), 0)
        self.assertEqual(len(result.invalid_legs), 1)
        self.assertEqual(result.invalid_legs[0].reason, "Game not found in current markets")
    
    @patch.object(ParlayBuilder, '_get_fresh_market_snapshot')
    def test_validate_parlay_legs_odds_changed(self, mock_snapshot):
        """Test validation with significantly changed odds."""
        # Mock selection with different odds
        changed_selection = Selection("Los Angeles Lakers", 2.50)  # Much higher odds
        changed_book = BookOdds("DraftKings", "h2h", [changed_selection])
        changed_game = GameOdds("basketball_nba", "game_1", "2025-01-15T20:00:00Z", [changed_book])
        
        mock_snapshot.return_value = [changed_game]
        
        legs = [
            ParlayLeg("game_1", "h2h", "Los Angeles Lakers", "DraftKings", 1.85)  # Original odds
        ]
        
        result = self.builder.validate_parlay_legs(legs)
        
        self.assertEqual(len(result.valid_legs), 0)
        self.assertEqual(len(result.invalid_legs), 1)
        self.assertIn("Odds changed significantly", result.invalid_legs[0].reason)
        self.assertEqual(result.invalid_legs[0].current_odds, 2.50)
    
    def test_validate_parlay_legs_empty_list(self):
        """Test validation with empty legs list."""
        with self.assertRaises(ParlayBuilderError):
            self.builder.validate_parlay_legs([])
    
    @patch.object(ParlayBuilder, 'validate_parlay_legs')
    def test_build_validated_parlay_viable(self, mock_validate):
        """Test building a viable parlay."""
        # Mock successful validation
        mock_validation = ParlayValidation(
            original_legs=[],
            valid_legs=[Mock(), Mock()],  # 2 valid legs
            invalid_legs=[],
            total_odds=3.54,
            validation_timestamp="2025-08-13T10:00:00Z",
            market_snapshot_games=5
        )
        mock_validate.return_value = mock_validation
        
        result = self.builder.build_validated_parlay([], min_legs=2)
        
        self.assertIsNotNone(result)
        self.assertEqual(result, mock_validation)
    
    @patch.object(ParlayBuilder, 'validate_parlay_legs')
    def test_build_validated_parlay_not_viable(self, mock_validate):
        """Test building a non-viable parlay."""
        # Mock validation with insufficient legs
        mock_validation = ParlayValidation(
            original_legs=[],
            valid_legs=[Mock()],  # Only 1 valid leg
            invalid_legs=[],
            total_odds=1.85,
            validation_timestamp="2025-08-13T10:00:00Z",
            market_snapshot_games=5
        )
        mock_validate.return_value = mock_validation
        
        result = self.builder.build_validated_parlay([], min_legs=2)
        
        self.assertIsNone(result)
    
    def test_get_market_summary_no_snapshot(self):
        """Test market summary with no snapshot."""
        result = self.builder.get_market_summary()
        
        self.assertEqual(result["status"], "No market snapshot available")
    
    def test_get_market_summary_with_snapshot(self):
        """Test market summary with active snapshot."""
        self.builder._current_market_snapshot = self.mock_game_odds
        self.builder._snapshot_timestamp = "2025-08-13T10:00:00Z"
        
        result = self.builder.get_market_summary()
        
        self.assertEqual(result["status"], "Active")
        self.assertEqual(result["total_games"], 3)
        self.assertEqual(result["snapshot_timestamp"], "2025-08-13T10:00:00Z")
        self.assertIn("DraftKings", result["bookmakers"])
        self.assertIn("FanDuel", result["bookmakers"])
        self.assertIn("BetMGM", result["bookmakers"])


class TestOffSeasonScenarios(unittest.TestCase):
    """Test ParlayBuilder behavior during NBA off-season."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.builder = ParlayBuilder()
    
    @patch('tools.parlay_builder.OddsFetcherTool')
    def test_off_season_no_games_available(self, mock_odds_fetcher_class):
        """Test behavior when no games are available (off-season)."""
        # Mock empty response (no games)
        mock_odds_fetcher = Mock()
        mock_odds_fetcher.get_game_odds.return_value = []
        mock_odds_fetcher_class.return_value = mock_odds_fetcher
        
        builder = ParlayBuilder()
        builder.odds_fetcher = mock_odds_fetcher
        
        # Test validation with sample legs
        legs = create_sample_legs()
        
        result = builder.validate_parlay_legs(legs)
        
        # All legs should be invalid (games not found)
        self.assertEqual(len(result.valid_legs), 0)
        self.assertEqual(len(result.invalid_legs), len(legs))
        
        for invalid_result in result.invalid_legs:
            self.assertEqual(invalid_result.reason, "Game not found in current markets")
    
    @patch('tools.parlay_builder.OddsFetcherTool')
    def test_off_season_api_error_handling(self, mock_odds_fetcher_class):
        """Test handling of API errors during off-season."""
        # Mock API error
        mock_odds_fetcher = Mock()
        mock_odds_fetcher.get_game_odds.side_effect = Exception("No games available")
        mock_odds_fetcher_class.return_value = mock_odds_fetcher
        
        builder = ParlayBuilder()
        builder.odds_fetcher = mock_odds_fetcher
        
        legs = create_sample_legs()
        
        with self.assertRaises(ParlayBuilderError):
            builder.validate_parlay_legs(legs)


class TestSampleLegsFunction(unittest.TestCase):
    """Test the create_sample_legs utility function."""
    
    def test_create_sample_legs(self):
        """Test creating sample legs."""
        legs = create_sample_legs()
        
        self.assertEqual(len(legs), 3)
        self.assertIsInstance(legs[0], ParlayLeg)
        self.assertIsInstance(legs[1], ParlayLeg)
        self.assertIsInstance(legs[2], ParlayLeg)
        
        # Check that different market types are represented
        market_types = [leg.market_type for leg in legs]
        self.assertIn("h2h", market_types)
        self.assertIn("spreads", market_types)
        self.assertIn("totals", market_types)


class TestIntegrationScenarios(unittest.TestCase):
    """Integration tests for realistic scenarios."""
    
    def setUp(self):
        """Set up integration test fixtures."""
        self.builder = ParlayBuilder()
    
    @patch('tools.parlay_builder.OddsFetcherTool')
    def test_mixed_validation_results(self, mock_odds_fetcher_class):
        """Test scenario with mixed validation results."""
        # Create mock data with some matching and some non-matching selections
        matching_selection = Selection("Los Angeles Lakers", 1.85)
        matching_book = BookOdds("DraftKings", "h2h", [matching_selection])
        matching_game = GameOdds("basketball_nba", "game_1", "2025-01-15T20:00:00Z", [matching_book])
        
        # Game 2 exists but wrong bookmaker
        wrong_book_selection = Selection("Boston Celtics", 1.91, -5.5)
        wrong_book = BookOdds("BetMGM", "spreads", [wrong_book_selection])  # Different bookmaker
        wrong_book_game = GameOdds("basketball_nba", "game_2", "2025-01-15T20:30:00Z", [wrong_book])
        
        # Game 3 doesn't exist
        
        mock_odds_fetcher = Mock()
        mock_odds_fetcher.get_game_odds.return_value = [matching_game, wrong_book_game]
        mock_odds_fetcher_class.return_value = mock_odds_fetcher
        
        builder = ParlayBuilder()
        builder.odds_fetcher = mock_odds_fetcher
        
        legs = [
            ParlayLeg("game_1", "h2h", "Los Angeles Lakers", "DraftKings", 1.85),  # Should match
            ParlayLeg("game_2", "spreads", "Boston Celtics", "FanDuel", 1.91, -5.5),  # Wrong bookmaker
            ParlayLeg("game_3", "totals", "Over", "BetMGM", 1.95, 220.5)  # Game not found
        ]
        
        result = builder.validate_parlay_legs(legs)
        
        # Verify results
        self.assertEqual(len(result.valid_legs), 1)  # Only first leg valid
        self.assertEqual(len(result.invalid_legs), 2)  # Two legs invalid
        
        # Check specific invalid reasons
        invalid_reasons = [invalid.reason for invalid in result.invalid_legs]
        self.assertTrue(any("not available at specified bookmaker" in reason for reason in invalid_reasons))
        self.assertTrue(any("Game not found" in reason for reason in invalid_reasons))
        
        # Check alternative bookmakers suggested
        bookmaker_invalid = next(invalid for invalid in result.invalid_legs 
                               if "not available at specified bookmaker" in invalid.reason)
        self.assertIn("BetMGM", bookmaker_invalid.alternative_bookmakers)


if __name__ == '__main__':
    # Set up logging for tests
    import logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise during tests
    
    # Run tests
    unittest.main(verbosity=2)
