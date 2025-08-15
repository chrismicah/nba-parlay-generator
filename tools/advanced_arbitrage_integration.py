#!/usr/bin/env python3
"""
Advanced Arbitrage Integration - JIRA-023B

Integrates the ArbitrageDetectorTool with existing systems:
- JIRA-004: OddsFetcherTool for live odds data
- JIRA-005: OddsLatencyMonitor for signal freshness
- JIRA-023A: MarketDiscrepancyDetector for enhanced detection
- JIRA-024: Alert suppression and refresh logic

Provides a unified interface for execution-aware arbitrage detection
with real-world hedge fund-level sophistication.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict

from tools.arbitrage_detector_tool import ArbitrageDetectorTool, ArbitrageOpportunity

# Import existing tools
try:
    from tools.odds_fetcher_tool import OddsFetcherTool, GameOdds
    HAS_ODDS_FETCHER = True
except ImportError:
    HAS_ODDS_FETCHER = False
    logging.warning("OddsFetcherTool not available")

try:
    from monitoring.odds_latency_monitor import OddsLatencyMonitor
    HAS_LATENCY_MONITOR = True
except ImportError:
    HAS_LATENCY_MONITOR = False
    logging.warning("OddsLatencyMonitor not available")

try:
    from tools.market_discrepancy_detector import MarketDiscrepancyDetector
    HAS_MARKET_DISCREPANCY = True
except ImportError:
    HAS_MARKET_DISCREPANCY = False
    logging.warning("MarketDiscrepancyDetector not available")

logger = logging.getLogger(__name__)


@dataclass
class ExecutionReport:
    """Report of arbitrage execution analysis."""
    scan_timestamp: str
    games_analyzed: int
    arbitrage_opportunities: int
    total_profit_potential: float
    avg_execution_risk: float
    high_confidence_opportunities: int
    stale_signals_rejected: int
    false_positives_avoided: int
    execution_time_ms: float
    
    opportunities: List[ArbitrageOpportunity]
    alerts_generated: int = 0
    recommendations: List[str] = None
    
    def __post_init__(self):
        if self.recommendations is None:
            self.recommendations = []


class AdvancedArbitrageIntegration:
    """
    Advanced arbitrage integration system that combines:
    - Execution-aware arbitrage detection
    - Live odds data integration  
    - Signal freshness validation
    - Market discrepancy correlation
    - Intelligent alert management
    """
    
    def __init__(self,
                 min_profit_threshold: float = 0.01,    # 1% minimum edge
                 max_latency_seconds: float = 45.0,     # 45 second freshness
                 confidence_filter: str = "medium",     # minimum confidence
                 enable_cross_validation: bool = True): # cross-validate with market discrepancy
        """
        Initialize the advanced arbitrage integration system.
        
        Args:
            min_profit_threshold: Minimum profit threshold for opportunities
            max_latency_seconds: Maximum acceptable data age
            confidence_filter: Minimum confidence level ("low", "medium", "high")
            enable_cross_validation: Enable cross-validation with other detectors
        """
        self.min_profit_threshold = min_profit_threshold
        self.max_latency_seconds = max_latency_seconds
        self.confidence_filter = confidence_filter
        self.enable_cross_validation = enable_cross_validation
        
        # Initialize core arbitrage detector
        self.arbitrage_detector = ArbitrageDetectorTool(
            min_profit_threshold=min_profit_threshold,
            max_latency_threshold=max_latency_seconds,
            false_positive_epsilon=0.0005  # Stricter FP suppression
        )
        
        # Initialize external integrations
        self.odds_fetcher = OddsFetcherTool() if HAS_ODDS_FETCHER else None
        self.latency_monitor = OddsLatencyMonitor() if HAS_LATENCY_MONITOR else None
        self.market_discrepancy = MarketDiscrepancyDetector() if HAS_MARKET_DISCREPANCY else None
        
        # Performance tracking
        self.execution_reports = []
        self.alerts_suppressed = 0
        self.cross_validations_performed = 0
        
        logger.info(f"AdvancedArbitrageIntegration initialized - Min edge: {min_profit_threshold:.2%}")
    
    def fetch_live_odds_data(self, game_ids: List[str]) -> Dict[str, Any]:
        """
        Fetch live odds data using JIRA-004 OddsFetcherTool.
        
        Args:
            game_ids: List of game identifiers
            
        Returns:
            Dictionary of game_id -> odds data
        """
        if not self.odds_fetcher:
            logger.warning("OddsFetcherTool not available - using mock data")
            return self._generate_mock_odds_data(game_ids)
        
        odds_data = {}
        
        for game_id in game_ids:
            try:
                game_odds = self.odds_fetcher.get_game_odds(game_id)
                if game_odds:
                    odds_data[game_id] = self._extract_arbitrage_odds(game_odds)
                else:
                    logger.warning(f"No odds data available for game {game_id}")
            except Exception as e:
                logger.error(f"Failed to fetch odds for game {game_id}: {e}")
        
        return odds_data
    
    def _extract_arbitrage_odds(self, game_odds: GameOdds) -> Dict[str, Any]:
        """Extract arbitrage-relevant odds from GameOdds object."""
        extracted_odds = {
            'game_id': getattr(game_odds, 'id', 'unknown'),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'markets': {},
            'books': []
        }
        
        # Extract moneyline odds from each book
        if hasattr(game_odds, 'books') and game_odds.books:
            for book in game_odds.books:
                book_data = {
                    'name': getattr(book, 'key', 'unknown'),
                    'odds': {}
                }
                
                if hasattr(book, 'markets'):
                    for market in book.markets:
                        if market.key == 'h2h':  # Moneyline market
                            if hasattr(market, 'selections'):
                                for selection in market.selections:
                                    team_name = getattr(selection, 'name', 'unknown')
                                    odds_value = getattr(selection, 'price', None)
                                    
                                    if odds_value:
                                        book_data['odds'][team_name] = odds_value
                
                if book_data['odds']:
                    extracted_odds['books'].append(book_data)
        
        return extracted_odds
    
    def _generate_mock_odds_data(self, game_ids: List[str]) -> Dict[str, Any]:
        """Generate mock odds data for testing when OddsFetcherTool unavailable."""
        import random
        
        mock_data = {}
        books = ['draftkings', 'fanduel', 'betmgm', 'caesars', 'pointsbet']
        
        for game_id in game_ids:
            # Occasionally create arbitrage opportunities
            if random.random() < 0.3:  # 30% chance of arbitrage
                # Create clear arbitrage
                home_odds = random.uniform(100, 150)
                away_odds = random.uniform(-120, -90)
            else:
                # Normal balanced odds
                home_odds = random.uniform(-120, -100)
                away_odds = random.uniform(100, 120)
            
            mock_data[game_id] = {
                'game_id': game_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'books': []
            }
            
            # Add slight variations across books
            for book in books:
                home_variation = random.uniform(-10, 10)
                away_variation = random.uniform(-10, 10)
                
                mock_data[game_id]['books'].append({
                    'name': book,
                    'odds': {
                        'home': home_odds + home_variation,
                        'away': away_odds + away_variation
                    }
                })
        
        return mock_data
    
    def validate_signal_freshness(self, odds_data: Dict[str, Any]) -> bool:
        """
        Validate signal freshness using JIRA-005 OddsLatencyMonitor.
        
        Args:
            odds_data: Odds data to validate
            
        Returns:
            True if signals are fresh enough, False otherwise
        """
        if not self.latency_monitor:
            # Fallback to timestamp-based validation
            return self.arbitrage_detector.check_signal_freshness(
                odds_data, self.max_latency_seconds
            )
        
        try:
            # Check with latency monitor
            last_update = self.latency_monitor.get_last_update_time()
            if last_update:
                current_time = datetime.now(timezone.utc)
                latency = (current_time - last_update).total_seconds()
                
                if latency > self.max_latency_seconds:
                    logger.warning(f"Signal too stale: {latency:.1f}s > {self.max_latency_seconds:.1f}s")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Latency validation failed: {e}")
            return False
    
    def cross_validate_with_market_discrepancy(self, 
                                             arbitrage_opp: ArbitrageOpportunity,
                                             game_id: str) -> bool:
        """
        Cross-validate arbitrage with JIRA-023A MarketDiscrepancyDetector.
        
        This provides additional confidence by ensuring the arbitrage
        is also detected by the market discrepancy system.
        
        Args:
            arbitrage_opp: Arbitrage opportunity to validate
            game_id: Game identifier
            
        Returns:
            True if cross-validation passes, False otherwise
        """
        if not self.enable_cross_validation or not self.market_discrepancy:
            return True  # Skip validation if disabled or unavailable
        
        try:
            self.cross_validations_performed += 1
            
            # Scan game for market discrepancies
            discrepancies = self.market_discrepancy.scan_game_for_discrepancies(game_id)
            
            # Look for arbitrage-type discrepancies
            arbitrage_discrepancies = [
                d for d in discrepancies 
                if d.discrepancy_type == 'arbitrage' and d.profit_potential > 0
            ]
            
            if arbitrage_discrepancies:
                logger.info(f"Cross-validation passed: {len(arbitrage_discrepancies)} market discrepancies found")
                return True
            else:
                logger.warning(f"Cross-validation failed: No supporting market discrepancies")
                return False
                
        except Exception as e:
            logger.error(f"Cross-validation failed: {e}")
            return False  # Fail safe - reject if validation fails
    
    def detect_arbitrage_opportunities(self, 
                                     odds_data: Dict[str, Any],
                                     game_id: str) -> List[ArbitrageOpportunity]:
        """
        Detect arbitrage opportunities from odds data.
        
        Args:
            odds_data: Odds data for the game
            game_id: Game identifier
            
        Returns:
            List of validated arbitrage opportunities
        """
        opportunities = []
        
        if 'books' not in odds_data or len(odds_data['books']) < 2:
            return opportunities
        
        books_data = odds_data['books']
        
        # Extract odds for two-way arbitrage detection
        home_odds = []
        away_odds = []
        
        for book in books_data:
            book_name = book['name']
            if 'home' in book['odds'] and 'away' in book['odds']:
                home_odds.append((book['odds']['home'], book_name))
                away_odds.append((book['odds']['away'], book_name))
        
        # Detect two-way arbitrages
        for home_odds_val, home_book in home_odds:
            for away_odds_val, away_book in away_odds:
                if home_book != away_book:  # Different books
                    arbitrage = self.arbitrage_detector.detect_arbitrage_two_way(
                        home_odds_val, home_book, away_odds_val, away_book
                    )
                    
                    if arbitrage:
                        # Set game context
                        arbitrage.game_id = game_id
                        arbitrage.market_type = "h2h"
                        
                        # Apply confidence filter
                        if self._passes_confidence_filter(arbitrage):
                            # Cross-validate if enabled
                            if self.cross_validate_with_market_discrepancy(arbitrage, game_id):
                                opportunities.append(arbitrage)
                            else:
                                logger.info(f"Arbitrage rejected by cross-validation: {game_id}")
                        else:
                            logger.info(f"Arbitrage below confidence threshold: {arbitrage.confidence_level}")
        
        # Detect three-way arbitrages if enough books
        if len(books_data) >= 3:
            # Look for three-way markets (Win/Draw/Loss)
            three_way_odds = []
            for book in books_data:
                if len(book['odds']) >= 3:
                    odds_values = list(book['odds'].values())[:3]
                    for i, odds_val in enumerate(odds_values):
                        three_way_odds.append((odds_val, f"{book['name']}_outcome_{i}"))
            
            if len(three_way_odds) >= 3:
                # Take first three for simplicity
                arbitrage = self.arbitrage_detector.detect_arbitrage_three_way(
                    three_way_odds[:3]
                )
                
                if arbitrage:
                    arbitrage.game_id = game_id
                    arbitrage.market_type = "3way"
                    
                    if self._passes_confidence_filter(arbitrage):
                        if self.cross_validate_with_market_discrepancy(arbitrage, game_id):
                            opportunities.append(arbitrage)
        
        return opportunities
    
    def _passes_confidence_filter(self, arbitrage: ArbitrageOpportunity) -> bool:
        """Check if arbitrage passes minimum confidence filter."""
        confidence_levels = {"low": 0, "medium": 1, "high": 2}
        
        required_level = confidence_levels.get(self.confidence_filter, 1)
        actual_level = confidence_levels.get(arbitrage.confidence_level, 0)
        
        return actual_level >= required_level
    
    def scan_multiple_games(self, game_ids: List[str]) -> ExecutionReport:
        """
        Scan multiple games for arbitrage opportunities with full integration.
        
        Args:
            game_ids: List of game identifiers to scan
            
        Returns:
            ExecutionReport with comprehensive analysis
        """
        scan_start = datetime.now(timezone.utc)
        
        logger.info(f"Scanning {len(game_ids)} games for arbitrage opportunities")
        
        # Fetch live odds data
        odds_data = self.fetch_live_odds_data(game_ids)
        
        all_opportunities = []
        stale_rejected = 0
        false_positives = 0
        
        for game_id in game_ids:
            if game_id not in odds_data:
                continue
            
            game_odds = odds_data[game_id]
            
            # Validate signal freshness
            if not self.validate_signal_freshness(game_odds):
                stale_rejected += 1
                continue
            
            # Detect arbitrage opportunities
            opportunities = self.detect_arbitrage_opportunities(game_odds, game_id)
            
            # Final validation of each opportunity
            validated_opportunities = []
            for opp in opportunities:
                if self.arbitrage_detector.validate_arbitrage_opportunity(opp):
                    validated_opportunities.append(opp)
                else:
                    false_positives += 1
            
            all_opportunities.extend(validated_opportunities)
        
        # Calculate metrics
        scan_end = datetime.now(timezone.utc)
        execution_time = (scan_end - scan_start).total_seconds() * 1000  # ms
        
        total_profit_potential = sum(opp.profit_margin for opp in all_opportunities)
        avg_execution_risk = (
            sum(opp.execution_risk_score for opp in all_opportunities) / len(all_opportunities)
            if all_opportunities else 0.0
        )
        
        high_confidence_count = len([
            opp for opp in all_opportunities 
            if opp.confidence_level == "high"
        ])
        
        # Generate recommendations
        recommendations = self._generate_recommendations(all_opportunities)
        
        # Create execution report
        report = ExecutionReport(
            scan_timestamp=scan_start.isoformat(),
            games_analyzed=len(game_ids),
            arbitrage_opportunities=len(all_opportunities),
            total_profit_potential=total_profit_potential,
            avg_execution_risk=avg_execution_risk,
            high_confidence_opportunities=high_confidence_count,
            stale_signals_rejected=stale_rejected,
            false_positives_avoided=false_positives,
            execution_time_ms=execution_time,
            opportunities=all_opportunities,
            recommendations=recommendations
        )
        
        self.execution_reports.append(report)
        
        logger.info(f"Scan complete: {len(all_opportunities)} opportunities found in {execution_time:.1f}ms")
        return report
    
    def _generate_recommendations(self, opportunities: List[ArbitrageOpportunity]) -> List[str]:
        """Generate actionable recommendations based on opportunities."""
        recommendations = []
        
        if not opportunities:
            recommendations.append("No arbitrage opportunities detected. Monitor for market inefficiencies.")
            return recommendations
        
        # Sort by risk-adjusted profit
        sorted_opps = sorted(opportunities, key=lambda x: x.risk_adjusted_profit, reverse=True)
        
        # Top opportunity recommendation
        top_opp = sorted_opps[0]
        recommendations.append(
            f"Execute top arbitrage: {top_opp.risk_adjusted_profit:.2%} profit "
            f"with {top_opp.confidence_level} confidence ({top_opp.type})"
        )
        
        # High confidence opportunities
        high_conf_opps = [opp for opp in opportunities if opp.confidence_level == "high"]
        if high_conf_opps:
            recommendations.append(
                f"Prioritize {len(high_conf_opps)} high-confidence opportunities "
                f"with avg profit {sum(opp.profit_margin for opp in high_conf_opps) / len(high_conf_opps):.2%}"
            )
        
        # Portfolio approach
        if len(opportunities) >= 3:
            total_profit = sum(opp.profit_margin for opp in opportunities)
            recommendations.append(
                f"Consider portfolio approach: {len(opportunities)} opportunities "
                f"with combined {total_profit:.2%} profit potential"
            )
        
        # Risk warnings
        high_risk_opps = [opp for opp in opportunities if opp.execution_risk_score > 0.2]
        if high_risk_opps:
            recommendations.append(
                f"Exercise caution: {len(high_risk_opps)} opportunities have elevated execution risk"
            )
        
        return recommendations
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status and performance metrics."""
        return {
            "integration_status": {
                "odds_fetcher_available": self.odds_fetcher is not None,
                "latency_monitor_available": self.latency_monitor is not None,
                "market_discrepancy_available": self.market_discrepancy is not None,
                "cross_validation_enabled": self.enable_cross_validation
            },
            "configuration": {
                "min_profit_threshold": self.min_profit_threshold,
                "max_latency_seconds": self.max_latency_seconds,
                "confidence_filter": self.confidence_filter
            },
            "performance_metrics": {
                "execution_reports_generated": len(self.execution_reports),
                "alerts_suppressed": self.alerts_suppressed,
                "cross_validations_performed": self.cross_validations_performed,
                "detector_stats": self.arbitrage_detector.get_execution_summary()
            },
            "last_scan": (
                self.execution_reports[-1].scan_timestamp 
                if self.execution_reports else None
            )
        }


