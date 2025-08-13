#!/usr/bin/env python3
"""
Update closing lines script - fetches closing odds and computes CLV.
"""

import argparse
import logging
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from tools.bets_logger import BetsLogger
from tools.odds_fetcher_tool import OddsFetcherTool, GameOdds


logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Update closing lines and compute CLV")
    
    # Database path
    parser.add_argument("--db", default="data/parlays.sqlite", 
                       help="Path to SQLite database (default: data/parlays.sqlite)")
    
    # Required arguments
    parser.add_argument("--sport-key", required=True, help="Sport key (e.g., basketball_nba)")
    
    # Optional arguments
    parser.add_argument("--regions", default="us", help="Regions to fetch odds for")
    parser.add_argument("--markets", default="h2h,spreads,totals,player_points", 
                       help="Comma-separated markets to fetch")
    
    # Filters
    parser.add_argument("--game-id", action="append", help="Filter by game ID (can specify multiple)")
    parser.add_argument("--since", help="Only consider bets created_at >= since (ISO datetime)")
    parser.add_argument("--window-minutes", type=int, default=90, 
                       help="Window around current time for game commencement (default: 90)")
    
    # Execution mode
    parser.add_argument("--dry-run", action="store_true", 
                       help="Compute and print what would be updated without writing")
    
    args = parser.parse_args()
    return args


def load_targets(bets_logger: BetsLogger, game_ids: Optional[List[str]] = None, 
                since: Optional[str] = None) -> List:
    """Load target bets that need closing lines."""
    if game_ids:
        # Use explicit game IDs
        targets = bets_logger.fetch_bets_missing_clv(game_ids=game_ids, since_iso=since)
    else:
        # Use all bets missing CLV
        targets = bets_logger.fetch_bets_missing_clv(since_iso=since)
    
    logger.info(f"Found {len(targets)} bets missing closing lines")
    return targets


def fetch_latest_odds(odds_fetcher: OddsFetcherTool, sport_key: str, regions: str, 
                     markets: str) -> List[GameOdds]:
    """Fetch latest odds from the API."""
    markets_list = [m.strip() for m in markets.split(',')]
    
    try:
        games = odds_fetcher.get_game_odds(sport_key, regions, markets_list)
        logger.info(f"Fetched odds for {len(games)} games")
        return games
    except Exception as e:
        logger.error(f"Failed to fetch odds: {e}")
        raise


def infer_market_from_leg_description(leg_description: str) -> str:
    """Infer market type from leg description."""
    desc_lower = leg_description.lower()
    
    # Market inference based on keywords
    if any(keyword in desc_lower for keyword in ["moneyline", "h2h", "ml"]):
        return "h2h"
    elif any(keyword in desc_lower for keyword in ["spread", "-", "+", "pts", "line"]):
        return "spreads"
    elif any(keyword in desc_lower for keyword in ["total", "o/", "u/", "over", "under"]):
        return "totals"
    elif any(keyword in desc_lower for keyword in ["points", "assists", "rebounds"]):
        return "player_points"
    
    # Fallback to any market
    return "any"


def find_selection_for_leg(leg_description: str, games: List[GameOdds], 
                          target_game_id: str) -> Optional[Tuple[float, str]]:
    """
    Find matching selection for a leg description.
    
    Returns:
        Tuple of (price_decimal, market_type) or None if not found
    """
    # Find the target game
    target_game = None
    for game in games:
        if game.game_id == target_game_id:
            target_game = game
            break
    
    if not target_game:
        return None
    
    # Infer preferred market
    preferred_market = infer_market_from_leg_description(leg_description)
    
    # Market priority order
    market_priority = ["player_points", "spreads", "totals", "h2h"]
    
    # If we have a preferred market, put it first
    if preferred_market in market_priority:
        market_priority.insert(0, market_priority.pop(market_priority.index(preferred_market)))
    
    # Search through books and markets
    for book in target_game.books:
        for market in market_priority:
            # Find books with this market
            for book_odds in target_game.books:
                if book_odds.market == market:
                    # Look for matching selection
                    for selection in book_odds.selections:
                        if _selection_matches_leg(selection.name, leg_description):
                            return selection.price_decimal, book_odds.market
    
    # Fallback: search all markets
    for book in target_game.books:
        for selection in book.selections:
            if _selection_matches_leg(selection.name, leg_description):
                return selection.price_decimal, book.market
    
    return None


