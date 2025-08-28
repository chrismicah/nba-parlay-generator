#!/usr/bin/env python3
"""
Multi-Sport BioBERT Injury Classifier Demo

Demonstrates the capabilities of the trained multi-sport BioBERT model
for classifying NFL and NBA injury severity with enhanced features.
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from train_multisport_biobert_injury_classifier import MultiSportBioBERTInjuryClassifier
from datetime import datetime
import json

def demo_multi_sport_predictions():
    """Demo the multi-sport BioBERT classifier with various injury scenarios"""
    
    print("🏥 Multi-Sport BioBERT Injury Severity Classifier Demo")
    print("=" * 60)
    print()
    
    # Initialize classifier
    classifier = MultiSportBioBERTInjuryClassifier(confidence_threshold=0.8)
    
    # Check if model exists
    model_path = "models/multisport_biobert_injury_classifier"
    if not os.path.exists(model_path):
        print("❌ Model not found. Please run training first:")
        print("   python tools/train_multisport_biobert_injury_classifier.py")
        return
    
    print("🤖 Loading Multi-Sport BioBERT Model...")
    try:
        classifier.load_model(model_path)
        print("✅ Model loaded successfully!")
        print()
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        return
    
    # Define test scenarios
    nfl_scenarios = [
        {
            "text": "Patrick Mahomes is out for the season with a torn ACL, surgery scheduled for next week",
            "author": "AdamSchefter",
            "expected": "out_for_season"
        },
        {
            "text": "Travis Kelce is questionable for Sunday's game with a minor ankle sprain, listed as probable",
            "author": "RapSheet", 
            "expected": "minor"
        },
        {
            "text": "Josh Allen is day-to-day with knee soreness, will be evaluated on game day",
            "author": "MikeGarafolo",
            "expected": "day_to_day"
        },
        {
            "text": "Player left practice early, injury status unknown pending MRI results",
            "author": "NFLInjuryNws",
            "expected": "unconfirmed"
        },
        {
            "text": "Aaron Rodgers placed on injured reserve with season-ending Achilles injury",
            "author": "ESPNNFL",
            "expected": "out_for_season"
        },
        {
            "text": "WR dealing with concussion protocol, uncertain for this week's game",
            "author": "FieldYates",
            "expected": "unconfirmed"
        }
    ]
    
    nba_scenarios = [
        {
            "text": "LeBron James undergoes foot surgery, expected to miss remainder of season",
            "author": "ShamsCharania",
            "expected": "out_for_season"
        },
        {
            "text": "Stephen Curry has minor wrist soreness, should be fine for tonight's game",
            "author": "wojespn",
            "expected": "minor"
        },
        {
            "text": "Anthony Davis is day-to-day with back tightness, game-time decision",
            "author": "ChrisBHaynes",
            "expected": "day_to_day"
        },
        {
            "text": "Injury report update pending, player status to be determined",
            "author": "Rotoworld_BK",
            "expected": "unconfirmed"
        }
    ]
    
    # Test NFL scenarios
    print("🏈 NFL Injury Classification Results:")
    print("-" * 50)
    
    for i, scenario in enumerate(nfl_scenarios, 1):
        print(f"\n{i}. NFL Scenario:")
        print(f"   Text: {scenario['text']}")
        print(f"   Reporter: @{scenario['author']}")
        print(f"   Expected: {scenario['expected']}")
        
        # Make prediction
        predictions = classifier.predict_with_confidence(
            texts=[scenario['text']],
            sports=['nfl'],
            authors=[scenario['author']],
            timestamps=[datetime.now().strftime('%a %b %d %H:%M:%S +0000 %Y')]
        )
        
        result = predictions[0]
        print(f"   🔍 Predicted: {result['predicted_label']}")
        print(f"   📊 Raw Confidence: {result['raw_confidence']:.3f}")
        print(f"   ⚖️  Adjusted Confidence: {result['adjusted_confidence']:.3f}")
        print(f"   👤 Author Credibility: {result['author_credibility']:.1f}")
        print(f"   ⏰ Timestamp Weight: {result['timestamp_weight']:.1f}")
        
        # Check if prediction matches expectation
        if result['predicted_label'] == scenario['expected']:
            print("   ✅ CORRECT PREDICTION")
        else:
            print("   ❌ INCORRECT PREDICTION")
        
        if result['is_confident']:
            print("   🎯 High Confidence - No Review Needed")
        else:
            print("   ⚠️  Low Confidence - Needs Manual Review")
    
    # Test NBA scenarios
    print("\n\n🏀 NBA Injury Classification Results:")
    print("-" * 50)
    
    for i, scenario in enumerate(nba_scenarios, 1):
        print(f"\n{i}. NBA Scenario:")
        print(f"   Text: {scenario['text']}")
        print(f"   Reporter: @{scenario['author']}")
        print(f"   Expected: {scenario['expected']}")
        
        # Make prediction
        predictions = classifier.predict_with_confidence(
            texts=[scenario['text']],
            sports=['nba'],
            authors=[scenario['author']],
            timestamps=[datetime.now().strftime('%a %b %d %H:%M:%S +0000 %Y')]
        )
        
        result = predictions[0]
        print(f"   🔍 Predicted: {result['predicted_label']}")
        print(f"   📊 Raw Confidence: {result['raw_confidence']:.3f}")
        print(f"   ⚖️  Adjusted Confidence: {result['adjusted_confidence']:.3f}")
        print(f"   👤 Author Credibility: {result['author_credibility']:.1f}")
        print(f"   ⏰ Timestamp Weight: {result['timestamp_weight']:.1f}")
        
        # Check if prediction matches expectation
        if result['predicted_label'] == scenario['expected']:
            print("   ✅ CORRECT PREDICTION")
        else:
            print("   ❌ INCORRECT PREDICTION")
            
        if result['is_confident']:
            print("   🎯 High Confidence - No Review Needed")
        else:
            print("   ⚠️  Low Confidence - Needs Manual Review")
    
    # Show probability distributions for a complex case
    print("\n\n📊 Detailed Probability Analysis:")
    print("-" * 50)
    
    complex_case = "Player underwent arthroscopic knee surgery and is expected to miss 4-6 weeks of action"
    print(f"Complex Case: {complex_case}")
    
    # Test with different sports and authors
    for sport, author in [("nfl", "AdamSchefter"), ("nba", "ShamsCharania")]:
        print(f"\n{sport.upper()} Context (@{author}):")
        
        predictions = classifier.predict_with_confidence(
            texts=[complex_case],
            sports=[sport],
            authors=[author]
        )
        
        result = predictions[0]
        print(f"   Predicted: {result['predicted_label']} ({result['adjusted_confidence']:.3f} confidence)")
        print("   Probability Distribution:")
        
        for label, prob in sorted(result['all_probabilities'].items(), key=lambda x: x[1], reverse=True):
            bar_length = int(prob * 20)  # Scale to 20 chars
            bar = "█" * bar_length + "░" * (20 - bar_length)
            print(f"     {label:15} {bar} {prob:.3f}")
    
    # Model summary
    print("\n\n🎯 Model Summary:")
    print("-" * 50)
    
    # Load training summary if available
    summary_path = f"{model_path}/training_summary.json"
    if os.path.exists(summary_path):
        with open(summary_path, 'r') as f:
            summary = json.load(f)
        
        print(f"✅ Model Type: {summary.get('model_type', 'Multi-Sport BioBERT')}")
        print(f"📈 Overall Accuracy: {summary.get('overall_accuracy', 'N/A'):.1%}")
        print(f"🏈 NFL Accuracy: {summary.get('nfl_accuracy', 'N/A')}")
        print(f"🏀 NBA Accuracy: {summary.get('nba_accuracy', 'N/A')}")
        print(f"🎯 Confident Predictions Accuracy: {summary.get('confident_accuracy', 'N/A'):.1%}")
        print(f"📊 Coverage (% above threshold): {summary.get('coverage', 'N/A'):.1%}")
        print(f"⚖️  Confidence Threshold: {summary.get('confidence_threshold', 0.8)}")
        print(f"🔧 Enhanced Features: {', '.join(summary.get('features', []))}")
    
    print("\n\n🏆 Demo Complete!")
    print("The Multi-Sport BioBERT classifier successfully handles both NFL and NBA injury classification")
    print("with sport-aware context, author credibility weighting, and timestamp decay.")

if __name__ == "__main__":
    demo_multi_sport_predictions()
