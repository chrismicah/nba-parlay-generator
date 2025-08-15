#!/usr/bin/env python3
"""
Feedback Loop Orchestrator - JIRA-020B

Orchestrates the complete post-analysis feedback loop system:
- Runs weekly performance analysis
- Updates few-shot examples with successful patterns
- Triggers RoBERTa retraining when needed
- Manages the feedback cycle for continuous improvement
"""

import logging
import json
import shutil
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

# Import our feedback loop components
from tools.post_analysis_feedback_loop import PostAnalysisFeedbackLoop, FeedbackReport
from tools.automated_roberta_retraining import AutomatedRoBERTaRetrainer, RetrainingResults
from tools.few_shot_parlay_extractor import FewShotParlayExtractor

logger = logging.getLogger(__name__)


@dataclass
class OrchestrationResults:
    """Results from complete orchestration cycle."""
    cycle_id: str
    timestamp: str
    analysis_completed: bool
    few_shot_updated: bool
    retraining_triggered: bool
    retraining_successful: bool
    total_bets_analyzed: int
    patterns_flagged: int
    patterns_successful: int
    new_few_shot_examples: int
    retraining_accuracy: float
    next_cycle_date: str
    improvements_made: List[str]
    metadata: Dict[str, Any]


class FeedbackLoopOrchestrator:
    """
    Main orchestrator for the complete feedback loop system.
    
    Coordinates weekly analysis, pattern identification, few-shot updates,
    and RoBERTa retraining to create a continuous improvement cycle.
    """
    
    def __init__(self,
                 db_path: str = "data/parlays.sqlite",
                 few_shot_path: str = "data/few_shot_parlay_examples.json",
                 orchestration_log_path: str = "data/orchestration_logs"):
        """
        Initialize the feedback loop orchestrator.
        
        Args:
            db_path: Path to the bets database
            few_shot_path: Path to few-shot examples file
            orchestration_log_path: Directory for orchestration logs
        """
        self.db_path = Path(db_path)
        self.few_shot_path = Path(few_shot_path)
        self.orchestration_log_path = Path(orchestration_log_path)
        
        # Initialize components
        self.feedback_loop = PostAnalysisFeedbackLoop(str(self.db_path))
        self.retrainer = AutomatedRoBERTaRetrainer(str(self.db_path))
        self.few_shot_extractor = FewShotParlayExtractor()
        
        # Create directories
        self.orchestration_log_path.mkdir(parents=True, exist_ok=True)
        
        logger.info("Initialized FeedbackLoopOrchestrator")
    
    def run_weekly_cycle(self, 
                        days_back: int = 7,
                        force_retraining: bool = False) -> OrchestrationResults:
        """
        Run complete weekly feedback loop cycle.
        
        Args:
            days_back: Number of days to analyze
            force_retraining: Force retraining regardless of recommendations
            
        Returns:
            Complete orchestration results
        """
        cycle_id = f"cycle_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        logger.info(f"Starting weekly feedback cycle: {cycle_id}")
        
        improvements_made = []
        analysis_completed = False
        few_shot_updated = False
        retraining_triggered = False
        retraining_successful = False
        retraining_accuracy = 0.0
        
        try:
            # Step 1: Run weekly analysis
            logger.info("Step 1: Running weekly performance analysis")
            feedback_report = self.feedback_loop.run_weekly_analysis(days_back)
            analysis_completed = True
            
            # Save feedback report
            report_path = self.feedback_loop.save_report(
                feedback_report, 
                f"{self.orchestration_log_path}/feedback_report_{cycle_id}.json"
            )
            improvements_made.append(f"Generated feedback report: {report_path}")
            
            # Step 2: Update few-shot examples with successful patterns
            if feedback_report.few_shot_candidates:
                logger.info("Step 2: Updating few-shot examples")
                updated_count = self.update_few_shot_examples(
                    feedback_report.few_shot_candidates
                )
                few_shot_updated = updated_count > 0
                if few_shot_updated:
                    improvements_made.append(f"Added {updated_count} new few-shot examples")
            else:
                logger.info("Step 2: No few-shot candidates found")
            
            # Step 3: Check if retraining is needed
            should_retrain = (feedback_report.retraining_recommendation or 
                            force_retraining)
            
            if should_retrain:
                logger.info("Step 3: Triggering RoBERTa retraining")
                retraining_triggered = True
                
                retraining_results = self.retrainer.run_automated_retraining(
                    days_back=90  # Use more data for retraining
                )
                retraining_successful = retraining_results.success
                retraining_accuracy = retraining_results.final_accuracy
                
                # Save retraining log
                retraining_log = self.retrainer.save_retraining_log(
                    retraining_results,
                    f"{self.orchestration_log_path}/retraining_log_{cycle_id}.json"
                )
                
                if retraining_successful:
                    improvements_made.append(
                        f"Successfully retrained RoBERTa: {retraining_accuracy:.3f} accuracy"
                    )
                else:
                    improvements_made.append("RoBERTa retraining failed")
            else:
                logger.info("Step 3: No retraining needed")
            
            # Step 4: Generate improvement recommendations
            self.generate_system_improvements(feedback_report, improvements_made)
            
            # Calculate next cycle date
            from datetime import timedelta
            next_cycle = datetime.now() + timedelta(days=7)
            
            results = OrchestrationResults(
                cycle_id=cycle_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                analysis_completed=analysis_completed,
                few_shot_updated=few_shot_updated,
                retraining_triggered=retraining_triggered,
                retraining_successful=retraining_successful,
                total_bets_analyzed=feedback_report.total_bets,
                patterns_flagged=len(feedback_report.flagged_patterns),
                patterns_successful=len(feedback_report.successful_patterns),
                new_few_shot_examples=len(feedback_report.few_shot_candidates),
                retraining_accuracy=retraining_accuracy,
                next_cycle_date=next_cycle.isoformat(),
                improvements_made=improvements_made,
                metadata={
                    "analysis_period": feedback_report.analysis_period,
                    "overall_win_rate": feedback_report.overall_win_rate,
                    "confidence_calibration": feedback_report.confidence_calibration
                }
            )
            
            # Save orchestration results
            self.save_orchestration_results(results)
            
            logger.info(f"Weekly feedback cycle completed: {cycle_id}")
            return results
            
        except Exception as e:
            logger.error(f"Weekly cycle failed: {e}")
            
            # Return error results
            return OrchestrationResults(
                cycle_id=cycle_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                analysis_completed=analysis_completed,
                few_shot_updated=few_shot_updated,
                retraining_triggered=retraining_triggered,
                retraining_successful=False,
                total_bets_analyzed=0,
                patterns_flagged=0,
                patterns_successful=0,
                new_few_shot_examples=0,
                retraining_accuracy=0.0,
                next_cycle_date="",
                improvements_made=improvements_made,
                metadata={"error": str(e)}
            )
    
    def update_few_shot_examples(self, candidates: List[Dict[str, Any]]) -> int:
        """
        Update few-shot examples with new successful patterns.
        
        Args:
            candidates: List of few-shot candidates
            
        Returns:
            Number of examples added
        """
        if not candidates:
            return 0
        
        try:
            # Load existing few-shot examples
            existing_examples = []
            if self.few_shot_path.exists():
                with open(self.few_shot_path, 'r') as f:
                    existing_data = json.load(f)
                    existing_examples = existing_data.get("examples", [])
            
            # Add new candidates
            added_count = 0
            for candidate in candidates[:5]:  # Limit to top 5
                # Check if already exists (avoid duplicates)
                duplicate = False
                for existing in existing_examples:
                    if (existing.get("reasoning_text", "")[:100] == 
                        candidate.get("reasoning_text", "")[:100]):
                        duplicate = True
                        break
                
                if not duplicate:
                    # Convert candidate to few-shot format
                    few_shot_example = {
                        "example_id": candidate["example_id"],
                        "input_data": {
                            "reasoning_text": candidate["reasoning_text"],
                            "confidence_score": candidate["confidence_score"]
                        },
                        "reasoning": candidate["reasoning_text"],
                        "generated_parlay": {
                            "outcome": candidate["actual_outcome"],
                            "confidence": candidate["confidence_score"]
                        },
                        "outcome": candidate["actual_outcome"],
                        "confidence_score": candidate["confidence_score"],
                        "success_metrics": {
                            "pattern_type": candidate.get("pattern_type"),
                            "pattern_category": candidate.get("pattern_category"),
                            "quality_score": candidate["quality_score"]
                        },
                        "metadata": {
                            **candidate.get("metadata", {}),
                            "added_timestamp": datetime.now(timezone.utc).isoformat(),
                            "source": "feedback_loop_orchestrator"
                        }
                    }
                    
                    existing_examples.append(few_shot_example)
                    added_count += 1
            
            if added_count > 0:
                # Backup existing file
                if self.few_shot_path.exists():
                    backup_path = self.few_shot_path.with_suffix('.json.backup')
                    shutil.copy2(self.few_shot_path, backup_path)
                
                # Save updated examples
                updated_data = {
                    "examples": existing_examples,
                    "metadata": {
                        "total_examples": len(existing_examples),
                        "last_updated": datetime.now(timezone.utc).isoformat(),
                        "update_source": "feedback_loop_orchestrator",
                        "new_examples_added": added_count
                    }
                }
                
                with open(self.few_shot_path, 'w') as f:
                    json.dump(updated_data, f, indent=2, default=str)
                
                logger.info(f"Added {added_count} new few-shot examples")
            
            return added_count
            
        except Exception as e:
            logger.error(f"Failed to update few-shot examples: {e}")
            return 0
    
    def generate_system_improvements(self, 
                                   feedback_report: FeedbackReport,
                                   improvements_made: List[str]):
        """
        Generate system-wide improvement recommendations.
        
        Args:
            feedback_report: Feedback analysis report
            improvements_made: List to append improvements to
        """
        # Analyze confidence calibration issues
        poor_calibration_bins = []
        for bin_name, metrics in feedback_report.confidence_calibration.items():
            if isinstance(metrics, dict) and not metrics.get("well_calibrated", True):
                poor_calibration_bins.append((bin_name, metrics))
        
        if poor_calibration_bins:
            improvements_made.append(
                f"Identified {len(poor_calibration_bins)} poorly calibrated confidence bins"
            )
        
        # Check for systematic issues
        if len(feedback_report.flagged_patterns) > 2:
            improvements_made.append(
                "Multiple failing patterns detected - recommend prompt engineering review"
            )
        
        # Positive feedback
        if feedback_report.overall_win_rate > 0.65:
            improvements_made.append(
                f"Strong overall performance: {feedback_report.overall_win_rate:.1%} win rate"
            )
        
        if len(feedback_report.successful_patterns) > 0:
            improvements_made.append(
                f"Identified {len(feedback_report.successful_patterns)} successful patterns for reinforcement"
            )
    
    def save_orchestration_results(self, results: OrchestrationResults) -> str:
        """
        Save orchestration results to file.
        
        Args:
            results: Orchestration results
            
        Returns:
            Path where results were saved
        """
        output_path = self.orchestration_log_path / f"orchestration_{results.cycle_id}.json"
        
        with open(output_path, 'w') as f:
            json.dump(asdict(results), f, indent=2, default=str)
        
        logger.info(f"Orchestration results saved to {output_path}")
        return str(output_path)
    
    def get_orchestration_history(self, days_back: int = 30) -> List[OrchestrationResults]:
        """
        Get history of orchestration cycles.
        
        Args:
            days_back: Number of days to look back
            
        Returns:
            List of historical orchestration results
        """
        history = []
        
        # Find all orchestration log files
        for log_file in self.orchestration_log_path.glob("orchestration_cycle_*.json"):
            try:
                with open(log_file, 'r') as f:
                    data = json.load(f)
                    
                # Parse timestamp
                timestamp = datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))
                cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
                
                if timestamp > cutoff:
                    results = OrchestrationResults(**data)
                    history.append(results)
                    
            except Exception as e:
                logger.warning(f"Failed to parse orchestration log {log_file}: {e}")
        
        # Sort by timestamp (newest first)
        history.sort(key=lambda x: x.timestamp, reverse=True)
        return history
    
    def print_cycle_summary(self, results: OrchestrationResults):
        """Print a summary of the orchestration cycle results."""
        print(f"🔄 FEEDBACK LOOP CYCLE SUMMARY")
        print("=" * 50)
        print(f"Cycle ID: {results.cycle_id}")
        print(f"Timestamp: {results.timestamp}")
        print(f"Analysis Period: {results.metadata.get('analysis_period', 'N/A')}")
        
        print(f"\n📊 ANALYSIS RESULTS")
        print("-" * 30)
        print(f"Analysis Completed: {'✅' if results.analysis_completed else '❌'}")
        print(f"Total Bets Analyzed: {results.total_bets_analyzed}")
        print(f"Overall Win Rate: {results.metadata.get('overall_win_rate', 0):.1%}")
        print(f"Patterns Flagged: {results.patterns_flagged}")
        print(f"Successful Patterns: {results.patterns_successful}")
        
        print(f"\n🎓 FEW-SHOT UPDATES")
        print("-" * 30)
        print(f"Few-Shot Updated: {'✅' if results.few_shot_updated else '⏸️'}")
        print(f"New Examples: {results.new_few_shot_examples}")
        
        print(f"\n🤖 MODEL RETRAINING")
        print("-" * 30)
        print(f"Retraining Triggered: {'✅' if results.retraining_triggered else '⏸️'}")
        print(f"Retraining Successful: {'✅' if results.retraining_successful else '❌'}")
        if results.retraining_accuracy > 0:
            print(f"Final Accuracy: {results.retraining_accuracy:.3f}")
        
        print(f"\n💡 IMPROVEMENTS MADE")
        print("-" * 30)
        for improvement in results.improvements_made:
            print(f"• {improvement}")
        
        print(f"\n⏰ NEXT CYCLE")
        print("-" * 30)
        print(f"Scheduled: {results.next_cycle_date}")


