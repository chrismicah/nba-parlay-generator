#!/usr/bin/env python3
"""
Enhanced Parlay Strategist with Knowledge Base RAG Integration

Integrates Ed Miller's "The Logic of Sports Betting" and Wayne Winston's "Mathletics"
into parlay generation using RAG (Retrieval-Augmented Generation).

Key Features:
- RAG-enhanced reasoning with 1,590+ sports betting chunks
- Integration of academic sports betting theory
- Value betting and correlation analysis from expert sources
- Mathematical foundations from Mathletics
- Betting logic from Ed Miller's work
"""

from __future__ import annotations

import logging
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone

# Import base strategist
from tools.enhanced_parlay_strategist_agent import (
    FewShotEnhancedParlayStrategistAgent,
    ParlayRecommendation,
    ParlayReasoning,
    ReasoningFactor
)

# Import RAG system
from tools.knowledge_base_rag import SportsKnowledgeRAG

# Import game data
from tools.odds_fetcher_tool import GameOdds

logger = logging.getLogger(__name__)


@dataclass
class RAGEnhancedParlayRecommendation(ParlayRecommendation):
    """Parlay recommendation enhanced with knowledge base insights."""
    knowledge_insights: List[str] = field(default_factory=list)
    expert_guidance: List[str] = field(default_factory=list)
    value_betting_analysis: str = ""
    correlation_warnings: List[str] = field(default_factory=list)
    bankroll_recommendations: List[str] = field(default_factory=list)


