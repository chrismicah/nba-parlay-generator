#!/usr/bin/env python3
"""
Enhanced ParlayStrategistAgent with Textual Reasoning - JIRA-019

Generates parlay recommendations with detailed textual rationale that can be used
to train a RoBERTa confidence classifier.

Key Features:
- Detailed textual reasoning for each parlay decision
- Integration with injury analysis and market intelligence
- Structured reasoning format for ML training
- Historical outcome tracking for confidence labeling
"""

from __future__ import annotations

import logging
import random
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json

from tools.odds_fetcher_tool import GameOdds, BookOdds, Selection

# Import injury classifier (optional dependency)
try:
    from tools.classify_injury_severity import BioBERTInjuryClassifier
    HAS_INJURY_CLASSIFIER = True
except ImportError:
    HAS_INJURY_CLASSIFIER = False
    BioBERTInjuryClassifier = None

# Set up logging
logger = logging.getLogger(__name__)


@dataclass
class ReasoningFactor:
    """Individual reasoning factor for parlay decisions."""
    factor_type: str  # 'injury', 'line_movement', 'matchup', 'public_betting', 'weather', 'rest'
    description: str
    confidence: float  # 0.0 to 1.0
    impact: str  # 'positive', 'negative', 'neutral'
    weight: float = 1.0  # How much this factor influences the decision


@dataclass
class ParlayReasoning:
    """Complete textual reasoning for a parlay decision."""
    parlay_id: str
    reasoning_text: str
    confidence_score: float  # 0.0 to 1.0 overall confidence
    reasoning_factors: List[ReasoningFactor]
    generated_at: str
    strategist_version: str = "enhanced_v1.0"


@dataclass
class ParlayRecommendation:
    """Enhanced parlay recommendation with reasoning."""
    legs: List[Dict[str, Any]]
    reasoning: ParlayReasoning
    expected_value: Optional[float] = None
    kelly_percentage: Optional[float] = None


