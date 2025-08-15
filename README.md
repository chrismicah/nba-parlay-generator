# NBA Parlay Generator

A comprehensive NBA betting analysis and parlay generation system with multi-sportsbook validation capabilities.

## 🏀 Features

- **Parlay Generation**: AI-powered parlay suggestions based on historical data and odds analysis
- **Multi-Sportsbook Validation**: Automated betslip testing across FanDuel, DraftKings, and Bet365
- **Injury Analysis**: Real-time injury severity classification using BioBERT
- **Odds Monitoring**: Live odds fetching and closing line value (CLV) tracking
- **Data Collection**: Automated scraping from multiple NBA news sources
- **Performance Tracking**: Comprehensive ROI and performance analytics

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd nba-parlay-generator

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (for betslip simulator)
playwright install
```

### 2. Environment Setup

```bash
# Set up environment variables
python setup_env.py

# Edit .env file with your credentials
nano .env
```

Required environment variables:
```bash
# API Keys
THE_ODDS_API_KEY=your_odds_api_key
BALLDONTLIE_API_KEY=your_balldontlie_api_key

# Sportsbook Credentials (for betslip simulator)
FANDUEL_EMAIL=your_fanduel_email
FANDUEL_PASSWORD=your_fanduel_password
DRAFTKINGS_EMAIL=your_draftkings_email
DRAFTKINGS_PASSWORD=your_draftkings_password
BET365_USERNAME=your_bet365_username
BET365_PASSWORD=your_bet365_password

# Optional MFA Codes
FANDUEL_MFA_CODE=your_fanduel_mfa_code
DRAFTKINGS_MFA_CODE=your_draftkings_mfa_code
BET365_MFA_CODE=your_bet365_mfa_code
```

## 📊 Core Components

### 1. Baseline Simulation (`simulations/baseline_simulation.py`)

Generate ROI baselines for random parlay performance analysis.

```bash
# Run 10,000 random parlay simulations
python simulations/baseline_simulation.py \
    --sport-key basketball_nba \
    --results-csv data/game_results.csv \
    --num-parlays 10000 \
    --legs-min 2 \
    --legs-max 3 \
    --stake-per-parlay 1.0 \
    --seed 42 \
    --export-csv results/baseline_results.csv \
    --export-json results/baseline_summary.json
```

**Features:**
- Simulates random 2-3 leg parlays
- Separate analysis for Summer League vs Regular season
- Comprehensive ROI and hit rate metrics
- Deterministic results with seed control
- CSV/JSON export capabilities

### 2. Betslip Simulator (`scripts/betslip_simulator.py`)

Validate parlay construction across multiple sportsbooks.

```bash
# Test a parlay on FanDuel
python scripts/betslip_simulator.py \
    --books fanduel \
    --sport-key basketball_nba \
    --game-id "lakers_warriors_20241215" \
    --home "Los Angeles Lakers" \
    --away "Golden State Warriors" \
    --legs-json data/parlay_legs.json \
    --headed \
    --mfa-prompt
```

**Features:**
- Multi-sportsbook support (FanDuel, DraftKings, Bet365)
- Automated login with MFA support
- Real-time betslip validation
- Screenshot and video capture for debugging
- State persistence between runs

### 3. Data Collection

```bash
# Run all scrapers
python scripts/run_scrapers.py

# Scrape specific sources
python scripts/scrape_twitter_api.py
python scripts/scrape_additional_nba_tweets.py
```

### 4. Performance Analysis

```bash
# Generate performance report
python scripts/performance_reporter.py --db data/parlays.sqlite

# Update bet results
python scripts/update_bet_results.py --db data/parlays.sqlite
```

## 🔧 Advanced Usage

### Betslip Simulator MFA Handling

The betslip simulator supports multiple MFA approaches:

```bash
# Interactive prompts
python scripts/betslip_simulator.py --mfa-prompt --headed

# Direct code input
python scripts/betslip_simulator.py --mfa-code 123456 --headed

# Manual login (no stored credentials)
python scripts/betslip_simulator.py --manual-login --headed

# Environment variable MFA codes
export FANDUEL_MFA_CODE=123456
python scripts/betslip_simulator.py --headed
```

### Baseline Simulation Options

```bash
# Summer League specific analysis
python simulations/baseline_simulation.py \
    --summer-league-flag \
    --results-csv data/summer_league_results.csv

# Custom markets
python simulations/baseline_simulation.py \
    --markets "h2h,spreads" \
    --regions "us,uk"

# Use pre-fetched odds
python simulations/baseline_simulation.py \
    --odds-json data/odds_snapshot.json
```

## 📁 Project Structure

```
nba-parlay-generator/
├── app/                    # Main application
├── scripts/               # Utility scripts
│   ├── betslip_simulator.py    # Multi-sportsbook validation
│   ├── performance_reporter.py # Performance analytics
│   └── run_scrapers.py         # Data collection
├── simulations/           # Simulation tools
│   ├── baseline_simulation.py  # ROI baseline analysis
│   └── README.md
├── tools/                 # Core tools and utilities
├── data/                  # Data storage
│   ├── parlays.sqlite     # SQLite database
│   └── chunks/            # Processed data chunks
├── models/                # ML models
├── tests/                 # Test suite
└── artifacts/             # Generated artifacts
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Test specific components
pytest tests/test_baseline_simulation.py
pytest tests/test_betslip_simulator.py

# Run with coverage
pytest --cov=scripts --cov=simulations --cov=tools
```

## 📈 Database Schema

The system uses SQLite for data storage (`data/parlays.sqlite`):

```sql
-- Bets table
CREATE TABLE bets (
    bet_id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT NOT NULL,
    parlay_id TEXT NOT NULL,
    leg_description TEXT NOT NULL,
    odds REAL NOT NULL,
    stake REAL NOT NULL,
    predicted_outcome TEXT NOT NULL,
    actual_outcome TEXT,
    is_win INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    odds_at_alert REAL,
    closing_line_odds REAL,
    clv_percentage REAL
);
```

## 🔒 Security Notes

- **Credentials**: Never commit `.env` files to version control
- **MFA Codes**: Use time-based codes from authenticator apps
- **State Files**: Browser state files are automatically `.gitignored`
- **Logging**: Sensitive information is automatically redacted from logs

## 🐛 Troubleshooting

### Common Issues

1. **Playwright Installation**
   ```bash
   pip install playwright
   playwright install
   ```

2. **Missing Credentials**
   ```bash
   # Check .env file exists and has correct format
   cat .env
   
   # Use manual login as fallback
   python scripts/betslip_simulator.py --manual-login --headed
   ```

3. **MFA Issues**
   ```bash
   # Use interactive prompts
   python scripts/betslip_simulator.py --mfa-prompt --headed
   
   # Or manual login
   python scripts/betslip_simulator.py --manual-login --headed
   ```

4. **Database Issues**
   ```bash
   # Check database exists
   ls -la data/parlays.sqlite
   
   # Recreate if needed
   python -c "from tools.bets_logger import BetsLogger; BetsLogger().ensure_schema()"
   ```

## 📚 Documentation

- [Betslip Simulator Guide](scripts/README.md) - Detailed betslip simulator documentation
- [Baseline Simulation Guide](simulations/README.md) - ROI baseline analysis documentation
- [BioBERT Injury Classifier](README_BioBERT_Injury_Classifier.md) - Injury analysis documentation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This tool is for educational and research purposes only. Please ensure compliance with local gambling laws and sportsbook terms of service. The authors are not responsible for any financial losses incurred through the use of this software.
