#!/usr/bin/env python3
"""
Baseline simulation for parlay ROI analysis.

Simulates random 2-3 leg parlays to establish ROI baselines for comparison.
Supports separate Summer League and regular season baselines.
"""

import argparse
import csv
import json
import logging
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from tools.odds_fetcher_tool import OddsFetcherTool, GameOdds, BookOdds, Selection

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class GameResult:
    """Historical game result data."""
    game_id: str
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    closing_spread_home: Optional[float] = None
    closing_total: Optional[float] = None
    date_utc: Optional[str] = None
    league: Optional[str] = None


@dataclass
class CandidateLeg:
    """A candidate leg for parlay construction."""
    game_id: str
    bookmaker: str
    market: str
    selection_name: str
    line: Optional[float]
    price_decimal: float


@dataclass
class ParlayOutcome:
    """Result of a single parlay simulation."""
    parlay_id: int
    legs: int
    profit: float
    effective_parlay_odds: float
    segment: str
    leg_outcomes: List[str]  # "win", "loss", "push"


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Simulate random parlays for ROI baseline analysis")
    
    parser.add_argument("--sport-key", required=True, type=str,
                       help="Sport key (e.g., basketball_nba, basketball_nba_summer_league)")
    parser.add_argument("--regions", default="us", type=str,
                       help="Betting regions (default: us)")
    parser.add_argument("--markets", default="h2h,spreads,totals", type=str,
                       help="Markets to include (default: h2h,spreads,totals)")
    parser.add_argument("--odds-json", type=Path,
                       help="Path to normalized odds snapshot file")
    parser.add_argument("--results-csv", required=True, type=Path,
                       help="Path to historical results CSV file")
    parser.add_argument("--num-parlays", default=10000, type=int,
                       help="Number of random parlays to simulate (default: 10000)")
    parser.add_argument("--legs-min", default=2, type=int,
                       help="Minimum legs per parlay (default: 2)")
    parser.add_argument("--legs-max", default=3, type=int,
                       help="Maximum legs per parlay (default: 3)")
    parser.add_argument("--stake-per-parlay", default=1.0, type=float,
                       help="Fixed stake for each parlay (default: 1.0)")
    parser.add_argument("--seed", default=42, type=int,
                       help="RNG seed for reproducibility (default: 42)")
    parser.add_argument("--summer-league-flag", action="store_true",
                       help="Force treat all games as Summer League")
    parser.add_argument("--export-csv", type=Path,
                       help="Path to export per-parlay outcomes CSV")
    parser.add_argument("--export-json", type=Path,
                       help="Path to export summary JSON")
    parser.add_argument("--verbose", action="store_true",
                       help="Print extra diagnostics")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    return args


