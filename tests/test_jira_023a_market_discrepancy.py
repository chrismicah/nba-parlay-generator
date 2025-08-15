#!/usr/bin/env python3
"""
Test Suite for JIRA-023A: Market Discrepancy Detector System

Tests the complete market discrepancy detection system including:
- Market discrepancy detection algorithms
- Arbitrage opportunity identification
- Value betting opportunity detection
- ParlayStrategistAgent integration
- Real-time monitoring and alerting
"""

import unittest
import time
import tempfile
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.market_discrepancy_detector import (
    MarketDiscrepancyDetector, MarketDiscrepancy, ArbitrageOpportunity, ValueOpportunity
)
from tools.enhanced_parlay_strategist_with_discrepancy import EnhancedParlayStrategistWithDiscrepancy
from tools.market_discrepancy_monitor import MarketDiscrepancyMonitor, MonitoringConfig, Alert


class TestMarketDiscrepancyDetector(unittest.TestCase):
    """Test the core market discrepancy detection functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.detector = MarketDiscrepancyDetector(
            min_arbitrage_profit=0.02,
            min_value_edge=0.05,
            confidence_threshold=0.7
        )
    
    def test_odds_conversion(self):
        """Test odds to implied probability conversion."""
        # Test positive American odds
        prob = self.detector.odds_to_implied_probability(100)
        self.assertAlmostEqual(prob, 0.5, places=3)
        
        # Test negative American odds
        prob = self.detector.odds_to_implied_probability(-110)
        self.assertAlmostEqual(prob, 0.524, places=3)
        
        # Test conversion back
        odds = self.detector.implied_probability_to_odds(0.5)
        self.assertAlmostEqual(abs(odds), 100, places=0)
    
    def test_arbitrage_calculation(self):
        """Test arbitrage percentage calculation."""
        # No arbitrage case
        implied_probs = [0.52, 0.48]  # Sums to 1.0
        arb_pct = self.detector.calculate_arbitrage_percentage(implied_probs)
        self.assertAlmostEqual(arb_pct, 0.0, places=3)
        
        # Arbitrage case
        implied_probs = [0.45, 0.45]  # Sums to 0.9
        arb_pct = self.detector.calculate_arbitrage_percentage(implied_probs)
        self.assertAlmostEqual(arb_pct, -0.1, places=3)
        
        # Overround case (typical sportsbook)
        implied_probs = [0.55, 0.55]  # Sums to 1.1
        arb_pct = self.detector.calculate_arbitrage_percentage(implied_probs)
        self.assertAlmostEqual(arb_pct, 0.1, places=3)
    
    def create_mock_market_data(self, scenario='normal'):
        """Create mock market data for testing."""
        if scenario == 'arbitrage':
            # Create clear arbitrage opportunity
            mock_data = {
                'sportsbook1': Mock(selections=[
                    Mock(name='home', price=-90),   # Better home odds
                    Mock(name='away', price=110)
                ]),
                'sportsbook2': Mock(selections=[
                    Mock(name='home', price=-120),
                    Mock(name='away', price=130)    # Better away odds
                ])
            }
        elif scenario == 'value':
            # Create value opportunity
            mock_data = {
                'sportsbook1': Mock(selections=[
                    Mock(name='home', price=-110),
                    Mock(name='away', price=100)    # Outlier odds
                ]),
                'sportsbook2': Mock(selections=[
                    Mock(name='home', price=-105),
                    Mock(name='away', price=-105)
                ]),
                'sportsbook3': Mock(selections=[
                    Mock(name='home', price=-108),
                    Mock(name='away', price=-102)
                ])
            }
        else:  # normal
            mock_data = {
                'sportsbook1': Mock(selections=[
                    Mock(name='home', price=-110),
                    Mock(name='away', price=-110)
                ]),
                'sportsbook2': Mock(selections=[
                    Mock(name='home', price=-105),
                    Mock(name='away', price=-115)
                ])
            }
        
        return mock_data
    
    def test_best_odds_finding(self):
        """Test finding best odds across sportsbooks."""
        mock_data = self.create_mock_market_data('arbitrage')
        best_odds = self.detector.find_best_odds_per_outcome(mock_data)
        
        self.assertIn('home', best_odds)
        self.assertIn('away', best_odds)
        
        # Best home odds should be -90 (from sportsbook1)
        self.assertEqual(best_odds['home']['sportsbook'], 'sportsbook1')
        self.assertEqual(best_odds['home']['odds'], -90)
        
        # Best away odds should be 130 (from sportsbook2)
        self.assertEqual(best_odds['away']['sportsbook'], 'sportsbook2')
        self.assertEqual(best_odds['away']['odds'], 130)
    
    def test_arbitrage_detection(self):
        """Test arbitrage opportunity detection."""
        mock_data = self.create_mock_market_data('arbitrage')
        
        arbitrage_opp = self.detector.detect_arbitrage_opportunity(
            'test_game', 'h2h', mock_data
        )
        
        self.assertIsNotNone(arbitrage_opp)
        self.assertIsInstance(arbitrage_opp, ArbitrageOpportunity)
        self.assertGreater(arbitrage_opp.profit_percentage, 0)
        self.assertEqual(len(arbitrage_opp.bets_required), 2)
        self.assertEqual(len(arbitrage_opp.sportsbooks_involved), 2)
    
    def test_value_detection(self):
        """Test value opportunity detection."""
        mock_data = self.create_mock_market_data('value')
        
        value_opps = self.detector.detect_value_opportunities(
            'test_game', 'h2h', mock_data
        )
        
        self.assertIsInstance(value_opps, list)
        # Should find value opportunities with 3 sportsbooks
        self.assertGreater(len(value_opps), 0)
        
        for opp in value_opps:
            self.assertIsInstance(opp, ValueOpportunity)
            self.assertGreater(opp.implied_edge, 0)
            self.assertIn(opp.confidence_level, ['low', 'medium', 'high'])
    
    def test_robust_consensus_calculation(self):
        """Test robust consensus calculation with outlier removal."""
        # Normal case
        probs = [0.5, 0.52, 0.48, 0.51, 0.49]
        consensus = self.detector.calculate_robust_consensus(probs)
        self.assertAlmostEqual(consensus, 0.5, places=2)
        
        # With outliers
        probs = [0.5, 0.52, 0.48, 0.51, 0.49, 0.8, 0.2]  # 0.8 and 0.2 are outliers
        consensus = self.detector.calculate_robust_consensus(probs)
        self.assertAlmostEqual(consensus, 0.5, places=1)  # Should ignore outliers
    
    def test_kelly_stake_calculation(self):
        """Test Kelly criterion stake calculation."""
        edge = 0.1  # 10% edge
        odds = 100  # Even money
        
        stake = self.detector.calculate_kelly_stake(edge, odds)
        
        self.assertGreater(stake, 0)
        self.assertLessEqual(stake, 0.1)  # Capped at 10%
    
    def test_risk_assessment(self):
        """Test arbitrage risk assessment."""
        mock_data = self.create_mock_market_data('arbitrage')
        best_odds = self.detector.find_best_odds_per_outcome(mock_data)
        
        risk_level = self.detector.assess_arbitrage_risk(mock_data, best_odds)
        
        self.assertIn(risk_level, ['low', 'medium', 'high'])
    
    def test_scan_game_workflow(self):
        """Test complete game scanning workflow."""
        # Mock the fetch_market_data method to return test data
        self.detector.fetch_market_data = Mock(return_value=self.create_mock_market_data('arbitrage'))
        
        discrepancies = self.detector.scan_game_for_discrepancies('test_game')
        
        self.assertIsInstance(discrepancies, list)
        # Should find arbitrage opportunity
        arb_discrepancies = [d for d in discrepancies if d.discrepancy_type == 'arbitrage']
        self.assertGreater(len(arb_discrepancies), 0)


class TestEnhancedParlayStrategist(unittest.TestCase):
    """Test the enhanced parlay strategist with discrepancy integration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.strategist = EnhancedParlayStrategistWithDiscrepancy(
            base_strategist=None,  # No base strategist for testing
            discrepancy_weight=0.3,
            min_arbitrage_confidence=0.8,
            min_value_confidence=0.7
        )
    
    def test_initialization(self):
        """Test strategist initialization."""
        self.assertIsNotNone(self.strategist.discrepancy_detector)
        self.assertEqual(self.strategist.discrepancy_weight, 0.3)
        self.assertEqual(self.strategist.min_arbitrage_confidence, 0.8)
        self.assertEqual(self.strategist.min_value_confidence, 0.7)
    
    def create_mock_discrepancy(self, discrepancy_type='arbitrage'):
        """Create mock discrepancy for testing."""
        if discrepancy_type == 'arbitrage':
            return MarketDiscrepancy(
                game_id='test_game',
                market_type='h2h',
                market_key='test_game_h2h',
                discrepancy_type='arbitrage',
                best_odds={'home': {'sportsbook': 'book1', 'odds': -90}},
                worst_odds={'home': {'sportsbook': 'book2', 'odds': -120}},
                arbitrage_percentage=0.05,
                implied_probability_spread=0.0,
                value_score=5.0,
                confidence_score=0.9,
                sportsbooks_compared=['book1', 'book2'],
                detection_timestamp=datetime.now(timezone.utc).isoformat(),
                market_data={},
                recommended_action="Arbitrage opportunity",
                profit_potential=5.0
            )
        else:  # value
            return MarketDiscrepancy(
                game_id='test_game',
                market_type='h2h',
                market_key='test_game_h2h_home',
                discrepancy_type='value',
                best_odds={'home': {'sportsbook': 'book1', 'odds': 120}},
                worst_odds={},
                arbitrage_percentage=0.0,
                implied_probability_spread=0.08,
                value_score=8.0,
                confidence_score=0.8,
                sportsbooks_compared=['book1', 'book2', 'book3'],
                detection_timestamp=datetime.now(timezone.utc).isoformat(),
                market_data={},
                recommended_action="Value bet",
                profit_potential=8.0
            )
    
    def test_discrepancy_factor_extraction(self):
        """Test extraction of reasoning factors from discrepancies."""
        discrepancies = [
            self.create_mock_discrepancy('arbitrage'),
            self.create_mock_discrepancy('value')
        ]
        
        factors = self.strategist.extract_discrepancy_factors('test_game', discrepancies)
        
        self.assertEqual(len(factors), 2)
        
        # Check arbitrage factor
        arb_factor = next(f for f in factors if f.factor_type == 'market_arbitrage')
        self.assertEqual(arb_factor.weight, 1.0)
        self.assertIn('profit', arb_factor.description.lower())
        
        # Check value factor
        val_factor = next(f for f in factors if f.factor_type == 'market_value')
        self.assertEqual(val_factor.weight, 0.8)
        self.assertIn('edge', val_factor.description.lower())
    
    def test_discrepancy_reasoning_generation(self):
        """Test generation of discrepancy-based reasoning."""
        mock_factors = [
            type('ReasoningFactor', (), {
                'factor_type': 'market_arbitrage',
                'description': 'Test arbitrage',
                'confidence': 0.9,
                'supporting_data': {
                    'profit_percentage': 0.05,
                    'market_type': 'h2h'
                }
            })(),
            type('ReasoningFactor', (), {
                'factor_type': 'market_value',
                'description': 'Test value',
                'confidence': 0.8,
                'supporting_data': {
                    'edge_percentage': 0.08,
                    'market_type': 'spreads',
                    'value_score': 8.0
                }
            })()
        ]
        
        reasoning = self.strategist.generate_discrepancy_reasoning(mock_factors)
        
        self.assertIn('MARKET DISCREPANCY ANALYSIS', reasoning)
        self.assertIn('ARBITRAGE OPPORTUNITIES', reasoning)
        self.assertIn('VALUE OPPORTUNITIES', reasoning)
        self.assertIn('STRATEGIC IMPLICATIONS', reasoning)
    
    def test_enhanced_recommendation_generation(self):
        """Test complete enhanced recommendation generation."""
        # Mock the scan_market_discrepancies method
        mock_discrepancies = {
            'test_game': [self.create_mock_discrepancy('arbitrage')]
        }
        self.strategist.scan_market_discrepancies = Mock(return_value=mock_discrepancies)
        
        # Mock high-value signals
        mock_signals = [{
            'signal_type': 'arbitrage_opportunity',
            'game_id': 'test_game',
            'confidence': 0.9,
            'recommended_action': 'Test action'
        }]
        self.strategist.discrepancy_detector.get_high_value_signals = Mock(return_value=mock_signals)
        
        result = self.strategist.generate_enhanced_parlay_recommendation(['test_game'])
        
        self.assertIn('enhanced_recommendation', result)
        self.assertIn('market_discrepancies', result)
        self.assertIn('high_value_signals', result)
        self.assertIn('analysis_metadata', result)
        
        # Check metadata
        metadata = result['analysis_metadata']
        self.assertEqual(metadata['games_analyzed'], 1)
        self.assertGreater(metadata['discrepancies_found'], 0)
    
    def test_system_status(self):
        """Test system status reporting."""
        status = self.strategist.get_system_status()
        
        self.assertIn('discrepancy_detector_status', status)
        self.assertIn('configuration', status)
        self.assertIn('detector_stats', status)
        
        self.assertEqual(status['discrepancy_detector_status'], 'active')
        self.assertEqual(status['configuration']['discrepancy_weight'], 0.3)


