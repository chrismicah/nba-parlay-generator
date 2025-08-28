#!/usr/bin/env python3
"""
Comprehensive Feedback Loop Demo - ML-FEEDBACK-DEMO-001

Demonstrates the complete ML feedback loop system including:
- API cost tracking and budget management
- Data drift detection using Kolmogorov-Smirnov test
- Automated XGBoost model retraining
- MLflow experiment tracking
- Daily reporting with actionable insights
- Scheduled execution capabilities
"""

import logging
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from ml.ml_feedback_loop import FeedbackLoop, FeedbackConfig
from monitoring.api_cost_tracker import APICostTracker, get_cost_tracker
from scripts.daily_parlay_report import DailyReportGenerator, DailyReportConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def demo_complete_feedback_system():
    """Demonstrate the complete feedback loop system."""
    
    print("🎯 ML Feedback Loop System - Complete Demo")
    print("=" * 60)
    
    # Step 1: Initialize API Cost Tracker
    print("\n💰 Step 1: API Cost Tracking")
    print("-" * 30)
    
    cost_tracker = get_cost_tracker()
    
    # Simulate some API usage
    cost_tracker.log_api_call("the_odds_api", "/odds/nba", True, response_size_kb=25)
    cost_tracker.log_api_call("api_football", "/games", True, response_size_kb=35)
    cost_tracker.log_api_call("xai_grok", "/generate", True, response_size_kb=8)
    
    # Check costs and budget
    todays_costs = cost_tracker.get_todays_costs()
    total_cost = sum(todays_costs.values())
    
    print(f"Today's API costs: ${total_cost:.4f}")
    for service, cost in todays_costs.items():
        print(f"  • {service}: ${cost:.4f}")
    
    # Check if we can afford feedback loop
    estimated_cost = cost_tracker.estimate_feedback_loop_cost(100)
    can_afford, reason = cost_tracker.should_run_feedback_loop(estimated_cost)
    
    print(f"Feedback loop estimated cost: ${estimated_cost:.3f}")
    print(f"Can afford to run: {'✅' if can_afford else '❌'} - {reason}")
    
    # Step 2: Feedback Loop for NBA
    print("\n🏀 Step 2: NBA Feedback Loop")
    print("-" * 30)
    
    nba_config = FeedbackConfig(
        sport="nba",
        outcome_lookback_days=7,
        experiment_name="nba_feedback_demo",
        drift_detection_threshold=0.05
    )
    
    nba_feedback = FeedbackLoop(nba_config)
    nba_results = nba_feedback.run_feedback_cycle()
    
    print(f"NBA Feedback Results:")
    print(f"  • Success: {nba_results.get('success', False)}")
    print(f"  • Drift detected: {nba_results.get('drift_detected', False)}")
    print(f"  • Model retrained: {nba_results.get('retrained', False)}")
    print(f"  • Outcome samples: {nba_results.get('outcome_samples', 0)}")
    
    if nba_results.get('performance_improvement'):
        improvements = nba_results['performance_improvement']
        print(f"  • Performance improvements:")
        for metric, value in improvements.items():
            print(f"    - {metric}: {value:+.3f}")
    
    # Step 3: Feedback Loop for NFL
    print("\n🏈 Step 3: NFL Feedback Loop")
    print("-" * 30)
    
    nfl_config = FeedbackConfig(
        sport="nfl",
        outcome_lookback_days=7,
        experiment_name="nfl_feedback_demo",
        drift_detection_threshold=0.05
    )
    
    nfl_feedback = FeedbackLoop(nfl_config)
    nfl_results = nfl_feedback.run_feedback_cycle()
    
    print(f"NFL Feedback Results:")
    print(f"  • Success: {nfl_results.get('success', False)}")
    print(f"  • Drift detected: {nfl_results.get('drift_detected', False)}")
    print(f"  • Model retrained: {nfl_results.get('retrained', False)}")
    print(f"  • Outcome samples: {nfl_results.get('outcome_samples', 0)}")
    
    # Step 4: Daily Report Generation
    print("\n📊 Step 4: Daily Report Generation")
    print("-" * 30)
    
    report_config = DailyReportConfig()
    report_config.enable_alerts = False  # Disable for demo
    
    report_generator = DailyReportGenerator(report_config)
    daily_report = await report_generator.generate_daily_report()
    
    if daily_report.get('error'):
        print(f"❌ Report generation failed: {daily_report['error']}")
    else:
        print("✅ Daily report generated successfully!")
        
        # Show insights
        insights = daily_report.get('insights_and_alerts', {})
        summary = insights.get('summary', {})
        
        print(f"System Health: {summary.get('overall_health', 'UNKNOWN')}")
        print(f"Alerts: {summary.get('alert_count', 0)}")
        print(f"Positive Trends: {summary.get('positive_trends_count', 0)}")
        
        # Show recommendations
        recommendations = daily_report.get('recommendations', [])
        if recommendations:
            print("\n💡 Top Recommendations:")
            for i, rec in enumerate(recommendations[:2], 1):
                print(f"  {i}. {rec['title']} ({rec['priority']} priority)")
                print(f"     {rec['description']}")
    
    # Step 5: MLflow Experiment Tracking
    print("\n🧪 Step 5: MLflow Experiment Summary")
    print("-" * 30)
    
    try:
        import mlflow
        
        # List recent experiments
        client = mlflow.tracking.MlflowClient()
        experiments = client.search_experiments()
        
        print("Recent MLflow experiments:")
        for exp in experiments[:3]:
            runs = client.search_runs(exp.experiment_id, max_results=1)
            run_count = len(client.search_runs(exp.experiment_id))
            
            print(f"  • {exp.name}: {run_count} runs")
            if runs:
                latest_run = runs[0]
                print(f"    Latest: {latest_run.info.start_time}")
        
    except Exception as e:
        print(f"MLflow tracking info unavailable: {e}")
    
    # Step 6: Show Scheduler Setup
    print("\n⏰ Step 6: Scheduling Setup")
    print("-" * 30)
    
    print("To run automated feedback loops:")
    print("1. Daily drift checks at 6:00 AM:")
    print("   nba_feedback.schedule_jobs()")
    print("   nba_feedback.run_scheduler()")
    print()
    print("2. Weekly forced retraining on Mondays:")
    print("   # Automatically included in schedule_jobs()")
    print()
    print("3. Daily reports with cost monitoring:")
    print("   # Run daily_parlay_report.py as cron job")
    
    # Summary
    print("\n🎯 System Capabilities Summary")
    print("=" * 60)
    
    print("✅ Automated Data Drift Detection")
    print("   • Kolmogorov-Smirnov statistical tests")
    print("   • Configurable drift thresholds")
    print("   • Multi-feature drift analysis")
    
    print("\n✅ Smart Model Retraining")
    print("   • XGBoost classifier with performance tracking")
    print("   • Incremental data updates")
    print("   • Performance improvement validation")
    
    print("\n✅ MLflow Experiment Tracking")
    print("   • Automated metric logging")
    print("   • Model artifact management")
    print("   • A/B testing support")
    
    print("\n✅ API Cost Management")
    print("   • Real-time cost tracking")
    print("   • Budget-aware decision making")
    print("   • Service-specific limits")
    
    print("\n✅ Comprehensive Reporting")
    print("   • Daily performance analytics")
    print("   • Actionable insights and alerts")
    print("   • Automated notification system")
    
    print("\n✅ Production-Ready Scheduling")
    print("   • Daily and weekly automation")
    print("   • Failure handling and recovery")
    print("   • Cost-aware execution")
    
    print("\n🚀 Ready for Production Deployment!")


async def demo_scheduler_setup():
    """Demonstrate scheduler setup (non-blocking)."""
    
    print("\n⏰ Scheduler Demo (5 second preview)")
    print("-" * 40)
    
    nba_config = FeedbackConfig(
        sport="nba",
        daily_schedule_time="23:30",  # Set to near current time for demo
        weekly_schedule_time="23:30"
    )
    
    feedback_loop = FeedbackLoop(nba_config)
    feedback_loop.schedule_jobs()
    
    print("Scheduled jobs created:")
    print("  • Daily NBA drift check")
    print("  • Weekly NBA model retraining")
    
    # Show what the scheduler would do (without actually running)
    import schedule
    
    print("\nScheduled tasks:")
    for job in schedule.jobs:
        print(f"  • {job.job_func.__name__} - Next run: {job.next_run}")
    
    print("\nIn production, call feedback_loop.run_scheduler() to start")


if __name__ == "__main__":
    print("🤖 Starting comprehensive feedback loop demo...")
    
    # Run main demo
    asyncio.run(demo_complete_feedback_system())
    
    # Show scheduler setup
    asyncio.run(demo_scheduler_setup())
    
    print("\n✨ Demo completed! Feedback loop system ready for integration.")
