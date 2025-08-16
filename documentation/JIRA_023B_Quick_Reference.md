# JIRA-023B Quick Reference Guide

## 🚀 **Quick Start**

### Run Basic Demo
```bash
python tools/arbitrage_detector_tool.py
```

### Run Complete Demo
```bash
python -m tools.jira_023b_complete_demo
```

### Run Integration System
```bash
python -m tools.advanced_arbitrage_integration
```

### Run Tests
```bash
python tests/test_arbitrage_detector_tool.py
```

---

## 📋 **Basic Usage**

### 1. Simple Two-Way Arbitrage Detection
```python
from tools.arbitrage_detector_tool import ArbitrageDetectorTool

detector = ArbitrageDetectorTool(min_profit_threshold=0.005)  # 0.5% minimum

# Lakers vs Celtics example
arbitrage = detector.detect_arbitrage_two_way(
    105, "fanduel",      # Lakers +105 at FanDuel
    -90, "draftkings"    # Celtics -90 at DraftKings
)

if arbitrage:
    print(f"Profit: {arbitrage.profit_margin:.2%}")
    print(f"Risk-adjusted: {arbitrage.risk_adjusted_profit:.2%}")
    print(f"Confidence: {arbitrage.confidence_level}")
```

### 2. Three-Way Arbitrage Detection
```python
# Soccer/International markets: Win/Draw/Loss
three_way_odds = [
    (250, "betmgm"),     # Home +250
    (320, "caesars"),    # Draw +320
    (180, "pointsbet")   # Away +180
]

arbitrage = detector.detect_arbitrage_three_way(three_way_odds)
if arbitrage:
    print(f"Three-way profit: {arbitrage.profit_margin:.2%}")
```

### 3. Integration with Live Odds
```python
from tools.advanced_arbitrage_integration import AdvancedArbitrageIntegration

integration = AdvancedArbitrageIntegration(
    min_profit_threshold=0.01,
    confidence_filter="medium"
)

# Scan multiple games
game_ids = ['game_001', 'game_002', 'game_003']
report = integration.scan_multiple_games(game_ids)

print(f"Found {report.arbitrage_opportunities} opportunities")
for opp in report.opportunities:
    print(f"  {opp.profit_margin:.2%} profit ({opp.confidence_level})")
```

---

## ⚙️ **Configuration Options**

### Core Detector
```python
detector = ArbitrageDetectorTool(
    min_profit_threshold=0.01,        # 1% minimum edge
    max_latency_threshold=45.0,       # 45 seconds max staleness
    default_slippage_buffer=0.015,    # 1.5% default slippage
    false_positive_epsilon=0.0005,    # Stricter FP suppression
    execution_window=300.0            # 5 minutes execution window
)
```

### Integration System
```python
integration = AdvancedArbitrageIntegration(
    min_profit_threshold=0.01,        # 1% minimum
    max_latency_seconds=45.0,         # 45 second freshness
    confidence_filter="medium",       # minimum confidence level
    enable_cross_validation=True      # enable cross-validation
)
```

### Custom Sportsbook
```python
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

## 📊 **Output Format**

### Standard Arbitrage Response
```json
{
  "arbitrage": true,
  "type": "2-way",
  "profit_margin": 0.024,
  "stake_ratios": {
    "fanduel": 0.507,
    "draftkings": 0.493
  },
  "adjusted_for_slippage": true,
  "latency_seconds": 0.0,
  "legs": [
    {
      "book": "Fanduel",
      "market": "ML",
      "team": "Lakers",
      "odds": 105,
      "adjusted_odds": 101.83,
      "available": true
    }
  ]
}
```

---

## 🔧 **Key Methods**

| Method | Purpose | Example |
|--------|---------|---------|
| `detect_arbitrage_two_way()` | Find 2-way arbitrage | `detector.detect_arbitrage_two_way(105, "fanduel", -90, "draftkings")` |
| `detect_arbitrage_three_way()` | Find 3-way arbitrage | `detector.detect_arbitrage_three_way([(250, "betmgm"), (320, "caesars"), (180, "pointsbet")])` |
| `adjust_for_spread_and_slippage()` | Apply execution costs | `detector.adjust_for_spread_and_slippage(100, "draftkings", 5000)` |
| `validate_arbitrage_opportunity()` | Final validation | `detector.validate_arbitrage_opportunity(opportunity)` |
| `scan_multiple_games()` | Batch scanning | `integration.scan_multiple_games(['game_001', 'game_002'])` |

---

## 🎯 **Sportsbook Tiers**

### Tier 1 (High Liquidity)
| Book | Spread | Slippage | Max Stake | Reliability |
|------|--------|----------|-----------|-------------|
| DraftKings | 1.5% | 0.8% | $25,000 | 98% |
| FanDuel | 1.5% | 0.8% | $25,000 | 98% |
| BetMGM | 1.8% | 1.0% | $20,000 | 96% |

### Tier 2 (Medium Liquidity)
| Book | Spread | Slippage | Max Stake | Reliability |
|------|--------|----------|-----------|-------------|
| Caesars | 2.2% | 1.2% | $15,000 | 94% |
| PointsBet | 2.5% | 1.5% | $10,000 | 92% |

---

## 🚨 **Troubleshooting**

### No Opportunities Found
```python
# Lower thresholds
detector = ArbitrageDetectorTool(min_profit_threshold=0.002)  # 0.2%
```

### Stale Data Issues
```python
# Increase latency tolerance
detector = ArbitrageDetectorTool(max_latency_threshold=300.0)  # 5 minutes
```

### Integration Errors
```python
# Use mock data for testing
integration.odds_fetcher = None  # Enables mock mode
```

---

## 📈 **Performance Metrics**

### Expected Results
- **Detection Speed**: < 1000ms for 4 games
- **Profit Margins**: 0.5% - 10% after execution costs
- **False Positive Rate**: < 5% with proper configuration
- **Signal Freshness**: 30-60 second tolerance

### Monitoring
```python
# Get performance summary
summary = detector.get_execution_summary()
print(f"Opportunities: {summary['total_opportunities_detected']}")
print(f"False positives avoided: {summary['false_positives_avoided']}")
print(f"Average profit: {summary['average_profit_margin']:.2%}")
```

---

## 📚 **Full Documentation**
For complete documentation see: `documentation/JIRA_023B_ArbitrageDetectorTool_Documentation.md`


