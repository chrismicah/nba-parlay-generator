#!/usr/bin/env python3
"""
App-Ready Grok Tweet Fetcher Demo

Shows how to use the enhanced grok_tweet_fetcher with hardcoded NFL/NBA accounts
for app development.
"""

import asyncio
import json
from datetime import datetime, timezone
import sys
import os

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.grok_tweet_fetcher import (
    fetch_injury_updates, 
    get_sport_handles, 
    NFL_HANDLES, 
    NBA_HANDLES
)

async def demo_nfl_injury_monitoring():
    """Demo NFL injury monitoring with hardcoded accounts"""
    print("🏈 NFL Injury Monitoring Demo\n")
    
    print("📱 NFL Handles (Hardcoded):")
    for handle in NFL_HANDLES:
        print(f"   • @{handle}")
    
    print(f"\n🔍 Fetching NFL injury updates...")
    
    try:
        # Use the app-friendly function
        nfl_updates = await fetch_injury_updates(
            sport="nfl",
            min_likes=5,
            min_views=1000,  # Lower threshold for demo
            max_search_results=10  # Small number for demo
        )
        
        print(f"✅ Success! Retrieved {nfl_updates['count']} tweets")
        print(f"📊 From {len(nfl_updates['handles_used'])} handles")
        print(f"⏰ Time range: {nfl_updates['from_date']} to {nfl_updates['to_date']}")
        
        if nfl_updates['tweets']:
            print(f"\n📱 Sample tweets:")
            for i, tweet in enumerate(nfl_updates['tweets'][:3], 1):
                print(f"   {i}. @{tweet['author']}: {tweet['text'][:100]}...")
        else:
            print(f"ℹ️  No tweets found in the time window (normal for demo)")
            
    except Exception as e:
        print(f"❌ Error: {e}")

async def demo_nba_injury_monitoring():
    """Demo NBA injury monitoring with hardcoded accounts"""
    print("\n🏀 NBA Injury Monitoring Demo\n")
    
    print("📱 NBA Handles (Hardcoded):")
    for handle in NBA_HANDLES:
        print(f"   • @{handle}")
    
    print(f"\n🔍 Fetching NBA injury updates...")
    
    try:
        # Use the app-friendly function
        nba_updates = await fetch_injury_updates(
            sport="nba",
            min_likes=5,
            min_views=1000,  # Lower threshold for demo
            max_search_results=10  # Small number for demo
        )
        
        print(f"✅ Success! Retrieved {nba_updates['count']} tweets")
        print(f"📊 From {len(nba_updates['handles_used'])} handles")
        print(f"⏰ Time range: {nba_updates['from_date']} to {nba_updates['to_date']}")
        
        if nba_updates['tweets']:
            print(f"\n📱 Sample tweets:")
            for i, tweet in enumerate(nba_updates['tweets'][:3], 1):
                print(f"   {i}. @{tweet['author']}: {tweet['text'][:100]}...")
        else:
            print(f"ℹ️  No tweets found in the time window (normal for demo)")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def demo_app_integration():
    """Show how this integrates into an app"""
    print("\n🚀 App Integration Example\n")
    
    print("```python")
    print("# In your Flask/FastAPI app:")
    print("from tools.grok_tweet_fetcher import fetch_injury_updates")
    print("")
    print("@app.route('/api/injuries/<sport>')")
    print("async def get_injuries(sport: str):")
    print("    # Get real-time injury updates")
    print("    updates = await fetch_injury_updates(sport)")
    print("    return {")
    print("        'injuries': updates['tweets'],")
    print("        'count': updates['count'],")
    print("        'timestamp': updates['timestamp']")
    print("    }")
    print("")
    print("# For scheduled monitoring:")
    print("async def monitor_injuries():")
    print("    while True:")
    print("        nfl_updates = await fetch_injury_updates('nfl')")
    print("        nba_updates = await fetch_injury_updates('nba')")
    print("        ")
    print("        # Process updates...")
    print("        await asyncio.sleep(300)  # Check every 5 minutes")
    print("```")

def demo_command_line_usage():
    """Show command line usage examples"""
    print("\n💻 Command Line Usage Examples\n")
    
    examples = [
        {
            "description": "NFL monitoring with defaults",
            "command": "python tools/grok_tweet_fetcher.py --sport nfl --out data/tweets/nfl_injuries.jsonl"
        },
        {
            "description": "NBA monitoring with custom settings",
            "command": "python tools/grok_tweet_fetcher.py --sport nba --min-likes 10 --min-views 5000"
        },
        {
            "description": "Custom handles override",
            "command": "python tools/grok_tweet_fetcher.py --sport nfl --handles AdamSchefter RapSheet"
        },
        {
            "description": "Real-time monitoring (last 2 hours)",
            "command": "python tools/grok_tweet_fetcher.py --sport nfl --window-days 1 --target-count 50"
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"{i}. {example['description']}:")
        print(f"   {example['command']}")
        print()

def show_hardcoded_advantages():
    """Show advantages of hardcoded accounts"""
    print("✅ Advantages of Hardcoded Accounts:\n")
    
    advantages = [
        "🔒 **App Stability**: No need to manage handle lists in config files",
        "⚡ **Performance**: No need to load handles from external sources",  
        "🎯 **Quality Control**: Curated list of trusted NFL/NBA reporters",
        "🛠️ **Easy Deployment**: Everything needed is in the code",
        "📊 **Consistent Results**: Same handles across all environments",
        "🚀 **Quick Start**: Just call fetch_injury_updates('nfl') and go!",
        "🔄 **Maintainable**: Easy to update handles in one place",
        "🏈 **Sport-Optimized**: Different handles for NFL vs NBA needs"
    ]
    
    for advantage in advantages:
        print(f"   {advantage}")

async def main():
    """Run the complete demo"""
    print("🚀 Enhanced Grok Tweet Fetcher - App Ready Demo")
    print("=" * 50)
    
    # Check if API key is available
    try:
        from tools.grok_tweet_fetcher import _get_api_key
        api_key = _get_api_key()
        print(f"✅ API key loaded (twitter_key or XAI_API_KEY)")
    except SystemExit:
        print(f"❌ API key not found. Set XAI_API_KEY or twitter_key in your .env file for live demo.")
        print(f"📋 Showing features anyway...\n")
        
        demo_app_integration()
        demo_command_line_usage()
        show_hardcoded_advantages()
        return
    
    # Run live demos
    await demo_nfl_injury_monitoring()
    await demo_nba_injury_monitoring()
    
    # Show integration examples
    demo_app_integration()
    demo_command_line_usage()
    show_hardcoded_advantages()

if __name__ == "__main__":
    asyncio.run(main())