def load_results_csv(path: Path) -> Dict[str, GameResult]:
    """Load historical results from CSV file."""
    results = {}
    
    with open(path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        # Validate required columns
        required_columns = {'game_id', 'home_team', 'away_team', 'home_score', 'away_score'}
        missing_columns = required_columns - set(reader.fieldnames or [])
        if missing_columns:
            logger.error(f"Missing required columns in results CSV: {missing_columns}")
            exit(2)
        
        for row in reader:
            try:
                game_result = GameResult(
                    game_id=row['game_id'],
                    home_team=row['home_team'],
                    away_team=row['away_team'],
                    home_score=int(row['home_score']),
                    away_score=int(row['away_score']),
                    closing_spread_home=float(row['closing_spread_home']) if row.get('closing_spread_home') else None,
                    closing_total=float(row['closing_total']) if row.get('closing_total') else None,
                    date_utc=row.get('date_utc'),
                    league=row.get('league')
                )
                results[game_result.game_id] = game_result
            except (ValueError, KeyError) as e:
                logger.warning(f"Skipping invalid row: {e}")
                continue
    
    logger.info(f"Loaded {len(results)} game results from {path}")
    return results


def load_odds_snapshot(args: argparse.Namespace) -> List[GameOdds]:
    """Load odds snapshot from file or fetch live data."""
    if args.odds_json:
        logger.info(f"Loading odds from {args.odds_json}")
        with open(args.odds_json, 'r') as f:
            data = json.load(f)
        
        # Convert JSON back to GameOdds objects
        games = []
        for game_data in data:
            books = []
            for book_data in game_data['books']:
                selections = [
                    Selection(
                        name=sel['name'],
                        price_decimal=sel['price_decimal'],
                        line=sel.get('line')
                    )
                    for sel in book_data['selections']
                ]
                books.append(BookOdds(
                    bookmaker=book_data['bookmaker'],
                    market=book_data['market'],
                    selections=selections
                ))
            
            games.append(GameOdds(
                sport_key=game_data['sport_key'],
                game_id=game_data['game_id'],
                commence_time=game_data['commence_time'],
                books=books
            ))
        
        return games
    else:
        logger.info("Fetching live odds data")
        markets = args.markets.split(',')
        odds_fetcher = OddsFetcherTool()
        return odds_fetcher.get_game_odds_sync(args.sport_key, args.regions, markets)


def build_candidate_pool(games: List[GameOdds], markets: List[str]) -> List[CandidateLeg]:
    """Build candidate pool of legs from odds data."""
    candidates = []
    seen = set()  # For deduplication
    
    for game in games:
        for book in game.books:
            if book.market not in markets:
                continue
            
            for selection in book.selections:
                # Create unique key for deduplication
                key = (game.game_id, book.market, selection.name, selection.line, book.bookmaker)
                if key in seen:
                    continue
                seen.add(key)
                
                candidates.append(CandidateLeg(
                    game_id=game.game_id,
                    bookmaker=book.bookmaker,
                    market=book.market,
                    selection_name=selection.name,
                    line=selection.line,
                    price_decimal=selection.price_decimal
                ))
    
    logger.info(f"Built candidate pool: {len(candidates)} unique legs from {len(games)} games")
    return candidates


def sample_parlay(rng: random.Random, candidate_pool: List[CandidateLeg], 
                 legs_min: int, legs_max: int) -> List[CandidateLeg]:
    """Sample a random parlay from the candidate pool."""
    num_legs = rng.randint(legs_min, legs_max)
    
    # Sample legs with constraint: max 1 leg per game
    selected_legs = []
    used_games = set()
    
    # Shuffle candidates to avoid bias
    shuffled_candidates = candidate_pool.copy()
    rng.shuffle(shuffled_candidates)
    
    for leg in shuffled_candidates:
        if len(selected_legs) >= num_legs:
            break
        
        # Avoid multiple legs from same game
        if leg.game_id not in used_games:
            selected_legs.append(leg)
            used_games.add(leg.game_id)
    
    return selected_legs


def settle_leg(leg: CandidateLeg, game_result: GameResult) -> str:
    """Settle a single leg based on game result."""
    if leg.market == "h2h":
        # Head-to-head: winner by final score
        if "home" in leg.selection_name.lower() or game_result.home_team in leg.selection_name:
            return "win" if game_result.home_score > game_result.away_score else "loss"
        elif "away" in leg.selection_name.lower() or game_result.away_team in leg.selection_name:
            return "win" if game_result.away_score > game_result.home_score else "loss"
        else:
            # Try to match team names
            if game_result.home_team in leg.selection_name:
                return "win" if game_result.home_score > game_result.away_score else "loss"
            elif game_result.away_team in leg.selection_name:
                return "win" if game_result.away_score > game_result.home_score else "loss"
            else:
                logger.warning(f"Could not determine winner for h2h leg: {leg.selection_name}")
                return "loss"  # Conservative default
    
    elif leg.market == "spreads":
        # Spread: team margin vs line
        if leg.line is None:
            logger.warning(f"No line for spread leg: {leg.selection_name}")
            return "loss"
        
        # Determine which team this selection represents
        is_home_team = ("home" in leg.selection_name.lower() or 
                       game_result.home_team in leg.selection_name)
        
        if is_home_team:
            margin = game_result.home_score - game_result.away_score
            result = margin - leg.line
        else:
            margin = game_result.away_score - game_result.home_score
            result = margin - leg.line
        
        if result > 0:
            return "win"
        elif result == 0:
            return "push"
        else:
            return "loss"
    
    elif leg.market == "totals":
        # Totals: combined score vs line
        if leg.line is None:
            logger.warning(f"No line for totals leg: {leg.selection_name}")
            return "loss"
        
        total_score = game_result.home_score + game_result.away_score
        result = total_score - leg.line
        
        if "over" in leg.selection_name.lower():
            if result > 0:
                return "win"
            elif result == 0:
                return "push"
            else:
                return "loss"
        elif "under" in leg.selection_name.lower():
            if result < 0:
                return "win"
            elif result == 0:
                return "push"
            else:
                return "loss"
        else:
            logger.warning(f"Could not determine over/under for totals leg: {leg.selection_name}")
            return "loss"
    
    else:
        logger.warning(f"Unknown market type: {leg.market}")
        return "loss"


def settle_parlay(legs: List[CandidateLeg], leg_outcomes: List[str]) -> Tuple[float, float, str]:
    """Settle a parlay based on leg outcomes."""
    # If any leg loses, parlay loses
    if "loss" in leg_outcomes:
        return 0.0, -1.0, "loss"
    
    # Calculate effective odds (only winning legs contribute)
    effective_odds = 1.0
    winning_legs = 0
    
    for i, outcome in enumerate(leg_outcomes):
        if outcome == "win":
            effective_odds *= legs[i].price_decimal
            winning_legs += 1
        # Pushes contribute factor 1.0 (no change to odds)
    
    if winning_legs == 0:
        # All legs pushed
        return 1.0, 0.0, "push"
    else:
        return effective_odds, effective_odds - 1.0, "win"


def determine_segment(legs: List[CandidateLeg], game_results: Dict[str, GameResult], 
                     summer_league_flag: bool) -> str:
    """Determine segment (summer/regular) for a parlay."""
    if summer_league_flag:
        return "summer"
    
    # Check if all legs' games have league info
    leagues = set()
    for leg in legs:
        if leg.game_id in game_results:
            league = game_results[leg.game_id].league
            if league:
                leagues.add(league)
    
    if len(leagues) == 1:
        league = list(leagues)[0]
        if league == "summer":
            return "summer"
        elif league == "regular":
            return "regular"
    
    # Default to regular if mixed or unclear
    return "regular"


def run_simulation(args: argparse.Namespace, candidate_pool: List[CandidateLeg], 
                  game_results: Dict[str, GameResult]) -> List[ParlayOutcome]:
    """Run the main simulation."""
    if len(candidate_pool) < args.legs_min:
        logger.error(f"Insufficient candidate legs ({len(candidate_pool)}) for minimum legs ({args.legs_min})")
        exit(3)
    
    rng = random.Random(args.seed)
    outcomes = []
    
    logger.info(f"Starting simulation: {args.num_parlays} parlays, {args.legs_min}-{args.legs_max} legs each")
    
    for parlay_id in range(args.num_parlays):
        # Sample parlay
        legs = sample_parlay(rng, candidate_pool, args.legs_min, args.legs_max)
        
        if len(legs) < args.legs_min:
            logger.warning(f"Could not sample enough legs for parlay {parlay_id}")
            continue
        
        # Settle each leg
        leg_outcomes = []
        for leg in legs:
            if leg.game_id in game_results:
                outcome = settle_leg(leg, game_results[leg.game_id])
                leg_outcomes.append(outcome)
            else:
                logger.warning(f"No result for game {leg.game_id}")
                leg_outcomes.append("loss")
        
        # Settle parlay
        effective_odds, profit_multiplier, status = settle_parlay(legs, leg_outcomes)
        profit = args.stake_per_parlay * profit_multiplier
        
        # Determine segment
        segment = determine_segment(legs, game_results, args.summer_league_flag)
        
        outcomes.append(ParlayOutcome(
            parlay_id=parlay_id,
            legs=len(legs),
            profit=profit,
            effective_parlay_odds=effective_odds,
            segment=segment,
            leg_outcomes=leg_outcomes
        ))
    
    logger.info(f"Simulation complete: {len(outcomes)} parlays processed")
    return outcomes


def summarize(outcomes: List[ParlayOutcome], args: argparse.Namespace) -> Dict[str, Any]:
    """Generate summary statistics."""
    if not outcomes:
        return {}
    
    # Overall stats
    total_stake = len(outcomes) * args.stake_per_parlay
    total_profit = sum(o.profit for o in outcomes)
    roi_percent = (total_profit / total_stake) * 100 if total_stake > 0 else 0
    
    wins = sum(1 for o in outcomes if o.profit > 0)
    hit_rate = (wins / len(outcomes)) * 100 if outcomes else 0
    
    avg_legs = sum(o.legs for o in outcomes) / len(outcomes)
    avg_odds = sum(o.effective_parlay_odds for o in outcomes) / len(outcomes)
    
    profits = [o.profit for o in outcomes]
    profit_stats = {
        "min": min(profits),
        "max": max(profits),
        "mean": sum(profits) / len(profits),
        "median": sorted(profits)[len(profits) // 2]
    }
    
    # Segment stats
    segments = {}
    for segment in ["summer", "regular"]:
        segment_outcomes = [o for o in outcomes if o.segment == segment]
        if segment_outcomes:
            seg_stake = len(segment_outcomes) * args.stake_per_parlay
            seg_profit = sum(o.profit for o in segment_outcomes)
            seg_roi = (seg_profit / seg_stake) * 100 if seg_stake > 0 else 0
            seg_wins = sum(1 for o in segment_outcomes if o.profit > 0)
            seg_hit_rate = (seg_wins / len(segment_outcomes)) * 100 if segment_outcomes else 0
            
            segments[segment] = {
                "count": len(segment_outcomes),
                "total_stake": seg_stake,
                "total_profit": seg_profit,
                "roi_percent": seg_roi,
                "hit_rate": seg_hit_rate
            }
    
    return {
        "parameters": {
            "sport_key": args.sport_key,
            "num_parlays": args.num_parlays,
            "legs_min": args.legs_min,
            "legs_max": args.legs_max,
            "stake_per_parlay": args.stake_per_parlay,
            "seed": args.seed,
            "summer_league_flag": args.summer_league_flag
        },
        "overall": {
            "total_parlays": len(outcomes),
            "total_stake": total_stake,
            "total_profit": total_profit,
            "roi_percent": roi_percent,
            "hit_rate": hit_rate,
            "avg_legs": avg_legs,
            "avg_odds": avg_odds,
            "profit_stats": profit_stats
        },
        "segments": segments,
        "diagnostics": {
            "candidate_pool_size": len(outcomes[0].leg_outcomes) if outcomes else 0
        }
    }


def maybe_write_csv(outcomes: List[ParlayOutcome], path: Optional[Path]):
    """Write per-parlay outcomes to CSV if path provided."""
    if not path:
        return
    
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['parlay_id', 'legs', 'effective_odds', 'profit', 'segment'])
        
        for outcome in outcomes:
            writer.writerow([
                outcome.parlay_id,
                outcome.legs,
                outcome.effective_parlay_odds,
                outcome.profit,
                outcome.segment
            ])
    
    logger.info(f"Exported {len(outcomes)} parlay outcomes to {path}")


def maybe_write_json(summary: Dict[str, Any], path: Optional[Path]):
    """Write summary to JSON if path provided."""
    if not path:
        return
    
    with open(path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"Exported summary to {path}")


def main():
    """Main entry point."""
    args = parse_args()
    
    # Print run header
    print(f"=== Baseline Simulation Run ===")
    print(f"Sport: {args.sport_key}")
    print(f"Parlays: {args.num_parlays}")
    print(f"Legs: {args.legs_min}-{args.legs_max}")
    print(f"Stake: ${args.stake_per_parlay}")
    print(f"Seed: {args.seed}")
    print(f"Database: {args.results_csv}")
    print()
    
    # Load data
    game_results = load_results_csv(args.results_csv)
    games = load_odds_snapshot(args)
    
    # Build candidate pool
    markets = args.markets.split(',')
    candidate_pool = build_candidate_pool(games, markets)
    
    # Run simulation
    outcomes = run_simulation(args, candidate_pool, game_results)
    
    # Generate summary
    summary = summarize(outcomes, args)
    
    # Print results
    print(f"=== Results ===")
    print(f"Overall ROI: {summary['overall']['roi_percent']:.2f}%")
    print(f"Overall Hit Rate: {summary['overall']['hit_rate']:.2f}%")
    print(f"Total Profit: ${summary['overall']['total_profit']:.2f}")
    print(f"Average Legs: {summary['overall']['avg_legs']:.1f}")
    print(f"Average Odds: {summary['overall']['avg_odds']:.2f}")
    print()
    
    # Segment results
    for segment, stats in summary['segments'].items():
        print(f"{segment.title()} League:")
        print(f"  ROI: {stats['roi_percent']:.2f}%")
        print(f"  Hit Rate: {stats['hit_rate']:.2f}%")
        print(f"  Parlays: {stats['count']}")
        print()
    
    # Diagnostics
    print(f"=== Diagnostics ===")
    print(f"Games with results: {len(game_results)}")
    print(f"Games with odds: {len(games)}")
    print(f"Candidate legs: {len(candidate_pool)}")
    print()
    
    if args.verbose:
        print("=== Sample Parlays ===")
        for i in range(min(5, len(outcomes))):
            outcome = outcomes[i]
            print(f"Parlay {outcome.parlay_id}: {outcome.legs} legs, "
                  f"odds {outcome.effective_parlay_odds:.2f}, "
                  f"profit ${outcome.profit:.2f}, "
                  f"segment {outcome.segment}")
        print()
    
    # Export if requested
    maybe_write_csv(outcomes, args.export_csv)
    maybe_write_json(summary, args.export_json)


if __name__ == "__main__":
    main()
