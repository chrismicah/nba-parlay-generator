#!/usr/bin/env python3
"""
Complete Demo for JIRA-023A: Market Discrepancy Detector System

Demonstrates the full functionality of the market discrepancy detection system
including arbitrage detection, value identification, and ParlayStrategist integration.
"""

import sys
import time
import logging
from pathlib import Path

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from tools.market_discrepancy_detector import MarketDiscrepancyDetector
from tools.enhanced_parlay_strategist_with_discrepancy import EnhancedParlayStrategistWithDiscrepancy
from tools.market_discrepancy_monitor import MarketDiscrepancyMonitor, console_alert_handler, MonitoringConfig


def demo_market_discrepancy_detection():
    """Demonstrate core market discrepancy detection."""
    print("🔍 DEMO 1: Market Discrepancy Detection")
    print("=" * 60)
    
    # Initialize detector
    detector = MarketDiscrepancyDetector(
        min_arbitrage_profit=0.02,  # 2% minimum
        min_value_edge=0.05,        # 5% minimum
        confidence_threshold=0.7
    )
    
    # Test with sample games (uses mock data since APIs not available)
    sample_games = ['game_001', 'game_002', 'game_003']
    
    print(f"🎯 Scanning {len(sample_games)} games for discrepancies...")
    discrepancies = detector.scan_multiple_games(sample_games)
    
    # Display results
    total_discrepancies = sum(len(discs) for discs in discrepancies.values())
    print(f"\n📊 DETECTION RESULTS")
    print("-" * 40)
    print(f"Games scanned: {len(sample_games)}")
    print(f"Total discrepancies: {total_discrepancies}")
    print(f"Arbitrage opportunities: {len(detector.arbitrage_opportunities)}")
    print(f"Value opportunities: {len(detector.value_opportunities)}")
    
    # Show top arbitrage opportunities
    if detector.arbitrage_opportunities:
        print(f"\n💰 TOP ARBITRAGE OPPORTUNITIES")
        print("-" * 40)
        for i, opp in enumerate(detector.arbitrage_opportunities[:3], 1):
            print(f"{i}. Game {opp.game_id} ({opp.market_type})")
            print(f"   Profit: {opp.profit_percentage:.2%} guaranteed")
            print(f"   Risk Level: {opp.risk_level}")
            print(f"   Sportsbooks: {', '.join(opp.sportsbooks_involved)}")
    
    # Show top value opportunities
    if detector.value_opportunities:
        print(f"\n📈 TOP VALUE OPPORTUNITIES")
        print("-" * 40)
        for i, opp in enumerate(detector.value_opportunities[:3], 1):
            print(f"{i}. Game {opp.game_id} - {opp.outcome}")
            print(f"   Edge: {opp.implied_edge:.2%} at {opp.sportsbook}")
            print(f"   Confidence: {opp.confidence_level}")
            print(f"   Kelly Stake: {opp.suggested_stake:.1%} of bankroll")
    
    return detector