class EnhancedParlayStrategistAgent:
    """
    Advanced parlay strategist that generates detailed textual reasoning
    for each parlay recommendation to enable confidence classification.
    """
    
    def __init__(self, use_injury_classifier: bool = True):
        """
        Initialize the enhanced strategist agent.
        
        Args:
            use_injury_classifier: Whether to use BioBERT injury analysis
        """
        self.agent_id = "enhanced_parlay_strategist_v1.0"
        self.use_injury_classifier = use_injury_classifier
        
        # Initialize injury classifier if requested
        self.injury_classifier = None
        if self.use_injury_classifier and HAS_INJURY_CLASSIFIER:
            try:
                self.injury_classifier = BioBERTInjuryClassifier()
                logger.info("BioBERT injury classifier initialized")
            except Exception as e:
                logger.warning(f"Could not initialize injury classifier: {e}")
        elif self.use_injury_classifier:
            logger.warning("Injury classifier requested but not available")
        
        # Common NBA teams for analysis
        self.nba_teams = [
            'Lakers', 'Celtics', 'Warriors', 'Nets', 'Heat', 'Bulls', 'Knicks',
            'Clippers', 'Nuggets', 'Suns', 'Mavericks', 'Rockets', 'Spurs',
            'Thunder', 'Jazz', 'Blazers', 'Kings', 'Timberwolves', 'Pelicans',
            'Magic', 'Hawks', 'Hornets', 'Pistons', 'Pacers', 'Cavaliers',
            'Raptors', 'Wizards', 'Bucks', '76ers', 'Grizzlies'
        ]
        
        logger.info(f"Enhanced ParlayStrategistAgent initialized: {self.agent_id}")
    
    def generate_parlay_with_reasoning(self, current_games: List[GameOdds],
                                     target_legs: int = 3,
                                     min_total_odds: float = 3.0) -> Optional[ParlayRecommendation]:
        """
        Generate a parlay recommendation with detailed textual reasoning.
        
        Args:
            current_games: Available games with odds
            target_legs: Number of legs to include
            min_total_odds: Minimum acceptable total odds
            
        Returns:
            ParlayRecommendation with reasoning or None if no viable parlay found
        """
        if not current_games:
            logger.warning("No games available for parlay generation")
            return None
        
        logger.info(f"Generating parlay with reasoning from {len(current_games)} available games")
        
        # Analyze each game for opportunities
        game_analyses = []
        for game in current_games[:5]:  # Limit to first 5 games for demo
            analysis = self._analyze_game_deeply(game)
            if analysis:
                game_analyses.append(analysis)
        
        if len(game_analyses) < target_legs:
            logger.warning(f"Only {len(game_analyses)} games analyzed, need {target_legs} legs")
            return None
        
        # Select best opportunities
        selected_opportunities = self._select_best_opportunities(game_analyses, target_legs)
        
        if len(selected_opportunities) < target_legs:
            logger.warning("Could not find enough viable opportunities")
            return None
        
        # Generate comprehensive reasoning
        reasoning = self._generate_comprehensive_reasoning(selected_opportunities)
        
        # Calculate confidence score
        overall_confidence = self._calculate_overall_confidence(selected_opportunities, reasoning.reasoning_factors)
        reasoning.confidence_score = overall_confidence
        
        # Build parlay legs
        parlay_legs = []
        total_odds = 1.0
        
        for opportunity in selected_opportunities:
            leg = {
                'game_id': opportunity['game_id'],
                'market_type': opportunity['market_type'],
                'selection_name': opportunity['selection_name'],
                'bookmaker': opportunity['bookmaker'],
                'odds_decimal': opportunity['odds_decimal'],
                'line': opportunity.get('line'),
                'reasoning_summary': opportunity['reasoning_summary']
            }
            parlay_legs.append(leg)
            total_odds *= opportunity['odds_decimal']
        
        if total_odds < min_total_odds:
            logger.info(f"Total odds {total_odds:.2f} below minimum {min_total_odds}")
            return None
        
        # Calculate expected value (simplified)
        expected_value = self._calculate_expected_value(selected_opportunities, total_odds)
        
        recommendation = ParlayRecommendation(
            legs=parlay_legs,
            reasoning=reasoning,
            expected_value=expected_value,
            kelly_percentage=self._calculate_kelly_percentage(expected_value, total_odds)
        )
        
        logger.info(f"Generated parlay with {len(parlay_legs)} legs, "
                   f"total odds {total_odds:.2f}, confidence {overall_confidence:.3f}")
        
        return recommendation
    
    def _analyze_game_deeply(self, game: GameOdds) -> Optional[Dict[str, Any]]:
        """Perform deep analysis of a single game for betting opportunities."""
        analysis = {
            'game_id': game.game_id,
            'teams': self._extract_teams_from_game(game),
            'opportunities': [],
            'injury_intel': [],
            'line_movement': [],
            'public_betting_info': []
        }
        
        # Analyze each market
        for book in game.books:
            for selection in book.selections:
                opportunity = self._analyze_selection_opportunity(game, book, selection)
                if opportunity:
                    analysis['opportunities'].append(opportunity)
        
        # Add injury intelligence (simulated for demo)
        analysis['injury_intel'] = self._simulate_injury_intelligence(analysis['teams'])
        
        # Add line movement analysis (simulated for demo)  
        analysis['line_movement'] = self._simulate_line_movement_analysis(game)
        
        # Add public betting information (simulated for demo)
        analysis['public_betting_info'] = self._simulate_public_betting_data(game)
        
        return analysis if analysis['opportunities'] else None
    
    def _analyze_selection_opportunity(self, game: GameOdds, book: BookOdds, 
                                     selection: Selection) -> Optional[Dict[str, Any]]:
        """Analyze a specific selection for betting value."""
        # Basic opportunity detection (enhanced from mock version)
        opportunity = None
        reasoning_factors = []
        
        if book.market == "h2h":
            # Moneyline opportunity analysis
            if 1.7 <= selection.price_decimal <= 2.8:
                # Favorable odds range
                reasoning_factors.append(ReasoningFactor(
                    factor_type='odds_value',
                    description=f"{selection.name} at {selection.price_decimal} offers value in competitive matchup",
                    confidence=0.7,
                    impact='positive'
                ))
                
                opportunity = {
                    'game_id': game.game_id,
                    'market_type': 'h2h',
                    'selection_name': selection.name,
                    'bookmaker': book.bookmaker,
                    'odds_decimal': selection.price_decimal,
                    'reasoning_factors': reasoning_factors,
                    'opportunity_type': 'moneyline_value'
                }
        
        elif book.market == "spreads" and selection.line is not None:
            # Spread opportunity analysis
            if abs(selection.line) <= 6.5 and 1.8 <= selection.price_decimal <= 2.1:
                reasoning_factors.append(ReasoningFactor(
                    factor_type='spread_analysis',
                    description=f"{selection.name} {selection.line:+.1f} in close matchup at {selection.price_decimal}",
                    confidence=0.6,
                    impact='positive'
                ))
                
                opportunity = {
                    'game_id': game.game_id,
                    'market_type': 'spreads',
                    'selection_name': selection.name,
                    'bookmaker': book.bookmaker,
                    'odds_decimal': selection.price_decimal,
                    'line': selection.line,
                    'reasoning_factors': reasoning_factors,
                    'opportunity_type': 'spread_value'
                }
        
        elif book.market == "totals" and selection.line is not None:
            # Totals opportunity analysis
            if selection.name.lower() in ['over', 'under'] and 200 <= selection.line <= 250:
                reasoning_factors.append(ReasoningFactor(
                    factor_type='totals_analysis',
                    description=f"{selection.name} {selection.line} appears favorable based on team pace metrics",
                    confidence=0.65,
                    impact='positive'
                ))
                
                opportunity = {
                    'game_id': game.game_id,
                    'market_type': 'totals',
                    'selection_name': selection.name,
                    'bookmaker': book.bookmaker,
                    'odds_decimal': selection.price_decimal,
                    'line': selection.line,
                    'reasoning_factors': reasoning_factors,
                    'opportunity_type': 'totals_value'
                }
        
        if opportunity:
            opportunity['reasoning_summary'] = self._generate_opportunity_summary(opportunity)
        
        return opportunity
    
    def _select_best_opportunities(self, game_analyses: List[Dict[str, Any]], 
                                 target_legs: int) -> List[Dict[str, Any]]:
        """Select the best opportunities for the parlay."""
        all_opportunities = []
        
        for analysis in game_analyses:
            for opportunity in analysis['opportunities']:
                # Enhanced opportunity with game context
                enhanced_opportunity = opportunity.copy()
                enhanced_opportunity['injury_intel'] = analysis['injury_intel']
                enhanced_opportunity['line_movement'] = analysis['line_movement'] 
                enhanced_opportunity['public_betting_info'] = analysis['public_betting_info']
                
                # Calculate opportunity score
                enhanced_opportunity['opportunity_score'] = self._calculate_opportunity_score(enhanced_opportunity)
                all_opportunities.append(enhanced_opportunity)
        
        # Sort by opportunity score and select top N
        all_opportunities.sort(key=lambda x: x['opportunity_score'], reverse=True)
        
        # Ensure we don't select multiple legs from same game
        selected = []
        used_games = set()
        
        for opp in all_opportunities:
            if len(selected) >= target_legs:
                break
            if opp['game_id'] not in used_games:
                selected.append(opp)
                used_games.add(opp['game_id'])
        
        return selected
    
    def _generate_comprehensive_reasoning(self, opportunities: List[Dict[str, Any]]) -> ParlayReasoning:
        """Generate comprehensive textual reasoning for the parlay."""
        parlay_id = f"parlay_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        reasoning_parts = []
        all_factors = []
        
        # Introduction
        reasoning_parts.append(f"PARLAY ANALYSIS ({len(opportunities)} legs):")
        reasoning_parts.append("")
        
        # Analyze each leg
        for i, opp in enumerate(opportunities, 1):
            reasoning_parts.append(f"LEG {i}: {opp['selection_name']} ({opp['market_type']})")
            reasoning_parts.append(f"Odds: {opp['odds_decimal']} at {opp['bookmaker']}")
            
            # Add reasoning factors
            for factor in opp['reasoning_factors']:
                reasoning_parts.append(f"• {factor.description}")
                all_factors.append(factor)
            
            # Add injury intelligence
            if opp['injury_intel']:
                for injury in opp['injury_intel']:
                    reasoning_parts.append(f"• Injury Intel: {injury}")
                    all_factors.append(ReasoningFactor(
                        factor_type='injury',
                        description=injury,
                        confidence=0.6,
                        impact='negative' if 'out' in injury.lower() else 'neutral'
                    ))
            
            # Add line movement
            if opp['line_movement']:
                for movement in opp['line_movement']:
                    reasoning_parts.append(f"• Line Movement: {movement}")
                    all_factors.append(ReasoningFactor(
                        factor_type='line_movement',
                        description=movement,
                        confidence=0.5,
                        impact='positive' if 'favorable' in movement.lower() else 'neutral'
                    ))
            
            reasoning_parts.append("")
        
        # Overall assessment
        reasoning_parts.append("OVERALL ASSESSMENT:")
        total_odds = 1.0
        for opp in opportunities:
            total_odds *= opp['odds_decimal']
        
        reasoning_parts.append(f"Combined odds: {total_odds:.2f}")
        reasoning_parts.append(f"Risk assessment: {self._assess_overall_risk(opportunities)}")
        reasoning_parts.append(f"Value assessment: {self._assess_overall_value(opportunities)}")
        
        # Generate final reasoning text
        reasoning_text = "\n".join(reasoning_parts)
        
        return ParlayReasoning(
            parlay_id=parlay_id,
            reasoning_text=reasoning_text,
            confidence_score=0.0,  # Will be calculated later
            reasoning_factors=all_factors,
            generated_at=datetime.now(timezone.utc).isoformat()
        )
    
    def _calculate_opportunity_score(self, opportunity: Dict[str, Any]) -> float:
        """Calculate a score for ranking opportunities."""
        base_score = 0.5
        
        # Odds value scoring
        odds = opportunity['odds_decimal']
        if 1.8 <= odds <= 2.2:
            base_score += 0.3  # Sweet spot
        elif 1.5 <= odds <= 3.0:
            base_score += 0.1  # Acceptable range
        
        # Factor-based scoring
        for factor in opportunity['reasoning_factors']:
            if factor.impact == 'positive':
                base_score += factor.confidence * 0.2
            elif factor.impact == 'negative':
                base_score -= factor.confidence * 0.1
        
        # Injury impact
        injury_penalty = len([x for x in opportunity.get('injury_intel', []) if 'out' in x.lower()]) * 0.1
        base_score -= injury_penalty
        
        return max(0.0, min(1.0, base_score))
    
    def _calculate_overall_confidence(self, opportunities: List[Dict[str, Any]], 
                                   factors: List[ReasoningFactor]) -> float:
        """Calculate overall confidence score for the parlay."""
        if not factors:
            return 0.5
        
        # Base confidence from opportunity scores
        avg_opp_score = sum(opp['opportunity_score'] for opp in opportunities) / len(opportunities)
        
        # Factor-based confidence adjustment
        positive_factors = [f for f in factors if f.impact == 'positive']
        negative_factors = [f for f in factors if f.impact == 'negative']
        
        positive_confidence = sum(f.confidence for f in positive_factors) / max(1, len(positive_factors))
        negative_confidence = sum(f.confidence for f in negative_factors) / max(1, len(negative_factors))
        
        # Weighted combination
        confidence = (avg_opp_score * 0.4 + 
                     positive_confidence * 0.4 - 
                     negative_confidence * 0.2)
        
        return max(0.1, min(0.9, confidence))
    
    def _calculate_expected_value(self, opportunities: List[Dict[str, Any]], total_odds: float) -> float:
        """Calculate expected value of the parlay (simplified)."""
        # Simplified EV calculation based on confidence
        avg_confidence = sum(opp['opportunity_score'] for opp in opportunities) / len(opportunities)
        implied_probability = avg_confidence
        
        # EV = (Probability of Win * Payout) - (Probability of Loss * Stake)
        payout = total_odds - 1  # Profit on $1 bet
        ev = (implied_probability * payout) - ((1 - implied_probability) * 1)
        
        return ev
    
    def _calculate_kelly_percentage(self, expected_value: float, total_odds: float) -> float:
        """Calculate Kelly criterion betting percentage."""
        if expected_value <= 0:
            return 0.0
        
        # Kelly % = (Expected Value) / (Odds - 1)
        kelly_pct = expected_value / (total_odds - 1)
        
        # Cap at 25% for safety
        return min(0.25, max(0.0, kelly_pct))
    
    # Simulation methods (replace with real data in production)
    def _simulate_injury_intelligence(self, teams: List[str]) -> List[str]:
        """Simulate injury intelligence (replace with real BioBERT analysis)."""
        if not teams:
            teams = random.sample(self.nba_teams, 2)
        
        team_to_use = teams[0] if teams else "Team"
        injury_scenarios = [
            f"{team_to_use} star player questionable with ankle injury",
            f"{team_to_use} backup center ruled out",
            f"{team_to_use} all players healthy for tonight",
            f"{team_to_use} point guard probable despite knee soreness"
        ]
        return random.choices(injury_scenarios, k=random.randint(0, 2))
    
    def _simulate_line_movement_analysis(self, game: GameOdds) -> List[str]:
        """Simulate line movement analysis."""
        movements = [
            "Line moved 1.5 points toward home team despite 60% public money on away team",
            "Sharp money detected on the under, total dropped from 220 to 218.5",
            "No significant line movement, indicating balanced action",
            "Late money coming in on favorite, spread moved half point"
        ]
        return random.choices(movements, k=random.randint(0, 2))
    
    def _simulate_public_betting_data(self, game: GameOdds) -> List[str]:
        """Simulate public betting information."""
        public_info = [
            f"Public betting 70% on favorite but line hasn't moved",
            f"Sharp money indicators suggest value on underdog",
            f"Recreational bettors heavily on the over",
            f"Balanced action across all markets"
        ]
        return random.choices(public_info, k=random.randint(0, 1))
    
    def _extract_teams_from_game(self, game: GameOdds) -> List[str]:
        """Extract team names from game data."""
        teams = []
        for book in game.books:
            if book.market == "h2h":
                for selection in book.selections:
                    # Extract team names from selection names (which may include cities)
                    team_name = self._extract_team_name(selection.name)
                    if team_name:
                        teams.append(team_name)
                if len(teams) >= 2:
                    break
        
        # If no teams found, return default teams
        if not teams:
            teams = random.sample(self.nba_teams, 2)
        
        return list(set(teams))[:2]  # Limit to 2 teams
    
    def _extract_team_name(self, selection_name: str) -> Optional[str]:
        """Extract team name from selection string."""
        # Check if any NBA team name is in the selection
        for team in self.nba_teams:
            if team.lower() in selection_name.lower():
                return team
        
        # If no match, try to extract from common patterns
        # e.g., "Los Angeles Lakers" -> "Lakers"
        words = selection_name.split()
        if len(words) >= 2:
            return words[-1]  # Last word is often the team name
        
        return None
    
    def _generate_opportunity_summary(self, opportunity: Dict[str, Any]) -> str:
        """Generate a brief summary of the opportunity."""
        if opportunity['market_type'] == 'h2h':
            return f"{opportunity['selection_name']} ML at {opportunity['odds_decimal']} offers value"
        elif opportunity['market_type'] == 'spreads':
            return f"{opportunity['selection_name']} {opportunity['line']:+.1f} at {opportunity['odds_decimal']}"
        elif opportunity['market_type'] == 'totals':
            return f"{opportunity['selection_name']} {opportunity['line']} at {opportunity['odds_decimal']}"
        return "Value opportunity identified"
    
    def _assess_overall_risk(self, opportunities: List[Dict[str, Any]]) -> str:
        """Assess overall risk level of the parlay."""
        avg_odds = sum(opp['odds_decimal'] for opp in opportunities) / len(opportunities)
        
        if avg_odds < 1.7:
            return "Low risk - Heavy favorites"
        elif avg_odds > 2.5:
            return "High risk - Underdogs and longshots"
        else:
            return "Medium risk - Balanced selections"
    
    def _assess_overall_value(self, opportunities: List[Dict[str, Any]]) -> str:
        """Assess overall value proposition of the parlay."""
        avg_score = sum(opp['opportunity_score'] for opp in opportunities) / len(opportunities)
        
        if avg_score > 0.7:
            return "Strong value across all legs"
        elif avg_score > 0.5:
            return "Moderate value with some concerns"
        else:
            return "Limited value - proceed with caution"


