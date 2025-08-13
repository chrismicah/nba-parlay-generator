#!/usr/bin/env python3
"""
Tests for BetsLogger class.
"""

import pytest
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from tools.bets_logger import BetsLogger


class TestBetsLogger:
    """Test suite for BetsLogger."""
    
    @pytest.fixture
    def temp_db_path(self, tmp_path):
        """Create temporary database path."""
        return tmp_path / "test_parlays.sqlite"
    
    @pytest.fixture
    def bets_logger(self, temp_db_path):
        """Create BetsLogger instance with temporary database."""
        return BetsLogger(temp_db_path)
    
    def test_schema_created_and_indexes_exist(self, bets_logger):
        """Test that schema and indexes are created correctly."""
        with bets_logger:
            # Check that table exists
            cursor = bets_logger.connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bets'")
            table_exists = cursor.fetchone() is not None
            assert table_exists, "bets table should exist"
            
            # Check that indexes exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='bets'")
            indexes = [row[0] for row in cursor.fetchall()]
            
            assert 'idx_bets_parlay_id' in indexes, "parlay_id index should exist"
            assert 'idx_bets_game_id' in indexes, "game_id index should exist"
            
            # Check table structure
            cursor.execute("PRAGMA table_info(bets)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}
            
            expected_columns = {
                'bet_id': 'INTEGER',
                'game_id': 'TEXT',
                'parlay_id': 'TEXT',
                'leg_description': 'TEXT',
                'odds': 'REAL',
                'stake': 'REAL',
                'predicted_outcome': 'TEXT',
                'actual_outcome': 'TEXT',
                'is_win': 'INTEGER',
                'created_at': 'TEXT',
                'updated_at': 'TEXT'
            }
            
            for col_name, col_type in expected_columns.items():
                assert col_name in columns, f"Column {col_name} should exist"
                assert columns[col_name] == col_type, f"Column {col_name} should be {col_type}"
    
    def test_log_single_leg_and_fetch_open(self, bets_logger):
        """Test logging a single leg and fetching open bets."""
        with bets_logger:
            # Log a single leg
            bet_id = bets_logger.log_parlay_leg(
                parlay_id="parlay_123",
                game_id="game_456",
                leg_description="LAL -2.5",
                odds=1.91,
                stake=10.0,
                predicted_outcome="Lakers cover spread"
            )
            
            assert bet_id > 0, "bet_id should be positive"
            
            # Fetch open bets
            open_bets = bets_logger.fetch_open_bets()
            assert len(open_bets) == 1, "Should have one open bet"
            
            bet = open_bets[0]
            assert bet['bet_id'] == bet_id
            assert bet['parlay_id'] == "parlay_123"
            assert bet['game_id'] == "game_456"
            assert bet['leg_description'] == "LAL -2.5"
            assert bet['odds'] == 1.91
            assert bet['stake'] == 10.0
            assert bet['predicted_outcome'] == "Lakers cover spread"
            assert bet['actual_outcome'] is None
            assert bet['is_win'] is None
    
    def test_log_parlay_bulk_insert_counts(self, bets_logger):
        """Test bulk insert of parlay legs."""
        with bets_logger:
            legs = [
                {
                    'leg_description': 'LAL -2.5',
                    'odds': 1.91,
                    'stake': 10.0,
                    'predicted_outcome': 'Lakers cover spread'
                },
                {
                    'leg_description': 'Over 220.5',
                    'odds': 1.87,
                    'stake': 10.0,
                    'predicted_outcome': 'Total goes over'
                }
            ]
            
            bet_ids = bets_logger.log_parlay("parlay_123", "game_456", legs)
            
            assert len(bet_ids) == 2, "Should return 2 bet IDs"
            assert all(bid > 0 for bid in bet_ids), "All bet IDs should be positive"
            
            # Check that both legs are in database
            open_bets = bets_logger.fetch_open_bets()
            assert len(open_bets) == 2, "Should have 2 open bets"
            
            # Check that both legs have same parlay_id
            parlay_ids = {bet['parlay_id'] for bet in open_bets}
            assert parlay_ids == {"parlay_123"}, "All bets should have same parlay_id"
    
    def test_update_bet_outcome_sets_fields_and_closes_open(self, bets_logger):
        """Test updating bet outcome and verifying it's no longer open."""
        with bets_logger:
            # Log a bet
            bet_id = bets_logger.log_parlay_leg(
                parlay_id="parlay_123",
                game_id="game_456",
                leg_description="LAL -2.5",
                odds=1.91,
                stake=10.0,
                predicted_outcome="Lakers cover spread"
            )
            
            # Verify it's open
            open_bets = bets_logger.fetch_open_bets()
            assert len(open_bets) == 1
            
            # Update outcome
            bets_logger.update_bet_outcome(bet_id, "Lakers won by 5", True)
            
            # Verify it's no longer open
            open_bets = bets_logger.fetch_open_bets()
            assert len(open_bets) == 0, "Bet should no longer be open"
            
            # Check the updated data
            cursor = bets_logger.connection.cursor()
            cursor.execute("SELECT * FROM bets WHERE bet_id = ?", (bet_id,))
            bet = cursor.fetchone()
            
            assert bet['actual_outcome'] == "Lakers won by 5"
            assert bet['is_win'] == 1
            assert bet['updated_at'] != bet['created_at']
    
    def test_upsert_outcome_by_keys_updates_row(self, bets_logger):
        """Test upserting outcome by parlay_id and leg_description."""
        with bets_logger:
            # Log a bet
            bet_id = bets_logger.log_parlay_leg(
                parlay_id="parlay_123",
                game_id="game_456",
                leg_description="LAL -2.5",
                odds=1.91,
                stake=10.0,
                predicted_outcome="Lakers cover spread"
            )
            
            # Upsert outcome
            affected_count = bets_logger.upsert_outcome_by_keys(
                parlay_id="parlay_123",
                leg_description="LAL -2.5",
                actual_outcome="Lakers won by 5",
                is_win=True
            )
            
            assert affected_count == 1, "Should affect one row"
            
            # Verify the update
            cursor = bets_logger.connection.cursor()
            cursor.execute("SELECT * FROM bets WHERE bet_id = ?", (bet_id,))
            bet = cursor.fetchone()
            
            assert bet['actual_outcome'] == "Lakers won by 5"
            assert bet['is_win'] == 1
    
    def test_timestamps_are_utc_iso(self, bets_logger):
        """Test that timestamps are in UTC ISO format."""
        with bets_logger:
            bet_id = bets_logger.log_parlay_leg(
                parlay_id="parlay_123",
                game_id="game_456",
                leg_description="LAL -2.5",
                odds=1.91,
                stake=10.0,
                predicted_outcome="Lakers cover spread"
            )
            
            cursor = bets_logger.connection.cursor()
            cursor.execute("SELECT created_at, updated_at FROM bets WHERE bet_id = ?", (bet_id,))
            bet = cursor.fetchone()
            
            # Check that timestamps are valid ISO format
            created_at = datetime.fromisoformat(bet['created_at'].replace('Z', '+00:00'))
            updated_at = datetime.fromisoformat(bet['updated_at'].replace('Z', '+00:00'))
            
            # Check that they're timezone-aware
            assert created_at.tzinfo is not None
            assert updated_at.tzinfo is not None
            
            # Check that they're recent (within last minute)
            now = datetime.now(timezone.utc)
            assert abs((now - created_at).total_seconds()) < 60
            assert abs((now - updated_at).total_seconds()) < 60
    
    def test_fetch_open_bets_with_filters(self, bets_logger):
        """Test fetching open bets with filters."""
        with bets_logger:
            # Log multiple bets
            bets_logger.log_parlay_leg("parlay_1", "game_1", "LAL -2.5", 1.91, 10.0, "Lakers cover")
            bets_logger.log_parlay_leg("parlay_2", "game_1", "Over 220.5", 1.87, 10.0, "Total over")
            bets_logger.log_parlay_leg("parlay_3", "game_2", "GSW +3.5", 1.89, 10.0, "Warriors cover")
            
            # Test game_id filter
            game_1_bets = bets_logger.fetch_open_bets(game_id="game_1")
            assert len(game_1_bets) == 2
            
            # Test parlay_id filter
            parlay_1_bets = bets_logger.fetch_open_bets(parlay_id="parlay_1")
            assert len(parlay_1_bets) == 1
            
            # Test both filters
            filtered_bets = bets_logger.fetch_open_bets(game_id="game_1", parlay_id="parlay_1")
            assert len(filtered_bets) == 1
    
    def test_context_manager(self, temp_db_path):
        """Test context manager functionality."""
        with BetsLogger(temp_db_path) as logger:
            # Should be connected
            assert logger.connection is not None
            
            # Should be able to log
            bet_id = logger.log_parlay_leg("parlay_123", "game_456", "test", 1.5, 10.0, "test")
            assert bet_id > 0
        
        # Should be disconnected after context
        assert logger.connection is None
    
    def test_error_handling(self, bets_logger):
        """Test error handling for invalid operations."""
        with bets_logger:
            # Try to update non-existent bet
            with pytest.raises(ValueError, match="Bet with ID 999 not found"):
                bets_logger.update_bet_outcome(999, "test", True)
            
            # Try to log without connection
            bets_logger.close()
            with pytest.raises(RuntimeError, match="Database connection not established"):
                bets_logger.log_parlay_leg("test", "test", "test", 1.0, 1.0, "test")
    
    def test_upsert_outcome_by_keys_no_match(self, bets_logger):
        """Test upsert when no matching bet is found."""
        with bets_logger:
            # Try to upsert non-existent bet
            affected_count = bets_logger.upsert_outcome_by_keys(
                parlay_id="nonexistent",
                leg_description="nonexistent",
                actual_outcome="test",
                is_win=True
            )
            
            assert affected_count == 0, "Should affect zero rows"
