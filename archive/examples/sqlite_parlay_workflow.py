#!/usr/bin/env python3
"""
Complete SQLite Parlay Workflow Example

Demonstrates the full parlay lifecycle using SQLite:
1. Log parlay legs to database
2. Settle bets with actual outcomes
3. Generate performance reports
4. Calculate CLV (Closing Line Value)

This replaces the previous CSV-based workflow with persistent SQLite storage.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any
import uuid

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from tools.bets_logger import BetsLogger
from tools.parlay_builder import ParlayLeg


def generate_sample_parlay_data() -> List[Dict[str, Any]]:
    """Generate sample parlay data for demonstration."""
    
    # Sample parlay 1: 3-leg NBA parlay
    parlay_1_id = f"parlay_{uuid.uuid4().hex[:8]}"
    parlay_1_legs = [
        {
            'game_id': 'nba_game_001',
            'parlay_id': parlay_1_id,
            'leg_description': 'Lakers ML @ 1.85 [Book: DraftKings]',
            'odds': 1.85,
            'stake': 50.0,
            'predicted_outcome': 'Lakers win'
        },
        {
            'game_id': 'nba_game_002', 
            'parlay_id': parlay_1_id,
            'leg_description': 'Celtics -5.5 @ 1.91 [Book: FanDuel]',
            'odds': 1.91,
            'stake': 50.0,
            'predicted_outcome': 'Celtics cover -5.5'
        },
        {
            'game_id': 'nba_game_003',
            'parlay_id': parlay_1_id, 
            'leg_description': 'Over 220.5 @ 1.95 [Book: BetMGM]',
            'odds': 1.95,
            'stake': 50.0,
            'predicted_outcome': 'Total points over 220.5'
        }
    ]
    
    # Sample parlay 2: 2-leg NBA parlay
    parlay_2_id = f"parlay_{uuid.uuid4().hex[:8]}"
    parlay_2_legs = [
        {
            'game_id': 'nba_game_004',
            'parlay_id': parlay_2_id,
            'leg_description': 'Warriors +3.5 @ 1.88 [Book: DraftKings]',
            'odds': 1.88,
            'stake': 25.0,
            'predicted_outcome': 'Warriors cover +3.5'
        },
        {
            'game_id': 'nba_game_005',
            'parlay_id': parlay_2_id,
            'leg_description': 'Under 215.5 @ 1.92 [Book: FanDuel]', 
            'odds': 1.92,
            'stake': 25.0,
            'predicted_outcome': 'Total points under 215.5'
        }
    ]
    
    return parlay_1_legs + parlay_2_legs


def generate_sample_results() -> Dict[str, Dict[str, Any]]:
    """Generate sample game results for settlement."""
    return {
        'nba_game_001': {
            'Lakers ML @ 1.85 [Book: DraftKings]': {
                'actual_outcome': 'Lakers won 112-108',
                'is_win': True
            }
        },
        'nba_game_002': {
            'Celtics -5.5 @ 1.91 [Book: FanDuel]': {
                'actual_outcome': 'Celtics won 118-110 (covered -5.5)',
                'is_win': True
            }
        },
        'nba_game_003': {
            'Over 220.5 @ 1.95 [Book: BetMGM]': {
                'actual_outcome': 'Total: 225 points (over)',
                'is_win': True
            }
        },
        'nba_game_004': {
            'Warriors +3.5 @ 1.88 [Book: DraftKings]': {
                'actual_outcome': 'Warriors lost 105-110 (covered +3.5)',
                'is_win': True
            }
        },
        'nba_game_005': {
            'Under 215.5 @ 1.92 [Book: FanDuel]': {
                'actual_outcome': 'Total: 218 points (over)',
                'is_win': False
            }
        }
    }


def demonstrate_parlay_logging(db_path: str) -> List[int]:
    """Demonstrate logging parlay legs to SQLite database."""
    print("🏀 STEP 1: LOGGING PARLAY LEGS TO SQLITE")
    print("=" * 60)
    
    sample_legs = generate_sample_parlay_data()
    bet_ids = []
    
    with BetsLogger(db_path) as logger:
        for leg in sample_legs:
            bet_id = logger.log_parlay_leg(
                parlay_id=leg['parlay_id'],
                game_id=leg['game_id'],
                leg_description=leg['leg_description'],
                odds=leg['odds'],
                stake=leg['stake'],
                predicted_outcome=leg['predicted_outcome']
            )
            bet_ids.append(bet_id)
            print(f"✅ Logged bet_id {bet_id}: {leg['leg_description']}")
    
    print(f"\n📊 Successfully logged {len(bet_ids)} parlay legs")
    return bet_ids


def demonstrate_bet_settlement(db_path: str) -> None:
    """Demonstrate settling bets with actual outcomes."""
    print("\n🎯 STEP 2: SETTLING BETS WITH ACTUAL OUTCOMES")
    print("=" * 60)
    
    results = generate_sample_results()
    
    with BetsLogger(db_path) as logger:
        # Get all open bets
        open_bets = logger.fetch_open_bets()
        print(f"📋 Found {len(open_bets)} open bets to settle")
        
        settled_count = 0
        for bet in open_bets:
            game_id = bet['game_id']
            leg_description = bet['leg_description']
            
            if game_id in results and leg_description in results[game_id]:
                result = results[game_id][leg_description]
                
                logger.update_bet_outcome(
                    bet_id=bet['bet_id'],
                    actual_outcome=result['actual_outcome'],
                    is_win=result['is_win']
                )
                
                status = "✅ WIN" if result['is_win'] else "❌ LOSS"
                print(f"{status} bet_id {bet['bet_id']}: {result['actual_outcome']}")
                settled_count += 1
        
        print(f"\n📊 Successfully settled {settled_count} bets")


def demonstrate_clv_calculation(db_path: str) -> None:
    """Demonstrate CLV (Closing Line Value) calculation."""
    print("\n💰 STEP 3: CALCULATING CLV (CLOSING LINE VALUE)")
    print("=" * 60)
    
    # Sample closing line odds (typically different from opening odds)
    closing_odds_data = {
        1: 1.82,  # bet_id 1: opened at 1.85, closed at 1.82 (negative CLV)
        2: 1.95,  # bet_id 2: opened at 1.91, closed at 1.95 (positive CLV)
        3: 1.90,  # bet_id 3: opened at 1.95, closed at 1.90 (negative CLV)
        4: 1.92,  # bet_id 4: opened at 1.88, closed at 1.92 (positive CLV)
        5: 1.89   # bet_id 5: opened at 1.92, closed at 1.89 (negative CLV)
    }
    
    with BetsLogger(db_path) as logger:
        for bet_id, closing_odds in closing_odds_data.items():
            try:
                logger.set_closing_line(bet_id, closing_odds)
                
                # Calculate CLV manually for display
                # Get the original odds
                cursor = logger.connection.cursor()
                cursor.execute("SELECT odds_at_alert FROM bets WHERE bet_id = ?", (bet_id,))
                row = cursor.fetchone()
                
                if row:
                    opening_odds = row[0]
                    clv = logger.compute_clv(opening_odds, closing_odds)
                    clv_status = "📈 POSITIVE" if clv > 0 else "📉 NEGATIVE"
                    print(f"{clv_status} CLV bet_id {bet_id}: {opening_odds:.2f} → {closing_odds:.2f} ({clv:+.2f}%)")
                
            except Exception as e:
                print(f"⚠️ Could not set CLV for bet_id {bet_id}: {e}")
    
    print(f"\n📊 CLV calculation complete")


def demonstrate_performance_reporting(db_path: str) -> None:
    """Demonstrate performance reporting from SQLite."""
    print("\n📈 STEP 4: GENERATING PERFORMANCE REPORT")
    print("=" * 60)
    
    with BetsLogger(db_path) as logger:
        # Get all bets for analysis
        cursor = logger.connection.cursor()
        cursor.execute("""
            SELECT bet_id, parlay_id, game_id, leg_description, odds, stake,
                   is_win, actual_outcome, odds_at_alert, closing_line_odds, clv_percentage
            FROM bets 
            ORDER BY bet_id
        """)
        
        all_bets = cursor.fetchall()
        
        # Calculate overall metrics
        total_bets = len(all_bets)
        decided_bets = [bet for bet in all_bets if bet['is_win'] is not None]
        wins = [bet for bet in decided_bets if bet['is_win'] == 1]
        losses = [bet for bet in decided_bets if bet['is_win'] == 0]
        
        total_stake = sum(bet['stake'] for bet in decided_bets)
        total_winnings = sum(bet['stake'] * bet['odds'] for bet in wins)
        total_profit = total_winnings - total_stake
        
        roi = (total_profit / total_stake * 100) if total_stake > 0 else 0
        hit_rate = (len(wins) / len(decided_bets) * 100) if decided_bets else 0
        
        print(f"📊 OVERALL PERFORMANCE:")
        print(f"   Total Bets: {total_bets}")
        print(f"   Decided Bets: {len(decided_bets)}")
        print(f"   Wins: {len(wins)}")
        print(f"   Losses: {len(losses)}")
        print(f"   Total Stake: ${total_stake:.2f}")
        print(f"   Total Winnings: ${total_winnings:.2f}")
        print(f"   Total Profit: ${total_profit:+.2f}")
        print(f"   ROI: {roi:+.2f}%")
        print(f"   Hit Rate: {hit_rate:.1f}%")
        
        # CLV Analysis
        clv_bets = [bet for bet in all_bets if bet['clv_percentage'] is not None]
        if clv_bets:
            avg_clv = sum(bet['clv_percentage'] for bet in clv_bets) / len(clv_bets)
            positive_clv = [bet for bet in clv_bets if bet['clv_percentage'] > 0]
            
            print(f"\n💰 CLV ANALYSIS:")
            print(f"   Bets with CLV: {len(clv_bets)}")
            print(f"   Average CLV: {avg_clv:+.2f}%")
            print(f"   Positive CLV Bets: {len(positive_clv)} ({len(positive_clv)/len(clv_bets)*100:.1f}%)")
        
        # Parlay Analysis
        parlay_groups = {}
        for bet in decided_bets:
            parlay_id = bet['parlay_id']
            if parlay_id not in parlay_groups:
                parlay_groups[parlay_id] = []
            parlay_groups[parlay_id].append(bet)
        
        print(f"\n🎲 PARLAY ANALYSIS:")
        for parlay_id, legs in parlay_groups.items():
            all_won = all(leg['is_win'] == 1 for leg in legs)
            parlay_odds = 1.0
            for leg in legs:
                parlay_odds *= leg['odds']
            
            parlay_stake = legs[0]['stake'] * len(legs)  # Assuming equal stakes
            if all_won:
                parlay_profit = parlay_stake * parlay_odds - parlay_stake
                status = f"✅ WON ${parlay_profit:+.2f}"
            else:
                parlay_profit = -parlay_stake
                status = f"❌ LOST ${parlay_profit:+.2f}"
            
            print(f"   {parlay_id}: {len(legs)} legs @ {parlay_odds:.2f} - {status}")


def demonstrate_database_queries(db_path: str) -> None:
    """Demonstrate advanced database queries."""
    print("\n🔍 STEP 5: ADVANCED DATABASE QUERIES")
    print("=" * 60)
    
    with BetsLogger(db_path) as logger:
        cursor = logger.connection.cursor()
        
        # Query 1: Best performing bookmakers
        print("📚 PERFORMANCE BY BOOKMAKER:")
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN leg_description LIKE '%DraftKings%' THEN 'DraftKings'
                    WHEN leg_description LIKE '%FanDuel%' THEN 'FanDuel'
                    WHEN leg_description LIKE '%BetMGM%' THEN 'BetMGM'
                    ELSE 'Other'
                END as bookmaker,
                COUNT(*) as total_bets,
                SUM(CASE WHEN is_win = 1 THEN 1 ELSE 0 END) as wins,
                ROUND(AVG(CASE WHEN is_win = 1 THEN 100.0 ELSE 0.0 END), 1) as win_rate,
                ROUND(SUM(stake), 2) as total_stake,
                ROUND(SUM(CASE WHEN is_win = 1 THEN stake * odds ELSE 0 END) - SUM(stake), 2) as profit
            FROM bets 
            WHERE is_win IS NOT NULL
            GROUP BY bookmaker
            ORDER BY profit DESC
        """)
        
        for row in cursor.fetchall():
            print(f"   {row[0]}: {row[1]} bets, {row[2]} wins ({row[3]}%), ${row[5]:+.2f} profit")
        
        # Query 2: Performance by market type
        print(f"\n🎯 PERFORMANCE BY MARKET TYPE:")
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN leg_description LIKE '%ML%' OR leg_description LIKE '%moneyline%' THEN 'Moneyline'
                    WHEN leg_description LIKE '%+%' OR leg_description LIKE '%-%' OR leg_description LIKE '%spread%' THEN 'Spread'
                    WHEN leg_description LIKE '%Over%' OR leg_description LIKE '%Under%' OR leg_description LIKE '%total%' THEN 'Total'
                    ELSE 'Other'
                END as market_type,
                COUNT(*) as total_bets,
                SUM(CASE WHEN is_win = 1 THEN 1 ELSE 0 END) as wins,
                ROUND(AVG(CASE WHEN is_win = 1 THEN 100.0 ELSE 0.0 END), 1) as win_rate,
                ROUND(AVG(clv_percentage), 2) as avg_clv
            FROM bets 
            WHERE is_win IS NOT NULL
            GROUP BY market_type
            ORDER BY win_rate DESC
        """)
        
        for row in cursor.fetchall():
            clv_str = f", {row[4]:+.2f}% CLV" if row[4] is not None else ""
            print(f"   {row[0]}: {row[1]} bets, {row[2]} wins ({row[3]}%){clv_str}")


def main():
    """Main demonstration function."""
    print("🏀 COMPLETE SQLITE PARLAY WORKFLOW DEMONSTRATION")
    print("=" * 80)
    print("This example demonstrates the full parlay lifecycle using SQLite:")
    print("1. Log parlay legs to database")
    print("2. Settle bets with actual outcomes") 
    print("3. Calculate CLV (Closing Line Value)")
    print("4. Generate performance reports")
    print("5. Run advanced database queries")
    print()
    
    # Use temporary database for demo
    db_path = "data/demo_parlays.sqlite"
    
    try:
        # Clean up any existing demo database
        if Path(db_path).exists():
            Path(db_path).unlink()
        
        # Run the complete workflow
        bet_ids = demonstrate_parlay_logging(db_path)
        demonstrate_bet_settlement(db_path)
        demonstrate_clv_calculation(db_path)
        demonstrate_performance_reporting(db_path)
        demonstrate_database_queries(db_path)
        
        print("\n" + "=" * 80)
        print("✅ SQLITE WORKFLOW DEMONSTRATION COMPLETE!")
        print("=" * 80)
        print(f"📁 Demo database saved at: {db_path}")
        print("🔧 You can inspect the database using:")
        print(f"   sqlite3 {db_path}")
        print("   .schema bets")
        print("   SELECT * FROM bets;")
        print()
        print("🚀 MIGRATION BENEFITS:")
        print("✅ Persistent storage (no more CSV file management)")
        print("✅ ACID transactions (data integrity guaranteed)")
        print("✅ Complex queries (SQL analytics)")
        print("✅ Concurrent access (multiple processes)")
        print("✅ Indexing (fast lookups)")
        print("✅ Schema evolution (easy to add new columns)")
        print("✅ Backup/restore (single file)")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
