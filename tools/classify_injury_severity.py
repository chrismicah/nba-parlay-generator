#!/usr/bin/env python3
"""
Injury Severity Classification Inference Script

This script uses the trained BioBERT model to classify injury severity
with confidence thresholding.
"""

import argparse
import json
import sys
from train_biobert_injury_classifier import BioBERTInjuryClassifier

def main():
    parser = argparse.ArgumentParser(description='Classify injury severity using BioBERT')
    parser.add_argument('--text', type=str, help='Text to classify')
    parser.add_argument('--file', type=str, help='File containing texts to classify (one per line)')
    parser.add_argument('--model-path', type=str, default='models/biobert_injury_classifier',
                       help='Path to the trained model')
    parser.add_argument('--confidence-threshold', type=float, default=0.8,
                       help='Confidence threshold for predictions')
    parser.add_argument('--output-format', choices=['text', 'json'], default='text',
                       help='Output format')
    
    args = parser.parse_args()
    
    if not args.text and not args.file:
        print("Error: Must provide either --text or --file")
        sys.exit(1)
    
    # Initialize classifier
    classifier = BioBERTInjuryClassifier(confidence_threshold=args.confidence_threshold)
    
    try:
        classifier.load_model(args.model_path)
    except Exception as e:
        print(f"Error loading model: {e}")
        sys.exit(1)
    
    # Prepare texts
    if args.text:
        texts = [args.text]
    else:
        with open(args.file, 'r') as f:
            texts = [line.strip() for line in f if line.strip()]
    
    # Make predictions
    predictions = classifier.predict_with_confidence(texts)
    
    # Output results
    if args.output_format == 'json':
        print(json.dumps(predictions, indent=2))
    else:
        for i, pred in enumerate(predictions):
            if len(texts) > 1:
                print(f"\n--- Prediction {i+1} ---")
            
            print(f"Text: {pred['text']}")
            print(f"Predicted Severity: {pred['predicted_label']}")
            print(f"Confidence: {pred['confidence']:.4f}")
            
            if pred['needs_review']:
                print("⚠️  LOW CONFIDENCE - Needs manual review")
            else:
                print("✅ HIGH CONFIDENCE")
            
            print("\nAll probabilities:")
            for label, prob in pred['all_probabilities'].items():
                indicator = "👉" if label == pred['predicted_label'] else "  "
                print(f"{indicator} {label}: {prob:.4f}")

if __name__ == "__main__":
    main()
