# NBA/NFL Parlay System 🏀🏈

A comprehensive, production-ready sports betting analysis and parlay generation system with unified architecture supporting both NBA and NFL through machine learning, expert knowledge base, and automated scheduling.

## 🎯 Key Features

- **🔧 Unified Architecture**: Single `UnifiedParlayStrategistAgent` handles both NBA and NFL with sport-specific data adapters
- **🧠 ML Prediction Layer**: Advanced machine learning models, BioBERT injury classifiers, and Bayesian confidence scoring
- **📚 Expert Knowledge Base**: RAG integration with Ed Miller's "The Logic of Sports Betting" and Wayne Winston's "Mathletics" (1,590+ chunks)
- **⚡ Automated Scheduling**: APScheduler for daily triggers (NFL: Thu/Sun/Mon, NBA: Daily) 
- **🐳 Container-Ready**: Full Docker containerization with Redis and Qdrant support
- **🌐 REST API**: FastAPI endpoints with identical response formats across sports
- **📊 Real-time Monitoring**: Health checks, performance metrics, and system statistics
- **🚀 Production Ready**: Clean, maintainable codebase ready for cloud deployment

## 🏗️ Clean Architecture

After comprehensive cleanup and refactoring, the codebase now follows a clean, organized structure:

```
nba_parlay_project/
├── 📱 app/                    # FastAPI application & routes
│   ├── main.py               # Main development server
│   └── simple_main.py        # Simplified test server
├── 🤖 agents/                # Multi-sport scheduler integration  
│   └── multi_sport_scheduler_integration.py
├── 🔧 tools/                 # Core utilities & adapters
│   ├── unified_parlay_strategist_agent.py  # Main unified agent
│   ├── sport_data_adapters.py              # NFL/NBA data adapters
│   ├── knowledge_base_rag.py               # Expert knowledge RAG
│   ├── odds_fetcher_tool.py                # Odds API integration
│   ├── grok_tweet_fetcher.py               # Twitter monitoring
│   └── [50+ other tools]
├── 🧠 ml/                    # ML models & training
│   ├── ml_prop_trainer.py    # Historical prop modeling
│   ├── ml_qlearning_agent.py # Q-learning optimization
│   └── [10+ other ML modules]
├── 📊 data/                  # Datasets & knowledge base
│   ├── chunks/               # Knowledge base chunks (1,590+)
│   ├── tweets/               # Twitter data & labels
│   ├── ml_training/          # Training datasets
│   └── [comprehensive data]
├── 🧪 tests/                 # Comprehensive test suite
│   ├── test_unified_parlay_system.py       # Unified system tests
│   ├── test_codebase_structure.py          # Structure validation
│   └── [35+ other test files]
├── 📚 docs/                  # Organized documentation
│   ├── architecture/         # System design docs
│   ├── guides/              # User guides & tutorials
│   ├── deployment/          # Production deployment
│   └── [organized by category]
├── 📜 scripts/              # Utility & production scripts
│   ├── production/          # Production deployment scripts
│   ├── betslip_simulator.py # Multi-sportsbook validation
│   └── [10+ utility scripts]
├── 🗃️ models/               # ML model weights & configs
├── 🔧 config/               # Configuration files
├── 🗂️ archive/              # Deprecated code (safely archived)
│   ├── examples/            # Demo scripts
│   └── deprecated_tools/    # Legacy components
└── 🐳 Docker                # Container configuration
    ├── Dockerfile           # Production container
    └── docker-compose.yml   # Multi-service orchestration
```

## 🚀 Quick Start (Docker - Recommended)

### 1. Container Deployment

```bash
# Clone and setup
git clone <repository-url>
cd nba_parlay_project

# Create environment configuration
cp .env.example .env
# Edit .env with your API keys and settings

# Build and start all services
docker-compose build
docker-compose up -d

# View service logs
docker-compose logs -f web

# Check system health
curl http://localhost:8000/health
```

### 2. API Testing

