#!/usr/bin/env python3
"""
NFL Baseline Simulation for 10k Random Parlays - JIRA Task Implementation

Simulates 10,000 random NFL parlays to establish ROI baseline comparison.
Specifically designed for NFL markets including three-way outcomes (Win/Tie/Loss).

Key Features:
- NFL-specific market handling (h2h, spreads, totals, three_way)
- Historical NFL game result integration
- 10k random parlay simulation for statistical significance
- ROI baseline calculation for comparison with intelligent strategies
- NFL season and game type segmentation
- Enhanced with knowledge base insights for context

Usage:
python simulations/nfl_baseline_simulation.py \
    --sport-key americanfootball_nfl \
    --results-csv data/nfl_results_2023.csv \
    --num-parlays 10000 \
    --export-json results/nfl_baseline_roi.json
"""

import argparse
import csv
import json
import logging
import random
import sys
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.odds_fetcher_tool import OddsFetcherTool, GameOdds, BookOdds, Selection

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class NFLGameResult:
    """Historical NFL game result data."""
    game_id: str
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    game_type: str = "regular"  # "regular", "playoff", "preseason"
    week: int = 1
    season: int = 2023
    closing_spread_home: Optional[float] = None
    closing_total: Optional[float] = None
    date_utc: Optional[str] = None
    overtime: bool = False


@dataclass
class NFLCandidateLeg:
    """A candidate leg for NFL parlay construction."""
    game_id: str
    bookmaker: str
    market: str
    selection_name: str
    line: Optional[float]
    price_decimal: float
    team: Optional[str] = None  # For three-way markets


@dataclass
class NFLParlayOutcome:
    """Result of a single NFL parlay simulation."""
    parlay_id: int
    legs: int
    profit: float
    effective_parlay_odds: float
    segment: str  # "regular", "playoff", "preseason"
    leg_outcomes: List[str]  # "win", "loss", "push"
    week: int
    contains_three_way: bool = False


def parse_nfl_args() -> argparse.Namespace:
    """Parse NFL-specific command line arguments."""
    parser = argparse.ArgumentParser(description="Simulate 10k random NFL parlays for ROI baseline analysis")
    
    parser.add_argument("--sport-key", default="americanfootball_nfl", type=str,
                       help="NFL sport key (default: americanfootball_nfl)")
    parser.add_argument("--regions", default="us", type=str,
                       help="Betting regions (default: us)")
    parser.add_argument("--markets", default="h2h,spreads,totals,three_way", type=str,
                       help="NFL markets including three-way (default: h2h,spreads,totals,three_way)")
    parser.add_argument("--odds-json", type=Path,
                       help="Path to normalized NFL odds snapshot file")
    parser.add_argument("--results-csv", required=True, type=Path,
                       help="Path to historical NFL results CSV file")
    parser.add_argument("--num-parlays", default=10000, type=int,
                       help="Number of random parlays to simulate (default: 10000)")
    parser.add_argument("--legs-min", default=2, type=int,
                       help="Minimum legs per parlay (default: 2)")
    parser.add_argument("--legs-max", default=4, type=int,
                       help="Maximum legs per parlay - NFL typically 2-4 (default: 4)")
    parser.add_argument("--stake-per-parlay", default=100.0, type=float,
                       help="Fixed stake for each parlay in dollars (default: 100.0)")
    parser.add_argument("--seed", default=42, type=int,
                       help="RNG seed for reproducibility (default: 42)")
    parser.add_argument("--include-three-way", action="store_true",
                       help="Include NFL three-way markets (Win/Tie/Loss)")
    parser.add_argument("--export-csv", type=Path,
                       help="Path to export per-parlay outcomes CSV")
    parser.add_argument("--export-json", type=Path,
                       help="Path to export NFL baseline summary JSON")
    parser.add_argument("--verbose", action="store_true",
                       help="Print extra diagnostics")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    return args