def main():
    """Main function for testing the enhanced strategist."""
    import sys
    import os
    
    # Add project root to path
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from tools.odds_fetcher_tool import OddsFetcherTool
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        print("🧠 Enhanced ParlayStrategistAgent with Reasoning - JIRA-019")
        print("=" * 70)
        
        # Initialize agent
        agent = EnhancedParlayStrategistAgent()
        
        # Get current games
        odds_fetcher = OddsFetcherTool()
        print("📡 Fetching current NBA games...")
        
        try:
            current_games = odds_fetcher.get_game_odds("basketball_nba", "us", ["h2h", "spreads", "totals"])
            print(f"✅ Found {len(current_games)} games with odds")
        except Exception as e:
            print(f"⚠️ Could not fetch live odds: {e}")
            print("💡 Generating demonstration with sample data...")
            current_games = []
        
        # Generate parlay with reasoning
        recommendation = agent.generate_parlay_with_reasoning(current_games, target_legs=3)
        
        if recommendation:
            print(f"\n🎯 Generated Parlay Recommendation:")
            print(f"=" * 50)
            
            # Show legs
            total_odds = 1.0
            for i, leg in enumerate(recommendation.legs, 1):
                line_str = f" {leg['line']:+.1f}" if leg.get('line') else ""
                print(f"Leg {i}: {leg['selection_name']}{line_str} @ {leg['odds_decimal']} ({leg['bookmaker']})")
                total_odds *= leg['odds_decimal']
            
            print(f"\nTotal Odds: {total_odds:.2f}")
            print(f"Confidence Score: {recommendation.reasoning.confidence_score:.3f}")
            print(f"Expected Value: {recommendation.expected_value:.3f}")
            print(f"Kelly %: {recommendation.kelly_percentage:.1%}")
            
            print(f"\n📝 Detailed Reasoning:")
            print("=" * 50)
            print(recommendation.reasoning.reasoning_text)
            
            print(f"\n✅ Enhanced ParlayStrategistAgent working correctly!")
            print(f"🎯 Ready for confidence classification training (JIRA-019)")
            
        else:
            print("⚠️ No viable parlay recommendation generated")
            print("💡 This is expected when no games are available or no value is found")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
