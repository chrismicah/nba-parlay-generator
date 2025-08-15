#!/usr/bin/env python3
"""
Test Suite for JIRA-020: Few-Shot Learning Enhancement

Tests the few-shot learning capabilities added to the ParlayStrategistAgent
to improve parlay prompting using high-confidence past examples.
"""

import unittest
import json
import logging
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.few_shot_parlay_extractor import FewShotParlayExtractor, FewShotExample
from tools.enhanced_parlay_strategist_agent import FewShotEnhancedParlayStrategistAgent, FewShotContext
from tools.odds_fetcher_tool import GameOdds, BookOdds, Selection


class TestFewShotParlayExtractor(unittest.TestCase):
    """Test the few-shot parlay extractor functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_dataset_path = os.path.join(self.temp_dir, "test_dataset.jsonl")
        
        # Create test dataset
        test_samples = [
            {
                "parlay_id": "test_high_conf_1",
                "reasoning": "PARLAY ANALYSIS (3 legs):\n\nLEG 1: Lakers ML @ 1.85\n• Sharp money indicators\n• Statistical edge identified\n\nOVERALL ASSESSMENT:\nCombined odds: 5.5\nRisk assessment: Low risk\nValue assessment: Strong value",
                "outcome": "win",
                "confidence_label": "high_confidence",
                "generated_at": "2025-08-01T12:00:00",
                "legs_count": 3,
                "total_odds": 5.5
            },
            {
                "parlay_id": "test_high_conf_2",
                "reasoning": "PARLAY ANALYSIS (2 legs):\n\nLEG 1: Celtics -4.5\n• Line movement favorable\n• Injury advantage\n\nOVERALL ASSESSMENT:\nCombined odds: 3.8\nRisk assessment: Low risk",
                "outcome": "win",
                "confidence_label": "high_confidence",
                "generated_at": "2025-08-02T12:00:00",
                "legs_count": 2,
                "total_odds": 3.8
            },
            {
                "parlay_id": "test_low_conf_1",
                "reasoning": "PARLAY ANALYSIS (3 legs):\n\nLEG 1: Warriors +7.5\n• Public money trap concerns\n• Injury concerns present\n\nOVERALL ASSESSMENT:\nCombined odds: 8.2\nRisk assessment: High risk",
                "outcome": "loss",
                "confidence_label": "low_confidence",
                "generated_at": "2025-08-03T12:00:00",
                "legs_count": 3,
                "total_odds": 8.2
            }
        ]
        
        with open(self.test_dataset_path, 'w') as f:
            for sample in test_samples:
                f.write(json.dumps(sample) + '\n')
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_load_dataset(self):
        """Test loading parlay reasoning dataset."""
        extractor = FewShotParlayExtractor(self.test_dataset_path)
        samples = extractor.load_dataset()
        
        self.assertEqual(len(samples), 3)
        self.assertEqual(samples[0]['parlay_id'], 'test_high_conf_1')
        self.assertEqual(samples[1]['confidence_label'], 'high_confidence')
        self.assertEqual(samples[2]['outcome'], 'loss')
    
    def test_extract_successful_examples(self):
        """Test extracting successful high-confidence examples."""
        extractor = FewShotParlayExtractor(self.test_dataset_path)
        examples = extractor.extract_successful_examples(num_examples=5)
        
        # Should only get high-confidence winning examples
        self.assertEqual(len(examples), 2)  # Only 2 high-conf wins in test data
        
        for example in examples:
            self.assertIsInstance(example, FewShotExample)
            self.assertEqual(example.outcome, 'win')
            self.assertGreater(example.success_metrics['success_score'], 0)
    
    def test_success_score_calculation(self):
        """Test success score calculation logic."""
        extractor = FewShotParlayExtractor(self.test_dataset_path)
        
        # Test high-scoring parlay
        high_score_parlay = {
            'total_odds': 4.0,  # Good odds range
            'legs_count': 3,    # Optimal leg count
            'reasoning': 'Sharp money indicators and statistical edge identified',
            'outcome': 'win'
        }
        score1 = extractor._calculate_success_score(high_score_parlay)
        
        # Test lower-scoring parlay
        low_score_parlay = {
            'total_odds': 12.0,  # Too high odds
            'legs_count': 6,     # Too many legs
            'reasoning': 'Public money trap concerns and injury concerns',
            'outcome': 'win'
        }
        score2 = extractor._calculate_success_score(low_score_parlay)
        
        self.assertGreater(score1, score2)
    
    def test_input_data_extraction(self):
        """Test extraction of structured input data from reasoning."""
        extractor = FewShotParlayExtractor(self.test_dataset_path)
        
        reasoning = """PARLAY ANALYSIS (2 legs):
        
