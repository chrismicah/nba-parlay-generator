#!/usr/bin/env python3
"""
NFL Grok API Workflow - Which Files Are Executed

Shows exactly which files run when NFL injury monitoring is active.
"""

import os
from pathlib import Path

def show_nfl_grok_file_execution():
    """
    Show the complete file execution flow for NFL Grok monitoring
    """
    print("🏈 NFL Grok API Workflow - File Execution Order\n")
    
    print("1️⃣ CORE GROK API FILES:")
    core_files = [
        {
            "file": "tools/grok_tweet_fetcher.py",
            "purpose": "Main Grok API interface",
            "when_executed": "Every monitoring cycle (5-15 min intervals)",
            "what_it_does": [
                "Connects to X/Twitter via Grok API",
                "Fetches tweets from NFL reporters",
                "Handles rate limiting and pagination",
                "Saves raw tweets to JSONL/CSV"
            ],
            "nfl_specific": "Uses NFL reporter handles like @AdamSchefter, @RapSheet"
        },
        {
            "file": "tools/classify_tweet.py", 
            "purpose": "Tweet classification for injury detection",
            "when_executed": "After each tweet fetch",
            "what_it_does": [
                "Classifies tweets as injury_news vs other",
                "Uses RoBERTa model for text classification", 
                "Filters out non-injury content",
                "Returns confidence scores"
            ],
            "nfl_specific": "Trained on NFL injury keywords and patterns"
        },
        {
            "file": "tools/classify_injury_severity.py",
            "purpose": "Injury severity classification",
            "when_executed": "For tweets classified as injury_news",
            "what_it_does": [
                "Uses BioBERT model for medical text analysis",
                "Classifies severity: out, questionable, doubtful, probable",
                "Extracts confidence and medical insights",
                "Handles NFL-specific injury terminology"
            ],
            "nfl_specific": "Understands NFL injury report terms (IR, PUP, etc.)"
        }
    ]
    
    for file_info in core_files:
        print(f"   📄 {file_info['file']}")
        print(f"      🎯 Purpose: {file_info['purpose']}")
        print(f"      ⏰ When: {file_info['when_executed']}")
        print(f"      🔧 What it does:")
        for action in file_info['what_it_does']:
            print(f"         • {action}")
        print(f"      🏈 NFL-specific: {file_info['nfl_specific']}")
        print()

def show_nfl_workflow_orchestration():
    """
    Show how files work together for NFL monitoring
    """
    print("2️⃣ NFL WORKFLOW ORCHESTRATION:")
    
    workflow_steps = [
        {
            "step": 1,
            "file": "scripts/run_scrapers.py",
            "action": "Orchestrates monitoring schedule",
            "nfl_details": "Triggers NFL monitoring every 5-15 minutes during game days"
        },
        {
            "step": 2, 
            "file": "tools/grok_tweet_fetcher.py",
            "action": "Fetch tweets from NFL reporters",
            "nfl_details": "Gets tweets from @AdamSchefter, @RapSheet, @MikeGarafolo, etc."
        },
        {
            "step": 3,
            "file": "tools/classify_tweet.py", 
            "action": "Filter for injury-related content",
            "nfl_details": "Looks for 'out', 'questionable', 'IR', 'concussion protocol'"
        },
        {
            "step": 4,
            "file": "tools/classify_injury_severity.py",
            "action": "Analyze injury severity",
            "nfl_details": "Understands NFL injury report hierarchy (Out > Doubtful > Questionable)"
        },
        {
            "step": 5,
            "file": "tools/enhanced_parlay_strategist_agent.py",
            "action": "Integrate with parlay validation",
            "nfl_details": "Checks if any NFL parlay players are affected by injuries"
        },
        {
            "step": 6,
            "file": "data/tweets/nfl_injury_updates.jsonl",
            "action": "Store processed injury data",
            "nfl_details": "Saves NFL injury tweets with severity labels for quick lookup"
        }
    ]
    
    print("   🔄 Step-by-step execution:")
    for step in workflow_steps:
        print(f"   {step['step']}. 📄 {step['file']}")
        print(f"      Action: {step['action']}")
        print(f"      NFL: {step['nfl_details']}")
        print()

def show_nfl_data_flow():
    """
    Show how data flows through the NFL system
    """
    print("3️⃣ NFL DATA FLOW:")
    
    data_flow = [
        {
            "source": "X/Twitter API (Grok)",
            "format": "Raw tweet JSON", 
            "example": '{"author": "AdamSchefter", "text": "Chiefs RB Isiah Pacheco (ankle) out vs Bills"}'
        },
        {
            "source": "tools/grok_tweet_fetcher.py",
            "format": "Structured tweet data",
            "example": '{"author": "AdamSchefter", "timestamp": "...", "text": "...", "likes": 1500}'
        },
        {
            "source": "tools/classify_tweet.py",
            "format": "Classification result",
            "example": '{"predicted_label": "injury_news", "confidence": 0.94}'
        },
        {
            "source": "tools/classify_injury_severity.py", 
            "format": "Severity analysis",
            "example": '{"severity": "out", "confidence": 0.98, "body_part": "ankle"}'
        },
        {
            "source": "Parlay validation system",
            "format": "Decision output",
            "example": '{"action": "CANCEL", "reason": "Isiah Pacheco ruled out"}'
        }
    ]
    
    print("   📊 Data transformation pipeline:")
    for i, flow in enumerate(data_flow, 1):
        print(f"   {i}. 📡 {flow['source']}")
        print(f"      Format: {flow['format']}")
        print(f"      Example: {flow['example']}")
        print("      ⬇️")
    print("   🏆 Final: Parlay decision made!")

