#!/usr/bin/env python3
"""
Test Suite for JIRA-020A: Bayesian Confidence Scoring System

Tests the adaptive Bayesian confidence scoring system that incorporates:
- RoBERTa confidence scores from JIRA-019
- RAG retrieval quality metrics
- Real-time odds movement from latency monitor
- Summer League volatility weighting
- Threshold-based bet flagging system
"""

import unittest
import logging
import numpy as np
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.bayesian_confidence_scorer import (
    BayesianConfidenceScorer, EvidenceSource, BayesianUpdate, ConfidenceAssessment
)


class TestEvidenceSource(unittest.TestCase):
    """Test the EvidenceSource dataclass."""
    
    def test_evidence_source_creation(self):
        """Test creating evidence source objects."""
        evidence = EvidenceSource(
            name="test_evidence",
            confidence=0.8,
            reliability=0.9,
            weight=1.0,
            metadata={"test": True}
        )
        
        self.assertEqual(evidence.name, "test_evidence")
        self.assertEqual(evidence.confidence, 0.8)
        self.assertEqual(evidence.reliability, 0.9)
        self.assertEqual(evidence.weight, 1.0)
        self.assertEqual(evidence.metadata["test"], True)
    
    def test_evidence_source_defaults(self):
        """Test default values for evidence source."""
        evidence = EvidenceSource(
            name="minimal",
            confidence=0.5,
            reliability=0.7
        )
        
        self.assertEqual(evidence.weight, 1.0)
        self.assertEqual(evidence.metadata, {})


