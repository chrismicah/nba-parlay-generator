# 📚 JIRA-020B Usage Guide: Post-Analysis Feedback Loop System

This guide provides comprehensive instructions for running and configuring the post-analysis feedback loop system.

## 🚀 Quick Start

### 1. Run Complete Demo
The easiest way to see the system in action:

```bash
cd /path/to/nba_parlay_project
python -m tools.jira_020b_complete_demo
```

This creates mock data and demonstrates the complete workflow including:
- Weekly performance analysis
- Pattern identification
- Few-shot learning updates
- RoBERTa retraining assessment
- Complete orchestration cycle

## 🔧 Production Setup

### Prerequisites

1. **Database**: Ensure you have a SQLite database with bet data
2. **Python Environment**: Python 3.8+ with required packages
3. **File Permissions**: Write access to data directories

### Required Database Schema

Your database should have a `bets` table with these columns:
```sql
CREATE TABLE bets (
    bet_id INTEGER PRIMARY KEY,
    reasoning TEXT,              -- Parlay reasoning text
    confidence_score REAL,       -- Confidence score (0.0-1.0)
    outcome TEXT,               -- 'won' or 'lost'
    timestamp TEXT              -- ISO format timestamp
);
```

### Directory Structure

Ensure these directories exist:
```
nba_parlay_project/
├── data/
│   ├── parlays.sqlite          # Main database
│   ├── few_shot_parlay_examples.json  # Few-shot examples
│   ├── feedback_reports/       # Analysis reports
│   └── orchestration_logs/     # Cycle logs
└── models/
    └── parlay_confidence_classifier/  # RoBERTa model
```

## 📊 Running Individual Components

### 1. Weekly Performance Analysis

```bash
# Basic analysis (last 7 days)
python tools/post_analysis_feedback_loop.py

# Custom analysis with Python
python -c "
from tools.post_analysis_feedback_loop import PostAnalysisFeedbackLoop

# Initialize analyzer
analyzer = PostAnalysisFeedbackLoop(
    db_path='data/parlays.sqlite',
    min_confidence_samples=10,
    high_confidence_threshold=0.8,
    low_win_rate_threshold=0.4
)

# Run analysis
report = analyzer.run_weekly_analysis(days_back=14)
analyzer.print_report_summary(report)

# Save report
report_path = analyzer.save_report(report)
print(f'Report saved to: {report_path}')
"
```

### 2. RoBERTa Retraining

```bash
# Basic retraining assessment
python tools/automated_roberta_retraining.py

# Custom retraining with Python
python -c "
from tools.automated_roberta_retraining import AutomatedRoBERTaRetrainer, RetrainingConfig

# Configure retraining
config = RetrainingConfig(
    learning_rate=2e-5,
    batch_size=16,
    num_epochs=3,
    min_samples_per_class=50
)

# Initialize retrainer
retrainer = AutomatedRoBERTaRetrainer(
    db_path='data/parlays.sqlite',
    config=config
)

# Run retraining
results = retrainer.run_automated_retraining(days_back=90)

print(f'Retraining Success: {results.success}')
print(f'Final Accuracy: {results.final_accuracy:.3f}')
print(f'Training Time: {results.training_time_minutes:.1f} minutes')
"
```

### 3. Complete Orchestration

```bash
# Basic weekly cycle
python tools/feedback_loop_orchestrator.py

# Custom orchestration with Python
python -c "
from tools.feedback_loop_orchestrator import FeedbackLoopOrchestrator

# Initialize orchestrator
orchestrator = FeedbackLoopOrchestrator(
    db_path='data/parlays.sqlite',
    few_shot_path='data/few_shot_parlay_examples.json',
    orchestration_log_path='data/orchestration_logs'
)

# Run weekly cycle
results = orchestrator.run_weekly_cycle(
    days_back=7,
    force_retraining=False
)

# Print results
orchestrator.print_cycle_summary(results)

# Check history
history = orchestrator.get_orchestration_history(days_back=30)
print(f'Found {len(history)} previous cycles')
"
```

## ⚙️ Configuration Options

### PostAnalysisFeedbackLoop Parameters