class RAGEnhancedParlayStrategist(FewShotEnhancedParlayStrategistAgent):
    """
    Parlay strategist enhanced with knowledge base RAG system.
    
    Leverages Ed Miller and Wayne Winston's sports betting expertise
    to provide more intelligent parlay recommendations.
    """
    
    def __init__(self, 
                 use_injury_classifier: bool = True,
                 few_shot_examples_path: str = "data/few_shot_parlay_examples.json",
                 enable_rag: bool = True):
        """
        Initialize RAG-enhanced parlay strategist.
        
        Args:
            use_injury_classifier: Whether to use injury analysis
            few_shot_examples_path: Path to few-shot examples
            enable_rag: Whether to enable knowledge base RAG
        """
        super().__init__(use_injury_classifier, few_shot_examples_path)
        
        self.agent_id = "rag_enhanced_parlay_strategist_v1.0"
        self.enable_rag = enable_rag
        
        # Initialize RAG system
        self.rag_system = None
        if self.enable_rag:
            try:
                self.rag_system = SportsKnowledgeRAG()
                logger.info("Knowledge Base RAG system initialized with sports betting books")
            except Exception as e:
                logger.warning(f"Could not initialize RAG system: {e}")
                self.enable_rag = False
        
        logger.info(f"RAG Enhanced Parlay Strategist initialized (RAG enabled: {self.enable_rag})")
    
    async def generate_rag_enhanced_parlay(self,
                                         current_games: List[GameOdds],
                                         target_legs: int = 3,
                                         min_total_odds: float = 3.0,
                                         sport: str = "nba") -> Optional[RAGEnhancedParlayRecommendation]:
        """
        Generate parlay recommendation enhanced with knowledge base insights.
        
        Args:
            current_games: Available games with odds
            target_legs: Number of legs to include
            min_total_odds: Minimum acceptable total odds
            sport: Sport type ("nba" or "nfl")
            
        Returns:
            RAGEnhancedParlayRecommendation with expert insights
        """
        logger.info(f"Generating RAG-enhanced {sport.upper()} parlay recommendation")
        
        # Generate base parlay recommendation
        base_recommendation = self.generate_parlay_with_reasoning(
            current_games, target_legs, min_total_odds
        )
        
        if not base_recommendation:
            return None
        
        # Create enhanced recommendation
        enhanced_recommendation = RAGEnhancedParlayRecommendation(
            legs=base_recommendation.legs,
            reasoning=base_recommendation.reasoning,
            expected_value=base_recommendation.expected_value,
            kelly_percentage=base_recommendation.kelly_percentage
        )
        
        # Add RAG enhancements
        if self.enable_rag and self.rag_system:
            await self._enhance_with_knowledge_base(enhanced_recommendation, sport)
        
        logger.info(f"Enhanced parlay with {len(enhanced_recommendation.knowledge_insights)} knowledge insights")
        
        return enhanced_recommendation
    
    async def _enhance_with_knowledge_base(self,
                                         recommendation: RAGEnhancedParlayRecommendation,
                                         sport: str) -> None:
        """Enhance recommendation with knowledge base insights."""
        
        # 1. Get parlay-specific insights
        market_types = list(set(leg['market_type'] for leg in recommendation.legs))
        team_names = [leg.get('selection_name', '') for leg in recommendation.legs]
        
        parlay_insights = self.rag_system.get_parlay_insights(
            sport=sport,
            market_types=market_types,
            team_names=team_names
        )
        
        recommendation.knowledge_insights.extend(parlay_insights.insights)
        
        # 2. Get value betting analysis
        total_odds = 1.0
        for leg in recommendation.legs:
            total_odds *= leg['odds_decimal']
        
        odds_range = (min(leg['odds_decimal'] for leg in recommendation.legs),
                     max(leg['odds_decimal'] for leg in recommendation.legs))
        
        value_insights = self.rag_system.get_value_betting_insights(odds_range)
        
        if value_insights.chunks:
            recommendation.value_betting_analysis = self._extract_value_analysis(value_insights)
        
        # 3. Get correlation warnings
        correlation_warnings = self._analyze_correlation_with_rag(recommendation, sport)
        recommendation.correlation_warnings.extend(correlation_warnings)
        
        # 4. Get bankroll management recommendations
        bankroll_insights = self.rag_system.get_bankroll_management_insights()
        
        bankroll_recs = self._extract_bankroll_recommendations(
            bankroll_insights, 
            total_odds, 
            recommendation.kelly_percentage
        )
        recommendation.bankroll_recommendations.extend(bankroll_recs)
        
        # 5. Get statistical insights for the sport
        stat_insights = self.rag_system.get_statistical_insights(sport)
        
        expert_guidance = self._extract_expert_guidance(stat_insights, sport)
        recommendation.expert_guidance.extend(expert_guidance)
        
        # 6. Update reasoning with RAG insights
        self._update_reasoning_with_rag(recommendation)
    
    def _extract_value_analysis(self, value_insights) -> str:
        """Extract value betting analysis from RAG results."""
        if not value_insights.chunks:
            return "No specific value betting guidance found."
        
        # Look for key value betting concepts
        content = " ".join([chunk.content for chunk in value_insights.chunks])
        
        analysis_parts = []
        
        if "expected value" in content.lower():
            analysis_parts.append("Focus on positive expected value calculation")
        
        if "kelly" in content.lower():
            analysis_parts.append("Apply Kelly Criterion for optimal bet sizing")
        
        if "edge" in content.lower():
            analysis_parts.append("Identify mathematical edge over bookmaker odds")
        
        if "variance" in content.lower():
            analysis_parts.append("Consider variance and risk in parlay construction")
        
        if analysis_parts:
            return "; ".join(analysis_parts)
        else:
            return "Apply value betting principles: bet when expected value is positive"
    
    def _analyze_correlation_with_rag(self, recommendation, sport: str) -> List[str]:
        """Analyze correlation risks using knowledge base."""
        if not self.rag_system:
            return []
        
        # Search for correlation-related content
        correlation_query = f"{sport} betting correlation risk parlay dependent outcomes"
        correlation_results = self.rag_system.search_knowledge(correlation_query, top_k=3)
        
        warnings = []
        
        # Check for same-game legs
        game_ids = [leg['game_id'] for leg in recommendation.legs]
        if len(set(game_ids)) < len(game_ids):
            warnings.append("Multiple legs from same game increase correlation risk")
        
        # Check for related market types
        market_types = [leg['market_type'] for leg in recommendation.legs]
        if 'h2h' in market_types and 'spreads' in market_types:
            warnings.append("Moneyline and spread bets are highly correlated")
        
        # Add insights from knowledge base
        if correlation_results.chunks:
            content = " ".join([chunk.content for chunk in correlation_results.chunks])
            if "dependent" in content.lower():
                warnings.append("Expert analysis warns about dependent outcome risks")
        
        return warnings
    
    def _extract_bankroll_recommendations(self,
                                        bankroll_insights,
                                        total_odds: float,
                                        kelly_percentage: float) -> List[str]:
        """Extract bankroll management recommendations."""
        recommendations = []
        
        # Basic Kelly Criterion recommendation
        if kelly_percentage > 0:
            recommendations.append(f"Kelly Criterion suggests {kelly_percentage:.1%} of bankroll")
        
        # Conservative adjustment for parlays
        if len(recommendations) > 0 and total_odds > 10:
            recommendations.append("Consider reducing bet size due to high variance in parlays")
        
        # Add insights from knowledge base
        if bankroll_insights.chunks:
            content = " ".join([chunk.content for chunk in bankroll_insights.chunks])
            
            if "conservative" in content.lower():
                recommendations.append("Expert guidance emphasizes conservative sizing")
            
            if "risk of ruin" in content.lower():
                recommendations.append("Manage risk of ruin with proper position sizing")
        
        return recommendations
    
    def _extract_expert_guidance(self, stat_insights, sport: str) -> List[str]:
        """Extract expert guidance from statistical insights."""
        guidance = []
        
        if not stat_insights.chunks:
            return ["No specific expert guidance found for this sport"]
        
        # Analyze content for expert recommendations
        content = " ".join([chunk.content for chunk in stat_insights.chunks])
        
        # Ed Miller guidance
        if "miller" in content.lower():
            guidance.append("Ed Miller: Focus on mathematical foundations and logical reasoning")
        
        # Wayne Winston guidance
        if any(term in content.lower() for term in ["winston", "mathletics"]):
            guidance.append("Wayne Winston: Apply statistical models and data-driven analysis")
        
        # Sport-specific guidance
        if sport.lower() == "nfl":
            if "football" in content.lower():
                guidance.append("Football analysis shows importance of situational factors")
        elif sport.lower() == "nba":
            if "basketball" in content.lower():
                guidance.append("Basketball analytics emphasize pace and efficiency metrics")
        
        # General statistical guidance
        if "regression" in content.lower():
            guidance.append("Use regression analysis to identify predictive factors")
        
        if "variance" in content.lower():
            guidance.append("Account for variance in small sample sizes")
        
        return guidance if guidance else ["Apply rigorous statistical analysis methods"]
    
    def _update_reasoning_with_rag(self, recommendation: RAGEnhancedParlayRecommendation) -> None:
        """Update the reasoning text with RAG insights."""
        original_reasoning = recommendation.reasoning.reasoning_text
        
        # Add RAG section to reasoning
        rag_section = "\n\nKNOWLEDGE BASE ANALYSIS:\n"
        rag_section += "Expert insights from Ed Miller's 'The Logic of Sports Betting' and Wayne Winston's 'Mathletics':\n\n"
        
        # Add knowledge insights
        if recommendation.knowledge_insights:
            rag_section += "KEY INSIGHTS:\n"
            for insight in recommendation.knowledge_insights:
                rag_section += f"• {insight}\n"
        
        # Add value analysis
        if recommendation.value_betting_analysis:
            rag_section += f"\nVALUE ANALYSIS:\n• {recommendation.value_betting_analysis}\n"
        
        # Add correlation warnings
        if recommendation.correlation_warnings:
            rag_section += "\nCORRELATION WARNINGS:\n"
            for warning in recommendation.correlation_warnings:
                rag_section += f"• {warning}\n"
        
        # Add bankroll recommendations
        if recommendation.bankroll_recommendations:
            rag_section += "\nBANKROLL MANAGEMENT:\n"
            for rec in recommendation.bankroll_recommendations:
                rag_section += f"• {rec}\n"
        
        # Add expert guidance
        if recommendation.expert_guidance:
            rag_section += "\nEXPERT GUIDANCE:\n"
            for guidance in recommendation.expert_guidance:
                rag_section += f"• {guidance}\n"
        
        # Update reasoning
        recommendation.reasoning.reasoning_text = original_reasoning + rag_section
        recommendation.reasoning.strategist_version = "rag_enhanced_v1.0"