def load_nfl_results_csv(path: Path) -> Dict[str, NFLGameResult]:
    """Load historical NFL results from CSV file."""
    results = {}
    
    with open(path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        # Validate required columns for NFL
        required_columns = {'game_id', 'home_team', 'away_team', 'home_score', 'away_score'}
        missing_columns = required_columns - set(reader.fieldnames or [])
        if missing_columns:
            logger.error(f"Missing required columns in NFL results CSV: {missing_columns}")
            exit(2)
        
        for row in reader:
            try:
                game_result = NFLGameResult(
                    game_id=row['game_id'],
                    home_team=row['home_team'],
                    away_team=row['away_team'],
                    home_score=int(row['home_score']),
                    away_score=int(row['away_score']),
                    game_type=row.get('game_type', 'regular'),
                    week=int(row.get('week', 1)),
                    season=int(row.get('season', 2023)),
                    closing_spread_home=float(row['closing_spread_home']) if row.get('closing_spread_home') else None,
                    closing_total=float(row['closing_total']) if row.get('closing_total') else None,
                    date_utc=row.get('date_utc'),
                    overtime=row.get('overtime', '').lower() == 'true'
                )
                results[game_result.game_id] = game_result
            except (ValueError, KeyError) as e:
                logger.warning(f"Skipping invalid NFL row: {e}")
                continue
    
    logger.info(f"Loaded {len(results)} NFL game results from {path}")
    return results


def create_nfl_demo_data() -> Tuple[List[GameOdds], Dict[str, NFLGameResult]]:
    """Create demo NFL data for simulation if no real data available."""
    logger.warning("Using demo NFL data - for testing purposes only")
    
    # Create demo games with NFL-style odds
    demo_games = []
    demo_results = {}
    
    # Game 1: Chiefs vs Bills
    chiefs_bills_books = [
        BookOdds(
            bookmaker="DraftKings",
            market="h2h",
            selections=[
                Selection(name="Kansas City Chiefs", price_decimal=1.75),
                Selection(name="Buffalo Bills", price_decimal=2.15)
            ]
        ),
        BookOdds(
            bookmaker="FanDuel",
            market="spreads",
            selections=[
                Selection(name="Kansas City Chiefs", price_decimal=1.91, line=-3.5),
                Selection(name="Buffalo Bills", price_decimal=1.91, line=3.5)
            ]
        ),
        BookOdds(
            bookmaker="BetMGM",
            market="totals",
            selections=[
                Selection(name="Over", price_decimal=1.91, line=54.5),
                Selection(name="Under", price_decimal=1.91, line=54.5)
            ]
        ),
        BookOdds(
            bookmaker="Caesars",
            market="three_way",
            selections=[
                Selection(name="Kansas City Chiefs", price_decimal=1.85),
                Selection(name="Tie", price_decimal=15.0),
                Selection(name="Buffalo Bills", price_decimal=2.25)
            ]
        )
    ]
    
    chiefs_bills_game = GameOdds(
        game_id="nfl_chiefs_bills_demo",
        sport_key="americanfootball_nfl",
        commence_time="2024-01-21T21:00:00Z",
        books=chiefs_bills_books
    )
    demo_games.append(chiefs_bills_game)
    
    # Add corresponding result (Chiefs win 24-20)
    demo_results["nfl_chiefs_bills_demo"] = NFLGameResult(
        game_id="nfl_chiefs_bills_demo",
        home_team="Buffalo Bills",
        away_team="Kansas City Chiefs", 
        home_score=20,
        away_score=24,
        game_type="playoff",
        week=19,
        season=2024
    )
    
    # Game 2: Cowboys vs Eagles
    cowboys_eagles_books = [
        BookOdds(
            bookmaker="DraftKings",
            market="h2h",
            selections=[
                Selection(name="Dallas Cowboys", price_decimal=2.40),
                Selection(name="Philadelphia Eagles", price_decimal=1.65)
            ]
        ),
        BookOdds(
            bookmaker="FanDuel",
            market="spreads",
            selections=[
                Selection(name="Dallas Cowboys", price_decimal=1.91, line=5.5),
                Selection(name="Philadelphia Eagles", price_decimal=1.91, line=-5.5)
            ]
        ),
        BookOdds(
            bookmaker="BetMGM",
            market="totals",
            selections=[
                Selection(name="Over", price_decimal=1.95, line=47.5),
                Selection(name="Under", price_decimal=1.87, line=47.5)
            ]
        )
    ]
    
    cowboys_eagles_game = GameOdds(
        game_id="nfl_cowboys_eagles_demo",
        sport_key="americanfootball_nfl",
        commence_time="2024-01-14T18:00:00Z",
        books=cowboys_eagles_books
    )
    demo_games.append(cowboys_eagles_game)
    
    # Add corresponding result (Eagles win 31-17)
    demo_results["nfl_cowboys_eagles_demo"] = NFLGameResult(
        game_id="nfl_cowboys_eagles_demo",
        home_team="Philadelphia Eagles",
        away_team="Dallas Cowboys",
        home_score=31,
        away_score=17,
        game_type="playoff",
        week=18,
        season=2024
    )
    
    # Game 3: 49ers vs Packers  
    niners_packers_books = [
        BookOdds(
            bookmaker="DraftKings",
            market="h2h", 
            selections=[
                Selection(name="San Francisco 49ers", price_decimal=1.55),
                Selection(name="Green Bay Packers", price_decimal=2.50)
            ]
        ),
        BookOdds(
            bookmaker="FanDuel",
            market="spreads",
            selections=[
                Selection(name="San Francisco 49ers", price_decimal=1.91, line=-7.5),
                Selection(name="Green Bay Packers", price_decimal=1.91, line=7.5)
            ]
        ),
        BookOdds(
            bookmaker="BetMGM",
            market="totals",
            selections=[
                Selection(name="Over", price_decimal=1.91, line=49.5),
                Selection(name="Under", price_decimal=1.91, line=49.5)
            ]
        )
    ]
    
    niners_packers_game = GameOdds(
        game_id="nfl_49ers_packers_demo",
        sport_key="americanfootball_nfl",
        commence_time="2024-01-13T21:30:00Z",
        books=niners_packers_books
    )
    demo_games.append(niners_packers_game)
    
    # Add corresponding result (49ers win 24-21)
    demo_results["nfl_49ers_packers_demo"] = NFLGameResult(
        game_id="nfl_49ers_packers_demo",
        home_team="Green Bay Packers",
        away_team="San Francisco 49ers",
        home_score=21,
        away_score=24,
        game_type="playoff",
        week=18,
        season=2024
    )
    
    return demo_games, demo_results


def load_nfl_odds_snapshot(args: argparse.Namespace) -> List[GameOdds]:
    """Load NFL odds snapshot from file or create demo data."""
    if args.odds_json and args.odds_json.exists():
        logger.info(f"Loading NFL odds from {args.odds_json}")
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
        logger.info("Creating demo NFL odds data")
        demo_games, _ = create_nfl_demo_data()
        return demo_games


def build_nfl_candidate_pool(games: List[GameOdds], markets: List[str], 
                           include_three_way: bool = False) -> List[NFLCandidateLeg]:
    """Build candidate pool of NFL legs from odds data."""
    candidates = []
    seen = set()  # For deduplication
    
    for game in games:
        for book in game.books:
            if book.market not in markets:
                continue
            
            # Skip three-way markets if not requested
            if book.market == "three_way" and not include_three_way:
                continue
            
            for selection in book.selections:
                # Create unique key for deduplication
                key = (game.game_id, book.market, selection.name, selection.line, book.bookmaker)
                if key in seen:
                    continue
                seen.add(key)
                
                # Extract team for three-way markets
                team = None
                if book.market == "three_way" and selection.name not in ["Tie", "Draw"]:
                    team = selection.name
                
                candidates.append(NFLCandidateLeg(
                    game_id=game.game_id,
                    bookmaker=book.bookmaker,
                    market=book.market,
                    selection_name=selection.name,
                    line=selection.line,
                    price_decimal=selection.price_decimal,
                    team=team
                ))
    
    logger.info(f"Built NFL candidate pool: {len(candidates)} unique legs from {len(games)} games")
    return candidates


def sample_nfl_parlay(rng: random.Random, candidate_pool: List[NFLCandidateLeg], 
                     legs_min: int, legs_max: int) -> List[NFLCandidateLeg]:
    """Sample a random NFL parlay from the candidate pool."""
    num_legs = rng.randint(legs_min, legs_max)
    
    # Sample legs with constraints: max 1 leg per game, avoid conflicting markets
    selected_legs = []
    used_games = set()
    used_game_markets = set()  # Track game+market combinations
    
    # Shuffle candidates to avoid bias
    shuffled_candidates = candidate_pool.copy()
    rng.shuffle(shuffled_candidates)
    
    for leg in shuffled_candidates:
        if len(selected_legs) >= num_legs:
            break
        
        # Avoid multiple legs from same game
        if leg.game_id in used_games:
            continue
        
        # Avoid conflicting markets in same game (e.g., h2h and three_way)
        game_market_key = (leg.game_id, leg.market)
        conflicting_markets = {
            "h2h": ["three_way"],
            "three_way": ["h2h"]
        }
        
        has_conflict = False
        if leg.market in conflicting_markets:
            for conflict_market in conflicting_markets[leg.market]:
                if (leg.game_id, conflict_market) in used_game_markets:
                    has_conflict = True
                    break
        
        if not has_conflict:
            selected_legs.append(leg)
            used_games.add(leg.game_id)
            used_game_markets.add(game_market_key)
    
    return selected_legs


def settle_nfl_leg(leg: NFLCandidateLeg, game_result: NFLGameResult) -> str:
    """Settle a single NFL leg based on game result."""
    if leg.market == "h2h":
        # Head-to-head: winner by final score
        if game_result.home_team in leg.selection_name:
            return "win" if game_result.home_score > game_result.away_score else "loss"
        elif game_result.away_team in leg.selection_name:
            return "win" if game_result.away_score > game_result.home_score else "loss"
        else:
            logger.warning(f"Could not determine winner for NFL h2h leg: {leg.selection_name}")
            return "loss"
    
    elif leg.market == "three_way":
        # Three-way: Win/Tie/Loss including ties
        if "tie" in leg.selection_name.lower() or "draw" in leg.selection_name.lower():
            return "win" if game_result.home_score == game_result.away_score else "loss"
        elif game_result.home_team in leg.selection_name:
            return "win" if game_result.home_score > game_result.away_score else "loss"
        elif game_result.away_team in leg.selection_name:
            return "win" if game_result.away_score > game_result.home_score else "loss"
        else:
            logger.warning(f"Could not determine winner for NFL three-way leg: {leg.selection_name}")
            return "loss"
    
    elif leg.market == "spreads":
        # Spread: team margin vs line
        if leg.line is None:
            logger.warning(f"No line for NFL spread leg: {leg.selection_name}")
            return "loss"
        
        # Determine which team this selection represents
        is_home_team = game_result.home_team in leg.selection_name
        
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
            logger.warning(f"No line for NFL totals leg: {leg.selection_name}")
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
            logger.warning(f"Could not determine over/under for NFL totals leg: {leg.selection_name}")
            return "loss"
    
    else:
        logger.warning(f"Unknown NFL market type: {leg.market}")
        return "loss"


def settle_nfl_parlay(legs: List[NFLCandidateLeg], leg_outcomes: List[str]) -> Tuple[float, float, str]:
    """Settle an NFL parlay based on leg outcomes."""
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


def determine_nfl_segment(legs: List[NFLCandidateLeg], 
                         game_results: Dict[str, NFLGameResult]) -> Tuple[str, int]:
    """Determine segment (regular/playoff/preseason) and week for an NFL parlay."""
    game_types = set()
    weeks = set()
    
    for leg in legs:
        if leg.game_id in game_results:
            result = game_results[leg.game_id]
            game_types.add(result.game_type)
            weeks.add(result.week)
    
    # Determine segment priority: playoff > regular > preseason
    if "playoff" in game_types:
        segment = "playoff"
    elif "regular" in game_types:
        segment = "regular"
    else:
        segment = "preseason"
    
    # Use most common week
    week = max(weeks) if weeks else 1
    
    return segment, week


def run_nfl_simulation(args: argparse.Namespace, candidate_pool: List[NFLCandidateLeg], 
                      game_results: Dict[str, NFLGameResult]) -> List[NFLParlayOutcome]:
    """Run the main NFL simulation."""
    if len(candidate_pool) < args.legs_min:
        logger.error(f"Insufficient NFL candidate legs ({len(candidate_pool)}) for minimum legs ({args.legs_min})")
        exit(3)
    
    rng = random.Random(args.seed)
    outcomes = []
    
    logger.info(f"Starting NFL simulation: {args.num_parlays} parlays, {args.legs_min}-{args.legs_max} legs each")
    
    for parlay_id in range(args.num_parlays):
        if parlay_id % 1000 == 0 and parlay_id > 0:
            logger.info(f"Processed {parlay_id} NFL parlays...")
        
        # Sample parlay
        legs = sample_nfl_parlay(rng, candidate_pool, args.legs_min, args.legs_max)
        
        if len(legs) < args.legs_min:
            logger.warning(f"Could not sample enough legs for NFL parlay {parlay_id}")
            continue
        
        # Check if contains three-way markets
        contains_three_way = any(leg.market == "three_way" for leg in legs)
        
        # Settle each leg
        leg_outcomes = []
        for leg in legs:
            if leg.game_id in game_results:
                outcome = settle_nfl_leg(leg, game_results[leg.game_id])
                leg_outcomes.append(outcome)
            else:
                logger.warning(f"No result for NFL game {leg.game_id}")
                leg_outcomes.append("loss")
        
        # Settle parlay
        effective_odds, profit_multiplier, status = settle_nfl_parlay(legs, leg_outcomes)
        profit = args.stake_per_parlay * profit_multiplier
        
        # Determine segment and week
        segment, week = determine_nfl_segment(legs, game_results)
        
        outcomes.append(NFLParlayOutcome(
            parlay_id=parlay_id,
            legs=len(legs),
            profit=profit,
            effective_parlay_odds=effective_odds,
            segment=segment,
            leg_outcomes=leg_outcomes,
            week=week,
            contains_three_way=contains_three_way
        ))
    
    logger.info(f"NFL simulation complete: {len(outcomes)} parlays processed")
    return outcomes


def summarize_nfl_results(outcomes: List[NFLParlayOutcome], args: argparse.Namespace) -> Dict[str, Any]:
    """Generate NFL-specific summary statistics."""
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
    
    # NFL-specific segment stats
    segments = {}
    for segment in ["regular", "playoff", "preseason"]:
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
    
    # Three-way market analysis
    three_way_outcomes = [o for o in outcomes if o.contains_three_way]
    regular_outcomes = [o for o in outcomes if not o.contains_three_way]
    
    three_way_stats = {}
    if three_way_outcomes:
        tw_stake = len(three_way_outcomes) * args.stake_per_parlay
        tw_profit = sum(o.profit for o in three_way_outcomes)
        tw_roi = (tw_profit / tw_stake) * 100 if tw_stake > 0 else 0
        tw_wins = sum(1 for o in three_way_outcomes if o.profit > 0)
        tw_hit_rate = (tw_wins / len(three_way_outcomes)) * 100 if three_way_outcomes else 0
        
        three_way_stats = {
            "count": len(three_way_outcomes),
            "roi_percent": tw_roi,
            "hit_rate": tw_hit_rate
        }
    
    regular_market_stats = {}
    if regular_outcomes:
        reg_stake = len(regular_outcomes) * args.stake_per_parlay
        reg_profit = sum(o.profit for o in regular_outcomes)
        reg_roi = (reg_profit / reg_stake) * 100 if reg_stake > 0 else 0
        reg_wins = sum(1 for o in regular_outcomes if o.profit > 0)
        reg_hit_rate = (reg_wins / len(regular_outcomes)) * 100 if regular_outcomes else 0
        
        regular_market_stats = {
            "count": len(regular_outcomes),
            "roi_percent": reg_roi,
            "hit_rate": reg_hit_rate
        }
    
    return {
        "parameters": {
            "sport_key": args.sport_key,
            "num_parlays": args.num_parlays,
            "legs_min": args.legs_min,
            "legs_max": args.legs_max,
            "stake_per_parlay": args.stake_per_parlay,
            "seed": args.seed,
            "include_three_way": args.include_three_way
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
        "market_analysis": {
            "three_way_markets": three_way_stats,
            "regular_markets": regular_market_stats
        },
        "nfl_insights": {
            "candidate_pool_size": len(outcomes[0].leg_outcomes) if outcomes else 0,
            "three_way_parlays": len(three_way_outcomes),
            "avg_week": sum(o.week for o in outcomes) / len(outcomes) if outcomes else 0
        }
    }


def write_nfl_csv(outcomes: List[NFLParlayOutcome], path: Optional[Path]):
    """Write NFL per-parlay outcomes to CSV if path provided."""
    if not path:
        return
    
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['parlay_id', 'legs', 'effective_odds', 'profit', 'segment', 'week', 'contains_three_way'])
        
        for outcome in outcomes:
            writer.writerow([
                outcome.parlay_id,
                outcome.legs,
                outcome.effective_parlay_odds,
                outcome.profit,
                outcome.segment,
                outcome.week,
                outcome.contains_three_way
            ])
    
    logger.info(f"Exported {len(outcomes)} NFL parlay outcomes to {path}")


def write_nfl_json(summary: Dict[str, Any], path: Optional[Path]):
    """Write NFL summary to JSON if path provided."""
    if not path:
        return
    
    with open(path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"Exported NFL baseline summary to {path}")


def main():
    """Main entry point for NFL baseline simulation."""
    args = parse_nfl_args()
    
    # Print NFL run header
    print(f"=== NFL Baseline Simulation - 10k Random Parlays ===")
    print(f"Sport: {args.sport_key}")
    print(f"Target Parlays: {args.num_parlays:,}")
    print(f"Legs per Parlay: {args.legs_min}-{args.legs_max}")
    print(f"Stake per Parlay: ${args.stake_per_parlay}")
    print(f"Include Three-Way: {args.include_three_way}")
    print(f"RNG Seed: {args.seed}")
    print(f"Results Database: {args.results_csv}")
    print()
    
    # Load NFL data
    if args.results_csv.exists():
        game_results = load_nfl_results_csv(args.results_csv)
    else:
        logger.warning("No results CSV found, using demo data")
        _, game_results = create_nfl_demo_data()
    
    nfl_games = load_nfl_odds_snapshot(args)
    
    # Build NFL candidate pool
    markets = args.markets.split(',')
    candidate_pool = build_nfl_candidate_pool(nfl_games, markets, args.include_three_way)
    
    # Run NFL simulation
    outcomes = run_nfl_simulation(args, candidate_pool, game_results)
    
    # Generate NFL summary
    summary = summarize_nfl_results(outcomes, args)
    
    # Print NFL results
    print(f"=== NFL Baseline Results ===")
    print(f"Random Parlay ROI: {summary['overall']['roi_percent']:.2f}%")
    print(f"Random Parlay Hit Rate: {summary['overall']['hit_rate']:.2f}%")
    print(f"Total Profit/Loss: ${summary['overall']['total_profit']:.2f}")
    print(f"Average Legs: {summary['overall']['avg_legs']:.1f}")
    print(f"Average Odds: {summary['overall']['avg_odds']:.2f}")
    print()
    
    # NFL segment results
    for segment, stats in summary['segments'].items():
        print(f"{segment.title()} Season:")
        print(f"  ROI: {stats['roi_percent']:.2f}%")
        print(f"  Hit Rate: {stats['hit_rate']:.2f}%")
        print(f"  Parlays: {stats['count']:,}")
        print()
    
    # Market analysis
    if 'market_analysis' in summary:
        ma = summary['market_analysis']
        if ma.get('three_way_markets'):
            print(f"Three-Way Markets:")
            print(f"  ROI: {ma['three_way_markets']['roi_percent']:.2f}%")
            print(f"  Hit Rate: {ma['three_way_markets']['hit_rate']:.2f}%")
            print()
        
        if ma.get('regular_markets'):
            print(f"Regular Markets (H2H/Spreads/Totals):")
            print(f"  ROI: {ma['regular_markets']['roi_percent']:.2f}%")
            print(f"  Hit Rate: {ma['regular_markets']['hit_rate']:.2f}%")
            print()
    
    # Diagnostics
    print(f"=== NFL Simulation Diagnostics ===")
    print(f"Games with results: {len(game_results)}")
    print(f"Games with odds: {len(nfl_games)}")
    print(f"NFL candidate legs: {len(candidate_pool):,}")
    print(f"Successful parlays: {len(outcomes):,}")
    if 'nfl_insights' in summary:
        insights = summary['nfl_insights']
        print(f"Three-way parlays: {insights.get('three_way_parlays', 0):,}")
        print(f"Average week: {insights.get('avg_week', 0):.1f}")
    print()
    
    print(f"✅ NFL Baseline Simulation Complete!")
    print(f"📊 Random parlay baseline established for ROI comparison")
    print(f"🎯 Use this data to compare against intelligent NFL strategies")
    
    # Export if requested
    write_nfl_csv(outcomes, args.export_csv)
    write_nfl_json(summary, args.export_json)


if __name__ == "__main__":
    main()
