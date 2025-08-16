#!/usr/bin/env python3
"""
Final Market Verifier - JIRA-024

Performs final verification of market availability and odds before alert dispatch.
This module integrates with the alert dispatch system to ensure markets are still 
available at the specified odds right before sending notifications.
"""

import logging
import time
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum

# Import core dependencies
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
    logging.warning("OddsFetcherTool not available - final verification disabled")

try:
    from tools.market_discrepancy_monitor import Alert
    HAS_ALERT_SYSTEM = True
except ImportError:
    HAS_ALERT_SYSTEM = False
    # Mock Alert class for type hints
    class Alert:
        pass

logger = logging.getLogger(__name__)


class VerificationResult(Enum):
    """Result of market verification."""
    VALID = "valid"                    # Market is available at acceptable odds
    MARKET_UNAVAILABLE = "unavailable" # Market no longer exists
    ODDS_SHIFTED = "odds_shifted"      # Odds have changed significantly
    STALE_DATA = "stale_data"          # Data is too old to be reliable
    ERROR = "error"                    # Error during verification


@dataclass
class OddsComparison:
    """Comparison between expected and current odds."""
    leg_id: str
    sportsbook: str
    market_type: str
    outcome: str
    
    # Expected (from original alert)
    expected_odds: float
    expected_implied_prob: float
    
    # Current (from fresh fetch)
    current_odds: Optional[float]
    current_implied_prob: Optional[float]
    
    # Analysis
    odds_shift: Optional[float] = None      # Positive = worse for bettor
    prob_shift: Optional[float] = None      # Change in implied probability
    shift_percentage: Optional[float] = None # Percentage change
    
    available: bool = True
    
    def __post_init__(self):
        """Calculate derived fields."""
        if self.current_odds is not None:
            self.odds_shift = self.current_odds - self.expected_odds
            self.prob_shift = self.current_implied_prob - self.expected_implied_prob
            if self.expected_odds != 0:
                self.shift_percentage = self.odds_shift / abs(self.expected_odds)


@dataclass
class VerificationReport:
    """Complete verification report for an alert."""
    alert_id: str
    verification_result: VerificationResult
    verification_timestamp: str
    
    # Odds analysis
    odds_comparisons: List[OddsComparison]
    max_odds_shift: float = 0.0
    max_prob_shift: float = 0.0
    
    # Market availability
    unavailable_markets: List[str] = field(default_factory=list)
    available_markets: List[str] = field(default_factory=list)
    
    # Thresholds used
    max_odds_shift_threshold: float = 0.0
    max_prob_shift_threshold: float = 0.0
    
    # Final recommendation
    should_dispatch_alert: bool = False
    cancellation_reason: Optional[str] = None
    
    # Performance metrics
    verification_duration_ms: float = 0.0
    fresh_data_age_seconds: float = 0.0


@dataclass
class VerificationConfig:
    """Configuration for final market verification."""
    
    # Odds shift thresholds
    max_american_odds_shift: float = 10.0      # Max acceptable shift in American odds
    max_implied_prob_shift: float = 0.02       # Max 2% shift in implied probability
    max_shift_percentage: float = 0.05         # Max 5% relative change
    
    # Market availability
    require_all_markets_available: bool = True
    min_markets_available_percentage: float = 0.8  # 80% of markets must be available
    
    # Data freshness
    max_data_age_seconds: float = 60.0         # Max 1 minute old data
    verification_timeout_seconds: float = 10.0 # Max time to spend on verification
    
    # Retry logic
    max_retries: int = 2
    retry_delay_seconds: float = 1.0
    
    # Alert-specific overrides
    critical_alert_stricter: bool = True       # Use stricter thresholds for critical alerts
    arbitrage_alert_stricter: bool = True      # Use stricter thresholds for arbitrage


