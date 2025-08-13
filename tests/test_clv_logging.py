#!/usr/bin/env python3
"""
Tests for CLV (Closing Line Value) logging functionality.
"""

import pytest
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from tools.bets_logger import BetsLogger
from tools.odds_fetcher_tool import GameOdds, BookOdds, Selection


class TestCLVLogging:
    """Test suite for CLV logging functionality."""
    
    @pytest.fixture
    def temp_db_path(self, tmp_path):
        """Create temporary database path."""
        return tmp_path / "test_clv.sqlite"
    
    @pytest.fixture
    def bets_logger(self, temp_db_path):
        """Create BetsLogger instance with temporary database."""
        return BetsLogger(temp_db_path)
    
    def test_schema_migration_adds_columns_and_backfills_odds_at_alert(self, temp_db_path):
        """Test that schema migration adds CLV columns and backfills odds_at_alert."""
        # Create a database with old schema (without CLV columns)
        with BetsLogger(temp_db_path) as logger:
            # Insert a bet with old schema
            bet_id = logger.log_parlay_leg(
                parlay_id="test_parlay",
                game_id="test_game",
                leg_description="LAL -2.5",
                odds=1.91,
                stake=10.0,
                predicted_outcome="Lakers cover"
            )
        
        # Close and reopen to trigger migration
        with BetsLogger(temp_db_path) as logger:
            # Check that CLV columns exist
            cursor = logger.connection.cursor()
            cursor.execute("PRAGMA table_info(bets)")
            columns = {row[1] for row in cursor.fetchall()}
            
            assert 'odds_at_alert' in columns, "odds_at_alert column should exist"
            assert 'closing_line_odds' in columns, "closing_line_odds column should exist"
            assert 'clv_percentage' in columns, "clv_percentage column should exist"
            
            # Check that odds_at_alert was backfilled
            cursor.execute("SELECT odds_at_alert FROM bets WHERE bet_id = ?", (bet_id,))
            odds_at_alert = cursor.fetchone()[0]
            assert odds_at_alert == 1.91, "odds_at_alert should be backfilled from odds"
    
    def test_compute_clv_percentage_sign_and_value(self, bets_logger):
        """Test CLV computation with positive and negative values."""
        with bets_logger:
            # Test positive CLV (beat the close)
            clv_positive = bets_logger.compute_clv(2.10, 1.95)
            assert clv_positive == pytest.approx(7.6923, rel=1e-3)
            
            # Test negative CLV (worse than close)
            clv_negative = bets_logger.compute_clv(1.80, 1.95)
            assert clv_negative == pytest.approx(-7.6923, rel=1e-3)
            
            # Test zero CLV (same odds)
            clv_zero = bets_logger.compute_clv(1.95, 1.95)
            assert clv_zero == 0.0
    
    def test_compute_clv_invalid_inputs(self, bets_logger):
        """Test CLV computation with invalid inputs."""
        with bets_logger:
            # Test zero closing odds
            with pytest.raises(ValueError, match="Closing line odds must be positive"):
                bets_logger.compute_clv(1.91, 0.0)
            
            # Test negative closing odds
            with pytest.raises(ValueError, match="Closing line odds must be positive"):
                bets_logger.compute_clv(1.91, -1.0)
    
    def test_set_closing_line_updates_row_and_clv(self, bets_logger):
        """Test setting closing line updates the row and computes CLV."""
        with bets_logger:
            # Insert a bet
            bet_id = bets_logger.log_parlay_leg(
                parlay_id="test_parlay",
                game_id="test_game",
                leg_description="LAL -2.5",
                odds=2.10,  # odds_at_alert will be 2.10
                stake=10.0,
                predicted_outcome="Lakers cover"
            )
            
            # Set closing line
            bets_logger.set_closing_line(bet_id, 1.95)
            
            # Check the updated data
            cursor = bets_logger.connection.cursor()
            cursor.execute("SELECT closing_line_odds, clv_percentage FROM bets WHERE bet_id = ?", (bet_id,))
            row = cursor.fetchone()
            
            assert row[0] == 1.95, "closing_line_odds should be set"
            assert row[1] == pytest.approx(7.6923, rel=1e-3), "clv_percentage should be computed correctly"
    
    def test_set_closing_line_invalid_bet_id(self, bets_logger):
        """Test setting closing line with invalid bet ID."""
        with bets_logger:
            with pytest.raises(ValueError, match="Bet with ID 999 not found"):
                bets_logger.set_closing_line(999, 1.95)
    
    def test_fetch_bets_missing_clv(self, bets_logger):
        """Test fetching bets missing CLV data."""
        with bets_logger:
            # Insert bets with different states
            bet1 = bets_logger.log_parlay_leg("parlay1", "game1", "LAL -2.5", 1.91, 10.0, "test")
            bet2 = bets_logger.log_parlay_leg("parlay2", "game2", "GSW +3.5", 1.89, 10.0, "test")
            
            # Set closing line for one bet
            bets_logger.set_closing_line(bet1, 1.85)
            
            # Fetch bets missing CLV
            missing_clv = bets_logger.fetch_bets_missing_clv()
            
            assert len(missing_clv) == 1, "Should have one bet missing CLV"
            assert missing_clv[0]['bet_id'] == bet2, "Should be the bet without closing line"
    
    def test_fetch_bets_missing_clv_with_filters(self, bets_logger):
        """Test fetching bets missing CLV with filters."""
        with bets_logger:
            # Insert bets for different games
            bet1 = bets_logger.log_parlay_leg("parlay1", "game1", "LAL -2.5", 1.91, 10.0, "test")
            bet2 = bets_logger.log_parlay_leg("parlay2", "game2", "GSW +3.5", 1.89, 10.0, "test")
            
            # Filter by game_id
            missing_clv = bets_logger.fetch_bets_missing_clv(game_ids=["game1"])
            assert len(missing_clv) == 1
            assert missing_clv[0]['game_id'] == "game1"
            
            # Filter by since date
            since_iso = datetime.now(timezone.utc).isoformat()
            missing_clv = bets_logger.fetch_bets_missing_clv(since_iso=since_iso)
            assert len(missing_clv) == 0  # No bets created after "now"
    
    def test_log_parlay_leg_sets_odds_at_alert(self, bets_logger):
        """Test that logging a parlay leg sets odds_at_alert."""
        with bets_logger:
            bet_id = bets_logger.log_parlay_leg(
                parlay_id="test_parlay",
                game_id="test_game",
                leg_description="LAL -2.5",
                odds=1.91,
                stake=10.0,
                predicted_outcome="Lakers cover"
            )
            
            # Check that odds_at_alert was set
            cursor = bets_logger.connection.cursor()
            cursor.execute("SELECT odds_at_alert FROM bets WHERE bet_id = ?", (bet_id,))
            odds_at_alert = cursor.fetchone()[0]
            
            assert odds_at_alert == 1.91, "odds_at_alert should be set to the provided odds"
    
    def test_log_parlay_sets_odds_at_alert(self, bets_logger):
        """Test that logging a parlay sets odds_at_alert for all legs."""
        with bets_logger:
            legs = [
                {
                    'leg_description': 'LAL -2.5',
                    'odds': 1.91,
                    'stake': 10.0,
                    'predicted_outcome': 'Lakers cover'
                },
                {
                    'leg_description': 'Over 220.5',
                    'odds': 1.87,
                    'stake': 10.0,
                    'predicted_outcome': 'Total over'
                }
            ]
            
            bet_ids = bets_logger.log_parlay("test_parlay", "test_game", legs)
            
            # Check that odds_at_alert was set for all legs
            cursor = bets_logger.connection.cursor()
            for bet_id in bet_ids:
                cursor.execute("SELECT odds_at_alert FROM bets WHERE bet_id = ?", (bet_id,))
                odds_at_alert = cursor.fetchone()[0]
                assert odds_at_alert is not None, f"odds_at_alert should be set for bet {bet_id}"


