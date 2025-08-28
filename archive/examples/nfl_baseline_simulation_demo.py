#!/usr/bin/env python3
"""
NFL Baseline Simulation Demo - 10k Random Parlays

Demonstrates the NFL-specific baseline simulation with sample data.
This creates the ROI baseline for comparison with intelligent NFL strategies.
"""

import csv
import json
import tempfile
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def create_nfl_sample_data():
    """Create sample NFL data for baseline simulation demonstration."""
    
    # Create sample NFL results CSV with realistic data
    nfl_results_data = [
        ['game_id', 'home_team', 'away_team', 'home_score', 'away_score', 'closing_spread_home', 'closing_total', 'date_utc', 'game_type', 'week', 'season', 'overtime'],
        
        # Week 18 NFL Games
        ['nfl_chiefs_raiders_w18', 'Kansas City Chiefs', 'Las Vegas Raiders', 13, 31, '12.5', '41.5', '2024-01-07T18:00:00Z', 'regular', 18, 2023, 'false'],
        ['nfl_bills_dolphins_w18', 'Buffalo Bills', 'Miami Dolphins', 21, 14, '-2.5', '42.0', '2024-01-07T18:00:00Z', 'regular', 18, 2023, 'false'],
        ['nfl_eagles_giants_w18', 'Philadelphia Eagles', 'New York Giants', 27, 10, '-12.0', '38.5', '2024-01-07T18:00:00Z', 'regular', 18, 2023, 'false'],
        ['nfl_cowboys_commanders_w18', 'Dallas Cowboys', 'Washington Commanders', 10, 26, '-10.5', '44.0', '2024-01-07T18:00:00Z', 'regular', 18, 2023, 'false'],
        ['nfl_49ers_rams_w18', 'San Francisco 49ers', 'Los Angeles Rams', 21, 20, '-5.5', '43.5', '2024-01-07T18:00:00Z', 'regular', 18, 2023, 'false'],
        ['nfl_seahawks_cardinals_w18', 'Seattle Seahawks', 'Arizona Cardinals', 21, 20, '-5.0', '41.5', '2024-01-07T18:00:00Z', 'regular', 18, 2023, 'true'],
        
        # Wild Card Playoff Games
        ['nfl_bills_steelers_wc', 'Buffalo Bills', 'Pittsburgh Steelers', 31, 17, '-2.5', '43.5', '2024-01-15T16:30:00Z', 'playoff', 19, 2023, 'false'],
        ['nfl_browns_texans_wc', 'Cleveland Browns', 'Houston Texans', 14, 45, '1.5', '44.0', '2024-01-13T16:30:00Z', 'playoff', 19, 2023, 'false'],
        ['nfl_dolphins_chiefs_wc', 'Miami Dolphins', 'Kansas City Chiefs', 7, 26, '12.5', '43.0', '2024-01-13T20:00:00Z', 'playoff', 19, 2023, 'false'],
        ['nfl_packers_cowboys_wc', 'Green Bay Packers', 'Dallas Cowboys', 32, 48, '7.0', '49.5', '2024-01-14T16:30:00Z', 'playoff', 19, 2023, 'false'],
        ['nfl_rams_lions_wc', 'Los Angeles Rams', 'Detroit Lions', 23, 24, '3.5', '51.5', '2024-01-14T20:00:00Z', 'playoff', 19, 2023, 'false'],
        ['nfl_eagles_buccaneers_wc', 'Philadelphia Eagles', 'Tampa Bay Buccaneers', 9, 32, '-2.5', '45.5', '2024-01-15T20:00:00Z', 'playoff', 19, 2023, 'false'],
        
        # Divisional Round
        ['nfl_texans_ravens_div', 'Houston Texans', 'Baltimore Ravens', 10, 34, '9.5', '43.5', '2024-01-20T16:30:00Z', 'playoff', 20, 2023, 'false'],
        ['nfl_chiefs_bills_div', 'Kansas City Chiefs', 'Buffalo Bills', 27, 24, '-2.5', '46.5', '2024-01-21T18:30:00Z', 'playoff', 20, 2023, 'false'],
        ['nfl_packers_49ers_div', 'Green Bay Packers', 'San Francisco 49ers', 21, 24, '7.0', '50.5', '2024-01-20T20:00:00Z', 'playoff', 20, 2023, 'false'],
        ['nfl_buccaneers_lions_div', 'Tampa Bay Buccaneers', 'Detroit Lions', 23, 31, '6.0', '51.5', '2024-01-21T15:00:00Z', 'playoff', 20, 2023, 'false'],
        
        # Conference Championships
        ['nfl_ravens_chiefs_afc', 'Baltimore Ravens', 'Kansas City Chiefs', 17, 27, '3.5', '44.5', '2024-01-28T15:00:00Z', 'playoff', 21, 2023, 'false'],
        ['nfl_49ers_lions_nfc', 'San Francisco 49ers', 'Detroit Lions', 34, 31, '-7.0', '51.5', '2024-01-28T18:30:00Z', 'playoff', 21, 2023, 'false'],
        
        # Super Bowl
        ['nfl_chiefs_49ers_sb', 'Kansas City Chiefs', 'San Francisco 49ers', 25, 22, '-1.5', '47.5', '2024-02-11T18:30:00Z', 'playoff', 22, 2023, 'true'],
    ]
    
    # Create sample NFL odds JSON with realistic three-way markets
    nfl_odds_data = [
        {
            "sport_key": "americanfootball_nfl",
            "game_id": "nfl_chiefs_49ers_sb",
            "commence_time": "2024-02-11T18:30:00Z",
            "books": [
                {
                    "bookmaker": "draftkings",
                    "market": "h2h",
                    "selections": [
                        {"name": "Kansas City Chiefs", "price_decimal": 1.55, "line": None},
                        {"name": "San Francisco 49ers", "price_decimal": 2.50, "line": None}
                    ]
                },
                {
                    "bookmaker": "fanduel",
                    "market": "spreads", 
                    "selections": [
                        {"name": "Kansas City Chiefs", "price_decimal": 1.91, "line": -1.5},
                        {"name": "San Francisco 49ers", "price_decimal": 1.91, "line": 1.5}
                    ]
                },
                {
                    "bookmaker": "betmgm",
                    "market": "totals",
                    "selections": [
                        {"name": "Over", "price_decimal": 1.91, "line": 47.5},
                        {"name": "Under", "price_decimal": 1.91, "line": 47.5}
                    ]
                },
                {
                    "bookmaker": "caesars",
                    "market": "three_way",
                    "selections": [
                        {"name": "Kansas City Chiefs", "price_decimal": 1.65, "line": None},
                        {"name": "Tie", "price_decimal": 20.0, "line": None},
                        {"name": "San Francisco 49ers", "price_decimal": 2.65, "line": None}
                    ]
                }
            ]
        },
        {
            "sport_key": "americanfootball_nfl",
            "game_id": "nfl_49ers_lions_nfc",
            "commence_time": "2024-01-28T18:30:00Z",
            "books": [
                {
                    "bookmaker": "draftkings",
                    "market": "h2h",
                    "selections": [
                        {"name": "San Francisco 49ers", "price_decimal": 1.45, "line": None},
                        {"name": "Detroit Lions", "price_decimal": 2.75, "line": None}
                    ]
                },
                {
                    "bookmaker": "fanduel",
                    "market": "spreads",
                    "selections": [
                        {"name": "San Francisco 49ers", "price_decimal": 1.91, "line": -7.0},
                        {"name": "Detroit Lions", "price_decimal": 1.91, "line": 7.0}
                    ]
                },
                {
                    "bookmaker": "betmgm",
                    "market": "totals",
                    "selections": [
                        {"name": "Over", "price_decimal": 1.87, "line": 51.5},
                        {"name": "Under", "price_decimal": 1.95, "line": 51.5}
                    ]
                },
                {
                    "bookmaker": "caesars",
                    "market": "three_way",
                    "selections": [
                        {"name": "San Francisco 49ers", "price_decimal": 1.55, "line": None},
                        {"name": "Tie", "price_decimal": 12.0, "line": None},
                        {"name": "Detroit Lions", "price_decimal": 2.85, "line": None}
                    ]
                }
            ]
        },
        {
            "sport_key": "americanfootball_nfl",
            "game_id": "nfl_ravens_chiefs_afc",
            "commence_time": "2024-01-28T15:00:00Z",
            "books": [
                {
                    "bookmaker": "draftkings",
                    "market": "h2h",
                    "selections": [
                        {"name": "Baltimore Ravens", "price_decimal": 2.30, "line": None},
                        {"name": "Kansas City Chiefs", "price_decimal": 1.65, "line": None}
                    ]
                },
                {
                    "bookmaker": "fanduel",
                    "market": "spreads",
                    "selections": [
                        {"name": "Baltimore Ravens", "price_decimal": 1.91, "line": 3.5},
                        {"name": "Kansas City Chiefs", "price_decimal": 1.91, "line": -3.5}
                    ]
                },
                {
                    "bookmaker": "betmgm",
                    "market": "totals",
                    "selections": [
                        {"name": "Over", "price_decimal": 1.91, "line": 44.5},
                        {"name": "Under", "price_decimal": 1.91, "line": 44.5}
                    ]
                }
            ]
        }
    ]
    
    return nfl_results_data, nfl_odds_data


