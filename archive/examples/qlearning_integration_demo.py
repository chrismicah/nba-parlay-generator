#!/usr/bin/env python3
"""
Q-Learning Parlay Agent Integration Demo - QLEARNING-DEMO-001

Demonstrates the complete Q-Learning reinforcement learning integration 
for optimal parlay construction within the ParlayBuilder system.

Features:
- Custom Gymnasium environment for parlay construction
- Deep Q-Network (DQN) with experience replay 
- Integration with existing ParlayBuilder infrastructure
- Strategy comparison vs other methods (Random, EV-based, LP optimization)
- Evaluation against baseline strategies
- Experimental flag controls for production safety
"""

import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from ml.ml_qlearning_agent import QLearningParlayAgent, QLearningConfig, evaluate_vs_baseline
from tools.parlay_builder import ParlayBuilder

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_sample_legs():
    """Create sample parlay legs for testing."""
    return [
        {
            'leg_id': 'nba_lebron_points',
            'odds': -110,
            'expected_value': 0.05,
            'market_type': 'points',
            'sport': 'nba',
            'player_name': 'LeBron James',
            'selection_name': 'LeBron James Over 25.5 Points',
            'game_id': 'nba_lakers_warriors',
            'sportsbook': 'DRAFTKINGS'
        },
        {
            'leg_id': 'nba_curry_threes',
            'odds': 120,
            'expected_value': 0.08,
            'market_type': 'threes',
            'sport': 'nba',
            'player_name': 'Stephen Curry',
            'selection_name': 'Stephen Curry Over 4.5 Threes',
            'game_id': 'nba_lakers_warriors',
            'sportsbook': 'DRAFTKINGS'
        },
        {
            'leg_id': 'nba_davis_rebounds',
            'odds': -150,
            'expected_value': 0.03,
            'market_type': 'rebounds',
            'sport': 'nba',
            'player_name': 'Anthony Davis',
            'selection_name': 'Anthony Davis Over 10.5 Rebounds',
            'game_id': 'nba_lakers_warriors',
            'sportsbook': 'DRAFTKINGS'
        },
        {
            'leg_id': 'nfl_allen_passing',
            'odds': 180,
            'expected_value': 0.12,
            'market_type': 'passing_yards',
            'sport': 'nfl',
            'player_name': 'Josh Allen',
            'selection_name': 'Josh Allen Over 275.5 Passing Yards',
            'game_id': 'nfl_bills_chiefs',
            'sportsbook': 'DRAFTKINGS'
        },
        {
            'leg_id': 'nfl_diggs_receiving',
            'odds': -130,
            'expected_value': 0.06,
            'market_type': 'receiving_yards',
            'sport': 'nfl',
            'player_name': 'Stefon Diggs',
            'selection_name': 'Stefon Diggs Over 85.5 Receiving Yards',
            'game_id': 'nfl_bills_chiefs',
            'sportsbook': 'DRAFTKINGS'
        },
        {
            'leg_id': 'nfl_mahomes_touchdowns',
            'odds': -200,
            'expected_value': 0.04,
            'market_type': 'touchdowns',
            'sport': 'nfl',
            'player_name': 'Patrick Mahomes',
            'selection_name': 'Patrick Mahomes Over 1.5 Passing TDs',
            'game_id': 'nfl_bills_chiefs',
            'sportsbook': 'DRAFTKINGS'
        }
    ]

def demo_qlearning_training():
    """Demonstrate Q-Learning agent training."""
    print("🤖 Q-Learning Agent Training Demo")
    print("-" * 40)
    
    # Initialize with reduced episodes for demo
    config = QLearningConfig(
        num_episodes=200,
        eval_frequency=50,
        learning_rate=1e-3
    )
    
    agent = QLearningParlayAgent(config)
    
    print(f"Environment: {agent.env.observation_space.shape[0]} state dims, {agent.env.action_space.n} actions")
    print(f"Network: {sum(p.numel() for p in agent.q_network.parameters())} parameters")
    
    # Train agent
    print("\n🚀 Training agent...")
    training_results = agent.train()
    
    print(f"✅ Training completed!")
    print(f"  Episodes: {training_results['total_episodes']}")
    print(f"  Final reward: {training_results['avg_reward']:.3f}")
    print(f"  Final epsilon: {training_results['final_epsilon']:.3f}")
    
    # Save model
    agent.save_model()
    print("💾 Model saved for integration testing")
    
    return agent