def _selection_matches_leg(selection_name: str, leg_description: str) -> bool:
    """Check if selection name matches leg description (case-insensitive substring)."""
    selection_lower = selection_name.lower()
    leg_lower = leg_description.lower()
    
    # Extract key parts from leg description
    leg_parts = leg_lower.split()
    
    # Check if any part of the leg description appears in selection name
    for part in leg_parts:
        if len(part) > 2 and part in selection_lower:  # Avoid matching very short words
            return True
    
    # Also check if "LAL" appears in "Los Angeles Lakers"
    if "lal" in leg_lower and "los angeles lakers" in selection_lower:
        return True
    
    # Check for common team abbreviations
    team_mappings = {
        "lal": "los angeles lakers",
        "gsw": "golden state warriors",
        "bos": "boston celtics",
        "nyk": "new york knicks",
        "phi": "philadelphia 76ers",
        "tor": "toronto raptors"
    }
    
    for abbrev, full_name in team_mappings.items():
        if abbrev in leg_lower and full_name in selection_lower:
            return True
    
    return False


def update_closing_lines(bets_logger: BetsLogger, targets: List, games: List[GameOdds], 
                        dry_run: bool = False) -> Dict[str, int]:
    """Update closing lines for target bets."""
    updated_count = 0
    unmatched_count = 0
    already_had_closing_line = 0
    clv_values = []
    
    for bet in targets:
        bet_id = bet['bet_id']
        game_id = bet['game_id']
        leg_description = bet['leg_description']
        
        # Check if already has closing line
        if bet['closing_line_odds'] is not None:
            already_had_closing_line += 1
            continue
        
        # Find matching selection
        result = find_selection_for_leg(leg_description, games, game_id)
        
        if result:
            closing_odds, market_type = result
            
            if closing_odds and closing_odds > 0:
                if not dry_run:
                    try:
                        bets_logger.set_closing_line(bet_id, closing_odds)
                        updated_count += 1
                        
                        # Get the computed CLV
                        cursor = bets_logger.connection.cursor()
                        cursor.execute("SELECT clv_percentage FROM bets WHERE bet_id = ?", (bet_id,))
                        clv_row = cursor.fetchone()
                        if clv_row and clv_row[0] is not None:
                            clv_values.append(clv_row[0])
                        
                        logger.debug(f"Updated bet {bet_id}: {leg_description} -> {closing_odds} ({market_type})")
                    except Exception as e:
                        logger.error(f"Failed to update bet {bet_id}: {e}")
                        unmatched_count += 1
                else:
                    # Dry run - just compute CLV
                    try:
                        clv = bets_logger.compute_clv(bet['odds_at_alert'], closing_odds)
                        clv_values.append(clv)
                        updated_count += 1
                        logger.debug(f"Would update bet {bet_id}: {leg_description} -> {closing_odds} (CLV: {clv}%)")
                    except Exception as e:
                        logger.error(f"Failed to compute CLV for bet {bet_id}: {e}")
                        unmatched_count += 1
            else:
                unmatched_count += 1
                logger.debug(f"No valid closing odds for bet {bet_id}: {leg_description}")
        else:
            unmatched_count += 1
            logger.debug(f"No matching selection for bet {bet_id}: {leg_description}")
    
    # Calculate CLV statistics
    clv_stats = {}
    if clv_values:
        clv_stats = {
            'min': min(clv_values),
            'median': sorted(clv_values)[len(clv_values) // 2],
            'mean': sum(clv_values) / len(clv_values),
            'max': max(clv_values)
        }
    
    return {
        'updated_count': updated_count,
        'unmatched_count': unmatched_count,
        'already_had_closing_line': already_had_closing_line,
        'clv_stats': clv_stats
    }


def main() -> int:
    """Main function."""
    args = parse_args()
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    try:
        # Initialize components
        with BetsLogger(args.db) as bets_logger:
            odds_fetcher = OddsFetcherTool()
            
            # Load target bets
            targets = load_targets(bets_logger, args.game_id, args.since)
            
            if not targets:
                if args.game_id or args.since:
                    logger.warning("No target bets found with specified filters")
                    return 3
                else:
                    logger.info("No bets missing closing lines")
                    return 0
            
            # Fetch latest odds
            try:
                games = fetch_latest_odds(odds_fetcher, args.sport_key, args.regions, args.markets)
            except Exception as e:
                logger.error(f"Failed to fetch odds: {e}")
                return 2
            
            # Update closing lines
            stats = update_closing_lines(bets_logger, targets, games, args.dry_run)
            
            # Print summary
            print(f"Closing Lines Update Summary:")
            print(f"  Total candidates: {len(targets)}")
            print(f"  Updated: {stats['updated_count']}")
            print(f"  Unmatched: {stats['unmatched_count']}")
            print(f"  Already had closing line: {stats['already_had_closing_line']}")
            
            if stats['clv_stats']:
                clv = stats['clv_stats']
                print(f"  CLV Distribution:")
                print(f"    Min: {clv['min']:.4f}%")
                print(f"    Median: {clv['median']:.4f}%")
                print(f"    Mean: {clv['mean']:.4f}%")
                print(f"    Max: {clv['max']:.4f}%")
            
            if args.dry_run:
                print(f"  (DRY RUN - No changes made)")
            
            logger.info(f"Update completed: {stats['updated_count']} bets updated")
            return 0
            
    except Exception as e:
        logger.error(f"Update failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
