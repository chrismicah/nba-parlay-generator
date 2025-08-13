#!/usr/bin/env python3
"""
Update bet results script - settles open bets with actual outcomes.
"""

import argparse
import csv
import importlib
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from tools.bets_logger import BetsLogger

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Update bet results from various sources")
    
    # Database path
    parser.add_argument("--db", default="data/parlays.sqlite", 
                       help="Path to SQLite database (default: data/parlays.sqlite)")
    
    # Results source (exactly one required)
    parser.add_argument("--results-json", help="Path to JSON file with results")
    parser.add_argument("--results-csv", help="Path to CSV file with results")
    parser.add_argument("--provider-module", help="Dotted path to provider module with fetch_results function")
    
    # Optional filters
    parser.add_argument("--game-id", action="append", help="Filter by game ID (can specify multiple)")
    parser.add_argument("--since", help="Only update bets created_at >= since (ISO datetime)")
    
    args = parser.parse_args()
    
    # Validate that exactly one results source is provided
    sources = [args.results_json, args.results_csv, args.provider_module]
    if sum(1 for s in sources if s) != 1:
        parser.error("Must provide exactly one of --results-json, --results-csv, or --provider-module")
    
    return args


def load_results_from_json(filepath: str) -> Dict[str, Any]:
    """Load results from JSON file."""
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    logger.info(f"Loaded results from JSON: {len(data)} games")
    return data


def load_results_from_csv(filepath: str) -> Dict[str, Any]:
    """Load results from CSV file and aggregate by game_id."""
    results = {}
    
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            game_id = row.get('game_id')
            if not game_id:
                continue
            
            if game_id not in results:
                results[game_id] = {}
            
            # Handle different CSV formats
            if 'leg_description' in row and 'actual_outcome' in row:
                leg_desc = row['leg_description']
                actual_outcome = row['actual_outcome']
                is_win = _parse_win_value(row.get('is_win', '0'))
                
                results[game_id][leg_desc] = {
                    'actual_outcome': actual_outcome,
                    'is_win': is_win
                }
            elif 'parlay_id' in row and 'leg_description' in row:
                # Alternative format with parlay_id
                parlay_id = row['parlay_id']
                leg_desc = row['leg_description']
                actual_outcome = row.get('actual_outcome', '')
                is_win = _parse_win_value(row.get('is_win', '0'))
                
                key = f"{parlay_id}:{leg_desc}"
                results[game_id][key] = {
                    'actual_outcome': actual_outcome,
                    'is_win': is_win
                }
    
    logger.info(f"Loaded results from CSV: {len(results)} games")
    return results


def load_results_from_provider(provider_path: str, game_ids: List[str]) -> Dict[str, Any]:
    """Load results from provider module."""
    try:
        module = importlib.import_module(provider_path)
        fetch_results = getattr(module, 'fetch_results')
        
        results = fetch_results(game_ids)
        logger.info(f"Loaded results from provider {provider_path}: {len(results)} games")
        return results
        
    except (ImportError, AttributeError) as e:
        logger.error(f"Failed to import provider module {provider_path}: {e}")
        raise


def _parse_win_value(value: str) -> bool:
    """Parse win value from various string formats."""
    if isinstance(value, bool):
        return value
    
    value_str = str(value).lower().strip()
    
    if value_str in ('1', 'true', 'yes', 'win', 'w'):
        return True
    elif value_str in ('0', 'false', 'no', 'loss', 'l'):
        return False
    else:
        logger.warning(f"Unknown win value: {value}, defaulting to False")
        return False


def filter_open_bets(bets_logger: BetsLogger, game_ids: Optional[List[str]] = None, 
                    since: Optional[str] = None) -> List:
    """Filter open bets based on criteria."""
    open_bets = bets_logger.fetch_open_bets()
    
    if game_ids:
        open_bets = [bet for bet in open_bets if bet['game_id'] in game_ids]
    
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
            open_bets = [
                bet for bet in open_bets 
                if datetime.fromisoformat(bet['created_at'].replace('Z', '+00:00')) >= since_dt
            ]
        except ValueError as e:
            logger.error(f"Invalid since date format: {e}")
            return []
    
    return open_bets


def update_bets_with_results(bets_logger: BetsLogger, open_bets: List, 
                           results: Dict[str, Any]) -> Dict[str, int]:
    """Update bets with results and return summary statistics."""
    updated_count = 0
    skipped_no_match = 0
    
    for bet in open_bets:
        game_id = bet['game_id']
        parlay_id = bet['parlay_id']
        leg_description = bet['leg_description']
        
        # Try to find matching result
        result = None
        
        if game_id in results:
            game_results = results[game_id]
            
            # Try exact match first
            if leg_description in game_results:
                result = game_results[leg_description]
            else:
                # Try parlay_id:leg_description format
                key = f"{parlay_id}:{leg_description}"
                if key in game_results:
                    result = game_results[key]
        
        if result:
            try:
                bets_logger.update_bet_outcome(
                    bet['bet_id'],
                    result['actual_outcome'],
                    result['is_win']
                )
                updated_count += 1
            except Exception as e:
                logger.error(f"Failed to update bet {bet['bet_id']}: {e}")
                skipped_no_match += 1
        else:
            skipped_no_match += 1
    
    return {
        'updated_count': updated_count,
        'skipped_no_match': skipped_no_match
    }


def main() -> int:
    """Main function."""
    args = parse_args()
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    try:
        # Initialize bets logger
        with BetsLogger(args.db) as bets_logger:
            # Get open bets
            open_bets = filter_open_bets(bets_logger, args.game_id, args.since)
            total_open_before = len(open_bets)
            
            logger.info(f"Found {total_open_before} open bets to process")
            
            if not open_bets:
                logger.info("No open bets to update")
                return 0
            
            # Load results based on source
            if args.results_json:
                results = load_results_from_json(args.results_json)
            elif args.results_csv:
                results = load_results_from_csv(args.results_csv)
            elif args.provider_module:
                game_ids = list(set(bet['game_id'] for bet in open_bets))
                results = load_results_from_provider(args.provider_module, game_ids)
            else:
                logger.error("No results source specified")
                return 1
            
            # Update bets
            stats = update_bets_with_results(bets_logger, open_bets, results)
            
            # Get final count of open bets
            final_open_bets = bets_logger.fetch_open_bets()
            total_open_after = len(final_open_bets)
            
            # Print summary
            print(f"Update Summary:")
            print(f"  Updated: {stats['updated_count']}")
            print(f"  Skipped (no match): {stats['skipped_no_match']}")
            print(f"  Total open before: {total_open_before}")
            print(f"  Total open after: {total_open_after}")
            
            logger.info(f"Update completed: {stats['updated_count']} bets updated")
            return 0
            
    except Exception as e:
        logger.error(f"Update failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
