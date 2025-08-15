#!/usr/bin/env python3
"""
Market Discrepancy Detector - JIRA-023A

Identifies arbitrage and value opportunities by comparing odds across sportsbooks.
Uses OddsFetcherTool to poll markets and detect significant discrepancies that
could represent profitable betting opportunities.
"""

import logging
import json
import time
import asyncio
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import statistics

# Import OddsFetcherTool from JIRA-004
try:
    from tools.odds_fetcher_tool import OddsFetcherTool, GameOdds, BookOdds, Selection
    HAS_ODDS_FETCHER = True
except ImportError:
    HAS_ODDS_FETCHER = False
    # Mock classes for type hints when not available
    class GameOdds:
        pass
    class BookOdds:
        pass
    class Selection:
        pass
    logging.warning("OddsFetcherTool not available - using mock data")

logger = logging.getLogger(__name__)


@dataclass
class MarketDiscrepancy:
    """Represents a detected market discrepancy."""
    game_id: str
    market_type: str  # 'h2h', 'spreads', 'totals'
    market_key: str   # Specific market identifier
    discrepancy_type: str  # 'arbitrage', 'value', 'suspicious'
    
    # Best odds details
    best_odds: Dict[str, Any]  # {outcome: {sportsbook: str, odds: float}}
    worst_odds: Dict[str, Any]  # {outcome: {sportsbook: str, odds: float}}
    
    # Analysis metrics
    arbitrage_percentage: float  # Negative means guaranteed profit
    implied_probability_spread: float  # Difference in implied probabilities
    value_score: float  # How significant the value opportunity is
    confidence_score: float  # Confidence in the discrepancy
    
    # Metadata
    sportsbooks_compared: List[str]
    detection_timestamp: str
    market_data: Dict[str, Any]
    
    # Risk assessment
    risk_factors: List[str] = field(default_factory=list)
    recommended_action: str = ""
    profit_potential: float = 0.0


@dataclass
class ArbitrageOpportunity:
    """Specific arbitrage opportunity details."""
    game_id: str
    market_type: str
    total_investment: float
    guaranteed_profit: float
    profit_percentage: float
    
    bets_required: List[Dict[str, Any]]  # List of bets to place
    sportsbooks_involved: List[str]
    
    # Risk assessment
    risk_level: str  # 'low', 'medium', 'high'
    time_sensitivity: str  # 'immediate', 'short', 'medium'
    liquidity_concerns: List[str]
    
    detection_timestamp: str
    expires_at: Optional[str] = None


@dataclass
class ValueOpportunity:
    """Specific value betting opportunity."""
    game_id: str
    market_type: str
    outcome: str
    sportsbook: str
    
    offered_odds: float
    fair_odds: float  # Estimated true odds
    implied_edge: float  # Percentage edge over fair odds
    
    # Supporting analysis
    consensus_odds: float  # Average across all books
    outlier_strength: float  # How much this deviates from consensus
    market_efficiency_score: float  # How efficiently priced this market is
    
    # Recommendation
    suggested_stake: float
    expected_value: float
    confidence_level: str  # 'low', 'medium', 'high'
    
    detection_timestamp: str


