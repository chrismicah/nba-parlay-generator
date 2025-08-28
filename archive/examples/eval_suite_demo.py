#!/usr/bin/env python3
"""
ML Model Evaluation Suite Demo - EVAL-DEMO-001

Comprehensive demonstration of the ML model evaluation framework including:
- Backtesting with financial metrics (ROI, Sharpe, drawdown)
- A/B testing with statistical significance
- Strategy comparison across baselines and ML models
- Performance visualization and analytics

This demo showcases the evaluation capabilities for sports betting ML models.
"""

import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from eval_ml_models import EvalConfig, EvalSuite, BacktestResult
import pandas as pd
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def demo_basic_functionality():
    """Demonstrate basic evaluation suite functionality."""
    print("🎯 ML Model Evaluation Suite - Basic Demo")
    print("=" * 50)
    
    # Initialize for NBA
    config = EvalConfig(
        sport="nba",
        initial_bankroll=10000.0,
        bet_size_strategy="fixed",
        fixed_bet_amount=100.0
    )
    
    eval_suite = EvalSuite(config)
    
    print(f"Sport: {config.sport.upper()}")
    print(f"Models loaded: {list(eval_suite.models.keys())}")
    print(f"Baselines available: {list(eval_suite.baselines.keys())}")
    print(f"Initial bankroll: ${config.initial_bankroll:,.0f}")
    print(f"Bet strategy: {config.bet_size_strategy}")
    
    return eval_suite

def demo_data_generation():
    """Demonstrate synthetic data generation."""
    print("\n📊 Historical Data Generation")
    print("-" * 30)
    
    config = EvalConfig(sport="nba")
    eval_suite = EvalSuite(config)
    
    # Load/generate historical data
    df = eval_suite.load_historical_data()
    
    print(f"Generated {len(df)} historical records")
    print(f"Date range: {df['date'].min().strftime('%Y-%m-%d')} to {df['date'].max().strftime('%Y-%m-%d')}")
    print(f"Average legs per parlay: {df['legs'].mean():.1f}")
    print(f"Average odds: {df['odds'].mean():.0f}")
    print(f"Win rate: {df['outcome'].mean():.1%}")
    print(f"Average expected value: {df['expected_value'].mean():.1%}")
    
    # Show sample data
    print("\nSample records:")
    sample = df[['date', 'legs', 'odds', 'outcome', 'expected_value']].head()
    for _, row in sample.iterrows():
        outcome_str = "✅ Win" if row['outcome'] else "❌ Loss"
        print(f"  {row['date'].strftime('%Y-%m-%d')}: {row['legs']} legs, "
              f"odds {row['odds']:.0f}, EV {row['expected_value']:+.1%} - {outcome_str}")
    
    return eval_suite

def demo_backtesting():
    """Demonstrate backtesting functionality."""
    print("\n🔬 Backtesting Demo")
    print("-" * 20)
    
    config = EvalConfig(
        sport="nba",
        bet_size_strategy="fixed",
        fixed_bet_amount=100.0,
        initial_bankroll=10000.0
    )
    
    eval_suite = EvalSuite(config)
    
    # Run backtests for all strategies
    print("Running backtests for all available strategies...")
    results = eval_suite.run_comprehensive_evaluation()
    
    print(f"\n📈 Backtest Results:")
    print("-" * 80)
    print(f"{'Strategy':<20} | {'ROI':<8} | {'Sharpe':<6} | {'Win Rate':<8} | {'Bets':<5} | {'Return':<10}")
    print("-" * 80)
    
    for strategy_name, result in results.items():
        strategy_display = strategy_name.replace('_', ' ').title()[:19]
        roi_str = f"{result.roi:.1%}"
        sharpe_str = f"{result.sharpe_ratio:.2f}"
        win_rate_str = f"{result.win_rate:.1%}"
        return_str = f"${result.total_return:,.0f}"
        
        print(f"{strategy_display:<20} | {roi_str:<8} | {sharpe_str:<6} | "
              f"{win_rate_str:<8} | {result.total_bets:<5} | {return_str:<10}")
    
    # Identify best strategy
    best_strategy = max(results.items(), key=lambda x: x[1].roi)
    best_name, best_result = best_strategy
    
    print(f"\n🏆 Best Strategy: {best_name.replace('_', ' ').title()}")
    print(f"   ROI: {best_result.roi:.1%}")
    print(f"   Sharpe Ratio: {best_result.sharpe_ratio:.2f}")
    print(f"   Max Drawdown: {best_result.max_drawdown:.1%}")
    print(f"   Total Return: ${best_result.total_return:,.0f}")
    
    return results