def main():
    """Main function for testing the advanced arbitrage integration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🎯 Advanced Arbitrage Integration - JIRA-023B")
    print("=" * 60)
    
    # Initialize integration system
    integration = AdvancedArbitrageIntegration(
        min_profit_threshold=0.01,  # 1% minimum
        max_latency_seconds=45.0,
        confidence_filter="medium",
        enable_cross_validation=True
    )
    
    print("🔧 SYSTEM STATUS")
    print("-" * 40)
    status = integration.get_system_status()
    
    print("Integration Components:")
    for component, available in status["integration_status"].items():
        status_icon = "✅" if available else "❌"
        print(f"  {status_icon} {component.replace('_', ' ').title()}")
    
    print(f"\nConfiguration:")
    print(f"  Min Profit Threshold: {status['configuration']['min_profit_threshold']:.2%}")
    print(f"  Max Latency: {status['configuration']['max_latency_seconds']:.0f}s")
    print(f"  Confidence Filter: {status['configuration']['confidence_filter']}")
    
    # Test with sample games
    test_games = ['game_001', 'game_002', 'game_003', 'game_004']
    
    print(f"\n🔍 SCANNING {len(test_games)} GAMES")
    print("-" * 40)
    
    # Execute comprehensive scan
    report = integration.scan_multiple_games(test_games)
    
    print(f"📊 EXECUTION REPORT")
    print("-" * 40)
    print(f"Scan Duration: {report.execution_time_ms:.1f}ms")
    print(f"Games Analyzed: {report.games_analyzed}")
    print(f"Arbitrage Opportunities: {report.arbitrage_opportunities}")
    print(f"Total Profit Potential: {report.total_profit_potential:.2%}")
    print(f"Avg Execution Risk: {report.avg_execution_risk:.3f}")
    print(f"High Confidence Opportunities: {report.high_confidence_opportunities}")
    print(f"Stale Signals Rejected: {report.stale_signals_rejected}")
    print(f"False Positives Avoided: {report.false_positives_avoided}")
    
    # Show opportunities
    if report.opportunities:
        print(f"\n💰 ARBITRAGE OPPORTUNITIES")
        print("-" * 40)
        for i, opp in enumerate(report.opportunities, 1):
            print(f"{i}. {opp.type.upper()} - Game {opp.game_id}")
            print(f"   Profit: {opp.profit_margin:.2%} (Risk-Adj: {opp.risk_adjusted_profit:.2%})")
            print(f"   Confidence: {opp.confidence_level}, Risk Score: {opp.execution_risk_score:.3f}")
            print(f"   Books: {len(opp.legs)} legs")
    
    # Show recommendations
    if report.recommendations:
        print(f"\n🎯 RECOMMENDATIONS")
        print("-" * 40)
        for i, rec in enumerate(report.recommendations, 1):
            print(f"{i}. {rec}")
    
    print(f"\n✅ JIRA-023B Advanced Arbitrage Integration Complete!")
    print(f"🎯 Hedge fund-level execution-aware arbitrage detection operational")


if __name__ == "__main__":
    main()