class TestUpdateClosingLinesScript:
    """Test suite for update closing lines script functionality."""
    
    @pytest.fixture
    def sample_games(self):
        """Create sample games for testing."""
        return [
            GameOdds(
                sport_key="basketball_nba",
                game_id="test_game_1",
                commence_time="2025-01-15T19:30:00Z",
                books=[
                    BookOdds(
                        bookmaker="DraftKings",
                        market="spreads",
                        selections=[
                            Selection(name="Los Angeles Lakers", price_decimal=1.85, line=-2.5),
                            Selection(name="Golden State Warriors", price_decimal=1.85, line=2.5)
                        ]
                    ),
                    BookOdds(
                        bookmaker="DraftKings",
                        market="totals",
                        selections=[
                            Selection(name="Over", price_decimal=1.87, line=220.5),
                            Selection(name="Under", price_decimal=1.87, line=220.5)
                        ]
                    )
                ]
            )
        ]
    
    def test_update_closing_lines_script_happy_path(self, tmp_path, sample_games, monkeypatch):
        """Test the happy path for updating closing lines."""
        from scripts.update_closing_lines import update_closing_lines, find_selection_for_leg
        
        # Mock OddsFetcherTool
        class MockOddsFetcher:
            def get_game_odds(self, sport_key, regions, markets):
                return sample_games
        
        monkeypatch.setattr("scripts.update_closing_lines.OddsFetcherTool", MockOddsFetcher)
        
        # Create database with a bet
        temp_db_path = tmp_path / "test_clv.sqlite"
        with BetsLogger(temp_db_path) as logger:
            bet_id = logger.log_parlay_leg(
                parlay_id="test_parlay",
                game_id="test_game_1",
                leg_description="LAL -2.5",
                odds=1.91,  # odds_at_alert
                stake=10.0,
                predicted_outcome="Lakers cover"
            )
            
            # Get the bet for testing
            targets = logger.fetch_bets_missing_clv()
            assert len(targets) == 1
        
        # Test the update function
        with BetsLogger(temp_db_path) as logger:
            stats = update_closing_lines(logger, targets, sample_games, dry_run=False)
            
            assert stats['updated_count'] == 1, "Should update one bet"
            assert stats['unmatched_count'] == 0, "Should have no unmatched"
            
            # Check that CLV was computed correctly
            cursor = logger.connection.cursor()
            cursor.execute("SELECT closing_line_odds, clv_percentage FROM bets WHERE bet_id = ?", (bet_id,))
            row = cursor.fetchone()
            
            assert row[0] == 1.85, "closing_line_odds should be set"
            # CLV = ((1.91 - 1.85) / 1.85) * 100 = 3.2432%
            assert row[1] == pytest.approx(3.2432, rel=1e-3), "CLV should be computed correctly"
    
    def test_update_closing_lines_script_dry_run(self, tmp_path, sample_games, monkeypatch):
        """Test dry run mode for updating closing lines."""
        from scripts.update_closing_lines import update_closing_lines
        
        # Mock OddsFetcherTool
        class MockOddsFetcher:
            def get_game_odds(self, sport_key, regions, markets):
                return sample_games
        
        monkeypatch.setattr("scripts.update_closing_lines.OddsFetcherTool", MockOddsFetcher)
        
        # Create database with a bet
        temp_db_path = tmp_path / "test_clv.sqlite"
        with BetsLogger(temp_db_path) as logger:
            bet_id = logger.log_parlay_leg(
                parlay_id="test_parlay",
                game_id="test_game_1",
                leg_description="LAL -2.5",
                odds=1.91,
                stake=10.0,
                predicted_outcome="Lakers cover"
            )
            
            targets = logger.fetch_bets_missing_clv()
        
        # Test dry run
        with BetsLogger(temp_db_path) as logger:
            stats = update_closing_lines(logger, targets, sample_games, dry_run=True)
            
            assert stats['updated_count'] == 1, "Should count one update"
            assert stats['unmatched_count'] == 0, "Should have no unmatched"
            
            # Check that no actual update occurred
            cursor = logger.connection.cursor()
            cursor.execute("SELECT closing_line_odds FROM bets WHERE bet_id = ?", (bet_id,))
            closing_line_odds = cursor.fetchone()[0]
            
            assert closing_line_odds is None, "No update should occur in dry run mode"
    
    def test_find_selection_for_leg_matching(self, sample_games):
        """Test finding selection for leg description."""
        from scripts.update_closing_lines import find_selection_for_leg
        
        # Test exact match
        result = find_selection_for_leg("LAL -2.5", sample_games, "test_game_1")
        assert result is not None
        price, market = result
        assert price == 1.85
        assert market == "spreads"
        
        # Test no match
        result = find_selection_for_leg("Nonexistent", sample_games, "test_game_1")
        assert result is None
        
        # Test game not found
        result = find_selection_for_leg("LAL -2.5", sample_games, "nonexistent_game")
        assert result is None
    
    def test_infer_market_from_leg_description(self):
        """Test market inference from leg description."""
        from scripts.update_closing_lines import infer_market_from_leg_description
        
        assert infer_market_from_leg_description("LAL moneyline") == "h2h"
        assert infer_market_from_leg_description("LAL -2.5 spread") == "spreads"
        assert infer_market_from_leg_description("Over 220.5 total") == "totals"
        assert infer_market_from_leg_description("Jokic 25 points") == "player_points"
        assert infer_market_from_leg_description("Unknown description") == "any"
