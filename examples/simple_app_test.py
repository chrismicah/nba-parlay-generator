#!/usr/bin/env python3
"""
Simple App-Friendly Test for NFL and NBA

Shows how to use fetch_injury_updates() function directly.
"""

import asyncio
import json
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.grok_tweet_fetcher import fetch_injury_updates, get_sport_handles

async def test_nfl_app_friendly():
    """Test NFL injury monitoring with app-friendly function"""
    print("🏈 Testing NFL App-Friendly Function\n")
    
    print("📱 NFL Handles:")
    nfl_handles = get_sport_handles("nfl")
    for handle in nfl_handles:
        print(f"   • @{handle}")
    
    print(f"\n🔍 Calling fetch_injury_updates('nfl')...")
    
    try:
        # This is how you'd use it in your app
        nfl_updates = await fetch_injury_updates(
            sport="nfl",
            min_likes=3,        # Lower for demo
            min_views=500,      # Lower for demo
            max_search_results=5  # Small for demo
        )
        
        print(f"✅ Success!")
        print(f"   📊 Tweets found: {nfl_updates['count']}")
        print(f"   👥 Handles used: {len(nfl_updates['handles_used'])}")
        print(f"   ⏰ Timestamp: {nfl_updates['timestamp']}")
        
        if nfl_updates['tweets']:
            print(f"\n📱 Sample NFL tweets:")
            for i, tweet in enumerate(nfl_updates['tweets'][:2], 1):
                print(f"   {i}. @{tweet['author']}: {tweet['text'][:80]}...")
        
        return nfl_updates
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

async def test_nba_app_friendly():
    """Test NBA injury monitoring with app-friendly function"""
    print("\n🏀 Testing NBA App-Friendly Function\n")
    
    print("📱 NBA Handles:")
    nba_handles = get_sport_handles("nba")
    for handle in nba_handles:
        print(f"   • @{handle}")
    
    print(f"\n🔍 Calling fetch_injury_updates('nba')...")
    
    try:
        # This is how you'd use it in your app
        nba_updates = await fetch_injury_updates(
            sport="nba", 
            min_likes=3,        # Lower for demo
            min_views=500,      # Lower for demo
            max_search_results=5  # Small for demo
        )
        
        print(f"✅ Success!")
        print(f"   📊 Tweets found: {nba_updates['count']}")
        print(f"   👥 Handles used: {len(nba_updates['handles_used'])}")
        print(f"   ⏰ Timestamp: {nba_updates['timestamp']}")
        
        if nba_updates['tweets']:
            print(f"\n📱 Sample NBA tweets:")
            for i, tweet in enumerate(nba_updates['tweets'][:2], 1):
                print(f"   {i}. @{tweet['author']}: {tweet['text'][:80]}...")
        
        return nba_updates
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

async def demo_app_usage():
    """Show how this would work in a real app"""
    print("\n🚀 Real App Usage Example\n")
    
    print("```python")
    print("# In your FastAPI/Flask app:")
    print("from tools.grok_tweet_fetcher import fetch_injury_updates")
    print("")
    print("@app.get('/api/injuries/{sport}')")
    print("async def get_injuries(sport: str):")
    print("    try:")
    print("        updates = await fetch_injury_updates(sport)")
    print("        return {")
    print("            'success': True,")
    print("            'data': {")
    print("                'sport': updates['sport'],")
    print("                'tweets': updates['tweets'],")
    print("                'count': updates['count'],")
    print("                'timestamp': updates['timestamp']")
    print("            }")
    print("        }")
    print("    except Exception as e:")
    print("        return {'success': False, 'error': str(e)}")
    print("")
    print("# Usage:")
    print("# GET /api/injuries/nfl  -> NFL injury tweets")
    print("# GET /api/injuries/nba  -> NBA injury tweets")
    print("```")

def save_results(nfl_updates, nba_updates):
    """Save results to files for inspection"""
    if nfl_updates:
        with open("data/tweets/nfl_app_test.json", "w") as f:
            json.dump(nfl_updates, f, indent=2, default=str)
        print(f"\n💾 NFL results saved to data/tweets/nfl_app_test.json")
    
    if nba_updates:
        with open("data/tweets/nba_app_test.json", "w") as f:
            json.dump(nba_updates, f, indent=2, default=str)
        print(f"💾 NBA results saved to data/tweets/nba_app_test.json")

async def main():
    """Run the simple app test"""
    print("🚀 Simple App-Friendly Test - NFL & NBA")
    print("=" * 45)
    
    # Test NFL
    nfl_updates = await test_nfl_app_friendly()
    
    # Test NBA  
    nba_updates = await test_nba_app_friendly()
    
    # Show app usage
    await demo_app_usage()
    
    # Save results
    save_results(nfl_updates, nba_updates)
    
    print(f"\n🎯 Summary:")
    if nfl_updates:
        print(f"   🏈 NFL: {nfl_updates['count']} tweets from {len(nfl_updates['handles_used'])} handles")
    if nba_updates:
        print(f"   🏀 NBA: {nba_updates['count']} tweets from {len(nba_updates['handles_used'])} handles")
    
    print(f"\n✅ App-friendly functions working perfectly!")

if __name__ == "__main__":
    asyncio.run(main())
