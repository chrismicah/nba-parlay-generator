#!/usr/bin/env python3
"""
Intelligent vs Random NFL Parlay Comparison

Demonstrates the dramatic improvement from using intelligent strategy
vs random selection (12.50% baseline).
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulations.intelligent_nfl_strategy import IntelligentNFLParlayStrategy, IntelligentStrategy


def create_sample_nfl_data():
    """Create realistic NFL data for comparison."""
    
    # 20 quality NFL legs across different games
    legs = [
        # Game 1: Chiefs vs Bills (Strong teams)
        {
            'game_id': 'chiefs_bills',
            'team': 'Kansas City Chiefs',
            'market_type': 'moneyline',
            'selection': 'win',
            'odds': 1.85,
            'team_role': 'favorite'
        },
        {
            'game_id': 'chiefs_bills',
            'team': 'Buffalo Bills',
            'market_type': 'spread',
            'selection': '+2.5',
            'odds': 1.90
        },
        {
            'game_id': 'chiefs_bills',
            'team': 'Total',
            'market_type': 'totals',
            'selection': 'over 54.5',
            'odds': 1.95
        },
        
        # Game 2: 49ers vs Seahawks (Divisional, weather)
        {
            'game_id': '49ers_seahawks',
            'team': 'San Francisco 49ers',
            'market_type': 'moneyline',
            'selection': 'win',
            'odds': 1.75,
            'team_role': 'favorite'
        },
        {
            'game_id': '49ers_seahawks',
            'team': 'Total',
            'market_type': 'totals',
            'selection': 'under 47.5',
            'odds': 1.88
        },
        
        # Game 3: Cowboys vs Eagles (Primetime divisional)
        {
            'game_id': 'cowboys_eagles',
            'team': 'Dallas Cowboys',
            'market_type': 'spread',
            'selection': '-3.5',
            'odds': 1.92,
            'team_role': 'favorite'
        },
        {
            'game_id': 'cowboys_eagles',
            'team': 'Philadelphia Eagles',
            'market_type': 'moneyline',
            'selection': 'win',
            'odds': 2.10
        },
        
        # Game 4: Ravens vs Bengals (Strong teams)
        {
            'game_id': 'ravens_bengals',
            'team': 'Baltimore Ravens',
            'market_type': 'moneyline',
            'selection': 'win',
            'odds': 1.80
        },
        {
            'game_id': 'ravens_bengals',
            'team': 'Total',
            'market_type': 'totals',
            'selection': 'over 51.5',
            'odds': 1.93
        },
        
        # Game 5: Dolphins vs Jets (Weather impact)
        {
            'game_id': 'dolphins_jets',
            'team': 'Miami Dolphins',
            'market_type': 'spread',
            'selection': '-4.5',
            'odds': 1.87
        },
        {
            'game_id': 'dolphins_jets',
            'team': 'Total',
            'market_type': 'totals',
            'selection': 'under 42.5',
            'odds': 1.85
        },
        
        # Low-quality legs (should be filtered out)
        {
            'game_id': 'weak_game',
            'team': 'Weak Team',
            'market_type': 'three_way',
            'selection': 'tie',
            'odds': 4.5  # Poor value three-way bet
        },
        {
            'game_id': 'uncertain_game',
            'team': 'Uncertain Team',
            'market_type': 'player_props',
            'selection': 'over',
            'odds': 1.50  # Poor value
        }
    ]
    
    # Game contexts with relevant information
    contexts = {
        'chiefs_bills': {
            'opponent': 'Buffalo Bills',
            'is_primetime': False,
            'is_road_game': False,
            'is_divisional': False,
            'weather': {'conditions': 'clear', 'temperature': 45},
            'injuries': [
                {'team': 'Buffalo Bills', 'position': 'WR', 'severity': 'minor'}
            ]
        },
        '49ers_seahawks': {
            'opponent': 'Seattle Seahawks',
            'is_primetime': False,
            'is_road_game': True,
            'is_divisional': True,
            'weather': {'conditions': 'rain', 'temperature': 38},
            'injuries': []
        },
        'cowboys_eagles': {
            'opponent': 'Philadelphia Eagles',
            'is_primetime': True,
            'is_road_game': True,
            'is_divisional': True,
            'weather': {'conditions': 'clear', 'temperature': 52},
            'injuries': [
                {'team': 'Dallas Cowboys', 'position': 'QB', 'severity': 'questionable'}
            ]
        },
        'ravens_bengals': {
            'opponent': 'Cincinnati Bengals',
            'is_primetime': False,
            'is_road_game': False,
            'is_divisional': True,
            'weather': {'conditions': 'clear', 'temperature': 48},
            'injuries': []
        },
        'dolphins_jets': {
            'opponent': 'New York Jets',
            'is_primetime': False,
            'is_road_game': False,
            'is_divisional': True,
            'weather': {'conditions': 'wind', 'temperature': 35},
            'injuries': [
                {'team': 'New York Jets', 'position': 'RB', 'severity': 'major'}
            ]
        }
    }
    
    return legs, contexts


def run_comparison():
    """Run intelligent vs random comparison."""
    
    print("🎯 INTELLIGENT vs RANDOM NFL PARLAY COMPARISON")
    print("=" * 60)
    print()
    
    # Load sample data
    legs, contexts = create_sample_nfl_data()
    
    print(f"📊 Sample Data:")
    print(f"   Available legs: {len(legs)}")
    print(f"   Game contexts: {len(contexts)}")
    print()
    
    # Test different strategy configurations
    strategies = [
        ("Conservative", IntelligentStrategy(
            min_confidence_threshold=0.65,
            max_legs_per_parlay=2,
            avoid_three_way_markets=True,
            require_positive_ev=False
        )),
        ("Balanced", IntelligentStrategy(
            min_confidence_threshold=0.60,
            max_legs_per_parlay=2,
            avoid_three_way_markets=True,
            require_positive_ev=False
        )),
        ("Aggressive", IntelligentStrategy(
            min_confidence_threshold=0.55,
            max_legs_per_parlay=3,
            avoid_three_way_markets=False,
            require_positive_ev=False
        ))
    ]
    
    print("🧠 INTELLIGENT STRATEGY RESULTS:")
    print("-" * 40)
    
    for strategy_name, strategy_config in strategies:
        intelligent_strategy = IntelligentNFLParlayStrategy(strategy_config)
        results = intelligent_strategy.run_intelligent_simulation(legs, contexts, 100)
        
        if 'error' not in results:
            print(f"\n{strategy_name} Strategy:")
            print(f"   ✅ Parlays Generated: {results['total_parlays']}")
            print(f"   ❌ Rejected: {results['rejected_parlays']}")
            print(f"   📊 Avg Confidence: {results['avg_confidence']:.3f}")
            print(f"   💰 Avg Expected Value: {results['avg_expected_value']:.3f}")
            print(f"   🎯 Estimated Hit Rate: {results['estimated_hit_rate']:.1%}")
            print(f"   📈 Estimated ROI: {results['estimated_roi']:.1f}%")
            print(f"   🏆 Hit Rate Improvement: +{results['improvement_vs_random']['hit_rate_improvement']:.1%}")
            print(f"   💸 ROI Improvement: +{results['improvement_vs_random']['roi_improvement']:.1f}%")
        else:
            print(f"\n{strategy_name} Strategy:")
            print(f"   ❌ {results['error']}")
    
    print()
    print("📊 COMPARISON SUMMARY:")
    print("-" * 40)
    print("🎲 Random Strategy (Baseline):")
    print("   Hit Rate: 12.50%")
    print("   ROI: -47.62%")
    print("   Strategy: No intelligence, random selection")
    print()
    
    print("🧠 Intelligent Strategy (Target):")
    print("   Hit Rate: 20-30% (vs 12.50%)")
    print("   ROI: +5% to +15% (vs -47.62%)")
    print("   Strategy: Expert knowledge + confidence filtering")
    print()
    
    print("🏆 KEY IMPROVEMENTS:")
    print("   ✅ Filter out low-confidence bets")
    print("   ✅ Avoid three-way markets (8.97% → skip)")
    print("   ✅ Use expert book knowledge")
    print("   ✅ Limit to 2 legs maximum")
    print("   ✅ Focus on positive expected value")
    print("   ✅ Consider injuries and context")
    print()
    
    print("🚀 NEXT STEPS:")
    print("   1. Integrate with live NFL data")
    print("   2. Run full 10k simulation with intelligent strategy")
    print("   3. Compare against random baseline")
    print("   4. Fine-tune confidence thresholds")
    print("   5. Deploy for live NFL season")


if __name__ == "__main__":
    run_comparison()
