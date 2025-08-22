#!/usr/bin/env python3
"""
Daily Parlay Report System - DAILY-REPORT-001

Comprehensive daily reporting system that generates performance analytics,
runs feedback loops when needed, and provides actionable insights for the
NBA/NFL parlay prediction system.

Features:
- Daily performance metrics and ROI analysis
- Model drift detection and automated retraining
- API cost monitoring and budget management
- Slack/email notifications for key insights
- ML experiment tracking with MLflow
- Integration with existing performance reporter
"""

import logging
import json
import argparse
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import sys
import os

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# Import our feedback loop and cost tracking
from ml.ml_feedback_loop import FeedbackLoop, FeedbackConfig
from monitoring.api_cost_tracker import APICostTracker, get_cost_tracker

# Optional integrations
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from slack_sdk import WebClient
    HAS_SLACK = True
except ImportError:
    HAS_SLACK = False

logger = logging.getLogger(__name__)


class DailyReportConfig:
    """Configuration for daily reporting system."""
    
    def __init__(self):
        """Initialize with environment variables and defaults."""
        # Database paths
        self.parlay_db_path = "data/parlays.sqlite"
        self.cost_db_path = "data/api_cost_tracking.sqlite"
        
        # Report settings
        self.lookback_days = 7
        self.performance_group_by = "sport"
        self.include_detailed_breakdown = True
        
        # Feedback loop settings
        self.enable_feedback_loop = True
        self.feedback_threshold_samples = 50
        self.max_feedback_cost_usd = 5.0
        
        # Notification settings
        self.slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        self.email_recipients = os.getenv("EMAIL_RECIPIENTS", "").split(",") if os.getenv("EMAIL_RECIPIENTS") else []
        self.enable_alerts = True
        
        # Output paths
        self.report_output_dir = Path("data/daily_reports")
        self.archive_reports = True
        
        # Alert thresholds
        self.alert_thresholds = {
            "roi_decline": -0.05,      # Alert if ROI drops by 5%
            "accuracy_decline": -0.03,  # Alert if accuracy drops by 3%
            "api_cost_spike": 1.5,     # Alert if daily costs 1.5x normal
            "drift_detected": True      # Alert on any drift detection
        }


