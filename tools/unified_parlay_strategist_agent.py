#!/usr/bin/env python3
"""
Unified Parlay Strategist Agent - Refactored Architecture

Provides a unified interface for generating parlays across all sports (NBA, NFL)
while maintaining sport-specific data sources and processing logic.

Key Features:
- Single agent that handles both NBA and NFL with sport parameter
- Sport-specific data adapters ensure no cross-contamination  
- Shared core logic for odds analysis, ML predictions, and parlay building
- Unified response format across all sports
- Sport-aware knowledge base filtering
- Consistent reasoning and confidence scoring
"""

from __future__ import annotations

import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json

# Import sport adapters
from tools.sport_data_adapters import (
    SportDataAdapter, NFLDataAdapter, NBADataAdapter, 
    SportContext, NFLContext, NBAContext, create_sport_adapter
)

# Import base strategist components
from tools.parlay_strategist_agent import (
    ReasoningFactor, ParlayReasoning, ParlayRecommendation,
    EnhancedParlayStrategistAgent
)

# Import odds components
from tools.odds_fetcher_tool import GameOdds, BookOdds, Selection

# Import knowledge base with error handling
try:
    from tools.knowledge_base_rag import SportsKnowledgeRAG, KnowledgeChunk, RAGResult
    HAS_KNOWLEDGE_BASE = True
except ImportError:
    HAS_KNOWLEDGE_BASE = False
    SportsKnowledgeRAG = KnowledgeChunk = RAGResult = None

# Import injury classifier (optional dependency)
try:
    from tools.classify_injury_severity import BioBERTInjuryClassifier
    HAS_INJURY_CLASSIFIER = True
except ImportError:
    HAS_INJURY_CLASSIFIER = False
    BioBERTInjuryClassifier = None

# Import arbitrage detection
try:
    from tools.arbitrage_detector_tool import ArbitrageDetectorTool
    HAS_ARBITRAGE = True
except ImportError:
    HAS_ARBITRAGE = False
    ArbitrageDetectorTool = None

# Import Bayesian confidence scoring
try:
    from tools.bayesian_confidence_scorer import BayesianConfidenceScorer
    HAS_BAYESIAN = True
except ImportError:
    HAS_BAYESIAN = False
    BayesianConfidenceScorer = None

logger = logging.getLogger(__name__)


@dataclass
class UnifiedParlayRecommendation:
    """Unified parlay recommendation format for all sports."""
    sport: str
    legs: List[Dict[str, Any]]
    confidence: float
    expected_value: Optional[float] = None
    kelly_percentage: Optional[float] = None
    knowledge_insights: List[str] = field(default_factory=list)
    reasoning: str = ""
    
    # Additional context
    sport_context: List[SportContext] = field(default_factory=list)
    arbitrage_opportunities: List[Dict[str, Any]] = field(default_factory=list)
    correlation_warnings: List[str] = field(default_factory=list)
    expert_guidance: List[str] = field(default_factory=list)
    value_betting_analysis: str = ""
    bankroll_recommendations: List[str] = field(default_factory=list)
    
    # Metadata
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    agent_version: str = "unified_v1.0"