def demo_ab_testing(results):
    """Demonstrate A/B testing functionality."""
    print("\n⚖️ A/B Testing Demo")
    print("-" * 20)
    
    if len(results) < 2:
        print("❌ Need at least 2 strategies for A/B testing")
        return
    
    # Compare top 2 strategies
    sorted_strategies = sorted(results.items(), key=lambda x: x[1].roi, reverse=True)
    strategy_a_name, strategy_a_result = sorted_strategies[0]
    strategy_b_name, strategy_b_result = sorted_strategies[1]
    
    print(f"Comparing: {strategy_a_name} vs {strategy_b_name}")
    
    # Initialize evaluation suite for A/B test
    config = EvalConfig(sport="nba")
    eval_suite = EvalSuite(config)
    
    # Run A/B test
    ab_result = eval_suite.run_ab_test(strategy_a_name, strategy_b_name)
    
    if 'error' not in ab_result:
        print(f"\n📊 A/B Test Results:")
        print(f"Strategy A ({strategy_a_name}): ROI {ab_result['result_a'].roi:.1%}")
        print(f"Strategy B ({strategy_b_name}): ROI {ab_result['result_b'].roi:.1%}")
        
        winner = ab_result['winner']
        improvement = ab_result['improvement']
        significant = ab_result['statistical_significance']['significant']
        
        print(f"\n🏆 Winner: {winner}")
        print(f"📈 Improvement: {improvement:.1%}")
        print(f"📊 Statistically Significant: {'Yes' if significant else 'No'}")
        
        if significant:
            print("✅ The difference is statistically significant (p < 0.05)")
        else:
            print("⚠️ The difference is not statistically significant")
        
        # Show detailed statistics
        stats = ab_result['statistical_significance']
        print(f"\nStatistical Details:")
        print(f"  T-test p-value: {stats['t_test_p_value']:.4f}")
        print(f"  Mann-Whitney p-value: {stats['mann_whitney_p_value']:.4f}")
        print(f"  Effect size (Cohen's d): {stats['cohens_d']:.3f}")
        
    else:
        print(f"❌ A/B test failed: {ab_result['error']}")

def demo_performance_metrics():
    """Demonstrate performance metrics calculation."""
    print("\n📈 Performance Metrics Demo")
    print("-" * 30)
    
    # Create sample performance data
    np.random.seed(42)
    n_days = 252  # 1 year of trading days
    
    # Simulate daily returns
    daily_returns = np.random.normal(0.001, 0.02, n_days)  # 0.1% daily return, 2% volatility
    
    # Calculate cumulative returns
    cumulative_returns = np.cumprod(1 + daily_returns)
    initial_value = 10000
    portfolio_values = initial_value * cumulative_returns
    
    # Calculate metrics
    total_return = (portfolio_values[-1] - initial_value) / initial_value
    annualized_return = np.mean(daily_returns) * 252
    volatility = np.std(daily_returns) * np.sqrt(252)
    sharpe_ratio = annualized_return / volatility if volatility > 0 else 0
    
    # Maximum drawdown
    peak = np.maximum.accumulate(portfolio_values)
    drawdown = (portfolio_values - peak) / peak
    max_drawdown = np.min(drawdown)
    
    # Value at Risk (95%)
    var_95 = np.percentile(daily_returns, 5)
    
    print(f"Performance Metrics (Sample):")
    print(f"  Total Return: {total_return:.1%}")
    print(f"  Annualized Return: {annualized_return:.1%}")
    print(f"  Volatility: {volatility:.1%}")
    print(f"  Sharpe Ratio: {sharpe_ratio:.2f}")
    print(f"  Max Drawdown: {max_drawdown:.1%}")
    print(f"  Value at Risk (95%): {var_95:.1%}")
    
    print(f"\nInterpretation:")
    if sharpe_ratio > 1.0:
        print("✅ Excellent risk-adjusted returns (Sharpe > 1.0)")
    elif sharpe_ratio > 0.5:
        print("🆗 Good risk-adjusted returns (Sharpe > 0.5)")
    else:
        print("⚠️ Poor risk-adjusted returns (Sharpe < 0.5)")
    
    if max_drawdown > -0.2:
        print("✅ Manageable drawdown (< 20%)")
    else:
        print("⚠️ High drawdown risk (> 20%)")

