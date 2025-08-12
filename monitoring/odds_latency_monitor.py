#!/usr/bin/env python3
"""
Odds Latency Monitor

Monitors odds movement for a specific game by periodically fetching odds
and detecting changes in prices and lines.
"""

import argparse
import csv
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from tools.odds_fetcher_tool import OddsFetcherTool, OddsFetcherError, GameOdds


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Monitor odds movement for a specific game")
    
    # Required arguments
    parser.add_argument("--sport-key", required=True, help="Sport key (e.g., basketball_nba)")
    
    # Optional arguments
    parser.add_argument("--regions", default="us", help="Regions to fetch odds for")
    parser.add_argument("--markets", default="h2h,spreads,totals", 
                       help="Comma-separated markets to monitor")
    
    # Game identification (one of these must be provided)
    parser.add_argument("--game-id", help="Specific game ID to monitor")
    parser.add_argument("--home", help="Home team name filter (case-insensitive)")
    parser.add_argument("--away", help="Away team name filter (case-insensitive)")
    
    # Loop controls
    parser.add_argument("--interval", type=int, default=120, 
                       help="Polling interval in seconds (default: 120)")
    parser.add_argument("--iterations", type=int, 
                       help="Number of iterations to run (default: run until SIGINT)")
    parser.add_argument("--once", action="store_true", 
                       help="Do a single fetch then exit")
    
    # Output options
    parser.add_argument("--out", default=None, 
                       help="Output CSV file path")
    parser.add_argument("--print-diffs", action="store_true", 
                       help="Print detected changes to stdout")
    
    args = parser.parse_args()
    
    # Validate that at least one game identification method is provided
    if not args.game_id and not args.home and not args.away:
        parser.error("Must provide either --game-id or at least one of --home/--away")
    
    # Set default output file if not provided
    if args.out is None:
        args.out = f"data/odds_latency_{args.sport_key}.csv"
    
    return args


def resolve_target_game(games: List[GameOdds], game_id: Optional[str] = None, 
                       home: Optional[str] = None, away: Optional[str] = None) -> Optional[GameOdds]:
    """
    Resolve target game based on provided criteria.
    
    Args:
        games: List of available games
        game_id: Specific game ID to find
        home: Home team name filter
        away: Away team name filter
        
    Returns:
        Target game or None if not found
    """
    if game_id:
        # Find by specific game ID
        for game in games:
            if game.game_id == game_id:
                return game
        return None
    
    # Find by team name filters
    matching_games = []
    
    for game in games:
        # Get team names from h2h market, fallback to any market
        team_names = []
        for book in game.books:
            if book.market == "h2h":
                team_names = [s.name for s in book.selections]
                break
        
        if not team_names:
            # Fallback to any market
            for book in game.books:
                team_names = [s.name for s in book.selections]
                if team_names:
                    break
        
        # Check if game matches filters
        matches = True
        if home:
            home_match = any(home.lower() in name.lower() for name in team_names)
            if not home_match:
                matches = False
        
        if away:
            away_match = any(away.lower() in name.lower() for name in team_names)
            if not away_match:
                matches = False
        
        if matches:
            matching_games.append(game)
    
    if not matching_games:
        return None
    
    # Return the earliest future game
    future_games = []
    now = datetime.now(timezone.utc)
    
    for game in matching_games:
        try:
            game_time = datetime.fromisoformat(game.commence_time.replace('Z', '+00:00'))
            if game_time > now:
                future_games.append((game_time, game))
        except ValueError:
            continue
    
    if not future_games:
        return matching_games[0]  # Return any matching game if no future games
    
    # Return earliest future game
    future_games.sort(key=lambda x: x[0])
    return future_games[0][1]


def write_csv_headers(filepath: Path) -> None:
    """Write CSV headers if file doesn't exist."""
    if not filepath.exists():
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp_iso', 'game_id', 'bookmaker', 'market', 
                'selection_name', 'line', 'price_decimal'
            ])


def log_odds_to_csv(filepath: Path, game: GameOdds, timestamp: str) -> None:
    """Log odds data to CSV file."""
    with open(filepath, 'a', newline='') as f:
        writer = csv.writer(f)
        for book in game.books:
            for selection in book.selections:
                line = selection.line if selection.line is not None else ""
                writer.writerow([
                    timestamp,
                    game.game_id,
                    book.bookmaker,
                    book.market,
                    selection.name,
                    line,
                    selection.price_decimal
                ])