class FinalMarketVerifier:
    """
    Final market verification system for alert dispatch.
    
    Performs last-minute verification of market availability and odds
    to ensure alerts are only sent for valid opportunities.
    """
    
    def __init__(self, config: Optional[VerificationConfig] = None):
        """
        Initialize the final market verifier.
        
        Args:
            config: Verification configuration
        """
        self.config = config or VerificationConfig()
        
        # Initialize OddsFetcherTool if available
        if HAS_ODDS_FETCHER:
            self.odds_fetcher = OddsFetcherTool()
        else:
            self.odds_fetcher = None
            logger.warning("OddsFetcher unavailable - verification will be limited")
        
        # Statistics
        self.total_verifications = 0
        self.verifications_passed = 0
        self.verifications_failed = 0
        self.alerts_cancelled = 0
        
        # Cache for recent verifications (to avoid duplicate work)
        self.verification_cache = {}
        self.cache_ttl_seconds = 30.0
        
        logger.info("FinalMarketVerifier initialized")
    
    def verify_alert_before_dispatch(self, alert: Alert) -> VerificationReport:
        """
        Verify market conditions before dispatching an alert.
        
        Args:
            alert: Alert to verify
            
        Returns:
            VerificationReport with verification results
        """
        start_time = time.time()
        self.total_verifications += 1
        
        logger.info(f"Starting final verification for alert {alert.alert_id}")
        
        try:
            # Check cache first
            cached_result = self._check_verification_cache(alert)
            if cached_result:
                logger.debug(f"Using cached verification for {alert.alert_id}")
                return cached_result
            
            # Perform fresh verification
            report = self._perform_verification(alert)
            
            # Update statistics
            if report.should_dispatch_alert:
                self.verifications_passed += 1
            else:
                self.verifications_failed += 1
                self.alerts_cancelled += 1
                logger.info(f"Alert {alert.alert_id} cancelled: {report.cancellation_reason}")
            
            # Cache result
            self._cache_verification_result(alert, report)
            
            # Add performance metrics
            report.verification_duration_ms = (time.time() - start_time) * 1000
            
            return report
            
        except Exception as e:
            logger.error(f"Verification failed for alert {alert.alert_id}: {e}")
            self.verifications_failed += 1
            
            # Return error report
            return VerificationReport(
                alert_id=alert.alert_id,
                verification_result=VerificationResult.ERROR,
                verification_timestamp=datetime.now(timezone.utc).isoformat(),
                odds_comparisons=[],
                should_dispatch_alert=False,
                cancellation_reason=f"Verification error: {str(e)}",
                verification_duration_ms=(time.time() - start_time) * 1000
            )
    
    def _perform_verification(self, alert: Alert) -> VerificationReport:
        """Perform the actual verification logic."""
        current_time = datetime.now(timezone.utc)
        
        # Extract alert information
        game_id = alert.game_id
        market_type = alert.market_type
        opportunity_data = alert.opportunity_data
        
        # Determine verification thresholds based on alert type and priority
        config = self._get_alert_specific_config(alert)
        
        if not self.odds_fetcher:
            # Cannot verify without odds fetcher
            return VerificationReport(
                alert_id=alert.alert_id,
                verification_result=VerificationResult.ERROR,
                verification_timestamp=current_time.isoformat(),
                odds_comparisons=[],
                should_dispatch_alert=False,
                cancellation_reason="OddsFetcher not available for verification"
            )
        
        # Fetch fresh odds data
        fresh_odds = self._fetch_fresh_odds_with_retry(game_id, [market_type])
        
        if not fresh_odds:
            return VerificationReport(
                alert_id=alert.alert_id,
                verification_result=VerificationResult.ERROR,
                verification_timestamp=current_time.isoformat(),
                odds_comparisons=[],
                should_dispatch_alert=False,
                cancellation_reason="Failed to fetch fresh odds data"
            )
        
        # Extract expected odds from opportunity data
        expected_odds = self._extract_expected_odds(opportunity_data, alert.alert_type)
        
        # Compare expected vs current odds
        odds_comparisons = self._compare_odds(expected_odds, fresh_odds, market_type)
        
        # Analyze results
        verification_result, should_dispatch, cancellation_reason = self._analyze_verification_results(
            odds_comparisons, config
        )
        
        # Calculate metrics
        max_odds_shift = max([abs(comp.odds_shift) for comp in odds_comparisons 
                             if comp.odds_shift is not None], default=0.0)
        max_prob_shift = max([abs(comp.prob_shift) for comp in odds_comparisons 
                             if comp.prob_shift is not None], default=0.0)
        
        unavailable_markets = [comp.leg_id for comp in odds_comparisons if not comp.available]
        available_markets = [comp.leg_id for comp in odds_comparisons if comp.available]
        
        return VerificationReport(
            alert_id=alert.alert_id,
            verification_result=verification_result,
            verification_timestamp=current_time.isoformat(),
            odds_comparisons=odds_comparisons,
            max_odds_shift=max_odds_shift,
            max_prob_shift=max_prob_shift,
            unavailable_markets=unavailable_markets,
            available_markets=available_markets,
            max_odds_shift_threshold=config.max_american_odds_shift,
            max_prob_shift_threshold=config.max_implied_prob_shift,
            should_dispatch_alert=should_dispatch,
            cancellation_reason=cancellation_reason
        )
    
    def _get_alert_specific_config(self, alert: Alert) -> VerificationConfig:
        """Get alert-specific verification configuration."""
        config = VerificationConfig(
            max_american_odds_shift=self.config.max_american_odds_shift,
            max_implied_prob_shift=self.config.max_implied_prob_shift,
            max_shift_percentage=self.config.max_shift_percentage,
            require_all_markets_available=self.config.require_all_markets_available,
            min_markets_available_percentage=self.config.min_markets_available_percentage,
            max_data_age_seconds=self.config.max_data_age_seconds,
            verification_timeout_seconds=self.config.verification_timeout_seconds,
            max_retries=self.config.max_retries,
            retry_delay_seconds=self.config.retry_delay_seconds
        )
        
        # Apply stricter thresholds for critical/arbitrage alerts
        if alert.priority == 'critical' and self.config.critical_alert_stricter:
            config.max_american_odds_shift *= 0.5  # Stricter odds shift tolerance
            config.max_implied_prob_shift *= 0.5
            config.max_shift_percentage *= 0.5
        
        if alert.alert_type == 'arbitrage' and self.config.arbitrage_alert_stricter:
            config.max_american_odds_shift *= 0.3  # Very strict for arbitrage
            config.max_implied_prob_shift *= 0.3
            config.require_all_markets_available = True
        
        return config
    
    def _fetch_fresh_odds_with_retry(self, game_id: str, markets: List[str]) -> Optional[List[GameOdds]]:
        """Fetch fresh odds with retry logic."""
        for attempt in range(self.config.max_retries + 1):
            try:
                # Convert game_id to sport_key format if needed
                sport_key = self._convert_game_id_to_sport_key(game_id)
                
                odds_data = self.odds_fetcher.get_game_odds(sport_key, markets=markets)
                
                if odds_data:
                    return odds_data
                
            except Exception as e:
                logger.warning(f"Odds fetch attempt {attempt + 1} failed: {e}")
                if attempt < self.config.max_retries:
                    time.sleep(self.config.retry_delay_seconds)
        
        return None
    
    def _convert_game_id_to_sport_key(self, game_id: str) -> str:
        """Convert game ID to sport key format for OddsFetcher."""
        # For NBA, use basketball_nba
        # This is a simple mapping - could be enhanced based on game_id format
        if 'nba' in game_id.lower() or 'basketball' in game_id.lower():
            return 'basketball_nba'
        else:
            # Default to NBA for this project
            return 'basketball_nba'
    
    def _extract_expected_odds(self, opportunity_data: Dict[str, Any], alert_type: str) -> List[Dict[str, Any]]:
        """Extract expected odds from opportunity data."""
        expected_odds = []
        
        if alert_type == 'arbitrage':
            # For arbitrage alerts, extract from bets_required
            bets_required = opportunity_data.get('bets_required', [])
            for bet in bets_required:
                expected_odds.append({
                    'leg_id': f"{bet.get('outcome', 'unknown')}_{bet.get('sportsbook', 'unknown')}",
                    'sportsbook': bet.get('sportsbook', 'unknown'),
                    'outcome': bet.get('outcome', 'unknown'),
                    'odds': bet.get('odds', 0),
                    'stake': bet.get('stake', 0)
                })
        
        elif alert_type == 'value':
            # For value alerts, extract single bet information
            expected_odds.append({
                'leg_id': f"{opportunity_data.get('outcome', 'unknown')}_{opportunity_data.get('sportsbook', 'unknown')}",
                'sportsbook': opportunity_data.get('sportsbook', 'unknown'),
                'outcome': opportunity_data.get('outcome', 'unknown'),
                'odds': opportunity_data.get('offered_odds', 0)
            })
        
        return expected_odds
    
    def _compare_odds(self, expected_odds: List[Dict[str, Any]], 
                     fresh_odds: List[GameOdds], 
                     market_type: str) -> List[OddsComparison]:
        """Compare expected odds with fresh market data."""
        comparisons = []
        
        for expected in expected_odds:
            comparison = self._create_odds_comparison(expected, fresh_odds, market_type)
            comparisons.append(comparison)
        
        return comparisons
    
    def _create_odds_comparison(self, expected: Dict[str, Any], 
                               fresh_odds: List[GameOdds], 
                               market_type: str) -> OddsComparison:
        """Create comparison for a single odds leg."""
        expected_odds_val = expected.get('odds', 0)
        expected_sportsbook = expected.get('sportsbook', '').lower()
        expected_outcome = expected.get('outcome', '')
        
        # Find matching odds in fresh data
        current_odds_val = None
        available = False
        
        for game_odds in fresh_odds:
            for book_odds in game_odds.books:
                if book_odds.bookmaker.lower() == expected_sportsbook and book_odds.market == market_type:
                    for selection in book_odds.selections:
                        if selection.name.lower() == expected_outcome.lower():
                            current_odds_val = selection.price_decimal
                            if current_odds_val and current_odds_val != 0:
                                # Convert to American odds for comparison
                                current_odds_val = self._decimal_to_american_odds(current_odds_val)
                                available = True
                            break
                    break
            if available:
                break
        
        # Calculate implied probabilities
        expected_implied_prob = self._american_to_implied_probability(expected_odds_val)
        current_implied_prob = None
        if current_odds_val is not None:
            current_implied_prob = self._american_to_implied_probability(current_odds_val)
        
        return OddsComparison(
            leg_id=expected.get('leg_id', 'unknown'),
            sportsbook=expected_sportsbook,
            market_type=market_type,
            outcome=expected_outcome,
            expected_odds=expected_odds_val,
            expected_implied_prob=expected_implied_prob,
            current_odds=current_odds_val,
            current_implied_prob=current_implied_prob,
            available=available
        )
    
    def _american_to_implied_probability(self, american_odds: float) -> float:
        """Convert American odds to implied probability."""
        if american_odds > 0:
            return 100 / (american_odds + 100)
        else:
            return abs(american_odds) / (abs(american_odds) + 100)
    
    def _decimal_to_american_odds(self, decimal_odds: float) -> float:
        """Convert decimal odds to American odds."""
        if decimal_odds >= 2.0:
            return (decimal_odds - 1) * 100
        else:
            return -100 / (decimal_odds - 1)
    
    def _analyze_verification_results(self, comparisons: List[OddsComparison], 
                                    config: VerificationConfig) -> Tuple[VerificationResult, bool, Optional[str]]:
        """Analyze verification results and determine if alert should be dispatched."""
        
        # Check for unavailable markets
        unavailable_count = sum(1 for comp in comparisons if not comp.available)
        total_count = len(comparisons)
        
        if config.require_all_markets_available and unavailable_count > 0:
            return (VerificationResult.MARKET_UNAVAILABLE, False, 
                   f"{unavailable_count} of {total_count} markets unavailable")
        
        if total_count > 0:
            availability_percentage = (total_count - unavailable_count) / total_count
            if availability_percentage < config.min_markets_available_percentage:
                return (VerificationResult.MARKET_UNAVAILABLE, False,
                       f"Only {availability_percentage:.1%} of markets available")
        
        # Check for significant odds shifts
        for comp in comparisons:
            if not comp.available:
                continue
                
            if comp.odds_shift is not None and abs(comp.odds_shift) > config.max_american_odds_shift:
                return (VerificationResult.ODDS_SHIFTED, False,
                       f"Odds shifted by {comp.odds_shift:+.1f} for {comp.outcome} at {comp.sportsbook}")
            
            if comp.prob_shift is not None and abs(comp.prob_shift) > config.max_implied_prob_shift:
                return (VerificationResult.ODDS_SHIFTED, False,
                       f"Implied probability shifted by {comp.prob_shift:+.2%} for {comp.outcome}")
            
            if comp.shift_percentage is not None and abs(comp.shift_percentage) > config.max_shift_percentage:
                return (VerificationResult.ODDS_SHIFTED, False,
                       f"Odds shifted by {comp.shift_percentage:+.1%} for {comp.outcome}")
        
        # All checks passed
        return (VerificationResult.VALID, True, None)
    
    def _check_verification_cache(self, alert: Alert) -> Optional[VerificationReport]:
        """Check if we have a recent verification for this alert."""
        cache_key = f"{alert.game_id}_{alert.market_type}_{alert.alert_type}"
        
        if cache_key in self.verification_cache:
            cached_report, cache_time = self.verification_cache[cache_key]
            if time.time() - cache_time < self.cache_ttl_seconds:
                return cached_report
        
        return None
    
    def _cache_verification_result(self, alert: Alert, report: VerificationReport):
        """Cache verification result."""
        cache_key = f"{alert.game_id}_{alert.market_type}_{alert.alert_type}"
        self.verification_cache[cache_key] = (report, time.time())
        
        # Clean old cache entries
        current_time = time.time()
        expired_keys = [
            key for key, (_, cache_time) in self.verification_cache.items()
            if current_time - cache_time > self.cache_ttl_seconds
        ]
        for key in expired_keys:
            del self.verification_cache[key]
    
    def get_verification_stats(self) -> Dict[str, Any]:
        """Get verification statistics."""
        success_rate = 0.0
        if self.total_verifications > 0:
            success_rate = self.verifications_passed / self.total_verifications
        
        return {
            'total_verifications': self.total_verifications,
            'verifications_passed': self.verifications_passed,
            'verifications_failed': self.verifications_failed,
            'alerts_cancelled': self.alerts_cancelled,
            'success_rate': success_rate,
            'cache_entries': len(self.verification_cache),
            'config': {
                'max_american_odds_shift': self.config.max_american_odds_shift,
                'max_implied_prob_shift': self.config.max_implied_prob_shift,
                'max_shift_percentage': self.config.max_shift_percentage,
                'require_all_markets_available': self.config.require_all_markets_available,
                'max_data_age_seconds': self.config.max_data_age_seconds
            }
        }


