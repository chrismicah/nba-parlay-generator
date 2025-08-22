#!/usr/bin/env python3
"""
API Cost Tracker - COST-TRACKER-001

Tracks API usage and costs across all services to manage budgets and 
optimize API call efficiency. Integrates with feedback loop for cost-aware
model retraining decisions.

Supported APIs:
- The Odds API
- API-Football 
- XAI/Grok
- Firecrawl
- Ball Don't Lie (free tier tracking)
- OpenAI/ChatGPT (if used)
"""

import logging
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict
import os

logger = logging.getLogger(__name__)


@dataclass
class APICall:
    """Single API call record."""
    service: str
    endpoint: str
    timestamp: datetime
    cost_usd: float
    success: bool
    response_size_kb: Optional[int] = None
    request_type: str = "GET"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class DailyCostSummary:
    """Daily cost summary for a service."""
    service: str
    date: str
    total_calls: int
    successful_calls: int
    total_cost_usd: float
    avg_cost_per_call: float
    total_data_kb: int
    peak_hour: int = 0


class APICostTracker:
    """Tracks API usage costs and provides budget management."""
    
    # API Cost Configuration (USD)
    COST_PER_CALL = {
        "the_odds_api": 0.01,      # $0.01 per request
        "api_football": 0.005,      # $0.005 per request  
        "xai_grok": 0.02,          # $0.02 per generation
        "firecrawl": 0.003,        # $0.003 per crawl
        "balldontlie": 0.0,        # Free tier
        "openai_gpt": 0.01,        # $0.01 per request (est)
        "anthropic_claude": 0.015,  # $0.015 per request (est)
    }
    
    # Daily limits (USD)
    DAILY_LIMITS = {
        "the_odds_api": 5.0,
        "api_football": 3.0,
        "xai_grok": 8.0,
        "firecrawl": 2.0,
        "balldontlie": 0.0,
        "openai_gpt": 10.0,
        "anthropic_claude": 10.0,
        "total": 25.0
    }
    
    def __init__(self, db_path: str = "data/api_cost_tracking.sqlite"):
        """Initialize API cost tracker."""
        self.db_path = db_path
        self.setup_database()
        
        # Cache for today's costs
        self._todays_costs = {}
        self._cache_date = None
        
        logger.info(f"API Cost Tracker initialized: {db_path}")
    
    def setup_database(self):
        """Setup SQLite database for cost tracking."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create api_calls table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                cost_usd REAL NOT NULL,
                success BOOLEAN NOT NULL,
                response_size_kb INTEGER,
                request_type TEXT DEFAULT 'GET',
                metadata TEXT,
                date_only TEXT NOT NULL
            )
        """)
        
        # Create daily_summaries table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service TEXT NOT NULL,
                date TEXT NOT NULL,
                total_calls INTEGER NOT NULL,
                successful_calls INTEGER NOT NULL,
                total_cost_usd REAL NOT NULL,
                avg_cost_per_call REAL NOT NULL,
                total_data_kb INTEGER NOT NULL,
                peak_hour INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                UNIQUE(service, date)
            )
        """)
        
        # Create indices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_calls_date ON api_calls(date_only)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_calls_service ON api_calls(service)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_summaries_date ON daily_summaries(date)")
        
        conn.commit()
        conn.close()
        
        logger.debug("API cost tracking database initialized")
    
    def log_api_call(self, service: str, endpoint: str, success: bool = True,
                    response_size_kb: Optional[int] = None, 
                    request_type: str = "GET",
                    metadata: Optional[Dict[str, Any]] = None) -> float:
        """
        Log an API call and return its cost.
        
        Args:
            service: API service name (e.g., 'the_odds_api')
            endpoint: API endpoint called
            success: Whether the call was successful
            response_size_kb: Response size in KB
            request_type: HTTP request type
            metadata: Additional metadata
            
        Returns:
            Cost of the API call in USD
        """
        timestamp = datetime.now()
        cost = self.COST_PER_CALL.get(service, 0.0)
        
        # Apply success penalty (failed calls still cost money but track differently)
        if not success:
            cost *= 0.5  # Half cost for failed calls
        
        # Store call record
        api_call = APICall(
            service=service,
            endpoint=endpoint,
            timestamp=timestamp,
            cost_usd=cost,
            success=success,
            response_size_kb=response_size_kb,
            request_type=request_type,
            metadata=metadata or {}
        )
        
        self._save_api_call(api_call)
        
        # Invalidate cache
        self._cache_date = None
        
        logger.debug(f"API call logged: {service}/{endpoint} - ${cost:.4f}")
        return cost
    
    def can_afford_call(self, service: str, check_total_limit: bool = True) -> Tuple[bool, str]:
        """
        Check if we can afford another API call.
        
        Args:
            service: API service to check
            check_total_limit: Whether to check total daily limit
            
        Returns:
            Tuple of (can_afford: bool, reason: str)
        """
        today_costs = self.get_todays_costs()
        
        # Check service-specific limit
        service_cost = today_costs.get(service, 0.0)
        service_limit = self.DAILY_LIMITS.get(service, 0.0)
        
        if service_limit > 0 and service_cost >= service_limit:
            return False, f"Daily limit exceeded for {service}: ${service_cost:.2f} >= ${service_limit:.2f}"
        
        # Check total limit
        if check_total_limit:
            total_cost = sum(today_costs.values())
            total_limit = self.DAILY_LIMITS.get("total", 25.0)
            
            if total_cost >= total_limit:
                return False, f"Total daily limit exceeded: ${total_cost:.2f} >= ${total_limit:.2f}"
        
        return True, "OK"
    
    def get_todays_costs(self) -> Dict[str, float]:
        """Get today's costs by service."""
        today = datetime.now().date().isoformat()
        
        # Use cache if available
        if self._cache_date == today and self._todays_costs:
            return self._todays_costs.copy()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT service, SUM(cost_usd) 
            FROM api_calls 
            WHERE date_only = ? 
            GROUP BY service
        """, (today,))
        
        costs = dict(cursor.fetchall())
        conn.close()
        
        # Update cache
        self._todays_costs = costs
        self._cache_date = today
        
        return costs.copy()
    
    def get_cost_summary(self, days_back: int = 7) -> Dict[str, Any]:
        """
        Get cost summary for the last N days.
        
        Args:
            days_back: Number of days to look back
            
        Returns:
            Summary dictionary with costs and statistics
        """
        start_date = (datetime.now() - timedelta(days=days_back)).date().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get total costs by service
        cursor.execute("""
            SELECT service, 
                   COUNT(*) as total_calls,
                   SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_calls,
                   SUM(cost_usd) as total_cost,
                   AVG(cost_usd) as avg_cost,
                   SUM(COALESCE(response_size_kb, 0)) as total_data_kb
            FROM api_calls 
            WHERE date_only >= ?
            GROUP BY service
            ORDER BY total_cost DESC
        """, (start_date,))
        
        service_stats = []
        total_cost = 0.0
        total_calls = 0
        
        for row in cursor.fetchall():
            service, calls, success_calls, cost, avg_cost, data_kb = row
            service_stats.append({
                "service": service,
                "total_calls": calls,
                "successful_calls": success_calls,
                "success_rate": success_calls / calls if calls > 0 else 0,
                "total_cost_usd": cost,
                "avg_cost_per_call": avg_cost,
                "total_data_kb": data_kb,
                "daily_limit": self.DAILY_LIMITS.get(service, 0.0),
                "limit_utilization": cost / self.DAILY_LIMITS.get(service, 1.0) if self.DAILY_LIMITS.get(service, 0) > 0 else 0
            })
            total_cost += cost
            total_calls += calls
        
        # Get daily breakdown
        cursor.execute("""
            SELECT date_only, SUM(cost_usd) 
            FROM api_calls 
            WHERE date_only >= ?
            GROUP BY date_only
            ORDER BY date_only
        """, (start_date,))
        
        daily_costs = dict(cursor.fetchall())
        
        conn.close()
        
        # Today's costs
        todays_costs = self.get_todays_costs()
        todays_total = sum(todays_costs.values())
        
        summary = {
            "period": f"Last {days_back} days",
            "total_cost_usd": total_cost,
            "total_calls": total_calls,
            "avg_cost_per_day": total_cost / days_back,
            "service_breakdown": service_stats,
            "daily_costs": daily_costs,
            "todays_costs": {
                "by_service": todays_costs,
                "total": todays_total,
                "remaining_budget": self.DAILY_LIMITS.get("total", 25.0) - todays_total
            },
            "limits": self.DAILY_LIMITS
        }
        
        return summary
    
    def estimate_feedback_loop_cost(self, outcome_samples: int = 100) -> float:
        """
        Estimate cost of running feedback loop based on expected API calls.
        
        Args:
            outcome_samples: Number of outcome samples to process
            
        Returns:
            Estimated cost in USD
        """
        # Estimate API calls needed for feedback loop
        estimated_costs = {
            "odds_api_calls": outcome_samples * 0.1 * self.COST_PER_CALL.get("the_odds_api", 0.01),
            "data_fetching": 5 * self.COST_PER_CALL.get("api_football", 0.005),
            "model_training": 2.0,  # Fixed cost for compute
            "mlflow_logging": 0.5   # Fixed cost for logging
        }
        
        total_cost = sum(estimated_costs.values())
        
        logger.debug(f"Estimated feedback loop cost: ${total_cost:.3f} for {outcome_samples} samples")
        return total_cost
    
    def should_run_feedback_loop(self, estimated_cost: Optional[float] = None) -> Tuple[bool, str]:
        """
        Determine if feedback loop should run based on costs.
        
        Args:
            estimated_cost: Pre-calculated estimated cost
            
        Returns:
            Tuple of (should_run: bool, reason: str)
        """
        if estimated_cost is None:
            estimated_cost = self.estimate_feedback_loop_cost()
        
        todays_costs = self.get_todays_costs()
        current_total = sum(todays_costs.values())
        
        # Check if adding estimated cost would exceed limits
        projected_total = current_total + estimated_cost
        daily_limit = self.DAILY_LIMITS.get("total", 25.0)
        
        if projected_total > daily_limit:
            return False, f"Would exceed daily limit: ${projected_total:.2f} > ${daily_limit:.2f}"
        
        # Check if we have sufficient buffer (20% of daily limit)
        buffer = daily_limit * 0.2
        if projected_total > (daily_limit - buffer):
            return False, f"Would exceed safe buffer: ${projected_total:.2f} > ${daily_limit - buffer:.2f}"
        
        return True, f"Safe to run: ${projected_total:.2f} <= ${daily_limit:.2f}"
    
    def generate_daily_summaries(self):
        """Generate daily summaries for cost reporting."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get dates that need summarization
        cursor.execute("""
            SELECT DISTINCT date_only 
            FROM api_calls 
            WHERE date_only NOT IN (
                SELECT DISTINCT date FROM daily_summaries
            )
        """)
        
        dates_to_process = [row[0] for row in cursor.fetchall()]
        
        for date in dates_to_process:
            # Get summary data for this date
            cursor.execute("""
                SELECT service,
                       COUNT(*) as total_calls,
                       SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_calls,
                       SUM(cost_usd) as total_cost,
                       AVG(cost_usd) as avg_cost,
                       SUM(COALESCE(response_size_kb, 0)) as total_data_kb,
                       MODE() WITHIN GROUP (ORDER BY CAST(strftime('%H', timestamp) AS INTEGER)) as peak_hour
                FROM api_calls 
                WHERE date_only = ?
                GROUP BY service
            """, (date,))
            
            for row in cursor.fetchall():
                service, total_calls, successful_calls, total_cost, avg_cost, total_data_kb, peak_hour = row
                
                # Insert daily summary
                cursor.execute("""
                    INSERT OR REPLACE INTO daily_summaries 
                    (service, date, total_calls, successful_calls, total_cost_usd, 
                     avg_cost_per_call, total_data_kb, peak_hour, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (service, date, total_calls, successful_calls, total_cost,
                      avg_cost, total_data_kb, peak_hour or 0, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        if dates_to_process:
            logger.info(f"Generated daily summaries for {len(dates_to_process)} dates")
    
    def export_cost_report(self, output_path: str, days_back: int = 30):
        """Export detailed cost report to JSON."""
        summary = self.get_cost_summary(days_back)
        
        # Add metadata
        summary["report_generated"] = datetime.now().isoformat()
        summary["report_type"] = "api_cost_analysis"
        
        with open(output_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Cost report exported to {output_path}")
    
    def _save_api_call(self, api_call: APICall):
        """Save API call to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO api_calls 
            (service, endpoint, timestamp, cost_usd, success, response_size_kb, 
             request_type, metadata, date_only)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            api_call.service,
            api_call.endpoint,
            api_call.timestamp.isoformat(),
            api_call.cost_usd,
            api_call.success,
            api_call.response_size_kb,
            api_call.request_type,
            json.dumps(api_call.metadata),
            api_call.timestamp.date().isoformat()
        ))
        
        conn.commit()
        conn.close()