def diff_changes(current_game: GameOdds, last_snapshot: Dict[Tuple, Dict], 
                print_diffs: bool = False) -> Dict[Tuple, Dict]:
    """
    Compare current odds with previous snapshot and detect changes.
    
    Args:
        current_game: Current game odds
        last_snapshot: Previous snapshot of odds
        print_diffs: Whether to print detected changes
        
    Returns:
        Updated snapshot
    """
    current_snapshot = {}
    changes = []
    
    # Build current snapshot
    for book in current_game.books:
        for selection in book.selections:
            key = (book.bookmaker, book.market, selection.name, selection.line)
            current_snapshot[key] = {
                'price_decimal': selection.price_decimal,
                'line': selection.line
            }
    
    # Compare with last snapshot
    for key, current_data in current_snapshot.items():
        if key in last_snapshot:
            last_data = last_snapshot[key]
            
            # Check for price or line changes
            price_changed = current_data['price_decimal'] != last_data['price_decimal']
            line_changed = current_data['line'] != last_data['line']
            
            if price_changed or line_changed:
                bookmaker, market, selection_name, line = key
                
                # Format change message
                line_info = f"line {last_data['line']} -> {current_data['line']}" if line_changed else ""
                price_info = f"price {last_data['price_decimal']} -> {current_data['price_decimal']}" if price_changed else ""
                
                change_parts = [part for part in [line_info, price_info] if part]
                change_msg = f" {' '.join(change_parts)}"
                
                changes.append({
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'game_id': current_game.game_id,
                    'bookmaker': bookmaker,
                    'market': market,
                    'selection': selection_name,
                    'change': change_msg
                })
    
    # Print changes if requested
    if print_diffs and changes:
        for change in changes:
            print(f"{change['timestamp']} game={change['game_id']} book={change['bookmaker']} "
                  f"market={change['market']} sel={change['selection']}{change['change']}")
    
    return current_snapshot


def fetch_and_log_once(odds_fetcher: OddsFetcherTool, args: argparse.Namespace, 
                      last_snapshot: Dict[Tuple, Dict]) -> Dict[Tuple, Dict]:
    """
    Fetch odds once and log to CSV.
    
    Args:
        odds_fetcher: OddsFetcherTool instance
        args: Command line arguments
        last_snapshot: Previous snapshot for diffing
        
    Returns:
        Updated snapshot
    """
    try:
        # Fetch odds
        markets_list = [m.strip() for m in args.markets.split(',')]
        games = odds_fetcher.get_game_odds(args.sport_key, args.regions, markets_list)
        
        if not games:
            print("No games found")
            return last_snapshot
        
        # Resolve target game
        target_game = resolve_target_game(games, args.game_id, args.home, args.away)
        
        if not target_game:
            if args.game_id:
                print(f"Game ID {args.game_id} not found")
            else:
                home_filter = f"home={args.home}" if args.home else ""
                away_filter = f"away={args.away}" if args.away else ""
                filters = " and ".join(filter(None, [home_filter, away_filter]))
                print(f"No games found matching filters: {filters}")
            return last_snapshot
        
        # Log timestamp
        timestamp = datetime.now(timezone.utc).isoformat()
        print(f"{timestamp} - Monitoring game: {target_game.game_id}")
        
        # Get team names for display
        team_names = []
        for book in target_game.books:
            if book.market == "h2h":
                team_names = [s.name for s in book.selections]
                break
        
        if team_names:
            print(f"Teams: {' vs '.join(team_names)}")
        
        # Log to CSV
        filepath = Path(args.out)
        write_csv_headers(filepath)
        log_odds_to_csv(filepath, target_game, timestamp)
        
        # Detect and report changes
        new_snapshot = diff_changes(target_game, last_snapshot, args.print_diffs)
        
        return new_snapshot
        
    except OddsFetcherError as e:
        print(f"OddsFetcherError: {e}")
        return last_snapshot
    except Exception as e:
        print(f"Unexpected error: {e}")
        return last_snapshot


def main() -> None:
    """Main function."""
    args = parse_args()
    
    # Initialize odds fetcher
    odds_fetcher = OddsFetcherTool()
    
    # Initialize snapshot for diffing
    last_snapshot: Dict[Tuple, Dict] = {}
    
    # Handle graceful shutdown
    def signal_handler(signum, frame):
        print("\nStopping odds latency monitor.")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Single fetch mode
    if args.once:
        fetch_and_log_once(odds_fetcher, args, last_snapshot)
        return
    
    # Continuous monitoring mode
    iteration = 0
    while True:
        # Check iteration limit
        if args.iterations and iteration >= args.iterations:
            print(f"Completed {args.iterations} iterations")
            break
        
        # Fetch and log
        last_snapshot = fetch_and_log_once(odds_fetcher, args, last_snapshot)
        
        # Increment iteration counter
        iteration += 1
        
        # Sleep if not the last iteration
        if not args.iterations or iteration < args.iterations:
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
