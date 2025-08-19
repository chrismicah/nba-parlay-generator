#!/usr/bin/env python3
"""
Simple test script for the NFL Injury Severity Classifier
"""

import json
from transformers import RobertaTokenizer, RobertaForSequenceClassification
import torch


def test_injury_classifier():
    """Test the trained injury severity classifier"""
    print("🧪 Testing NFL Injury Severity Classifier")
    print("=" * 50)
    
    # Load model and tokenizer
    model_path = 'models/nfl_injury_severity_classifier'
    try:
        model = RobertaForSequenceClassification.from_pretrained(model_path)
        tokenizer = RobertaTokenizer.from_pretrained(model_path)
        
        # Load label mappings
        with open(f'{model_path}/label_mappings.json', 'r') as f:
            label_mappings = json.load(f)
        
        id_to_label = {int(k): v for k, v in label_mappings['id_to_label'].items()}
        
        print("✅ Model loaded successfully!")
        print(f"📊 Available severity labels: {label_mappings['labels']}")
        
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        return
    
    # Test tweets representing different injury severities
    test_tweets = [
        ("Player placed on injured reserve with torn ACL", "out_for_season"),
        ("QB questionable to return with ankle injury", "day_to_day"), 
        ("RB listed as day-to-day with minor hamstring strain", "day_to_day"),
        ("WR dealing with undisclosed injury, status unclear", "unconfirmed"),
        ("TE ruled out for remainder of season", "out_for_season"),
        ("Player has minor bruise, should be fine", "minor"),
        ("Injury update coming soon", "unconfirmed")
    ]
    
    print(f"\n🔬 Testing {len(test_tweets)} sample tweets:")
    print("-" * 70)
    
    correct_predictions = 0
    
    for i, (text, expected) in enumerate(test_tweets, 1):
        # Tokenize
        inputs = tokenizer(
            text,
            truncation=True,
            padding=True,
            max_length=512,
            return_tensors='pt'
        )
        
        # Predict (using CPU to avoid MPS issues)
        model.to('cpu')
        with torch.no_grad():
            outputs = model(**inputs)
            predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
            predicted_class_id = predictions.argmax().item()
            confidence = predictions.max().item()
        
        predicted_severity = id_to_label[predicted_class_id]
        
        # Check if prediction matches expected
        is_correct = predicted_severity == expected
        if is_correct:
            correct_predictions += 1
        
        status = "✅" if is_correct else "❌"
        
        print(f"{i}. {status} Text: '{text[:60]}...'")
        print(f"   Expected: {expected:>15} | Predicted: {predicted_severity:>15} ({confidence:.3f})")
        print()
    
    accuracy = correct_predictions / len(test_tweets)
    print(f"🎯 Test Accuracy: {correct_predictions}/{len(test_tweets)} = {accuracy:.2%}")
    
    if accuracy >= 0.7:
        print("🎉 Great! The classifier is working well on sample data.")
    else:
        print("⚠️  The classifier may need more training or better examples.")


if __name__ == "__main__":
    test_injury_classifier()
