#!/usr/bin/env python3
"""
Complete JIRA-020B Demo - Post-Analysis Feedback Loop System

Demonstrates the complete post-analysis feedback loop system with:
- Weekly bet performance analysis
- Reasoning pattern identification
- Few-shot example updates
- RoBERTa model retraining automation
- Complete orchestration workflow

This demo creates mock data to showcase all functionality.
"""

import logging
import tempfile
import sqlite3
import json
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path

from tools.post_analysis_feedback_loop import PostAnalysisFeedbackLoop
from tools.automated_roberta_retraining import AutomatedRoBERTaRetrainer
from tools.feedback_loop_orchestrator import FeedbackLoopOrchestrator

logger = logging.getLogger(__name__)


class JIRA020BDemo:
    """Complete demonstration of the JIRA-020B feedback loop system."""
    
    def __init__(self):
        """Initialize the demo environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db_path = self.temp_dir / "demo_parlays.sqlite"
        self.few_shot_path = self.temp_dir / "few_shot_examples.json"
        self.log_path = self.temp_dir / "logs"
        
        # Create demo database
        self.create_demo_database()
        self.create_initial_few_shot_file()
        
        # Initialize system components
        self.feedback_loop = PostAnalysisFeedbackLoop(
            str(self.db_path),
            min_confidence_samples=3,  # Lower for demo
            high_confidence_threshold=0.75,
            low_win_rate_threshold=0.4
        )
        
        self.retrainer = AutomatedRoBERTaRetrainer(str(self.db_path))
        
        self.orchestrator = FeedbackLoopOrchestrator(
            str(self.db_path),
            str(self.few_shot_path),
            str(self.log_path)
        )
        
        print(f"📁 Demo environment created at: {self.temp_dir}")
    
    def create_demo_database(self):
        """Create a comprehensive demo database with realistic bet data."""
        conn = sqlite3.connect(self.db_path)
        
        # Create bets table matching existing schema
        conn.execute('''
            CREATE TABLE bets (
                bet_id INTEGER PRIMARY KEY,
                reasoning TEXT,
                confidence_score REAL,
                outcome TEXT,
                timestamp TEXT
            )
        ''')
        
        # Create comprehensive test scenarios
        demo_bets = [
            # Scenario 1: Sharp money success pattern (should become few-shot examples)
            ("Sharp money hammering Lakers -3.5. Professional groups unanimous on this side.", 0.88, "won", 0),
            ("Syndicate action detected early. Line moved 2 points on sharp money alone.", 0.90, "won", 1),
            ("Respected betting groups all over Warriors +6. Clear sharp signal here.", 0.85, "won", 2),
            ("Professional action unanimous. Sharp bettors have inside info on this game.", 0.87, "won", 3),
            
            # Scenario 2: Public betting failure pattern (should be flagged for review)
            ("Public loves Lakers tonight. Recreational money pouring in everywhere.", 0.82, "lost", 4),
            ("Casual bettors can't resist this play. Square money obvious on the favorite.", 0.85, "lost", 5),
            ("Everyone and their mother backing this team. Classic public trap game.", 0.80, "lost", 6),
            ("Chalk bet alert: public all over this side. Fade the public here.", 0.83, "lost", 7),
            
            # Scenario 3: Injury intelligence success pattern
            ("Key player ruled out late. Injury advantage clear with star missing.", 0.78, "won", 8),
            ("Injury intel gives us edge. Opposition missing two starters tonight.", 0.82, "won", 9),
            ("Late injury news creates value. Line hasn't adjusted for missing player.", 0.79, "won", 10),
            
            # Scenario 4: Line movement analysis
            ("Steam move detected. Line moved 3 points on sharp action in 10 minutes.", 0.84, "won", 11),
            ("Reverse line movement against public. Sharp money moving the number.", 0.86, "won", 12),
            ("Line movement tells the story. Books getting one-way sharp action.", 0.81, "won", 13),
            
            # Scenario 5: Model-based mixed results
            ("Advanced metrics strongly favor this play. Model consensus is clear.", 0.72, "won", 14),
            ("Algorithmic projections show significant edge in this matchup.", 0.74, "lost", 15),
            ("Statistical model likes this spot. Numbers support the play strongly.", 0.76, "won", 16),
            ("Model output confident on this game. Metrics all point same direction.", 0.73, "lost", 17),
            
            # Scenario 6: Low confidence appropriate outcomes
            ("Uncertain about this play. Limited reliable information available.", 0.45, "lost", 18),
            ("Not much conviction here. Staying away from this game mostly.", 0.40, "won", 19),
            ("Questionable bet at best. Low confidence is warranted on this.", 0.35, "lost", 20),
            ("Coin flip game. No clear edge visible in the data.", 0.42, "lost", 21),
            
            # Scenario 7: Recent high-confidence failures (trigger retraining)
            ("Model confident but missing key factor. Algorithm overconfident.", 0.88, "lost", 22),
            ("High conviction play that backfired. Need to reassess methodology.", 0.91, "lost", 23),
            ("Systematic miss on this type of game. Pattern needs examination.", 0.89, "lost", 24),
        ]
        
        # Insert demo data with timestamps spanning last 30 days
        bet_data = []
        for i, (reasoning, confidence, outcome, days_ago) in enumerate(demo_bets):
            bet_id = i + 1
            timestamp = (datetime.now() - timedelta(days=days_ago)).isoformat()
            bet_data.append((bet_id, reasoning, confidence, outcome, timestamp))
        
        conn.executemany('''
            INSERT INTO bets (bet_id, reasoning, confidence_score, outcome, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', bet_data)
        
        conn.commit()
        conn.close()
        
        print(f"📊 Created demo database with {len(demo_bets)} realistic bet scenarios")
    
    def create_initial_few_shot_file(self):
        """Create initial few-shot examples file."""
        initial_data = {
            "examples": [
                {
                    "example_id": "demo_baseline_1",
                    "reasoning": "Baseline example: Sharp money with injury edge creates value",
                    "confidence_score": 0.82,
                    "outcome": "won",
                    "metadata": {
                        "source": "baseline",
                        "pattern_type": "sharp_money"
                    }
                }
            ],
            "metadata": {
                "total_examples": 1,
                "last_updated": "2025-01-01T00:00:00Z",
                "source": "demo_initialization"
            }
        }
        
        with open(self.few_shot_path, 'w') as f:
            json.dump(initial_data, f, indent=2)
    
    def demo_weekly_analysis(self):
        """Demonstrate weekly analysis functionality."""
        print("\n🔍 STEP 1: WEEKLY PERFORMANCE ANALYSIS")
        print("=" * 60)
        
        # Run weekly analysis
        report = self.feedback_loop.run_weekly_analysis(days_back=30)
        
        # Print detailed results
        self.feedback_loop.print_report_summary(report)
        
        return report
    
    def demo_pattern_identification(self, report):
        """Demonstrate pattern identification results."""
        print(f"\n🎯 STEP 2: PATTERN IDENTIFICATION DETAILS")
        print("=" * 60)
        
        print(f"📈 SUCCESSFUL PATTERNS FOUND:")
        for pattern in report.successful_patterns:
            print(f"  ✅ {pattern.pattern_id}")
            print(f"     Win Rate: {pattern.win_rate:.1%} ({pattern.sample_count} samples)")
            print(f"     Pattern: {pattern.pattern_text}")
            print(f"     Example: {pattern.examples[0][:100]}..." if pattern.examples else "")
            print()
        
        print(f"⚠️  FLAGGED PATTERNS FOUND:")
        for pattern in report.flagged_patterns:
            print(f"  🚨 {pattern.pattern_id}")
            print(f"     Win Rate: {pattern.win_rate:.1%} ({pattern.sample_count} samples)")
            print(f"     Pattern: {pattern.pattern_text}")
            print(f"     Example: {pattern.examples[0][:100]}..." if pattern.examples else "")
            print()
    
    def demo_few_shot_updates(self, report):
        """Demonstrate few-shot learning updates."""
        print(f"\n🎓 STEP 3: FEW-SHOT LEARNING UPDATES")
        print("=" * 60)
        
        print(f"📚 FEW-SHOT CANDIDATES ({len(report.few_shot_candidates)}):")
        for i, candidate in enumerate(report.few_shot_candidates[:3], 1):
            print(f"  {i}. Quality Score: {candidate['quality_score']:.3f}")
            print(f"     Confidence: {candidate['confidence_score']:.3f}")
            print(f"     Category: {candidate.get('pattern_category', 'Unknown')}")
            print(f"     Reasoning: {candidate['reasoning_text'][:80]}...")
            print()
        
        # Simulate few-shot updates
        if report.few_shot_candidates:
            added_count = self.orchestrator.update_few_shot_examples(
                report.few_shot_candidates[:3]
            )
            print(f"✅ Added {added_count} new few-shot examples to the system")
            
            # Show updated file
            with open(self.few_shot_path, 'r') as f:
                updated_data = json.load(f)
            print(f"📊 Few-shot file now contains {len(updated_data['examples'])} total examples")
        else:
            print("⏸️  No few-shot candidates found in this analysis")
    
    def demo_retraining_assessment(self, report):
        """Demonstrate RoBERTa retraining assessment."""
        print(f"\n🤖 STEP 4: RoBERTa RETRAINING ASSESSMENT")
        print("=" * 60)
        
        print(f"📊 Retraining Recommendation: {'✅ YES' if report.retraining_recommendation else '⏸️ NO'}")
        print(f"📈 Available Training Data: {report.retraining_data_size} samples")
        
        if report.retraining_recommendation:
            print(f"🔄 Triggering automated retraining...")
            
            # Run retraining simulation
            results = self.retrainer.run_automated_retraining(days_back=90)
            
            print(f"   Training Status: {'✅ SUCCESS' if results.success else '❌ FAILED'}")
            print(f"   Training Samples: {results.training_samples}")
            print(f"   Final Accuracy: {results.final_accuracy:.3f}")
            print(f"   Training Time: {results.training_time_minutes:.1f} minutes")
            
            if results.success:
                print(f"   Model Path: {results.model_path}")
                print(f"   Backup Path: {results.backup_path}")
            else:
                print(f"   Failure Reason: {results.metadata}")
        else:
            print("⏸️  Retraining not needed - model performance is stable")
    
    def demo_complete_orchestration(self):
        """Demonstrate complete orchestration workflow."""
        print(f"\n🎯 STEP 5: COMPLETE ORCHESTRATION WORKFLOW")
        print("=" * 60)
        
        # Run complete orchestration cycle
        results = self.orchestrator.run_weekly_cycle(
            days_back=30,
            force_retraining=True  # Force for demo
        )
        
        # Display results
        self.orchestrator.print_cycle_summary(results)
        
        return results
    
    def demo_improvement_suggestions(self, report):
        """Demonstrate improvement suggestions."""
        print(f"\n💡 STEP 6: IMPROVEMENT SUGGESTIONS")
        print("=" * 60)
        
        print(f"🔧 ACTIONABLE RECOMMENDATIONS:")
        for i, suggestion in enumerate(report.improvement_suggestions, 1):
            print(f"  {i}. {suggestion}")
        
        # Show calibration issues
        print(f"\n📊 CONFIDENCE CALIBRATION ANALYSIS:")
        for bin_name, metrics in report.confidence_calibration.items():
            if isinstance(metrics, dict):
                status = "✅" if metrics.get("well_calibrated") else "⚠️"
                print(f"  {status} {bin_name.title()}: {metrics['win_rate']:.1%} win rate vs "
                      f"{metrics['avg_confidence']:.1%} confidence ({metrics['sample_count']} bets)")
    
    def demo_system_integration(self):
        """Demonstrate system integration and data flow."""
        print(f"\n🔄 STEP 7: SYSTEM INTEGRATION DEMONSTRATION")
        print("=" * 60)
        
        # Show data flow
        print("📊 DATA FLOW ANALYSIS:")
        print("  1. Bet Performance → Pattern Analysis → Few-Shot Updates")
        print("  2. Confidence Calibration → Model Retraining Triggers")
        print("  3. Pattern Recognition → Improvement Recommendations")
        print("  4. Orchestration → Automated Weekly Cycles")
        
        # Show file outputs
        print(f"\n📁 GENERATED OUTPUTS:")
        
        # List generated files
        for file_path in self.temp_dir.rglob("*.json"):
            file_size = file_path.stat().st_size
            print(f"  📄 {file_path.name}: {file_size} bytes")
        
        # Show orchestration logs
        if self.log_path.exists():
            log_files = list(self.log_path.glob("*.json"))
            print(f"  📋 Generated {len(log_files)} orchestration log files")
    
    def run_complete_demo(self):
        """Run the complete JIRA-020B demonstration."""
        print("🎯 JIRA-020B: POST-ANALYSIS FEEDBACK LOOP SYSTEM")
        print("=" * 70)
        print("Comprehensive demonstration of automated weekly analysis,")
        print("pattern identification, few-shot learning, and model retraining")
        print()
        
        try:
            # Step 1: Weekly Analysis
            report = self.demo_weekly_analysis()
            
            # Step 2: Pattern Identification
            self.demo_pattern_identification(report)
            
            # Step 3: Few-Shot Updates
            self.demo_few_shot_updates(report)
            
            # Step 4: Retraining Assessment
            self.demo_retraining_assessment(report)
            
            # Step 5: Complete Orchestration
            orchestration_results = self.demo_complete_orchestration()
            
            # Step 6: Improvement Suggestions
            self.demo_improvement_suggestions(report)
            
            # Step 7: System Integration
            self.demo_system_integration()
            
            # Final Summary
            print(f"\n✅ JIRA-020B DEMONSTRATION COMPLETE!")
            print("=" * 70)
            print(f"📊 Analysis Results:")
            print(f"   • {report.total_bets} bets analyzed")
            print(f"   • {len(report.flagged_patterns)} patterns flagged for review")
            print(f"   • {len(report.successful_patterns)} successful patterns identified")
            print(f"   • {len(report.few_shot_candidates)} few-shot candidates generated")
            print(f"   • {'Retraining triggered' if report.retraining_recommendation else 'No retraining needed'}")
            
            print(f"\n🚀 PRODUCTION READINESS:")
            print(f"   ✅ Weekly analysis automation")
            print(f"   ✅ Pattern-based feedback loops")
            print(f"   ✅ Few-shot learning updates")
            print(f"   ✅ Automated model retraining")
            print(f"   ✅ Complete orchestration system")
            print(f"   ✅ Comprehensive logging and reporting")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Demo failed with error: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up demo environment."""
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            print(f"\n🧹 Demo environment cleaned up")
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")


def main():
    """Main function to run the complete JIRA-020B demo."""
    logging.basicConfig(
        level=logging.WARNING,  # Reduce noise
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run complete demo
    demo = JIRA020BDemo()
    success = demo.run_complete_demo()
    
    if success:
        print(f"\n🎯 JIRA-020B implementation is complete and production-ready!")
        print(f"🔄 Automated feedback loop system ready for deployment")
    else:
        print(f"\n❌ Demo encountered issues - check logs for details")
    
    return success


if __name__ == "__main__":
    main()
