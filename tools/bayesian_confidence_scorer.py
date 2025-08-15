#!/usr/bin/env python3
"""
Bayesian Confidence Scorer - JIRA-020A

Implements an adaptive Bayesian confidence scoring system that incorporates:
- RoBERTa confidence scores from JIRA-019
- RAG retrieval quality metrics
- Real-time odds movement from latency monitor
- Summer League volatility weighting
- Threshold-based bet flagging system

Uses Bayesian methods to update confidence as new evidence becomes available.
"""

import logging
import math
import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import json

logger = logging.getLogger(__name__)


@dataclass
class EvidenceSource:
    """Single piece of evidence for Bayesian updating."""
    name: str
    confidence: float  # 0.0 to 1.0
    reliability: float  # 0.0 to 1.0 (how much to trust this source)
    weight: float = 1.0  # Relative importance
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BayesianUpdate:
    """Result of a Bayesian update."""
    prior: float
    likelihood: float
    posterior: float
    evidence: EvidenceSource
    update_timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ConfidenceAssessment:
    """Complete confidence assessment with Bayesian analysis."""
    final_confidence: float
    posterior_probability: float
    should_flag: bool
    threshold_used: float
    evidence_sources: List[EvidenceSource]
    bayesian_updates: List[BayesianUpdate]
    volatility_adjustment: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class BayesianConfidenceScorer:
    """
    Adaptive Bayesian confidence scoring system.
    
    Uses Bayesian inference to combine multiple evidence sources and update
    confidence as new information becomes available.
    """
    
    def __init__(self, 
                 base_threshold: float = 0.6,
                 odds_movement_sensitivity: float = 0.1):
        """
        Initialize the Bayesian confidence scorer.
        
        Args:
            base_threshold: Base threshold for flagging bets (0.6 = 60%)
            odds_movement_sensitivity: How much odds movement affects confidence
        """
        self.base_threshold = base_threshold
        self.odds_movement_sensitivity = odds_movement_sensitivity
        
        # Prior distributions for different evidence types
        self.evidence_priors = {
            "roberta_confidence": 0.5,  # Neutral prior for RoBERTa
            "rag_quality": 0.6,         # Slightly positive prior for RAG
            "odds_movement": 0.5,       # Neutral prior for odds
            "injury_intel": 0.7,        # Positive prior for injury info
            "sharp_money": 0.8,         # Strong prior for sharp money
            "public_betting": 0.4       # Negative prior for public betting
        }
        
        # Reliability weights for each evidence source
        self.source_reliability = {
            "roberta_confidence": 0.85,  # High reliability for trained model
            "rag_quality": 0.75,         # Good reliability for RAG
            "odds_movement": 0.90,       # Very high reliability for market data
            "injury_intel": 0.80,        # High reliability for injury data
            "sharp_money": 0.95,         # Highest reliability for sharp money
            "public_betting": 0.70       # Lower reliability for public data
        }
        
        logger.info(f"Initialized BayesianConfidenceScorer with threshold {base_threshold}")
    
    def calculate_likelihood(self, evidence: EvidenceSource) -> float:
        """
        Calculate likelihood P(Evidence|Hypothesis) for Bayesian updating.
        
        Args:
            evidence: Evidence source with confidence and reliability
            
        Returns:
            Likelihood value for Bayesian calculation
        """
        # Adjust evidence confidence based on reliability
        adjusted_confidence = evidence.confidence * evidence.reliability
        
        # Convert confidence to likelihood using logistic transformation
        # This ensures likelihood is between 0 and 1 and handles extreme values
        likelihood = 1 / (1 + math.exp(-5 * (adjusted_confidence - 0.5)))
        
        return likelihood
    
    def bayesian_update(self, prior: float, evidence: EvidenceSource) -> BayesianUpdate:
        """
        Perform Bayesian update: P(H|E) = P(E|H) * P(H) / P(E)
        
        Args:
            prior: Prior probability
            evidence: New evidence to incorporate
            
        Returns:
            BayesianUpdate with prior, likelihood, and posterior
        """
        likelihood = self.calculate_likelihood(evidence)
        
        # Calculate marginal likelihood P(E) using law of total probability
        # P(E) = P(E|H) * P(H) + P(E|¬H) * P(¬H)
        likelihood_not_h = 1 - likelihood  # P(E|¬H)
        marginal_likelihood = (likelihood * prior) + (likelihood_not_h * (1 - prior))
        
        # Avoid division by zero
        if marginal_likelihood == 0:
            marginal_likelihood = 1e-10
        
        # Calculate posterior using Bayes' theorem
        posterior = (likelihood * prior) / marginal_likelihood
        
        # Apply evidence weight
        if evidence.weight != 1.0:
            # Weight interpolation: weighted_posterior = weight * posterior + (1-weight) * prior
            weighted_posterior = evidence.weight * posterior + (1 - evidence.weight) * prior
            posterior = weighted_posterior
        
        return BayesianUpdate(
            prior=prior,
            likelihood=likelihood,
            posterior=posterior,
            evidence=evidence
        )
    
    def sequential_bayesian_updates(self, 
                                   initial_prior: float,
                                   evidence_list: List[EvidenceSource]) -> Tuple[float, List[BayesianUpdate]]:
        """
        Perform sequential Bayesian updates with multiple evidence sources.
        
        Args:
            initial_prior: Starting prior probability
            evidence_list: List of evidence sources to incorporate
            
        Returns:
            Tuple of (final_posterior, list_of_updates)
        """
        current_prior = initial_prior
        updates = []
        
        # Sort evidence by reliability (most reliable first)
        sorted_evidence = sorted(evidence_list, 
                               key=lambda e: e.reliability * e.weight, 
                               reverse=True)
        
        for evidence in sorted_evidence:
            update = self.bayesian_update(current_prior, evidence)
            updates.append(update)
            
            # Use posterior as prior for next update
            current_prior = update.posterior
            
            logger.debug(f"Bayesian update - {evidence.name}: "
                        f"prior={update.prior:.3f} -> posterior={update.posterior:.3f}")
        
        return current_prior, updates
    
    def calculate_volatility_adjustment(self, game_metadata: Dict[str, Any]) -> float:
        """
        Calculate volatility adjustment factor based on game characteristics.
        
        Args:
            game_metadata: Game metadata including league, season type, etc.
            
        Returns:
            Volatility adjustment factor (negative values reduce confidence)
        """
        adjustment = 0.0
        
        # Preseason penalty (smaller)
        if game_metadata.get("season_type") == "preseason":
            adjustment -= 0.08
            logger.debug("Applied preseason penalty: -0.08")
        
        # Playoff boost
        if game_metadata.get("season_type") == "playoffs":
            adjustment += 0.05
            logger.debug("Applied playoff boost: +0.05")
        
        # Back-to-back penalty
        if game_metadata.get("is_back_to_back", False):
            adjustment -= 0.03
            logger.debug("Applied back-to-back penalty: -0.03")
        
        # National TV game boost (more scrutiny = more reliable)
        if game_metadata.get("is_national_tv", False):
            adjustment += 0.02
            logger.debug("Applied national TV boost: +0.02")
        
        return adjustment
    
    def extract_roberta_evidence(self, roberta_result: Dict[str, Any]) -> EvidenceSource:
        """
        Extract evidence from RoBERTa confidence prediction.
        
        Args:
            roberta_result: Result from parlay_confidence_predictor
            
        Returns:
            EvidenceSource for Bayesian updating
        """
        confidence = roberta_result.get("max_confidence_score", 0.5)
        certainty = roberta_result.get("prediction_certainty", 0.5)
        
        # Use certainty as reliability measure
        reliability = self.source_reliability["roberta_confidence"] * certainty
        
        return EvidenceSource(
            name="roberta_confidence",
            confidence=confidence,
            reliability=reliability,
            weight=1.0,
            metadata={
                "predicted_confidence": roberta_result.get("predicted_confidence"),
                "certainty": certainty,
                "probabilities": roberta_result.get("confidence_probabilities", {})
            }
        )
    
    def extract_rag_evidence(self, rag_results: List[Dict[str, Any]]) -> EvidenceSource:
        """
        Extract evidence from RAG retrieval quality.
        
        Args:
            rag_results: RAG retrieval results with relevance scores
            
        Returns:
            EvidenceSource for Bayesian updating
        """
        if not rag_results:
            return EvidenceSource(
                name="rag_quality",
                confidence=0.3,  # Low confidence if no results
                reliability=0.5,
                weight=0.5,
                metadata={"num_results": 0}
            )
        
        # Calculate quality metrics
        relevance_scores = [r.get("score", 0.0) for r in rag_results]
        avg_relevance = np.mean(relevance_scores)
        max_relevance = max(relevance_scores)
        coverage = len([r for r in rag_results if r.get("score", 0.0) > 0.7])
        
        # Quality based on relevance and coverage
        quality_score = (avg_relevance * 0.6) + (max_relevance * 0.3) + (min(coverage/3, 1.0) * 0.1)
        
        # Reliability based on source diversity and quality
        unique_sources = len(set(r.get("metadata", {}).get("source", "") for r in rag_results))
        source_reliability = min(unique_sources / 3, 1.0)  # Better if multiple sources
        
        reliability = self.source_reliability["rag_quality"] * source_reliability
        
        return EvidenceSource(
            name="rag_quality",
            confidence=quality_score,
            reliability=reliability,
            weight=1.0,
            metadata={
                "num_results": len(rag_results),
                "avg_relevance": avg_relevance,
                "max_relevance": max_relevance,
                "coverage": coverage,
                "unique_sources": unique_sources
            }
        )
    
    def extract_odds_movement_evidence(self, odds_history: List[Dict[str, Any]]) -> EvidenceSource:
        """
        Extract evidence from real-time odds movement.
        
        Args:
            odds_history: Historical odds data from latency monitor
            
        Returns:
            EvidenceSource for Bayesian updating
        """
        if len(odds_history) < 2:
            return EvidenceSource(
                name="odds_movement",
                confidence=0.5,  # Neutral if no movement data
                reliability=0.5,
                weight=0.3,
                metadata={"movement_detected": False}
            )
        
        # Calculate odds movement patterns
        movements = []
        for i in range(1, len(odds_history)):
            prev_odds = odds_history[i-1].get("price_decimal", 1.0)
            curr_odds = odds_history[i].get("price_decimal", 1.0)
            
            if prev_odds > 0:
                movement = (curr_odds - prev_odds) / prev_odds
                movements.append(movement)
        
        if not movements:
            movement_strength = 0.0
        else:
            # Strong consistent movement is positive evidence
            avg_movement = abs(np.mean(movements))
            movement_consistency = 1 - np.std(movements) if len(movements) > 1 else 1.0
            movement_strength = avg_movement * movement_consistency
        
        # Convert movement to confidence (strong movement = higher confidence)
        confidence = 0.5 + (movement_strength * self.odds_movement_sensitivity)
        confidence = max(0.0, min(1.0, confidence))
        
        return EvidenceSource(
            name="odds_movement",
            confidence=confidence,
            reliability=self.source_reliability["odds_movement"],
            weight=0.8,  # High weight for market data
            metadata={
                "movement_detected": len(movements) > 0,
                "avg_movement": np.mean(movements) if movements else 0.0,
                "movement_strength": movement_strength,
                "num_observations": len(odds_history)
            }
        )
    
    def extract_contextual_evidence(self, reasoning_text: str) -> List[EvidenceSource]:
        """
        Extract contextual evidence from reasoning text.
        
        Args:
            reasoning_text: Parlay reasoning text to analyze
            
        Returns:
            List of EvidenceSource objects for contextual factors
        """
        evidence_sources = []
        text_lower = reasoning_text.lower()
        
        # Injury intelligence evidence
        injury_indicators = ["injury", "out", "questionable", "doubtful", "probable", "dtd"]
        injury_mentions = sum(1 for indicator in injury_indicators if indicator in text_lower)
        if injury_mentions > 0:
            confidence = min(0.5 + (injury_mentions * 0.1), 0.9)
            evidence_sources.append(EvidenceSource(
                name="injury_intel",
                confidence=confidence,
                reliability=self.source_reliability["injury_intel"],
                weight=1.2,  # High weight for injury info
                metadata={"mentions": injury_mentions}
            ))
        
        # Sharp money evidence
        sharp_indicators = ["sharp", "syndicate", "professional", "wise guy", "steam"]
        sharp_mentions = sum(1 for indicator in sharp_indicators if indicator in text_lower)
        if sharp_mentions > 0:
            confidence = min(0.6 + (sharp_mentions * 0.15), 0.95)
            evidence_sources.append(EvidenceSource(
                name="sharp_money",
                confidence=confidence,
                reliability=self.source_reliability["sharp_money"],
                weight=1.5,  # Very high weight for sharp money
                metadata={"mentions": sharp_mentions}
            ))
        
        # Public betting evidence (contrarian indicator)
        public_indicators = ["public", "casual", "square", "chalk", "popular"]
        public_mentions = sum(1 for indicator in public_indicators if indicator in text_lower)
        if public_mentions > 0:
            # High public betting = lower confidence (contrarian)
            confidence = max(0.1, 0.6 - (public_mentions * 0.1))
            evidence_sources.append(EvidenceSource(
                name="public_betting",
                confidence=confidence,
                reliability=self.source_reliability["public_betting"],
                weight=0.8,
                metadata={"mentions": public_mentions}
            ))
        
        return evidence_sources
    
    def calculate_dynamic_threshold(self, 
                                  base_threshold: float,
                                  game_metadata: Dict[str, Any],
                                  evidence_reliability: float) -> float:
        """
        Calculate dynamic threshold based on game context and evidence quality.
        
        Args:
            base_threshold: Base threshold value
            game_metadata: Game context information
            evidence_reliability: Average reliability of evidence sources
            
        Returns:
            Adjusted threshold for bet flagging
        """
        threshold = base_threshold
        
        # Adjust based on evidence reliability
        if evidence_reliability > 0.8:
            threshold -= 0.05  # Lower threshold for high-quality evidence
        elif evidence_reliability < 0.6:
            threshold += 0.05  # Higher threshold for low-quality evidence
        
        # Game context adjustments
        if game_metadata.get("season_type") == "preseason":
            threshold += 0.05  # Higher threshold for preseason games
        elif game_metadata.get("season_type") == "playoffs":
            threshold -= 0.03  # Lower threshold for playoff games
        
        # Ensure reasonable bounds
        threshold = max(0.3, min(0.8, threshold))
        
        return threshold
    
    def assess_confidence(self,
                         roberta_result: Optional[Dict[str, Any]] = None,
                         rag_results: Optional[List[Dict[str, Any]]] = None,
                         odds_history: Optional[List[Dict[str, Any]]] = None,
                         reasoning_text: str = "",
                         game_metadata: Optional[Dict[str, Any]] = None) -> ConfidenceAssessment:
        """
        Perform comprehensive Bayesian confidence assessment.
        
        Args:
            roberta_result: RoBERTa confidence prediction result
            rag_results: RAG retrieval results with relevance scores
            odds_history: Historical odds data from latency monitor
            reasoning_text: Parlay reasoning text for contextual analysis
            game_metadata: Game context information
            
        Returns:
            Complete ConfidenceAssessment with Bayesian analysis
        """
        if game_metadata is None:
            game_metadata = {}
        
        logger.info("Starting Bayesian confidence assessment")
        
        # Collect all evidence sources
        evidence_sources = []
        
        # RoBERTa evidence
        if roberta_result:
            evidence_sources.append(self.extract_roberta_evidence(roberta_result))
        
        # RAG evidence
        if rag_results:
            evidence_sources.append(self.extract_rag_evidence(rag_results))
        
        # Odds movement evidence
        if odds_history:
            evidence_sources.append(self.extract_odds_movement_evidence(odds_history))
        
        # Contextual evidence from reasoning text
        if reasoning_text:
            evidence_sources.extend(self.extract_contextual_evidence(reasoning_text))
        
        if not evidence_sources:
            logger.warning("No evidence sources available - using neutral assessment")
            return ConfidenceAssessment(
                final_confidence=0.5,
                posterior_probability=0.5,
                should_flag=True,
                threshold_used=self.base_threshold,
                evidence_sources=[],
                bayesian_updates=[],
                volatility_adjustment=0.0,
                metadata={"warning": "no_evidence_sources"}
            )
        
        # Calculate initial prior (average of evidence-specific priors)
        relevant_priors = [self.evidence_priors.get(evidence.name, 0.5) for evidence in evidence_sources]
        initial_prior = np.mean(relevant_priors)
        
        # Perform sequential Bayesian updates
        final_posterior, updates = self.sequential_bayesian_updates(initial_prior, evidence_sources)
        
        # Apply volatility adjustment
        volatility_adjustment = self.calculate_volatility_adjustment(game_metadata)
        adjusted_confidence = final_posterior + volatility_adjustment
        adjusted_confidence = max(0.0, min(1.0, adjusted_confidence))
        
        # Calculate dynamic threshold
        avg_reliability = np.mean([e.reliability for e in evidence_sources])
        dynamic_threshold = self.calculate_dynamic_threshold(
            self.base_threshold, game_metadata, avg_reliability
        )
        
        # Determine if bet should be flagged
        should_flag = adjusted_confidence < dynamic_threshold
        
        logger.info(f"Bayesian assessment complete - "
                   f"Posterior: {final_posterior:.3f}, "
                   f"Adjusted: {adjusted_confidence:.3f}, "
                   f"Threshold: {dynamic_threshold:.3f}, "
                   f"Flag: {should_flag}")
        
        return ConfidenceAssessment(
            final_confidence=adjusted_confidence,
            posterior_probability=final_posterior,
            should_flag=should_flag,
            threshold_used=dynamic_threshold,
            evidence_sources=evidence_sources,
            bayesian_updates=updates,
            volatility_adjustment=volatility_adjustment,
            metadata={
                "initial_prior": initial_prior,
                "num_evidence_sources": len(evidence_sources),
                "avg_reliability": avg_reliability,
                "game_context": game_metadata
            }
        )
    
    def get_assessment_summary(self, assessment: ConfidenceAssessment) -> Dict[str, Any]:
        """
        Generate a human-readable summary of the confidence assessment.
        
        Args:
            assessment: ConfidenceAssessment to summarize
            
        Returns:
            Dictionary with summary information
        """
        evidence_summary = {}
        for evidence in assessment.evidence_sources:
            evidence_summary[evidence.name] = {
                "confidence": evidence.confidence,
                "reliability": evidence.reliability,
                "weight": evidence.weight
            }
        
        update_summary = []
        for update in assessment.bayesian_updates:
            update_summary.append({
                "evidence": update.evidence.name,
                "prior": update.prior,
                "posterior": update.posterior,
                "improvement": update.posterior - update.prior
            })
        
        recommendation = "PROCEED" if not assessment.should_flag else "FLAG - INSUFFICIENT CONFIDENCE"
        
        return {
            "recommendation": recommendation,
            "final_confidence": assessment.final_confidence,
            "posterior_probability": assessment.posterior_probability,
            "threshold_used": assessment.threshold_used,
            "confidence_vs_threshold": assessment.final_confidence - assessment.threshold_used,
            "volatility_adjustment": assessment.volatility_adjustment,
            "evidence_sources": evidence_summary,
            "bayesian_updates": update_summary,
            "metadata": assessment.metadata
        }


