#!/usr/bin/env python3
"""
Weekly Feedback Cycle Runner - JIRA-020B

Production script for running the weekly feedback loop cycle.
Includes error handling, logging, and notification capabilities.
"""

import sys
import logging
import argparse
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from tools.feedback_loop_orchestrator import FeedbackLoopOrchestrator


def setup_logging(log_level="INFO", log_file=None):
    """Set up logging configuration."""
    level = getattr(logging, log_level.upper())
    
    # Configure logging
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )


def send_notification(results, success=True):
    """Send notification about cycle results (placeholder for email/slack)."""
    status = "✅ SUCCESS" if success else "❌ FAILED"
    
    message = f"""
🔄 Weekly Feedback Cycle Complete - {status}

Cycle ID: {results.cycle_id if results else 'N/A'}
Timestamp: {datetime.now().isoformat()}

Results:
- Analysis Completed: {'✅' if results and results.analysis_completed else '❌'}
- Bets Analyzed: {results.total_bets_analyzed if results else 0}
- Patterns Flagged: {results.patterns_flagged if results else 0}
- Few-Shot Updated: {'✅' if results and results.few_shot_updated else '⏸️'}
- Retraining: {'✅' if results and results.retraining_successful else '❌' if results and results.retraining_triggered else '⏸️'}

Next Cycle: {results.next_cycle_date if results else 'TBD'}
    """
    
    print(message)
    
    # TODO: Add email/Slack notification here
    # send_email(subject=f"Feedback Cycle {status}", body=message)
    # send_slack_message(message)


def main():
    """Main function for running weekly feedback cycle."""
    parser = argparse.ArgumentParser(description="Run weekly feedback loop cycle")
    parser.add_argument("--db-path", default="data/parlays.sqlite", 
                       help="Path to database file")
    parser.add_argument("--few-shot-path", default="data/few_shot_parlay_examples.json",
                       help="Path to few-shot examples file")
    parser.add_argument("--log-path", default="data/orchestration_logs",
                       help="Path to orchestration logs directory")
    parser.add_argument("--days-back", type=int, default=7,
                       help="Number of days to analyze")
    parser.add_argument("--force-retraining", action="store_true",
                       help="Force RoBERTa retraining regardless of recommendation")
    parser.add_argument("--log-level", default="INFO",
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Logging level")
    parser.add_argument("--log-file", help="Optional log file path")
    parser.add_argument("--dry-run", action="store_true",
                       help="Run analysis only, don't make changes")
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.log_level, args.log_file)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting weekly feedback cycle")
    logger.info(f"Parameters: days_back={args.days_back}, force_retraining={args.force_retraining}")
    
    try:
        # Initialize orchestrator
        orchestrator = FeedbackLoopOrchestrator(
            db_path=args.db_path,
            few_shot_path=args.few_shot_path,
            orchestration_log_path=args.log_path
        )
        
        if args.dry_run:
            logger.info("DRY RUN MODE - Analysis only, no changes will be made")
            # Run analysis only
            report = orchestrator.feedback_loop.run_weekly_analysis(args.days_back)
            orchestrator.feedback_loop.print_report_summary(report)
            
            # Create mock results
            from tools.feedback_loop_orchestrator import OrchestrationResults
            results = OrchestrationResults(
                cycle_id=f"dry_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                timestamp=datetime.now().isoformat(),
                analysis_completed=True,
                few_shot_updated=False,
                retraining_triggered=False,
                retraining_successful=False,
                total_bets_analyzed=report.total_bets,
                patterns_flagged=len(report.flagged_patterns),
                patterns_successful=len(report.successful_patterns),
                new_few_shot_examples=len(report.few_shot_candidates),
                retraining_accuracy=0.0,
                next_cycle_date="DRY RUN",
                improvements_made=["DRY RUN - No changes made"],
                metadata={"dry_run": True}
            )
        else:
            # Run complete cycle
            results = orchestrator.run_weekly_cycle(
                days_back=args.days_back,
                force_retraining=args.force_retraining
            )
        
        # Print summary
        orchestrator.print_cycle_summary(results)
        
        # Send notification
        send_notification(results, success=True)
        
        logger.info("Weekly feedback cycle completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Weekly feedback cycle failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Send failure notification
        send_notification(None, success=False)
        
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