class TestBayesianConfidenceScorer(unittest.TestCase):
    """Test the main Bayesian confidence scorer functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.scorer = BayesianConfidenceScorer(
            base_threshold=0.6,
            odds_movement_sensitivity=0.1
        )
        logging.disable(logging.CRITICAL)  # Reduce test noise
    
    def tearDown(self):
        """Clean up after tests."""
        logging.disable(logging.NOTSET)
    
    def test_scorer_initialization(self):
        """Test scorer initialization with default and custom parameters."""
        # Test default initialization
        default_scorer = BayesianConfidenceScorer()
        self.assertEqual(default_scorer.base_threshold, 0.6)
        self.assertEqual(default_scorer.odds_movement_sensitivity, 0.1)
        
        # Test custom initialization
        custom_scorer = BayesianConfidenceScorer(
            base_threshold=0.7,
            odds_movement_sensitivity=0.15
        )
        self.assertEqual(custom_scorer.base_threshold, 0.7)
        self.assertEqual(custom_scorer.odds_movement_sensitivity, 0.15)
    
    def test_likelihood_calculation(self):
        """Test likelihood calculation for Bayesian updates."""
        evidence = EvidenceSource(
            name="test",
            confidence=0.8,
            reliability=0.9,
            weight=1.0
        )
        
        likelihood = self.scorer.calculate_likelihood(evidence)
        
        # Likelihood should be between 0 and 1
        self.assertGreater(likelihood, 0.0)
        self.assertLess(likelihood, 1.0)
        
        # Higher confidence should yield higher likelihood
        high_conf_evidence = EvidenceSource("high", confidence=0.9, reliability=0.9)
        low_conf_evidence = EvidenceSource("low", confidence=0.3, reliability=0.9)
        
        high_likelihood = self.scorer.calculate_likelihood(high_conf_evidence)
        low_likelihood = self.scorer.calculate_likelihood(low_conf_evidence)
        
        self.assertGreater(high_likelihood, low_likelihood)
    
    def test_single_bayesian_update(self):
        """Test single Bayesian update calculation."""
        prior = 0.5
        evidence = EvidenceSource(
            name="test_update",
            confidence=0.8,
            reliability=0.9,
            weight=1.0
        )
        
        update = self.scorer.bayesian_update(prior, evidence)
        
        self.assertIsInstance(update, BayesianUpdate)
        self.assertEqual(update.prior, prior)
        self.assertGreater(update.likelihood, 0.0)
        self.assertLess(update.likelihood, 1.0)
        self.assertGreater(update.posterior, 0.0)
        self.assertLess(update.posterior, 1.0)
        self.assertEqual(update.evidence, evidence)
    
    def test_sequential_bayesian_updates(self):
        """Test sequential Bayesian updates with multiple evidence sources."""
        initial_prior = 0.5
        evidence_list = [
            EvidenceSource("evidence_1", confidence=0.8, reliability=0.9, weight=1.0),
            EvidenceSource("evidence_2", confidence=0.7, reliability=0.8, weight=1.2),
            EvidenceSource("evidence_3", confidence=0.6, reliability=0.7, weight=0.8)
        ]
        
        final_posterior, updates = self.scorer.sequential_bayesian_updates(
            initial_prior, evidence_list
        )
        
        # Should have updates for each evidence source
        self.assertEqual(len(updates), len(evidence_list))
        
        # Posterior should be reasonable
        self.assertGreater(final_posterior, 0.0)
        self.assertLess(final_posterior, 1.0)
        
        # Each update should connect properly
        for i, update in enumerate(updates):
            if i == 0:
                self.assertEqual(update.prior, initial_prior)
            else:
                self.assertEqual(update.prior, updates[i-1].posterior)
    
    def test_volatility_adjustment(self):
        """Test volatility adjustment for different game types."""
        # Playoffs should have positive adjustment
        playoff_metadata = {"season_type": "playoffs"}
        playoff_adj = self.scorer.calculate_volatility_adjustment(playoff_metadata)
        self.assertGreater(playoff_adj, 0.0)
        
        # Regular season should be neutral
        regular_metadata = {"season_type": "regular"}
        regular_adj = self.scorer.calculate_volatility_adjustment(regular_metadata)
        self.assertEqual(regular_adj, 0.0)
        
        # Preseason should have negative adjustment
        preseason_metadata = {"season_type": "preseason"}
        preseason_adj = self.scorer.calculate_volatility_adjustment(preseason_metadata)
        self.assertLess(preseason_adj, 0.0)
        
        # Multiple factors should combine
        complex_metadata = {
            "season_type": "preseason",
            "is_back_to_back": True,
            "is_national_tv": True
        }
        complex_adj = self.scorer.calculate_volatility_adjustment(complex_metadata)
        # Should be negative (preseason penalty outweighs small boosts)
        self.assertLess(complex_adj, 0.0)
    
    def test_roberta_evidence_extraction(self):
        """Test extraction of evidence from RoBERTa results."""
        roberta_result = {
            "predicted_confidence": "high_confidence",
            "max_confidence_score": 0.85,
            "prediction_certainty": 0.8,
            "confidence_probabilities": {"low_confidence": 0.15, "high_confidence": 0.85}
        }
        
        evidence = self.scorer.extract_roberta_evidence(roberta_result)
        
        self.assertEqual(evidence.name, "roberta_confidence")
        self.assertEqual(evidence.confidence, 0.85)
        self.assertGreater(evidence.reliability, 0.0)
        self.assertEqual(evidence.weight, 1.0)
        self.assertIn("predicted_confidence", evidence.metadata)
    
    def test_rag_evidence_extraction(self):
        """Test extraction of evidence from RAG results."""
        # Test with good RAG results
        good_rag_results = [
            {"score": 0.9, "metadata": {"source": "the_ringer"}},
            {"score": 0.8, "metadata": {"source": "action_network"}},
            {"score": 0.75, "metadata": {"source": "nba_com"}}
        ]
        
        evidence = self.scorer.extract_rag_evidence(good_rag_results)
        
        self.assertEqual(evidence.name, "rag_quality")
        self.assertGreater(evidence.confidence, 0.7)  # Should be high for good results
        self.assertGreater(evidence.reliability, 0.0)
        self.assertEqual(evidence.metadata["num_results"], 3)
        
        # Test with empty results
        empty_evidence = self.scorer.extract_rag_evidence([])
        self.assertEqual(empty_evidence.name, "rag_quality")
        self.assertEqual(empty_evidence.confidence, 0.3)  # Low for no results
        self.assertEqual(empty_evidence.metadata["num_results"], 0)
    
    def test_odds_movement_evidence_extraction(self):
        """Test extraction of evidence from odds movement data."""
        # Test with clear movement
        odds_with_movement = [
            {"price_decimal": 1.90, "timestamp": "2025-01-01T10:00:00Z"},
            {"price_decimal": 1.95, "timestamp": "2025-01-01T11:00:00Z"},
            {"price_decimal": 2.00, "timestamp": "2025-01-01T12:00:00Z"}
        ]
        
        evidence = self.scorer.extract_odds_movement_evidence(odds_with_movement)
        
        self.assertEqual(evidence.name, "odds_movement")
        self.assertGreater(evidence.confidence, 0.5)  # Should detect movement
        self.assertEqual(evidence.metadata["movement_detected"], True)
        self.assertEqual(evidence.metadata["num_observations"], 3)
        
        # Test with insufficient data
        minimal_odds = [{"price_decimal": 1.90}]
        minimal_evidence = self.scorer.extract_odds_movement_evidence(minimal_odds)
        self.assertEqual(minimal_evidence.confidence, 0.5)  # Neutral
        self.assertEqual(minimal_evidence.metadata["movement_detected"], False)
    
    def test_contextual_evidence_extraction(self):
        """Test extraction of contextual evidence from reasoning text."""
        reasoning_with_context = """
        Lakers -3.5 looks strong tonight. LeBron is questionable but expected to play.
        Sharp money moved the line from -2.5 to -3.5 despite 65% public on the underdog.
        Professional bettors are backing the Lakers heavily.
        """
        
        evidence_list = self.scorer.extract_contextual_evidence(reasoning_with_context)
        
        # Should find injury, sharp money, and public betting evidence
        evidence_names = [e.name for e in evidence_list]
        self.assertIn("injury_intel", evidence_names)
        self.assertIn("sharp_money", evidence_names)
        self.assertIn("public_betting", evidence_names)
        
        # Sharp money should have high confidence
        sharp_evidence = next(e for e in evidence_list if e.name == "sharp_money")
        self.assertGreater(sharp_evidence.confidence, 0.7)
        self.assertGreater(sharp_evidence.weight, 1.0)  # High weight
    
    def test_dynamic_threshold_calculation(self):
        """Test dynamic threshold calculation based on context."""
        base_threshold = 0.6
        
        # High reliability evidence should lower threshold
        high_reliability_threshold = self.scorer.calculate_dynamic_threshold(
            base_threshold, {}, 0.9
        )
        self.assertLess(high_reliability_threshold, base_threshold)
        
        # Low reliability evidence should raise threshold
        low_reliability_threshold = self.scorer.calculate_dynamic_threshold(
            base_threshold, {}, 0.5
        )
        self.assertGreater(low_reliability_threshold, base_threshold)
        
        # Preseason should raise threshold
        preseason_threshold = self.scorer.calculate_dynamic_threshold(
            base_threshold, {"season_type": "preseason"}, 0.75
        )
        self.assertGreater(preseason_threshold, base_threshold)
        
        # Playoff games should lower threshold
        playoff_threshold = self.scorer.calculate_dynamic_threshold(
            base_threshold, {"season_type": "playoffs"}, 0.75
        )
        self.assertLess(playoff_threshold, base_threshold)
    
    def test_complete_confidence_assessment(self):
        """Test complete confidence assessment with all components."""
        roberta_result = {
            "predicted_confidence": "high_confidence",
            "max_confidence_score": 0.82,
            "prediction_certainty": 0.75
        }
        
        rag_results = [
            {"score": 0.87, "metadata": {"source": "the_ringer"}},
            {"score": 0.79, "metadata": {"source": "action_network"}}
        ]
        
        odds_history = [
            {"price_decimal": 1.91, "timestamp": "2025-01-01T10:00:00Z"},
            {"price_decimal": 1.95, "timestamp": "2025-01-01T11:00:00Z"}
        ]
        
        reasoning_text = "Sharp money backing this play heavily."
        
        game_metadata = {
            "season_type": "regular",
            "is_national_tv": True
        }
        
        assessment = self.scorer.assess_confidence(
            roberta_result=roberta_result,
            rag_results=rag_results,
            odds_history=odds_history,
            reasoning_text=reasoning_text,
            game_metadata=game_metadata
        )
        
        self.assertIsInstance(assessment, ConfidenceAssessment)
        self.assertGreater(assessment.final_confidence, 0.0)
        self.assertLess(assessment.final_confidence, 1.0)
        self.assertGreater(assessment.posterior_probability, 0.0)
        self.assertIn(assessment.should_flag, [True, False])
        self.assertGreater(assessment.threshold_used, 0.0)
        self.assertGreater(len(assessment.evidence_sources), 0)
        self.assertGreater(len(assessment.bayesian_updates), 0)
    
    def test_assessment_with_no_evidence(self):
        """Test assessment behavior with no evidence sources."""
        assessment = self.scorer.assess_confidence()
        
        self.assertEqual(assessment.final_confidence, 0.5)  # Neutral
        self.assertEqual(assessment.posterior_probability, 0.5)
        self.assertTrue(assessment.should_flag)  # Should flag with no evidence
        self.assertEqual(len(assessment.evidence_sources), 0)
        self.assertEqual(len(assessment.bayesian_updates), 0)
        self.assertIn("no_evidence_sources", assessment.metadata["warning"])
    
    def test_preseason_scenario(self):
        """Test specific preseason scenario with volatility penalty."""
        preseason_metadata = {"season_type": "preseason"}
        
        # High confidence evidence
        roberta_result = {
            "predicted_confidence": "high_confidence",
            "max_confidence_score": 0.9,
            "prediction_certainty": 0.85
        }
        
        assessment = self.scorer.assess_confidence(
            roberta_result=roberta_result,
            game_metadata=preseason_metadata
        )
        
        # Should apply volatility penalty
        self.assertLess(assessment.volatility_adjustment, 0.0)
        self.assertEqual(assessment.volatility_adjustment, -0.08)  # Preseason penalty
        
        # Threshold should be higher for preseason
        self.assertGreater(assessment.threshold_used, self.scorer.base_threshold)
    
    def test_assessment_summary(self):
        """Test assessment summary generation."""
        # Create a simple assessment
        roberta_result = {"max_confidence_score": 0.8, "prediction_certainty": 0.7}
        assessment = self.scorer.assess_confidence(roberta_result=roberta_result)
        
        summary = self.scorer.get_assessment_summary(assessment)
        
        # Should have all required fields
        required_fields = [
            "recommendation", "final_confidence", "posterior_probability",
            "threshold_used", "confidence_vs_threshold", "volatility_adjustment",
            "evidence_sources", "bayesian_updates", "metadata"
        ]
        
        for field in required_fields:
            self.assertIn(field, summary)
        
        # Recommendation should be clear
        self.assertIn(summary["recommendation"], ["PROCEED", "FLAG - INSUFFICIENT CONFIDENCE"])
        
        # Confidence vs threshold should be calculated correctly
        expected_margin = assessment.final_confidence - assessment.threshold_used
        self.assertAlmostEqual(summary["confidence_vs_threshold"], expected_margin, places=3)


class TestIntegrationScenarios(unittest.TestCase):
    """Test realistic integration scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.scorer = BayesianConfidenceScorer()
        logging.disable(logging.CRITICAL)
    
    def tearDown(self):
        """Clean up after tests."""
        logging.disable(logging.NOTSET)
    
    def test_high_confidence_scenario(self):
        """Test scenario with high confidence across all sources."""
        # All sources indicating high confidence
        roberta_result = {
            "predicted_confidence": "high_confidence",
            "max_confidence_score": 0.92,
            "prediction_certainty": 0.88
        }
        
        rag_results = [
            {"score": 0.94, "metadata": {"source": "mathletics"}},
            {"score": 0.89, "metadata": {"source": "the_ringer"}},
            {"score": 0.86, "metadata": {"source": "action_network"}}
        ]
        
        reasoning_text = """
        Sharp syndicate money has been hammering this line all day.
        Professional bettors moved the number from +3 to +1.5.
        No injury concerns and strong historical edge.
        """
        
        assessment = self.scorer.assess_confidence(
            roberta_result=roberta_result,
            rag_results=rag_results,
            reasoning_text=reasoning_text
        )
        
        # Should have high confidence and not be flagged
        self.assertGreater(assessment.final_confidence, 0.8)
        self.assertFalse(assessment.should_flag)
        
        summary = self.scorer.get_assessment_summary(assessment)
        self.assertEqual(summary["recommendation"], "PROCEED")
    
    def test_low_confidence_scenario(self):
        """Test scenario with low confidence that should be flagged."""
        # Low confidence across sources
        roberta_result = {
            "predicted_confidence": "low_confidence",
            "max_confidence_score": 0.35,
            "prediction_certainty": 0.6
        }
        
        rag_results = [
            {"score": 0.42, "metadata": {"source": "clutchpoints"}},
            {"score": 0.38, "metadata": {"source": "random_blog"}}
        ]
        
        reasoning_text = "Public is heavily on this side. Seems like a trap game."
        
        game_metadata = {"season_type": "preseason"}  # Extra volatility
        
        assessment = self.scorer.assess_confidence(
            roberta_result=roberta_result,
            rag_results=rag_results,
            reasoning_text=reasoning_text,
            game_metadata=game_metadata
        )
        
        # Should have low confidence and be flagged
        self.assertLess(assessment.final_confidence, 0.6)
        self.assertTrue(assessment.should_flag)
        
        summary = self.scorer.get_assessment_summary(assessment)
        self.assertEqual(summary["recommendation"], "FLAG - INSUFFICIENT CONFIDENCE")
    
    def test_mixed_evidence_scenario(self):
        """Test scenario with conflicting evidence sources."""
        # High RoBERTa confidence but low RAG quality
        roberta_result = {
            "predicted_confidence": "high_confidence",
            "max_confidence_score": 0.88,
            "prediction_certainty": 0.82
        }
        
        # Poor RAG results
        rag_results = [
            {"score": 0.45, "metadata": {"source": "low_quality_blog"}},
            {"score": 0.52, "metadata": {"source": "another_blog"}}
        ]
        
        # Mixed contextual signals
        reasoning_text = """
        Model likes this play but public is also heavily backing it.
        Some sharp action early but recreational money followed.
        """
        
        assessment = self.scorer.assess_confidence(
            roberta_result=roberta_result,
            rag_results=rag_results,
            reasoning_text=reasoning_text
        )
        
        # Should result in moderate confidence
        self.assertGreater(assessment.final_confidence, 0.4)
        self.assertLess(assessment.final_confidence, 0.8)
        
        # Bayesian updates should show the conflicting evidence
        self.assertGreater(len(assessment.bayesian_updates), 2)


def main():
    """Run the test suite."""
    # Set up logging for tests
    logging.basicConfig(
        level=logging.WARNING,  # Reduce noise during testing
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create test suite
    loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(loader.loadTestsFromTestCase(TestEvidenceSource))
    test_suite.addTest(loader.loadTestsFromTestCase(TestBayesianConfidenceScorer))
    test_suite.addTest(loader.loadTestsFromTestCase(TestIntegrationScenarios))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    if result.wasSuccessful():
        print(f"\n✅ All tests passed! ({result.testsRun} tests)")
        print("🎯 JIRA-020A Bayesian Confidence Scorer - Test Suite Complete")
        return True
    else:
        print(f"\n❌ {len(result.failures)} test(s) failed, {len(result.errors)} error(s)")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