class MarketDiscrepancyDetector:
    """
    Main market discrepancy detection system.
    
    Compares odds across sportsbooks to identify arbitrage opportunities,
    value bets, and suspicious market movements.
    """
    
    def __init__(self,
                 min_arbitrage_profit: float = 0.02,  # 2% minimum profit
                 min_value_edge: float = 0.05,        # 5% minimum value edge
                 max_update_age: int = 300,           # 5 minutes max age
                 confidence_threshold: float = 0.7):  # 70% confidence minimum
        """
        Initialize the market discrepancy detector.
        
        Args:
            min_arbitrage_profit: Minimum profit percentage for arbitrage alerts
            min_value_edge: Minimum edge percentage for value bet alerts
            max_update_age: Maximum age of odds data in seconds
            confidence_threshold: Minimum confidence for alerting
        """
        self.min_arbitrage_profit = min_arbitrage_profit
        self.min_value_edge = min_value_edge
        self.max_update_age = max_update_age
        self.confidence_threshold = confidence_threshold
        
        # Initialize OddsFetcherTool if available
        if HAS_ODDS_FETCHER:
            self.odds_fetcher = OddsFetcherTool()
        else:
            self.odds_fetcher = None
            
        # Cache for market data
        self.market_cache = {}
        self.last_update = {}
        
        # Tracking
        self.detected_discrepancies = []
        self.arbitrage_opportunities = []
        self.value_opportunities = []
        
        logger.info(f"Initialized MarketDiscrepancyDetector - Min Arbitrage: {min_arbitrage_profit:.1%}, Min Value: {min_value_edge:.1%}")
    
    def odds_to_implied_probability(self, odds: float) -> float:
        """Convert odds to implied probability."""
        if odds > 0:  # American odds positive
            return 100 / (odds + 100)
        else:  # American odds negative
            return abs(odds) / (abs(odds) + 100)
    
    def implied_probability_to_odds(self, prob: float) -> float:
        """Convert implied probability to American odds."""
        if prob >= 0.5:
            return -(prob / (1 - prob)) * 100
        else:
            return ((1 - prob) / prob) * 100
    
    def calculate_arbitrage_percentage(self, implied_probs: List[float]) -> float:
        """
        Calculate arbitrage percentage.
        
        Args:
            implied_probs: List of implied probabilities for all outcomes
            
        Returns:
            Arbitrage percentage (negative means guaranteed profit)
        """
        return sum(implied_probs) - 1.0
    
    def find_best_odds_per_outcome(self, market_data: Dict[str, BookOdds]) -> Dict[str, Dict[str, Any]]:
        """
        Find the best odds for each outcome across all sportsbooks.
        
        Args:
            market_data: Dictionary of sportsbook -> odds data
            
        Returns:
            Dictionary of outcome -> {sportsbook, odds, implied_prob}
        """
        best_odds = {}
        
        # Collect all possible outcomes
        all_outcomes = set()
        for book_odds in market_data.values():
            if hasattr(book_odds, 'selections') and book_odds.selections:
                for selection in book_odds.selections:
                    all_outcomes.add(selection.name)
        
        # Find best odds for each outcome
        for outcome in all_outcomes:
            best_odds[outcome] = {
                'sportsbook': None,
                'odds': None,
                'implied_prob': 1.0  # Worst case
            }
            
            for sportsbook, book_odds in market_data.items():
                if hasattr(book_odds, 'selections') and book_odds.selections:
                    for selection in book_odds.selections:
                        if selection.name == outcome and selection.price:
                            implied_prob = self.odds_to_implied_probability(selection.price)
                            
                            # Best odds = lowest implied probability
                            if implied_prob < best_odds[outcome]['implied_prob']:
                                best_odds[outcome] = {
                                    'sportsbook': sportsbook,
                                    'odds': selection.price,
                                    'implied_prob': implied_prob
                                }
        
        return best_odds
    
    def detect_arbitrage_opportunity(self, 
                                   game_id: str,
                                   market_type: str,
                                   market_data: Dict[str, BookOdds]) -> Optional[ArbitrageOpportunity]:
        """
        Detect arbitrage opportunities in market data.
        
        Args:
            game_id: Game identifier
            market_type: Type of market (h2h, spreads, totals)
            market_data: Market data from multiple sportsbooks
            
        Returns:
            ArbitrageOpportunity if found, None otherwise
        """
        if len(market_data) < 2:
            return None
        
        best_odds = self.find_best_odds_per_outcome(market_data)
        
        if len(best_odds) < 2:
            return None
        
        # Calculate arbitrage percentage
        implied_probs = [odds_data['implied_prob'] for odds_data in best_odds.values()]
        arbitrage_pct = self.calculate_arbitrage_percentage(implied_probs)
        
        # Check if this is a profitable arbitrage (negative percentage)
        if arbitrage_pct < -self.min_arbitrage_profit:
            # Calculate bet amounts for $100 total investment
            total_investment = 100.0
            bets_required = []
            
            for outcome, odds_data in best_odds.items():
                stake = (odds_data['implied_prob'] * total_investment) / sum(implied_probs)
                potential_return = stake * (1 / odds_data['implied_prob'])
                
                bets_required.append({
                    'outcome': outcome,
                    'sportsbook': odds_data['sportsbook'],
                    'odds': odds_data['odds'],
                    'stake': stake,
                    'potential_return': potential_return
                })
            
            guaranteed_profit = min(bet['potential_return'] for bet in bets_required) - total_investment
            profit_percentage = guaranteed_profit / total_investment
            
            # Assess risk level
            risk_level = self.assess_arbitrage_risk(market_data, best_odds)
            
            return ArbitrageOpportunity(
                game_id=game_id,
                market_type=market_type,
                total_investment=total_investment,
                guaranteed_profit=guaranteed_profit,
                profit_percentage=profit_percentage,
                bets_required=bets_required,
                sportsbooks_involved=list(set(odds_data['sportsbook'] for odds_data in best_odds.values())),
                risk_level=risk_level,
                time_sensitivity='immediate',  # Arbitrage opportunities are time-sensitive
                liquidity_concerns=[],
                detection_timestamp=datetime.now(timezone.utc).isoformat()
            )
        
        return None
    
    def detect_value_opportunities(self,
                                 game_id: str,
                                 market_type: str,
                                 market_data: Dict[str, BookOdds]) -> List[ValueOpportunity]:
        """
        Detect value betting opportunities.
        
        Args:
            game_id: Game identifier
            market_type: Type of market
            market_data: Market data from multiple sportsbooks
            
        Returns:
            List of ValueOpportunity objects
        """
        if len(market_data) < 3:  # Need at least 3 books for consensus
            return []
        
        value_opportunities = []
        
        # Collect all odds for each outcome
        outcome_odds = defaultdict(list)
        
        for sportsbook, book_odds in market_data.items():
            if hasattr(book_odds, 'selections') and book_odds.selections:
                for selection in book_odds.selections:
                    if selection.price:
                        outcome_odds[selection.name].append({
                            'sportsbook': sportsbook,
                            'odds': selection.price,
                            'implied_prob': self.odds_to_implied_probability(selection.price)
                        })
        
        # Analyze each outcome for value opportunities
        for outcome, odds_list in outcome_odds.items():
            if len(odds_list) < 3:  # Need at least 3 data points
                continue
            
            # Calculate consensus (remove outliers and average)
            implied_probs = [odds_data['implied_prob'] for odds_data in odds_list]
            consensus_prob = self.calculate_robust_consensus(implied_probs)
            consensus_odds = self.implied_probability_to_odds(consensus_prob)
            
            # Find outliers that might represent value
            for odds_data in odds_list:
                edge = (consensus_prob - odds_data['implied_prob']) / consensus_prob
                
                if edge > self.min_value_edge:
                    # Calculate additional metrics
                    outlier_strength = self.calculate_outlier_strength(odds_data['implied_prob'], implied_probs)
                    market_efficiency = self.calculate_market_efficiency(implied_probs)
                    
                    # Determine confidence level
                    confidence_level = self.determine_confidence_level(edge, outlier_strength, market_efficiency)
                    
                    if confidence_level != 'low':  # Only include medium/high confidence
                        value_opportunities.append(ValueOpportunity(
                            game_id=game_id,
                            market_type=market_type,
                            outcome=outcome,
                            sportsbook=odds_data['sportsbook'],
                            offered_odds=odds_data['odds'],
                            fair_odds=consensus_odds,
                            implied_edge=edge,
                            consensus_odds=consensus_odds,
                            outlier_strength=outlier_strength,
                            market_efficiency_score=market_efficiency,
                            suggested_stake=self.calculate_kelly_stake(edge, odds_data['odds']),
                            expected_value=edge * 100,  # Convert to percentage
                            confidence_level=confidence_level,
                            detection_timestamp=datetime.now(timezone.utc).isoformat()
                        ))
        
        return value_opportunities
    
    def calculate_robust_consensus(self, implied_probs: List[float]) -> float:
        """Calculate robust consensus probability by removing outliers."""
        if len(implied_probs) <= 2:
            return statistics.mean(implied_probs)
        
        # Remove extreme outliers (beyond 2 standard deviations)
        mean_prob = statistics.mean(implied_probs)
        std_prob = statistics.stdev(implied_probs)
        
        filtered_probs = [p for p in implied_probs 
                         if abs(p - mean_prob) <= 2 * std_prob]
        
        if len(filtered_probs) < 2:
            return mean_prob
        
        return statistics.mean(filtered_probs)
    
    def calculate_outlier_strength(self, value: float, all_values: List[float]) -> float:
        """Calculate how much of an outlier a value is."""
        if len(all_values) <= 1:
            return 0.0
        
        mean_val = statistics.mean(all_values)
        std_val = statistics.stdev(all_values) if len(all_values) > 1 else 0.1
        
        return abs(value - mean_val) / std_val if std_val > 0 else 0.0
    
    def calculate_market_efficiency(self, implied_probs: List[float]) -> float:
        """Calculate market efficiency score (lower = more efficient)."""
        if len(implied_probs) <= 1:
            return 1.0
        
        coefficient_of_variation = statistics.stdev(implied_probs) / statistics.mean(implied_probs)
        return min(coefficient_of_variation, 1.0)  # Cap at 1.0
    
    def determine_confidence_level(self, 
                                 edge: float, 
                                 outlier_strength: float, 
                                 market_efficiency: float) -> str:
        """Determine confidence level for value opportunity."""
        confidence_score = 0.0
        
        # Edge contribution (higher edge = higher confidence)
        confidence_score += min(edge * 10, 0.4)  # Max 40% from edge
        
        # Outlier strength contribution
        confidence_score += min(outlier_strength * 0.1, 0.3)  # Max 30% from outlier strength
        
        # Market efficiency contribution (lower efficiency = higher confidence)
        confidence_score += min((1 - market_efficiency) * 0.3, 0.3)  # Max 30% from efficiency
        
        if confidence_score >= 0.7:
            return 'high'
        elif confidence_score >= 0.5:
            return 'medium'
        else:
            return 'low'
    
    def calculate_kelly_stake(self, edge: float, odds: float) -> float:
        """Calculate Kelly criterion stake for value bet."""
        # Convert American odds to decimal
        if odds > 0:
            decimal_odds = (odds / 100) + 1
        else:
            decimal_odds = (100 / abs(odds)) + 1
        
        # Kelly formula: f = (bp - q) / b
        # where b = odds-1, p = true probability, q = 1-p
        b = decimal_odds - 1
        p = 1 / (1 + (1 / edge))  # Implied true probability
        q = 1 - p
        
        kelly_fraction = (b * p - q) / b
        
        # Cap at 10% of bankroll for safety
        return min(max(kelly_fraction, 0), 0.1)
    
    def assess_arbitrage_risk(self, 
                            market_data: Dict[str, BookOdds], 
                            best_odds: Dict[str, Dict[str, Any]]) -> str:
        """Assess risk level for arbitrage opportunity."""
        risk_factors = []
        
        # Check number of sportsbooks involved
        unique_books = set(odds_data['sportsbook'] for odds_data in best_odds.values())
        if len(unique_books) <= 2:
            risk_factors.append('limited_sportsbooks')
        
        # Check if odds are from smaller/less reliable books
        major_books = {'draftkings', 'fanduel', 'betmgm', 'caesars', 'pointsbet'}
        if not any(book.lower() in major_books for book in unique_books):
            risk_factors.append('minor_sportsbooks')
        
        # Check profit margin (very high margins might be suspicious)
        implied_probs = [odds_data['implied_prob'] for odds_data in best_odds.values()]
        arbitrage_pct = abs(self.calculate_arbitrage_percentage(implied_probs))
        
        if arbitrage_pct > 0.1:  # > 10% profit
            risk_factors.append('suspicious_margin')
        
        # Determine overall risk level
        if len(risk_factors) == 0:
            return 'low'
        elif len(risk_factors) <= 2:
            return 'medium'
        else:
            return 'high'
    
    def fetch_market_data(self, 
                         game_id: str, 
                         market_type: str = 'h2h') -> Optional[Dict[str, BookOdds]]:
        """
        Fetch market data for a specific game and market type.
        
        Args:
            game_id: Game identifier
            market_type: Type of market to fetch
            
        Returns:
            Dictionary of sportsbook -> odds data
        """
        if not self.odds_fetcher:
            # Return mock data for testing
            return self.generate_mock_market_data(game_id, market_type)
        
        try:
            # Use OddsFetcherTool to get odds
            game_odds = self.odds_fetcher.get_game_odds(game_id)
            
            if not game_odds:
                logger.warning(f"No odds data found for game {game_id}")
                return None
            
            # Extract relevant market data
            market_data = {}
            
            for book_odds in game_odds.books:
                if hasattr(book_odds, 'key') and hasattr(book_odds, 'markets'):
                    for market in book_odds.markets:
                        if market.key == market_type:
                            market_data[book_odds.key] = market
                            break
            
            return market_data if market_data else None
            
        except Exception as e:
            logger.error(f"Failed to fetch market data for {game_id}: {e}")
            return None
    
    def generate_mock_market_data(self, game_id: str, market_type: str) -> Dict[str, Any]:
        """Generate mock market data for testing."""
        import random
        
        # Mock sportsbooks
        sportsbooks = ['draftkings', 'fanduel', 'betmgm', 'caesars', 'pointsbet']
        
        # Base odds with some variation
        base_home_odds = -110
        base_away_odds = +105
        
        market_data = {}
        
        for book in sportsbooks:
            # Add some random variation
            home_variation = random.uniform(-20, 20)
            away_variation = random.uniform(-20, 20)
            
            # Create mock BookOdds-like structure
            mock_selections = [
                type('Selection', (), {
                    'name': 'home',
                    'price': base_home_odds + home_variation
                })(),
                type('Selection', (), {
                    'name': 'away', 
                    'price': base_away_odds + away_variation
                })()
            ]
            
            market_data[book] = type('BookOdds', (), {
                'selections': mock_selections,
                'key': book
            })()
        
        # Occasionally create arbitrage opportunity
        if random.random() < 0.1:  # 10% chance
            # Make one book have significantly better odds on each side
            market_data['draftkings'].selections[0].price = -90  # Better home odds
            market_data['fanduel'].selections[1].price = +140   # Better away odds
        
        return market_data
    
    def scan_game_for_discrepancies(self, game_id: str) -> List[MarketDiscrepancy]:
        """
        Scan a single game for all types of market discrepancies.
        
        Args:
            game_id: Game identifier
            
        Returns:
            List of detected discrepancies
        """
        discrepancies = []
        market_types = ['h2h', 'spreads', 'totals']
        
        for market_type in market_types:
            try:
                # Fetch market data
                market_data = self.fetch_market_data(game_id, market_type)
                
                if not market_data or len(market_data) < 2:
                    continue
                
                # Check for arbitrage
                arbitrage_opp = self.detect_arbitrage_opportunity(game_id, market_type, market_data)
                if arbitrage_opp:
                    self.arbitrage_opportunities.append(arbitrage_opp)
                    
                    # Create corresponding discrepancy record
                    best_odds = self.find_best_odds_per_outcome(market_data)
                    
                    discrepancy = MarketDiscrepancy(
                        game_id=game_id,
                        market_type=market_type,
                        market_key=f"{game_id}_{market_type}",
                        discrepancy_type='arbitrage',
                        best_odds=best_odds,
                        worst_odds={},  # TODO: Calculate worst odds
                        arbitrage_percentage=arbitrage_opp.profit_percentage,
                        implied_probability_spread=0.0,  # TODO: Calculate
                        value_score=arbitrage_opp.profit_percentage * 10,  # Arbitrage gets high value score
                        confidence_score=0.9 if arbitrage_opp.risk_level == 'low' else 0.7,
                        sportsbooks_compared=list(market_data.keys()),
                        detection_timestamp=arbitrage_opp.detection_timestamp,
                        market_data=market_data,
                        recommended_action=f"Arbitrage opportunity: {arbitrage_opp.profit_percentage:.1%} profit",
                        profit_potential=arbitrage_opp.guaranteed_profit
                    )
                    discrepancies.append(discrepancy)
                
                # Check for value opportunities
                value_opps = self.detect_value_opportunities(game_id, market_type, market_data)
                for value_opp in value_opps:
                    self.value_opportunities.append(value_opp)
                    
                    # Create corresponding discrepancy record
                    discrepancy = MarketDiscrepancy(
                        game_id=game_id,
                        market_type=market_type,
                        market_key=f"{game_id}_{market_type}_{value_opp.outcome}",
                        discrepancy_type='value',
                        best_odds={value_opp.outcome: {
                            'sportsbook': value_opp.sportsbook,
                            'odds': value_opp.offered_odds
                        }},
                        worst_odds={},
                        arbitrage_percentage=0.0,
                        implied_probability_spread=value_opp.implied_edge,
                        value_score=value_opp.expected_value,
                        confidence_score=0.8 if value_opp.confidence_level == 'high' else 0.6,
                        sportsbooks_compared=list(market_data.keys()),
                        detection_timestamp=value_opp.detection_timestamp,
                        market_data=market_data,
                        recommended_action=f"Value bet: {value_opp.implied_edge:.1%} edge",
                        profit_potential=value_opp.expected_value
                    )
                    discrepancies.append(discrepancy)
                    
            except Exception as e:
                logger.error(f"Error scanning {game_id} {market_type}: {e}")
                continue
        
        return discrepancies
    
    def scan_multiple_games(self, game_ids: List[str]) -> Dict[str, List[MarketDiscrepancy]]:
        """
        Scan multiple games for discrepancies.
        
        Args:
            game_ids: List of game identifiers
            
        Returns:
            Dictionary of game_id -> list of discrepancies
        """
        all_discrepancies = {}
        
        for game_id in game_ids:
            try:
                discrepancies = self.scan_game_for_discrepancies(game_id)
                if discrepancies:
                    all_discrepancies[game_id] = discrepancies
                    logger.info(f"Found {len(discrepancies)} discrepancies for game {game_id}")
                
                # Small delay to avoid rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Failed to scan game {game_id}: {e}")
        
        return all_discrepancies
    
    def get_high_value_signals(self, min_confidence: float = 0.7) -> List[Dict[str, Any]]:
        """
        Get high-value signals for ParlayStrategistAgent integration.
        
        Args:
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of high-value signals
        """
        signals = []
        
        # Add arbitrage opportunities as signals
        for arbitrage in self.arbitrage_opportunities:
            if arbitrage.risk_level in ['low', 'medium']:
                signals.append({
                    'signal_type': 'arbitrage_opportunity',
                    'game_id': arbitrage.game_id,
                    'market_type': arbitrage.market_type,
                    'profit_potential': arbitrage.profit_percentage,
                    'confidence': 0.9 if arbitrage.risk_level == 'low' else 0.7,
                    'urgency': 'high',  # Arbitrage is time-sensitive
                    'recommended_action': f"Arbitrage bet with {arbitrage.profit_percentage:.1%} guaranteed profit",
                    'metadata': {
                        'sportsbooks': arbitrage.sportsbooks_involved,
                        'bets_required': arbitrage.bets_required
                    }
                })
        
        # Add value opportunities as signals
        for value in self.value_opportunities:
            confidence_score = 0.8 if value.confidence_level == 'high' else 0.6
            
            if confidence_score >= min_confidence:
                signals.append({
                    'signal_type': 'value_opportunity',
                    'game_id': value.game_id,
                    'market_type': value.market_type,
                    'outcome': value.outcome,
                    'edge': value.implied_edge,
                    'confidence': confidence_score,
                    'urgency': 'medium',
                    'recommended_action': f"Value bet on {value.outcome} at {value.sportsbook}: {value.implied_edge:.1%} edge",
                    'metadata': {
                        'sportsbook': value.sportsbook,
                        'odds': value.offered_odds,
                        'fair_odds': value.fair_odds,
                        'suggested_stake': value.suggested_stake
                    }
                })
        
        # Sort by profit potential and confidence
        signals.sort(key=lambda x: x['confidence'] * x.get('edge', x.get('profit_potential', 0)), reverse=True)
        
        return signals
    
    def clear_old_opportunities(self, max_age_minutes: int = 30):
        """Clear opportunities older than specified age."""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)
        
        # Filter arbitrage opportunities
        self.arbitrage_opportunities = [
            opp for opp in self.arbitrage_opportunities
            if datetime.fromisoformat(opp.detection_timestamp.replace('Z', '+00:00')) > cutoff
        ]
        
        # Filter value opportunities
        self.value_opportunities = [
            opp for opp in self.value_opportunities
            if datetime.fromisoformat(opp.detection_timestamp.replace('Z', '+00:00')) > cutoff
        ]
        
        # Filter detected discrepancies
        self.detected_discrepancies = [
            disc for disc in self.detected_discrepancies
            if datetime.fromisoformat(disc.detection_timestamp.replace('Z', '+00:00')) > cutoff
        ]
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics of detected opportunities."""
        return {
            'total_arbitrage_opportunities': len(self.arbitrage_opportunities),
            'total_value_opportunities': len(self.value_opportunities),
            'total_discrepancies': len(self.detected_discrepancies),
            'avg_arbitrage_profit': statistics.mean([opp.profit_percentage for opp in self.arbitrage_opportunities]) if self.arbitrage_opportunities else 0.0,
            'avg_value_edge': statistics.mean([opp.implied_edge for opp in self.value_opportunities]) if self.value_opportunities else 0.0,
            'high_confidence_signals': len([s for s in self.get_high_value_signals() if s['confidence'] >= 0.8]),
            'last_scan_time': datetime.now(timezone.utc).isoformat()
        }


def main():
    """Main function for testing the market discrepancy detector."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🎯 Market Discrepancy Detector - JIRA-023A")
    print("=" * 60)
    
    # Initialize detector
    detector = MarketDiscrepancyDetector(
        min_arbitrage_profit=0.02,  # 2% minimum
        min_value_edge=0.05,        # 5% minimum
        confidence_threshold=0.7
    )
    
    # Test with sample game IDs
    sample_games = ['game_001', 'game_002', 'game_003']
    
    print("🔍 Scanning games for market discrepancies...")
    discrepancies = detector.scan_multiple_games(sample_games)
    
    # Display results
    total_discrepancies = sum(len(discs) for discs in discrepancies.values())
    print(f"\n📊 SCAN RESULTS")
    print("-" * 40)
    print(f"Games scanned: {len(sample_games)}")
    print(f"Total discrepancies found: {total_discrepancies}")
    print(f"Arbitrage opportunities: {len(detector.arbitrage_opportunities)}")
    print(f"Value opportunities: {len(detector.value_opportunities)}")
    
    # Show arbitrage opportunities
    if detector.arbitrage_opportunities:
        print(f"\n💰 ARBITRAGE OPPORTUNITIES")
        print("-" * 40)
        for i, opp in enumerate(detector.arbitrage_opportunities, 1):
            print(f"{i}. Game {opp.game_id} ({opp.market_type})")
            print(f"   Profit: {opp.profit_percentage:.2%} ({opp.risk_level} risk)")
            print(f"   Sportsbooks: {', '.join(opp.sportsbooks_involved)}")
            print(f"   Required bets: {len(opp.bets_required)}")
    
    # Show value opportunities
    if detector.value_opportunities:
        print(f"\n📈 VALUE OPPORTUNITIES")
        print("-" * 40)
        for i, opp in enumerate(detector.value_opportunities[:5], 1):  # Show top 5
            print(f"{i}. Game {opp.game_id} - {opp.outcome}")
            print(f"   Edge: {opp.implied_edge:.2%} at {opp.sportsbook}")
            print(f"   Confidence: {opp.confidence_level}")
            print(f"   Suggested stake: {opp.suggested_stake:.1%} of bankroll")
    
    # Show high-value signals for integration
    signals = detector.get_high_value_signals()
    if signals:
        print(f"\n🚨 HIGH-VALUE SIGNALS FOR PARLAY STRATEGIST")
        print("-" * 40)
        for i, signal in enumerate(signals[:3], 1):  # Show top 3
            print(f"{i}. {signal['signal_type'].title()}")
            print(f"   Game: {signal['game_id']}")
            print(f"   Confidence: {signal['confidence']:.1%}")
            print(f"   Action: {signal['recommended_action']}")
    
    # Summary stats
    stats = detector.get_summary_stats()
    print(f"\n📊 SUMMARY STATISTICS")
    print("-" * 40)
    print(f"Average arbitrage profit: {stats['avg_arbitrage_profit']:.2%}")
    print(f"Average value edge: {stats['avg_value_edge']:.2%}")
    print(f"High confidence signals: {stats['high_confidence_signals']}")
    
    print(f"\n✅ JIRA-023A Market Discrepancy Detector Complete!")
    print(f"🎯 Ready for integration with ParlayStrategistAgent")


if __name__ == "__main__":
    main()