def demo_parlay_builder_integration():
    """Demonstrate ParlayBuilder integration."""
    print("\n🏗️ ParlayBuilder Integration Demo")
    print("-" * 40)
    
    # Initialize ParlayBuilder
    parlay_builder = ParlayBuilder()
    
    print(f"Q-Learning available: {hasattr(parlay_builder, 'qlearning_agent')}")
    print(f"Q-Learning enabled: {getattr(parlay_builder, 'qlearning_enabled', False)}")
    
    # Create sample legs
    candidate_legs = create_sample_legs()
    print(f"\nTesting with {len(candidate_legs)} candidate legs:")
    for leg in candidate_legs:
        print(f"  • {leg['player_name']} - {leg['market_type']} (EV: {leg['expected_value']:.1%})")
    
    # Test experimental Q-Learning parlay building
    print("\n🧪 Testing Q-Learning Parlay Building (Experimental):")
    
    # This requires experimental=True flag
    qlearning_parlay = parlay_builder.build_qlearning_parlay(
        candidate_legs, 
        max_legs=4, 
        experimental=True
    )
    
    if qlearning_parlay:
        print(f"✅ Q-Learning selected {len(qlearning_parlay)} legs:")
        total_ev = 0
        for leg in qlearning_parlay:
            print(f"  • {leg['player_name']} - {leg['market_type']} (EV: {leg['expected_value']:.1%})")
            total_ev += leg['expected_value']
        print(f"  Total EV: {total_ev:.1%}")
    else:
        print("❌ Q-Learning agent not available or returned no parlay")
    
    # Test strategy comparison
    print("\n⚖️ Strategy Comparison:")
    comparison = parlay_builder.compare_parlay_strategies(candidate_legs, max_legs=4)
    
    print("Available strategies:")
    for strategy_name, results in comparison['strategies'].items():
        method = results['method']
        count = results['count']
        ev = results['total_ev']
        print(f"  • {method}: {count} legs, Total EV: {ev:.1%}")
    
    best_strategy = comparison['comparison_summary']['best_ev_strategy']
    best_method = comparison['strategies'][best_strategy]['method']
    print(f"\n🏆 Best EV Strategy: {best_method}")
    
    return comparison

def demo_safety_controls():
    """Demonstrate experimental flag safety controls."""
    print("\n🛡️ Safety Controls Demo")
    print("-" * 40)
    
    parlay_builder = ParlayBuilder()
    candidate_legs = create_sample_legs()
    
    # Test without experimental flag (should be blocked)
    print("Testing Q-Learning without experimental flag:")
    result = parlay_builder.build_qlearning_parlay(
        candidate_legs, 
        experimental=False  # Safety: blocked
    )
    print(f"  Result: {'✅ Blocked as expected' if result is None else '❌ Should be blocked'}")
    
    # Test with experimental flag (should work)
    print("\nTesting Q-Learning with experimental flag:")
    result = parlay_builder.build_qlearning_parlay(
        candidate_legs, 
        experimental=True  # Allowed
    )
    print(f"  Result: {'✅ Allowed' if result is not None else '❌ Agent not available'}")

def demo_evaluation_metrics():
    """Demonstrate evaluation against baselines."""
    print("\n📊 Evaluation Demo")
    print("-" * 40)
    
    # Load trained agent
    config = QLearningConfig()
    agent = QLearningParlayAgent(config)
    
    if agent.load_model():
        print("✅ Loaded pre-trained Q-Learning agent")
        
        # Evaluate agent
        print("\n🔍 Evaluating agent performance...")
        eval_results = agent.evaluate(episodes=50)
        
        print(f"Agent Performance:")
        print(f"  • Average reward: {eval_results['avg_reward']:.3f}")
        print(f"  • Win rate: {eval_results['win_rate']:.1%}")
        print(f"  • Average parlay size: {eval_results['avg_parlay_size']:.1f}")
        
        # Compare to baseline
        print(f"\n⚖️ Comparing to random baseline...")
        baseline_results = evaluate_vs_baseline(agent, episodes=50)
        
        improvement = baseline_results['improvement']
        print(f"Baseline Comparison:")
        print(f"  • Agent reward: {baseline_results['agent_avg_reward']:.3f}")
        print(f"  • Baseline reward: {baseline_results['baseline_avg_reward']:.3f}")
        print(f"  • Improvement: {improvement:+.3f}")
        print(f"  • Status: {'✅ Better' if improvement > 0 else '❌ Worse' if improvement < 0 else '🤝 Equal'}")
        
    else:
        print("❌ No pre-trained model found. Run training demo first.")

def main():
    """Main demo function."""
    print("🎯 Q-Learning Parlay Agent - Complete Integration Demo")
    print("=" * 70)
    
    print("This demo showcases:")
    print("  • Deep Q-Network training for parlay optimization")
    print("  • Custom Gymnasium environment for betting decisions")
    print("  • Integration with existing ParlayBuilder infrastructure")
    print("  • Safety controls via experimental flags")
    print("  • Strategy comparison and baseline evaluation")
    
    try:
        # Demo 1: Train a Q-Learning agent
        agent = demo_qlearning_training()
        
        # Demo 2: Test ParlayBuilder integration
        comparison = demo_parlay_builder_integration()
        
        # Demo 3: Show safety controls
        demo_safety_controls()
        
        # Demo 4: Evaluation metrics
        demo_evaluation_metrics()
        
        print("\n🎯 Demo Summary")
        print("=" * 30)
        
        # Summary of capabilities
        print("✅ Q-Learning Agent Features:")
        print("  • Custom Gymnasium environment for parlay construction")
        print("  • Deep Q-Network with experience replay and target networks")
        print("  • State representation: EV, correlation, market features")
        print("  • Action space: add/remove legs with optimal timing")
        print("  • Reward function based on historical outcome simulation")
        
        print("\n✅ ParlayBuilder Integration:")
        print("  • Experimental flag controls for production safety")
        print("  • Strategy comparison vs Random/EV/Optimization methods")
        print("  • Seamless integration with existing infrastructure")
        print("  • Model persistence and loading capabilities")
        
        print("\n✅ Production Readiness:")
        print("  • Safety controls prevent accidental usage")
        print("  • Comprehensive evaluation against baselines")
        print("  • Graceful fallback when models unavailable")
        print("  • Logging and monitoring integration")
        
        print(f"\n🚀 Q-Learning parlay optimization ready for experimental use!")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