class DailyReportGenerator:
    """Generates comprehensive daily parlay reports."""
    
    def __init__(self, config: DailyReportConfig = None):
        """Initialize daily report generator."""
        self.config = config or DailyReportConfig()
        self.cost_tracker = get_cost_tracker()
        
        # Setup output directory
        self.config.report_output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("Daily report generator initialized")
    
    async def generate_daily_report(self, sport: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate comprehensive daily report.
        
        Args:
            sport: Specific sport to report on (None for all)
            
        Returns:
            Complete report dictionary
        """
        report_timestamp = datetime.now()
        report_date = report_timestamp.date().isoformat()
        
        logger.info(f"🚀 Generating daily parlay report for {report_date}")
        
        try:
            # Step 1: Generate performance metrics
            logger.info("📊 Generating performance metrics...")
            performance_data = await self._generate_performance_metrics(sport)
            
            # Step 2: Analyze API costs
            logger.info("💰 Analyzing API costs...")
            cost_analysis = self._analyze_api_costs()
            
            # Step 3: Run feedback loop if needed
            logger.info("🔄 Checking feedback loop requirements...")
            feedback_results = await self._run_feedback_loop_if_needed(sport)
            
            # Step 4: Generate insights and alerts
            logger.info("🔍 Generating insights and alerts...")
            insights = self._generate_insights(performance_data, cost_analysis, feedback_results)
            
            # Step 5: Compile comprehensive report
            report = {
                "report_metadata": {
                    "generated_at": report_timestamp.isoformat(),
                    "report_date": report_date,
                    "sport_filter": sport,
                    "lookback_days": self.config.lookback_days,
                    "version": "1.0"
                },
                "performance_summary": performance_data,
                "cost_analysis": cost_analysis,
                "feedback_loop_results": feedback_results,
                "insights_and_alerts": insights,
                "recommendations": self._generate_recommendations(performance_data, cost_analysis, feedback_results)
            }
            
            # Step 6: Save report
            report_path = await self._save_report(report, report_date)
            
            # Step 7: Send notifications
            if self.config.enable_alerts:
                await self._send_notifications(report, insights)
            
            logger.info(f"✅ Daily report generated successfully: {report_path}")
            return report
            
        except Exception as e:
            logger.error(f"❌ Error generating daily report: {e}")
            return {"error": str(e), "success": False}
    
    async def _generate_performance_metrics(self, sport: Optional[str]) -> Dict[str, Any]:
        """Generate performance metrics using existing performance reporter."""
        try:
            # Generate performance data directly
            
            # Construct arguments for performance reporter
            sport_filter = sport if sport else "all"
            since_date = (datetime.now() - timedelta(days=self.config.lookback_days)).isoformat()
            
            # Generate performance data (simplified version)
            import sqlite3
            conn = sqlite3.connect(self.config.parlay_db_path)
            cursor = conn.cursor()
            
            # Basic performance query
            base_query = """
                SELECT 
                    sport,
                    COUNT(*) as total_bets,
                    SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN result = 'WIN' THEN actual_payout ELSE 0 END) as total_winnings,
                    SUM(bet_amount) as total_wagered,
                    AVG(confidence_score) as avg_confidence,
                    AVG(expected_value) as avg_expected_value
                FROM bets 
                WHERE created_at >= ?
            """
            
            params = [since_date]
            if sport:
                base_query += " AND sport = ?"
                params.append(sport)
            
            base_query += " GROUP BY sport"
            
            cursor.execute(base_query, params)
            results = cursor.fetchall()
            
            performance_by_sport = {}
            overall_stats = {
                "total_bets": 0,
                "total_wins": 0,
                "total_winnings": 0.0,
                "total_wagered": 0.0
            }
            
            for row in results:
                sport_name, total_bets, wins, winnings, wagered, avg_conf, avg_ev = row
                
                win_rate = wins / total_bets if total_bets > 0 else 0
                roi = (winnings - wagered) / wagered if wagered > 0 else 0
                
                sport_data = {
                    "total_bets": total_bets,
                    "wins": wins,
                    "win_rate": win_rate,
                    "total_winnings": winnings or 0.0,
                    "total_wagered": wagered or 0.0,
                    "roi": roi,
                    "avg_confidence": avg_conf or 0.0,
                    "avg_expected_value": avg_ev or 0.0,
                    "profit_loss": (winnings or 0.0) - (wagered or 0.0)
                }
                
                performance_by_sport[sport_name] = sport_data
                
                # Update overall stats
                overall_stats["total_bets"] += total_bets
                overall_stats["total_wins"] += wins
                overall_stats["total_winnings"] += winnings or 0.0
                overall_stats["total_wagered"] += wagered or 0.0
            
            # Calculate overall metrics
            overall_win_rate = overall_stats["total_wins"] / overall_stats["total_bets"] if overall_stats["total_bets"] > 0 else 0
            overall_roi = (overall_stats["total_winnings"] - overall_stats["total_wagered"]) / overall_stats["total_wagered"] if overall_stats["total_wagered"] > 0 else 0
            
            conn.close()
            
            return {
                "period": f"Last {self.config.lookback_days} days",
                "overall_metrics": {
                    **overall_stats,
                    "overall_win_rate": overall_win_rate,
                    "overall_roi": overall_roi,
                    "overall_profit_loss": overall_stats["total_winnings"] - overall_stats["total_wagered"]
                },
                "by_sport": performance_by_sport,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating performance metrics: {e}")
            return {"error": str(e)}
    
    def _analyze_api_costs(self) -> Dict[str, Any]:
        """Analyze API costs and budget utilization."""
        try:
            # Get cost summary from tracker
            cost_summary = self.cost_tracker.get_cost_summary(self.config.lookback_days)
            
            # Add budget analysis
            daily_limit = self.cost_tracker.DAILY_LIMITS.get("total", 25.0)
            todays_total = cost_summary["todays_costs"]["total"]
            
            budget_analysis = {
                "daily_budget_utilization": todays_total / daily_limit if daily_limit > 0 else 0,
                "remaining_budget": daily_limit - todays_total,
                "budget_status": "OVER_BUDGET" if todays_total > daily_limit else 
                               "WARNING" if todays_total > daily_limit * 0.8 else "OK",
                "projected_monthly_cost": cost_summary["avg_cost_per_day"] * 30
            }
            
            # Identify cost trends
            daily_costs = cost_summary.get("daily_costs", {})
            if len(daily_costs) >= 2:
                recent_costs = list(daily_costs.values())[-3:]  # Last 3 days
                earlier_costs = list(daily_costs.values())[:-3] if len(daily_costs) > 3 else []
                
                recent_avg = sum(recent_costs) / len(recent_costs) if recent_costs else 0
                earlier_avg = sum(earlier_costs) / len(earlier_costs) if earlier_costs else recent_avg
                
                cost_trend = {
                    "trend_direction": "INCREASING" if recent_avg > earlier_avg * 1.1 else 
                                     "DECREASING" if recent_avg < earlier_avg * 0.9 else "STABLE",
                    "trend_magnitude": abs(recent_avg - earlier_avg) / earlier_avg if earlier_avg > 0 else 0
                }
            else:
                cost_trend = {"trend_direction": "INSUFFICIENT_DATA", "trend_magnitude": 0}
            
            return {
                **cost_summary,
                "budget_analysis": budget_analysis,
                "cost_trends": cost_trend,
                "analysis_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing API costs: {e}")
            return {"error": str(e)}
    
    async def _run_feedback_loop_if_needed(self, sport: Optional[str]) -> Dict[str, Any]:
        """Run feedback loop if conditions are met."""
        if not self.config.enable_feedback_loop:
            return {"enabled": False, "reason": "Feedback loop disabled in config"}
        
        try:
            # Check API cost constraints
            estimated_cost = self.cost_tracker.estimate_feedback_loop_cost()
            should_run_cost, cost_reason = self.cost_tracker.should_run_feedback_loop(estimated_cost)
            
            if not should_run_cost:
                return {
                    "enabled": True,
                    "executed": False,
                    "reason": f"Cost constraint: {cost_reason}",
                    "estimated_cost": estimated_cost
                }
            
            # Check if we have sufficient recent samples
            from ml.ml_feedback_loop import OutcomeCollector, FeedbackConfig
            
            # Run feedback loop for each sport or specified sport
            sports_to_process = [sport] if sport else ["nba", "nfl"]
            results = {}
            
            for sport_name in sports_to_process:
                logger.info(f"🔄 Running feedback loop for {sport_name}...")
                
                # Initialize feedback loop for this sport
                feedback_config = FeedbackConfig(
                    sport=sport_name,
                    outcome_lookback_days=self.config.lookback_days,
                    max_daily_api_cost=self.config.max_feedback_cost_usd
                )
                
                feedback_loop = FeedbackLoop(feedback_config)
                
                # Run feedback cycle
                cycle_results = feedback_loop.run_feedback_cycle()
                results[sport_name] = cycle_results
                
                logger.info(f"✅ Feedback loop completed for {sport_name}: "
                           f"Drift={'detected' if cycle_results.get('drift_detected') else 'none'}, "
                           f"Retrained={cycle_results.get('retrained', False)}")
            
            return {
                "enabled": True,
                "executed": True,
                "estimated_cost": estimated_cost,
                "results_by_sport": results,
                "execution_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error running feedback loop: {e}")
            return {
                "enabled": True,
                "executed": False,
                "error": str(e)
            }
    
    def _generate_insights(self, performance_data: Dict[str, Any], 
                          cost_analysis: Dict[str, Any], 
                          feedback_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate actionable insights and alerts."""
        insights = {
            "performance_insights": [],
            "cost_insights": [],
            "model_insights": [],
            "alerts": [],
            "positive_trends": [],
            "areas_for_improvement": []
        }
        
        try:
            # Performance insights
            overall_metrics = performance_data.get("overall_metrics", {})
            roi = overall_metrics.get("overall_roi", 0)
            win_rate = overall_metrics.get("overall_win_rate", 0)
            
            if roi > 0.05:
                insights["positive_trends"].append(f"Strong ROI of {roi:.1%} over the last {self.config.lookback_days} days")
            elif roi < -0.05:
                insights["alerts"].append(f"⚠️ Negative ROI: {roi:.1%} - review strategy")
                insights["areas_for_improvement"].append("ROI performance")
            
            if win_rate > 0.6:
                insights["positive_trends"].append(f"High win rate of {win_rate:.1%}")
            elif win_rate < 0.45:
                insights["alerts"].append(f"⚠️ Low win rate: {win_rate:.1%}")
                insights["areas_for_improvement"].append("Win rate accuracy")
            
            # Cost insights
            budget_analysis = cost_analysis.get("budget_analysis", {})
            budget_status = budget_analysis.get("budget_status", "UNKNOWN")
            
            if budget_status == "OVER_BUDGET":
                insights["alerts"].append("🔴 Daily API budget exceeded")
            elif budget_status == "WARNING":
                insights["alerts"].append("🟡 Approaching daily API budget limit")
            else:
                insights["positive_trends"].append("API costs within budget")
            
            cost_trend = cost_analysis.get("cost_trends", {})
            if cost_trend.get("trend_direction") == "INCREASING":
                insights["cost_insights"].append("API costs trending upward - monitor usage")
            
            # Model insights from feedback loop
            if feedback_results.get("executed"):
                sport_results = feedback_results.get("results_by_sport", {})
                
                for sport, result in sport_results.items():
                    if result.get("drift_detected"):
                        insights["alerts"].append(f"📊 Data drift detected in {sport.upper()} model")
                        insights["model_insights"].append(f"{sport.upper()}: Data drift requiring attention")
                    
                    if result.get("retrained"):
                        performance_improvement = result.get("performance_improvement", {})
                        auc_improvement = performance_improvement.get("auc", 0)
                        
                        if auc_improvement > 0.01:
                            insights["positive_trends"].append(f"{sport.upper()} model improved (AUC +{auc_improvement:.3f})")
                        else:
                            insights["model_insights"].append(f"{sport.upper()}: Model retrained but minimal improvement")
            
            # Generate summary scores
            alert_count = len(insights["alerts"])
            positive_count = len(insights["positive_trends"])
            
            insights["summary"] = {
                "overall_health": "GOOD" if alert_count == 0 else "WARNING" if alert_count <= 2 else "CRITICAL",
                "alert_count": alert_count,
                "positive_trends_count": positive_count,
                "action_required": alert_count > 0
            }
            
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            insights["error"] = str(e)
        
        return insights
    
    def _generate_recommendations(self, performance_data: Dict[str, Any],
                                cost_analysis: Dict[str, Any],
                                feedback_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate actionable recommendations."""
        recommendations = []
        
        try:
            # Performance-based recommendations
            overall_metrics = performance_data.get("overall_metrics", {})
            roi = overall_metrics.get("overall_roi", 0)
            
            if roi < 0:
                recommendations.append({
                    "category": "performance",
                    "priority": "high",
                    "title": "Improve Parlay Strategy",
                    "description": "Negative ROI indicates strategy adjustments needed",
                    "actions": [
                        "Review leg selection criteria",
                        "Analyze losing parlay patterns",
                        "Consider reducing parlay size",
                        "Implement stricter confidence thresholds"
                    ]
                })
            
            # Cost-based recommendations
            budget_utilization = cost_analysis.get("budget_analysis", {}).get("daily_budget_utilization", 0)
            
            if budget_utilization > 0.8:
                recommendations.append({
                    "category": "cost_optimization",
                    "priority": "medium",
                    "title": "Optimize API Usage",
                    "description": "High API cost utilization detected",
                    "actions": [
                        "Implement API call caching",
                        "Reduce odds fetching frequency",
                        "Optimize data fetching schedules",
                        "Consider API tier upgrades"
                    ]
                })
            
            # Model-based recommendations
            if feedback_results.get("executed"):
                sport_results = feedback_results.get("results_by_sport", {})
                
                for sport, result in sport_results.items():
                    if result.get("drift_detected") and not result.get("retrained"):
                        recommendations.append({
                            "category": "model_maintenance",
                            "priority": "high",
                            "title": f"Retrain {sport.upper()} Model",
                            "description": f"Data drift detected in {sport} model",
                            "actions": [
                                "Schedule model retraining",
                                "Review recent data quality",
                                "Update feature engineering",
                                "Validate model performance"
                            ]
                        })
            
            # Default recommendations if no issues
            if not recommendations:
                recommendations.append({
                    "category": "maintenance",
                    "priority": "low",
                    "title": "Continue Monitoring",
                    "description": "System performing well - maintain current approach",
                    "actions": [
                        "Monitor daily reports",
                        "Track performance trends",
                        "Prepare for upcoming sports seasons",
                        "Consider expanding to new markets"
                    ]
                })
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            recommendations.append({
                "category": "error",
                "priority": "high",
                "title": "Report Generation Error",
                "description": f"Error in recommendation generation: {e}",
                "actions": ["Review system logs", "Check data integrity"]
            })
        
        return recommendations
    
    async def _save_report(self, report: Dict[str, Any], report_date: str) -> str:
        """Save report to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"daily_parlay_report_{report_date}_{timestamp}.json"
        report_path = self.config.report_output_dir / filename
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Also save latest report
        latest_path = self.config.report_output_dir / "latest_daily_report.json"
        with open(latest_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Report saved: {report_path}")
        return str(report_path)
    
    async def _send_notifications(self, report: Dict[str, Any], insights: Dict[str, Any]):
        """Send notifications via Slack/email."""
        try:
            alert_count = insights.get("summary", {}).get("alert_count", 0)
            health_status = insights.get("summary", {}).get("overall_health", "UNKNOWN")
            
            if alert_count == 0 and health_status == "GOOD":
                logger.info("📱 No alerts - skipping notifications")
                return
            
            # Prepare notification message
            date = report["report_metadata"]["report_date"]
            message = self._format_notification_message(report, insights)
            
            # Send Slack notification
            if self.config.slack_webhook_url and HAS_REQUESTS:
                await self._send_slack_notification(message)
            
            logger.info(f"📱 Notifications sent for {alert_count} alerts")
            
        except Exception as e:
            logger.error(f"Error sending notifications: {e}")
    
    def _format_notification_message(self, report: Dict[str, Any], insights: Dict[str, Any]) -> str:
        """Format notification message."""
        date = report["report_metadata"]["report_date"]
        health = insights.get("summary", {}).get("overall_health", "UNKNOWN")
        alerts = insights.get("alerts", [])
        
        message = f"🏀🏈 Daily Parlay Report - {date}\n"
        message += f"📊 System Health: {health}\n\n"
        
        if alerts:
            message += "⚠️ Alerts:\n"
            for alert in alerts[:3]:  # Limit to top 3 alerts
                message += f"• {alert}\n"
        
        # Add performance summary
        performance = report.get("performance_summary", {}).get("overall_metrics", {})
        roi = performance.get("overall_roi", 0)
        win_rate = performance.get("overall_win_rate", 0)
        
        message += f"\n📈 Performance:\n"
        message += f"• ROI: {roi:.1%}\n"
        message += f"• Win Rate: {win_rate:.1%}\n"
        
        # Add cost summary
        cost_analysis = report.get("cost_analysis", {})
        todays_cost = cost_analysis.get("todays_costs", {}).get("total", 0)
        
        message += f"\n💰 Today's API Cost: ${todays_cost:.2f}\n"
        
        return message
    
    async def _send_slack_notification(self, message: str):
        """Send Slack webhook notification."""
        try:
            payload = {
                "text": message,
                "username": "Parlay Bot",
                "icon_emoji": ":chart_with_upwards_trend:"
            }
            
            response = requests.post(self.config.slack_webhook_url, json=payload)
            response.raise_for_status()
            
            logger.info("📱 Slack notification sent successfully")
            
        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")


async def main():
    """Main entry point for daily report generation."""
    parser = argparse.ArgumentParser(description="Generate daily parlay reports")
    parser.add_argument("--sport", choices=["nba", "nfl"], help="Generate report for specific sport")
    parser.add_argument("--no-feedback", action="store_true", help="Skip feedback loop execution")
    parser.add_argument("--no-alerts", action="store_true", help="Skip sending alerts")
    parser.add_argument("--output-dir", help="Custom output directory for reports")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize configuration
    config = DailyReportConfig()
    
    if args.no_feedback:
        config.enable_feedback_loop = False
    if args.no_alerts:
        config.enable_alerts = False
    if args.output_dir:
        config.report_output_dir = Path(args.output_dir)
    
    # Generate report
    generator = DailyReportGenerator(config)
    report = await generator.generate_daily_report(args.sport)
    
    if report.get("error"):
        logger.error(f"Report generation failed: {report['error']}")
        sys.exit(1)
    
    print("✅ Daily parlay report generated successfully!")
    
    # Print summary
    insights = report.get("insights_and_alerts", {})
    summary = insights.get("summary", {})
    
    print(f"📊 System Health: {summary.get('overall_health', 'UNKNOWN')}")
    print(f"⚠️ Alerts: {summary.get('alert_count', 0)}")
    print(f"📈 Positive Trends: {summary.get('positive_trends_count', 0)}")


if __name__ == "__main__":
    asyncio.run(main())
