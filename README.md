# NBA/NFL Parlay System 🏀🏈

A comprehensive containerized sports betting analysis and parlay generation system supporting both NBA and NFL with ML prediction layer, expert knowledge base, and automated scheduling.

## 🎯 Features

- **Multi-Sport Support**: Full NBA and NFL parlay generation
- **ML Prediction Layer**: Advanced machine learning models for both sports
- **Expert Knowledge Base**: Integration with Ed Miller and Wayne Winston sports betting books
- **Automated Scheduling**: APScheduler for daily game triggers (NFL: Thu/Sun/Mon, NBA: Daily)
- **Container-Ready**: Full Docker containerization with Qdrant and Redis support
- **REST API**: FastAPI endpoints for parlay generation and system monitoring
- **Real-time Monitoring**: Health checks, performance metrics, and job status tracking
- **Production Ready**: Scalable architecture ready for cloud deployment

## 🐳 Docker Quick Start (Recommended)

### 1. Docker Compose Setup

```bash
# Clone the repository
git clone <repository-url>
cd nba_parlay_project

# Create environment file
cp .env.example .env
# Edit .env with your API keys and configuration

# Build and start all services
docker-compose build
docker-compose up

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### 2. Health Check & Testing

```bash
# Check system health
curl http://localhost:8000/health

# Generate NFL parlay
curl -X POST http://localhost:8000/generate-nfl-parlay \
  -H "Content-Type: application/json" \
  -d '{"target_legs": 3, "min_total_odds": 5.0}'

# Generate NBA parlay  
curl -X POST http://localhost:8000/generate-nba-parlay \
  -H "Content-Type: application/json" \
  -d '{"target_legs": 3, "min_total_odds": 5.0}'

# Search knowledge base
curl "http://localhost:8000/knowledge-base/search?query=value betting&top_k=3"
```

### 3. Production Environment Variables

```bash
# Sports Configuration
ENABLE_NFL=true
ENABLE_NBA=true
PRE_GAME_HOURS=3

# External Services
REDIS_URL=redis://redis:6379/0
QDRANT_URL=http://qdrant:6333

# API Keys (required)
THE_ODDS_API_KEY=your_odds_api_key
BALLDONTLIE_API_KEY=your_balldontlie_key
API_SPORTS_KEY=your_api_football_key
```

## 🔧 Manual Installation (Development)

### 1. Prerequisites

```bash
# Install Python 3.10+
python --version  # Should be 3.10 or higher

# Clone the repository
git clone <repository-url>
cd nba_parlay_project

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements_production.txt

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

## 🏗️ Container Architecture

The system is fully containerized with the following services:

### Docker Services

```yaml
# docker-compose.yml services
web:           # FastAPI + APScheduler + ML Layer
  - NBA/NFL parlay generation endpoints
  - Automated scheduling triggers
  - Health monitoring and metrics
  - ML model inference

qdrant:        # Vector Database (Optional)
  - Knowledge base embeddings
  - Semantic search capabilities
  - Expert content indexing

redis:         # Caching Layer (Optional)  
  - API response caching
  - Session management
  - Background task queuing
```

### Container Features

- **Volume Mounts**: Models, data chunks, and logs are persisted
- **Environment Configuration**: Sports toggles, API keys, and service URLs
- **Health Checks**: Automated monitoring for all services
- **Scalability**: Ready for horizontal scaling and cloud deployment
- **Security**: No hardcoded credentials, environment-based configuration

### Exposed Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | System status and component health |
| `/health` | GET | Detailed health check for monitoring |
| `/system-health` | GET | Container-specific health metrics |
| `/generate-nfl-parlay` | POST | Generate NFL parlay recommendation |
| `/generate-nba-parlay` | POST | Generate NBA parlay recommendation |
| `/knowledge-base/search` | GET | Search expert knowledge base |
| `/stats` | GET | System statistics and performance |

### Scheduler Configuration

```yaml
NFL Schedule:
  days: [thursday, sunday, monday]
  times: [13:00, 16:25, 20:20]  # Eastern Time
  season: [August - February]

NBA Schedule:  
  days: [tuesday, wednesday, thursday, friday, saturday, sunday]
  times: [19:00, 20:00, 20:30, 21:00, 22:00]  # Eastern Time
  season: [October - June]
```

## 📁 Project Structure

```
nba_parlay_project/
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