```bash
# Generate NFL parlay (unified response format)
curl -X POST http://localhost:8000/generate-nfl-parlay \
  -H "Content-Type: application/json" \
  -d '{
    "target_legs": 3,
    "min_total_odds": 5.0,
    "include_arbitrage": true
  }'

# Generate NBA parlay (identical response format)
curl -X POST http://localhost:8000/generate-nba-parlay \
  -H "Content-Type: application/json" \
  -d '{
    "target_legs": 3, 
    "min_total_odds": 5.0,
    "include_arbitrage": true
  }'

# Search expert knowledge base
curl "http://localhost:8000/knowledge-base/search?query=value betting&top_k=3"
```

### 3. Unified Response Format

Both NFL and NBA endpoints return identical JSON structure:

```json
{
  "success": true,
  "sport": "NFL" | "NBA",
  "parlay": {
    "legs": [...],
    "confidence": 0.78,
    "expected_value": 0.12,
    "kelly_percentage": 0.05,
    "knowledge_insights": [...],
    "reasoning": "Expert analysis with sport-specific insights"
  },
  "generated_at": "2025-01-27T...",
  "agent_version": "unified_v1.0"
}
```

## 🛠️ Local Development

### 1. Setup

```bash
# Prerequisites: Python 3.8+
python --version

# Setup virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements_production.txt

# Install browser support (for betslip simulator)
playwright install
```

### 2. Environment Configuration

Create `.env` file with required variables:

```bash
# API Keys
THE_ODDS_API_KEY=your_odds_api_key
BALLDONTLIE_API_KEY=your_balldontlie_key
API_SPORTS_KEY=your_api_football_key

# Sports Configuration
ENABLE_NFL=true
ENABLE_NBA=true
PRE_GAME_HOURS=3

# Optional Services
REDIS_URL=redis://localhost:6379/0
QDRANT_URL=http://localhost:6333

# Sportsbook Credentials (for betslip simulator)
FANDUEL_EMAIL=your_email
FANDUEL_PASSWORD=your_password
DRAFTKINGS_EMAIL=your_email
DRAFTKINGS_PASSWORD=your_password
```

### 3. Run Development Server

```bash
# Start development server
cd app/
python main.py

# Or use uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 🏭 Production Deployment

### 1. Production Scripts

```bash
# Start production system
python scripts/production/run_production.py

# With custom configuration
python scripts/production/production_main.py

# Background service
./scripts/production/start_production.sh
```

### 2. Container Services

The system includes three main services:

```yaml
# docker-compose.yml
services:
  web:           # Main application
    - FastAPI + Unified Parlay System
    - APScheduler automated triggers  
    - ML model inference
    - Health monitoring
    
  redis:         # Caching layer
    - API response caching
    - Session management
    - Background task queuing
    
  qdrant:        # Vector database  
    - Knowledge base embeddings
    - Semantic search capabilities
    - Expert content indexing
```

### 3. Health Monitoring

| Endpoint | Description |
|----------|-------------|
| `/health` | Basic health check |
| `/system-health` | Container-specific metrics |
| `/stats` | Performance statistics |

## 🧪 Testing & Validation

### 1. Run Test Suite

```bash
# Full test suite
python -m pytest tests/ -v

# Structure validation tests
python -m pytest tests/test_codebase_structure.py -v

# Unified system tests  
python -m pytest tests/test_unified_parlay_system.py -v

# Test coverage
python -m pytest --cov=app --cov=tools --cov=agents
```

### 2. System Validation

```bash
# Test unified agent creation
python -c "
from tools.unified_parlay_strategist_agent import create_unified_agent
nfl_agent = create_unified_agent('NFL')
nba_agent = create_unified_agent('NBA')
print(f'✅ NFL Agent: {nfl_agent.sport}')
print(f'✅ NBA Agent: {nba_agent.sport}')
"

