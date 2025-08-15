#!/usr/bin/env python3
"""
Feedback System Monitor - JIRA-020B

Monitors the health and performance of the feedback loop system.
Provides status checks, performance metrics, and alerts.
"""

import sys
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))


class FeedbackSystemMonitor:
    """Monitor for feedback loop system health and performance."""
    
    def __init__(self, 
                 db_path="data/parlays.sqlite",
                 log_path="data/orchestration_logs",
                 reports_path="data/feedback_reports"):
        self.db_path = Path(db_path)
        self.log_path = Path(log_path)
        self.reports_path = Path(reports_path)
    
    def check_database_health(self):
        """Check database connectivity and recent data."""
        print("📊 DATABASE HEALTH CHECK")
        print("-" * 40)
        
        if not self.db_path.exists():
            print("❌ Database file not found")
            return False
        
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Check table exists
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bets'")
            if not cursor.fetchone():
                print("❌ Bets table not found")
                return False
            
            # Check total records
            cursor = conn.execute("SELECT COUNT(*) FROM bets")
            total_bets = cursor.fetchone()[0]
            print(f"📈 Total bets in database: {total_bets}")
            
            # Check recent data (last 30 days)
            cutoff = (datetime.now() - timedelta(days=30)).isoformat()
            cursor = conn.execute("SELECT COUNT(*) FROM bets WHERE timestamp > ?", (cutoff,))
            recent_bets = cursor.fetchone()[0]
            print(f"📅 Recent bets (30 days): {recent_bets}")
            
            # Check outcome distribution
            cursor = conn.execute("SELECT outcome, COUNT(*) FROM bets GROUP BY outcome")
            outcomes = dict(cursor.fetchall())
            print(f"🎯 Outcome distribution: {outcomes}")
            
            # Check confidence score distribution
            cursor = conn.execute("""
                SELECT 
                    CASE 
                        WHEN confidence_score < 0.5 THEN 'Low'
                        WHEN confidence_score < 0.75 THEN 'Medium' 
                        ELSE 'High'
                    END as conf_range,
                    COUNT(*) as count
                FROM bets 
                WHERE confidence_score IS NOT NULL
                GROUP BY conf_range
            """)
            confidence_dist = dict(cursor.fetchall())
            print(f"🎯 Confidence distribution: {confidence_dist}")
            
            conn.close()
            
            if recent_bets < 10:
                print("⚠️  Warning: Limited recent data for analysis")
                return False
            
            print("✅ Database health: GOOD")
            return True
            
        except Exception as e:
            print(f"❌ Database error: {e}")
            return False
    
    def check_recent_cycles(self):
        """Check for recent orchestration cycles."""
        print("\n🔄 RECENT CYCLES CHECK")
        print("-" * 40)
        
        if not self.log_path.exists():
            print("❌ Orchestration logs directory not found")
            return False
        
        # Find recent cycle logs
        cutoff = datetime.now() - timedelta(days=14)  # Last 2 weeks
        recent_cycles = []
        
        for log_file in self.log_path.glob("orchestration_cycle_*.json"):
            try:
                with open(log_file) as f:
                    data = json.load(f)
                    timestamp = datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))
                    if timestamp > cutoff:
                        recent_cycles.append((timestamp, data))
            except Exception as e:
                print(f"⚠️  Error reading {log_file}: {e}")
        
        if not recent_cycles:
            print("❌ No recent cycles found (last 14 days)")
            return False
        
        # Sort by timestamp (newest first)
        recent_cycles.sort(key=lambda x: x[0], reverse=True)
        
        print(f"📊 Found {len(recent_cycles)} recent cycles")
        
        # Show details for most recent cycles
        for i, (timestamp, data) in enumerate(recent_cycles[:3]):
            print(f"\n{i+1}. Cycle: {data['cycle_id']}")
            print(f"   Timestamp: {timestamp}")
            print(f"   Analysis: {'✅' if data['analysis_completed'] else '❌'}")
            print(f"   Bets Analyzed: {data['total_bets_analyzed']}")
            print(f"   Patterns Flagged: {data['patterns_flagged']}")
            print(f"   Successful Patterns: {data['patterns_successful']}")
            print(f"   Few-Shot Updated: {'✅' if data['few_shot_updated'] else '⏸️'}")
            print(f"   Retraining: {'✅' if data['retraining_successful'] else '❌' if data['retraining_triggered'] else '⏸️'}")
        
        # Check for failures
        failed_cycles = [c for _, c in recent_cycles if not c['analysis_completed']]
        if failed_cycles:
            print(f"\n⚠️  Warning: {len(failed_cycles)} failed cycles detected")
        
        print("✅ Recent cycles: GOOD")
        return True
    
    def check_system_performance(self):
        """Check system performance metrics."""
        print("\n📈 PERFORMANCE METRICS")
        print("-" * 40)
        
        if not self.reports_path.exists():
            print("❌ Feedback reports directory not found")
            return False
        
        # Find recent reports
        cutoff = datetime.now() - timedelta(days=30)
        recent_reports = []
        
        for report_file in self.reports_path.glob("weekly_analysis_*.json"):
            try:
                with open(report_file) as f:
                    data = json.load(f)
                    timestamp = datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))
                    if timestamp > cutoff:
                        recent_reports.append((timestamp, data))
            except Exception as e:
                print(f"⚠️  Error reading {report_file}: {e}")
        
        if not recent_reports:
            print("❌ No recent reports found")
            return False
        
        # Sort by timestamp
        recent_reports.sort(key=lambda x: x[0])
        
        # Calculate performance trends
        win_rates = []
        bet_counts = []
        pattern_counts = []
        
        for timestamp, data in recent_reports:
            if data['total_bets'] > 0:
                win_rates.append(data['overall_win_rate'])
                bet_counts.append(data['total_bets'])
                pattern_counts.append(len(data['flagged_patterns']) + len(data['successful_patterns']))
        
        if win_rates:
            avg_win_rate = sum(win_rates) / len(win_rates)
            avg_bet_count = sum(bet_counts) / len(bet_counts)
            avg_pattern_count = sum(pattern_counts) / len(pattern_counts)
            
            print(f"📊 Average Win Rate: {avg_win_rate:.1%}")
            print(f"📊 Average Bets per Analysis: {avg_bet_count:.1f}")
            print(f"📊 Average Patterns per Analysis: {avg_pattern_count:.1f}")
            
            # Check trends
            if len(win_rates) >= 2:
                recent_trend = win_rates[-1] - win_rates[0]
                trend_indicator = "📈" if recent_trend > 0.05 else "📉" if recent_trend < -0.05 else "➡️"
                print(f"{trend_indicator} Win Rate Trend: {recent_trend:+.1%}")
        
        print("✅ Performance metrics: CALCULATED")
        return True
    
    def check_file_system(self):
        """Check file system health and disk space."""
        print("\n💾 FILE SYSTEM CHECK")
        print("-" * 40)
        
        # Check required directories
        required_dirs = [
            "data",
            "data/feedback_reports",
            "data/orchestration_logs",
            "models",
            "models/parlay_confidence_classifier"
        ]
        
        for dir_path in required_dirs:
            path = Path(dir_path)
            if path.exists():
                print(f"✅ {dir_path}: EXISTS")
            else:
                print(f"❌ {dir_path}: MISSING")
                # Create directory
                try:
                    path.mkdir(parents=True, exist_ok=True)
                    print(f"   Created directory: {dir_path}")
                except Exception as e:
                    print(f"   Failed to create: {e}")
        
        # Check few-shot examples file
        few_shot_path = Path("data/few_shot_parlay_examples.json")
        if few_shot_path.exists():
            try:
                with open(few_shot_path) as f:
                    data = json.load(f)
                    example_count = len(data.get("examples", []))
                    print(f"📚 Few-shot examples: {example_count}")
            except Exception as e:
                print(f"⚠️  Few-shot file error: {e}")
        else:
            print("⚠️  Few-shot examples file not found")
        
        # Check disk space (approximate)
        try:
            import shutil
            total, used, free = shutil.disk_usage(".")
            free_gb = free // (1024**3)
            print(f"💾 Free disk space: {free_gb} GB")
            
            if free_gb < 1:
                print("⚠️  Warning: Low disk space")
        except Exception:
            print("⚠️  Could not check disk space")
        
        return True
    
    def generate_health_report(self):
        """Generate comprehensive health report."""
        print("🏥 FEEDBACK SYSTEM HEALTH REPORT")
        print("=" * 50)
        print(f"Generated: {datetime.now().isoformat()}")
        print()
        
        checks = [
            ("Database Health", self.check_database_health),
            ("Recent Cycles", self.check_recent_cycles),
            ("Performance Metrics", self.check_system_performance),
            ("File System", self.check_file_system)
        ]
        
        results = {}
        for check_name, check_func in checks:
            try:
                results[check_name] = check_func()
            except Exception as e:
                print(f"❌ {check_name} check failed: {e}")
                results[check_name] = False
        
        # Overall health summary
        print("\n🎯 OVERALL SYSTEM HEALTH")
        print("=" * 50)
        
        passed_checks = sum(results.values())
        total_checks = len(results)
        health_percentage = (passed_checks / total_checks) * 100
        
        for check_name, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{check_name}: {status}")
        
        print(f"\nOverall Health: {health_percentage:.0f}% ({passed_checks}/{total_checks})")
        
        if health_percentage >= 75:
            print("🟢 System Status: HEALTHY")
        elif health_percentage >= 50:
            print("🟡 System Status: WARNING")
        else:
            print("🔴 System Status: CRITICAL")
        
        return results


def main():
    """Main function for system monitoring."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor feedback system health")
    parser.add_argument("--db-path", default="data/parlays.sqlite",
                       help="Path to database file")
    parser.add_argument("--log-path", default="data/orchestration_logs",
                       help="Path to orchestration logs")
    parser.add_argument("--reports-path", default="data/feedback_reports",
                       help="Path to feedback reports")
    
    args = parser.parse_args()
    
    monitor = FeedbackSystemMonitor(
        db_path=args.db_path,
        log_path=args.log_path,
        reports_path=args.reports_path
    )
    
    results = monitor.generate_health_report()
    
    # Exit with error code if critical issues found
    passed_checks = sum(results.values())
    total_checks = len(results)
    
    if passed_checks < total_checks * 0.5:  # Less than 50% passed
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
