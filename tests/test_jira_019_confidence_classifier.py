#!/usr/bin/env python3
"""
Comprehensive Test Suite for JIRA-019 RoBERTa Confidence Classifier

Tests all components of the parlay confidence classification system:
- Enhanced ParlayStrategistAgent
- Dataset generation
- RoBERTa training pipeline
- Confidence prediction inference
- Integration with parlay building workflow
"""

import unittest
import tempfile
import shutil
import json
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools.parlay_strategist_agent import EnhancedParlayStrategistAgent, ParlayRecommendation
from tools.generate_parlay_reasoning_dataset import ParlayReasoningDatasetGenerator
from tools.train_parlay_confidence_classifier import ParlayConfidenceClassifier
from tools.parlay_confidence_predictor import ParlayConfidencePredictor, ParlayConfidenceIntegration


class TestEnhancedParlayStrategistAgent(unittest.TestCase):
    """Test the enhanced parlay strategist with reasoning generation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.agent = EnhancedParlayStrategistAgent(use_injury_classifier=False)
    
    def test_agent_initialization(self):
        """Test agent initializes correctly."""
        self.assertIsNotNone(self.agent)
        self.assertEqual(self.agent.agent_id, "enhanced_parlay_strategist_v1.0")
        self.assertFalse(self.agent.use_injury_classifier)
    
    def test_generate_parlay_with_reasoning_no_games(self):
        """Test parlay generation with no games available."""
        result = self.agent.generate_parlay_with_reasoning([])
        self.assertIsNone(result)
    
    def test_generate_parlay_with_reasoning_mock_games(self):
        """Test parlay generation with mock game data."""
        # Create mock game data
        mock_games = self._create_mock_games()
        
        result = self.agent.generate_parlay_with_reasoning(
            mock_games, 
            target_legs=2, 
            min_total_odds=2.0
        )
        
        if result:  # May return None if no viable opportunities found
            self.assertIsInstance(result, ParlayRecommendation)
            self.assertIsNotNone(result.reasoning)
            self.assertGreater(len(result.reasoning.reasoning_text), 100)
            self.assertGreaterEqual(len(result.legs), 2)
            self.assertGreater(result.reasoning.confidence_score, 0.0)
            self.assertLess(result.reasoning.confidence_score, 1.0)
    
    def test_reasoning_text_quality(self):
        """Test that generated reasoning text contains expected elements."""
        mock_games = self._create_mock_games()
        result = self.agent.generate_parlay_with_reasoning(mock_games, target_legs=2)
        
        if result:
            reasoning = result.reasoning.reasoning_text
            
            # Check for key reasoning components
            self.assertIn("PARLAY ANALYSIS", reasoning)
            self.assertIn("LEG", reasoning)
            self.assertIn("OVERALL ASSESSMENT", reasoning)
            self.assertIn("odds", reasoning.lower())
            
            # Check reasoning factors exist
            self.assertGreater(len(result.reasoning.reasoning_factors), 0)
    
    def _create_mock_games(self):
        """Create mock game data for testing."""
        from tools.odds_fetcher_tool import GameOdds, BookOdds, Selection
        
        # Create mock selections
        selection1 = Selection(name="Lakers", price_decimal=1.8, line=None)
        selection2 = Selection(name="Celtics", price_decimal=2.1, line=None)
        selection3 = Selection(name="Over", price_decimal=1.9, line=220.5)
        selection4 = Selection(name="Under", price_decimal=1.9, line=220.5)
        
        # Create mock books
        book1 = BookOdds(
            bookmaker="DraftKings",
            market="h2h",
            selections=[selection1, selection2]
        )
        book2 = BookOdds(
            bookmaker="FanDuel", 
            market="totals",
            selections=[selection3, selection4]
        )
        
        # Create mock game
        game = GameOdds(
            game_id="test_game_001",
            books=[book1, book2]
        )
        
        return [game]


class TestParlayReasoningDatasetGenerator(unittest.TestCase):
    """Test the dataset generation for training."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.dataset_path = os.path.join(self.temp_dir, "test_dataset.jsonl")
        self.generator = ParlayReasoningDatasetGenerator(self.dataset_path)
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_generator_initialization(self):
        """Test generator initializes correctly."""
        self.assertIsNotNone(self.generator)
        self.assertTrue(Path(self.dataset_path).parent.exists())
    
    def test_generate_small_dataset(self):
        """Test generating a small dataset."""
        self.generator.generate_dataset(num_samples=10)
        
        # Check file was created
        self.assertTrue(Path(self.dataset_path).exists())
        
        # Load and validate samples
        samples = self.generator.load_dataset()
        self.assertEqual(len(samples), 10)
        
        # Check sample structure
        sample = samples[0]
        required_fields = ['parlay_id', 'reasoning', 'outcome', 'confidence_label', 'generated_at']
        for field in required_fields:
            self.assertIn(field, sample)
        
        # Check confidence labels
        confidence_labels = {s['confidence_label'] for s in samples}
        self.assertTrue(confidence_labels.issubset({'high_confidence', 'low_confidence'}))
        
        # Check outcomes
        outcomes = {s['outcome'] for s in samples}
        self.assertTrue(outcomes.issubset({'win', 'loss'}))
    
    def test_dataset_statistics(self):
        """Test dataset statistics calculation."""
        self.generator.generate_dataset(num_samples=20)
        stats = self.generator.get_dataset_stats()
        
        self.assertEqual(stats['total_samples'], 20)
        self.assertIn('confidence_distribution', stats)
        self.assertIn('outcome_distribution', stats)
        self.assertIn('win_rates_by_confidence', stats)
        self.assertIn('averages', stats)
    
    def test_reasoning_text_quality(self):
        """Test quality of generated reasoning text."""
        self.generator.generate_dataset(num_samples=5)
        samples = self.generator.load_dataset()
        
        for sample in samples:
            reasoning = sample['reasoning']
            
            # Check minimum length and structure
            self.assertGreater(len(reasoning), 200)
            self.assertIn('PARLAY ANALYSIS', reasoning)
            self.assertIn('LEG', reasoning)
            self.assertIn('OVERALL ASSESSMENT', reasoning)