def demo_enhanced_parlay_strategist(detector):
    """Demonstrate enhanced parlay strategist integration."""
    print(f"\n🎯 DEMO 2: Enhanced ParlayStrategist Integration")
    print("=" * 60)
    
    # Initialize enhanced strategist
    strategist = EnhancedParlayStrategistWithDiscrepancy(
        base_strategist=None,  # No base strategist for demo
        discrepancy_weight=0.3,
        min_arbitrage_confidence=0.8,
        min_value_confidence=0.7
    )
    
    # Generate enhanced recommendation
    test_games = ['game_001', 'game_002']
    
    print(f"🚀 Generating enhanced recommendation for: {', '.join(test_games)}")
    result = strategist.generate_enhanced_parlay_recommendation(test_games)
    
    # Display results
    print(f"\n📊 ENHANCEMENT RESULTS")
    print("-" * 40)
    
    metadata = result['analysis_metadata']
    print(f"Games analyzed: {metadata['games_analyzed']}")
    print(f"Discrepancies found: {metadata['discrepancies_found']}")
    print(f"Arbitrage opportunities: {metadata['arbitrage_opportunities']}")
    print(f"Value opportunities: {metadata['value_opportunities']}")
    
    # Show enhanced recommendation
    enhanced_rec = result['enhanced_recommendation']
    print(f"\n🎯 ENHANCED RECOMMENDATION")
    print("-" * 40)
    print(f"Confidence: {enhanced_rec.confidence:.1%}")
    
    if hasattr(enhanced_rec, 'discrepancy_boost'):
        print(f"Base confidence: {enhanced_rec.base_confidence:.1%}")
        print(f"Discrepancy boost: +{enhanced_rec.discrepancy_boost:.1%}")
        print(f"Arbitrage signals: {enhanced_rec.arbitrage_signals}")
        print(f"Value signals: {enhanced_rec.value_signals}")
    
    # Show high-value signals
    signals = result['high_value_signals']
    if signals:
        print(f"\n🚨 HIGH-VALUE SIGNALS ({len(signals)})")
        print("-" * 40)
        for i, signal in enumerate(signals[:3], 1):
            print(f"{i}. {signal['signal_type'].replace('_', ' ').title()}")
            print(f"   Game: {signal['game_id']}")
            print(f"   Confidence: {signal['confidence']:.1%}")
            print(f"   Action: {signal['recommended_action']}")
    
    print(f"\n📝 REASONING EXCERPT:")
    print("-" * 40)
    reasoning_lines = enhanced_rec.reasoning.split('\n')[:5]
    for line in reasoning_lines:
        if line.strip():
            print(f"  {line}")
    if len(enhanced_rec.reasoning.split('\n')) > 5:
        print("  ...")
    
    return strategist


def demo_real_time_monitoring():
    """Demonstrate real-time monitoring system."""
    print(f"\n🔍 DEMO 3: Real-Time Monitoring System")
    print("=" * 60)
    
    # Custom alert handler for demo
    alert_count = [0]  # Use list for mutable counter
    
    def demo_alert_handler(alert):
        alert_count[0] += 1
        priority_emoji = {'critical': '🚨', 'high': '⚠️', 'medium': '📊', 'low': 'ℹ️'}
        emoji = priority_emoji.get(alert.priority, '📢')
        
        print(f"\n{emoji} ALERT #{alert_count[0]} - {alert.priority.upper()}")
        print(f"   Type: {alert.alert_type.title()}")
        print(f"   Game: {alert.game_id} ({alert.market_type})")
        print(f"   Message: {alert.message}")
        print(f"   Confidence: {alert.confidence:.1%}")
        print(f"   Profit Potential: {alert.profit_potential:.2%}")
    
    # Initialize monitor with demo configuration
    config = MonitoringConfig(
        scan_interval_seconds=3,   # Fast scanning for demo
        alert_cooldown_seconds=5,  # Short cooldown for demo
        min_arbitrage_profit=0.01, # Lower threshold for demo
        min_value_edge=0.03
    )
    
    monitor = MarketDiscrepancyMonitor(
        config=config,
        alert_handlers=[demo_alert_handler]
    )
    
    # Start monitoring
    test_games = ['game_001', 'game_002', 'game_003']
    monitor_duration = 10  # seconds
    
    print(f"🚀 Starting monitoring for {len(test_games)} games...")
    print(f"⏱️  Will monitor for {monitor_duration} seconds...")
    print("🔔 Alerts will appear below:")
    
    try:
        monitor.start_monitoring(test_games)
        time.sleep(monitor_duration)
        
    finally:
        monitor.stop_monitoring()
    
    # Show monitoring statistics
    stats = monitor.get_monitoring_stats()
    print(f"\n📊 MONITORING STATISTICS")
    print("-" * 40)
    print(f"Monitoring duration: {stats['uptime_seconds']:.1f} seconds")
    print(f"Scans completed: {stats['scan_count']}")
    print(f"Alerts generated: {stats['total_alerts_generated']}")
    print(f"Active alerts: {stats['active_alerts']}")
    
    # Show active alerts
    active_alerts = monitor.get_active_alerts()
    if active_alerts:
        print(f"\n🚨 ACTIVE ALERTS ({len(active_alerts)})")
        print("-" * 40)
        for alert in active_alerts[:3]:
            print(f"• {alert.priority.upper()}: {alert.message}")
            print(f"  Confidence: {alert.confidence:.1%}, Potential: {alert.profit_potential:.2%}")
    
    return monitor


