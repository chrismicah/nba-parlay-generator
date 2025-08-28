# NBA Parlay Project - Quick Start

## 🚀 **Get Started in 5 Minutes**

### **1. Run the Complete Demo**
```bash
cd /Users/chris.s/Projects/nba_parlay_project
python3 examples/sqlite_parlay_workflow.py
```

**What you'll see:**
- ✅ 5 parlay legs logged to SQLite
- ✅ Bets settled with outcomes
- ✅ CLV calculations
- ✅ Performance report (66% ROI, 80% hit rate)

### **2. Test Live Parlay Building**
```bash
python3 examples/parlay_builder_integration.py
```

**What this does:**
- 📡 Fetches live NBA odds (44+ games)
- 🧠 Generates valuable parlay legs
- ✅ Validates against current markets
- 🏆 Builds viable parlays

### **3. Generate Your First Report**
```bash
python3 scripts/performance_reporter.py --db data/demo_parlays.sqlite --detailed
```

**Sample output:**
```
OVERALL METRICS
Total bets: 5
ROI: 66.25%
Hit rate: 80.00%

PER-GROUP BREAKDOWN
Spreads: 100% hit rate, 90% ROI
H2H: 100% hit rate, 85% ROI  
Totals: 50% hit rate, 30% ROI
```

---

## 🎯 **Ready for Production?**

### **Log Your First Real Parlay**
```python
from tools.bets_logger import BetsLogger

with BetsLogger("data/parlays.sqlite") as logger:
    bet_id = logger.log_parlay_leg(
        parlay_id="my_first_parlay",
        game_id="nba_lal_vs_bos_20250815",
        leg_description="Lakers ML @ 1.85 [Book: DraftKings]",
        odds=1.85,
        stake=100.0,
        predicted_outcome="Lakers win"
    )
    print(f"✅ Logged bet_id: {bet_id}")
```

### **Settle When Game Ends**
```python
with BetsLogger("data/parlays.sqlite") as logger:
    logger.update_bet_outcome(
        bet_id=bet_id,
        actual_outcome="Lakers won 112-108",
        is_win=True
    )
```

### **Track Your Performance**
```bash
python3 scripts/performance_reporter.py --db data/parlays.sqlite --detailed
```

---

## 📊 **Key Features**

- ✅ **SQLite Database**: Persistent, queryable storage
- ✅ **Live Odds Integration**: Real-time market validation
- ✅ **Performance Analytics**: ROI, hit rates, CLV tracking
- ✅ **Automated Settlement**: Bulk bet result processing
- ✅ **Comprehensive Reporting**: Daily/weekly summaries

---

## 🔗 **Full Documentation**

See [`documentation/HOW_TO_RUN.md`](HOW_TO_RUN.md) for complete usage guide.

**You're ready to start tracking your NBA parlay performance!** 🏀
