#!/usr/bin/env python3
"""
Performance reporter script - compute ROI and leg-by-leg accuracy from bets database.
"""

import argparse
import csv
import json
import logging
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Dict, List, Optional, Any, Tuple, Union


logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Generate performance reports from bets database")
    
    # Database path
    parser.add_argument("--db", default="data/parlays.sqlite", 
                       help="Path to SQLite database (default: data/parlays.sqlite)")
    
    # Time filters
    parser.add_argument("--since", help="Filter bets created_at >= since (UTC ISO 8601)")
    parser.add_argument("--until", help="Filter bets created_at < until (UTC ISO 8601)")
    
    # Grouping and output options
    parser.add_argument("--group-by", choices=["bet_type", "day", "bookmaker", "game_id", "sport"], 
                       default="bet_type", help="Group results by (default: bet_type)")
    parser.add_argument("--sport", choices=["nba", "nfl", "all"], default="all",
                       help="Filter by sport (default: all)")
    parser.add_argument("--export-csv", help="Export results to CSV file")
    parser.add_argument("--export-json", help="Export results to JSON file")
    parser.add_argument("--include-open", action="store_true", 
                       help="Include open bets in counts but exclude from ROI/hit-rate")
    parser.add_argument("--detailed", action="store_true", 
                       help="Print detailed per-group breakdown")
    parser.add_argument("--top-n", type=int, default=10, 
                       help="Number of top/bottom legs to show (default: 10)")
    
    args = parser.parse_args()
    return args


def load_rows(db_path: str, since: Optional[str] = None, until: Optional[str] = None, sport: str = "all") -> List[sqlite3.Row]:
    """Load bet rows from database with optional time and sport filters."""
    try:
        # Try read-only connection first
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    except sqlite3.OperationalError:
        # Fall back to regular connection
        conn = sqlite3.connect(db_path)
    
    conn.row_factory = sqlite3.Row
    
    # Check if CLV and sport columns exist
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(bets)")
    columns = {row[1] for row in cursor.fetchall()}
    has_clv = 'odds_at_alert' in columns and 'closing_line_odds' in columns and 'clv_percentage' in columns
    has_sport = 'sport' in columns
    
    # Build query
    query = """
        SELECT bet_id, parlay_id, game_id, leg_description, odds, stake, 
               is_win, created_at, actual_outcome
    """
    
    if has_clv:
        query += ", odds_at_alert, closing_line_odds, clv_percentage"
    
    if has_sport:
        query += ", sport"
    
    query += " FROM bets WHERE 1=1"
    params = []
    
    if since:
        query += " AND created_at >= ?"
        params.append(since)
    
    if until:
        query += " AND created_at < ?"
        params.append(until)
    
    # Add sport filter if specified and sport column exists
    if sport != "all" and has_sport:
        query += " AND sport = ?"
        params.append(sport)
    
    query += " ORDER BY created_at DESC"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    conn.close()
    
    logger.info(f"Loaded {len(rows)} bets from database")
    return rows


def infer_bet_type(leg_description: str) -> str:
    """Infer bet type from leg description."""
    desc_lower = leg_description.lower()
    
    # Check for bet type keywords (order matters - more specific first)
    if any(keyword in desc_lower for keyword in ["points", "assists", "rebounds", "pra", "stat"]):
        return "player_prop"
    elif any(keyword in desc_lower for keyword in ["moneyline", "h2h", "ml"]):
        return "h2h"
    elif any(keyword in desc_lower for keyword in ["spread", "line", "+", "-", "pts", "ats"]):
        return "spreads"
    elif any(keyword in desc_lower for keyword in ["total", "over", "under", "o/", "u/"]):
        return "totals"
    else:
        return "unknown"