def demo_betting_strategies():
    """Demonstrate different betting strategies."""
    print("\n💰 Betting Strategy Comparison")
    print("-" * 35)
    
    strategies = [
        ("Fixed", "fixed", {"fixed_bet_amount": 100}),
        ("Percentage", "percentage", {"percentage_bet": 0.02}),
        ("Kelly", "kelly", {"kelly_multiplier": 0.25})
    ]
    
    for strategy_name, strategy_type, params in strategies:
        print(f"\n{strategy_name} Betting Strategy:")
        
        config = EvalConfig(
            sport="nba",
            bet_size_strategy=strategy_type,
            initial_bankroll=10000.0,
            **params
        )
        
        eval_suite = EvalSuite(config)
        
        # Run a single backtest
        result = eval_suite.run_backtest("baseline_random")
        
        print(f"  ROI: {result.roi:.1%}")
        print(f"  Sharpe Ratio: {result.sharpe_ratio:.2f}")
        print(f"  Total Bets: {result.total_bets}")
        print(f"  Win Rate: {result.win_rate:.1%}")
        print(f"  Final Bankroll: ${(config.initial_bankroll + result.total_return):,.0f}")

def demo_sport_comparison():
    """Demonstrate comparison between NBA and NFL."""
    print("\n🏀🏈 NBA vs NFL Comparison")
    print("-" * 30)
    
    sports = ["nba", "nfl"]
    
    for sport in sports:
        print(f"\n{sport.upper()} Evaluation:")
        
        config = EvalConfig(sport=sport, fixed_bet_amount=100)
        eval_suite = EvalSuite(config)
        
        # Quick evaluation
        result = eval_suite.run_backtest("baseline_highest_ev")
        
        print(f"  Models Available: {list(eval_suite.models.keys())}")
        print(f"  Sample ROI: {result.roi:.1%}")
        print(f"  Sample Win Rate: {result.win_rate:.1%}")
        print(f"  Sample Sharpe: {result.sharpe_ratio:.2f}")

def main():
    """Main demo function."""
    print("🎯 ML Model Evaluation Suite - Comprehensive Demo")
    print("=" * 60)
    
    print("This demo showcases:")
    print("  • Comprehensive backtesting with financial metrics")
    print("  • A/B testing with statistical significance")
    print("  • Multiple betting strategies and risk management")
    print("  • Performance analytics and model comparison")
    print("  • Multi-sport evaluation capabilities")
    
    try:
        # Demo 1: Basic functionality
        eval_suite = demo_basic_functionality()
        
        # Demo 2: Data generation
        eval_suite = demo_data_generation()
        
        # Demo 3: Backtesting
        results = demo_backtesting()
        
        # Demo 4: A/B testing
        demo_ab_testing(results)
        
        # Demo 5: Performance metrics
        demo_performance_metrics()
        
        # Demo 6: Betting strategies
        demo_betting_strategies()
        
        # Demo 7: Sport comparison
        demo_sport_comparison()
        
        print("\n🎯 Demo Summary")
        print("=" * 20)
        
        print("✅ Evaluation Suite Capabilities:")
        print("  • Load and evaluate ML models (XGBoost, Optimizer)")
        print("  • Generate realistic synthetic data for backtesting")
        print("  • Calculate comprehensive financial metrics")
        print("  • Perform statistical A/B testing")
        print("  • Support multiple betting strategies")
        print("  • Compare performance across sports")
        
        print("\n✅ Available Interfaces:")
        print("  • Command-line backtesting")
        print("  • Interactive Streamlit dashboard")
        print("  • Programmatic API for integration")
        print("  • Statistical analysis and reporting")
        
        print("\n🚀 Next Steps:")
        print("  • Run: python eval_ml_models.py --mode backtest --sport nba")
        print("  • Launch dashboard: streamlit run eval_ml_models.py")
        print("  • A/B test: python eval_ml_models.py --mode ab_test --strategy-a baseline_random --strategy-b ml_optimizer")
        
        print(f"\n✅ ML Model Evaluation Suite is ready for production use!")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