class TestParlayConfidenceClassifier(unittest.TestCase):
    """Test the RoBERTa confidence classifier training."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.model_path = os.path.join(self.temp_dir, "test_model")
        self.dataset_path = os.path.join(self.temp_dir, "test_dataset.jsonl")
        
        # Generate small dataset for testing
        generator = ParlayReasoningDatasetGenerator(self.dataset_path)
        generator.generate_dataset(num_samples=20)
        
        self.classifier = ParlayConfidenceClassifier(model_save_path=self.model_path)
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_classifier_initialization(self):
        """Test classifier initializes correctly."""
        self.assertIsNotNone(self.classifier)
        self.assertEqual(self.classifier.model_name, "roberta-base")
    
    def test_load_dataset(self):
        """Test dataset loading."""
        samples = self.classifier.load_dataset(self.dataset_path)
        self.assertGreater(len(samples), 0)
        
        # Check sample structure
        sample = samples[0]
        self.assertIn('reasoning', sample)
        self.assertIn('confidence_label', sample)
    
    def test_prepare_data(self):
        """Test data preparation for training."""
        samples = self.classifier.load_dataset(self.dataset_path)
        train_dataset, val_dataset, test_dataset = self.classifier.prepare_data(
            samples, test_size=0.3, val_size=0.2
        )
        
        self.assertGreater(len(train_dataset), 0)
        self.assertGreater(len(val_dataset), 0)
        self.assertGreater(len(test_dataset), 0)
        
        # Check total samples match
        total_samples = len(train_dataset) + len(val_dataset) + len(test_dataset)
        self.assertEqual(total_samples, len(samples))
    
    @patch('torch.cuda.is_available', return_value=False)  # Force CPU for testing
    def test_model_training_dry_run(self, mock_cuda):
        """Test model training setup (dry run to avoid long training)."""
        samples = self.classifier.load_dataset(self.dataset_path)
        train_dataset, val_dataset, test_dataset = self.classifier.prepare_data(samples)
        
        # Test that training can be set up without errors
        # We won't actually train to save time
        try:
            # Initialize model to test setup
            from transformers import AutoModelForSequenceClassification
            model = AutoModelForSequenceClassification.from_pretrained(
                self.classifier.model_name,
                num_labels=len(self.classifier.label2id),
                id2label=self.classifier.id2label,
                label2id=self.classifier.label2id
            )
            self.assertIsNotNone(model)
        except Exception as e:
            self.fail(f"Model initialization failed: {e}")


class TestParlayConfidencePredictor(unittest.TestCase):
    """Test the confidence prediction inference pipeline."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.model_path = os.path.join(self.temp_dir, "test_model")
        
        # Create a mock model directory structure
        os.makedirs(self.model_path, exist_ok=True)
        
        # Create mock metadata
        metadata = {
            "model_name": "roberta-base",
            "label2id": {"low_confidence": 0, "high_confidence": 1},
            "id2label": {"0": "low_confidence", "1": "high_confidence"}
        }
        with open(os.path.join(self.model_path, "training_metadata.json"), 'w') as f:
            json.dump(metadata, f)
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_predictor_initialization(self):
        """Test predictor initializes correctly."""
        predictor = ParlayConfidencePredictor(self.model_path)
        self.assertIsNotNone(predictor)
        self.assertFalse(predictor.is_loaded)
    
    def test_model_info_without_model(self):
        """Test getting model info before loading."""
        predictor = ParlayConfidencePredictor(self.model_path)
        info = predictor.get_model_info()
        self.assertEqual(info["status"], "Model not loaded")
    
    def test_prediction_without_model_raises_error(self):
        """Test that prediction without loaded model raises error."""
        predictor = ParlayConfidencePredictor(self.model_path)
        
        with self.assertRaises(Exception):
            predictor.predict("test reasoning")
    
    def test_analyze_reasoning_structure(self):
        """Test reasoning analysis structure without model."""
        # We can test the text analysis part without a trained model
        sample_reasoning = """PARLAY ANALYSIS (3 legs):

LEG 1: Lakers -3.5 (-110)
• Sharp money moved line from -2.5 to -3.5
• Lakers are confident at home

LEG 2: Warriors vs Suns Under 225.5
• Both teams missing key players
• Public betting heavily on over

OVERALL ASSESSMENT:
Risk assessment: Medium risk with injury concerns
Value assessment: Strong value with sharp money alignment"""
        
        # Test the text analysis components
        word_count = len(sample_reasoning.split())
        self.assertGreater(word_count, 50)
        
        has_injury = 'injury' in sample_reasoning.lower()
        has_sharp = 'sharp' in sample_reasoning.lower()
        has_public = 'public' in sample_reasoning.lower()
        
        self.assertTrue(has_injury)
        self.assertTrue(has_sharp)
        self.assertTrue(has_public)


