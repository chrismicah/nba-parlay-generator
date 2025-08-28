#!/usr/bin/env python3
"""
Bayesian Enhanced Parlay Strategist - JIRA-020A Integration

Integrates the Bayesian confidence scoring system with the enhanced parlay strategist
to provide adaptive confidence assessment using:
- RoBERTa confidence scores from JIRA-019
- RAG retrieval quality metrics  
- Real-time odds movement from latency monitor
- Summer League volatility weighting
- Threshold-based bet flagging system
"""

import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

# Import base strategist and few-shot capabilities
from tools.enhanced_parlay_strategist_agent import (
    FewShotEnhancedParlayStrategistAgent, ParlayRecommendation, ParlayReasoning
)

# Import Bayesian confidence system
from tools.bayesian_confidence_scorer import (
    BayesianConfidenceScorer, ConfidenceAssessment, EvidenceSource
)

# Import confidence predictor for RoBERTa integration
try:
    from tools.parlay_confidence_predictor import ParlayConfidencePredictor
    HAS_ROBERTA = True
except ImportError:
    HAS_ROBERTA = False
    logging.warning("RoBERTa confidence predictor not available")

# Import RAG retrieval system
try:
    from tools.embedder import SportsKnowledgeEmbedder
    HAS_RAG = True
except ImportError:
    HAS_RAG = False
    logging.warning("RAG retrieval system not available")

logger = logging.getLogger(__name__)


@dataclass
class BayesianParlayRecommendation:
    """Enhanced parlay recommendation with Bayesian confidence assessment."""
    # Base recommendation
    base_recommendation: ParlayRecommendation
    
    # Bayesian assessment
    bayesian_assessment: ConfidenceAssessment
    
    # Enhanced metadata
    confidence_breakdown: Dict[str, Any]
    risk_assessment: str
    bet_recommendation: str
    alert_status: str  # "PROCEED", "CAUTION", "FLAG"
    
    # Timestamps
    assessment_timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "base_recommendation": asdict(self.base_recommendation),
            "bayesian_assessment": {
                "final_confidence": self.bayesian_assessment.final_confidence,
                "posterior_probability": self.bayesian_assessment.posterior_probability,
                "should_flag": self.bayesian_assessment.should_flag,
                "threshold_used": self.bayesian_assessment.threshold_used,
                "volatility_adjustment": self.bayesian_assessment.volatility_adjustment,
                "evidence_sources": [asdict(e) for e in self.bayesian_assessment.evidence_sources],
                "bayesian_updates": [asdict(u) for u in self.bayesian_assessment.bayesian_updates],
                "metadata": self.bayesian_assessment.metadata
            },
            "confidence_breakdown": self.confidence_breakdown,
            "risk_assessment": self.risk_assessment,
            "bet_recommendation": self.bet_recommendation,
            "alert_status": self.alert_status,
            "assessment_timestamp": self.assessment_timestamp
        }


