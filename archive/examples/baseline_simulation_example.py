#!/usr/bin/env python3
"""
Example usage of the baseline simulation script.

This example demonstrates how to run the baseline simulation with sample data.
"""

import csv
import json
import tempfile
from pathlib import Path

# Import will be handled in the run_example function


def create_sample_data():
    """Create sample data for demonstration."""
    
    # Create sample results CSV
    results_data = [
        ['game_id', 'home_team', 'away_team', 'home_score', 'away_score', 'closing_spread_home', 'closing_total', 'date_utc', 'league'],
        ['game1', 'Lakers', 'Warriors', 110, 105, '2.5', '220.5', '2024-01-01T00:00:00Z', 'regular'],
        ['game2', 'Celtics', 'Heat', 95, 100, '-1.5', '195.0', '2024-01-01T00:00:00Z', 'regular'],
        ['game3', 'Suns', 'Mavericks', 120, 115, '3.0', '225.0', '2024-01-01T00:00:00Z', 'summer'],
        ['game4', 'Bucks', 'Nets', 108, 112, '1.0', '210.0', '2024-01-01T00:00:00Z', 'regular'],
    ]
    
    # Create sample odds JSON
    odds_data = [
        {
            "sport_key": "basketball_nba",
            "game_id": "game1",
            "commence_time": "2024-01-01T00:00:00Z",
            "books": [
                {
                    "bookmaker": "fanduel",
                    "market": "h2h",
                    "selections": [
                        {"name": "Lakers", "price_decimal": 1.85, "line": None},
                        {"name": "Warriors", "price_decimal": 1.95, "line": None}
                    ]
                },
                {
                    "bookmaker": "draftkings",
                    "market": "spreads",
                    "selections": [
                        {"name": "Lakers -2.5", "price_decimal": 1.91, "line": -2.5},
                        {"name": "Warriors +2.5", "price_decimal": 1.91, "line": 2.5}
                    ]
                },
                {
                    "bookmaker": "betmgm",
                    "market": "totals",
                    "selections": [
                        {"name": "Over 220.5", "price_decimal": 1.90, "line": 220.5},
                        {"name": "Under 220.5", "price_decimal": 1.90, "line": 220.5}
                    ]
                }
            ]
        },
        {
            "sport_key": "basketball_nba",
            "game_id": "game2",
            "commence_time": "2024-01-01T00:00:00Z",
            "books": [
                {
                    "bookmaker": "fanduel",
                    "market": "h2h",
                    "selections": [
                        {"name": "Celtics", "price_decimal": 2.10, "line": None},
                        {"name": "Heat", "price_decimal": 1.75, "line": None}
                    ]
                }
            ]
        },
        {
            "sport_key": "basketball_nba",
            "game_id": "game3",
            "commence_time": "2024-01-01T00:00:00Z",
            "books": [
                {
                    "bookmaker": "fanduel",
                    "market": "h2h",
                    "selections": [
                        {"name": "Suns", "price_decimal": 1.80, "line": None},
                        {"name": "Mavericks", "price_decimal": 2.00, "line": None}
                    ]
                }
            ]
        },
        {
            "sport_key": "basketball_nba",
            "game_id": "game4",
            "commence_time": "2024-01-01T00:00:00Z",
            "books": [
                {
                    "bookmaker": "fanduel",
                    "market": "h2h",
                    "selections": [
                        {"name": "Bucks", "price_decimal": 1.90, "line": None},
                        {"name": "Nets", "price_decimal": 1.90, "line": None}
                    ]
                }
            ]
        }
    ]
    
    return results_data, odds_data


def run_example():
    """Run the baseline simulation example."""
    
    # Create temporary files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create sample data
        results_data, odds_data = create_sample_data()
        
        # Write results CSV
        results_csv = temp_path / "sample_results.csv"
        with open(results_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(results_data)
        
        # Write odds JSON
        odds_json = temp_path / "sample_odds.json"
        with open(odds_json, 'w') as f:
            json.dump(odds_data, f, indent=2)
        
        # Create output files
        output_csv = temp_path / "parlay_outcomes.csv"
        output_json = temp_path / "summary.json"
        
        print("=== Baseline Simulation Example ===")
        print(f"Results CSV: {results_csv}")
        print(f"Odds JSON: {odds_json}")
        print(f"Output CSV: {output_csv}")
        print(f"Output JSON: {output_json}")
        print()
        
        # Import and run the simulation
        import sys
        import os
        
        # Add the project root to the path
        project_root = Path(__file__).parent.parent
        sys.path.insert(0, str(project_root))
        
        # Mock command line arguments
        import argparse
        from simulations.baseline_simulation import parse_args, load_results_csv, load_odds_snapshot, build_candidate_pool, run_simulation, summarize, maybe_write_csv, maybe_write_json
        
        # Create args object
        class MockArgs:
            def __init__(self):
                self.sport_key = "basketball_nba"
                self.regions = "us"
                self.markets = "h2h,spreads,totals"
                self.odds_json = odds_json
                self.results_csv = results_csv
                self.num_parlays = 1000  # Smaller number for example
                self.legs_min = 2
                self.legs_max = 3
                self.stake_per_parlay = 1.0
                self.seed = 42
                self.summer_league_flag = False
                self.export_csv = output_csv
                self.export_json = output_json
                self.verbose = True
        
        args = MockArgs()
        
        # Run simulation
        print("Loading data...")
        game_results = load_results_csv(args.results_csv)
        games = load_odds_snapshot(args)
        
        print("Building candidate pool...")
        markets = args.markets.split(',')
        candidate_pool = build_candidate_pool(games, markets)
        
        print("Running simulation...")
        outcomes = run_simulation(args, candidate_pool, game_results)
        
        print("Generating summary...")
        summary = summarize(outcomes, args)
        
        # Print results
        print("\n=== Results ===")
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
        
        # Export results
        maybe_write_csv(outcomes, args.export_csv)
        maybe_write_json(summary, args.export_json)
        
        print("=== Files Created ===")
        print(f"Parlay outcomes: {output_csv}")
        print(f"Summary: {output_json}")
        
        # Show sample of exported data
        print("\n=== Sample Parlay Outcomes ===")
        with open(output_csv, 'r') as f:
            reader = csv.reader(f)
            rows = list(reader)
            for i, row in enumerate(rows[:5]):  # Show first 5 rows
                print(f"  {row}")
        
        print("\n=== Sample Summary ===")
        with open(output_json, 'r') as f:
            summary_data = json.load(f)
            print(f"  Total Parlays: {summary_data['overall']['total_parlays']}")
            print(f"  Overall ROI: {summary_data['overall']['roi_percent']:.2f}%")
            print(f"  Segments: {list(summary_data['segments'].keys())}")


if __name__ == "__main__":
    run_example()