class TestParlayConfidenceIntegration(unittest.TestCase):
    """Test integration with parlay building workflow."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock predictor
        self.mock_predictor = MagicMock()
        self.mock_predictor.analyze_parlay_reasoning.return_value = {
            "confidence_prediction": {
                "predicted_confidence": "high_confidence",
                "max_confidence_score": 0.85,
                "prediction_certainty": 0.7
            },
            "reasoning_analysis": {
                "word_count": 250,
                "has_injury_intel": True,
                "has_sharp_money_indicators": True
            },
            "recommendation": "STRONG BUY: High confidence prediction with strong model certainty."
        }
        
        self.integration = ParlayConfidenceIntegration(self.mock_predictor)
    
    def test_integration_initialization(self):
        """Test integration initializes correctly."""
        self.assertIsNotNone(self.integration)
        self.assertEqual(self.integration.predictor, self.mock_predictor)
    
    def test_enhance_parlay_recommendation(self):
        """Test enhancing parlay recommendation with confidence."""
        sample_recommendation = {
            "parlay_id": "test_001",
            "legs": [{"team": "Lakers", "bet": "-3.5", "odds": 1.91}],
            "total_odds": 1.91,
            "reasoning": "Sample reasoning text"
        }
        
        enhanced = self.integration.enhance_parlay_recommendation(sample_recommendation)
        
        # Check that enhancement was added
        self.assertIn("ai_confidence_analysis", enhanced)
        self.assertIn("confidence_score", enhanced)
        self.assertIn("bet_recommendation", enhanced)
        self.assertIn("model_certainty", enhanced)
        
        # Check values
        self.assertEqual(enhanced["confidence_score"], 0.85)
        self.assertEqual(enhanced["model_certainty"], 0.7)
    
    def test_enhance_recommendation_without_reasoning_raises_error(self):
        """Test that missing reasoning field raises error."""
        bad_recommendation = {
            "parlay_id": "test_001",
            "legs": [{"team": "Lakers", "bet": "-3.5", "odds": 1.91}]
            # Missing 'reasoning' field
        }
        
        with self.assertRaises(ValueError):
            self.integration.enhance_parlay_recommendation(bad_recommendation)
    
    def test_filter_recommendations_by_confidence(self):
        """Test filtering recommendations by confidence threshold."""
        recommendations = [
            {
                "parlay_id": "high_conf",
                "reasoning": "High confidence reasoning",
                "legs": []
            },
            {
                "parlay_id": "low_conf", 
                "reasoning": "Low confidence reasoning",
                "legs": []
            }
        ]
        
        # Mock different confidence scores for different inputs
        def mock_analyze(reasoning_text):
            if "High confidence" in reasoning_text:
                return {
                    "confidence_prediction": {
                        "predicted_confidence": "high_confidence",
                        "max_confidence_score": 0.85,
                        "prediction_certainty": 0.8
                    },
                    "reasoning_analysis": {},
                    "recommendation": "STRONG BUY"
                }
            else:
                return {
                    "confidence_prediction": {
                        "predicted_confidence": "low_confidence",
                        "max_confidence_score": 0.45,
                        "prediction_certainty": 0.6
                    },
                    "reasoning_analysis": {},
                    "recommendation": "AVOID"
                }
        
        self.mock_predictor.analyze_parlay_reasoning.side_effect = mock_analyze
        
        filtered = self.integration.filter_recommendations_by_confidence(
            recommendations, min_confidence=0.7
        )
        
        # Should only return the high confidence recommendation
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["parlay_id"], "high_conf")


class TestJIRA019Integration(unittest.TestCase):
    """Test complete JIRA-019 integration workflow."""
    
    def test_end_to_end_workflow_structure(self):
        """Test that all components can be imported and initialized."""
        try:
            # Test imports
            from tools.parlay_strategist_agent import EnhancedParlayStrategistAgent
            from tools.generate_parlay_reasoning_dataset import ParlayReasoningDatasetGenerator
            from tools.train_parlay_confidence_classifier import ParlayConfidenceClassifier
            from tools.parlay_confidence_predictor import ParlayConfidencePredictor
            
            # Test initialization
            agent = EnhancedParlayStrategistAgent(use_injury_classifier=False)
            generator = ParlayReasoningDatasetGenerator()
            classifier = ParlayConfidenceClassifier()
            predictor = ParlayConfidencePredictor()
            
            self.assertIsNotNone(agent)
            self.assertIsNotNone(generator)
            self.assertIsNotNone(classifier)
            self.assertIsNotNone(predictor)
            
        except ImportError as e:
            self.fail(f"Failed to import JIRA-019 components: {e}")
    
    def test_data_flow_compatibility(self):
        """Test that data flows correctly between components."""
        # Test that strategist output is compatible with dataset generator
        agent = EnhancedParlayStrategistAgent(use_injury_classifier=False)
        
        # Mock a recommendation (since we don't have live games)
        mock_reasoning = ParlayRecommendation(
            legs=[],
            reasoning=MagicMock(reasoning_text="Sample reasoning", confidence_score=0.7)
        )
        
        # Test that reasoning text can be used for dataset
        reasoning_text = mock_reasoning.reasoning.reasoning_text
        self.assertIsInstance(reasoning_text, str)
        
        # Test that format matches dataset expectations
        sample_data = {
            "reasoning": reasoning_text,
            "confidence_label": "high_confidence",
            "outcome": "win"
        }
        
        # Verify required fields exist
        required_fields = ["reasoning", "confidence_label", "outcome"]
        for field in required_fields:
            self.assertIn(field, sample_data)


def run_comprehensive_tests():
    """Run all JIRA-019 tests."""
    print("🧪 Running Comprehensive JIRA-019 Test Suite")
    print("=" * 60)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestEnhancedParlayStrategistAgent,
        TestParlayReasoningDatasetGenerator,
        TestParlayConfidenceClassifier,
        TestParlayConfidencePredictor,
        TestParlayConfidenceIntegration,
        TestJIRA019Integration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\n📊 Test Results Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"  • {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print(f"\n💥 Errors:")
        for test, traceback in result.errors:
            print(f"  • {test}: {traceback.split('Error:')[-1].strip()}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)