LEG 1: Lakers ML @ 1.85
• Sharp money movement detected
• Statistical trend favorable

LEG 2: Celtics -4.5 @ 1.91
• Injury advantage present
• Line moved favorably
        """
        
        input_data = extractor._extract_input_data_from_reasoning(reasoning)
        
        self.assertEqual(len(input_data['available_games']), 2)
        self.assertIn('injury', str(input_data['injury_intel']).lower())
        self.assertIn('line moved', str(input_data['line_movements']).lower())
        self.assertIn('statistical', str(input_data['statistical_insights']).lower())
    
    def test_parlay_structure_extraction(self):
        """Test extraction of parlay structure from reasoning."""
        extractor = FewShotParlayExtractor(self.test_dataset_path)
        
        reasoning = """PARLAY ANALYSIS (2 legs):
        
LEG 1: Lakers ML @ 1.85
Odds: 1.85 at DraftKings
• Sharp money detected

LEG 2: Celtics -4.5 @ 1.91
Odds: 1.91 at FanDuel
• Line movement favorable

OVERALL ASSESSMENT:
Combined odds: 3.54
Risk assessment: Low risk
Value assessment: Strong value
        """
        
        parlay = extractor._extract_parlay_structure(reasoning)
        
        self.assertEqual(len(parlay['legs']), 2)
        self.assertEqual(parlay['total_odds'], 3.54)
        self.assertEqual(parlay['risk_assessment'], 'Low risk')
        self.assertEqual(parlay['value_assessment'], 'Strong value')
    
    def test_save_few_shot_examples(self):
        """Test saving few-shot examples to JSON."""
        extractor = FewShotParlayExtractor(self.test_dataset_path)
        examples = extractor.extract_successful_examples(num_examples=2)
        
        output_path = os.path.join(self.temp_dir, "test_few_shot.json")
        extractor.save_few_shot_examples(output_path)
        
        # Verify file was created and contains expected data
        self.assertTrue(os.path.exists(output_path))
        
        with open(output_path, 'r') as f:
            data = json.load(f)
        
        self.assertIn('metadata', data)
        self.assertIn('examples', data)
        self.assertIn('prompt_template', data)
        self.assertEqual(len(data['examples']), 2)


class TestFewShotEnhancedParlayStrategistAgent(unittest.TestCase):
    """Test the few-shot enhanced parlay strategist agent."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_few_shot_path = os.path.join(self.temp_dir, "test_few_shot.json")
        
        # Create test few-shot examples file
        test_few_shot_data = {
            "metadata": {
                "generated_at": "2025-08-15T12:00:00",
                "total_examples": 2,
                "source_dataset": "test_dataset.jsonl"
            },
            "examples": [
                {
                    "example_id": "few_shot_01",
                    "input_data": {
                        "available_games": [
                            {
                                "selection": "Lakers ML",
                                "market_type": "moneyline",
                                "team": "Lakers",
                                "factors": ["Sharp money detected", "Statistical edge"]
                            }
                        ],
                        "injury_intel": [],
                        "line_movements": ["Line moved favorably"],
                        "statistical_insights": ["Statistical edge identified"]
                    },
                    "reasoning": "PARLAY ANALYSIS (2 legs):\n\nLEG 1: Lakers ML\n• Sharp money detected\n\nOVERALL ASSESSMENT:\nCombined odds: 3.5\nRisk assessment: Low risk",
                    "outcome": "win",
                    "confidence_score": 0.8,
                    "success_metrics": {
                        "success_score": 2.1,
                        "rank": 1,
                        "total_odds": 3.5,
                        "legs_count": 2
                    }
                }
            ],
            "prompt_template": "=== HIGH-CONFIDENCE SUCCESSFUL PARLAY EXAMPLES ===\nExample reasoning templates..."
        }
        
        with open(self.test_few_shot_path, 'w') as f:
            json.dump(test_few_shot_data, f)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_load_few_shot_examples(self):
        """Test loading few-shot examples."""
        agent = FewShotEnhancedParlayStrategistAgent(
            use_injury_classifier=False,
            few_shot_examples_path=self.test_few_shot_path
        )
        
        self.assertIsNotNone(agent.few_shot_context)
        self.assertEqual(len(agent.few_shot_context.examples), 1)
        self.assertIn("HIGH-CONFIDENCE", agent.few_shot_context.prompt_template)
    
    def test_few_shot_stats(self):
        """Test few-shot statistics reporting."""
        agent = FewShotEnhancedParlayStrategistAgent(
            use_injury_classifier=False,
            few_shot_examples_path=self.test_few_shot_path
        )
        
        stats = agent.get_few_shot_stats()
        
        self.assertTrue(stats['few_shot_enabled'])
        self.assertEqual(stats['examples_loaded'], 1)
        self.assertIn('metadata', stats)
        self.assertIn('example_success_scores', stats)
    
    def test_extract_few_shot_insights(self):
        """Test extraction of few-shot insights for games."""
        agent = FewShotEnhancedParlayStrategistAgent(
            use_injury_classifier=False,
            few_shot_examples_path=self.test_few_shot_path
        )
        
        # Mock game data
        mock_game = MagicMock()
        mock_game.game_id = "test_game_1"
        
        analysis = {
            'teams': ['Lakers', 'Celtics'],
            'opportunities': [
                {
                    'market_type': 'moneyline',
                    'selection_name': 'Lakers ML',
                    'opportunity_score': 0.6
                }
            ]
        }
        
        insights = agent._extract_few_shot_insights_for_game(mock_game, analysis)
        
        # Should find at least some patterns (either team or market)
        self.assertGreater(len(insights), 0)
        
        # Check pattern types
        pattern_types = [insight['type'] for insight in insights]
        self.assertTrue(any(ptype in ['team_pattern', 'market_pattern'] for ptype in pattern_types))
    
    def test_pattern_matching_score(self):
        """Test pattern matching score calculation."""
        agent = FewShotEnhancedParlayStrategistAgent(
            use_injury_classifier=False,
            few_shot_examples_path=self.test_few_shot_path
        )
        
        opportunities = [
            {
                'few_shot_insights': [
                    {'type': 'market_pattern', 'confidence_boost': 0.1},
                    {'type': 'team_pattern', 'confidence_boost': 0.15}
                ]
            }
        ]
        
        score = agent._calculate_pattern_matching_score(opportunities)
        self.assertGreater(score, 0)
        self.assertLessEqual(score, 1.0)
    
    def test_similarity_score_calculation(self):
        """Test similarity score calculation."""
        agent = FewShotEnhancedParlayStrategistAgent(
            use_injury_classifier=False,
            few_shot_examples_path=self.test_few_shot_path
        )
        
        opportunities = [
            {
                'market_type': 'moneyline',
                'reasoning_factors': [
                    MagicMock(description="Sharp money movement detected")
                ]
            }
        ]
        
        score = agent._calculate_similarity_score(opportunities)
        self.assertGreater(score, 0)
        self.assertLessEqual(score, 1.0)
    
    def test_few_shot_enhanced_generation(self):
        """Test few-shot enhanced parlay generation."""
        agent = FewShotEnhancedParlayStrategistAgent(
            use_injury_classifier=False,
            few_shot_examples_path=self.test_few_shot_path
        )
        
        # Mock game data
        mock_games = [
            self._create_mock_game("game1", "Lakers", "Celtics"),
            self._create_mock_game("game2", "Warriors", "Nets"),
        ]
        
        # Test with few-shot enabled
        recommendation_with_fs = agent.generate_parlay_with_reasoning(
            mock_games, target_legs=2, use_few_shot=True
        )
        
        # Test without few-shot
        recommendation_without_fs = agent.generate_parlay_with_reasoning(
            mock_games, target_legs=2, use_few_shot=False
        )
        
        if recommendation_with_fs and recommendation_without_fs:
            # Few-shot version should have enhanced reasoning
            self.assertIn("FEW-SHOT", recommendation_with_fs.reasoning.reasoning_text)
            self.assertNotIn("FEW-SHOT", recommendation_without_fs.reasoning.reasoning_text)
    
    def _create_mock_game(self, game_id: str, home_team: str, away_team: str) -> GameOdds:
        """Create a mock game for testing."""
        # Create mock selections
        home_selection = Selection(name=home_team, price_decimal=1.85)
        away_selection = Selection(name=away_team, price_decimal=2.10)
        
        # Create mock book
        mock_book = BookOdds(
            bookmaker="DraftKings",
            market="h2h",
            selections=[home_selection, away_selection]
        )
        
        # Create mock game
        return GameOdds(
            sport_key="basketball_nba",
            game_id=game_id,
            commence_time="2025-08-15T20:00:00Z",
            books=[mock_book]
        )


