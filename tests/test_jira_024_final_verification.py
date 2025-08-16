#!/usr/bin/env python3
"""
Test suite for JIRA-024 Final Market Verification

Tests the final market verification system integration with alert dispatch.
"""

import unittest
import logging
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from dataclasses import asdict

# Set up path for imports
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from tools.final_market_verifier import (
    FinalMarketVerifier, VerificationConfig, VerificationResult, 
    OddsComparison, VerificationReport
)
from tools.market_discrepancy_monitor import (
    MarketDiscrepancyMonitor, MonitoringConfig, Alert
)

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestFinalMarketVerifier(unittest.TestCase):
    """Test the FinalMarketVerifier class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = VerificationConfig(
            max_american_odds_shift=5.0,
            max_implied_prob_shift=0.01,
            max_shift_percentage=0.03,
            require_all_markets_available=True,
            max_data_age_seconds=60.0
        )
        self.verifier = FinalMarketVerifier(self.config)
    
    def test_verifier_initialization(self):
        """Test verifier initializes correctly."""
        self.assertIsNotNone(self.verifier)
        self.assertEqual(self.verifier.config.max_american_odds_shift, 5.0)
        self.assertEqual(self.verifier.total_verifications, 0)
    
    def test_american_to_implied_probability(self):
        """Test odds conversion functions."""
        # Positive odds
        prob = self.verifier._american_to_implied_probability(100)
        self.assertAlmostEqual(prob, 0.5, places=3)
        
        # Negative odds
        prob = self.verifier._american_to_implied_probability(-110)
        self.assertAlmostEqual(prob, 0.524, places=3)
    
    def test_decimal_to_american_odds(self):
        """Test decimal to American odds conversion."""
        # Even odds
        american = self.verifier._decimal_to_american_odds(2.0)
        self.assertEqual(american, 100)
        
        # Favorites
        american = self.verifier._decimal_to_american_odds(1.91)
        self.assertAlmostEqual(american, -110, places=0)
    
    def test_extract_expected_odds_arbitrage(self):
        """Test extracting expected odds from arbitrage data."""
        opportunity_data = {
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
        }
        
        expected_odds = self.verifier._extract_expected_odds(opportunity_data, 'arbitrage')
        self.assertEqual(len(expected_odds), 2)
        self.assertEqual(expected_odds[0]['odds'], -110)
        self.assertEqual(expected_odds[1]['odds'], 120)
    
    def test_extract_expected_odds_value(self):
        """Test extracting expected odds from value bet data."""
        opportunity_data = {
            'outcome': 'Lakers',
            'sportsbook': 'draftkings',
            'offered_odds': -105
        }
        
        expected_odds = self.verifier._extract_expected_odds(opportunity_data, 'value')
        self.assertEqual(len(expected_odds), 1)
        self.assertEqual(expected_odds[0]['odds'], -105)
    
    def test_odds_comparison_calculation(self):
        """Test odds comparison calculations."""
        comparison = OddsComparison(
            leg_id="test_leg",
            sportsbook="draftkings",
            market_type="h2h",
            outcome="Lakers",
            expected_odds=-110,
            expected_implied_prob=0.524,
            current_odds=-115,
            current_implied_prob=0.535
        )
        
        self.assertAlmostEqual(comparison.odds_shift, -5.0, places=1)
        self.assertAlmostEqual(comparison.prob_shift, 0.011, places=3)
        self.assertAlmostEqual(abs(comparison.shift_percentage), 0.045, places=3)
    
    @patch('tools.final_market_verifier.OddsFetcherTool')
    def test_verify_alert_no_odds_fetcher(self, mock_odds_fetcher):
        """Test verification when OddsFetcher is not available."""
        # Create verifier without odds fetcher
        verifier = FinalMarketVerifier(self.config)
        verifier.odds_fetcher = None
        
        alert = self._create_test_alert()
        report = verifier.verify_alert_before_dispatch(alert)
        
        self.assertEqual(report.verification_result, VerificationResult.ERROR)
        self.assertFalse(report.should_dispatch_alert)
        self.assertIn("OddsFetcher not available", report.cancellation_reason)
    
    @patch('tools.final_market_verifier.OddsFetcherTool')
    def test_verify_alert_successful(self, mock_odds_fetcher_class):
        """Test successful alert verification."""
        # Mock the odds fetcher
        mock_odds_fetcher = Mock()
        mock_odds_fetcher_class.return_value = mock_odds_fetcher
        
        # Create verifier with mocked odds fetcher
        verifier = FinalMarketVerifier(self.config)
        verifier.odds_fetcher = mock_odds_fetcher
        
        # Mock fresh odds data (similar odds to expected)
        mock_game_odds = self._create_mock_game_odds()
        mock_odds_fetcher.get_game_odds.return_value = [mock_game_odds]
        
        alert = self._create_test_alert()
        report = verifier.verify_alert_before_dispatch(alert)
        
        # Should pass verification since odds are similar
        self.assertTrue(report.should_dispatch_alert)
        self.assertEqual(report.verification_result, VerificationResult.VALID)
    
    @patch('tools.final_market_verifier.OddsFetcherTool')
    def test_verify_alert_odds_shifted(self, mock_odds_fetcher_class):
        """Test alert verification when odds have shifted significantly."""
        # Mock the odds fetcher
        mock_odds_fetcher = Mock()
        mock_odds_fetcher_class.return_value = mock_odds_fetcher
        
        # Create verifier with strict config
        strict_config = VerificationConfig(
            max_american_odds_shift=2.0,  # Very strict
            max_implied_prob_shift=0.005,
            require_all_markets_available=True
        )
        verifier = FinalMarketVerifier(strict_config)
        verifier.odds_fetcher = mock_odds_fetcher
        
        # Mock fresh odds data with significant shift
        mock_game_odds = self._create_mock_game_odds(odds_shift=10)  # 10-point shift
        mock_odds_fetcher.get_game_odds.return_value = [mock_game_odds]
        
        alert = self._create_test_alert()
        report = verifier.verify_alert_before_dispatch(alert)
        
        # Should fail verification due to odds shift
        self.assertFalse(report.should_dispatch_alert)
        self.assertEqual(report.verification_result, VerificationResult.ODDS_SHIFTED)
    
    def test_verification_stats(self):
        """Test verification statistics tracking."""
        initial_stats = self.verifier.get_verification_stats()
        self.assertEqual(initial_stats['total_verifications'], 0)
        
        # Simulate some verifications
        self.verifier.total_verifications = 10
        self.verifier.verifications_passed = 8
        self.verifier.verifications_failed = 2
        
        stats = self.verifier.get_verification_stats()
        self.assertEqual(stats['total_verifications'], 10)
        self.assertEqual(stats['success_rate'], 0.8)
    
    def _create_test_alert(self):
        """Create a test alert for verification."""
        return Alert(
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
    
    def _create_mock_game_odds(self, odds_shift=0):
        """Create mock GameOdds for testing."""
        # Mock the structure that OddsFetcherTool returns
        mock_selection1 = Mock()
        mock_selection1.name = 'Lakers'
        mock_selection1.price_decimal = 1.91 + (odds_shift * 0.01)  # Roughly -110 + shift
        
        mock_selection2 = Mock()
        mock_selection2.name = 'Celtics'
        mock_selection2.price_decimal = 2.20 + (odds_shift * 0.01)  # Roughly +120 + shift
        
        mock_book_odds1 = Mock()
        mock_book_odds1.bookmaker = 'draftkings'
        mock_book_odds1.market = 'h2h'
        mock_book_odds1.selections = [mock_selection1]
        
        mock_book_odds2 = Mock()
        mock_book_odds2.bookmaker = 'fanduel'
        mock_book_odds2.market = 'h2h'
        mock_book_odds2.selections = [mock_selection2]
        
        mock_game_odds = Mock()
        mock_game_odds.books = [mock_book_odds1, mock_book_odds2]
        
        return mock_game_odds


class TestMarketDiscrepancyMonitorIntegration(unittest.TestCase):
    """Test integration of final verification with MarketDiscrepancyMonitor."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.monitoring_config = MonitoringConfig(
            enable_final_verification=True,
            scan_interval_seconds=1,
            alert_cooldown_seconds=1
        )
        
        # Mock alert handlers
        self.mock_handler = Mock()
        self.monitor = MarketDiscrepancyMonitor(
            config=self.monitoring_config,
            alert_handlers=[self.mock_handler]
        )
    
    @patch('tools.final_market_verifier.FinalMarketVerifier')
    def test_monitor_with_verification_enabled(self, mock_verifier_class):
        """Test monitor initialization with verification enabled."""
        self.assertIsNotNone(self.monitor.final_verifier)
        self.assertTrue(self.monitor.config.enable_final_verification)
    
    @patch('tools.final_market_verifier.FinalMarketVerifier')
    def test_alert_dispatch_with_verification_pass(self, mock_verifier_class):
        """Test alert dispatch when verification passes."""
        # Mock the verifier
        mock_verifier = Mock()
        mock_verifier_class.return_value = mock_verifier
        self.monitor.final_verifier = mock_verifier
        
        # Mock verification to pass
        mock_report = Mock()
        mock_report.should_dispatch_alert = True
        mock_report.verification_result = VerificationResult.VALID
        mock_verifier.verify_alert_before_dispatch.return_value = mock_report
        
        # Create test alert
        alert = Alert(
            alert_id="test_alert",
            alert_type="arbitrage",
            priority="high",
            game_id="test_game",
            market_type="h2h",
            opportunity_data={},
            confidence=0.8,
            profit_potential=0.03,
            time_sensitivity="immediate",
            message="Test alert",
            recommended_action="Test action",
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
        # Send alert
        self.monitor._send_alert(alert)
        
        # Verify alert was sent to handlers
        self.mock_handler.assert_called_once()
        self.assertEqual(self.monitor.alerts_verified, 1)
        self.assertEqual(self.monitor.alerts_cancelled_verification, 0)
    
    @patch('tools.final_market_verifier.FinalMarketVerifier')
    def test_alert_dispatch_with_verification_fail(self, mock_verifier_class):
        """Test alert dispatch when verification fails."""
        # Mock the verifier
        mock_verifier = Mock()
        mock_verifier_class.return_value = mock_verifier
        self.monitor.final_verifier = mock_verifier
        
        # Mock verification to fail
        mock_report = Mock()
        mock_report.should_dispatch_alert = False
        mock_report.verification_result = VerificationResult.ODDS_SHIFTED
        mock_report.cancellation_reason = "Odds shifted too much"
        mock_verifier.verify_alert_before_dispatch.return_value = mock_report
        
        # Create test alert
        alert = Alert(
            alert_id="test_alert_fail",
            alert_type="arbitrage",
            priority="medium",
            game_id="test_game",
            market_type="h2h",
            opportunity_data={},
            confidence=0.8,
            profit_potential=0.03,
            time_sensitivity="immediate",
            message="Test alert",
            recommended_action="Test action",
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
        # Add alert to active alerts first
        self.monitor.active_alerts[alert.alert_id] = alert
        
        # Send alert
        self.monitor._send_alert(alert)
        
        # Verify alert was NOT sent to handlers
        self.mock_handler.assert_not_called()
        self.assertEqual(self.monitor.alerts_verified, 1)
        self.assertEqual(self.monitor.alerts_cancelled_verification, 1)
        
        # Verify alert was removed from active alerts
        self.assertNotIn(alert.alert_id, self.monitor.active_alerts)
    
    def test_monitoring_stats_with_verification(self):
        """Test monitoring statistics include verification metrics."""
        stats = self.monitor.get_monitoring_stats()
        
        self.assertIn('verification_enabled', stats)
        if stats['verification_enabled']:
            self.assertIn('alerts_verified', stats)
            self.assertIn('alerts_cancelled_verification', stats)
            self.assertIn('verification_success_rate', stats)


class TestJIRA024Integration(unittest.TestCase):
    """Integration test for complete JIRA-024 implementation."""
    
    def setUp(self):
        """Set up integration test fixtures."""
        self.verification_config = VerificationConfig(
            max_american_odds_shift=5.0,
            max_implied_prob_shift=0.02,
            require_all_markets_available=True
        )
        
        self.monitoring_config = MonitoringConfig(
            enable_final_verification=True,
            verification_config=self.verification_config,
            scan_interval_seconds=1
        )
    
    @patch('tools.final_market_verifier.FinalMarketVerifier')
    def test_end_to_end_verification_workflow(self, mock_verifier_class):
        """Test complete end-to-end verification workflow."""
        # Create monitor with verification enabled
        monitor = MarketDiscrepancyMonitor(config=self.monitoring_config)
        
        # Verify verification is enabled
        self.assertTrue(monitor.config.enable_final_verification)
        
        # Create mock alert handler to track dispatched alerts
        dispatched_alerts = []
        def mock_handler(alert):
            dispatched_alerts.append(alert)
        
        monitor.add_alert_handler(mock_handler)
        
        # Mock the verifier to simulate different scenarios
        mock_verifier = Mock()
        monitor.final_verifier = mock_verifier
        
        # Scenario 1: Alert passes verification
        mock_report_pass = Mock()
        mock_report_pass.should_dispatch_alert = True
        mock_report_pass.verification_result = VerificationResult.VALID
        
        # Scenario 2: Alert fails verification
        mock_report_fail = Mock()
        mock_report_fail.should_dispatch_alert = False
        mock_report_fail.verification_result = VerificationResult.ODDS_SHIFTED
        mock_report_fail.cancellation_reason = "Odds shifted significantly"
        
        # Configure mock to return different results for different calls
        mock_verifier.verify_alert_before_dispatch.side_effect = [
            mock_report_pass,   # First alert passes
            mock_report_fail    # Second alert fails
        ]
        
        # Create test alerts
        alert1 = Alert(
            alert_id="pass_alert",
            alert_type="arbitrage",
            priority="high",
            game_id="game1",
            market_type="h2h",
            opportunity_data={},
            confidence=0.9,
            profit_potential=0.05,
            time_sensitivity="immediate",
            message="High value arbitrage",
            recommended_action="Place arbitrage bets",
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
        alert2 = Alert(
            alert_id="fail_alert",
            alert_type="value",
            priority="medium",
            game_id="game2",
            market_type="spreads",
            opportunity_data={},
            confidence=0.7,
            profit_potential=0.08,
            time_sensitivity="short",
            message="Value bet opportunity",
            recommended_action="Place value bet",
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
        # Send alerts through the system
        monitor._send_alert(alert1)  # Should pass verification and be dispatched
        monitor._send_alert(alert2)  # Should fail verification and be cancelled
        
        # Verify results
        self.assertEqual(len(dispatched_alerts), 1)  # Only one alert dispatched
        self.assertEqual(dispatched_alerts[0].alert_id, "pass_alert")
        
        # Check monitoring statistics
        stats = monitor.get_monitoring_stats()
        self.assertEqual(stats['alerts_verified'], 2)
        self.assertEqual(stats['alerts_cancelled_verification'], 1)
        
        # Verify the verifier was called correctly
        self.assertEqual(mock_verifier.verify_alert_before_dispatch.call_count, 2)


def run_tests():
    """Run all JIRA-024 tests."""
    print("🧪 Running JIRA-024 Final Market Verification Tests")
    print("=" * 60)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestFinalMarketVerifier,
        TestMarketDiscrepancyMonitorIntegration,
        TestJIRA024Integration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    print(f"\n📊 TEST RESULTS")
    print("-" * 40)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\n❌ FAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print(f"\n💥 ERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\n{'✅' if success else '❌'} JIRA-024 Tests {'PASSED' if success else 'FAILED'}")
    
    return success


if __name__ == "__main__":
    run_tests()