def main():
    """Main function for testing the orchestration system."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🎯 Feedback Loop Orchestrator - JIRA-020B")
    print("=" * 60)
    
    # Initialize orchestrator
    orchestrator = FeedbackLoopOrchestrator(
        db_path="data/parlays.sqlite",
        few_shot_path="data/few_shot_parlay_examples.json"
    )
    
    # Run weekly cycle
    print("🔄 Running weekly feedback loop cycle...")
    results = orchestrator.run_weekly_cycle(
        days_back=14,  # 2 weeks for demo
        force_retraining=False
    )
    
    # Print summary
    orchestrator.print_cycle_summary(results)
    
    # Show orchestration history
    print(f"\n📈 ORCHESTRATION HISTORY")
    print("-" * 30)
    history = orchestrator.get_orchestration_history(days_back=30)
    if history:
        for i, cycle in enumerate(history[:3], 1):  # Show last 3 cycles
            print(f"{i}. {cycle.cycle_id}: {cycle.total_bets_analyzed} bets, "
                  f"{'✅' if cycle.analysis_completed else '❌'} analysis, "
                  f"{'✅' if cycle.retraining_successful else '❌'} retraining")
    else:
        print("No previous cycles found")
    
    print(f"\n✅ JIRA-020B Feedback Loop Orchestration Complete!")
    print(f"🎯 Automated weekly cycle ready for deployment")


if __name__ == "__main__":
    main()
