# NBA Parlay Project - How to Run Guide

## 🚀 **Quick Start Guide**

This guide shows you how to run your NBA Parlay Project with SQLite database logging and performance tracking.

---

## 📋 **Prerequisites**

1. **Python 3.11+** installed
2. **Required packages** installed:
   ```bash
   pip install -r requirements.txt
   ```
3. **Environment variables** set in `.env` file:
   ```bash
   THE_ODDS_API_KEY=your_odds_api_key
   BALLDONTLIE_API_KEY=your_balldontlie_key
   APIFY_TOKEN=your_apify_token
   ```

---

## 🗄️ **Database Setup**

Your production SQLite database is ready at `data/parlays.sqlite`. No additional setup needed!

**Check database status:**
```bash
sqlite3 data/parlays.sqlite "SELECT COUNT(*) FROM bets;"
```

---

## 🏀 **Core Workflows**

### **1. Generate and Validate Parlays**

**Build validated parlays using ParlayBuilder (JIRA-021):**
```bash
# Run the complete parlay workflow
python3 examples/parlay_builder_integration.py
```

**What this does:**
- Fetches current NBA odds from The Odds API
- Generates potential valuable parlay legs
- Validates legs against live market availability
- Builds viable parlays with current odds

### **2. Log Parlay Bets to Database**

**Manual logging example:**
```python
from tools.bets_logger import BetsLogger

with BetsLogger("data/parlays.sqlite") as logger:
    bet_id = logger.log_parlay_leg(
        parlay_id="parlay_20250815_001",
        game_id="nba_lal_vs_bos_20250815",
        leg_description="Lakers ML @ 1.85 [Book: DraftKings]",
        odds=1.85,
        stake=100.0,
        predicted_outcome="Lakers win"
    )
    print(f"Logged bet_id: {bet_id}")
```

**Bulk logging example:**
```python
legs = [
    {'leg_description': 'Lakers ML @ 1.85', 'odds': 1.85, 'stake': 50.0, 'predicted_outcome': 'Lakers win'},
    {'leg_description': 'Celtics -5.5 @ 1.91', 'odds': 1.91, 'stake': 50.0, 'predicted_outcome': 'Celtics cover'},
    {'leg_description': 'Over 220.5 @ 1.95', 'odds': 1.95, 'stake': 50.0, 'predicted_outcome': 'Total over'}
]

with BetsLogger("data/parlays.sqlite") as logger:
    bet_ids = logger.log_parlay("parlay_001", "game_123", legs)
    print(f"Logged {len(bet_ids)} legs")
```

### **3. Settle Bets with Game Results**

**From JSON results file:**
```bash
python3 scripts/update_bet_results.py \
    --db data/parlays.sqlite \
    --results-json game_results.json
```

**From CSV results file:**
```bash
python3 scripts/update_bet_results.py \
    --db data/parlays.sqlite \
    --results-csv results.csv
```

**Manual settlement:**
```python
with BetsLogger("data/parlays.sqlite") as logger:
    logger.update_bet_outcome(
        bet_id=1,
        actual_outcome="Lakers won 112-108",
        is_win=True
    )
```

### **4. Generate Performance Reports**

**Daily performance report:**
```bash
python3 scripts/performance_reporter.py \
    --db data/parlays.sqlite \
    --group-by day \
    --detailed
```

**Performance by bet type:**
```bash
python3 scripts/performance_reporter.py \
    --db data/parlays.sqlite \
    --group-by bet_type \
    --detailed
```

**Export reports:**
```bash
# Export to CSV
python3 scripts/performance_reporter.py \
    --db data/parlays.sqlite \
    --export-csv performance_report.csv

# Export to JSON
python3 scripts/performance_reporter.py \
    --db data/parlays.sqlite \
    --export-json performance_report.json
```

**Time-filtered reports:**
```bash
# Last 7 days
python3 scripts/performance_reporter.py \
    --db data/parlays.sqlite \
    --since "2025-08-08" \
    --detailed

# Specific date range
python3 scripts/performance_reporter.py \
    --db data/parlays.sqlite \
    --since "2025-08-01" \
    --until "2025-08-15" \
    --group-by day
```

---

## 🧪 **Testing and Examples**

### **Run Complete Workflow Demo**
```bash
# Complete SQLite workflow demonstration
python3 examples/sqlite_parlay_workflow.py
```

**What this demo shows:**
- Logging parlay legs to SQLite
- Settling bets with outcomes
- Calculating CLV (Closing Line Value)
- Generating performance reports
- Advanced database queries

### **Run Integration Tests**
```bash
# Test the complete SQLite system
python3 -m pytest tests/test_sqlite_integration.py -v

# Test ParlayBuilder functionality
python3 -m pytest tests/test_parlay_builder.py -v
```

### **Test Individual Components**

**Test ParlayBuilder with live odds:**
```bash
PYTHONPATH=/Users/chris.s/Projects/nba_parlay_project python3 tools/parlay_builder.py
```

**Test odds fetching:**
```bash
python3 -c "
from tools.odds_fetcher_tool import OddsFetcherTool
fetcher = OddsFetcherTool()
games = fetcher.get_game_odds('basketball_nba')
print(f'Found {len(games)} games with odds')
"
```