```python
PostAnalysisFeedbackLoop(
    db_path="data/parlays.sqlite",           # Database path
    min_confidence_samples=10,               # Min samples for pattern analysis
    high_confidence_threshold=0.8,           # High confidence definition
    low_win_rate_threshold=0.4               # Pattern flagging threshold
)
```

### RetrainingConfig Parameters

```python
RetrainingConfig(
    model_name="roberta-base",               # Base model
    output_dir="models/parlay_confidence_classifier",  # Output directory
    learning_rate=2e-5,                      # Learning rate
    batch_size=16,                           # Training batch size
    num_epochs=3,                            # Training epochs
    max_length=512,                          # Max sequence length
    validation_split=0.2,                    # Validation split
    min_samples_per_class=50                 # Min samples per class
)
```

### FeedbackLoopOrchestrator Parameters

```python
FeedbackLoopOrchestrator(
    db_path="data/parlays.sqlite",           # Database path
    few_shot_path="data/few_shot_parlay_examples.json",  # Few-shot file
    orchestration_log_path="data/orchestration_logs"     # Log directory
)
```

## 🕐 Automated Scheduling

### Cron Job Setup

1. **Edit crontab**:
```bash
crontab -e
```

2. **Add weekly execution** (every Monday at 9 AM):
```bash
0 9 * * 1 cd /path/to/nba_parlay_project && python -m tools.feedback_loop_orchestrator >> /var/log/feedback_loop.log 2>&1
```

3. **Alternative: Daily execution** (every day at 2 AM):
```bash
0 2 * * * cd /path/to/nba_parlay_project && python -m tools.feedback_loop_orchestrator >> /var/log/feedback_loop.log 2>&1
```

### Systemd Service (Linux)

Create `/etc/systemd/system/feedback-loop.service`:
```ini
[Unit]
Description=NBA Parlay Feedback Loop
After=network.target

[Service]
Type=oneshot
User=your_user
WorkingDirectory=/path/to/nba_parlay_project
ExecStart=/usr/bin/python -m tools.feedback_loop_orchestrator
Environment=PYTHONPATH=/path/to/nba_parlay_project

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/feedback-loop.timer`:
```ini
[Unit]
Description=Run feedback loop weekly
Requires=feedback-loop.service

[Timer]
OnCalendar=Mon *-*-* 09:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start:
```bash
sudo systemctl enable feedback-loop.timer
sudo systemctl start feedback-loop.timer
```

## 📋 Monitoring & Logs

### Log Files

The system generates several types of logs:

1. **Feedback Reports**: `data/feedback_reports/weekly_analysis_YYYYMMDD_HHMMSS.json`
2. **Orchestration Logs**: `data/orchestration_logs/orchestration_cycle_YYYYMMDD_HHMMSS.json`
3. **Retraining Logs**: `data/retraining_logs/roberta_retraining_YYYYMMDD_HHMMSS.json`

### Monitoring Script

Create a monitoring script `scripts/monitor_feedback_loop.py`:
```python
#!/usr/bin/env python3
"""Monitor feedback loop system health."""

import json
from pathlib import Path
from datetime import datetime, timedelta

def check_recent_cycles():
    """Check for recent orchestration cycles."""
    log_dir = Path("data/orchestration_logs")
    if not log_dir.exists():
        print("❌ No orchestration logs found")
        return False
    
    # Check for cycles in last 8 days
    cutoff = datetime.now() - timedelta(days=8)
    recent_logs = []
    
    for log_file in log_dir.glob("orchestration_cycle_*.json"):
        try:
            with open(log_file) as f:
                data = json.load(f)
                timestamp = datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))
                if timestamp > cutoff:
                    recent_logs.append((timestamp, data))
        except Exception as e:
            print(f"⚠️  Error reading {log_file}: {e}")
    
    if not recent_logs:
        print("❌ No recent cycles found (last 8 days)")
        return False
    
    # Show most recent cycle
    recent_logs.sort(key=lambda x: x[0], reverse=True)
    latest_timestamp, latest_data = recent_logs[0]
    
    print(f"✅ Latest cycle: {latest_timestamp}")
    print(f"   Analysis completed: {'✅' if latest_data['analysis_completed'] else '❌'}")
    print(f"   Bets analyzed: {latest_data['total_bets_analyzed']}")
    print(f"   Patterns flagged: {latest_data['patterns_flagged']}")
    print(f"   Few-shot updated: {'✅' if latest_data['few_shot_updated'] else '⏸️'}")
    print(f"   Retraining: {'✅' if latest_data['retraining_successful'] else '❌' if latest_data['retraining_triggered'] else '⏸️'}")
    
    return True

