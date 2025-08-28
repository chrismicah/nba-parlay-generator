# JIRA-024 Final Market Verification - Quick Reference

## 🚀 Quick Start

### Enable Final Verification
```python
from tools.market_discrepancy_monitor import MarketDiscrepancyMonitor, MonitoringConfig
from tools.final_market_verifier import VerificationConfig

# Configure verification thresholds
verification_config = VerificationConfig(
    max_american_odds_shift=5.0,       # ±5 points maximum shift
    max_implied_prob_shift=0.01,       # ±1% probability shift  
    require_all_markets_available=True  # All legs must be available
)

# Configure monitoring with verification enabled
monitoring_config = MonitoringConfig(
    enable_final_verification=True,
    verification_config=verification_config
)

# Create monitor - alerts will be automatically verified
monitor = MarketDiscrepancyMonitor(config=monitoring_config)
monitor.start_monitoring(['game_001', 'game_002'])
```

### Standalone Verification
```python
from tools.final_market_verifier import FinalMarketVerifier

verifier = FinalMarketVerifier()
report = verifier.verify_alert_before_dispatch(alert)

if report.should_dispatch_alert:
    print("✅ Alert verified - safe to send")
    # Send alert
else:
    print(f"❌ Alert cancelled: {report.cancellation_reason}")
    # Don't send alert
```

---

## ⚙️ Configuration Options

### Basic Configuration
```python
VerificationConfig(
    max_american_odds_shift=10.0,      # Max odds shift (American odds)
    max_implied_prob_shift=0.02,       # Max probability shift (decimal)
    max_shift_percentage=0.05,         # Max relative change (percentage)
    require_all_markets_available=True, # Require all legs available
    max_data_age_seconds=60.0          # Max stale data age
)
```

### Alert-Specific Rules
- **Critical alerts**: 50% stricter thresholds automatically applied
- **Arbitrage alerts**: 70% stricter thresholds + require all markets
- **Value alerts**: Standard thresholds

### Disable Verification
```python
MonitoringConfig(
    enable_final_verification=False  # Disable verification
)
```

---

## 📊 Monitoring Verification

### Check Verification Statistics
```python
monitor = MarketDiscrepancyMonitor(config=config)
stats = monitor.get_monitoring_stats()

print(f"Verification enabled: {stats['verification_enabled']}")
print(f"Alerts verified: {stats['alerts_verified']}")  
print(f"Alerts cancelled: {stats['alerts_cancelled_verification']}")
print(f"Success rate: {stats['verification_success_rate']:.1%}")
```

### Verification Report Details
```python
verifier = FinalMarketVerifier()
report = verifier.verify_alert_before_dispatch(alert)

print(f"Result: {report.verification_result.value}")
print(f"Should dispatch: {report.should_dispatch_alert}")
print(f"Max odds shift: {report.max_odds_shift}")
print(f"Unavailable markets: {len(report.unavailable_markets)}")
print(f"Duration: {report.verification_duration_ms:.1f}ms")
```

---

## 🚨 Common Scenarios

### Odds Shifted Too Much
```
❌ Alert cancelled: Odds shifted by +15.0 for Lakers at draftkings
```
**Solution**: Increase `max_american_odds_shift` threshold or investigate market volatility

### Market Unavailable  
```
❌ Alert cancelled: 2 of 3 markets unavailable
```
**Solution**: Set `require_all_markets_available=False` or check data freshness

### Stale Data
```
❌ Alert cancelled: Fresh odds data not available
```
**Solution**: Check OddsFetcher API status or increase `max_data_age_seconds`

### Verification Error
```
❌ Alert cancelled: Verification error: API timeout
```
**Solution**: Check network connectivity or increase `verification_timeout_seconds`

---

## 🎯 Recommended Thresholds

### Conservative (Production)
```python
VerificationConfig(
    max_american_odds_shift=5.0,       # Tight control
    max_implied_prob_shift=0.01,       # 1% max shift
    require_all_markets_available=True, # All legs required
    max_data_age_seconds=30.0          # Fresh data only
)
```

### Moderate (Testing)
```python
VerificationConfig(
    max_american_odds_shift=10.0,      # Some flexibility
    max_implied_prob_shift=0.02,       # 2% max shift
    require_all_markets_available=True, # All legs required
    max_data_age_seconds=60.0          # 1-minute tolerance
)
```

### Lenient (Development)
```python
VerificationConfig(
    max_american_odds_shift=15.0,      # High tolerance
    max_implied_prob_shift=0.03,       # 3% max shift
    require_all_markets_available=False, # Allow some missing
    max_data_age_seconds=120.0         # 2-minute tolerance
)
```

---

## 🔧 Troubleshooting

### Low Success Rate (<70%)
1. Check if thresholds are too strict
2. Verify OddsFetcher API reliability
3. Check market volatility during active hours
4. Review verification timeout settings

### High Cancellation Rate (>50%)  
1. Increase odds shift thresholds
2. Allow some markets to be unavailable
3. Check data freshness requirements
4. Review alert generation timing

### Slow Verification (>5 seconds)
1. Check OddsFetcher API performance
2. Reduce retry attempts
3. Verify network connectivity
4. Check verification timeout settings

### API Errors
1. Verify THE_ODDS_API_KEY is set
2. Check API rate limits
3. Verify network connectivity
4. Check OddsFetcher configuration

---

## 📈 Performance Tips

### Optimize Verification Speed
```python
VerificationConfig(
    verification_timeout_seconds=3.0,  # Shorter timeout
    max_retries=1,                     # Fewer retries
    max_data_age_seconds=30.0          # Fresh data requirement
)
```

### Reduce API Calls
- Verification caching is enabled by default (30-second TTL)
- Similar alerts within cache period won't trigger duplicate verification
- Cache automatically cleaned to prevent memory leaks

### Monitor Key Metrics
- **Verification Duration**: Should be <5 seconds average
- **Success Rate**: Should be >80% in normal conditions  
- **Cache Hit Rate**: Higher is better for performance
- **API Error Rate**: Should be <10%

---

## ❓ FAQ

**Q: Does verification slow down alerts?**  
A: Typical verification takes 1-3 seconds. Critical alerts prioritize speed with shorter timeouts.

**Q: What happens if verification fails?**  
A: Low/medium priority alerts are cancelled. Critical/high priority alerts may still be sent depending on configuration.

**Q: Can I verify alerts manually?**  
A: Yes, use `FinalMarketVerifier.verify_alert_before_dispatch(alert)` for manual verification.

**Q: How do I disable verification?**  
A: Set `enable_final_verification=False` in MonitoringConfig.

**Q: What data does verification use?**  
A: Fresh odds data from OddsFetcherTool, same as the main system.

**Q: Can verification work without OddsFetcher?**  
A: No, verification requires fresh odds data. Alerts will be cancelled if OddsFetcher is unavailable.

---

*For complete implementation details, see [JIRA_024_COMPLETION_SUMMARY.md](JIRA_024_COMPLETION_SUMMARY.md)*
