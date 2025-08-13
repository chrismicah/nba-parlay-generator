#!/usr/bin/env python3
"""
Integration script showing how to use the BioBERT injury classifier
in the NBA parlay project workflow.
"""

import pandas as pd
import json
import sys
import os

# Add the tools directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from train_biobert_injury_classifier import BioBERTInjuryClassifier

def classify_injury_tweets(csv_path, output_path=None, confidence_threshold=0.8):
    """
    Classify injury severity for tweets in a CSV file
    
    Args:
        csv_path: Path to CSV file with tweets
        output_path: Path to save results (optional)
        confidence_threshold: Confidence threshold for predictions
    
    Returns:
        DataFrame with injury severity predictions
    """
    
    # Load tweets
    df = pd.read_csv(csv_path)
    
    # Filter out rows with missing text
    df = df.dropna(subset=['text'])
    df = df[df['text'].str.strip() != '']
    
    # Initialize classifier
    classifier = BioBERTInjuryClassifier(confidence_threshold=confidence_threshold)
    
    # Get predictions for all tweets (convert to string to handle any type issues)
    texts = [str(text) for text in df['text'].tolist()]
    predictions = classifier.predict_with_confidence(texts)
    
    # Add predictions to dataframe
    df['predicted_injury_severity'] = [p['predicted_label'] for p in predictions]
    df['injury_confidence'] = [p['confidence'] for p in predictions]
    df['needs_manual_review'] = [p['needs_review'] for p in predictions]
    
    # Add probability columns for each severity level
    for label in ['day_to_day', 'minor', 'out_for_season', 'unconfirmed']:
        df[f'prob_{label}'] = [p['all_probabilities'][label] for p in predictions]
    
    # Save results if output path provided
    if output_path:
        df.to_csv(output_path, index=False)
        print(f"Results saved to {output_path}")
    
    return df

def analyze_injury_predictions(df):
    """Analyze the injury severity predictions"""
    
    print("="*80)
    print("INJURY SEVERITY ANALYSIS")
    print("="*80)
    
    # Overall statistics
    total_tweets = len(df)
    confident_predictions = df['needs_manual_review'] == False
    coverage = confident_predictions.sum() / total_tweets
    
    print(f"Total tweets analyzed: {total_tweets}")
    print(f"High confidence predictions: {confident_predictions.sum()}")
    print(f"Coverage (% above threshold): {coverage:.2%}")
    print(f"Tweets needing manual review: {(~confident_predictions).sum()}")
    
    # Severity distribution
    print(f"\nPredicted Injury Severity Distribution:")
    severity_counts = df['predicted_injury_severity'].value_counts()
    for severity, count in severity_counts.items():
        percentage = count / total_tweets * 100
        print(f"  {severity}: {count} ({percentage:.1f}%)")
    
    # Confidence statistics by severity
    print(f"\nAverage Confidence by Severity:")
    confidence_by_severity = df.groupby('predicted_injury_severity')['injury_confidence'].agg(['mean', 'count'])
    for severity, stats in confidence_by_severity.iterrows():
        print(f"  {severity}: {stats['mean']:.3f} (n={stats['count']})")
    
    # High-confidence predictions by severity
    print(f"\nHigh-Confidence Predictions by Severity:")
    high_conf_by_severity = df[confident_predictions].groupby('predicted_injury_severity').size()
    for severity, count in high_conf_by_severity.items():
        total_for_severity = severity_counts[severity]
        percentage = count / total_for_severity * 100
        print(f"  {severity}: {count}/{total_for_severity} ({percentage:.1f}%)")

def filter_actionable_injuries(df, min_confidence=0.8):
    """
    Filter tweets to actionable injury information for betting/fantasy purposes
    
    Args:
        df: DataFrame with injury predictions
        min_confidence: Minimum confidence threshold
    
    Returns:
        DataFrame with actionable injury tweets
    """
    
    # Filter for high-confidence predictions
    actionable = df[
        (df['injury_confidence'] >= min_confidence) &
        (df['predicted_injury_severity'].isin(['out_for_season', 'day_to_day', 'minor']))
    ].copy()
    
    # Sort by confidence (highest first)
    actionable = actionable.sort_values('injury_confidence', ascending=False)
    
    print(f"\nActionable Injury Tweets (confidence >= {min_confidence}):")
    print(f"Found {len(actionable)} high-confidence injury-related tweets")
    
    if len(actionable) > 0:
        print(f"\nTop 5 Most Confident Predictions:")
        for idx, row in actionable.head().iterrows():
            print(f"\n{row['predicted_injury_severity'].upper()} (confidence: {row['injury_confidence']:.3f})")
            print(f"  Text: {row['text'][:100]}...")
            print(f"  Author: {row.get('author', 'Unknown')}")
    
    return actionable

def main():
    """Main function demonstrating injury classification integration"""
    
    # Example usage with the expanded NBA reporters dataset
    input_file = "data/tweets/nba_reporters_expanded.csv"
    output_file = "data/tweets/nba_reporters_with_injury_severity.csv"
    
    try:
        print("Classifying injury severity for NBA reporter tweets...")
        
        # Classify tweets
        df_with_predictions = classify_injury_tweets(
            input_file, 
            output_file, 
            confidence_threshold=0.8
        )
        
        # Analyze results
        analyze_injury_predictions(df_with_predictions)
        
        # Filter actionable injuries
        actionable_injuries = filter_actionable_injuries(df_with_predictions)
        
        # Save actionable injuries separately
        if len(actionable_injuries) > 0:
            actionable_output = "data/tweets/actionable_injury_tweets.csv"
            actionable_injuries.to_csv(actionable_output, index=False)
            print(f"\nActionable injury tweets saved to {actionable_output}")
        
        print("\n" + "="*80)
        print("INTEGRATION COMPLETE")
        print("="*80)
        print("The injury severity classifier is now ready for use in your NBA parlay project!")
        print("\nNext steps:")
        print("1. Use high-confidence injury predictions for betting decisions")
        print("2. Set up alerts for 'out_for_season' predictions")
        print("3. Monitor 'day_to_day' predictions for lineup changes")
        print("4. Review low-confidence predictions manually")
        
    except FileNotFoundError:
        print(f"Error: Could not find {input_file}")
        print("Please make sure you have scraped NBA reporter tweets first.")
        print("Run: python3 tools/apify_tweet_scraper_v2.py")
    except Exception as e:
        print(f"Error during classification: {e}")

if __name__ == "__main__":
    main()
