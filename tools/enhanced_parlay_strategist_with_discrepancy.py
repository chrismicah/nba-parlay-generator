#!/usr/bin/env python3
"""
Enhanced ParlayStrategistAgent with Market Discrepancy Integration - JIRA-023A

Integrates the Market Discrepancy Detector with the ParlayStrategistAgent to provide
high-value signals from arbitrage and value betting opportunities across sportsbooks.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

# Import base strategist
try:
    from tools.parlay_strategist_agent import ParlayStrategistAgent, ParlayRecommendation, ReasoningFactor
    HAS_BASE_STRATEGIST = True
except ImportError:
    HAS_BASE_STRATEGIST = False
    # Mock for type hints
    class ParlayStrategistAgent:
        pass
    class ParlayRecommendation:
        pass
    class ReasoningFactor:
        pass

# Import market discrepancy detector
from tools.market_discrepancy_detector import MarketDiscrepancyDetector, MarketDiscrepancy

logger = logging.getLogger(__name__)


class EnhancedParlayStrategistWithDiscrepancy:
    """
    Enhanced ParlayStrategistAgent that incorporates market discrepancy signals
    for improved parlay recommendations with arbitrage and value opportunities.
    """
    
    def __init__(self,
                 base_strategist: Optional[ParlayStrategistAgent] = None,
                 discrepancy_weight: float = 0.3,
                 min_arbitrage_confidence: float = 0.8,
                 min_value_confidence: float = 0.7):
        """
        Initialize enhanced strategist with market discrepancy integration.
        
        Args:
            base_strategist: Base ParlayStrategistAgent instance
            discrepancy_weight: Weight given to discrepancy signals (0.0-1.0)
            min_arbitrage_confidence: Minimum confidence for arbitrage signals
            min_value_confidence: Minimum confidence for value signals
        """
        self.base_strategist = base_strategist or (ParlayStrategistAgent() if HAS_BASE_STRATEGIST else None)
        self.discrepancy_weight = discrepancy_weight
        self.min_arbitrage_confidence = min_arbitrage_confidence
        self.min_value_confidence = min_value_confidence
        
        # Initialize market discrepancy detector
        self.discrepancy_detector = MarketDiscrepancyDetector(
            min_arbitrage_profit=0.02,  # 2% minimum arbitrage profit
            min_value_edge=0.05,        # 5% minimum value edge
            confidence_threshold=min_value_confidence
        )
        
        # Cache for discrepancy data
        self.cached_discrepancies = {}
        self.last_scan_time = None
        
        logger.info(f"Enhanced ParlayStrategist initialized with discrepancy weight: {discrepancy_weight}")
    
    def scan_market_discrepancies(self, game_ids: List[str], force_refresh: bool = False) -> Dict[str, List[MarketDiscrepancy]]:
        """
        Scan for market discrepancies across specified games.
        
        Args:
            game_ids: List of game IDs to scan
            force_refresh: Force refresh even if recently scanned
            
        Returns:
            Dictionary of game_id -> discrepancies
        """
        # Check if we need to refresh
        current_time = datetime.now(timezone.utc)
        
        if (not force_refresh and 
            self.last_scan_time and 
            (current_time - self.last_scan_time).total_seconds() < 300):  # 5 minutes cache
            logger.debug("Using cached discrepancy data")
            return self.cached_discrepancies
        
        logger.info(f"Scanning {len(game_ids)} games for market discrepancies")
        
        # Clear old opportunities first
        self.discrepancy_detector.clear_old_opportunities(max_age_minutes=30)
        
        # Scan for discrepancies
        discrepancies = self.discrepancy_detector.scan_multiple_games(game_ids)
        
        # Update cache
        self.cached_discrepancies = discrepancies
        self.last_scan_time = current_time
        
        logger.info(f"Found discrepancies in {len(discrepancies)} games")
        return discrepancies
    
    def extract_discrepancy_factors(self, game_id: str, discrepancies: List[MarketDiscrepancy]) -> List[ReasoningFactor]:
        """
        Extract reasoning factors from market discrepancies.
        
        Args:
            game_id: Game identifier
            discrepancies: List of discrepancies for the game
            
        Returns:
            List of ReasoningFactor objects
        """
        factors = []
        
        for discrepancy in discrepancies:
            if discrepancy.discrepancy_type == 'arbitrage':
                # Arbitrage opportunity factor
                factor = ReasoningFactor(
                    factor_type='market_arbitrage',
                    description=f"Arbitrage opportunity detected: {discrepancy.arbitrage_percentage:.1%} guaranteed profit",
                    confidence=discrepancy.confidence_score,
                    weight=1.0,  # Arbitrage gets maximum weight
                    supporting_data={
                        'profit_percentage': discrepancy.arbitrage_percentage,
                        'sportsbooks': discrepancy.sportsbooks_compared,
                        'market_type': discrepancy.market_type,
                        'best_odds': discrepancy.best_odds
                    }
                )
                factors.append(factor)
                
            elif discrepancy.discrepancy_type == 'value':
                # Value betting opportunity factor
                factor = ReasoningFactor(
                    factor_type='market_value',
                    description=f"Value opportunity: {discrepancy.implied_probability_spread:.1%} edge over fair odds",
                    confidence=discrepancy.confidence_score,
                    weight=0.8,  # High weight for value opportunities
                    supporting_data={
                        'value_score': discrepancy.value_score,
                        'edge_percentage': discrepancy.implied_probability_spread,
                        'market_type': discrepancy.market_type,
                        'best_odds': discrepancy.best_odds,
                        'profit_potential': discrepancy.profit_potential
                    }
                )
                factors.append(factor)
        
        return factors
    
    def integrate_discrepancy_signals(self, 
                                    base_recommendation: ParlayRecommendation,
                                    discrepancy_factors: List[ReasoningFactor]) -> ParlayRecommendation:
        """
        Integrate market discrepancy signals into base parlay recommendation.
        
        Args:
            base_recommendation: Base recommendation from ParlayStrategistAgent
            discrepancy_factors: Discrepancy-based reasoning factors
            
        Returns:
            Enhanced recommendation with discrepancy integration
        """
        if not discrepancy_factors:
            return base_recommendation
        
        # Calculate discrepancy boost
        arbitrage_boost = 0.0
        value_boost = 0.0
        
        for factor in discrepancy_factors:
            if factor.factor_type == 'market_arbitrage':
                # Arbitrage provides direct confidence boost
                arbitrage_boost += factor.confidence * factor.weight * 0.2  # Max 20% boost
            elif factor.factor_type == 'market_value':
                # Value opportunities provide moderate boost
                value_boost += factor.confidence * factor.weight * 0.15  # Max 15% boost
        
        # Apply discrepancy weight
        total_boost = (arbitrage_boost + value_boost) * self.discrepancy_weight
        
        # Enhanced confidence calculation
        base_confidence = getattr(base_recommendation, 'confidence', 0.5)
        enhanced_confidence = min(base_confidence + total_boost, 1.0)
        
        # Create enhanced reasoning
        discrepancy_reasoning = self.generate_discrepancy_reasoning(discrepancy_factors)
        
        # Combine base reasoning with discrepancy insights
        if hasattr(base_recommendation, 'reasoning'):
            enhanced_reasoning = f"{base_recommendation.reasoning}\n\n{discrepancy_reasoning}"
        else:
            enhanced_reasoning = discrepancy_reasoning
        
        # Create enhanced recommendation
        enhanced_recommendation = type('EnhancedParlayRecommendation', (), {
            'confidence': enhanced_confidence,
            'reasoning': enhanced_reasoning,
            'base_confidence': base_confidence,
            'discrepancy_boost': total_boost,
            'arbitrage_signals': len([f for f in discrepancy_factors if f.factor_type == 'market_arbitrage']),
            'value_signals': len([f for f in discrepancy_factors if f.factor_type == 'market_value']),
            'high_value_factors': discrepancy_factors,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })()
        
        # Copy other attributes from base recommendation
        for attr in dir(base_recommendation):
            if not attr.startswith('_') and attr not in ['confidence', 'reasoning']:
                try:
                    setattr(enhanced_recommendation, attr, getattr(base_recommendation, attr))
                except:
                    pass
        
        return enhanced_recommendation
    
    def generate_discrepancy_reasoning(self, discrepancy_factors: List[ReasoningFactor]) -> str:
        """
        Generate human-readable reasoning from discrepancy factors.
        
        Args:
            discrepancy_factors: List of discrepancy-based factors
            
        Returns:
            Formatted reasoning text
        """
        if not discrepancy_factors:
            return ""
        
        reasoning_parts = ["🎯 MARKET DISCREPANCY ANALYSIS:"]
        
        arbitrage_factors = [f for f in discrepancy_factors if f.factor_type == 'market_arbitrage']
        value_factors = [f for f in discrepancy_factors if f.factor_type == 'market_value']
        
        if arbitrage_factors:
            reasoning_parts.append("\n💰 ARBITRAGE OPPORTUNITIES DETECTED:")
            for factor in arbitrage_factors:
                profit_pct = factor.supporting_data.get('profit_percentage', 0)
                market_type = factor.supporting_data.get('market_type', 'unknown')
                reasoning_parts.append(f"  • {market_type.upper()} market: {profit_pct:.1%} guaranteed profit")
                reasoning_parts.append(f"    Confidence: {factor.confidence:.1%}")
        
        if value_factors:
            reasoning_parts.append("\n📈 VALUE OPPORTUNITIES IDENTIFIED:")
            for factor in value_factors:
                edge_pct = factor.supporting_data.get('edge_percentage', 0)
                market_type = factor.supporting_data.get('market_type', 'unknown')
                value_score = factor.supporting_data.get('value_score', 0)
                reasoning_parts.append(f"  • {market_type.upper()} market: {edge_pct:.1%} edge over fair odds")
                reasoning_parts.append(f"    Value Score: {value_score:.1f}, Confidence: {factor.confidence:.1%}")
        
        # Add strategic implications
        if arbitrage_factors:
            reasoning_parts.append("\n🎯 STRATEGIC IMPLICATIONS:")
            reasoning_parts.append("  • Arbitrage opportunities suggest market inefficiencies")
            reasoning_parts.append("  • Consider splitting action across multiple sportsbooks")
            reasoning_parts.append("  • Time-sensitive - odds may converge quickly")
        
        if value_factors:
            if not arbitrage_factors:
                reasoning_parts.append("\n🎯 STRATEGIC IMPLICATIONS:")
            reasoning_parts.append("  • Value opportunities indicate mispriced markets")
            reasoning_parts.append("  • Focus on outcomes with highest edge percentages")
            reasoning_parts.append("  • Consider increasing position size for high-confidence values")
        
        return "\n".join(reasoning_parts)
    
    def generate_enhanced_parlay_recommendation(self, 
                                              game_ids: List[str],
                                              additional_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate enhanced parlay recommendation with market discrepancy integration.
        
        Args:
            game_ids: List of games to analyze
            additional_context: Additional context for base strategist
            
        Returns:
            Enhanced recommendation with discrepancy analysis
        """
        logger.info(f"Generating enhanced parlay recommendation for {len(game_ids)} games")
        
        # Scan for market discrepancies
        all_discrepancies = self.scan_market_discrepancies(game_ids)
        
        # Get high-value signals
        high_value_signals = self.discrepancy_detector.get_high_value_signals(
            min_confidence=self.min_value_confidence
        )
        
        # Generate base recommendation if base strategist available
        base_recommendation = None
        if self.base_strategist and hasattr(self.base_strategist, 'generate_parlay_recommendation'):
            try:
                base_recommendation = self.base_strategist.generate_parlay_recommendation(
                    game_ids, additional_context
                )
            except Exception as e:
                logger.warning(f"Base strategist failed: {e}")
        
        # Extract discrepancy factors for each game
        all_discrepancy_factors = []
        game_specific_factors = {}
        
        for game_id in game_ids:
            if game_id in all_discrepancies:
                factors = self.extract_discrepancy_factors(game_id, all_discrepancies[game_id])
                all_discrepancy_factors.extend(factors)
                game_specific_factors[game_id] = factors
        
        # Create enhanced recommendation
        if base_recommendation:
            enhanced_recommendation = self.integrate_discrepancy_signals(
                base_recommendation, all_discrepancy_factors
            )
        else:
            # Create standalone recommendation based on discrepancies
            enhanced_recommendation = self.create_discrepancy_based_recommendation(
                game_ids, all_discrepancy_factors, high_value_signals
            )
        
        # Compile comprehensive response
        response = {
            'enhanced_recommendation': enhanced_recommendation,
            'base_recommendation': base_recommendation,
            'market_discrepancies': {
                game_id: [asdict(disc) for disc in discs] 
                for game_id, discs in all_discrepancies.items()
            },
            'high_value_signals': high_value_signals,
            'discrepancy_factors': [asdict(factor) for factor in all_discrepancy_factors],
            'game_specific_factors': {
                game_id: [asdict(factor) for factor in factors]
                for game_id, factors in game_specific_factors.items()
            },
            'summary_stats': self.discrepancy_detector.get_summary_stats(),
            'analysis_metadata': {
                'games_analyzed': len(game_ids),
                'discrepancies_found': sum(len(discs) for discs in all_discrepancies.values()),
                'arbitrage_opportunities': len(self.discrepancy_detector.arbitrage_opportunities),
                'value_opportunities': len(self.discrepancy_detector.value_opportunities),
                'analysis_timestamp': datetime.now(timezone.utc).isoformat()
            }
        }
        
        logger.info(f"Enhanced recommendation complete - found {response['analysis_metadata']['discrepancies_found']} discrepancies")
        return response
    
    def create_discrepancy_based_recommendation(self,
                                              game_ids: List[str],
                                              discrepancy_factors: List[ReasoningFactor],
                                              high_value_signals: List[Dict[str, Any]]) -> Any:
        """
        Create recommendation based purely on market discrepancy analysis.
        
        Args:
            game_ids: List of game IDs
            discrepancy_factors: Discrepancy-based factors
            high_value_signals: High-value signals from detector
            
        Returns:
            Discrepancy-based recommendation
        """
        if not discrepancy_factors:
            confidence = 0.3
            reasoning = "No significant market discrepancies detected. Proceed with standard analysis."
        else:
            # Calculate confidence based on factor quality
            total_confidence = sum(f.confidence * f.weight for f in discrepancy_factors)
            avg_confidence = total_confidence / len(discrepancy_factors) if discrepancy_factors else 0.5
            confidence = min(avg_confidence, 0.9)  # Cap at 90%
            
            reasoning = self.generate_discrepancy_reasoning(discrepancy_factors)
        
        # Create recommendation structure
        recommendation = type('DiscrepancyBasedRecommendation', (), {
            'confidence': confidence,
            'reasoning': reasoning,
            'recommendation_type': 'discrepancy_based',
            'games_analyzed': game_ids,
            'arbitrage_opportunities': len([f for f in discrepancy_factors if f.factor_type == 'market_arbitrage']),
            'value_opportunities': len([f for f in discrepancy_factors if f.factor_type == 'market_value']),
            'high_value_signals': high_value_signals,
            'recommended_actions': self.generate_recommended_actions(high_value_signals),
            'timestamp': datetime.now(timezone.utc).isoformat()
        })()
        
        return recommendation
    
    def generate_recommended_actions(self, high_value_signals: List[Dict[str, Any]]) -> List[str]:
        """Generate specific recommended actions based on signals."""
        actions = []
        
        for signal in high_value_signals:
            if signal['signal_type'] == 'arbitrage_opportunity':
                actions.append(f"ARBITRAGE: {signal['recommended_action']}")
            elif signal['signal_type'] == 'value_opportunity':
                actions.append(f"VALUE BET: {signal['recommended_action']}")
        
        if not actions:
            actions.append("Monitor for emerging market discrepancies")
        
        return actions
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status and performance metrics."""
        return {
            'discrepancy_detector_status': 'active',
            'last_scan_time': self.last_scan_time.isoformat() if self.last_scan_time else None,
            'cached_games': len(self.cached_discrepancies),
            'base_strategist_available': self.base_strategist is not None,
            'configuration': {
                'discrepancy_weight': self.discrepancy_weight,
                'min_arbitrage_confidence': self.min_arbitrage_confidence,
                'min_value_confidence': self.min_value_confidence
            },
            'detector_stats': self.discrepancy_detector.get_summary_stats()
        }


def main():
    """Main function for testing enhanced strategist with discrepancy detection."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🎯 Enhanced ParlayStrategist with Market Discrepancy Integration - JIRA-023A")
    print("=" * 80)
    
    # Initialize enhanced strategist
    strategist = EnhancedParlayStrategistWithDiscrepancy(
        discrepancy_weight=0.3,
        min_arbitrage_confidence=0.8,
        min_value_confidence=0.7
    )
    
    # Test with sample games
    test_games = ['game_001', 'game_002', 'game_003']
    
    print(f"🔍 Generating enhanced recommendation for games: {', '.join(test_games)}")
    
    # Generate enhanced recommendation
    result = strategist.generate_enhanced_parlay_recommendation(test_games)
    
    # Display results
    print(f"\n📊 ANALYSIS RESULTS")
    print("=" * 50)
    
    metadata = result['analysis_metadata']
    print(f"Games analyzed: {metadata['games_analyzed']}")
    print(f"Discrepancies found: {metadata['discrepancies_found']}")
    print(f"Arbitrage opportunities: {metadata['arbitrage_opportunities']}")
    print(f"Value opportunities: {metadata['value_opportunities']}")
    
    # Show enhanced recommendation
    enhanced_rec = result['enhanced_recommendation']
    print(f"\n🎯 ENHANCED RECOMMENDATION")
    print("=" * 50)
    print(f"Confidence: {enhanced_rec.confidence:.1%}")
    
    if hasattr(enhanced_rec, 'discrepancy_boost'):
        print(f"Discrepancy boost: +{enhanced_rec.discrepancy_boost:.1%}")
        print(f"Arbitrage signals: {enhanced_rec.arbitrage_signals}")
        print(f"Value signals: {enhanced_rec.value_signals}")
    
    print(f"\nReasoning:")
    print(enhanced_rec.reasoning)
    
    # Show high-value signals
    if result['high_value_signals']:
        print(f"\n🚨 HIGH-VALUE SIGNALS")
        print("=" * 50)
        for i, signal in enumerate(result['high_value_signals'][:3], 1):
            print(f"{i}. {signal['signal_type'].replace('_', ' ').title()}")
            print(f"   Game: {signal['game_id']}")
            print(f"   Confidence: {signal['confidence']:.1%}")
            print(f"   Action: {signal['recommended_action']}")
    
    # System status
    status = strategist.get_system_status()
    print(f"\n⚙️ SYSTEM STATUS")
    print("=" * 50)
    print(f"Discrepancy detector: {status['discrepancy_detector_status']}")
    print(f"Last scan: {status['last_scan_time']}")
    print(f"Cached games: {status['cached_games']}")
    print(f"Base strategist: {'Available' if status['base_strategist_available'] else 'Not available'}")
    
    print(f"\n✅ JIRA-023A Enhanced ParlayStrategist Integration Complete!")
    print(f"🎯 Market discrepancy signals successfully integrated")


if __name__ == "__main__":
    main()