def main():
    """Main function for testing the final market verifier."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🔍 Final Market Verifier - JIRA-024")
    print("=" * 60)
    
    # Initialize verifier
    config = VerificationConfig(
        max_american_odds_shift=5.0,    # Allow 5-point shift
        max_implied_prob_shift=0.01,    # Allow 1% probability shift
        max_shift_percentage=0.03,      # Allow 3% relative change
        require_all_markets_available=True
    )
    
    verifier = FinalMarketVerifier(config)
    
    print("🔧 CONFIGURATION")
    print("-" * 40)
    print(f"Max American odds shift: ±{config.max_american_odds_shift}")
    print(f"Max implied probability shift: ±{config.max_implied_prob_shift:.1%}")
    print(f"Max relative shift: ±{config.max_shift_percentage:.1%}")
    print(f"Require all markets available: {config.require_all_markets_available}")
    
    # Create mock alert for testing
    if HAS_ALERT_SYSTEM:
        mock_alert = Alert(
            alert_id="test_alert_001",
            alert_type="arbitrage",
            priority="high",
            game_id="nba_game_001",
            market_type="h2h",
            opportunity_data={
                'bets_required': [
                    {
                        'outcome': 'Lakers',
                        'sportsbook': 'draftkings',
                        'odds': -110,
                        'stake': 50
                    },
                    {
                        'outcome': 'Celtics',
                        'sportsbook': 'fanduel',
                        'odds': +120,
                        'stake': 45
                    }
                ]
            },
            confidence=0.85,
            profit_potential=0.03,
            time_sensitivity="immediate",
            message="Test arbitrage opportunity",
            recommended_action="Place bets on both teams",
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
        print(f"\n🧪 TESTING VERIFICATION")
        print("-" * 40)
        print(f"Testing alert: {mock_alert.alert_id}")
        print(f"Alert type: {mock_alert.alert_type}")
        print(f"Priority: {mock_alert.priority}")
        
        # Perform verification
        report = verifier.verify_alert_before_dispatch(mock_alert)
        
        print(f"\n📊 VERIFICATION RESULTS")
        print("-" * 40)
        print(f"Result: {report.verification_result.value}")
        print(f"Should dispatch: {report.should_dispatch_alert}")
        if report.cancellation_reason:
            print(f"Cancellation reason: {report.cancellation_reason}")
        print(f"Duration: {report.verification_duration_ms:.1f}ms")
        print(f"Odds comparisons: {len(report.odds_comparisons)}")
        
        if report.odds_comparisons:
            print(f"\n📈 ODDS ANALYSIS")
            print("-" * 40)
            for comp in report.odds_comparisons:
                print(f"• {comp.outcome} at {comp.sportsbook}")
                print(f"  Expected: {comp.expected_odds:+.0f} ({comp.expected_implied_prob:.1%})")
                if comp.current_odds is not None:
                    print(f"  Current:  {comp.current_odds:+.0f} ({comp.current_implied_prob:.1%})")
                    print(f"  Shift:    {comp.odds_shift:+.1f} ({comp.shift_percentage:+.1%})")
                else:
                    print(f"  Current:  Not available")
                print(f"  Available: {comp.available}")
    
    # Show statistics
    stats = verifier.get_verification_stats()
    print(f"\n📊 VERIFICATION STATISTICS")
    print("-" * 40)
    print(f"Total verifications: {stats['total_verifications']}")
    print(f"Passed: {stats['verifications_passed']}")
    print(f"Failed: {stats['verifications_failed']}")
    print(f"Alerts cancelled: {stats['alerts_cancelled']}")
    print(f"Success rate: {stats['success_rate']:.1%}")
    
    print(f"\n✅ JIRA-024 Final Market Verifier Complete!")
    print(f"🎯 Ready to integrate with alert dispatch system")


if __name__ == "__main__":
    main()