if __name__ == "__main__":
    print("🔍 Feedback Loop System Health Check")
    print("=" * 40)
    check_recent_cycles()
```

Run monitoring:
```bash
python scripts/monitor_feedback_loop.py
```

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Error**
```bash
# Check database exists and is accessible
ls -la data/parlays.sqlite
sqlite3 data/parlays.sqlite ".tables"
```

2. **No Bet Data Found**
```bash
# Check database has recent data
sqlite3 data/parlays.sqlite "SELECT COUNT(*) FROM bets WHERE timestamp > datetime('now', '-30 days');"
```

3. **Permission Errors**
```bash
# Fix directory permissions
chmod -R 755 data/
mkdir -p data/feedback_reports data/orchestration_logs data/retraining_logs
```

4. **Import Errors**
```bash
# Check Python path
export PYTHONPATH=/path/to/nba_parlay_project:$PYTHONPATH
python -c "import tools.post_analysis_feedback_loop; print('✅ Import successful')"
```

5. **Transformers Library Missing**
```bash
# Install transformers for RoBERTa retraining
pip install transformers torch datasets scikit-learn
```

### Debug Mode

Run with debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)

from tools.feedback_loop_orchestrator import FeedbackLoopOrchestrator
orchestrator = FeedbackLoopOrchestrator()
results = orchestrator.run_weekly_cycle(days_back=7)
```

### Manual Data Check

Verify your data:
```python
from tools.post_analysis_feedback_loop import PostAnalysisFeedbackLoop

analyzer = PostAnalysisFeedbackLoop()
analyses = analyzer.extract_bet_performance_data(days_back=30)

print(f"Found {len(analyses)} bet analyses")
if analyses:
    print(f"Sample analysis: {analyses[0]}")
    print(f"Date range: {min(a.timestamp for a in analyses)} to {max(a.timestamp for a in analyses)}")
```

## 📊 Output Interpretation

### Feedback Report Structure

```json
{
  "analysis_period": "Last 7 days",
  "total_bets": 25,
  "overall_win_rate": 0.64,
  "confidence_calibration": {
    "high": {
      "win_rate": 0.75,
      "avg_confidence": 0.82,
      "calibration_error": 0.07,
      "well_calibrated": true
    }
  },
  "flagged_patterns": [
    {
      "pattern_id": "failing_public_betting",
      "win_rate": 0.25,
      "sample_count": 4
    }
  ],
  "successful_patterns": [
    {
      "pattern_id": "successful_sharp_money",
      "win_rate": 0.90,
      "sample_count": 10
    }
  ],
  "retraining_recommendation": true,
  "improvement_suggestions": [
    "Public betting patterns show 75% failure rate - consider reducing weight"
  ]
}
```

### Understanding Results

- **Win Rate**: Percentage of bets that won
- **Calibration Error**: Difference between confidence and actual win rate
- **Well Calibrated**: Error < 10%
- **Pattern Sample Count**: Number of bets matching the pattern
- **Quality Score**: Win rate × confidence × reliability

## 🎯 Best Practices

### 1. Data Quality
- Ensure consistent bet outcome labeling ('won'/'lost')
- Maintain detailed reasoning text (>50 characters)
- Regular database cleanup and validation

### 2. Scheduling
- Run weekly cycles on consistent schedule
- Allow sufficient time between cycles for data accumulation
- Monitor system resources during retraining

### 3. Monitoring
- Set up alerts for failed cycles
- Review flagged patterns regularly
- Track long-term performance trends

### 4. Configuration
- Adjust thresholds based on your data volume
- Start with conservative settings and tune over time
- Document any custom configurations

This completes the comprehensive usage guide for the JIRA-020B feedback loop system. The system is designed to be robust and self-maintaining, but regular monitoring ensures optimal performance.