# Test data source isolation
python -c "
from tools.sport_data_adapters import create_sport_adapter
nfl_adapter = create_sport_adapter('NFL')
nba_adapter = create_sport_adapter('NBA')
nfl_sources = nfl_adapter.get_data_sources()
nba_sources = nba_adapter.get_data_sources()
print(f'NFL Keywords: {nfl_sources.tweet_keywords[:3]}')
print(f'NBA Keywords: {nba_sources.tweet_keywords[:3]}')
"
```

## 🔧 Key Tools & Utilities

### 1. Betslip Simulator

Multi-sportsbook validation with MFA support:

```bash
# Test parlay on FanDuel
python scripts/betslip_simulator.py \
    --books fanduel \
    --sport-key basketball_nba \
    --legs-json data/parlay_legs.json \
    --headed --mfa-prompt

# Automated validation across books
python scripts/betslip_simulator.py \
    --books fanduel,draftkings,bet365 \
    --sport-key americanfootball_nfl
```

### 2. Data Collection

```bash
# Run all scrapers
python scripts/run_scrapers.py

# Twitter monitoring for injuries
python tools/grok_tweet_fetcher.py --sport NFL
python tools/grok_tweet_fetcher.py --sport NBA

# Apify data collection
python tools/apify_injury_tweet_scraper.py
```

### 3. Performance Analysis

```bash
# Generate performance reports
python scripts/performance_reporter.py --db data/parlays.sqlite

# Baseline simulation analysis
python simulations/baseline_simulation.py \
    --sport-key basketball_nba \
    --num-parlays 10000 \
    --export-csv results/baseline.csv
```

## 📊 Architecture Benefits

### ✅ Before vs After Cleanup

| Before | After |
|--------|-------|
| ❌ Two separate agents (NFL & NBA) | ✅ Single unified agent |
| ❌ Inconsistent response formats | ✅ Identical JSON structure |
| ❌ Code duplication (~60%) | ✅ Shared core logic |
| ❌ Mixed sport data sources | ✅ Complete sport isolation |
| ❌ Scattered documentation | ✅ Organized `/docs` structure |
| ❌ No containerization tests | ✅ Comprehensive test suite |

### 🏗️ Unified System Features

- **Sport Isolation**: NFL uses only NFL APIs/data, NBA uses only NBA APIs/data
- **Shared Logic**: Odds analysis, ML predictions, confidence scoring unified
- **Consistent Interface**: Identical methods and response formats
- **Extensible Design**: Easy to add new sports (MLB, NHL, etc.)
- **Clean Architecture**: Well-organized, maintainable codebase

## 📚 Documentation

Comprehensive documentation organized in `/docs`:

- **Architecture**: System design and technical decisions
- **Guides**: User tutorials and how-to documentation  
- **Deployment**: Production setup and containerization
- **API Reference**: Endpoint documentation and examples

## 🛡️ Security & Best Practices

- **Environment Variables**: All secrets in `.env` (never committed)
- **Container Security**: Non-root user, minimal attack surface
- **API Rate Limiting**: Built-in rate limiting for external APIs
- **Data Validation**: Comprehensive input validation and sanitization
- **Error Handling**: Graceful degradation and error recovery

## 🐛 Troubleshooting

### Common Issues

1. **Container Build Fails**
   ```bash
   # Clean Docker cache and rebuild
   docker system prune -a
   docker-compose build --no-cache
   ```

2. **Import Errors**
   ```bash
   # Verify Python path and dependencies
   python -c "import app.main; print('✅ App imports OK')"
   pip install -r requirements.txt
   ```

3. **Missing API Keys**
   ```bash
   # Check environment configuration
   cat .env | grep API_KEY
   curl http://localhost:8000/health
   ```

4. **Database Issues**
   ```bash
   # Recreate database schema
   python -c "from tools.bets_logger import BetsLogger; BetsLogger().ensure_schema()"
   ```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Add comprehensive tests for new functionality
4. Ensure all tests pass: `python -m pytest tests/ -v`
5. Update documentation as needed
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This tool is for educational and research purposes only. Please ensure compliance with local gambling laws and sportsbook terms of service. The authors are not responsible for any financial losses incurred through the use of this software.