def demo_system_integration():
    """Demonstrate complete system integration."""
    print(f"\n🎯 DEMO 4: Complete System Integration")
    print("=" * 60)
    
    print("🔗 Integration Points:")
    print("  ✅ OddsFetcherTool (JIRA-004) → Market Data")
    print("  ✅ Market Discrepancy Detection → Opportunities")
    print("  ✅ Enhanced ParlayStrategist → Recommendations")
    print("  ✅ Real-Time Monitor → Alerts")
    print("  ✅ High-Value Signals → Strategic Intelligence")
    
    print(f"\n🎯 Production Workflow:")
    print("  1. 📡 Continuous market scanning across sportsbooks")
    print("  2. 🔍 Real-time discrepancy detection and analysis")
    print("  3. 🚨 Intelligent alerting for time-sensitive opportunities")
    print("  4. 🎲 Enhanced parlay recommendations with market signals")
    print("  5. 💰 Systematic exploitation of market inefficiencies")
    
    print(f"\n📈 Key Benefits:")
    print("  • Guaranteed profit identification (arbitrage)")
    print("  • Statistical edge detection (value betting)")
    print("  • Real-time market intelligence")
    print("  • Risk-assessed opportunity ranking")
    print("  • Automated monitoring and alerting")
    print("  • Seamless integration with existing systems")


def main():
    """Run the complete JIRA-023A demonstration."""
    # Configure logging to reduce noise
    logging.basicConfig(level=logging.WARNING)
    
    print("🎯 JIRA-023A COMPLETE SYSTEM DEMONSTRATION")
    print("Market Discrepancy Detector with Real-Time Monitoring")
    print("=" * 80)
    
    try:
        # Demo 1: Core detection
        detector = demo_market_discrepancy_detection()
        
        # Demo 2: Enhanced strategist
        strategist = demo_enhanced_parlay_strategist(detector)
        
        # Demo 3: Real-time monitoring
        monitor = demo_real_time_monitoring()
        
        # Demo 4: System integration overview
        demo_system_integration()
        
        # Final summary
        print(f"\n✅ JIRA-023A DEMONSTRATION COMPLETE!")
        print("=" * 60)
        print("🎯 All systems operational and integrated:")
        print("  ✅ Market Discrepancy Detection")
        print("  ✅ Arbitrage Opportunity Identification") 
        print("  ✅ Value Betting Intelligence")
        print("  ✅ Enhanced Parlay Strategy")
        print("  ✅ Real-Time Monitoring & Alerts")
        print("  ✅ ParlayStrategistAgent Integration")
        
        print(f"\n🚀 PRODUCTION READINESS:")
        print("  ✅ Comprehensive market analysis")
        print("  ✅ Real-time opportunity detection")
        print("  ✅ Intelligent signal integration")
        print("  ✅ Risk-assessed recommendations")
        print("  ✅ Scalable monitoring architecture")
        print("  ✅ Extensible alert framework")
        
        print(f"\n💡 Next Steps:")
        print("  1. Deploy with live odds data")
        print("  2. Configure production alert handlers")
        print("  3. Integrate with betting execution system")
        print("  4. Monitor performance and tune thresholds")
        
    except KeyboardInterrupt:
        print("\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo error: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    print(f"\n{'✅ Demo completed successfully!' if success else '❌ Demo encountered errors'}")