def run_nfl_baseline_demo():
    """Run the NFL baseline simulation demo."""
    print("🏈 NFL Baseline Simulation Demo - 10k Random Parlays")
    print("=" * 60)
    print("Creating sample NFL data and running baseline simulation...")
    print()
    
    # Create sample data
    results_data, odds_data = create_nfl_sample_data()
    
    # Create temporary files
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as results_file:
        writer = csv.writer(results_file)
        writer.writerows(results_data)
        results_path = results_file.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as odds_file:
        json.dump(odds_data, odds_file, indent=2)
        odds_path = odds_file.name
    
    # Create output files
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as output_csv:
        output_csv_path = output_csv.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as output_json:
        output_json_path = output_json.name
    
    try:
        # Import and run simulation
        from simulations.nfl_baseline_simulation import main as run_nfl_simulation
        import sys
        
        # Set up arguments for the simulation
        original_argv = sys.argv
        sys.argv = [
            'nfl_baseline_simulation.py',
            '--sport-key', 'americanfootball_nfl',
            '--results-csv', results_path,
            '--odds-json', odds_path,
            '--num-parlays', '1000',  # Smaller for demo
            '--legs-min', '2',
            '--legs-max', '4',
            '--stake-per-parlay', '100.0',
            '--include-three-way',
            '--export-csv', output_csv_path,
            '--export-json', output_json_path,
            '--verbose'
        ]
        
        print("Running NFL baseline simulation...")
        print(f"Simulating 1,000 random NFL parlays...")
        print()
        
        # Run the simulation
        run_nfl_simulation()
        
        # Restore argv
        sys.argv = original_argv
        
        print()
        print("🎯 NFL Baseline Demo Results:")
        
        # Load and display results
        with open(output_json_path, 'r') as f:
            results = json.load(f)
        
        overall = results['overall']
        print(f"   📊 Random Parlay Performance:")
        print(f"      • ROI: {overall['roi_percent']:.2f}%")
        print(f"      • Hit Rate: {overall['hit_rate']:.2f}%")
        print(f"      • Total Profit: ${overall['total_profit']:.2f}")
        print(f"      • Average Odds: {overall['avg_odds']:.2f}")
        print()
        
        # Segment analysis
        if 'segments' in results:
            print(f"   🏈 NFL Season Analysis:")
            for segment, stats in results['segments'].items():
                print(f"      • {segment.title()}: ROI {stats['roi_percent']:.2f}%, Hit Rate {stats['hit_rate']:.2f}%")
            print()
        
        # Market analysis
        if 'market_analysis' in results:
            ma = results['market_analysis']
            print(f"   🎯 Market Type Analysis:")
            if ma.get('three_way_markets'):
                tw = ma['three_way_markets']
                print(f"      • Three-Way Markets: ROI {tw['roi_percent']:.2f}%, Hit Rate {tw['hit_rate']:.2f}%")
            if ma.get('regular_markets'):
                reg = ma['regular_markets']
                print(f"      • Regular Markets: ROI {reg['roi_percent']:.2f}%, Hit Rate {reg['hit_rate']:.2f}%")
            print()
        
        print(f"✅ NFL Baseline Simulation Complete!")
        print(f"📈 Baseline ROI established for intelligent strategy comparison")
        print(f"🔍 Use this data to measure improvement over random selection")
        print()
        print(f"📋 To run full 10k simulation:")
        print(f"   python simulations/nfl_baseline_simulation.py \\")
        print(f"     --sport-key americanfootball_nfl \\")
        print(f"     --results-csv path/to/nfl_results.csv \\")
        print(f"     --num-parlays 10000 \\")
        print(f"     --include-three-way \\")
        print(f"     --export-json nfl_baseline_roi.json")
        
    except Exception as e:
        print(f"❌ Error running NFL baseline simulation: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up temporary files
        try:
            os.unlink(results_path)
            os.unlink(odds_path)
            os.unlink(output_csv_path)
            os.unlink(output_json_path)
        except:
            pass


if __name__ == "__main__":
    run_nfl_baseline_demo()