class TestMarketDiscrepancyMonitor(unittest.TestCase):
    """Test the real-time monitoring and alerting system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = MonitoringConfig(
            scan_interval_seconds=1,  # Fast for testing
            alert_cooldown_seconds=5,
            min_arbitrage_profit=0.01,
            min_value_edge=0.03
        )
        
        self.alert_received = []
        
        def test_alert_handler(alert):
            self.alert_received.append(alert)
        
        self.monitor = MarketDiscrepancyMonitor(
            config=self.config,
            alert_handlers=[test_alert_handler]
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        if self.monitor.is_monitoring:
            self.monitor.stop_monitoring()
    
    def test_monitor_initialization(self):
        """Test monitor initialization."""
        self.assertFalse(self.monitor.is_monitoring)
        self.assertEqual(len(self.monitor.alert_handlers), 1)
        self.assertIsNotNone(self.monitor.detector)
    
    def test_alert_creation(self):
        """Test alert creation from discrepancies."""
        # Create mock arbitrage opportunity
        mock_arbitrage = ArbitrageOpportunity(
            game_id='test_game',
            market_type='h2h',
            total_investment=100.0,
            guaranteed_profit=5.0,
            profit_percentage=0.05,
            bets_required=[],
            sportsbooks_involved=['book1', 'book2'],
            risk_level='low',
            time_sensitivity='immediate',
            liquidity_concerns=[],
            detection_timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        # Add to detector
        self.monitor.detector.arbitrage_opportunities = [mock_arbitrage]
        
        # Create mock discrepancy
        mock_discrepancy = MarketDiscrepancy(
            game_id='test_game',
            market_type='h2h',
            market_key='test_game_h2h',
            discrepancy_type='arbitrage',
            best_odds={},
            worst_odds={},
            arbitrage_percentage=0.05,
            implied_probability_spread=0.0,
            value_score=5.0,
            confidence_score=0.9,
            sportsbooks_compared=['book1', 'book2'],
            detection_timestamp=datetime.now(timezone.utc).isoformat(),
            market_data={},
            recommended_action="Test action",
            profit_potential=5.0
        )
        
        alert = self.monitor._create_alert_from_discrepancy('test_game', mock_discrepancy)
        
        self.assertIsNotNone(alert)
        self.assertEqual(alert.alert_type, 'arbitrage')
        self.assertEqual(alert.game_id, 'test_game')
        self.assertIn('profit', alert.message.lower())
    
    def test_alert_cooldown(self):
        """Test alert cooldown mechanism."""
        # Create test alert
        alert = Alert(
            alert_id='test_alert',
            alert_type='arbitrage',
            priority='high',
            game_id='test_game',
            market_type='h2h',
            opportunity_data={},
            confidence=0.9,
            profit_potential=0.05,
            time_sensitivity='immediate',
            message='Test alert',
            recommended_action='Test action',
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
        # First alert should be allowed
        should_generate = self.monitor._should_generate_alert(alert)
        self.assertTrue(should_generate)
        
        # Simulate alert generation
        alert_key = f"{alert.game_id}_{alert.market_type}_{alert.alert_type}"
        self.monitor.last_alert_times[alert_key] = datetime.now(timezone.utc)
        
        # Second alert should be blocked by cooldown
        should_generate = self.monitor._should_generate_alert(alert)
        self.assertFalse(should_generate)
    
    def test_monitoring_workflow(self):
        """Test basic monitoring workflow."""
        # Mock the detector to return test discrepancies
        mock_discrepancies = {
            'test_game': [MarketDiscrepancy(
                game_id='test_game',
                market_type='h2h',
                market_key='test_key',
                discrepancy_type='arbitrage',
                best_odds={},
                worst_odds={},
                arbitrage_percentage=0.05,
                implied_probability_spread=0.0,
                value_score=5.0,
                confidence_score=0.9,
                sportsbooks_compared=['book1', 'book2'],
                detection_timestamp=datetime.now(timezone.utc).isoformat(),
                market_data={},
                recommended_action="Test",
                profit_potential=5.0
            )]
        }
        
        self.monitor.detector.scan_multiple_games = Mock(return_value=mock_discrepancies)
        
        # Add mock arbitrage opportunity
        mock_arbitrage = ArbitrageOpportunity(
            game_id='test_game',
            market_type='h2h',
            total_investment=100.0,
            guaranteed_profit=5.0,
            profit_percentage=0.05,
            bets_required=[],
            sportsbooks_involved=['book1', 'book2'],
            risk_level='low',
            time_sensitivity='immediate',
            liquidity_concerns=[],
            detection_timestamp=datetime.now(timezone.utc).isoformat()
        )
        self.monitor.detector.arbitrage_opportunities = [mock_arbitrage]
        
        # Start monitoring briefly
        self.monitor.start_monitoring(['test_game'])
        time.sleep(2)  # Let it run for 2 seconds
        self.monitor.stop_monitoring()
        
        # Check results
        stats = self.monitor.get_monitoring_stats()
        self.assertGreater(stats['scan_count'], 0)
        self.assertFalse(stats['is_monitoring'])
    
    def test_alert_export(self):
        """Test alert history export."""
        # Add some test alerts to history
        test_alerts = [
            Alert(
                alert_id=f'test_{i}',
                alert_type='arbitrage',
                priority='high',
                game_id=f'game_{i}',
                market_type='h2h',
                opportunity_data={},
                confidence=0.9,
                profit_potential=0.05,
                time_sensitivity='immediate',
                message=f'Test alert {i}',
                recommended_action='Test action',
                created_at=(datetime.now(timezone.utc) - timedelta(hours=i)).isoformat()
            )
            for i in range(3)
        ]
        
        self.monitor.alert_history = test_alerts
        
        # Export all alerts
        exported = self.monitor.export_alerts()
        self.assertEqual(len(exported), 3)
        
        # Export with time filter
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        exported = self.monitor.export_alerts(start_time=cutoff)
        self.assertEqual(len(exported), 1)  # Only the most recent


class TestIntegrationScenarios(unittest.TestCase):
    """Test integration scenarios across the entire system."""
    
    def test_end_to_end_arbitrage_detection(self):
        """Test complete arbitrage detection workflow."""
        # Create detector
        detector = MarketDiscrepancyDetector()
        
        # Create mock data with clear arbitrage
        mock_data = {
            'book1': Mock(selections=[
                Mock(name='home', price=-80),   # Very good home odds
                Mock(name='away', price=100)
            ]),
            'book2': Mock(selections=[
                Mock(name='home', price=-120),
                Mock(name='away', price=150)    # Very good away odds
            ])
        }
        
        # Mock fetch method
        detector.fetch_market_data = Mock(return_value=mock_data)
        
        # Scan for discrepancies
        discrepancies = detector.scan_game_for_discrepancies('test_game')
        
        # Should find arbitrage
        arb_discrepancies = [d for d in discrepancies if d.discrepancy_type == 'arbitrage']
        self.assertGreater(len(arb_discrepancies), 0)
        
        # Should have arbitrage opportunity
        self.assertGreater(len(detector.arbitrage_opportunities), 0)
        
        # Get high-value signals
        signals = detector.get_high_value_signals()
        self.assertGreater(len(signals), 0)
        
        arb_signals = [s for s in signals if s['signal_type'] == 'arbitrage_opportunity']
        self.assertGreater(len(arb_signals), 0)
    
    def test_enhanced_strategist_integration(self):
        """Test enhanced strategist integration with discrepancy detection."""
        strategist = EnhancedParlayStrategistWithDiscrepancy()
        
        # Mock arbitrage opportunity
        mock_arbitrage = ArbitrageOpportunity(
            game_id='test_game',
            market_type='h2h',
            total_investment=100.0,
            guaranteed_profit=5.0,
            profit_percentage=0.05,
            bets_required=[],
            sportsbooks_involved=['book1', 'book2'],
            risk_level='low',
            time_sensitivity='immediate',
            liquidity_concerns=[],
            detection_timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        strategist.discrepancy_detector.arbitrage_opportunities = [mock_arbitrage]
        
        # Mock scan results
        mock_discrepancy = MarketDiscrepancy(
            game_id='test_game',
            market_type='h2h',
            market_key='test_key',
            discrepancy_type='arbitrage',
            best_odds={},
            worst_odds={},
            arbitrage_percentage=0.05,
            implied_probability_spread=0.0,
            value_score=5.0,
            confidence_score=0.9,
            sportsbooks_compared=['book1', 'book2'],
            detection_timestamp=datetime.now(timezone.utc).isoformat(),
            market_data={},
            recommended_action="Test",
            profit_potential=5.0
        )
        
        strategist.scan_market_discrepancies = Mock(return_value={'test_game': [mock_discrepancy]})
        
        # Generate recommendation
        result = strategist.generate_enhanced_parlay_recommendation(['test_game'])
        
        # Verify integration
        self.assertIn('enhanced_recommendation', result)
        self.assertIn('high_value_signals', result)
        
        enhanced_rec = result['enhanced_recommendation']
        self.assertGreater(enhanced_rec.confidence, 0.5)
        self.assertIn('arbitrage', enhanced_rec.reasoning.lower())


def main():
    """Run the complete test suite."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTest(loader.loadTestsFromTestCase(TestMarketDiscrepancyDetector))
    suite.addTest(loader.loadTestsFromTestCase(TestEnhancedParlayStrategist))
    suite.addTest(loader.loadTestsFromTestCase(TestMarketDiscrepancyMonitor))
    suite.addTest(loader.loadTestsFromTestCase(TestIntegrationScenarios))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    if result.wasSuccessful():
        print(f"\n✅ All tests passed! ({result.testsRun} tests)")
        print("🎯 JIRA-023A Market Discrepancy Detector - Test Suite Complete")
        return True
    else:
        print(f"\n❌ {len(result.failures)} test(s) failed, {len(result.errors)} error(s)")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