def infer_bookmaker(leg_description: str) -> str:
    """Infer bookmaker from leg description if present."""
    import re
    
    # Look for pattern like "[Book: FanDuel]" or "Book: DraftKings"
    match = re.search(r'\[?Book:\s*([^\]]+)\]?', leg_description, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    return ""


def compute_leg_profit(odds: float, stake: float, is_win: Optional[int], 
                      actual_outcome: Optional[str]) -> Optional[float]:
    """
    Compute profit for a single leg.
    
    Returns:
        Profit amount (positive for win, negative for loss, 0 for push, None for open)
    """
    if is_win is None:
        return None  # Open bet
    
    # Check for push
    if actual_outcome and "push" in actual_outcome.lower():
        return 0.0
    
    if is_win == 1:
        # Win: profit = stake * (odds - 1)
        return stake * (odds - 1)
    elif is_win == 0:
        # Loss: profit = -stake
        return -stake
    else:
        return None


def rollup_metrics(rows: List[sqlite3.Row], group_by: str, include_open: bool) -> Dict[str, Any]:
    """Roll up metrics by the specified grouping."""
    groups = defaultdict(lambda: {
        'count_total': 0,
        'count_decided': 0,
        'count_open': 0,
        'wins': 0,
        'losses': 0,
        'pushes': 0,
        'stake_sum': 0.0,
        'profit_sum': 0.0,
        'legs': []  # Store individual legs for leaders/laggards
    })
    
    for row in rows:
        # Determine group key
        if group_by == "bet_type":
            group_key = infer_bet_type(row['leg_description'])
        elif group_by == "day":
            # Extract date from created_at (YYYY-MM-DD)
            group_key = row['created_at'][:10]
        elif group_by == "bookmaker":
            group_key = infer_bookmaker(row['leg_description']) or "unknown"
        elif group_by == "game_id":
            group_key = row['game_id']
        elif group_by == "sport":
            # Use sport column if available, otherwise default to 'nba'
            if hasattr(row, 'keys') and 'sport' in row.keys():
                group_key = row['sport'] or 'nba'
            else:
                group_key = 'nba'  # Default assumption for legacy data
        else:
            group_key = "unknown"
        
        # Handle stake and odds first
        stake = row['stake'] or 0.0
        odds = row['odds'] or 0.0
        
        if stake <= 0:
            logger.warning(f"Zero or missing stake for bet_id {row['bet_id']}")
            continue
        
        if odds == 0:
            logger.warning(f"Zero or missing odds for bet_id {row['bet_id']}")
            continue
        
        group = groups[group_key]
        group['count_total'] += 1
        group['stake_sum'] += stake
        
        # Compute profit
        profit = compute_leg_profit(odds, stake, row['is_win'], row['actual_outcome'])
        
        # Store leg info for leaders/laggards
        leg_info = {
            'bet_id': row['bet_id'],
            'parlay_id': row['parlay_id'],
            'game_id': row['game_id'],
            'leg_description': row['leg_description'],
            'stake': stake,
            'odds': odds,
            'profit': profit,
            'created_at': row['created_at'],
            'is_win': row['is_win']
        }
        group['legs'].append(leg_info)
        
        if row['is_win'] is None:
            # Open bet
            group['count_open'] += 1
            if include_open:
                continue  # Skip from metrics but count in totals
        else:
            # Decided bet
            group['count_decided'] += 1
            group['profit_sum'] += profit or 0.0
            
            if profit == 0.0 and row['actual_outcome'] and "push" in row['actual_outcome'].lower():
                group['pushes'] += 1
            elif row['is_win'] == 1:
                group['wins'] += 1
            elif row['is_win'] == 0:
                group['losses'] += 1
    
    # Calculate ROI and hit rate for each group
    for group in groups.values():
        if group['stake_sum'] > 0:
            group['roi_pct'] = (group['profit_sum'] / group['stake_sum']) * 100
        else:
            group['roi_pct'] = 0.0
        
        total_decided = group['wins'] + group['losses']  # Exclude pushes
        if total_decided > 0:
            group['hit_rate_pct'] = (group['wins'] / total_decided) * 100
        else:
            group['hit_rate_pct'] = 0.0
    
    return dict(groups)


def summarize_clv(rows: List[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    """Summarize CLV statistics if available."""
    clv_values = []
    
    for row in rows:
        # Check if CLV columns exist and have data
        if hasattr(row, 'keys') and 'clv_percentage' in row.keys() and row['clv_percentage'] is not None:
            # Only include CLV for valid bets (non-zero stake and odds)
            stake = row['stake'] or 0.0
            odds = row['odds'] or 0.0
            if stake > 0 and odds > 0:
                clv_values.append(row['clv_percentage'])
    
    if not clv_values:
        return None
    
    return {
        'count_clv': len(clv_values),
        'clv_min': min(clv_values),
        'clv_median': median(clv_values),
        'clv_mean': mean(clv_values),
        'clv_max': max(clv_values)
    }


def get_leaders_laggards(groups: Dict[str, Any], top_n: int) -> Tuple[List[Dict], List[Dict]]:
    """Get top and bottom performing legs."""
    all_legs = []
    for group in groups.values():
        all_legs.extend(group['legs'])
    
    # Filter to decided bets only
    decided_legs = [leg for leg in all_legs if leg['profit'] is not None]
    
    # Sort by profit
    decided_legs.sort(key=lambda x: x['profit'], reverse=True)
    
    leaders = decided_legs[:top_n]
    laggards = decided_legs[-top_n:][::-1]  # Reverse to show worst first
    
    return leaders, laggards


def emit_console_report(overall: Dict[str, Any], groups: Dict[str, Any], 
                       leaders: List[Dict], laggards: List[Dict], 
                       clv_summary: Optional[Dict[str, Any]], args: argparse.Namespace) -> None:
    """Emit human-readable console report."""
    print("=" * 80)
    print("PERFORMANCE REPORT")
    print("=" * 80)
    print(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    print(f"Database: {args.db}")
    
    filters = []
    if args.since:
        filters.append(f"since: {args.since}")
    if args.until:
        filters.append(f"until: {args.until}")
    if args.sport != "all":
        filters.append(f"sport: {args.sport}")
    
    if filters:
        print(f"Filters: {', '.join(filters)}")
    
    print(f"Grouped by: {args.group_by}")
    print()
    
    # Overall metrics
    print("OVERALL METRICS")
    print("-" * 40)
    print(f"Total bets: {overall['count_total']}")
    print(f"Decided bets: {overall['count_decided']}")
    if args.include_open:
        print(f"Open bets: {overall['count_open']}")
    
    if overall['count_decided'] > 0:
        print(f"Wins: {overall['wins']}")
        print(f"Losses: {overall['losses']}")
        if overall['pushes'] > 0:
            print(f"Pushes: {overall['pushes']}")
        
        print(f"Total stake: ${overall['stake_sum']:.2f}")
        print(f"Total profit: ${overall['profit_sum']:.2f}")
        print(f"ROI: {overall['roi_pct']:.2f}%")
        print(f"Hit rate: {overall['hit_rate_pct']:.2f}%")
    else:
        print("No decided bets found")
    
    print()
    
    # CLV summary if available
    if clv_summary:
        print("CLV SUMMARY")
        print("-" * 40)
        print(f"Bets with CLV: {clv_summary['count_clv']}")
        print(f"CLV range: {clv_summary['clv_min']:.4f}% to {clv_summary['clv_max']:.4f}%")
        print(f"CLV median: {clv_summary['clv_median']:.4f}%")
        print(f"CLV mean: {clv_summary['clv_mean']:.4f}%")
        print()
    
    # Detailed breakdown
    if args.detailed and groups:
        print("PER-GROUP BREAKDOWN")
        print("-" * 40)
        
        # Sort groups by profit_sum descending
        sorted_groups = sorted(groups.items(), key=lambda x: x[1]['profit_sum'], reverse=True)
        
        for group_key, group in sorted_groups:
            print(f"\n{args.group_by.title()}: {group_key}")
            print(f"  Total: {group['count_total']}, Decided: {group['count_decided']}")
            if args.include_open and group['count_open'] > 0:
                print(f"  Open: {group['count_open']}")
            
            if group['count_decided'] > 0:
                print(f"  Wins: {group['wins']}, Losses: {group['losses']}")
                if group['pushes'] > 0:
                    print(f"  Pushes: {group['pushes']}")
                print(f"  Stake: ${group['stake_sum']:.2f}, Profit: ${group['profit_sum']:.2f}")
                print(f"  ROI: {group['roi_pct']:.2f}%, Hit rate: {group['hit_rate_pct']:.2f}%")
            else:
                print("  No decided bets")
    
    # Leaders and laggards
    if leaders:
        print(f"\nTOP {len(leaders)} PROFITABLE LEGS")
        print("-" * 40)
        for i, leg in enumerate(leaders, 1):
            print(f"{i:2d}. {leg['parlay_id']} | {leg['game_id']} | {leg['leg_description']}")
            print(f"     Stake: ${leg['stake']:.2f}, Odds: {leg['odds']:.2f}, Profit: ${leg['profit']:.2f}")
            print(f"     Created: {leg['created_at']}")
    
    if laggards:
        print(f"\nBOTTOM {len(laggards)} LEGS")
        print("-" * 40)
        for i, leg in enumerate(laggards, 1):
            print(f"{i:2d}. {leg['parlay_id']} | {leg['game_id']} | {leg['leg_description']}")
            print(f"     Stake: ${leg['stake']:.2f}, Odds: {leg['odds']:.2f}, Profit: ${leg['profit']:.2f}")
            print(f"     Created: {leg['created_at']}")
    
    print("\n" + "=" * 80)


def write_csv(groups: Dict[str, Any], output_path: str) -> None:
    """Write groups data to CSV file."""
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow([
            'group_key', 'count_total', 'count_decided', 'count_open',
            'wins', 'losses', 'pushes', 'stake_sum', 'profit_sum',
            'roi_pct', 'hit_rate_pct'
        ])
        
        # Write data
        for group_key, group in groups.items():
            writer.writerow([
                group_key,
                group['count_total'],
                group['count_decided'],
                group['count_open'],
                group['wins'],
                group['losses'],
                group['pushes'],
                f"{group['stake_sum']:.2f}",
                f"{group['profit_sum']:.2f}",
                f"{group['roi_pct']:.2f}",
                f"{group['hit_rate_pct']:.2f}"
            ])
    
    logger.info(f"Exported CSV to {output_path}")


def write_json(overall: Dict[str, Any], groups: Dict[str, Any], 
               leaders: List[Dict], laggards: List[Dict], 
               clv_summary: Optional[Dict[str, Any]], output_path: str) -> None:
    """Write complete data to JSON file."""
    data = {
        'overall': overall,
        'groups': {k: {**v, 'legs': []} for k, v in groups.items()},  # Exclude legs from JSON
        'leaders': leaders,
        'laggards': laggards
    }
    
    if clv_summary:
        data['clv_summary'] = clv_summary
    
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    
    logger.info(f"Exported JSON to {output_path}")


def main() -> int:
    """Main function."""
    args = parse_args()
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    try:
        # Load data
        rows = load_rows(args.db, args.since, args.until, args.sport)
        
        if not rows:
            print("No bets found matching the specified criteria")
            return 0
        
        # Roll up metrics
        groups = rollup_metrics(rows, args.group_by, args.include_open)
        
        # Calculate overall metrics
        overall = {
            'count_total': sum(g['count_total'] for g in groups.values()),
            'count_decided': sum(g['count_decided'] for g in groups.values()),
            'count_open': sum(g['count_open'] for g in groups.values()),
            'wins': sum(g['wins'] for g in groups.values()),
            'losses': sum(g['losses'] for g in groups.values()),
            'pushes': sum(g['pushes'] for g in groups.values()),
            'stake_sum': sum(g['stake_sum'] for g in groups.values()),
            'profit_sum': sum(g['profit_sum'] for g in groups.values())
        }
        
        if overall['stake_sum'] > 0:
            overall['roi_pct'] = (overall['profit_sum'] / overall['stake_sum']) * 100
        else:
            overall['roi_pct'] = 0.0
        
        total_decided = overall['wins'] + overall['losses']
        if total_decided > 0:
            overall['hit_rate_pct'] = (overall['wins'] / total_decided) * 100
        else:
            overall['hit_rate_pct'] = 0.0
        
        # Get leaders and laggards
        leaders, laggards = get_leaders_laggards(groups, args.top_n)
        
        # Summarize CLV if available
        clv_summary = summarize_clv(rows)
        
        # Emit console report
        emit_console_report(overall, groups, leaders, laggards, clv_summary, args)
        
        # Export if requested
        if args.export_csv:
            write_csv(groups, args.export_csv)
        
        if args.export_json:
            write_json(overall, groups, leaders, laggards, clv_summary, args.export_json)
        
        return 0
        
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
