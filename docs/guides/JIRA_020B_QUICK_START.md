# 🚀 JIRA-020B Quick Start Guide

## TL;DR - How to Run the Feedback Loop System

### 1. **See It in Action (Demo)**
```bash
# Run complete demo with mock data
python -m tools.jira_020b_complete_demo
```

### 2. **Production Weekly Cycle**
```bash
# Run weekly analysis and improvements
python scripts/run_weekly_feedback_cycle.py

# Dry run (see what would happen without making changes)
python scripts/run_weekly_feedback_cycle.py --dry-run

# Force retraining
python scripts/run_weekly_feedback_cycle.py --force-retraining
```

### 3. **Monitor System Health**
```bash
# Check system status
python scripts/monitor_feedback_system.py
```

### 4. **Set Up Automation**
```bash
# Add to crontab for weekly Monday 9 AM runs
crontab -e

# Add this line:
0 9 * * 1 cd /path/to/nba_parlay_project && python scripts/run_weekly_feedback_cycle.py >> /var/log/feedback_loop.log 2>&1
```

## 📋 What Each Command Does

### Demo (`python -m tools.jira_020b_complete_demo`)
- Creates realistic mock bet data
- Runs complete analysis workflow
- Shows pattern detection in action
- Demonstrates few-shot learning updates
- Simulates RoBERTa retraining
- **Perfect for understanding the system**

### Weekly Cycle (`python scripts/run_weekly_feedback_cycle.py`)
- Analyzes real bet performance from your database
- Identifies failing reasoning patterns
- Extracts successful patterns for few-shot learning
- Triggers RoBERTa retraining when needed
- **This is what runs in production**

### System Monitor (`python scripts/monitor_feedback_system.py`)
- Checks database connectivity and data quality
- Verifies recent cycles ran successfully
- Calculates performance trends
- Identifies system issues
- **Use for troubleshooting and health checks**

## 🎯 Expected Outputs

### Successful Weekly Cycle
```
✅ JIRA-020B DEMONSTRATION COMPLETE!
📊 Analysis Results:
   • 25 bets analyzed
   • 1 patterns flagged for review
   • 2 successful patterns identified
   • 3 few-shot candidates generated
   • Retraining triggered

🚀 PRODUCTION READINESS:
   ✅ Weekly analysis automation
   ✅ Pattern-based feedback loops
   ✅ Few-shot learning updates
   ✅ Automated model retraining
   ✅ Complete orchestration system
```

### System Health Check
```
🎯 OVERALL SYSTEM HEALTH
Database Health: ✅ PASS
Recent Cycles: ✅ PASS
Performance Metrics: ✅ PASS
File System: ✅ PASS

Overall Health: 100% (4/4)
🟢 System Status: HEALTHY
```

## 🔧 Common Options

### Weekly Cycle Options
```bash
# Analyze last 14 days instead of 7
python scripts/run_weekly_feedback_cycle.py --days-back 14

# Save logs to file
python scripts/run_weekly_feedback_cycle.py --log-file /var/log/feedback.log

# Debug mode
python scripts/run_weekly_feedback_cycle.py --log-level DEBUG

# Custom database path
python scripts/run_weekly_feedback_cycle.py --db-path /path/to/your/database.sqlite
```

### Individual Components
```bash
# Just run analysis (no changes)
python tools/post_analysis_feedback_loop.py

# Just test retraining system
python tools/automated_roberta_retraining.py

# Just run orchestration
python tools/feedback_loop_orchestrator.py
```

## 📁 File Locations

After running, you'll find:

- **Analysis Reports**: `data/feedback_reports/weekly_analysis_YYYYMMDD_HHMMSS.json`
- **Cycle Logs**: `data/orchestration_logs/orchestration_cycle_YYYYMMDD_HHMMSS.json`
- **Retraining Logs**: `data/retraining_logs/roberta_retraining_YYYYMMDD_HHMMSS.json`
- **Updated Few-Shot**: `data/few_shot_parlay_examples.json`

## ⚠️ Prerequisites

1. **Database**: SQLite database with `bets` table containing:
   - `bet_id` (INTEGER)
   - `reasoning` (TEXT) 
   - `confidence_score` (REAL)
   - `outcome` (TEXT: 'won' or 'lost')
   - `timestamp` (TEXT: ISO format)

2. **Python Packages**: All required packages from `requirements.txt`

3. **Directories**: The system auto-creates needed directories

## 🆘 Troubleshooting

### "No bet data available"
- Check your database has recent data: `sqlite3 data/parlays.sqlite "SELECT COUNT(*) FROM bets;"`
- Verify schema matches expected format

### "Database connection error"
- Ensure database file exists and is readable
- Check file permissions

### "Import errors"
- Run from project root directory
- Ensure Python path includes project: `export PYTHONPATH=/path/to/nba_parlay_project:$PYTHONPATH`

### "Transformers not available"
- Install for RoBERTa retraining: `pip install transformers torch datasets scikit-learn`
- System works without transformers (simulates retraining)

## 🎯 Next Steps

1. **Start with demo**: `python -m tools.jira_020b_complete_demo`
2. **Check your data**: `python scripts/monitor_feedback_system.py`
3. **Run first cycle**: `python scripts/run_weekly_feedback_cycle.py --dry-run`
4. **Set up automation**: Add to crontab for weekly runs
5. **Monitor regularly**: Check logs and system health

The system is designed to be self-maintaining once set up. It will continuously improve your parlay prompts and model calibration based on actual bet outcomes.