---

## 📊 **Monitoring and Analytics**

### **Check Database Status**
```bash
# Count total bets
sqlite3 data/parlays.sqlite "SELECT COUNT(*) as total_bets FROM bets;"

# Count open bets
sqlite3 data/parlays.sqlite "SELECT COUNT(*) as open_bets FROM bets WHERE is_win IS NULL;"

# Recent bets
sqlite3 data/parlays.sqlite "
SELECT bet_id, parlay_id, leg_description, odds, stake, is_win, created_at 
FROM bets 
ORDER BY created_at DESC 
LIMIT 5;
"
```

### **Advanced Analytics Queries**
```bash
# ROI by bookmaker
sqlite3 data/parlays.sqlite "
SELECT 
    CASE 
        WHEN leg_description LIKE '%DraftKings%' THEN 'DraftKings'
        WHEN leg_description LIKE '%FanDuel%' THEN 'FanDuel'
        WHEN leg_description LIKE '%BetMGM%' THEN 'BetMGM'
        ELSE 'Other'
    END as bookmaker,
    COUNT(*) as total_bets,
    AVG(CASE WHEN is_win = 1 THEN 100.0 ELSE 0.0 END) as win_rate,
    SUM(stake) as total_stake,
    SUM(CASE WHEN is_win = 1 THEN stake * odds ELSE 0 END) - SUM(stake) as profit
FROM bets 
WHERE is_win IS NOT NULL
GROUP BY bookmaker
ORDER BY profit DESC;
"

# CLV analysis
sqlite3 data/parlays.sqlite "
SELECT 
    COUNT(*) as bets_with_clv,
    AVG(clv_percentage) as avg_clv,
    MIN(clv_percentage) as min_clv,
    MAX(clv_percentage) as max_clv
FROM bets 
WHERE clv_percentage IS NOT NULL;
"
```

---

## 🔧 **Configuration Options**

### **Database Paths**
- **Production**: `data/parlays.sqlite`
- **Demo/Testing**: `data/demo_parlays.sqlite`

### **Performance Reporter Options**
```bash
--group-by {bet_type,day,bookmaker,game_id}  # Grouping method
--since YYYY-MM-DD                          # Start date filter
--until YYYY-MM-DD                          # End date filter
--detailed                                  # Show per-group breakdown
--export-csv file.csv                       # Export to CSV
--export-json file.json                     # Export to JSON
--include-open                              # Include open bets in counts
--top-n 10                                  # Number of top/bottom legs to show
```

### **BetsLogger Configuration**
```python
# Custom database path
logger = BetsLogger("custom/path/bets.sqlite")

# Context manager (recommended)
with BetsLogger("data/parlays.sqlite") as logger:
    # Your operations here
    pass
```

---

## 🚨 **Troubleshooting**

### **Common Issues**

**1. "No module named 'tools'" Error**
```bash
# Set Python path
export PYTHONPATH=/Users/chris.s/Projects/nba_parlay_project
python3 your_script.py

# Or run from project root
cd /Users/chris.s/Projects/nba_parlay_project
python3 your_script.py
```

**2. "API key not found" Error**
```bash
# Check environment variables
echo $THE_ODDS_API_KEY
echo $BALLDONTLIE_API_KEY

# Or check .env file
cat .env
```

**3. "Database locked" Error**
```bash
# Check for active connections
lsof data/parlays.sqlite

# Or restart and try again
```

**4. "No games available" (Off-season)**
This is expected during NBA off-season (July-September). The system will work normally during active season (October-June).

### **Logs and Debugging**
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Your code here - will show detailed logs
```

---

## 📁 **File Structure**

```
nba_parlay_project/
├── data/
│   ├── parlays.sqlite          # Production database
│   └── demo_parlays.sqlite     # Demo database
├── tools/
│   ├── bets_logger.py          # SQLite logging system
│   ├── parlay_builder.py       # Parlay validation (JIRA-021)
│   └── odds_fetcher_tool.py    # Live odds fetching
├── scripts/
│   ├── performance_reporter.py # Performance analytics (JIRA-017)
│   └── update_bet_results.py   # Bet settlement
├── examples/
│   ├── sqlite_parlay_workflow.py      # Complete demo
│   └── parlay_builder_integration.py  # ParlayBuilder demo
├── tests/
│   ├── test_sqlite_integration.py     # SQLite tests
│   └── test_parlay_builder.py         # ParlayBuilder tests
└── documentation/
    └── HOW_TO_RUN.md          # This guide
```

---

## 🎯 **Next Steps**

1. **Start with demos**: Run `python3 examples/sqlite_parlay_workflow.py`
2. **Test with live data**: Run `python3 examples/parlay_builder_integration.py`
3. **Log your first real parlay**: Use the BetsLogger examples above
4. **Set up daily reporting**: Schedule performance reports
5. **Monitor your ROI**: Track performance over time

---

## 📞 **Support**

- **Run tests**: `python3 -m pytest tests/ -v`
- **Check logs**: Enable debug logging for detailed output
- **Database inspection**: Use `sqlite3 data/parlays.sqlite` for direct queries

Your NBA Parlay Project is ready to track real betting performance with enterprise-grade SQLite storage! 🚀