def show_nfl_configuration_files():
    """
    Show configuration and setup files for NFL
    """
    print("\n4️⃣ NFL CONFIGURATION FILES:")
    
    config_files = [
        {
            "file": "config.py",
            "purpose": "Environment variables and API keys",
            "nfl_content": "XAI_API_KEY for Grok access, rate limiting settings"
        },
        {
            "file": "requirements.txt",
            "purpose": "Python dependencies",
            "nfl_content": "xai-sdk>=0.2.0, transformers for NLP models"
        },
        {
            "file": ".env",
            "purpose": "API keys and secrets",
            "nfl_content": "XAI_API_KEY=your_key_here, monitoring intervals"
        },
        {
            "file": "models/multisport_biobert_injury_classifier/",
            "purpose": "NFL injury severity model",
            "nfl_content": "BioBERT model trained on NFL injury data"
        },
        {
            "file": "data/labeled_nfl_injury_tweets_part1.csv",
            "purpose": "Training data for NFL models",
            "nfl_content": "Labeled NFL injury tweets for model training"
        }
    ]
    
    for config in config_files:
        print(f"   📋 {config['file']}")
        print(f"      Purpose: {config['purpose']}")
        print(f"      NFL content: {config['nfl_content']}")
        print()

def show_nfl_execution_command():
    """
    Show actual command to run NFL monitoring
    """
    print("5️⃣ HOW TO RUN NFL MONITORING:")
    
    print("   🚀 Command to start NFL injury monitoring:")
    print("   ```bash")
    print("   # Run NFL Grok monitoring")
    print("   python tools/grok_tweet_fetcher.py \\")
    print("     --handles AdamSchefter RapSheet MikeGarafolo CameronWolfe \\")
    print("     --min-likes 5 \\")
    print("     --min-views 2000 \\")
    print("     --from-date $(date -d '30 minutes ago' -Iseconds) \\")
    print("     --to-date $(date -Iseconds) \\")
    print("     --out data/tweets/nfl_injury_monitoring.jsonl \\")
    print("     --append")
    print("   ```")
    
    print("\n   🔄 Continuous monitoring:")
    print("   ```bash")
    print("   # Run every 15 minutes (typical NFL setup)")
    print("   while true; do")
    print("     python tools/grok_tweet_fetcher.py [options]")
    print("     python tools/classify_tweet.py data/tweets/nfl_injury_monitoring.jsonl")
    print("     python tools/classify_injury_severity.py [classified_tweets]")
    print("     sleep 900  # 15 minutes")
    print("   done")
    print("   ```")
    
    print("\n   📊 Files created during execution:")
    output_files = [
        "data/tweets/nfl_injury_monitoring.jsonl - Raw NFL tweets",
        "data/tweets/nfl_classified.jsonl - Injury-classified tweets", 
        "data/tweets/nfl_severity.jsonl - Severity-analyzed tweets",
        "logs/nfl_monitoring.log - Execution logs",
        "data/nfl_injury_alerts.json - Active injury alerts"
    ]
    
    for file in output_files:
        print(f"     📄 {file}")

def show_nfl_vs_nba_differences():
    """
    Show file differences between NFL and NBA workflows
    """
    print("\n6️⃣ NFL vs NBA FILE DIFFERENCES:")
    
    differences = [
        {
            "aspect": "Reporter handles",
            "nfl": "@AdamSchefter, @RapSheet, @MikeGarafolo",
            "nba": "@ShamsCharania, @TheSteinLine, @ChrisBHaynes"
        },
        {
            "aspect": "Monitoring frequency", 
            "nfl": "Every 15-30 minutes (weekly games)",
            "nba": "Every 5-10 minutes (daily games)"
        },
        {
            "aspect": "Keyword models",
            "nfl": "NFL-specific: IR, PUP, concussion protocol",
            "nba": "NBA-specific: load management, rest day"
        },
        {
            "aspect": "Output files",
            "nfl": "nfl_injury_monitoring.jsonl",
            "nba": "nba_injury_monitoring.jsonl"
        }
    ]
    
    for diff in differences:
        print(f"   📊 {diff['aspect']}:")
        print(f"      🏈 NFL: {diff['nfl']}")
        print(f"      🏀 NBA: {diff['nba']}")
        print()

if __name__ == "__main__":
    show_nfl_grok_file_execution()
    show_nfl_workflow_orchestration()
    show_nfl_data_flow()
    show_nfl_configuration_files()
    show_nfl_execution_command()
    show_nfl_vs_nba_differences()