# Singleton instance for global access
_cost_tracker_instance = None

def get_cost_tracker() -> APICostTracker:
    """Get singleton instance of API cost tracker."""
    global _cost_tracker_instance
    if _cost_tracker_instance is None:
        _cost_tracker_instance = APICostTracker()
    return _cost_tracker_instance


def log_api_call(service: str, endpoint: str, success: bool = True, **kwargs) -> float:
    """Convenience function to log API call."""
    return get_cost_tracker().log_api_call(service, endpoint, success, **kwargs)


def can_afford_api_call(service: str) -> Tuple[bool, str]:
    """Convenience function to check if we can afford an API call."""
    return get_cost_tracker().can_afford_call(service)


if __name__ == "__main__":
    # Demo usage
    logging.basicConfig(level=logging.INFO)
    
    print("💰 API Cost Tracker Demo")
    print("=" * 40)
    
    # Initialize tracker
    tracker = APICostTracker()
    
    # Simulate some API calls
    print("📞 Simulating API calls...")
    tracker.log_api_call("the_odds_api", "/odds/nba", True, response_size_kb=15)
    tracker.log_api_call("api_football", "/games", True, response_size_kb=25)
    tracker.log_api_call("xai_grok", "/generate", True, response_size_kb=5)
    tracker.log_api_call("the_odds_api", "/odds/nfl", False, response_size_kb=0)
    
    # Check costs
    print("\n💸 Today's costs:")
    costs = tracker.get_todays_costs()
    for service, cost in costs.items():
        print(f"  • {service}: ${cost:.4f}")
    
    # Check if we can afford more calls
    print("\n✅ Can afford more calls?")
    for service in ["the_odds_api", "xai_grok"]:
        can_afford, reason = tracker.can_afford_call(service)
        print(f"  • {service}: {'✅' if can_afford else '❌'} - {reason}")
    
    # Check feedback loop cost
    print("\n🔄 Feedback loop analysis:")
    cost_estimate = tracker.estimate_feedback_loop_cost(100)
    should_run, reason = tracker.should_run_feedback_loop(cost_estimate)
    print(f"  • Estimated cost: ${cost_estimate:.3f}")
    print(f"  • Should run: {'✅' if should_run else '❌'} - {reason}")
    
    # Generate summary
    print("\n📊 Weekly summary:")
    summary = tracker.get_cost_summary(7)
    print(f"  • Total cost: ${summary['total_cost_usd']:.2f}")
    print(f"  • Total calls: {summary['total_calls']}")
    print(f"  • Avg cost/day: ${summary['avg_cost_per_day']:.2f}")
    
    print("\n✅ Demo completed!")
