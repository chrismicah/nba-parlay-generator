#!/usr/bin/env python3
"""
Migration Script: Add Sport Column to SQLite Schema
JIRA-NFL-006 - Add Sport Segmentation to SQLite Schema

This script adds the 'sport' column to the bets and arbitrage_opportunities tables
to support multi-sport data tracking (NBA + NFL).
"""

import sqlite3
import logging
import sys
from pathlib import Path
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def migrate_database(db_path: str, dry_run: bool = False):
    """
    Apply sport column migration to database.
    
    Args:
        db_path: Path to SQLite database file
        dry_run: If True, only show what would be done without making changes
    """
    logger.info(f"Starting migration for database: {db_path}")
    
    if dry_run:
        logger.info("DRY RUN MODE - No changes will be made")
    
    # Connect to database
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Enable foreign key support
        cursor.execute("PRAGMA foreign_keys=ON")
        
        # Check current schema
        logger.info("Checking current database schema...")
        
        # Check if bets table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bets'")
        bets_exists = cursor.fetchone() is not None
        
        # Check if arbitrage_opportunities table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='arbitrage_opportunities'")
        arbitrage_exists = cursor.fetchone() is not None
        
        logger.info(f"Tables found - bets: {bets_exists}, arbitrage_opportunities: {arbitrage_exists}")
        
        # Migrate bets table
        if bets_exists:
            # Check if sport column already exists
            cursor.execute("PRAGMA table_info(bets)")
            columns = {row[1] for row in cursor.fetchall()}
            
            if 'sport' not in columns:
                logger.info("Adding sport column to bets table...")
                
                if not dry_run:
                    # Add sport column with default value 'nba'
                    cursor.execute("ALTER TABLE bets ADD COLUMN sport TEXT DEFAULT 'nba'")
                    
                    # Create index on sport column
                    cursor.execute("CREATE INDEX idx_bets_sport ON bets(sport)")
                    
                    # Update any existing records to have sport='nba'
                    cursor.execute("UPDATE bets SET sport = 'nba' WHERE sport IS NULL")
                    
                    logger.info("✅ Successfully added sport column to bets table")
                else:
                    logger.info("[DRY RUN] Would add sport column to bets table")
            else:
                logger.info("Sport column already exists in bets table")
        else:
            logger.warning("Bets table does not exist - will be created with sport column by bets_logger.py")
        
        # Create or migrate arbitrage_opportunities table
        if arbitrage_exists:
            # Check if sport column exists
            cursor.execute("PRAGMA table_info(arbitrage_opportunities)")
            columns = {row[1] for row in cursor.fetchall()}
            
            if 'sport' not in columns:
                logger.info("Adding sport column to arbitrage_opportunities table...")
                
                if not dry_run:
                    cursor.execute("ALTER TABLE arbitrage_opportunities ADD COLUMN sport TEXT DEFAULT 'nba'")
                    cursor.execute("CREATE INDEX idx_arbitrage_sport ON arbitrage_opportunities(sport)")
                    cursor.execute("UPDATE arbitrage_opportunities SET sport = 'nba' WHERE sport IS NULL")
                    
                    logger.info("✅ Successfully added sport column to arbitrage_opportunities table")
                else:
                    logger.info("[DRY RUN] Would add sport column to arbitrage_opportunities table")
            else:
                logger.info("Sport column already exists in arbitrage_opportunities table")
        else:
            logger.info("Creating arbitrage_opportunities table with sport column...")
            
            if not dry_run:
                # Create arbitrage_opportunities table with sport column
                cursor.execute("""
                    CREATE TABLE arbitrage_opportunities (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        game_id TEXT NOT NULL,
                        market_type TEXT NOT NULL,
                        sport TEXT NOT NULL DEFAULT 'nba',
                        detection_timestamp TEXT NOT NULL,
                        profit_percentage REAL NOT NULL,
                        guaranteed_profit REAL NOT NULL,
                        total_investment REAL NOT NULL,
                        risk_level TEXT NOT NULL,
                        sportsbooks_involved TEXT NOT NULL,
                        bets_required TEXT NOT NULL,
                        expires_at TEXT,
                        is_active INTEGER DEFAULT 1,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                
                # Create indexes
                cursor.execute("CREATE INDEX idx_arbitrage_game_id ON arbitrage_opportunities(game_id)")
                cursor.execute("CREATE INDEX idx_arbitrage_sport ON arbitrage_opportunities(sport)")
                cursor.execute("CREATE INDEX idx_arbitrage_active ON arbitrage_opportunities(is_active)")
                cursor.execute("CREATE INDEX idx_arbitrage_timestamp ON arbitrage_opportunities(detection_timestamp)")
                
                logger.info("✅ Successfully created arbitrage_opportunities table with sport column")
            else:
                logger.info("[DRY RUN] Would create arbitrage_opportunities table with sport column")
        
        # Commit changes
        if not dry_run:
            conn.commit()
            logger.info("✅ Migration completed successfully")
        else:
            logger.info("✅ Dry run completed - no changes made")
        
        # Show final schema info
        logger.info("\nFinal schema summary:")
        
        if bets_exists or not dry_run:
            cursor.execute("PRAGMA table_info(bets)")
            bets_columns = [row[1] for row in cursor.fetchall()]
            logger.info(f"bets table columns: {', '.join(bets_columns)}")
        
        if arbitrage_exists or not dry_run:
            cursor.execute("PRAGMA table_info(arbitrage_opportunities)")
            arb_columns = [row[1] for row in cursor.fetchall()]
            logger.info(f"arbitrage_opportunities table columns: {', '.join(arb_columns)}")
    
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        if not dry_run:
            conn.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if not dry_run:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def main():
    """Main migration function."""
    print("🏈 JIRA-NFL-006: Add Sport Segmentation to SQLite Schema")
    print("=" * 60)
    
    # Database paths to migrate
    databases = [
        "data/parlays.sqlite",
        "data/demo_parlays.sqlite"
    ]
    
    # Check if dry run is requested
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    
    if dry_run:
        print("🔍 DRY RUN MODE: Will show what changes would be made")
        print("-" * 60)
    
    for db_path in databases:
        db_file = Path(db_path)
        
        print(f"\n📊 Processing database: {db_path}")
        print("-" * 40)
        
        if not db_file.exists():
            logger.warning(f"Database does not exist: {db_path}")
            if not dry_run:
                logger.info(f"Creating new database: {db_path}")
                # Touch the file to create it
                db_file.parent.mkdir(parents=True, exist_ok=True)
                db_file.touch()
        
        try:
            migrate_database(db_path, dry_run=dry_run)
            print(f"✅ Migration completed for {db_path}")
        except Exception as e:
            print(f"❌ Migration failed for {db_path}: {e}")
            logger.error(f"Failed to migrate {db_path}", exc_info=True)
    
    print(f"\n🎯 Migration Summary")
    print("-" * 40)
    if dry_run:
        print("Dry run completed. Use without --dry-run to apply changes.")
    else:
        print("All migrations completed!")
        print("\n📝 Next Steps:")
        print("1. Update ParlayStrategistAgent to include sport in inserts")
        print("2. Update ArbitrageDetectorTool to include sport in inserts")
        print("3. Modify performance_reporter.py to group metrics by sport")
        print("4. Run tests to verify schema changes")

if __name__ == "__main__":
    main()