class BayesianEnhancedParlayStrategist:
    """
    Enhanced parlay strategist with Bayesian confidence assessment.
    
    Combines few-shot learning capabilities with adaptive Bayesian confidence
    scoring to provide comprehensive parlay recommendations.
    """
    
    def __init__(self,
                 use_injury_classifier: bool = True,
                 use_roberta_confidence: bool = True,
                 use_rag_retrieval: bool = True,
                 bayesian_threshold: float = 0.6):
        """
        Initialize the Bayesian enhanced parlay strategist.
        
        Args:
            use_injury_classifier: Whether to use injury classification
            use_roberta_confidence: Whether to use RoBERTa confidence prediction
            use_rag_retrieval: Whether to use RAG retrieval for context
            bayesian_threshold: Threshold for Bayesian confidence flagging
        """
        # Initialize base strategist with few-shot capabilities
        self.base_strategist = FewShotEnhancedParlayStrategistAgent(
            use_injury_classifier=use_injury_classifier
        )
        
        # Initialize Bayesian confidence scorer
        self.bayesian_scorer = BayesianConfidenceScorer(
            base_threshold=bayesian_threshold
        )
        
        # Initialize optional components
        self.roberta_predictor = None
        self.rag_embedder = None
        self.use_roberta_confidence = use_roberta_confidence and HAS_ROBERTA
        self.use_rag_retrieval = use_rag_retrieval and HAS_RAG
        
        # Initialize RoBERTa predictor if available
        if self.use_roberta_confidence:
            try:
                self.roberta_predictor = ParlayConfidencePredictor()
                logger.info("RoBERTa confidence predictor initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize RoBERTa predictor: {e}")
                self.use_roberta_confidence = False
        
        # Initialize RAG embedder if available
        if self.use_rag_retrieval:
            try:
                self.rag_embedder = SportsKnowledgeEmbedder()
                logger.info("RAG retrieval system initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize RAG system: {e}")
                self.use_rag_retrieval = False
        
        logger.info(f"Initialized BayesianEnhancedParlayStrategist - "
                   f"RoBERTa: {self.use_roberta_confidence}, "
                   f"RAG: {self.use_rag_retrieval}")
    
    def get_roberta_confidence(self, reasoning_text: str) -> Optional[Dict[str, Any]]:
        """
        Get RoBERTa confidence prediction for reasoning text.
        
        Args:
            reasoning_text: Parlay reasoning text
            
        Returns:
            RoBERTa confidence result or None
        """
        if not self.use_roberta_confidence or not self.roberta_predictor:
            return None
        
        try:
            if not self.roberta_predictor.is_loaded:
                self.roberta_predictor.load_model()
            
            result = self.roberta_predictor.predict(reasoning_text)
            logger.debug(f"RoBERTa confidence: {result['max_confidence_score']:.3f}")
            return result
            
        except Exception as e:
            logger.error(f"RoBERTa confidence prediction failed: {e}")
            return None
    
    def get_rag_retrieval_quality(self, 
                                 query: str,
                                 game_context: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """
        Get RAG retrieval results and quality metrics.
        
        Args:
            query: Query text for retrieval
            game_context: Game context for filtering
            
        Returns:
            RAG retrieval results or None
        """
        if not self.use_rag_retrieval or not self.rag_embedder:
            return None
        
        try:
            # Extract team names for filtering
            home_team = game_context.get("home_team", "")
            away_team = game_context.get("away_team", "")
            
            # Perform retrieval with team filtering
            results = self.rag_embedder.search_similar(
                query=query,
                limit=5,
                metadata_filter={"teams": [home_team, away_team]}
            )
            
            # Add relevance scores (mock implementation - would use actual scoring)
            for result in results:
                # Simple relevance scoring based on similarity and source quality
                base_score = result.get("similarity", 0.0)
                source = result.get("metadata", {}).get("source", "")
                
                # Source quality boost
                quality_multiplier = {
                    "mathletics": 1.1,
                    "logic_of_sports_betting": 1.08,
                    "the_ringer": 1.05,
                    "action_network": 1.03,
                    "nba_com": 1.0
                }.get(source.lower(), 0.95)
                
                result["score"] = base_score * quality_multiplier
            
            logger.debug(f"RAG retrieval: {len(results)} results, "
                        f"avg score: {sum(r['score'] for r in results)/len(results):.3f}")
            return results
            
        except Exception as e:
            logger.error(f"RAG retrieval failed: {e}")
            return None
    
    def simulate_odds_movement(self, game_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Simulate odds movement data (would be replaced with real latency monitor data).
        
        Args:
            game_context: Game context information
            
        Returns:
            Simulated odds history
        """
        # Mock odds movement data - in production, this would come from the latency monitor
        base_odds = game_context.get("odds", 1.91)
        
        # Simulate some realistic movement
        movement_patterns = [
            base_odds,
            base_odds + 0.02,  # Slight increase
            base_odds + 0.04,  # More movement
            base_odds + 0.01   # Settle
        ]
        
        odds_history = []
        for i, odds in enumerate(movement_patterns):
            odds_history.append({
                "price_decimal": odds,
                "timestamp": f"2025-01-01T{10+i}:00:00Z",
                "bookmaker": "DraftKings",
                "market": "h2h"
            })
        
        return odds_history
    
    def extract_game_metadata(self, game_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract game metadata for Bayesian assessment.
        
        Args:
            game_context: Game context information
            
        Returns:
            Formatted game metadata
        """
        return {
            "season_type": game_context.get("season_type", "regular").lower(),
            "is_back_to_back": game_context.get("is_back_to_back", False),
            "is_national_tv": game_context.get("is_national_tv", False),
            "home_team": game_context.get("home_team", ""),
            "away_team": game_context.get("away_team", ""),
            "game_importance": game_context.get("importance", "regular")
        }
    
    def generate_risk_assessment(self, assessment: ConfidenceAssessment) -> str:
        """
        Generate human-readable risk assessment.
        
        Args:
            assessment: Bayesian confidence assessment
            
        Returns:
            Risk assessment string
        """
        confidence = assessment.final_confidence
        volatility = abs(assessment.volatility_adjustment)
        
        if confidence >= 0.8:
            if volatility < 0.05:
                return "LOW RISK - High confidence with stable conditions"
            else:
                return "MODERATE RISK - High confidence but volatile conditions"
        elif confidence >= 0.6:
            if volatility < 0.05:
                return "MODERATE RISK - Adequate confidence with stable conditions"
            else:
                return "HIGH RISK - Moderate confidence with volatile conditions"
        else:
            return "HIGH RISK - Low confidence, recommend avoiding"
    
    def generate_bet_recommendation(self, assessment: ConfidenceAssessment) -> Tuple[str, str]:
        """
        Generate bet recommendation and alert status.
        
        Args:
            assessment: Bayesian confidence assessment
            
        Returns:
            Tuple of (bet_recommendation, alert_status)
        """
        confidence = assessment.final_confidence
        should_flag = assessment.should_flag
        
        if should_flag:
            return ("AVOID - Insufficient confidence for betting", "FLAG")
        
        if confidence >= 0.85:
            return ("STRONG BET - High confidence, consider increased stake", "PROCEED")
        elif confidence >= 0.7:
            return ("GOOD BET - Solid confidence, standard stake recommended", "PROCEED")
        elif confidence >= 0.6:
            return ("MARGINAL BET - Borderline confidence, reduce stake", "CAUTION")
        else:
            return ("AVOID - Low confidence", "FLAG")
    
    def generate_confidence_breakdown(self, assessment: ConfidenceAssessment) -> Dict[str, Any]:
        """
        Generate detailed confidence breakdown.
        
        Args:
            assessment: Bayesian confidence assessment
            
        Returns:
            Confidence breakdown dictionary
        """
        evidence_breakdown = {}
        for evidence in assessment.evidence_sources:
            evidence_breakdown[evidence.name] = {
                "confidence": evidence.confidence,
                "reliability": evidence.reliability,
                "weight": evidence.weight,
                "contribution": evidence.confidence * evidence.reliability * evidence.weight
            }
        
        update_summary = []
        for update in assessment.bayesian_updates:
            update_summary.append({
                "evidence": update.evidence.name,
                "prior_to_posterior": f"{update.prior:.3f} → {update.posterior:.3f}",
                "improvement": update.posterior - update.prior
            })
        
        return {
            "final_confidence": assessment.final_confidence,
            "posterior_probability": assessment.posterior_probability,
            "threshold_comparison": {
                "threshold": assessment.threshold_used,
                "margin": assessment.final_confidence - assessment.threshold_used,
                "meets_threshold": not assessment.should_flag
            },
            "volatility_impact": {
                "adjustment": assessment.volatility_adjustment,
                "factors": assessment.metadata.get("game_context", {})
            },
            "evidence_contributions": evidence_breakdown,
            "bayesian_progression": update_summary,
            "reliability_metrics": {
                "num_sources": len(assessment.evidence_sources),
                "avg_reliability": sum(e.reliability for e in assessment.evidence_sources) / max(len(assessment.evidence_sources), 1),
                "evidence_diversity": len(set(e.name for e in assessment.evidence_sources))
            }
        }
    
    def generate_enhanced_recommendation(self,
                                       games_data: List[Dict[str, Any]],
                                       market_analysis: Optional[Dict[str, Any]] = None,
                                       user_preferences: Optional[Dict[str, Any]] = None) -> BayesianParlayRecommendation:
        """
        Generate enhanced parlay recommendation with Bayesian confidence assessment.
        
        Args:
            games_data: List of game data for parlay building
            market_analysis: Optional market analysis data
            user_preferences: Optional user preferences
            
        Returns:
            BayesianParlayRecommendation with full assessment
        """
        logger.info("Generating Bayesian enhanced parlay recommendation")
        
        # Generate base recommendation using few-shot enhanced strategist
        base_recommendation = self.base_strategist.generate_parlay_recommendation(
            games_data=games_data,
            market_analysis=market_analysis,
            user_preferences=user_preferences
        )
        
        # Extract reasoning text for analysis
        reasoning_text = base_recommendation.reasoning.detailed_analysis
        
        # Build comprehensive context from games data
        game_context = {}
        if games_data:
            first_game = games_data[0]
            game_context = {
                "home_team": first_game.get("home_team", ""),
                "away_team": first_game.get("away_team", ""),
                "league": first_game.get("league", "NBA"),
                "season_type": first_game.get("season_type", "regular"),
                "is_back_to_back": first_game.get("is_back_to_back", False),
                "is_national_tv": first_game.get("is_national_tv", False),
                "odds": first_game.get("odds", 1.91)
            }
        
        # Get RoBERTa confidence assessment
        roberta_result = self.get_roberta_confidence(reasoning_text)
        
        # Build RAG query from reasoning and game context
        rag_query = f"Analysis for {game_context.get('away_team', '')} vs {game_context.get('home_team', '')} betting"
        rag_results = self.get_rag_retrieval_quality(rag_query, game_context)
        
        # Simulate odds movement (would be real data in production)
        odds_history = self.simulate_odds_movement(game_context)
        
        # Extract game metadata
        game_metadata = self.extract_game_metadata(game_context)
        
        # Perform Bayesian confidence assessment
        bayesian_assessment = self.bayesian_scorer.assess_confidence(
            roberta_result=roberta_result,
            rag_results=rag_results,
            odds_history=odds_history,
            reasoning_text=reasoning_text,
            game_metadata=game_metadata
        )
        
        # Generate enhanced analysis
        confidence_breakdown = self.generate_confidence_breakdown(bayesian_assessment)
        risk_assessment = self.generate_risk_assessment(bayesian_assessment)
        bet_recommendation, alert_status = self.generate_bet_recommendation(bayesian_assessment)
        
        # Create enhanced recommendation
        enhanced_recommendation = BayesianParlayRecommendation(
            base_recommendation=base_recommendation,
            bayesian_assessment=bayesian_assessment,
            confidence_breakdown=confidence_breakdown,
            risk_assessment=risk_assessment,
            bet_recommendation=bet_recommendation,
            alert_status=alert_status,
            assessment_timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        logger.info(f"Enhanced recommendation complete - "
                   f"Confidence: {bayesian_assessment.final_confidence:.3f}, "
                   f"Status: {alert_status}")
        
        return enhanced_recommendation
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system status.
        
        Returns:
            System status information
        """
        return {
            "base_strategist": {
                "few_shot_enabled": self.base_strategist.few_shot_enabled,
                "examples_loaded": len(self.base_strategist.few_shot_examples) if self.base_strategist.few_shot_enabled else 0,
                "injury_classifier": self.base_strategist.injury_classifier is not None
            },
            "bayesian_scorer": {
                "threshold": self.bayesian_scorer.base_threshold,
                "evidence_types": len(self.bayesian_scorer.evidence_priors)
            },
            "roberta_confidence": {
                "enabled": self.use_roberta_confidence,
                "available": HAS_ROBERTA,
                "loaded": self.roberta_predictor.is_loaded if self.roberta_predictor else False
            },
            "rag_retrieval": {
                "enabled": self.use_rag_retrieval,
                "available": HAS_RAG,
                "initialized": self.rag_embedder is not None
            }
        }


def main():
    """Main function for testing the Bayesian enhanced strategist."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🎯 Bayesian Enhanced Parlay Strategist - JIRA-020A Integration")
    print("=" * 60)
    
    # Initialize strategist
    strategist = BayesianEnhancedParlayStrategist(
        use_injury_classifier=False,  # Disable for demo
        use_roberta_confidence=False,  # Disable for demo (no model available)
        use_rag_retrieval=False       # Disable for demo (no vector store)
    )
    
    # Show system status
    status = strategist.get_system_status()
    print("📊 System Status:")
    print(f"  Base Strategist: Few-shot enabled: {status['base_strategist']['few_shot_enabled']}")
    print(f"  Bayesian Scorer: Threshold: {status['bayesian_scorer']['threshold']}")
    print(f"  RoBERTa: Enabled: {status['roberta_confidence']['enabled']}")
    print(f"  RAG: Enabled: {status['rag_retrieval']['enabled']}")
    
    # Create sample game data
    sample_games = [
        {
            "home_team": "Lakers",
            "away_team": "Warriors",
            "league": "NBA",
            "season_type": "regular",
            "is_national_tv": True,
            "odds": 1.91,
            "spread": -3.5,
            "total": 225.5
        },
        {
            "home_team": "Celtics", 
            "away_team": "Heat",
            "league": "NBA",
            "season_type": "regular",
            "is_back_to_back": True,
            "odds": 1.65,
            "spread": -5.5,
            "total": 218.0
        }
    ]
    
    print(f"\n🏀 Generating enhanced parlay recommendation...")
    print(f"Games: {sample_games[0]['away_team']} @ {sample_games[0]['home_team']}, "
          f"{sample_games[1]['away_team']} @ {sample_games[1]['home_team']}")
    
    # Generate recommendation
    recommendation = strategist.generate_enhanced_recommendation(
        games_data=sample_games,
        market_analysis={"trend": "favorites_performing_well"},
        user_preferences={"risk_tolerance": "moderate"}
    )
    
    # Display results
    print(f"\n🎯 Enhanced Recommendation Results:")
    print(f"Alert Status: {recommendation.alert_status}")
    print(f"Bet Recommendation: {recommendation.bet_recommendation}")
    print(f"Risk Assessment: {recommendation.risk_assessment}")
    
    print(f"\n📈 Confidence Analysis:")
    breakdown = recommendation.confidence_breakdown
    print(f"Final Confidence: {breakdown['final_confidence']:.3f}")
    print(f"Posterior Probability: {breakdown['posterior_probability']:.3f}")
    print(f"Threshold: {breakdown['threshold_comparison']['threshold']:.3f}")
    print(f"Margin: {breakdown['threshold_comparison']['margin']:+.3f}")
    print(f"Meets Threshold: {breakdown['threshold_comparison']['meets_threshold']}")
    
    print(f"\n🔬 Evidence Analysis:")
    print(f"Evidence Sources: {breakdown['reliability_metrics']['num_sources']}")
    print(f"Average Reliability: {breakdown['reliability_metrics']['avg_reliability']:.3f}")
    
    if breakdown['evidence_contributions']:
        print(f"Top Evidence:")
        for name, contrib in breakdown['evidence_contributions'].items():
            print(f"  {name}: confidence={contrib['confidence']:.3f}, "
                  f"reliability={contrib['reliability']:.3f}")
    
    print(f"\n⚖️ Volatility Impact:")
    vol_impact = breakdown['volatility_impact']
    print(f"Adjustment: {vol_impact['adjustment']:+.3f}")
    print(f"Game Factors: {vol_impact['factors']}")
    
    # Test Summer League scenario
    print(f"\n🏀 Testing Summer League scenario...")
    summer_games = [
        {
            "home_team": "Lakers",
            "away_team": "Warriors", 
            "league": "Summer",
            "season_type": "summer",
            "odds": 2.10
        }
    ]
    
    summer_rec = strategist.generate_enhanced_recommendation(summer_games)
    print(f"Summer League Alert Status: {summer_rec.alert_status}")
    print(f"Summer League Confidence: {summer_rec.confidence_breakdown['final_confidence']:.3f}")
    print(f"Volatility Penalty: {summer_rec.confidence_breakdown['volatility_impact']['adjustment']:.3f}")
    
    print(f"\n✅ JIRA-020A Bayesian Enhanced Parlay Strategist Complete!")
    print(f"🎯 Adaptive confidence scoring with Bayesian methods successfully integrated")


if __name__ == "__main__":
    main()
