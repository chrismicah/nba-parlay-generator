# Baseline Simulation

This module provides functionality to simulate random parlay betting for ROI baseline analysis.

## Overview

The baseline simulation generates random 2-3 leg parlays from available betting markets and evaluates their performance using historical game results. This establishes a baseline ROI for comparison against more sophisticated parlay strategies.

## Features

- **Random Parlay Generation**: Creates random 2-3 leg parlays from available markets
- **Market Support**: Handles h2h, spreads, and totals markets
- **Historical Evaluation**: Uses actual game results to determine parlay outcomes
- **Summer League Support**: Separate baselines for Summer League and regular season
- **Deterministic**: Reproducible results with configurable RNG seed
- **Export Options**: CSV and JSON output formats
- **Comprehensive Statistics**: ROI, hit rate, profit distribution, and segment analysis

## Usage

### Command Line Interface

```bash
python simulations/baseline_simulation.py \
    --sport-key basketball_nba \
    --results-csv path/to/results.csv \
    --num-parlays 10000 \
    --seed 42 \
    --export-csv parlay_outcomes.csv \
    --export-json summary.json
```

### Key Parameters

- `--sport-key`: Sport identifier (e.g., basketball_nba, basketball_nba_summer_league)
- `--results-csv`: Path to historical game results CSV file
- `--odds-json`: Optional path to odds snapshot JSON (if not provided, fetches live data)
- `--num-parlays`: Number of random parlays to simulate (default: 10000)
- `--legs-min/--legs-max`: Range of legs per parlay (default: 2-3)
- `--stake-per-parlay`: Fixed stake amount (default: 1.0)
- `--seed`: RNG seed for reproducibility (default: 42)
- `--summer-league-flag`: Force treat all games as Summer League
- `--export-csv/--export-json`: Output file paths

## Input Data Formats

### Results CSV Schema

Required columns:
- `game_id`: Unique game identifier
- `home_team`: Home team name
- `away_team`: Away team name
- `home_score`: Final home team score
- `away_score`: Final away team score

Optional columns:
- `closing_spread_home`: Closing spread (positive = home favored)
- `closing_total`: Closing total points
- `date_utc`: Game date in ISO 8601 format
- `league`: League type ("summer" or "regular")

### Odds JSON Schema

```json
[
  {
    "sport_key": "basketball_nba",
    "game_id": "game1",
    "commence_time": "2024-01-01T00:00:00Z",
    "books": [
      {
        "bookmaker": "fanduel",
        "market": "h2h",
        "selections": [
          {"name": "Lakers", "price_decimal": 1.85, "line": null},
          {"name": "Warriors", "price_decimal": 1.95, "line": null}
        ]
      }
    ]
  }
]
```

## Output Formats

### Console Output

```
=== Baseline Simulation Run ===
Sport: basketball_nba
Parlays: 10000
Legs: 2-3
Stake: $1.0
Seed: 42
Database: results.csv

=== Results ===
Overall ROI: -4.25%
Overall Hit Rate: 12.34%
Total Profit: $-425.00
Average Legs: 2.5
Average Odds: 3.45

Regular League:
  ROI: -3.85%
  Hit Rate: 13.12%
  Parlays: 8500

Summer League:
  ROI: -6.12%
  Hit Rate: 8.45%
  Parlays: 1500
```

### CSV Export

Columns: `parlay_id`, `legs`, `effective_odds`, `profit`, `segment`

### JSON Export

```json
{
  "parameters": {
    "sport_key": "basketball_nba",
    "num_parlays": 10000,
    "legs_min": 2,
    "legs_max": 3,
    "stake_per_parlay": 1.0,
    "seed": 42,
    "summer_league_flag": false
  },
  "overall": {
    "total_parlays": 10000,
    "total_stake": 10000.0,
    "total_profit": -425.0,
    "roi_percent": -4.25,
    "hit_rate": 12.34,
    "avg_legs": 2.5,
    "avg_odds": 3.45,
    "profit_stats": {
      "min": -1.0,
      "max": 15.2,
      "mean": -0.0425,
      "median": -1.0
    }
  },
  "segments": {
    "regular": {
      "count": 8500,
      "total_stake": 8500.0,
      "total_profit": -327.25,
      "roi_percent": -3.85,
      "hit_rate": 13.12
    },
    "summer": {
      "count": 1500,
      "total_stake": 1500.0,
      "total_profit": -91.75,
      "roi_percent": -6.12,
      "hit_rate": 8.45
    }
  }
}
```

## Settlement Rules

### Head-to-Head (h2h)
- Winner determined by final score
- Team with higher score wins

### Spreads
- Team margin vs line determines outcome
- Positive margin - line > 0 = win
- Positive margin - line = 0 = push
- Positive margin - line < 0 = loss

### Totals
- Combined score vs line determines outcome
- For "Over": total score - line > 0 = win
- For "Under": total score - line < 0 = win
- Equal = push

### Parlay Settlement
- Any leg loss = parlay loss
- All legs win/push with at least one win = parlay win
- All legs push = stake returned (no profit/loss)
- Effective odds calculated from winning legs only

## Examples

### Basic Usage

```python
from simulations.baseline_simulation import main

# Run with live odds data
main([
    "--sport-key", "basketball_nba",
    "--results-csv", "game_results.csv",
    "--num-parlays", "5000",
    "--seed", "123"
])
```

### With Historical Odds

```python
# Use historical odds snapshot
main([
    "--sport-key", "basketball_nba",
    "--odds-json", "historical_odds.json",
    "--results-csv", "game_results.csv",
    "--num-parlays", "10000",
    "--export-csv", "outcomes.csv",
    "--export-json", "summary.json"
])
```

### Summer League Analysis

```python
# Force Summer League analysis
main([
    "--sport-key", "basketball_nba_summer_league",
    "--results-csv", "summer_league_results.csv",
    "--summer-league-flag",
    "--num-parlays", "5000"
])
```

## Testing

Run the test suite:

```bash
python -m pytest tests/test_baseline_simulation.py -v
```

## Dependencies

- Standard library only (no external dependencies)
- Uses existing project modules:
  - `tools.odds_fetcher_tool.OddsFetcherTool`

## Notes

- The simulation is deterministic given the same seed and inputs
- Candidate legs are deduplicated to avoid bias
- Maximum 1 leg per game to avoid correlated selections
- Conservative default: treats unclear selections as losses
- All monetary values are in the same currency as the stake
