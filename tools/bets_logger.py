#!/usr/bin/env python3
"""
BetsLogger - SQLite logging layer for parlay bets and outcomes.
"""

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class BetsLogger:
    """SQLite-based logger for parlay bets and outcomes."""
    
    def __init__(self, db_path: Union[str, Path] = "data/parlays.sqlite"):
        """
        Initialize BetsLogger with SQLite database.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection: Optional[sqlite3.Connection] = None
        
        logger.info(f"BetsLogger initialized with database: {self.db_path}")
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def connect(self) -> None:
        """Establish database connection with proper configuration."""
        self.connection = sqlite3.connect(str(self.db_path))
        self.connection.row_factory = sqlite3.Row
        
        # Configure for better performance and safety
        cursor = self.connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        
        self.ensure_schema()
        logger.debug("Database connection established")
    
    def close(self) -> None:
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.debug("Database connection closed")
    
    def ensure_schema(self) -> None:
        """Create database schema if it doesn't exist."""
        if not self.connection:
            raise RuntimeError("Database connection not established")
        
        cursor = self.connection.cursor()
        
        # Create bets table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bets (
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
                updated_at TEXT NOT NULL,
                odds_at_alert REAL,
                closing_line_odds REAL,
                clv_percentage REAL,
                sport TEXT DEFAULT 'nba'
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bets_parlay_id ON bets(parlay_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bets_game_id ON bets(game_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bets_sport ON bets(sport)")
        
        # Migrate existing schema if needed
        self._migrate_schema()
        
        self.connection.commit()
        logger.info("Database schema ensured")
    
    def _migrate_schema(self) -> None:
        """Migrate existing schema to add CLV and sport columns."""
        cursor = self.connection.cursor()
        
        # Check if CLV columns exist
        cursor.execute("PRAGMA table_info(bets)")
        columns = {row[1] for row in cursor.fetchall()}
        
        if 'odds_at_alert' not in columns:
            logger.info("Adding CLV columns to existing schema")
            
            # Add new columns
            cursor.execute("ALTER TABLE bets ADD COLUMN odds_at_alert REAL")
            cursor.execute("ALTER TABLE bets ADD COLUMN closing_line_odds REAL")
            cursor.execute("ALTER TABLE bets ADD COLUMN clv_percentage REAL")
            
            # Backfill odds_at_alert from odds
            cursor.execute("UPDATE bets SET odds_at_alert = odds WHERE odds_at_alert IS NULL")
            
            logger.info("CLV columns migration completed")
        
        # Check if sport column exists
        if 'sport' not in columns:
            logger.info("Adding sport column to existing schema")
            
            # Add sport column
            cursor.execute("ALTER TABLE bets ADD COLUMN sport TEXT DEFAULT 'nba'")
            
            # Create sport index
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bets_sport ON bets(sport)")
            
            # Backfill sport column for existing records
            cursor.execute("UPDATE bets SET sport = 'nba' WHERE sport IS NULL")
            
            logger.info("Sport column migration completed")
    
    def _get_utc_timestamp(self) -> str:
        """Get current UTC timestamp in ISO format."""
        return datetime.now(timezone.utc).isoformat()
    
    def log_parlay_leg(self, parlay_id: str, game_id: str, leg_description: str, 
                      odds: float, stake: float, predicted_outcome: str, sport: str = "nba") -> int:
        """
        Log a single parlay leg.
        
        Args:
            parlay_id: Unique identifier for the parlay
            game_id: Game identifier
            leg_description: Description of the bet leg
            odds: Decimal odds for this leg
            stake: Amount wagered on this leg
            predicted_outcome: Human-readable prediction
            sport: Sport type ('nba' or 'nfl', defaults to 'nba')
            
        Returns:
            bet_id of the inserted row
        """
        if not self.connection:
            raise RuntimeError("Database connection not established")
        
        timestamp = self._get_utc_timestamp()
        
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO bets (
                game_id, parlay_id, leg_description, odds, stake, 
                predicted_outcome, sport, created_at, updated_at, odds_at_alert
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (game_id, parlay_id, leg_description, odds, stake, 
              predicted_outcome, sport, timestamp, timestamp, odds))
        
        bet_id = cursor.lastrowid
        self.connection.commit()
        
        logger.debug(f"Logged parlay leg: bet_id={bet_id}, parlay_id={parlay_id}, game_id={game_id}")
        return bet_id
    
    def log_parlay(self, parlay_id: str, game_id: str, legs: List[Dict], sport: str = "nba") -> List[int]:
        """
        Log multiple legs of a parlay in bulk.
        
        Args:
            parlay_id: Unique identifier for the parlay
            game_id: Game identifier
            legs: List of leg dictionaries with keys: leg_description, odds, stake, predicted_outcome
            sport: Sport type ('nba' or 'nfl', defaults to 'nba')
            
        Returns:
            List of bet_ids for the inserted rows
        """
        if not self.connection:
            raise RuntimeError("Database connection not established")
        
        bet_ids = []
        timestamp = self._get_utc_timestamp()
        
        cursor = self.connection.cursor()
        
        for leg in legs:
            cursor.execute("""
                INSERT INTO bets (
                    game_id, parlay_id, leg_description, odds, stake, 
                    predicted_outcome, sport, created_at, updated_at, odds_at_alert
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (game_id, parlay_id, leg['leg_description'], leg['odds'], 
                  leg['stake'], leg['predicted_outcome'], sport, timestamp, timestamp, leg['odds']))
            
            bet_ids.append(cursor.lastrowid)
        
        self.connection.commit()
        
        logger.debug(f"Logged parlay: parlay_id={parlay_id}, game_id={game_id}, legs={len(legs)}")
        return bet_ids
    
    def fetch_open_bets(self, game_id: Optional[str] = None, 
                       parlay_id: Optional[str] = None, sport: Optional[str] = None) -> List[sqlite3.Row]:
        """
        Fetch unsettled bets (where is_win IS NULL).
        
        Args:
            game_id: Optional filter by game_id
            parlay_id: Optional filter by parlay_id
            sport: Optional filter by sport ('nba' or 'nfl')
            
        Returns:
            List of unsettled bet rows
        """
        if not self.connection:
            raise RuntimeError("Database connection not established")
        
        query = "SELECT * FROM bets WHERE is_win IS NULL"
        params = []
        
        if game_id:
            query += " AND game_id = ?"
            params.append(game_id)
        
        if parlay_id:
            query += " AND parlay_id = ?"
            params.append(parlay_id)
        
        if sport:
            query += " AND sport = ?"
            params.append(sport)
        
        query += " ORDER BY created_at DESC"
        
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        
        rows = cursor.fetchall()
        logger.debug(f"Fetched {len(rows)} open bets")
        return rows
    
    def update_bet_outcome(self, bet_id: int, actual_outcome: str, is_win: bool) -> None:
        """
        Update bet outcome and win status.
        
        Args:
            bet_id: ID of the bet to update
            actual_outcome: Actual result description
            is_win: Whether the bet won (True) or lost (False)
        """
        if not self.connection:
            raise RuntimeError("Database connection not established")
        
        timestamp = self._get_utc_timestamp()
        is_win_int = 1 if is_win else 0
        
        cursor = self.connection.cursor()
        cursor.execute("""
            UPDATE bets 
            SET actual_outcome = ?, is_win = ?, updated_at = ?
            WHERE bet_id = ?
        """, (actual_outcome, is_win_int, timestamp, bet_id))
        
        if cursor.rowcount == 0:
            raise ValueError(f"Bet with ID {bet_id} not found")
        
        self.connection.commit()
        logger.debug(f"Updated bet outcome: bet_id={bet_id}, is_win={is_win}")
    
    def upsert_outcome_by_keys(self, parlay_id: str, leg_description: str, 
                              actual_outcome: str, is_win: bool) -> int:
        """
        Update bet outcome by parlay_id and leg_description.
        
        Args:
            parlay_id: Parlay identifier
            leg_description: Leg description to match
            actual_outcome: Actual result description
            is_win: Whether the bet won (True) or lost (False)
            
        Returns:
            Number of affected rows
        """
        if not self.connection:
            raise RuntimeError("Database connection not established")
        
        timestamp = self._get_utc_timestamp()
        is_win_int = 1 if is_win else 0
        
        cursor = self.connection.cursor()
        cursor.execute("""
            UPDATE bets 
            SET actual_outcome = ?, is_win = ?, updated_at = ?
            WHERE parlay_id = ? AND leg_description = ? AND is_win IS NULL
        """, (actual_outcome, is_win_int, timestamp, parlay_id, leg_description))
        
        affected_count = cursor.rowcount
        self.connection.commit()
        
        logger.debug(f"Upserted outcome: parlay_id={parlay_id}, leg={leg_description}, affected={affected_count}")
        return affected_count
    
    def compute_clv(self, odds_at_alert: float, closing_line_odds: float) -> float:
        """
        Compute CLV (Closing Line Value) percentage.
        
        Args:
            odds_at_alert: Odds when the bet was placed
            closing_line_odds: Odds at closing time
            
        Returns:
            CLV percentage (positive means you beat the close)
        """
        if closing_line_odds <= 0:
            raise ValueError("Closing line odds must be positive")
        
        clv = ((odds_at_alert - closing_line_odds) / closing_line_odds) * 100.0
        return round(clv, 4)
    
    def set_closing_line(self, bet_id: int, closing_line_odds: float) -> None:
        """
        Set closing line odds and compute CLV.
        
        Args:
            bet_id: ID of the bet to update
            closing_line_odds: Closing line odds
        """
        if not self.connection:
            raise RuntimeError("Database connection not established")
        
        # Get odds_at_alert for this bet
        cursor = self.connection.cursor()
        cursor.execute("SELECT odds_at_alert FROM bets WHERE bet_id = ?", (bet_id,))
        row = cursor.fetchone()
        
        if not row:
            raise ValueError(f"Bet with ID {bet_id} not found")
        
        odds_at_alert = row[0]
        if odds_at_alert is None:
            raise ValueError(f"Bet {bet_id} has no odds_at_alert value")
        
        # Compute CLV
        clv_percentage = self.compute_clv(odds_at_alert, closing_line_odds)
        
        # Update the bet
        timestamp = self._get_utc_timestamp()
        cursor.execute("""
            UPDATE bets 
            SET closing_line_odds = ?, clv_percentage = ?, updated_at = ?
            WHERE bet_id = ?
        """, (closing_line_odds, clv_percentage, timestamp, bet_id))
        
        if cursor.rowcount == 0:
            raise ValueError(f"Bet with ID {bet_id} not found")
        
        self.connection.commit()
        logger.debug(f"Set closing line: bet_id={bet_id}, closing_odds={closing_line_odds}, clv={clv_percentage}%")
    
    def fetch_bets_missing_clv(self, game_ids: Optional[List[str]] = None, 
                              since_iso: Optional[str] = None) -> List[sqlite3.Row]:
        """
        Fetch bets that are missing closing line odds.
        
        Args:
            game_ids: Optional filter by game IDs
            since_iso: Optional filter by creation date (ISO format)
            
        Returns:
            List of bets missing CLV data
        """
        if not self.connection:
            raise RuntimeError("Database connection not established")
        
        query = """
            SELECT * FROM bets 
            WHERE odds_at_alert IS NOT NULL 
            AND closing_line_odds IS NULL
        """
        params = []
        
        if game_ids:
            placeholders = ','.join(['?' for _ in game_ids])
            query += f" AND game_id IN ({placeholders})"
            params.extend(game_ids)
        
        if since_iso:
            query += " AND created_at >= ?"
            params.append(since_iso)
        
        query += " ORDER BY created_at DESC"
        
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        
        rows = cursor.fetchall()
        logger.debug(f"Fetched {len(rows)} bets missing CLV")
        return rows
    
    def fetch_bets_by_sport(self, sport: str, limit: Optional[int] = None) -> List[sqlite3.Row]:
        """
        Fetch bets filtered by sport.
        
        Args:
            sport: Sport to filter by ('nba' or 'nfl')
            limit: Optional limit on number of results
            
        Returns:
            List of bet rows for the specified sport
        """
        if not self.connection:
            raise RuntimeError("Database connection not established")
        
        query = "SELECT * FROM bets WHERE sport = ? ORDER BY created_at DESC"
        params = [sport]
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        
        rows = cursor.fetchall()
        logger.debug(f"Fetched {len(rows)} bets for sport {sport}")
        return rows
    
    def get_sports_summary(self) -> Dict[str, Dict[str, int]]:
        """
        Get summary statistics by sport.
        
        Returns:
            Dictionary with sport-specific statistics
        """
        if not self.connection:
            raise RuntimeError("Database connection not established")
        
        cursor = self.connection.cursor()
        
        # Get total bets by sport
        cursor.execute("""
            SELECT 
                sport,
                COUNT(*) as total_bets,
                COUNT(CASE WHEN is_win = 1 THEN 1 END) as wins,
                COUNT(CASE WHEN is_win = 0 THEN 1 END) as losses,
                COUNT(CASE WHEN is_win IS NULL THEN 1 END) as pending
            FROM bets 
            GROUP BY sport
        """)
        
        results = {}
        for row in cursor.fetchall():
            sport = row[0] or 'unknown'
            results[sport] = {
                'total_bets': row[1],
                'wins': row[2],
                'losses': row[3],
                'pending': row[4],
                'win_rate': row[2] / (row[2] + row[3]) if (row[2] + row[3]) > 0 else 0.0
            }
        
        logger.debug(f"Sports summary: {results}")
        return results
