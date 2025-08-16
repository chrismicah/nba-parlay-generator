#!/usr/bin/env python3
"""
Market Discrepancy Real-Time Monitor - JIRA-023A

Provides real-time monitoring and alerting for market discrepancies.
Continuously scans markets and sends alerts for arbitrage and value opportunities.
"""

import asyncio
import logging
import json
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from threading import Thread, Event
import queue

from tools.market_discrepancy_detector import MarketDiscrepancyDetector, ArbitrageOpportunity, ValueOpportunity

# Import final market verifier (JIRA-024)
try:
    from tools.final_market_verifier import FinalMarketVerifier, VerificationConfig, VerificationResult
    HAS_FINAL_VERIFIER = True
except ImportError:
    HAS_FINAL_VERIFIER = False
    logging.warning("FinalMarketVerifier not available - alerts will be sent without final verification")

logger = logging.getLogger(__name__)


@dataclass
class Alert:
    """Alert for market discrepancy opportunities."""
    alert_id: str
    alert_type: str  # 'arbitrage', 'value', 'suspicious'
    priority: str    # 'low', 'medium', 'high', 'critical'
    
    game_id: str
    market_type: str
    opportunity_data: Dict[str, Any]
    
    confidence: float
    profit_potential: float
    time_sensitivity: str  # 'immediate', 'short', 'medium', 'long'
    
    message: str
    recommended_action: str
    
    created_at: str
    expires_at: Optional[str] = None
    acknowledged: bool = False


@dataclass
class MonitoringConfig:
    """Configuration for market discrepancy monitoring."""
    scan_interval_seconds: int = 60
    alert_cooldown_seconds: int = 300  # 5 minutes between similar alerts
    min_arbitrage_profit: float = 0.02
    min_value_edge: float = 0.05
    max_alert_age_minutes: int = 30
    
    # Alert thresholds
    critical_arbitrage_threshold: float = 0.05  # 5%+ profit
    high_value_threshold: float = 0.10         # 10%+ edge
    
    # Monitoring scope
    enabled_markets: List[str] = None
    priority_games: List[str] = None
    
    # Final verification settings (JIRA-024)
    enable_final_verification: bool = True
    verification_config: Optional['VerificationConfig'] = None
    
    def __post_init__(self):
        if self.enabled_markets is None:
            self.enabled_markets = ['h2h', 'spreads', 'totals']
        if self.priority_games is None:
            self.priority_games = []
        if self.verification_config is None and HAS_FINAL_VERIFIER:
            # Default verification config
            from tools.final_market_verifier import VerificationConfig
            self.verification_config = VerificationConfig()