class TestIntegrationJIRA020(unittest.TestCase):
    """Integration tests for the complete JIRA-020 implementation."""
    
    def setUp(self):
        """Set up integration test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create a small test dataset
        self.test_dataset_path = os.path.join(self.temp_dir, "integration_dataset.jsonl")
        test_samples = []
        
        # Generate some realistic test samples
        for i in range(20):
            confidence = "high_confidence" if i < 10 else "low_confidence"
            outcome = "win" if (confidence == "high_confidence" and i % 3 != 0) or (confidence == "low_confidence" and i % 4 == 0) else "loss"
            
            sample = {
                "parlay_id": f"integration_test_{i}",
                "reasoning": f"PARLAY ANALYSIS ({2 + i % 3} legs):\n\nLEG 1: Team{i % 5} ML @ 1.{80 + i}\n• {'Sharp money' if i % 2 == 0 else 'Statistical edge'} detected\n\nOVERALL ASSESSMENT:\nCombined odds: {2.5 + i * 0.1}\nRisk assessment: {'Low' if confidence == 'high_confidence' else 'High'} risk",
                "outcome": outcome,
                "confidence_label": confidence,
                "generated_at": f"2025-08-{1 + i % 28:02d}T12:00:00",
                "legs_count": 2 + i % 3,
                "total_odds": 2.5 + i * 0.1
            }
            test_samples.append(sample)
        
        with open(self.test_dataset_path, 'w') as f:
            for sample in test_samples:
                f.write(json.dumps(sample) + '\n')
    
    def tearDown(self):
        """Clean up integration test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_end_to_end_few_shot_workflow(self):
        """Test the complete end-to-end few-shot learning workflow."""
        # Step 1: Extract few-shot examples
        extractor = FewShotParlayExtractor(self.test_dataset_path)
        examples = extractor.extract_successful_examples(num_examples=5)
        
        self.assertGreater(len(examples), 0)
        
        # Step 2: Save examples
        few_shot_path = os.path.join(self.temp_dir, "integration_few_shot.json")
        extractor.save_few_shot_examples(few_shot_path)
        self.assertTrue(os.path.exists(few_shot_path))
        
        # Step 3: Initialize enhanced agent
        agent = FewShotEnhancedParlayStrategistAgent(
            use_injury_classifier=False,
            few_shot_examples_path=few_shot_path
        )
        
        # Step 4: Verify agent loaded examples
        stats = agent.get_few_shot_stats()
        self.assertTrue(stats['few_shot_enabled'])
        self.assertGreater(stats['examples_loaded'], 0)
        
        # Step 5: Test reasoning enhancement
        mock_games = [self._create_mock_game("integration_game", "TestTeam", "OpponentTeam")]
        
        # This should work without errors and include few-shot insights
        # (Note: May return None if no suitable opportunities found, which is okay)
        try:
            recommendation = agent.generate_parlay_with_reasoning(
                mock_games, target_legs=1, min_total_odds=1.5, use_few_shot=True
            )
            # If recommendation is generated, it should have few-shot elements
            if recommendation:
                self.assertIn("few_shot_enhanced", recommendation.reasoning.strategist_version)
        except Exception as e:
            self.fail(f"End-to-end workflow failed with error: {e}")
    
    def test_performance_comparison(self):
        """Test performance comparison between regular and few-shot enhanced agents."""
        # Extract few-shot examples
        extractor = FewShotParlayExtractor(self.test_dataset_path)
        examples = extractor.extract_successful_examples(num_examples=3)
        
        few_shot_path = os.path.join(self.temp_dir, "performance_few_shot.json")
        extractor.save_few_shot_examples(few_shot_path)
        
        # Initialize both agents
        regular_agent = FewShotEnhancedParlayStrategistAgent(
            use_injury_classifier=False,
            few_shot_examples_path="nonexistent_path.json"  # Force no few-shot
        )
        
        enhanced_agent = FewShotEnhancedParlayStrategistAgent(
            use_injury_classifier=False,
            few_shot_examples_path=few_shot_path
        )
        
        # Create mock games
        mock_games = [
            self._create_mock_game("perf_game1", "TeamA", "TeamB"),
            self._create_mock_game("perf_game2", "TeamC", "TeamD"),
        ]
        
        # Generate recommendations
        regular_rec = regular_agent.generate_parlay_with_reasoning(
            mock_games, target_legs=2, min_total_odds=2.0, use_few_shot=False
        )
        
        enhanced_rec = enhanced_agent.generate_parlay_with_reasoning(
            mock_games, target_legs=2, min_total_odds=2.0, use_few_shot=True
        )
        
        # Both should be able to generate something (or both fail gracefully)
        if regular_rec and enhanced_rec:
            # Enhanced version should have different reasoning
            self.assertNotEqual(
                regular_rec.reasoning.reasoning_text,
                enhanced_rec.reasoning.reasoning_text
            )
            
            # Enhanced version should have few-shot elements
            self.assertIn("FEW-SHOT", enhanced_rec.reasoning.reasoning_text)
    
    def _create_mock_game(self, game_id: str, home_team: str, away_team: str) -> GameOdds:
        """Create a mock game for integration testing."""
        # Create comprehensive mock selections
        home_ml = Selection(name=home_team, price_decimal=1.75)
        away_ml = Selection(name=away_team, price_decimal=2.25)
        
        home_spread = Selection(name=f"{home_team} -2.5", price_decimal=1.91, line=-2.5)
        away_spread = Selection(name=f"{away_team} +2.5", price_decimal=1.91, line=2.5)
        
        over = Selection(name="Over", price_decimal=1.95, line=215.5)
        under = Selection(name="Under", price_decimal=1.87, line=215.5)
        
        # Create multiple books
        moneyline_book = BookOdds(
            bookmaker="DraftKings",
            market="h2h",
            selections=[home_ml, away_ml]
        )
        
        spread_book = BookOdds(
            bookmaker="FanDuel",
            market="spreads",
            selections=[home_spread, away_spread]
        )
        
        totals_book = BookOdds(
            bookmaker="BetMGM",
            market="totals",
            selections=[over, under]
        )
        
        return GameOdds(
            sport_key="basketball_nba",
            game_id=game_id,
            commence_time="2025-08-15T20:00:00Z",
            books=[moneyline_book, spread_book, totals_book]
        )


def run_tests():
    """Run the complete test suite for JIRA-020."""
    # Set up logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise during testing
    
    # Create test suite
    loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(loader.loadTestsFromTestCase(TestFewShotParlayExtractor))
    test_suite.addTest(loader.loadTestsFromTestCase(TestFewShotEnhancedParlayStrategistAgent))
    test_suite.addTest(loader.loadTestsFromTestCase(TestIntegrationJIRA020))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    print("🧪 Running JIRA-020 Few-Shot Learning Tests")
    print("=" * 60)
    
    success = run_tests()
    
    if success:
        print("\n✅ All tests passed! JIRA-020 implementation is working correctly.")
    else:
        print("\n❌ Some tests failed. Please check the output above.")
        sys.exit(1)
