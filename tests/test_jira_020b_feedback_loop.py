#!/usr/bin/env python3
"""
Test Suite for JIRA-020B: Post-Analysis Feedback Loop System

Tests the complete feedback loop system including:
- Weekly bet performance analysis
- Reasoning pattern identification
- Few-shot example updates
- RoBERTa model retraining automation
- Orchestration system
"""

import unittest
import tempfile
import sqlite3
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.post_analysis_feedback_loop import (
    PostAnalysisFeedbackLoop, BetPerformanceAnalysis, ReasoningPattern, FeedbackReport
)
from tools.automated_roberta_retraining import AutomatedRoBERTaRetrainer, RetrainingResults
from tools.feedback_loop_orchestrator import FeedbackLoopOrchestrator, OrchestrationResults


class TestPostAnalysisFeedbackLoop(unittest.TestCase):
    """Test the post-analysis feedback loop functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_parlays.sqlite")
        self.setup_test_database()
        
        self.feedback_loop = PostAnalysisFeedbackLoop(
            db_path=self.db_path,
            min_confidence_samples=3,  # Lower for testing
            high_confidence_threshold=0.75,
            low_win_rate_threshold=0.4
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def setup_test_database(self):
        """Create test database with sample data."""
        conn = sqlite3.connect(self.db_path)
        
        # Create bets table (matching existing schema)
        conn.execute('''
            CREATE TABLE bets (
                bet_id INTEGER PRIMARY KEY,
                reasoning TEXT,
                confidence_score REAL,
                outcome TEXT,
                timestamp TEXT
            )
        ''')
        
        # Insert test data
        test_bets = [
            # High confidence wins (should be successful pattern)
            (1, "Sharp money backing Lakers heavily. Professional action from respected groups.", 0.85, "won", "2025-01-01T10:00:00Z"),
            (2, "Sharp syndicate moved the line. Clear injury advantage with star player out.", 0.88, "won", "2025-01-02T10:00:00Z"),
            (3, "Professional bettors unanimous. Sharp action all day on this side.", 0.90, "won", "2025-01-03T10:00:00Z"),
            
            # High confidence losses (should be flagged pattern)
            (4, "Public heavily backing this side. Recreational money pouring in.", 0.82, "lost", "2025-01-04T10:00:00Z"),
            (5, "Casual bettors love this play. Square money everywhere.", 0.85, "lost", "2025-01-05T10:00:00Z"),
            (6, "Public chalk bet. Everyone on this side.", 0.87, "lost", "2025-01-06T10:00:00Z"),
            
            # Medium confidence mixed results
            (7, "Model likes this play based on advanced metrics.", 0.65, "won", "2025-01-07T10:00:00Z"),
            (8, "Historical trends suggest edge here.", 0.68, "lost", "2025-01-08T10:00:00Z"),
            
            # Low confidence (should be neutral)
            (9, "Uncertain about this play. Limited information available.", 0.45, "lost", "2025-01-09T10:00:00Z"),
            (10, "Questionable bet. Not much conviction.", 0.40, "won", "2025-01-10T10:00:00Z"),
        ]
        
        conn.executemany('''
            INSERT INTO bets (bet_id, reasoning, confidence_score, outcome, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', test_bets)
        
        conn.commit()
        conn.close()
    
    def test_extract_bet_performance_data(self):
        """Test extraction of bet performance data."""
        analyses = self.feedback_loop.extract_bet_performance_data(days_back=30)
        
        self.assertGreater(len(analyses), 0)
        self.assertEqual(len(analyses), 10)  # Should get all test bets
        
        # Check data integrity
        for analysis in analyses:
            self.assertIsInstance(analysis, BetPerformanceAnalysis)
            self.assertIsNotNone(analysis.bet_id)
            self.assertIsNotNone(analysis.reasoning_text)
            self.assertIn(analysis.actual_outcome, ['win', 'loss'])
            self.assertIsInstance(analysis.win_loss, bool)
    
    def test_confidence_calibration_analysis(self):
        """Test confidence calibration analysis."""
        analyses = self.feedback_loop.extract_bet_performance_data(days_back=30)
        calibration = self.feedback_loop.analyze_confidence_calibration(analyses)
        
        self.assertIsInstance(calibration, dict)
        
        # Should have some calibration bins
        self.assertGreater(len(calibration), 0)
        
        for bin_name, metrics in calibration.items():
            if isinstance(metrics, dict):
                self.assertIn("win_rate", metrics)
                self.assertIn("avg_confidence", metrics)
                self.assertIn("calibration_error", metrics)
                self.assertIn("sample_count", metrics)
                self.assertIsInstance(metrics["well_calibrated"], bool)
    
    def test_failing_pattern_identification(self):
        """Test identification of failing reasoning patterns."""
        analyses = self.feedback_loop.extract_bet_performance_data(days_back=30)
        failing_patterns = self.feedback_loop.identify_failing_patterns(analyses)
        
        self.assertIsInstance(failing_patterns, list)
        
        # Should identify public betting as a failing pattern
        public_pattern_found = False
        for pattern in failing_patterns:
            if "public_betting" in pattern.pattern_id:
                public_pattern_found = True
                self.assertEqual(pattern.pattern_type, "failing")
                self.assertLess(pattern.win_rate, 0.5)  # Should have poor win rate
                self.assertGreater(pattern.sample_count, 0)
        
        # Should find the public betting pattern based on our test data
        self.assertTrue(public_pattern_found, "Should identify public betting as failing pattern")
    
    def test_successful_pattern_identification(self):
        """Test identification of successful reasoning patterns."""
        analyses = self.feedback_loop.extract_bet_performance_data(days_back=30)
        successful_patterns = self.feedback_loop.identify_successful_patterns(analyses)
        
        self.assertIsInstance(successful_patterns, list)
        
        # Should identify sharp money as a successful pattern
        sharp_pattern_found = False
        for pattern in successful_patterns:
            if "sharp_money" in pattern.pattern_id:
                sharp_pattern_found = True
                self.assertEqual(pattern.pattern_type, "successful")
                self.assertGreater(pattern.win_rate, 0.75)  # Should have good win rate
                self.assertGreater(pattern.sample_count, 0)
        
        # Should find the sharp money pattern based on our test data
        self.assertTrue(sharp_pattern_found, "Should identify sharp money as successful pattern")
    
    def test_few_shot_candidate_generation(self):
        """Test generation of few-shot learning candidates."""
        analyses = self.feedback_loop.extract_bet_performance_data(days_back=30)
        successful_patterns = self.feedback_loop.identify_successful_patterns(analyses)
        
        if successful_patterns:
            candidates = self.feedback_loop.generate_few_shot_candidates(
                successful_patterns, analyses
            )
            
            self.assertIsInstance(candidates, list)
            
            for candidate in candidates:
                self.assertIn("example_id", candidate)
                self.assertIn("reasoning_text", candidate)
                self.assertIn("confidence_score", candidate)
                self.assertIn("quality_score", candidate)
                self.assertEqual(candidate["actual_outcome"], "win")
    
    def test_retraining_need_assessment(self):
        """Test assessment of RoBERTa retraining needs."""
        analyses = self.feedback_loop.extract_bet_performance_data(days_back=30)
        calibration = self.feedback_loop.analyze_confidence_calibration(analyses)
        
        should_retrain, data_size = self.feedback_loop.assess_retraining_need(
            analyses, calibration
        )
        
        self.assertIsInstance(should_retrain, bool)
        self.assertIsInstance(data_size, int)
        self.assertEqual(data_size, len(analyses))
    
    def test_complete_weekly_analysis(self):
        """Test complete weekly analysis workflow."""
        report = self.feedback_loop.run_weekly_analysis(days_back=30)
        
        self.assertIsInstance(report, FeedbackReport)
        self.assertGreater(report.total_bets, 0)
        self.assertIsInstance(report.overall_win_rate, float)
        self.assertIsInstance(report.flagged_patterns, list)
        self.assertIsInstance(report.successful_patterns, list)
        self.assertIsInstance(report.few_shot_candidates, list)
        self.assertIsInstance(report.retraining_recommendation, bool)
        self.assertIsInstance(report.improvement_suggestions, list)


class TestAutomatedRoBERTaRetrainer(unittest.TestCase):
    """Test the automated RoBERTa retraining functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_parlays.sqlite")
        self.setup_test_database()
        
        self.retrainer = AutomatedRoBERTaRetrainer(
            db_path=self.db_path
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def setup_test_database(self):
        """Create test database with training data."""
        conn = sqlite3.connect(self.db_path)
        
        # Create bets table
        conn.execute('''
            CREATE TABLE bets (
                bet_id INTEGER PRIMARY KEY,
                reasoning TEXT,
                confidence_score REAL,
                outcome TEXT,
                timestamp TEXT
            )
        ''')
        
        # Insert training data
        training_data = []
        for i in range(100):
            # Create diverse training examples
            if i % 4 == 0:  # High confidence wins
                reasoning = f"Strong analysis {i}: Sharp money, injury edge, line movement."
                confidence = 0.85 + (i % 10) * 0.01
                outcome = "win"
            elif i % 4 == 1:  # High confidence losses
                reasoning = f"Poor analysis {i}: Public backing, no edge, questionable."
                confidence = 0.80 + (i % 10) * 0.01
                outcome = "loss"
            elif i % 4 == 2:  # Low confidence wins
                reasoning = f"Uncertain analysis {i}: Limited info, mixed signals."
                confidence = 0.45 + (i % 10) * 0.01
                outcome = "win"
            else:  # Low confidence losses
                reasoning = f"Weak analysis {i}: No conviction, risky play."
                confidence = 0.40 + (i % 10) * 0.01
                outcome = "loss"
            
            created_at = (datetime.now() - timedelta(days=i)).isoformat()
            # Convert outcome to existing schema format
            schema_outcome = "won" if outcome == "win" else "lost"
            training_data.append((i+1, reasoning, confidence, schema_outcome, created_at))
        
        conn.executemany('''
            INSERT INTO bets (bet_id, reasoning, confidence_score, outcome, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', training_data)
        
        conn.commit()
        conn.close()
    
    def test_extract_training_data(self):
        """Test extraction of training data."""
        texts, labels = self.retrainer.extract_training_data(days_back=90, min_samples=50)
        
        self.assertGreater(len(texts), 0)
        self.assertEqual(len(texts), len(labels))
        
        # Check data quality
        for text in texts:
            self.assertIsInstance(text, str)
            self.assertGreater(len(text), 0)
        
        for label in labels:
            self.assertIn(label, [0, 1])
    
    def test_training_data_validation(self):
        """Test validation of training data conditions."""
        texts, labels = self.retrainer.extract_training_data(days_back=90)
        
        if texts and labels:
            can_retrain, reason = self.retrainer.validate_retraining_conditions(texts, labels)
            
            self.assertIsInstance(can_retrain, bool)
            self.assertIsInstance(reason, str)
            
            if can_retrain:
                self.assertGreater(len(texts), 50)  # Should have sufficient data
    
    def test_automated_retraining_workflow(self):
        """Test complete automated retraining workflow."""
        results = self.retrainer.run_automated_retraining(days_back=90)
        
        self.assertIsInstance(results, RetrainingResults)
        self.assertIsInstance(results.success, bool)
        self.assertIsInstance(results.training_samples, int)
        self.assertIsInstance(results.final_accuracy, float)
        
        # Should complete (even if simulated)
        if results.success:
            self.assertGreater(results.final_accuracy, 0.0)
            self.assertGreater(results.training_time_minutes, 0.0)


class TestFeedbackLoopOrchestrator(unittest.TestCase):
    """Test the feedback loop orchestration system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_parlays.sqlite")
        self.few_shot_path = os.path.join(self.temp_dir, "few_shot_examples.json")
        self.log_path = os.path.join(self.temp_dir, "logs")
        
        self.setup_test_database()
        self.setup_few_shot_file()
        
        self.orchestrator = FeedbackLoopOrchestrator(
            db_path=self.db_path,
            few_shot_path=self.few_shot_path,
            orchestration_log_path=self.log_path
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def setup_test_database(self):
        """Create test database."""
        conn = sqlite3.connect(self.db_path)
        
        conn.execute('''
            CREATE TABLE bets (
                id INTEGER PRIMARY KEY,
                parlay_reasoning TEXT,
                confidence_score REAL,
                bayesian_confidence REAL,
                predicted_outcome TEXT,
                actual_outcome TEXT,
                created_at TEXT,
                metadata TEXT
            )
        ''')
        
        # Add some test data
        test_data = [
            (1, "Sharp money play with clear edge", 0.85, "won", "2025-01-01T10:00:00Z"),
            (2, "Public favorite, avoid this trap", 0.80, "lost", "2025-01-02T10:00:00Z"),
            (3, "Professional action detected", 0.88, "won", "2025-01-03T10:00:00Z"),
        ]
        
        conn.executemany('''
            INSERT INTO bets (bet_id, reasoning, confidence_score, outcome, timestamp) VALUES (?, ?, ?, ?, ?)
        ''', test_data)
        
        conn.commit()
        conn.close()
    
    def setup_few_shot_file(self):
        """Create initial few-shot examples file."""
        initial_data = {
            "examples": [
                {
                    "example_id": "existing_1",
                    "reasoning": "Existing example for testing"
                }
            ],
            "metadata": {
                "total_examples": 1,
                "last_updated": "2025-01-01T00:00:00Z"
            }
        }
        
        with open(self.few_shot_path, 'w') as f:
            json.dump(initial_data, f, indent=2)
    
    def test_orchestrator_initialization(self):
        """Test orchestrator initialization."""
        self.assertIsNotNone(self.orchestrator.feedback_loop)
        self.assertIsNotNone(self.orchestrator.retrainer)
        self.assertIsNotNone(self.orchestrator.few_shot_extractor)
        
        # Check that log directory was created
        self.assertTrue(Path(self.log_path).exists())
    
    def test_few_shot_examples_update(self):
        """Test updating few-shot examples."""
        candidates = [
            {
                "example_id": "test_1",
                "reasoning_text": "Test reasoning for sharp money play",
                "confidence_score": 0.85,
                "actual_outcome": "win",
                "pattern_type": "successful",
                "pattern_category": "sharp_money",
                "quality_score": 0.90,
                "metadata": {"test": True}
            }
        ]
        
        added_count = self.orchestrator.update_few_shot_examples(candidates)
        
        self.assertGreater(added_count, 0)
        
        # Verify file was updated
        with open(self.few_shot_path, 'r') as f:
            updated_data = json.load(f)
        
        self.assertGreater(len(updated_data["examples"]), 1)  # Should have original + new
        
        # Check new example was added
        new_example_found = False
        for example in updated_data["examples"]:
            if example.get("example_id") == "test_1":
                new_example_found = True
                break
        
        self.assertTrue(new_example_found)
    
    def test_weekly_cycle_execution(self):
        """Test complete weekly cycle execution."""
        results = self.orchestrator.run_weekly_cycle(days_back=7, force_retraining=False)
        
        self.assertIsInstance(results, OrchestrationResults)
        self.assertIsNotNone(results.cycle_id)
        self.assertIsInstance(results.analysis_completed, bool)
        self.assertIsInstance(results.total_bets_analyzed, int)
        self.assertIsInstance(results.improvements_made, list)
        
        # Should complete analysis
        self.assertTrue(results.analysis_completed)
    
    def test_orchestration_results_saving(self):
        """Test saving of orchestration results."""
        # Create mock results
        results = OrchestrationResults(
            cycle_id="test_cycle_123",
            timestamp=datetime.now(timezone.utc).isoformat(),
            analysis_completed=True,
            few_shot_updated=False,
            retraining_triggered=False,
            retraining_successful=False,
            total_bets_analyzed=5,
            patterns_flagged=1,
            patterns_successful=1,
            new_few_shot_examples=0,
            retraining_accuracy=0.0,
            next_cycle_date=datetime.now().isoformat(),
            improvements_made=["Test improvement"],
            metadata={"test": True}
        )
        
        saved_path = self.orchestrator.save_orchestration_results(results)
        
        self.assertTrue(Path(saved_path).exists())
        
        # Verify file contents
        with open(saved_path, 'r') as f:
            saved_data = json.load(f)
        
        self.assertEqual(saved_data["cycle_id"], "test_cycle_123")
        self.assertTrue(saved_data["analysis_completed"])


class TestIntegrationScenarios(unittest.TestCase):
    """Test integration scenarios across the entire feedback loop system."""
    
    def setUp(self):
        """Set up integration test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "integration_test.sqlite")
        self.setup_comprehensive_database()
    
    def tearDown(self):
        """Clean up integration test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def setup_comprehensive_database(self):
        """Create comprehensive test database for integration testing."""
        conn = sqlite3.connect(self.db_path)
        
        conn.execute('''
            CREATE TABLE bets (
                id INTEGER PRIMARY KEY,
                parlay_reasoning TEXT,
                confidence_score REAL,
                bayesian_confidence REAL,
                predicted_outcome TEXT,
                actual_outcome TEXT,
                created_at TEXT,
                metadata TEXT
            )
        ''')
        
        # Create comprehensive test data
        test_scenarios = [
            # Scenario 1: Sharp money success pattern (should become few-shot)
            ("Sharp money hammering this line all day. Professional groups unanimous.", 0.90, "win", "win"),
            ("Syndicate action detected early. Line moved 2 points on sharp money.", 0.88, "win", "win"),
            ("Respected betting groups all over this play. Clear sharp signal.", 0.85, "win", "win"),
            
            # Scenario 2: Public betting failure pattern (should be flagged)
            ("Public loves this side. Recreational money everywhere.", 0.82, "win", "loss"),
            ("Casual bettors can't resist this play. Square action obvious.", 0.85, "win", "loss"),
            ("Everyone and their mother backing this team. Public trap.", 0.80, "win", "loss"),
            
            # Scenario 3: Model-based mixed results
            ("Advanced metrics strongly favor this play. Model consensus.", 0.75, "win", "win"),
            ("Algorithmic projections show clear edge here.", 0.72, "win", "loss"),
            ("Statistical model likes this matchup significantly.", 0.78, "win", "win"),
            
            # Scenario 4: Low confidence appropriate outcomes
            ("Uncertain about this play. Limited reliable information.", 0.45, "loss", "loss"),
            ("Not much conviction here. Staying away mostly.", 0.40, "loss", "win"),
            ("Questionable bet at best. Low confidence warranted.", 0.35, "loss", "loss"),
        ]
        
        bet_data = []
        for i, (reasoning, confidence, predicted, actual) in enumerate(test_scenarios):
            bet_id = i + 1
            created_at = (datetime.now() - timedelta(days=i)).isoformat()
            # Convert outcome to existing schema format
            schema_outcome = "won" if actual == "win" else "lost"
            
            bet_data.append((
                bet_id, reasoning, confidence, schema_outcome, created_at
            ))
        
        conn.executemany('''
            INSERT INTO bets (bet_id, reasoning, confidence_score, outcome, timestamp) VALUES (?, ?, ?, ?, ?)
        ''', bet_data)
        
        conn.commit()
        conn.close()
    
    def test_end_to_end_feedback_cycle(self):
        """Test complete end-to-end feedback cycle."""
        # Initialize orchestrator
        orchestrator = FeedbackLoopOrchestrator(
            db_path=self.db_path,
            few_shot_path=os.path.join(self.temp_dir, "few_shot.json"),
            orchestration_log_path=os.path.join(self.temp_dir, "logs")
        )
        
        # Run complete cycle
        results = orchestrator.run_weekly_cycle(days_back=30, force_retraining=True)
        
        # Verify cycle completion
        self.assertTrue(results.analysis_completed)
        self.assertGreater(results.total_bets_analyzed, 10)
        
        # Should identify patterns
        self.assertGreater(results.patterns_flagged + results.patterns_successful, 0)
        
        # Should have improvement suggestions
        self.assertGreater(len(results.improvements_made), 0)
        
        # Verify logs were created
        log_files = list(Path(orchestrator.orchestration_log_path).glob("*.json"))
        self.assertGreater(len(log_files), 0)
    
    def test_pattern_detection_accuracy(self):
        """Test accuracy of pattern detection."""
        feedback_loop = PostAnalysisFeedbackLoop(self.db_path)
        
        # Run analysis
        analyses = feedback_loop.extract_bet_performance_data(days_back=30)
        failing_patterns = feedback_loop.identify_failing_patterns(analyses)
        successful_patterns = feedback_loop.identify_successful_patterns(analyses)
        
        # Verify expected patterns
        pattern_names = [p.pattern_id for p in failing_patterns + successful_patterns]
        
        # Should detect sharp money as successful (based on test data)
        sharp_found = any("sharp_money" in name for name in pattern_names)
        self.assertTrue(sharp_found, "Should detect sharp money pattern")
        
        # Should detect public betting issues (based on test data)
        public_found = any("public_betting" in name for name in pattern_names)
        self.assertTrue(public_found, "Should detect public betting pattern")


def main():
    """Run the complete test suite."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTest(loader.loadTestsFromTestCase(TestPostAnalysisFeedbackLoop))
    suite.addTest(loader.loadTestsFromTestCase(TestAutomatedRoBERTaRetrainer))
    suite.addTest(loader.loadTestsFromTestCase(TestFeedbackLoopOrchestrator))
    suite.addTest(loader.loadTestsFromTestCase(TestIntegrationScenarios))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    if result.wasSuccessful():
        print(f"\n✅ All tests passed! ({result.testsRun} tests)")
        print("🎯 JIRA-020B Feedback Loop System - Test Suite Complete")
        return True
    else:
        print(f"\n❌ {len(result.failures)} test(s) failed, {len(result.errors)} error(s)")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