class MarketDiscrepancyMonitor:
    """
    Real-time monitor for market discrepancies with alerting capabilities.
    
    Continuously scans markets for arbitrage and value opportunities,
    generates alerts, and provides notification mechanisms.
    """
    
    def __init__(self, 
                 config: Optional[MonitoringConfig] = None,
                 alert_handlers: Optional[List[Callable]] = None):
        """
        Initialize the market discrepancy monitor.
        
        Args:
            config: Monitoring configuration
            alert_handlers: List of functions to handle alerts
        """
        self.config = config or MonitoringConfig()
        self.alert_handlers = alert_handlers or []
        
        # Initialize detector
        self.detector = MarketDiscrepancyDetector(
            min_arbitrage_profit=self.config.min_arbitrage_profit,
            min_value_edge=self.config.min_value_edge
        )
        
        # Initialize final market verifier (JIRA-024)
        self.final_verifier = None
        if self.config.enable_final_verification and HAS_FINAL_VERIFIER:
            self.final_verifier = FinalMarketVerifier(self.config.verification_config)
            logger.info("Final market verification enabled")
        else:
            logger.warning("Final market verification disabled or unavailable")
        
        # Monitoring state
        self.is_monitoring = False
        self.monitor_thread = None
        self.stop_event = Event()
        
        # Alert management
        self.active_alerts = {}
        self.alert_history = []
        self.alert_queue = queue.Queue()
        self.last_alert_times = {}  # For cooldown management
        
        # Statistics
        self.scan_count = 0
        self.total_alerts_generated = 0
        self.alerts_verified = 0
        self.alerts_cancelled_verification = 0
        self.start_time = None
        
        logger.info("MarketDiscrepancyMonitor initialized")
    
    def add_alert_handler(self, handler: Callable[[Alert], None]):
        """Add an alert handler function."""
        self.alert_handlers.append(handler)
        logger.info(f"Added alert handler: {handler.__name__}")
    
    def start_monitoring(self, game_ids: List[str]):
        """Start real-time monitoring for specified games."""
        if self.is_monitoring:
            logger.warning("Monitor is already running")
            return
        
        self.is_monitoring = True
        self.start_time = datetime.now(timezone.utc)
        self.stop_event.clear()
        
        # Start monitoring thread
        self.monitor_thread = Thread(
            target=self._monitoring_loop,
            args=(game_ids,),
            daemon=True
        )
        self.monitor_thread.start()
        
        # Start alert processing thread
        alert_thread = Thread(
            target=self._alert_processing_loop,
            daemon=True
        )
        alert_thread.start()
        
        logger.info(f"Started monitoring {len(game_ids)} games")
    
    def stop_monitoring(self):
        """Stop real-time monitoring."""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        self.stop_event.set()
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        logger.info("Stopped monitoring")
    
    def _monitoring_loop(self, game_ids: List[str]):
        """Main monitoring loop."""
        logger.info("Monitoring loop started")
        
        while not self.stop_event.is_set():
            try:
                scan_start = time.time()
                
                # Scan for discrepancies
                discrepancies = self.detector.scan_multiple_games(game_ids)
                
                # Process discrepancies into alerts
                self._process_discrepancies(discrepancies)
                
                # Clean up old alerts
                self._cleanup_old_alerts()
                
                # Update statistics
                self.scan_count += 1
                scan_duration = time.time() - scan_start
                
                logger.debug(f"Scan {self.scan_count} completed in {scan_duration:.2f}s")
                
                # Wait for next scan
                self.stop_event.wait(self.config.scan_interval_seconds)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                self.stop_event.wait(10)  # Brief pause before retry
        
        logger.info("Monitoring loop stopped")
    
    def _process_discrepancies(self, discrepancies: Dict[str, List]):
        """Process detected discrepancies into alerts."""
        for game_id, game_discrepancies in discrepancies.items():
            for discrepancy in game_discrepancies:
                alert = self._create_alert_from_discrepancy(game_id, discrepancy)
                if alert and self._should_generate_alert(alert):
                    self.alert_queue.put(alert)
    
    def _create_alert_from_discrepancy(self, game_id: str, discrepancy) -> Optional[Alert]:
        """Create alert from market discrepancy."""
        current_time = datetime.now(timezone.utc)
        
        if discrepancy.discrepancy_type == 'arbitrage':
            # Find corresponding arbitrage opportunity
            arbitrage_opp = None
            for opp in self.detector.arbitrage_opportunities:
                if opp.game_id == game_id and opp.market_type == discrepancy.market_type:
                    arbitrage_opp = opp
                    break
            
            if not arbitrage_opp:
                return None
            
            # Determine priority
            if arbitrage_opp.profit_percentage >= self.config.critical_arbitrage_threshold:
                priority = 'critical'
            elif arbitrage_opp.profit_percentage >= 0.03:  # 3%
                priority = 'high'
            else:
                priority = 'medium'
            
            # Create alert
            alert = Alert(
                alert_id=f"arb_{game_id}_{discrepancy.market_type}_{int(current_time.timestamp())}",
                alert_type='arbitrage',
                priority=priority,
                game_id=game_id,
                market_type=discrepancy.market_type,
                opportunity_data=asdict(arbitrage_opp),
                confidence=discrepancy.confidence_score,
                profit_potential=arbitrage_opp.profit_percentage,
                time_sensitivity='immediate',
                message=f"Arbitrage opportunity: {arbitrage_opp.profit_percentage:.2%} guaranteed profit",
                recommended_action=f"Place bets across {len(arbitrage_opp.sportsbooks_involved)} sportsbooks",
                created_at=current_time.isoformat(),
                expires_at=(current_time + timedelta(minutes=10)).isoformat()  # Arbitrage expires quickly
            )
            
            return alert
        
        elif discrepancy.discrepancy_type == 'value':
            # Find corresponding value opportunity
            value_opp = None
            for opp in self.detector.value_opportunities:
                if (opp.game_id == game_id and 
                    opp.market_type == discrepancy.market_type and
                    discrepancy.market_key.endswith(opp.outcome)):
                    value_opp = opp
                    break
            
            if not value_opp:
                return None
            
            # Determine priority
            if value_opp.implied_edge >= self.config.high_value_threshold:
                priority = 'high'
            elif value_opp.implied_edge >= 0.07:  # 7%
                priority = 'medium'
            else:
                priority = 'low'
            
            # Create alert
            alert = Alert(
                alert_id=f"val_{game_id}_{discrepancy.market_type}_{value_opp.outcome}_{int(current_time.timestamp())}",
                alert_type='value',
                priority=priority,
                game_id=game_id,
                market_type=discrepancy.market_type,
                opportunity_data=asdict(value_opp),
                confidence=discrepancy.confidence_score,
                profit_potential=value_opp.implied_edge,
                time_sensitivity='short',
                message=f"Value opportunity: {value_opp.implied_edge:.1%} edge on {value_opp.outcome}",
                recommended_action=f"Bet {value_opp.outcome} at {value_opp.sportsbook}",
                created_at=current_time.isoformat(),
                expires_at=(current_time + timedelta(minutes=30)).isoformat()
            )
            
            return alert
        
        return None
    
    def _should_generate_alert(self, alert: Alert) -> bool:
        """Check if alert should be generated based on cooldown and other criteria."""
        alert_key = f"{alert.game_id}_{alert.market_type}_{alert.alert_type}"
        
        # Check cooldown
        if alert_key in self.last_alert_times:
            time_since_last = datetime.now(timezone.utc) - self.last_alert_times[alert_key]
            if time_since_last.total_seconds() < self.config.alert_cooldown_seconds:
                return False
        
        # Check if similar alert already active
        for active_alert in self.active_alerts.values():
            if (active_alert.game_id == alert.game_id and
                active_alert.market_type == alert.market_type and
                active_alert.alert_type == alert.alert_type):
                return False
        
        return True
    
    def _alert_processing_loop(self):
        """Process alerts from the queue."""
        while self.is_monitoring or not self.alert_queue.empty():
            try:
                # Get alert from queue (with timeout)
                alert = self.alert_queue.get(timeout=1)
                
                # Add to active alerts
                self.active_alerts[alert.alert_id] = alert
                self.alert_history.append(alert)
                self.total_alerts_generated += 1
                
                # Update last alert time
                alert_key = f"{alert.game_id}_{alert.market_type}_{alert.alert_type}"
                self.last_alert_times[alert_key] = datetime.now(timezone.utc)
                
                # Send to handlers
                self._send_alert(alert)
                
                logger.info(f"Generated {alert.priority} {alert.alert_type} alert for {alert.game_id}")
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing alert: {e}")
    
    def _send_alert(self, alert: Alert):
        """Send alert to all registered handlers with final verification (JIRA-024)."""
        # Perform final market verification before dispatch
        if self.final_verifier:
            try:
                verification_report = self.final_verifier.verify_alert_before_dispatch(alert)
                self.alerts_verified += 1
                
                if not verification_report.should_dispatch_alert:
                    # Cancel the alert
                    self.alerts_cancelled_verification += 1
                    logger.info(f"Alert {alert.alert_id} cancelled after verification: {verification_report.cancellation_reason}")
                    
                    # Remove from active alerts since it was cancelled
                    if alert.alert_id in self.active_alerts:
                        del self.active_alerts[alert.alert_id]
                    
                    # Log verification details
                    logger.debug(f"Verification report for {alert.alert_id}: "
                               f"Result={verification_report.verification_result.value}, "
                               f"Max odds shift={verification_report.max_odds_shift}, "
                               f"Unavailable markets={len(verification_report.unavailable_markets)}")
                    
                    return  # Don't send the alert
                
                # Alert passed verification, add verification info to alert message
                alert.message += f" [Verified: {verification_report.verification_result.value}]"
                
                logger.info(f"Alert {alert.alert_id} passed final verification")
                
            except Exception as e:
                logger.error(f"Final verification failed for alert {alert.alert_id}: {e}")
                # Decide whether to send alert anyway or cancel it
                if alert.priority in ['critical', 'high']:
                    logger.warning(f"Sending {alert.priority} priority alert despite verification failure")
                else:
                    logger.info(f"Cancelling {alert.priority} priority alert due to verification failure")
                    return
        
        # Send alert to all handlers
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Alert handler {handler.__name__} failed: {e}")
    
    def _cleanup_old_alerts(self):
        """Remove expired alerts from active alerts."""
        current_time = datetime.now(timezone.utc)
        expired_alerts = []
        
        for alert_id, alert in self.active_alerts.items():
            if alert.expires_at:
                expires_at = datetime.fromisoformat(alert.expires_at.replace('Z', '+00:00'))
                if current_time > expires_at:
                    expired_alerts.append(alert_id)
        
        for alert_id in expired_alerts:
            del self.active_alerts[alert_id]
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].acknowledged = True
            logger.info(f"Alert {alert_id} acknowledged")
            return True
        return False
    
    def get_active_alerts(self, priority_filter: Optional[str] = None) -> List[Alert]:
        """Get currently active alerts."""
        alerts = list(self.active_alerts.values())
        
        if priority_filter:
            alerts = [a for a in alerts if a.priority == priority_filter]
        
        # Sort by priority and creation time
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        alerts.sort(key=lambda a: (priority_order.get(a.priority, 4), a.created_at))
        
        return alerts
    
    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        uptime = None
        if self.start_time:
            uptime = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        
        stats = {
            'is_monitoring': self.is_monitoring,
            'uptime_seconds': uptime,
            'scan_count': self.scan_count,
            'total_alerts_generated': self.total_alerts_generated,
            'active_alerts': len(self.active_alerts),
            'alert_history_count': len(self.alert_history),
            'detector_stats': self.detector.get_summary_stats(),
            'config': asdict(self.config)
        }
        
        # Add verification statistics (JIRA-024)
        if self.final_verifier:
            verification_stats = self.final_verifier.get_verification_stats()
            stats.update({
                'verification_enabled': True,
                'alerts_verified': self.alerts_verified,
                'alerts_cancelled_verification': self.alerts_cancelled_verification,
                'verification_success_rate': verification_stats['success_rate'],
                'verification_details': verification_stats
            })
        else:
            stats['verification_enabled'] = False
        
        return stats
    
    def export_alerts(self, 
                     start_time: Optional[datetime] = None,
                     end_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Export alert history for analysis."""
        alerts = self.alert_history
        
        if start_time:
            alerts = [a for a in alerts 
                     if datetime.fromisoformat(a.created_at.replace('Z', '+00:00')) >= start_time]
        
        if end_time:
            alerts = [a for a in alerts 
                     if datetime.fromisoformat(a.created_at.replace('Z', '+00:00')) <= end_time]
        
        return [asdict(alert) for alert in alerts]


# Alert Handler Examples
def console_alert_handler(alert: Alert):
    """Example alert handler that prints to console."""
    priority_emoji = {
        'critical': '🚨',
        'high': '⚠️',
        'medium': '📊',
        'low': 'ℹ️'
    }
    
    emoji = priority_emoji.get(alert.priority, '📢')
    
    print(f"\n{emoji} {alert.priority.upper()} ALERT {emoji}")
    print(f"Type: {alert.alert_type.title()}")
    print(f"Game: {alert.game_id}")
    print(f"Market: {alert.market_type}")
    print(f"Message: {alert.message}")
    print(f"Action: {alert.recommended_action}")
    print(f"Confidence: {alert.confidence:.1%}")
    print(f"Profit Potential: {alert.profit_potential:.2%}")
    print(f"Time: {alert.created_at}")
    print("-" * 50)


def log_alert_handler(alert: Alert):
    """Example alert handler that logs alerts."""
    logger.info(f"ALERT: {alert.alert_type} | {alert.priority} | {alert.game_id} | {alert.message}")


def json_file_alert_handler(alert: Alert):
    """Example alert handler that saves alerts to JSON file."""
    try:
        import os
        os.makedirs('data/alerts', exist_ok=True)
        
        filename = f"data/alerts/alert_{alert.alert_id}.json"
        with open(filename, 'w') as f:
            json.dump(asdict(alert), f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save alert to file: {e}")


def main():
    """Main function for testing market discrepancy monitoring."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🔍 Market Discrepancy Real-Time Monitor - JIRA-023A")
    print("=" * 60)
    
    # Create monitoring configuration
    config = MonitoringConfig(
        scan_interval_seconds=10,  # Fast scanning for demo
        alert_cooldown_seconds=60,
        min_arbitrage_profit=0.01,  # Lower threshold for demo
        min_value_edge=0.03
    )
    
    # Initialize monitor with alert handlers
    monitor = MarketDiscrepancyMonitor(
        config=config,
        alert_handlers=[
            console_alert_handler,
            log_alert_handler,
            json_file_alert_handler
        ]
    )
    
    # Test games
    test_games = ['game_001', 'game_002', 'game_003']
    
    print(f"🚀 Starting monitoring for games: {', '.join(test_games)}")
    print("Monitoring will run for 30 seconds...")
    
    try:
        # Start monitoring
        monitor.start_monitoring(test_games)
        
        # Let it run for a bit
        time.sleep(30)
        
        # Show results
        stats = monitor.get_monitoring_stats()
        print(f"\n📊 MONITORING STATISTICS")
        print("=" * 50)
        print(f"Uptime: {stats['uptime_seconds']:.1f} seconds")
        print(f"Scans completed: {stats['scan_count']}")
        print(f"Alerts generated: {stats['total_alerts_generated']}")
        print(f"Active alerts: {stats['active_alerts']}")
        
        # Show active alerts
        active_alerts = monitor.get_active_alerts()
        if active_alerts:
            print(f"\n🚨 ACTIVE ALERTS ({len(active_alerts)})")
            print("=" * 50)
            for alert in active_alerts[:5]:  # Show top 5
                print(f"• {alert.priority.upper()}: {alert.message}")
                print(f"  Game: {alert.game_id}, Confidence: {alert.confidence:.1%}")
        
    finally:
        # Stop monitoring
        monitor.stop_monitoring()
        print("\n✅ Monitoring stopped")
    
    print(f"\n✅ JIRA-023A Market Discrepancy Monitor Complete!")
    print(f"🎯 Real-time monitoring and alerting system operational")


if __name__ == "__main__":
    main()
