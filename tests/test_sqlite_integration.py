#!/usr/bin/env python3
"""
Integration tests for SQLite parlay workflow.

Tests the complete SQLite-based parlay logging, settlement, and reporting system.
"""

import unittest
import tempfile
import os
from pathlib import Path
import sys

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from tools.bets_logger import BetsLogger


class TestSQLiteIntegration(unittest.TestCase):
    """Integration tests for SQLite parlay workflow."""
    
    def setUp(self):
        """Set up test database."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
        self.temp_db.close()
        self.db_path = self.temp_db.name
    
    def tearDown(self):
        """Clean up test database."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_complete_parlay_workflow(self):
        """Test the complete parlay workflow from logging to reporting."""
        
        # Step 1: Log parlay legs
        with BetsLogger(self.db_path) as logger:
            # Log first parlay leg
            bet_id_1 = logger.log_parlay_leg(
                parlay_id="test_parlay_1",
                game_id="game_001",
                leg_description="Lakers ML @ 1.85",
                odds=1.85,
                stake=100.0,
                predicted_outcome="Lakers win"
            )
            
            # Log second parlay leg
            bet_id_2 = logger.log_parlay_leg(
                parlay_id="test_parlay_1",
                game_id="game_002", 
                leg_description="Celtics -5.5 @ 1.91",
                odds=1.91,
                stake=100.0,
                predicted_outcome="Celtics cover"
            )
            
            self.assertIsInstance(bet_id_1, int)
            self.assertIsInstance(bet_id_2, int)
            self.assertNotEqual(bet_id_1, bet_id_2)
        
        # Step 2: Verify bets are logged as open
        with BetsLogger(self.db_path) as logger:
            open_bets = logger.fetch_open_bets()
            self.assertEqual(len(open_bets), 2)
            
            # Check first bet
            bet_1 = next(bet for bet in open_bets if bet['bet_id'] == bet_id_1)
            self.assertEqual(bet_1['parlay_id'], "test_parlay_1")
            self.assertEqual(bet_1['game_id'], "game_001")
            self.assertEqual(bet_1['odds'], 1.85)
            self.assertEqual(bet_1['stake'], 100.0)
            self.assertIsNone(bet_1['is_win'])
            self.assertIsNone(bet_1['actual_outcome'])
        
        # Step 3: Settle bets
        with BetsLogger(self.db_path) as logger:
            # Settle first bet as win
            logger.update_bet_outcome(
                bet_id=bet_id_1,
                actual_outcome="Lakers won 110-105",
                is_win=True
            )
            
            # Settle second bet as loss
            logger.update_bet_outcome(
                bet_id=bet_id_2,
                actual_outcome="Celtics won 108-106 (did not cover -5.5)",
                is_win=False
            )
        
        # Step 4: Verify bets are settled
        with BetsLogger(self.db_path) as logger:
            open_bets = logger.fetch_open_bets()
            self.assertEqual(len(open_bets), 0)  # No more open bets
            
            # Query all bets
            cursor = logger.connection.cursor()
            cursor.execute("SELECT * FROM bets ORDER BY bet_id")
            all_bets = cursor.fetchall()
            
            self.assertEqual(len(all_bets), 2)
            
            # Check settled bet 1 (win)
            bet_1 = all_bets[0]
            self.assertEqual(bet_1['is_win'], 1)
            self.assertEqual(bet_1['actual_outcome'], "Lakers won 110-105")
            
            # Check settled bet 2 (loss)
            bet_2 = all_bets[1]
            self.assertEqual(bet_2['is_win'], 0)
            self.assertEqual(bet_2['actual_outcome'], "Celtics won 108-106 (did not cover -5.5)")
        
        # Step 5: Test CLV calculation
        with BetsLogger(self.db_path) as logger:
            # Set closing line for first bet
            logger.set_closing_line(bet_id_1, 1.80)  # Closed lower than opening
            
            # Set closing line for second bet  
            logger.set_closing_line(bet_id_2, 1.95)  # Closed higher than opening
            
            # Verify CLV calculations
            cursor = logger.connection.cursor()
            cursor.execute("SELECT bet_id, odds_at_alert, closing_line_odds, clv_percentage FROM bets ORDER BY bet_id")
            clv_data = cursor.fetchall()
            
            # First bet: opened at 1.85, closed at 1.80 -> positive CLV (got better odds than close)
            bet_1_clv = clv_data[0]
            self.assertEqual(bet_1_clv['odds_at_alert'], 1.85)
            self.assertEqual(bet_1_clv['closing_line_odds'], 1.80)
            self.assertGreater(bet_1_clv['clv_percentage'], 0)  # Positive CLV (beat the close)
            
            # Second bet: opened at 1.91, closed at 1.95 -> negative CLV (worse odds than close)
            bet_2_clv = clv_data[1]
            self.assertEqual(bet_2_clv['odds_at_alert'], 1.91)
            self.assertEqual(bet_2_clv['closing_line_odds'], 1.95)
            self.assertLess(bet_2_clv['clv_percentage'], 0)  # Negative CLV (worse than close)
    
    def test_bulk_parlay_logging(self):
        """Test logging multiple legs of a parlay in bulk."""
        
        legs_data = [
            {
                'leg_description': 'Lakers ML @ 1.85',
                'odds': 1.85,
                'stake': 50.0,
                'predicted_outcome': 'Lakers win'
            },
            {
                'leg_description': 'Celtics -5.5 @ 1.91',
                'odds': 1.91,
                'stake': 50.0,
                'predicted_outcome': 'Celtics cover'
            },
            {
                'leg_description': 'Over 220.5 @ 1.95',
                'odds': 1.95,
                'stake': 50.0,
                'predicted_outcome': 'Total over 220.5'
            }
        ]
        
        with BetsLogger(self.db_path) as logger:
            bet_ids = logger.log_parlay(
                parlay_id="bulk_parlay_test",
                game_id="game_bulk",
                legs=legs_data
            )
            
            self.assertEqual(len(bet_ids), 3)
            self.assertTrue(all(isinstance(bet_id, int) for bet_id in bet_ids))
            
            # Verify all legs were logged
            open_bets = logger.fetch_open_bets(parlay_id="bulk_parlay_test")
            self.assertEqual(len(open_bets), 3)
            
            # Check that all legs have the same parlay_id
            for bet in open_bets:
                self.assertEqual(bet['parlay_id'], "bulk_parlay_test")
                self.assertEqual(bet['game_id'], "game_bulk")
    
    def test_upsert_outcome_by_keys(self):
        """Test updating bet outcomes by parlay_id and leg_description."""
        
        with BetsLogger(self.db_path) as logger:
            # Log a bet
            logger.log_parlay_leg(
                parlay_id="upsert_test",
                game_id="game_upsert",
                leg_description="Test Bet @ 2.00",
                odds=2.00,
                stake=25.0,
                predicted_outcome="Test outcome"
            )
            
            # Update using upsert method
            affected = logger.upsert_outcome_by_keys(
                parlay_id="upsert_test",
                leg_description="Test Bet @ 2.00",
                actual_outcome="Test result",
                is_win=True
            )
            
            self.assertEqual(affected, 1)
            
            # Verify the update
            open_bets = logger.fetch_open_bets()
            self.assertEqual(len(open_bets), 0)  # Should be no open bets
            
            # Check the settled bet
            cursor = logger.connection.cursor()
            cursor.execute("SELECT * FROM bets WHERE parlay_id = ?", ("upsert_test",))
            bet = cursor.fetchone()
            
            self.assertEqual(bet['is_win'], 1)
            self.assertEqual(bet['actual_outcome'], "Test result")
    
    def test_clv_computation(self):
        """Test CLV computation logic."""
        
        with BetsLogger(self.db_path) as logger:
            # Test positive CLV (beat the closing line)
            clv_positive = logger.compute_clv(odds_at_alert=2.00, closing_line_odds=1.90)
            self.assertAlmostEqual(clv_positive, 5.2632, places=3)  # (2.00-1.90)/1.90 * 100
            
            # Test negative CLV (worse than closing line)
            clv_negative = logger.compute_clv(odds_at_alert=1.80, closing_line_odds=1.90)
            self.assertAlmostEqual(clv_negative, -5.2632, places=3)  # (1.80-1.90)/1.90 * 100
            
            # Test zero CLV (same as closing line)
            clv_zero = logger.compute_clv(odds_at_alert=1.90, closing_line_odds=1.90)
            self.assertEqual(clv_zero, 0.0)
    
    def test_database_schema_migration(self):
        """Test that schema migration works correctly."""
        
        # Create database with initial schema (without CLV columns)
        with BetsLogger(self.db_path) as logger:
            cursor = logger.connection.cursor()
            
            # Check that CLV columns exist after initialization
            cursor.execute("PRAGMA table_info(bets)")
            columns = {row[1] for row in cursor.fetchall()}
            
            self.assertIn('odds_at_alert', columns)
            self.assertIn('closing_line_odds', columns)
            self.assertIn('clv_percentage', columns)
    
    def test_fetch_bets_missing_clv(self):
        """Test fetching bets that are missing CLV data."""
        
        with BetsLogger(self.db_path) as logger:
            # Log some bets
            bet_id_1 = logger.log_parlay_leg(
                parlay_id="clv_test_1",
                game_id="game_clv_1",
                leg_description="Bet 1 @ 1.85",
                odds=1.85,
                stake=100.0,
                predicted_outcome="Outcome 1"
            )
            
            bet_id_2 = logger.log_parlay_leg(
                parlay_id="clv_test_2",
                game_id="game_clv_2",
                leg_description="Bet 2 @ 1.91",
                odds=1.91,
                stake=100.0,
                predicted_outcome="Outcome 2"
            )
            
            # Set CLV for first bet only
            logger.set_closing_line(bet_id_1, 1.80)
            
            # Fetch bets missing CLV
            missing_clv = logger.fetch_bets_missing_clv()
            
            self.assertEqual(len(missing_clv), 1)
            self.assertEqual(missing_clv[0]['bet_id'], bet_id_2)
    
    def test_context_manager(self):
        """Test that BetsLogger works correctly as a context manager."""
        
        # Test successful context manager usage
        with BetsLogger(self.db_path) as logger:
            self.assertIsNotNone(logger.connection)
            
            bet_id = logger.log_parlay_leg(
                parlay_id="context_test",
                game_id="game_context",
                leg_description="Context Test @ 2.00",
                odds=2.00,
                stake=50.0,
                predicted_outcome="Context outcome"
            )
            
            self.assertIsInstance(bet_id, int)
        
        # After context manager, connection should be closed
        # (We can't directly test this without accessing private attributes)
        
        # Verify data was persisted
        with BetsLogger(self.db_path) as logger:
            open_bets = logger.fetch_open_bets(parlay_id="context_test")
            self.assertEqual(len(open_bets), 1)
            self.assertEqual(open_bets[0]['leg_description'], "Context Test @ 2.00")


if __name__ == '__main__':
    # Set up logging for tests
    import logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise during tests
    
    # Run tests
    unittest.main(verbosity=2)