async def main():
    """Main function for testing RAG-enhanced parlay strategist."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("📚 RAG-Enhanced Parlay Strategist - Knowledge Base Integration")
    print("=" * 70)
    
    try:
        # Initialize RAG-enhanced strategist
        strategist = RAGEnhancedParlayStrategist(enable_rag=True)
        
        print(f"✅ RAG Enhanced Strategist initialized")
        print(f"📖 Knowledge Base: {strategist.enable_rag}")
        
        if strategist.rag_system:
            print(f"📊 Sports Betting Chunks: {len(strategist.rag_system.sports_betting_chunks)}")
        
        # Create sample games for testing
        from tools.odds_fetcher_tool import BookOdds, Selection
        
        sample_games = []
        
        # Sample NBA game
        nba_books = [
            BookOdds(
                bookmaker="DraftKings",
                market="h2h",
                selections=[
                    Selection(name="Los Angeles Lakers", price_decimal=1.85),
                    Selection(name="Boston Celtics", price_decimal=2.05)
                ]
            ),
            BookOdds(
                bookmaker="FanDuel", 
                market="spreads",
                selections=[
                    Selection(name="Los Angeles Lakers", price_decimal=1.91, line=-2.5),
                    Selection(name="Boston Celtics", price_decimal=1.91, line=2.5)
                ]
            )
        ]
        
        from tools.odds_fetcher_tool import GameOdds
        nba_game = GameOdds(
            game_id="nba_lakers_celtics_test",
            sport_key="basketball_nba",
            sport_title="NBA",
            commence_time="2024-01-20T20:00:00Z",
            home_team="Boston Celtics",
            away_team="Los Angeles Lakers",
            books=nba_books
        )
        
        sample_games.append(nba_game)
        
        # Generate RAG-enhanced parlay
        print(f"\n🎯 Generating RAG-Enhanced NBA Parlay...")
        recommendation = await strategist.generate_rag_enhanced_parlay(
            current_games=sample_games,
            target_legs=2,
            min_total_odds=3.0,
            sport="nba"
        )
        
        if recommendation:
            print(f"\n✅ RAG-Enhanced Parlay Generated:")
            print(f"   Legs: {len(recommendation.legs)}")
            print(f"   Confidence: {recommendation.reasoning.confidence_score:.3f}")
            print(f"   Knowledge Insights: {len(recommendation.knowledge_insights)}")
            print(f"   Expert Guidance: {len(recommendation.expert_guidance)}")
            
            if recommendation.knowledge_insights:
                print(f"\n📚 Knowledge Base Insights:")
                for insight in recommendation.knowledge_insights[:3]:
                    print(f"   • {insight}")
            
            if recommendation.expert_guidance:
                print(f"\n🎓 Expert Guidance:")
                for guidance in recommendation.expert_guidance[:2]:
                    print(f"   • {guidance}")
            
            print(f"\n✅ RAG-Enhanced Parlay Strategist working correctly!")
            print(f"📖 Your sports betting books are now integrated into parlay generation!")
            
        else:
            print("⚠️ No parlay recommendation generated")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
