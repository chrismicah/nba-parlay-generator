#!/usr/bin/env python3
"""
Test Database NFL Support - JIRA-NFL-006

Test sport segmentation functionality in SQLite schema:
- Verify sport column exists in both tables
- Test sport filtering in queries
- Verify indexes work correctly
- Test BetsLogger sport parameter
- Test ArbitrageDetectorTool sport logging
- Test performance reporter sport filtering
"""

import pytest
import sqlite3
import tempfile
import json
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch

# Import classes to test
from tools.bets_logger import BetsLogger
from tools.arbitrage_detector_tool import ArbitrageDetectorTool
from scripts.performance_reporter import load_rows, rollup_metrics


class TestDatabaseNFLSupport:
    """Test suite for NFL database support."""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as tmp:
            return tmp.name
    
    @pytest.fixture
    def bets_logger(self, temp_db_path):
        """Create a BetsLogger instance with temp database."""
        logger = BetsLogger(temp_db_path)
        logger.connect()
        return logger
    
    def test_migration_creates_sport_columns(self, temp_db_path):
        """Test that migration script creates sport columns correctly."""
        # First create the basic tables by initializing BetsLogger
        logger = BetsLogger(temp_db_path)
        logger.connect()
        logger.close()
        
        # Run migration on temp database
        from migrations.add_sport_column import migrate_database
        
        migrate_database(temp_db_path, dry_run=False)
        
        # Verify schema
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        
        # Check bets table has sport column
        cursor.execute("PRAGMA table_info(bets)")
        bets_columns = {row[1] for row in cursor.fetchall()}
        assert 'sport' in bets_columns
        
        # Check arbitrage_opportunities table exists and has sport column
        cursor.execute("PRAGMA table_info(arbitrage_opportunities)")
        arb_columns = {row[1] for row in cursor.fetchall()}
        assert 'sport' in arb_columns
        
        # Check indexes exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_bets_sport'")
        assert cursor.fetchone() is not None
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_arbitrage_sport'")
        assert cursor.fetchone() is not None
        
        conn.close()
    
    def test_bets_logger_sport_parameter(self, bets_logger):
        """Test BetsLogger sport parameter functionality."""
        # Test NBA bet logging (default)
        bet_id_nba = bets_logger.log_parlay_leg(
            parlay_id="test_parlay_nba",
            game_id="nba_game_001",
            leg_description="Lakers ML",
            odds=-110.0,
            stake=100.0,
            predicted_outcome="Lakers win",
            sport="nba"
        )
        
        # Test NFL bet logging
        bet_id_nfl = bets_logger.log_parlay_leg(
            parlay_id="test_parlay_nfl",
            game_id="nfl_game_001", 
            leg_description="Chiefs ML",
            odds=-150.0,
            stake=100.0,
            predicted_outcome="Chiefs win",
            sport="nfl"
        )
        
        # Verify both records were inserted
        assert bet_id_nba is not None
        assert bet_id_nfl is not None
        
        # Test sport filtering
        nba_bets = bets_logger.fetch_bets_by_sport("nba")
        nfl_bets = bets_logger.fetch_bets_by_sport("nfl")
        
        assert len(nba_bets) == 1
        assert len(nfl_bets) == 1
        assert nba_bets[0]['sport'] == 'nba'
        assert nfl_bets[0]['sport'] == 'nfl'
        
        # Test sports summary
        summary = bets_logger.get_sports_summary()
        assert 'nba' in summary
        assert 'nfl' in summary
        assert summary['nba']['total_bets'] == 1
        assert summary['nfl']['total_bets'] == 1
    
    def test_bets_logger_bulk_parlay(self, bets_logger):
        """Test bulk parlay logging with sport parameter."""
        legs = [
            {
                'leg_description': 'Patriots ML',
                'odds': -120.0,
                'stake': 50.0,
                'predicted_outcome': 'Patriots win'
            },
            {
                'leg_description': 'Bills ML', 
                'odds': +150.0,
                'stake': 50.0,
                'predicted_outcome': 'Bills win'
            }
        ]
        
        bet_ids = bets_logger.log_parlay(
            parlay_id="nfl_parlay_001",
            game_id="nfl_game_002",
            legs=legs,
            sport="nfl"
        )
        
        assert len(bet_ids) == 2
        
        # Verify all legs have correct sport
        for bet_id in bet_ids:
            cursor = bets_logger.connection.cursor()
            cursor.execute("SELECT sport FROM bets WHERE bet_id = ?", (bet_id,))
            row = cursor.fetchone()
            assert row[0] == 'nfl'
    
    def test_fetch_open_bets_sport_filter(self, bets_logger):
        """Test fetching open bets with sport filter."""
        # Add NBA and NFL bets
        bets_logger.log_parlay_leg(
            parlay_id="open_nba",
            game_id="nba_game_open",
            leg_description="Lakers ML",
            odds=-110.0,
            stake=100.0,
            predicted_outcome="Lakers win",
            sport="nba"
        )
        
        bets_logger.log_parlay_leg(
            parlay_id="open_nfl", 
            game_id="nfl_game_open",
            leg_description="Chiefs ML",
            odds=-150.0,
            stake=100.0,
            predicted_outcome="Chiefs win",
            sport="nfl"
        )
        
        # Test sport filtering in open bets
        nba_open = bets_logger.fetch_open_bets(sport="nba")
        nfl_open = bets_logger.fetch_open_bets(sport="nfl") 
        all_open = bets_logger.fetch_open_bets()
        
        assert len(nba_open) == 1
        assert len(nfl_open) == 1
        assert len(all_open) == 2
        
        assert nba_open[0]['sport'] == 'nba'
        assert nfl_open[0]['sport'] == 'nfl'
    
    def test_arbitrage_detector_sport_logging(self, temp_db_path):
        """Test ArbitrageDetectorTool sport logging functionality."""
        # First ensure the database and tables exist
        from migrations.add_sport_column import migrate_database
        migrate_database(temp_db_path, dry_run=False)
        
        detector = ArbitrageDetectorTool(db_path=temp_db_path)
        
        # Create a mock arbitrage opportunity
        opportunity = detector.detect_arbitrage_two_way(
            odds_a=105,
            book_a="fanduel",
            odds_b=-90,
            book_b="draftkings"
        )
        
        if opportunity:
            # Test logging with NFL sport
            opportunity_id = detector.log_arbitrage_opportunity(opportunity, sport="nfl")
            assert opportunity_id is not None
            
            # Verify record was logged with correct sport
            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT sport, market_type FROM arbitrage_opportunities WHERE id = ?", (opportunity_id,))
            row = cursor.fetchone()
            assert row[0] == 'nfl'
            assert row[1] == '2-way'
            conn.close()
    
    def test_performance_reporter_sport_filtering(self, temp_db_path):
        """Test performance reporter sport filtering."""
        # Create test data
        logger = BetsLogger(temp_db_path)
        logger.connect()
        
        # Add NBA bets
        logger.log_parlay_leg(
            parlay_id="perf_nba_1",
            game_id="nba_game_perf",
            leg_description="Lakers ML",
            odds=-110.0,  # American odds
            stake=100.0,
            predicted_outcome="Lakers win",
            sport="nba"
        )
        
        # Add NFL bets
        logger.log_parlay_leg(
            parlay_id="perf_nfl_1", 
            game_id="nfl_game_perf",
            leg_description="Chiefs ML",
            odds=-125.0,  # American odds
            stake=150.0,
            predicted_outcome="Chiefs win",
            sport="nfl"
        )
        
        logger.close()
        
        # Test sport filtering in load_rows
        all_rows = load_rows(temp_db_path, sport="all")
        nba_rows = load_rows(temp_db_path, sport="nba")
        nfl_rows = load_rows(temp_db_path, sport="nfl")
        
        assert len(all_rows) == 2
        assert len(nba_rows) == 1
        assert len(nfl_rows) == 1
        
        # Test sport grouping
        groups = rollup_metrics(all_rows, "sport", include_open=True)
        assert 'nba' in groups
        assert 'nfl' in groups
        assert groups['nba']['count_total'] == 1
        assert groups['nfl']['count_total'] == 1
    
    def test_sport_column_default_values(self, bets_logger):
        """Test that sport column defaults to 'nba' when not specified."""
        # Log bet without sport parameter (should default to 'nba')
        bet_id = bets_logger.log_parlay_leg(
            parlay_id="default_sport_test",
            game_id="default_game",
            leg_description="Lakers ML",
            odds=-110.0,
            stake=100.0,
            predicted_outcome="Lakers win"
            # sport parameter omitted - should default to 'nba'
        )
        
        # Verify sport defaulted to 'nba'
        cursor = bets_logger.connection.cursor()
        cursor.execute("SELECT sport FROM bets WHERE bet_id = ?", (bet_id,))
        row = cursor.fetchone()
        assert row[0] == 'nba'
    
    def test_database_indexes_performance(self, temp_db_path):
        """Test that sport indexes improve query performance."""
        # Run migration to ensure indexes exist
        from migrations.add_sport_column import migrate_database
        migrate_database(temp_db_path, dry_run=False)
        
        # Create test data
        logger = BetsLogger(temp_db_path)
        logger.connect()
        
        # Add multiple bets for each sport
        for i in range(100):
            logger.log_parlay_leg(
                parlay_id=f"bulk_nba_{i}",
                game_id=f"nba_game_{i}",
                leg_description=f"Team {i} ML",
                odds=-110.0,
                stake=100.0,
                predicted_outcome=f"Team {i} win",
                sport="nba"
            )
            
            logger.log_parlay_leg(
                parlay_id=f"bulk_nfl_{i}",
                game_id=f"nfl_game_{i}",
                leg_description=f"Team {i} ML",
                odds=-110.0,
                stake=100.0,
                predicted_outcome=f"Team {i} win",
                sport="nfl"
            )
        
        logger.close()
        
        # Test query performance with index
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        
        # Enable query planner output
        cursor.execute("EXPLAIN QUERY PLAN SELECT * FROM bets WHERE sport = 'nba'")
        plan = cursor.fetchall()
        
        # Check that index is being used (SEARCH using index)
        plan_text = ' '.join(str(row) for row in plan)
        assert 'idx_bets_sport' in plan_text or 'USING INDEX' in plan_text.upper()
        
        conn.close()
    
    def test_backward_compatibility(self, temp_db_path):
        """Test that the system works with legacy data (no sport column)."""
        # Create database without sport column (simulate legacy state)
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        
        # Create old-style bets table without sport column
        cursor.execute("""
            CREATE TABLE bets (
                bet_id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT NOT NULL,
                parlay_id TEXT NOT NULL,
                leg_description TEXT NOT NULL,
                odds REAL NOT NULL,
                stake REAL NOT NULL,
                predicted_outcome TEXT NOT NULL,
                actual_outcome TEXT,
                is_win INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Insert legacy data
        cursor.execute("""
            INSERT INTO bets (game_id, parlay_id, leg_description, odds, stake, 
                             predicted_outcome, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ("legacy_game", "legacy_parlay", "Legacy Team ML", 110.0, 100.0,
              "Legacy prediction", "2024-01-01T00:00:00Z", "2024-01-01T00:00:00Z"))
        
        conn.commit()
        conn.close()
        
        # Test performance reporter with legacy data
        rows = load_rows(temp_db_path, sport="all")
        assert len(rows) == 1
        
        # Test grouping by sport with legacy data (should default to 'nba')
        groups = rollup_metrics(rows, "sport", include_open=True)
        assert 'nba' in groups  # Should default to NBA for legacy data
        assert groups['nba']['count_total'] == 1
    
    def teardown_method(self, method):
        """Clean up after each test."""
        # Close any open database connections
        import gc
        gc.collect()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
