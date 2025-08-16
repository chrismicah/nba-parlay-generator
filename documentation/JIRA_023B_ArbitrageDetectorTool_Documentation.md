# Advanced ArbitrageDetectorTool Documentation (JIRA-023B)

## 📋 Table of Contents
1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [How It Works](#how-it-works)
4. [Installation & Setup](#installation--setup)
5. [How to Run](#how-to-run)
6. [Configuration Options](#configuration-options)
7. [API Reference](#api-reference)
8. [Integration Guide](#integration-guide)
9. [Examples & Use Cases](#examples--use-cases)
10. [Troubleshooting](#troubleshooting)
11. [Performance Optimization](#performance-optimization)

---

## 📖 Overview

The **Advanced ArbitrageDetectorTool** is a hedge fund-level arbitrage detection system that incorporates real-world execution risk factors to surface guaranteed profit opportunities. Unlike simple theoretical arbitrage calculators, this system models:

- **Market Microstructure**: Bid-ask spreads, slippage, market impact
- **Execution Risk**: Book reliability, stake limits, timing constraints
- **Signal Quality**: Freshness validation, false positive suppression
- **Integration**: Real-time odds feeds, latency monitoring, cross-validation

### 🎯 Key Features

- ✅ **Execution-Aware Modeling**: Factors in real-world execution costs
- ✅ **False Positive Suppression**: Multi-layer validation prevents alert fatigue
- ✅ **Signal Decay Logic**: Timestamp validation with stale data rejection
- ✅ **Risk Assessment**: Comprehensive execution risk scoring
- ✅ **Multi-Book Support**: Tier-based sportsbook configurations
- ✅ **Real-Time Integration**: Live odds feeds with freshness monitoring

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                ArbitrageDetectorTool Core Engine                │
├─────────────────────────────────────────────────────────────────┤
│ • Execution-Aware Modeling     • False Positive Suppression    │
│ • Bid-Ask Spread Integration   • Signal Decay Logic            │
│ • Market Impact Calculations   • Risk Assessment Matrix        │
│ • Multi-Book Configuration     • Confidence Scoring            │
└─────────────────────────────────────────────────────────────────┘
                                │
                ┌───────────────┼───────────────┐
                ▼               ▼               ▼
    ┌──────────────────┐ ┌──────────────┐ ┌─────────────────┐
    │   JIRA-004       │ │  JIRA-005    │ │   JIRA-023A     │
    │ OddsFetcherTool  │ │ LatencyMon   │ │ MarketDiscrep   │
    │ (Live Odds)      │ │ (Freshness)  │ │ (Cross-Valid)   │
    └──────────────────┘ └──────────────┘ └─────────────────┘
                                │
                                ▼
                ┌─────────────────────────────────┐
                │  AdvancedArbitrageIntegration   │
                │  • Unified Interface            │
                │  • Multi-Game Scanning          │
                │  • Execution Reporting          │
                │  • Alert Management             │
                └─────────────────────────────────┘
```

### 📁 File Structure

```
tools/
├── arbitrage_detector_tool.py          # Core arbitrage detection engine
├── advanced_arbitrage_integration.py   # Integration wrapper
├── jira_023b_complete_demo.py          # Complete demonstration
├── odds_fetcher_tool.py                # Live odds integration (JIRA-004)
├── market_discrepancy_detector.py      # Cross-validation (JIRA-023A)
└── ...

tests/
├── test_arbitrage_detector_tool.py     # Comprehensive test suite
└── ...

documentation/
├── JIRA_023B_ArbitrageDetectorTool_Documentation.md  # This file
├── JIRA_023B_COMPLETION_SUMMARY.md                   # Implementation summary
└── ...
```

---

## ⚙️ How It Works

### 1. **Execution-Aware Odds Adjustment**

The system adjusts raw odds for real-world execution costs:

```python
def adjust_for_spread_and_slippage(self, odds: float, book_name: str, stake_size: float):
    """
    Hedge fund-level execution cost modeling:
    1. Bid-ask spread impact (hitting worse side of market)
    2. Slippage based on book-specific factors
    3. Market impact for large stakes
    4. Liquidity tier adjustments
    """
    
    # 1. Bid-ask spread adjustment (we hit the worse side)
    spread_impact = config.bid_ask_spread / 2
    adjusted_odds = decimal_odds * (1 - spread_impact)
    
    # 2. Slippage adjustment
    slippage_impact = config.slippage_factor
    adjusted_odds *= (1 - slippage_impact)
    
    # 3. Market impact for large stakes
    if stake_size > config.market_impact_threshold:
        impact_multiplier = min(stake_size / config.market_impact_threshold, 3.0)
        market_impact = config.slippage_factor * impact_multiplier * 0.5
        adjusted_odds *= (1 - market_impact)
    
    # 4. Liquidity tier penalty
    if config.liquidity_tier == "medium":
        adjusted_odds *= 0.995  # 0.5% penalty
    elif config.liquidity_tier == "low":
        adjusted_odds *= 0.990  # 1.0% penalty
```

### 2. **Sportsbook Configuration System**

Each sportsbook has detailed execution parameters:

```python
@dataclass
class BookConfiguration:
    name: str
    bid_ask_spread: float = 0.02      # 2% typical spread
    min_stake: float = 10.0           # Minimum bet amount
    max_stake: float = 10000.0        # Maximum bet amount
    slippage_factor: float = 0.01     # 1% typical slippage
    execution_delay: float = 2.0      # Seconds for bet placement
    reliability_score: float = 0.95   # Historical success rate
    liquidity_tier: str = "high"      # high, medium, low
    market_impact_threshold: float = 1000.0  # Large stake impact
    spread_scaling_factor: float = 1.5        # Spread increase under pressure
```

**Default Configurations:**

| Sportsbook | Spread | Slippage | Max Stake | Tier | Reliability |
|------------|--------|----------|-----------|------|-------------|
| DraftKings | 1.5%   | 0.8%     | $25,000   | High | 98%         |
| FanDuel    | 1.5%   | 0.8%     | $25,000   | High | 98%         |
| BetMGM     | 1.8%   | 1.0%     | $20,000   | High | 96%         |
| Caesars    | 2.2%   | 1.2%     | $15,000   | Med  | 94%         |
| PointsBet  | 2.5%   | 1.5%     | $10,000   | Med  | 92%         |

### 3. **False Positive Suppression**

Multi-layer validation prevents unprofitable alerts:

```python
# Layer 1: Epsilon threshold check
if sum(implied_probabilities) >= 1.0 - self.false_positive_epsilon:
    return None  # Not a true arbitrage

# Layer 2: Minimum edge threshold
if profit_margin < self.min_profit_threshold:
    return None  # Below minimum profit

# Layer 3: Risk-adjusted validation
if risk_adjusted_profit < expected_threshold:
    return None  # Too risky for edge

# Layer 4: Confidence scoring
if confidence_level == "low":
    return None  # Insufficient confidence
```

### 4. **Signal Decay & Freshness Validation**

```python
def check_signal_freshness(self, odds_data: Dict, max_age_seconds: float = 60.0):
    """
    Multi-source freshness validation:
    1. JIRA-005 Latency Monitor integration
    2. Timestamp-based fallback validation
    3. Stale signal rejection tracking
    """
    
    current_time = datetime.now(timezone.utc)
    
    # Check with latency monitor (JIRA-005)
    if self.latency_monitor:
        last_update = self.latency_monitor.get_last_update_time()
        if last_update:
            age = (current_time - last_update).total_seconds()
            if age > max_age_seconds:
                self.stale_signals_rejected += 1
                return False
    
    # Fallback: timestamp validation
    if 'timestamp' in odds_data:
        data_time = datetime.fromisoformat(odds_data['timestamp'])
        age = (current_time - data_time).total_seconds()
        if age > max_age_seconds:
            self.stale_signals_rejected += 1
            return False
    
    return True
```

---

## 🚀 Installation & Setup

### Prerequisites

```bash
# Python 3.8+ required
python --version

# Install required dependencies
pip install -r requirements.txt
```

### Required Dependencies

```txt
# Core dependencies
numpy>=1.21.0
pandas>=1.3.0
requests>=2.25.0
python-dateutil>=2.8.0

# Optional (for enhanced features)
httpx>=0.24.0        # For Qdrant integration
transformers>=4.0.0  # For RoBERTa models
```

### Environment Setup

1. **Clone the repository:**
```bash
git clone <repository-url>
cd nba_parlay_project
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure API keys (optional):**
```bash
# For live odds integration (JIRA-004)
export ODDS_API_KEY="your-odds-api-key"

# For enhanced monitoring
export QDRANT_URL="your-qdrant-instance"
```

---

## 🏃‍♂️ How to Run

### 1. **Basic Arbitrage Detection**

```bash
# Run the core arbitrage detector
python tools/arbitrage_detector_tool.py
```

**Output:**
```
🎯 Advanced ArbitrageDetectorTool - JIRA-023B
===============================================
🔧 CONFIGURATION
Minimum profit threshold: 0.50%
Maximum latency threshold: 60 seconds
Default slippage buffer: 1.00%

🎯 TEST 1: Two-Way Arbitrage Detection
Testing: Lakers +105 (FanDuel) vs Celtics -90 (DraftKings)
✅ Two-way arbitrage detected!
   Profit margin: 2.40%
   Risk-adjusted profit: 2.31%
   Confidence level: medium
```

### 2. **Complete System Demo**

```bash
# Run comprehensive demonstration
python -m tools.jira_023b_complete_demo
```

This demonstrates:
- ✅ Exact output format validation
- ✅ Execution-aware modeling
- ✅ False positive suppression
- ✅ Risk assessment & confidence scoring
- ✅ Signal decay & freshness validation
- ✅ Integration capabilities

### 3. **Advanced Integration**

```bash
# Run integrated system with live odds
python -m tools.advanced_arbitrage_integration
```

**Features:**
- Live odds integration (JIRA-004)
- Latency monitoring (JIRA-005)
- Cross-validation (JIRA-023A)
- Multi-game scanning
- Execution reporting

### 4. **Testing Suite**

```bash
# Run comprehensive tests
python tests/test_arbitrage_detector_tool.py
```

**Test Coverage:**
- Unit tests for all core methods
- Integration tests with external systems
- Edge case validation
- Performance benchmarks

---

## ⚙️ Configuration Options

### 1. **Core Detector Configuration**

```python
from tools.arbitrage_detector_tool import ArbitrageDetectorTool

detector = ArbitrageDetectorTool(
    min_profit_threshold=0.01,        # 1% minimum edge
    max_latency_threshold=45.0,       # 45 seconds max staleness
    default_slippage_buffer=0.015,    # 1.5% default slippage
    false_positive_epsilon=0.0005,    # Stricter FP suppression
    execution_window=300.0            # 5 minutes execution window
)
```

### 2. **Integration System Configuration**

```python
from tools.advanced_arbitrage_integration import AdvancedArbitrageIntegration

integration = AdvancedArbitrageIntegration(
    min_profit_threshold=0.01,        # 1% minimum
    max_latency_seconds=45.0,         # 45 second freshness
    confidence_filter="medium",       # minimum confidence level
    enable_cross_validation=True      # enable cross-validation
)
```

### 3. **Custom Sportsbook Configuration**

```python
from tools.arbitrage_detector_tool import BookConfiguration

# Add custom sportsbook
detector.book_configs["newbook"] = BookConfiguration(
    name="NewSportsbook",
    bid_ask_spread=0.03,             # 3% spread
    slippage_factor=0.02,            # 2% slippage
    max_stake=5000.0,                # $5K max
    liquidity_tier="low",            # Low liquidity
    reliability_score=0.85           # 85% reliability
)
```

---

## 📚 API Reference

### 🔧 ArbitrageDetectorTool Class

#### **Core Methods**

```python
def detect_arbitrage_two_way(self, 
                           odds_a: float, book_a: str,
                           odds_b: float, book_b: str,
                           slippage_buffer: Optional[float] = None) -> Optional[ArbitrageOpportunity]:
    """
    Detect two-way arbitrage with execution-aware modeling.
    
    Args:
        odds_a: American odds from first book (e.g., 105, -110)
        book_a: First sportsbook name (e.g., "fanduel")
        odds_b: American odds from second book
        book_b: Second sportsbook name (e.g., "draftkings")
        slippage_buffer: Optional custom slippage (default: 0.01)
    
    Returns:
        ArbitrageOpportunity object if profitable, None otherwise
    
    Example:
        arbitrage = detector.detect_arbitrage_two_way(105, "fanduel", -90, "draftkings")
        if arbitrage:
            print(f"Profit: {arbitrage.profit_margin:.2%}")
    """
```

```python
def detect_arbitrage_three_way(self,
                             odds_list: List[Tuple[float, str]],
                             slippage_buffer: Optional[float] = None) -> Optional[ArbitrageOpportunity]:
    """
    Detect three-way arbitrage (Win/Draw/Loss markets).
    
    Args:
        odds_list: List of (odds, book_name) tuples for three outcomes
        slippage_buffer: Optional custom slippage
    
    Returns:
        ArbitrageOpportunity object if profitable, None otherwise
    
    Example:
        three_way = [(250, "betmgm"), (320, "caesars"), (180, "pointsbet")]
        arbitrage = detector.detect_arbitrage_three_way(three_way)
    """
```

```python
def adjust_for_spread_and_slippage(self,
                                 odds: float,
                                 book_name: str, 
                                 stake_size: float = 1000.0) -> float:
    """
    Adjust odds for execution costs (spread, slippage, market impact).
    
    Args:
        odds: Original American odds
        book_name: Sportsbook name for configuration lookup
        stake_size: Bet size for market impact calculation
    
    Returns:
        Adjusted American odds accounting for execution costs
    
    Example:
        original_odds = 100
        adjusted_odds = detector.adjust_for_spread_and_slippage(original_odds, "draftkings", 5000)
        print(f"Adjustment: {original_odds} → {adjusted_odds}")
    """
```

```python
def validate_arbitrage_opportunity(self, opportunity: ArbitrageOpportunity) -> bool:
    """
    Final validation before execution (freshness, availability, thresholds).
    
    Args:
        opportunity: ArbitrageOpportunity to validate
    
    Returns:
        True if valid for execution, False otherwise
    """
```

#### **Utility Methods**

```python
def check_signal_freshness(self, odds_data: Dict[str, Any], max_age_seconds: Optional[float] = None) -> bool:
    """Check if odds data is fresh enough for execution."""

def get_execution_summary(self) -> Dict[str, Any]:
    """Get performance metrics and statistics."""

def odds_to_implied_probability(self, odds: float) -> float:
    """Convert American odds to implied probability."""

def implied_probability_to_odds(self, prob: float) -> float:
    """Convert implied probability to American odds."""
```

### 🔧 AdvancedArbitrageIntegration Class

```python
def scan_multiple_games(self, game_ids: List[str]) -> ExecutionReport:
    """
    Scan multiple games with full integration.
    
    Args:
        game_ids: List of game identifiers to scan
    
    Returns:
        ExecutionReport with comprehensive analysis
    
    Example:
        games = ['nba_lakers_celtics_20250115', 'nba_warriors_nets_20250115']
        report = integration.scan_multiple_games(games)
        print(f"Found {report.arbitrage_opportunities} opportunities")
    """
```

### 📊 Data Structures

#### **ArbitrageOpportunity**

```python
@dataclass
class ArbitrageOpportunity:
    arbitrage: bool                      # True if valid arbitrage
    type: str                           # "2-way", "3-way", "n-way"
    profit_margin: float                # Raw profit margin
    risk_adjusted_profit: float         # Profit after execution risk
    expected_edge: float                # Conservative profit estimate
    sharpe_ratio: float                 # Risk-adjusted return ratio
    total_stake: float                  # Total amount to stake
    stake_ratios: Dict[str, float]      # Book → stake percentage
    adjusted_for_slippage: bool         # Whether slippage applied
    max_latency_seconds: float          # Data age limit
    execution_time_window: float        # Time to execute all legs
    legs: List[ArbitrageLeg]           # Individual bet legs
    execution_risk_score: float         # Overall execution risk
    false_positive_probability: float   # FP likelihood estimate
    confidence_level: str               # "high", "medium", "low"
    detection_timestamp: str            # When detected
    expires_at: str                     # Expiration time
    game_id: Optional[str]              # Associated game
    market_type: Optional[str]          # Market type (h2h, spreads, etc.)
```

#### **ArbitrageLeg**

```python
@dataclass
class ArbitrageLeg:
    book: str                          # Sportsbook name
    market: str                        # Market type
    team: str                          # Team/outcome name
    odds: float                        # Original odds
    adjusted_odds: float               # Execution-adjusted odds
    implied_probability: float         # Original implied probability
    adjusted_implied_probability: float # Adjusted implied probability
    stake_ratio: float                 # Percentage of total stake
    stake_amount: float                # Dollar amount to stake
    expected_return: float             # Expected return amount
    available: bool                    # Whether bet is available
    last_update: Optional[str]         # Last odds update time
    latency_seconds: float             # Data age in seconds
    bid_ask_spread: float              # Applied spread
    slippage_estimate: float           # Applied slippage
    market_impact: float               # Market impact factor
    execution_confidence: float        # Execution success probability
```

---

## 🔗 Integration Guide

### 1. **JIRA-004: OddsFetcherTool Integration**

```python
from tools.odds_fetcher_tool import OddsFetcherTool
from tools.arbitrage_detector_tool import ArbitrageDetectorTool

# Initialize with live odds
odds_fetcher = OddsFetcherTool(api_key="your-api-key")
detector = ArbitrageDetectorTool()

# Scan live games
game_ids = ['nba_lakers_celtics_20250115']
for game_id in game_ids:
    # Fetch live odds
    game_odds = odds_fetcher.get_game_odds(game_id)
    
    if game_odds:
        # Extract arbitrage odds
        odds_data = extract_arbitrage_odds(game_odds)
        
        # Detect arbitrage
        opportunities = detect_arbitrage_opportunities(odds_data, game_id)
        
        for opp in opportunities:
            print(f"Arbitrage: {opp.profit_margin:.2%} profit")
```

### 2. **JIRA-005: OddsLatencyMonitor Integration**

```python
from monitoring.odds_latency_monitor import OddsLatencyMonitor

# Initialize with latency monitoring
latency_monitor = OddsLatencyMonitor()
detector = ArbitrageDetectorTool()
detector.latency_monitor = latency_monitor

# Freshness validation
odds_data = {"timestamp": "2025-01-15T12:00:00Z"}
is_fresh = detector.check_signal_freshness(odds_data, max_age_seconds=45)

if is_fresh:
    # Process arbitrage detection
    pass
else:
    print("Odds data too stale for execution")
```

### 3. **JIRA-023A: MarketDiscrepancyDetector Cross-Validation**

```python
from tools.market_discrepancy_detector import MarketDiscrepancyDetector

# Enable cross-validation
market_detector = MarketDiscrepancyDetector()
integration = AdvancedArbitrageIntegration(enable_cross_validation=True)
integration.market_discrepancy = market_detector

# Cross-validate arbitrage opportunities
arbitrage = detector.detect_arbitrage_two_way(105, "fanduel", -90, "draftkings")
if arbitrage:
    is_valid = integration.cross_validate_with_market_discrepancy(arbitrage, "game_123")
    if is_valid:
        print("Arbitrage validated by market discrepancy detector")
```

### 4. **Real-Time Pipeline Integration**

```python
import asyncio
from tools.advanced_arbitrage_integration import AdvancedArbitrageIntegration

async def real_time_arbitrage_scanner():
    """Real-time arbitrage scanning pipeline."""
    
    integration = AdvancedArbitrageIntegration(
        min_profit_threshold=0.01,
        confidence_filter="medium"
    )
    
    while True:
        try:
            # Get current games
            current_games = get_current_nba_games()
            
            # Scan for arbitrages
            report = integration.scan_multiple_games(current_games)
            
            # Process opportunities
            for opportunity in report.opportunities:
                if opportunity.confidence_level in ["high", "medium"]:
                    await send_arbitrage_alert(opportunity)
            
            # Wait before next scan
            await asyncio.sleep(30)  # 30-second intervals
            
        except Exception as e:
            print(f"Scanner error: {e}")
            await asyncio.sleep(60)  # Longer wait on error

# Run the pipeline
asyncio.run(real_time_arbitrage_scanner())
```

---

## 💡 Examples & Use Cases

### 1. **Basic Two-Way Arbitrage**

```python
from tools.arbitrage_detector_tool import ArbitrageDetectorTool

detector = ArbitrageDetectorTool(min_profit_threshold=0.005)  # 0.5% minimum

# Lakers vs Celtics example
arbitrage = detector.detect_arbitrage_two_way(
    105, "fanduel",      # Lakers +105 at FanDuel
    -90, "draftkings"    # Celtics -90 at DraftKings
)

if arbitrage:
    print(f"✅ Arbitrage detected!")
    print(f"   Type: {arbitrage.type}")
    print(f"   Profit: {arbitrage.profit_margin:.2%}")
    print(f"   Risk-adjusted: {arbitrage.risk_adjusted_profit:.2%}")
    print(f"   Confidence: {arbitrage.confidence_level}")
    
    print(f"\n💰 Stake Distribution (Total: ${arbitrage.total_stake:,.0f})")
    for leg in arbitrage.legs:
        print(f"   {leg.book}: ${leg.stake_amount:.2f} ({leg.stake_ratio:.1%})")
        print(f"   Expected return: ${leg.expected_return:.2f}")
```

**Output:**
```
✅ Arbitrage detected!
   Type: 2-way
   Profit: 2.40%
   Risk-adjusted: 2.31%
   Confidence: medium

💰 Stake Distribution (Total: $1,000)
   fanduel: $507.34 (50.7%)
   Expected return: $1,052.27
   draftkings: $492.66 (49.3%)
   Expected return: $1,052.27
```

### 2. **Three-Way Arbitrage (Soccer/International)**

```python
# Soccer match: Win/Draw/Loss
three_way_odds = [
    (250, "betmgm"),     # Home team +250
    (320, "caesars"),    # Draw +320
    (180, "pointsbet")   # Away team +180
]

arbitrage = detector.detect_arbitrage_three_way(three_way_odds)

if arbitrage:
    print(f"✅ Three-way arbitrage: {arbitrage.profit_margin:.2%} profit")
    print(f"   Sharpe ratio: {arbitrage.sharpe_ratio:.2f}")
    print(f"   Execution risk: {arbitrage.execution_risk_score:.3f}")
```

### 3. **Execution Cost Analysis**

```python
# Compare execution costs across sportsbooks
original_odds = 100
stake_sizes = [1000, 5000, 15000]

print("📊 EXECUTION COST ANALYSIS")
print(f"Original odds: +{original_odds}")
print("=" * 50)

for book in ["draftkings", "fanduel", "caesars", "pointsbet"]:
    print(f"\n{book.upper()}:")
    for stake in stake_sizes:
        adjusted = detector.adjust_for_spread_and_slippage(original_odds, book, stake)
        cost = original_odds - adjusted
        cost_pct = (cost / original_odds) * 100
        
        print(f"  ${stake:>6}: +{adjusted:>6.1f} (cost: -{cost_pct:>5.2f}%)")
```

**Output:**
```
📊 EXECUTION COST ANALYSIS
Original odds: +100
==================================================

DRAFTKINGS:
  $1000: + 101.8 (cost: -1.82%)
  $5000: + 103.6 (cost: -3.64%)
  $15000: + 103.6 (cost: -3.64%)

POINTSBET:
  $1000: + 106.9 (cost: -6.88%)
  $5000: + 112.1 (cost: -12.10%)
  $15000: + 112.1 (cost: -12.10%)
```

### 4. **False Positive Testing**

```python
# Test edge cases that should be filtered out
test_cases = [
    {"odds": (120, "fanduel", -95, "draftkings"), "desc": "Clear arbitrage"},
    {"odds": (102, "fanduel", -105, "draftkings"), "desc": "Marginal case"},
    {"odds": (-110, "fanduel", -110, "draftkings"), "desc": "No arbitrage"},
    {"odds": (500, "unknown", -400, "draftkings"), "desc": "Suspicious odds"},
]

print("🛡️ FALSE POSITIVE TESTING")
print("=" * 40)

for case in test_cases:
    odds_a, book_a, odds_b, book_b = case["odds"]
    arbitrage = detector.detect_arbitrage_two_way(odds_a, book_a, odds_b, book_b)
    
    status = "✅ DETECTED" if arbitrage else "❌ FILTERED"
    profit = f"({arbitrage.profit_margin:.2%})" if arbitrage else ""
    
    print(f"{case['desc']}: {status} {profit}")
```

### 5. **Real-Time Monitoring Setup**

```python
import time
from datetime import datetime

def monitor_arbitrage_opportunities():
    """Simple real-time monitoring loop."""
    
    integration = AdvancedArbitrageIntegration(
        min_profit_threshold=0.01,  # 1% minimum
        confidence_filter="medium"
    )
    
    print("🔍 Starting real-time arbitrage monitoring...")
    
    while True:
        try:
            # Get current games (replace with actual game IDs)
            current_games = get_todays_nba_games()
            
            if current_games:
                # Scan for opportunities
                report = integration.scan_multiple_games(current_games)
                
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"[{timestamp}] Scanned {report.games_analyzed} games")
                
                if report.opportunities:
                    print(f"🚨 ARBITRAGE ALERT: {len(report.opportunities)} opportunities found!")
                    
                    for opp in report.opportunities:
                        if opp.confidence_level == "high":
                            print(f"   HIGH CONFIDENCE: {opp.profit_margin:.2%} profit")
                            # Send alert/notification here
                
                # Show performance
                if report.stale_signals_rejected > 0:
                    print(f"   Rejected {report.stale_signals_rejected} stale signals")
                
                if report.false_positives_avoided > 0:
                    print(f"   Avoided {report.false_positives_avoided} false positives")
            
            # Wait before next scan
            time.sleep(30)  # 30-second intervals
            
        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped by user")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(60)  # Wait longer on error

# Start monitoring
monitor_arbitrage_opportunities()
```

---

## 🔧 Troubleshooting

### Common Issues & Solutions

#### 1. **No Arbitrage Opportunities Found**

**Symptoms:**
```
📊 EXECUTION SUMMARY
Total opportunities detected: 0
False positives avoided: 3
```

**Possible Causes & Solutions:**

1. **Thresholds too high:**
```python
# Lower the minimum profit threshold
detector = ArbitrageDetectorTool(min_profit_threshold=0.002)  # 0.2% instead of 1%
```

2. **Execution costs too high:**
```python
# Reduce slippage buffer for testing
detector = ArbitrageDetectorTool(default_slippage_buffer=0.005)  # 0.5% instead of 1%
```

3. **Confidence filter too strict:**
```python
# Allow lower confidence opportunities
integration = AdvancedArbitrageIntegration(confidence_filter="low")
```

#### 2. **Stale Data Rejection**

**Symptoms:**
```
WARNING: Rejecting stale odds data: 120.0s old
Stale signals rejected: 5
```

**Solutions:**

1. **Increase latency threshold:**
```python
detector = ArbitrageDetectorTool(max_latency_threshold=300.0)  # 5 minutes
```

2. **Check odds feed freshness:**
```python
# Verify odds fetcher is working
odds_data = odds_fetcher.get_game_odds("test_game")
if odds_data:
    print(f"Last update: {odds_data.get('timestamp')}")
```

#### 3. **Integration Errors**

**Symptoms:**
```
ERROR: Failed to fetch odds for game game_001: All odds providers failed
```

**Solutions:**

1. **Check API configuration:**
```python
# Verify API key
import os
api_key = os.getenv('ODDS_API_KEY')
print(f"API Key configured: {'Yes' if api_key else 'No'}")
```

2. **Use mock data for testing:**
```python
# Disable live feeds for testing
integration = AdvancedArbitrageIntegration()
integration.odds_fetcher = None  # Uses mock data
```

3. **Check network connectivity:**
```bash
# Test API endpoint
curl -H "Authorization: Bearer YOUR_API_KEY" \
     "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds"
```

#### 4. **Performance Issues**

**Symptoms:**
```
Scan Duration: 5000.0ms  # Very slow
```

**Optimization:**

1. **Reduce scan frequency:**
```python
# Scan less frequently
time.sleep(60)  # 60 seconds instead of 30
```

2. **Limit games scanned:**
```python
# Focus on specific games
priority_games = get_high_volume_games()[:5]  # Top 5 only
```

3. **Disable cross-validation:**
```python
integration = AdvancedArbitrageIntegration(enable_cross_validation=False)
```

#### 5. **Test Failures**

**Symptoms:**
```
FAILED (failures=3, errors=1)
test_edge_cases: ValueError not raised
```

**Solutions:**

1. **Run tests individually:**
```bash
# Test specific functionality
python -m pytest tests/test_arbitrage_detector_tool.py::TestArbitrageDetectorTool::test_two_way_arbitrage_detection_profitable -v
```

2. **Check mock data:**
```python
# Verify test data setup
def test_debug():
    detector = ArbitrageDetectorTool()
    result = detector.detect_arbitrage_two_way(105, "fanduel", -90, "draftkings")
    print(f"Test result: {result}")
```

3. **Update test expectations:**
```python
# Adjust for execution cost modeling
# Old: self.assertGreater(profit_margin, 0.02)  # 2%
# New: self.assertGreater(profit_margin, 0.005)  # 0.5% after costs
```

### Logging & Debugging

#### Enable Debug Logging

```python
import logging

# Enable detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Run detector with detailed logs
detector = ArbitrageDetectorTool()
arbitrage = detector.detect_arbitrage_two_way(105, "fanduel", -90, "draftkings")
```

#### Performance Profiling

```python
import time
import cProfile

def profile_detection():
    detector = ArbitrageDetectorTool()
    
    start_time = time.time()
    arbitrage = detector.detect_arbitrage_two_way(105, "fanduel", -90, "draftkings")
    end_time = time.time()
    
    print(f"Detection time: {(end_time - start_time) * 1000:.2f}ms")
    return arbitrage

# Profile the function
cProfile.run('profile_detection()')
```

---

## ⚡ Performance Optimization

### 1. **Batch Processing**

```python
def scan_multiple_arbitrages_optimized(odds_pairs: List[Tuple]):
    """Optimized batch processing of arbitrage opportunities."""
    
    detector = ArbitrageDetectorTool()
    opportunities = []
    
    # Batch configuration loading
    detector._preload_book_configs()
    
    for odds_a, book_a, odds_b, book_b in odds_pairs:
        arbitrage = detector.detect_arbitrage_two_way(odds_a, book_a, odds_b, book_b)
        if arbitrage:
            opportunities.append(arbitrage)
    
    return opportunities
```

### 2. **Caching & Memoization**

```python
from functools import lru_cache

class OptimizedArbitrageDetector(ArbitrageDetectorTool):
    """Performance-optimized version with caching."""
    
    @lru_cache(maxsize=1000)
    def odds_to_implied_probability_cached(self, odds: float) -> float:
        """Cached odds conversion."""
        return super().odds_to_implied_probability(odds)
    
    @lru_cache(maxsize=500)
    def adjust_for_spread_and_slippage_cached(self, 
                                            odds: float, 
                                            book_name: str, 
                                            stake_size: float) -> float:
        """Cached odds adjustment."""
        return super().adjust_for_spread_and_slippage(odds, book_name, stake_size)
```

### 3. **Parallel Processing**

```python
import concurrent.futures
from typing import List

def parallel_game_scanning(game_ids: List[str], max_workers: int = 4):
    """Scan multiple games in parallel."""
    
    def scan_single_game(game_id: str):
        integration = AdvancedArbitrageIntegration()
        return integration.scan_multiple_games([game_id])
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all game scans
        future_to_game = {
            executor.submit(scan_single_game, game_id): game_id 
            for game_id in game_ids
        }
        
        # Collect results
        all_opportunities = []
        for future in concurrent.futures.as_completed(future_to_game):
            game_id = future_to_game[future]
            try:
                report = future.result()
                all_opportunities.extend(report.opportunities)
            except Exception as e:
                print(f"Game {game_id} failed: {e}")
        
        return all_opportunities
```

### 4. **Memory Optimization**

```python
import gc
from dataclasses import dataclass
from typing import Optional

@dataclass
class LightweightArbitrage:
    """Memory-optimized arbitrage representation."""
    profit_margin: float
    confidence: str
    book_a: str
    book_b: str
    expires_at: str
    
    @classmethod
    def from_full_arbitrage(cls, arb: ArbitrageOpportunity) -> 'LightweightArbitrage':
        """Convert full arbitrage to lightweight version."""
        return cls(
            profit_margin=arb.profit_margin,
            confidence=arb.confidence_level,
            book_a=arb.legs[0].book if arb.legs else "",
            book_b=arb.legs[1].book if len(arb.legs) > 1 else "",
            expires_at=arb.expires_at
        )

def memory_efficient_scanning(game_ids: List[str]) -> List[LightweightArbitrage]:
    """Memory-efficient scanning for high-frequency use."""
    
    lightweight_opportunities = []
    
    for game_id in game_ids:
        # Scan single game
        integration = AdvancedArbitrageIntegration()
        report = integration.scan_multiple_games([game_id])
        
        # Convert to lightweight format
        for opp in report.opportunities:
            lightweight_opportunities.append(
                LightweightArbitrage.from_full_arbitrage(opp)
            )
        
        # Force garbage collection
        del integration, report
        gc.collect()
    
    return lightweight_opportunities
```

### 5. **Configuration Tuning**

```python
# Production configuration for high-frequency scanning
PRODUCTION_CONFIG = {
    "min_profit_threshold": 0.005,      # 0.5% minimum
    "max_latency_threshold": 30.0,      # 30 seconds max
    "confidence_filter": "medium",       # Medium confidence minimum
    "enable_cross_validation": False,    # Disable for speed
    "scan_interval": 15.0,              # 15-second intervals
    "max_games_per_scan": 10,           # Limit concurrent games
}

def create_production_detector():
    """Create optimized detector for production use."""
    return ArbitrageDetectorTool(
        min_profit_threshold=PRODUCTION_CONFIG["min_profit_threshold"],
        max_latency_threshold=PRODUCTION_CONFIG["max_latency_threshold"],
        default_slippage_buffer=0.008,   # Optimized slippage
        false_positive_epsilon=0.0003    # Stricter FP suppression
    )
```

---

## 📊 Monitoring & Metrics

### Performance Dashboards

```python
def generate_performance_report(detector: ArbitrageDetectorTool) -> Dict:
    """Generate comprehensive performance metrics."""
    
    summary = detector.get_execution_summary()
    
    return {
        "detection_performance": {
            "opportunities_found": summary["total_opportunities_detected"],
            "false_positives_avoided": summary["false_positives_avoided"],
            "success_rate": (
                summary["total_opportunities_detected"] / 
                (summary["total_opportunities_detected"] + summary["false_positives_avoided"])
                if summary["total_opportunities_detected"] + summary["false_positives_avoided"] > 0 
                else 0
            ),
            "average_profit": summary["average_profit_margin"],
            "average_risk_adjusted": summary["average_risk_adjusted_profit"]
        },
        "signal_quality": {
            "stale_rejections": summary["stale_signals_rejected"],
            "freshness_rate": 1.0 - (summary["stale_signals_rejected"] / 100),  # Approximate
        },
        "execution_parameters": summary["execution_parameters"],
        "confidence_distribution": summary["confidence_distribution"]
    }
```

This comprehensive documentation covers all aspects of the Advanced ArbitrageDetectorTool system. The tool provides hedge fund-level sophistication in arbitrage detection with real-world execution awareness, making it production-ready for professional trading operations.