def main():
    """Main function for testing the Bayesian confidence scorer."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🎯 Bayesian Confidence Scorer - JIRA-020A")
    print("=" * 50)
    
    # Initialize scorer
    scorer = BayesianConfidenceScorer()
    
    # Test with sample data
    sample_roberta_result = {
        "predicted_confidence": "high_confidence",
        "max_confidence_score": 0.82,
        "prediction_certainty": 0.75,
        "confidence_probabilities": {"low_confidence": 0.18, "high_confidence": 0.82}
    }
    
    sample_rag_results = [
        {"score": 0.87, "metadata": {"source": "the_ringer"}},
        {"score": 0.79, "metadata": {"source": "action_network"}},
        {"score": 0.73, "metadata": {"source": "nba_com"}}
    ]
    
    sample_odds_history = [
        {"price_decimal": 1.91, "timestamp": "2025-01-01T10:00:00Z"},
        {"price_decimal": 1.95, "timestamp": "2025-01-01T11:00:00Z"},
        {"price_decimal": 1.97, "timestamp": "2025-01-01T12:00:00Z"}
    ]
    
    sample_reasoning = """
    Lakers -3.5 looks strong tonight. LeBron is questionable but expected to play.
    Sharp money moved the line from -2.5 to -3.5 despite 65% public on the underdog.
    Professional bettors are backing the Lakers heavily.
    """
    
    sample_game_metadata = {
        "is_summer_league": False,
        "season_type": "regular",
        "is_back_to_back": False,
        "is_national_tv": True
    }
    
    print("📊 Running Bayesian confidence assessment...")
    
    # Perform assessment
    assessment = scorer.assess_confidence(
        roberta_result=sample_roberta_result,
        rag_results=sample_rag_results,
        odds_history=sample_odds_history,
        reasoning_text=sample_reasoning,
        game_metadata=sample_game_metadata
    )
    
    # Get summary
    summary = scorer.get_assessment_summary(assessment)
    
    print(f"\n🎯 Assessment Results:")
    print(f"Recommendation: {summary['recommendation']}")
    print(f"Final Confidence: {summary['final_confidence']:.3f}")
    print(f"Posterior Probability: {summary['posterior_probability']:.3f}")
    print(f"Threshold Used: {summary['threshold_used']:.3f}")
    print(f"Margin: {summary['confidence_vs_threshold']:+.3f}")
    print(f"Volatility Adjustment: {summary['volatility_adjustment']:+.3f}")
    
    print(f"\n📈 Evidence Sources:")
    for name, evidence in summary['evidence_sources'].items():
        print(f"  {name}: confidence={evidence['confidence']:.3f}, "
              f"reliability={evidence['reliability']:.3f}, weight={evidence['weight']:.1f}")
    
        print(f"\n🔄 Bayesian Updates:")
        for i, update in enumerate(summary['bayesian_updates'], 1):
            print(f"  {i}. {update['evidence']}: {update['prior']:.3f} → {update['posterior']:.3f} "
                  f"(Δ{update['improvement']:+.3f})")
        
        # Test Playoff scenario
        print(f"\n🏀 Testing Playoff scenario...")
        playoff_metadata = {"season_type": "playoffs", "is_national_tv": True}
        
        playoff_assessment = scorer.assess_confidence(
            roberta_result=sample_roberta_result,
            rag_results=sample_rag_results,
            reasoning_text=sample_reasoning,
            game_metadata=playoff_metadata
        )
        
        playoff_summary = scorer.get_assessment_summary(playoff_assessment)
        print(f"Playoff Recommendation: {playoff_summary['recommendation']}")
        print(f"Playoff Confidence: {playoff_summary['final_confidence']:.3f}")
        print(f"Volatility Adjustment: {playoff_summary['volatility_adjustment']:.3f}")
    
    print(f"\n✅ JIRA-020A Bayesian Confidence Scorer Complete!")
    print(f"🎯 Ready for integration with enhanced parlay system")


if __name__ == "__main__":
    main()