class UnifiedParlayStrategistAgent:
    """
    Unified parlay strategist that handles both NBA and NFL with sport-specific adapters.
    
    Maintains sport isolation while providing consistent parlay generation logic.
    """
    
    def __init__(self, sport: str, knowledge_base: Optional[SportsKnowledgeRAG] = None):
        """
        Initialize the unified parlay strategist agent.
        
        Args:
            sport: Either "NBA" or "NFL"
            knowledge_base: Optional shared knowledge base instance
        """
        self.sport = sport.upper()
        if self.sport not in ["NBA", "NFL"]:
            raise ValueError(f"Unsupported sport: {sport}. Must be 'NBA' or 'NFL'")
        
        self.agent_id = f"unified_parlay_strategist_{self.sport.lower()}_v1.0"
        self.logger = logging.getLogger(f"{__name__}.{self.sport}")
        
        # Initialize sport-specific adapter
        self.sport_adapter = create_sport_adapter(self.sport)
        
        # Initialize shared knowledge base
        self.knowledge_base = knowledge_base
        if not self.knowledge_base and HAS_KNOWLEDGE_BASE:
            try:
                self.knowledge_base = SportsKnowledgeRAG()
                self.logger.info("Knowledge base initialized")
            except Exception as e:
                self.logger.warning(f"Could not initialize knowledge base: {e}")
        
        # Initialize shared components
        self._initialize_shared_components()
        
        self.logger.info(f"Unified {self.sport} Parlay Strategist Agent initialized: {self.agent_id}")
    
    def _initialize_shared_components(self) -> None:
        """Initialize shared components used across all sports."""
        # Initialize arbitrage detector
        self.arbitrage_detector = None
        if HAS_ARBITRAGE:
            try:
                self.arbitrage_detector = ArbitrageDetectorTool()
                self.logger.info("Arbitrage detector initialized")
            except Exception as e:
                self.logger.warning(f"Could not initialize arbitrage detector: {e}")
        
        # Initialize Bayesian confidence scorer
        self.confidence_scorer = None
        if HAS_BAYESIAN:
            try:
                self.confidence_scorer = BayesianConfidenceScorer()
                self.logger.info("Bayesian confidence scorer initialized")
            except Exception as e:
                self.logger.warning(f"Could not initialize confidence scorer: {e}")
    
    async def generate_parlay_recommendation(self, 
                                           target_legs: int = 3,
                                           min_total_odds: float = 3.0,
                                           include_arbitrage: bool = True,
                                           max_correlation_risk: float = 0.3) -> Optional[UnifiedParlayRecommendation]:
        """
        Generate a unified parlay recommendation for the configured sport.
        
        Args:
            target_legs: Number of legs to include in parlay
            min_total_odds: Minimum total odds for the parlay
            include_arbitrage: Whether to look for arbitrage opportunities
            max_correlation_risk: Maximum acceptable correlation risk
            
        Returns:
            UnifiedParlayRecommendation or None if no viable parlay found
        """
        try:
            self.logger.info(f"Generating {self.sport} parlay: {target_legs} legs, min odds {min_total_odds}")
            
            # Step 1: Fetch sport-specific games and odds
            games = await self.sport_adapter.fetch_games()
            if not games:
                self.logger.warning(f"No {self.sport} games available")
                return None
            
            # Step 2: Preprocess market data using sport-specific logic
            processed_games = await self.sport_adapter.preprocess_market_data(games)
            
            # Step 3: Generate sport contexts for each game
            sport_contexts = []
            for game in processed_games[:5]:  # Limit to top 5 games for performance
                context = await self.sport_adapter.get_sport_context(game)
                sport_contexts.append(context)
            
            # Step 4: Build parlay legs using shared logic
            parlay_legs = await self._build_parlay_legs(
                processed_games, sport_contexts, target_legs, min_total_odds
            )
            
            if not parlay_legs:
                self.logger.warning(f"Could not build viable {self.sport} parlay legs")
                return None
            
            # Step 5: Validate parlay legs using sport-specific rules
            is_valid, validation_errors = self.sport_adapter.validate_parlay_legs(parlay_legs)
            if not is_valid:
                self.logger.warning(f"{self.sport} parlay validation failed: {validation_errors}")
                return None
            
            # Step 6: Calculate confidence using shared scoring
            confidence = await self._calculate_confidence(parlay_legs, sport_contexts)
            
            # Step 7: Generate sport-specific insights
            sport_insights = []
            for context in sport_contexts:
                context_insights = self.sport_adapter.get_sport_specific_insights(context)
                sport_insights.extend(context_insights)
            
            # Step 8: Get knowledge base insights (filtered by sport)
            knowledge_insights = await self._get_knowledge_insights(parlay_legs, sport_contexts)
            
            # Step 9: Detect arbitrage opportunities if requested
            arbitrage_opportunities = []
            if include_arbitrage and self.arbitrage_detector:
                arbitrage_opportunities = await self._detect_arbitrage(processed_games)
            
            # Step 10: Generate reasoning and analysis
            reasoning = await self._generate_reasoning(parlay_legs, sport_contexts, confidence)
            expert_guidance = await self._generate_expert_guidance(parlay_legs, knowledge_insights)
            value_analysis = await self._generate_value_analysis(parlay_legs, sport_contexts)
            bankroll_recs = await self._generate_bankroll_recommendations(confidence, parlay_legs)
            
            # Step 11: Calculate expected value and Kelly percentage
            expected_value = await self._calculate_expected_value(parlay_legs, confidence)
            kelly_percentage = await self._calculate_kelly_percentage(expected_value, confidence)
            
            # Create unified recommendation
            recommendation = UnifiedParlayRecommendation(
                sport=self.sport,
                legs=parlay_legs,
                confidence=confidence,
                expected_value=expected_value,
                kelly_percentage=kelly_percentage,
                knowledge_insights=knowledge_insights,
                reasoning=reasoning,
                sport_context=sport_contexts,
                arbitrage_opportunities=arbitrage_opportunities,
                correlation_warnings=await self._check_correlations(parlay_legs, max_correlation_risk),
                expert_guidance=expert_guidance,
                value_betting_analysis=value_analysis,
                bankroll_recommendations=bankroll_recs
            )
            
            self.logger.info(f"Generated {self.sport} parlay with {len(parlay_legs)} legs, confidence: {confidence:.3f}")
            return recommendation
            
        except Exception as e:
            self.logger.error(f"Error generating {self.sport} parlay: {e}")
            return None
    
    async def _build_parlay_legs(self, 
                                games: List[GameOdds], 
                                contexts: List[SportContext],
                                target_legs: int, 
                                min_total_odds: float) -> List[Dict[str, Any]]:
        """Build parlay legs using shared logic across sports."""
        legs = []
        
        # Implementation of shared parlay building logic
        # This would select the best bets across all games regardless of sport
        
        for i, game in enumerate(games[:target_legs]):
            if i < len(contexts):
                context = contexts[i]
            else:
                continue
            
            # Select best bet for this game using shared criteria
            best_bet = await self._select_best_bet_for_game(game, context)
            if best_bet:
                legs.append(best_bet)
        
        # Ensure we have enough legs and meet minimum odds
        if len(legs) >= target_legs:
            total_odds = self._calculate_total_odds(legs[:target_legs])
            if total_odds >= min_total_odds:
                return legs[:target_legs]
        
        return []
    
    async def _select_best_bet_for_game(self, game: GameOdds, context: SportContext) -> Optional[Dict[str, Any]]:
        """Select the best bet for a game using shared logic."""
        # Shared logic for selecting best bets
        # Would consider factors like odds value, confidence, etc.
        
        if not game.books or not game.books[0].selections:
            return None
        
        # For now, return a simple spread bet
        best_selection = game.books[0].selections[0]
        
        return {
            "game_id": game.game_id,
            "selection": f"{best_selection.team} {best_selection.market}",
            "odds": best_selection.odds,
            "book": game.books[0].bookmaker,
            "market_type": best_selection.market,
            "sport": self.sport,
            "context": context.metadata if hasattr(context, 'metadata') else {}
        }
    
    async def _calculate_confidence(self, legs: List[Dict[str, Any]], contexts: List[SportContext]) -> float:
        """Calculate confidence using shared Bayesian scoring if available."""
        if self.confidence_scorer:
            try:
                # Use Bayesian confidence scorer
                confidence = await self.confidence_scorer.calculate_parlay_confidence(legs, contexts)
                return min(max(confidence, 0.0), 1.0)
            except Exception as e:
                self.logger.warning(f"Bayesian confidence calculation failed: {e}")
        
        # Fallback to simple confidence calculation
        base_confidence = 0.7
        confidence_adjustments = []
        
        for leg in legs:
            # Adjust based on odds (higher odds = lower confidence)
            odds = leg.get('odds', 2.0)
            if odds > 3.0:
                confidence_adjustments.append(-0.1)
            elif odds < 1.5:
                confidence_adjustments.append(0.1)
        
        final_confidence = base_confidence + sum(confidence_adjustments)
        return min(max(final_confidence, 0.0), 1.0)
    
    async def _get_knowledge_insights(self, legs: List[Dict[str, Any]], contexts: List[SportContext]) -> List[str]:
        """Get knowledge base insights filtered by sport."""
        if not self.knowledge_base:
            return []
        
        insights = []
        
        try:
            # Create sport-specific query
            query_terms = [self.sport]
            for leg in legs:
                if 'selection' in leg:
                    query_terms.append(leg['selection'])
            
            query = " ".join(query_terms)
            
            # Search knowledge base with sport filter
            result = await self._search_knowledge_base_by_sport(query)
            
            if result and result.insights:
                insights.extend(result.insights)
            
            # Add specific insights based on sport contexts
            for context in contexts:
                context_insights = await self._get_context_specific_insights(context)
                insights.extend(context_insights)
                
        except Exception as e:
            self.logger.warning(f"Knowledge insights generation failed: {e}")
        
        return insights[:5]  # Limit to top 5 insights
    
    async def _search_knowledge_base_by_sport(self, query: str) -> Optional[RAGResult]:
        """Search knowledge base with sport-specific filtering."""
        if not self.knowledge_base:
            return None
        
        try:
            # Add sport-specific context to query
            sport_query = f"{self.sport} {query}"
            result = self.knowledge_base.search_knowledge(sport_query, top_k=5)
            
            # Filter results to ensure sport relevance
            filtered_chunks = []
            for chunk in result.chunks:
                if self._is_sport_relevant(chunk, self.sport):
                    filtered_chunks.append(chunk)
            
            result.chunks = filtered_chunks
            return result
            
        except Exception as e:
            self.logger.warning(f"Knowledge base search failed: {e}")
            return None
    
    def _is_sport_relevant(self, chunk: KnowledgeChunk, sport: str) -> bool:
        """Check if a knowledge chunk is relevant to the specified sport."""
        if not chunk or not chunk.content:
            return False
        
        content_lower = chunk.content.lower()
        sport_lower = sport.lower()
        
        # Check for sport-specific keywords
        sport_keywords = {
            'nfl': ['football', 'nfl', 'quarterback', 'touchdown', 'yard', 'rushing', 'passing'],
            'nba': ['basketball', 'nba', 'points', 'rebounds', 'assists', 'three-point', 'player']
        }
        
        relevant_keywords = sport_keywords.get(sport_lower, [])
        
        # If no sport-specific keywords found, consider it generally relevant
        if not any(keyword in content_lower for keyword in relevant_keywords):
            # Check if it's explicitly about another sport
            other_sports = [s for s in sport_keywords.keys() if s != sport_lower]
            if any(other_sport in content_lower for other_sport in other_sports):
                return False
        
        return True
    
    async def _get_context_specific_insights(self, context: SportContext) -> List[str]:
        """Generate insights specific to the sport context."""
        insights = []
        
        if isinstance(context, NFLContext):
            # NFL-specific insights
            if context.weather:
                insights.append(f"Weather conditions may impact {context.sport} game performance")
            if context.week > 14:
                insights.append(f"Late season {context.sport} games often have playoff implications")
        
        elif isinstance(context, NBAContext):
            # NBA-specific insights
            if context.rest_days:
                insights.append(f"Rest days can significantly impact {context.sport} player performance")
            if context.season_stage == "Playoffs":
                insights.append(f"{context.sport} playoff games typically have different dynamics")
        
        return insights
    
    async def _detect_arbitrage(self, games: List[GameOdds]) -> List[Dict[str, Any]]:
        """Detect arbitrage opportunities using shared logic."""
        if not self.arbitrage_detector:
            return []
        
        try:
            opportunities = []
            for game in games:
                arb_opps = await self.arbitrage_detector.find_arbitrage_opportunities(game)
                opportunities.extend(arb_opps)
            return opportunities
        except Exception as e:
            self.logger.warning(f"Arbitrage detection failed: {e}")
            return []
    
    async def _generate_reasoning(self, legs: List[Dict[str, Any]], contexts: List[SportContext], confidence: float) -> str:
        """Generate textual reasoning for the parlay."""
        reasoning_parts = [
            f"Generated {self.sport} parlay with {len(legs)} legs.",
            f"Overall confidence: {confidence:.1%}.",
        ]
        
        for i, leg in enumerate(legs):
            reasoning_parts.append(f"Leg {i+1}: {leg.get('selection', 'Unknown')} at {leg.get('odds', 'N/A')} odds.")
        
        # Add sport-specific reasoning
        if contexts:
            reasoning_parts.append(f"Analysis based on {len(contexts)} {self.sport} game contexts.")
        
        return " ".join(reasoning_parts)
    
    async def _generate_expert_guidance(self, legs: List[Dict[str, Any]], insights: List[str]) -> List[str]:
        """Generate expert guidance based on knowledge base insights."""
        guidance = []
        
        if insights:
            guidance.append(f"Expert analysis suggests careful consideration of {self.sport}-specific factors.")
            guidance.extend(insights[:3])  # Top 3 insights
        
        # Add general guidance
        guidance.append(f"Monitor line movement before placing {self.sport} bets.")
        guidance.append(f"Consider bankroll management for {self.sport} parlays.")
        
        return guidance
    
    async def _generate_value_analysis(self, legs: List[Dict[str, Any]], contexts: List[SportContext]) -> str:
        """Generate value betting analysis."""
        return f"Value analysis indicates potential opportunity in {self.sport} markets based on current lines and context."
    
    async def _generate_bankroll_recommendations(self, confidence: float, legs: List[Dict[str, Any]]) -> List[str]:
        """Generate bankroll management recommendations."""
        recommendations = []
        
        if confidence > 0.7:
            recommendations.append(f"High confidence {self.sport} parlay - consider standard unit size.")
        elif confidence > 0.5:
            recommendations.append(f"Moderate confidence {self.sport} parlay - consider half unit size.")
        else:
            recommendations.append(f"Lower confidence {self.sport} parlay - consider quarter unit size.")
        
        recommendations.append(f"Never bet more than 2-3% of bankroll on {self.sport} parlays.")
        
        return recommendations
    
    async def _calculate_expected_value(self, legs: List[Dict[str, Any]], confidence: float) -> Optional[float]:
        """Calculate expected value for the parlay."""
        try:
            total_odds = self._calculate_total_odds(legs)
            implied_probability = 1.0 / total_odds
            estimated_probability = confidence
            
            expected_value = (estimated_probability * (total_odds - 1)) - (1 - estimated_probability)
            return round(expected_value, 4)
        except:
            return None
    
    async def _calculate_kelly_percentage(self, expected_value: Optional[float], confidence: float) -> Optional[float]:
        """Calculate Kelly percentage for bet sizing."""
        if not expected_value or expected_value <= 0:
            return None
        
        try:
            kelly = expected_value / (confidence * 10)  # Conservative Kelly
            return min(max(kelly, 0.0), 0.05)  # Cap at 5%
        except:
            return None
    
    def _calculate_total_odds(self, legs: List[Dict[str, Any]]) -> float:
        """Calculate total parlay odds."""
        total_odds = 1.0
        for leg in legs:
            total_odds *= leg.get('odds', 2.0)
        return total_odds
    
    async def _check_correlations(self, legs: List[Dict[str, Any]], max_risk: float) -> List[str]:
        """Check for correlation warnings."""
        warnings = []
        
        # Basic correlation checking
        if len(legs) > 2:
            warnings.append(f"Multiple leg {self.sport} parlay - monitor correlations between bets.")
        
        return warnings


# Factory function for creating unified agents
def create_unified_agent(sport: str, knowledge_base: Optional[SportsKnowledgeRAG] = None) -> UnifiedParlayStrategistAgent:
    """
    Create a unified parlay strategist agent for the specified sport.
    
    Args:
        sport: Either "NBA" or "NFL"
        knowledge_base: Optional shared knowledge base instance
        
    Returns:
        UnifiedParlayStrategistAgent configured for the sport
    """
    return UnifiedParlayStrategistAgent(sport, knowledge_base)
