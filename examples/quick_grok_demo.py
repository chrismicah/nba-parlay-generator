#!/usr/bin/env python3
"""
Quick Grok API Demo - Shows how real-time injury monitoring works
without long wait times
"""

import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

def show_grok_api_usage():
    """
    Quick demonstration of how Grok API is used for injury monitoring
    """
    print("🚀 Quick Grok API Usage Example\n")
    
    # This is how the Grok API is called in your codebase:
    print("1️⃣ How the Grok API Call Works:")
    print("""
    from xai_sdk import Client
    from tools.grok_tweet_fetcher import fetch_tweets_batch
    
    # Initialize client
    client = Client(api_key="your_xai_api_key")
    
    # Fetch recent tweets from NBA reporters
    tweets = fetch_tweets_batch(
        client=client,
        handles=["ShamsCharania", "wojespn", "Underdog__NBA"],
        min_likes=5,
        min_views=1000,
        from_date="2024-01-15T10:00:00Z",  # Last 30 minutes
        to_date="2024-01-15T10:30:00Z",
        max_search_results=25  # ✅ Under the 30 limit
    )
    """)
    
    print("\n2️⃣ What the API Returns (Sample):")
    sample_tweets = [
        {
            "author": "wojespn",
            "timestamp": "2024-01-15T10:25:00Z",
            "text": "Lakers' LeBron James (ankle) is questionable for tonight's game vs Warriors, sources tell ESPN.",
            "url": "https://x.com/wojespn/status/123456789",
            "likes": 1500,
            "views": 75000
        },
        {
            "author": "ShamsCharania", 
            "timestamp": "2024-01-15T10:22:00Z",
            "text": "Celtics star Jayson Tatum will be re-evaluated in one week after suffering knee soreness, per sources.",
            "url": "https://x.com/ShamsCharania/status/123456790",
            "likes": 890,
            "views": 45000
        }
    ]
    
    for i, tweet in enumerate(sample_tweets, 1):
        print(f"   Tweet {i}:")
        print(f"     Author: @{tweet['author']}")
        print(f"     Text: {tweet['text']}")
        print(f"     Engagement: {tweet['likes']} likes, {tweet['views']} views")
        print()
    
    print("3️⃣ Real-Time Injury Processing:")
    
    # Simulate injury detection
    injury_keywords = ['questionable', 'ankle', 'knee', 'soreness', 're-evaluated']
    
    for tweet in sample_tweets:
        text_lower = tweet['text'].lower()
        detected_keywords = [kw for kw in injury_keywords if kw in text_lower]
        
        if detected_keywords:
            print(f"   🚨 INJURY DETECTED in @{tweet['author']} tweet:")
            print(f"      Keywords: {', '.join(detected_keywords)}")
            
            # Extract player (simplified)
            if 'lebron' in text_lower:
                player = "LeBron James"
                status = "QUESTIONABLE" if 'questionable' in text_lower else "UNKNOWN"
            elif 'tatum' in text_lower:
                player = "Jayson Tatum"
                status = "OUT" if 're-evaluated' in text_lower else "UNKNOWN"
            else:
                player = "Unknown Player"
                status = "UNKNOWN"
            
            print(f"      Player: {player}")
            print(f"      Status: {status}")
            print(f"      Impact: {'⚠️ Monitor closely' if status == 'QUESTIONABLE' else '🚫 Likely out'}")
            print()

    print("4️⃣ Parlay Validation Integration:")
    print("""
    # This is how it integrates with parlay validation:
    
    def validate_parlay_before_bet(parlay_legs, game_time):
        # Only check for injuries 30-60 minutes before game
        time_until_game = game_time - datetime.now(timezone.utc)
        
        if timedelta(minutes=30) <= time_until_game <= timedelta(minutes=60):
            # Fetch latest injury tweets via Grok API
            recent_tweets = fetch_tweets_batch(...)
            
            # Check each player in the parlay
            for leg in parlay_legs:
                player_name = extract_player_from_bet(leg)
                injury_status = check_player_injury_status(player_name, recent_tweets)
                
                if injury_status == "OUT":
                    return "CANCEL_BET", f"{player_name} ruled out"
                elif injury_status == "QUESTIONABLE": 
                    return "REDUCE_STAKE", f"{player_name} questionable"
        
        return "PROCEED", "No injury concerns detected"
    """)

    print("5️⃣ Why This is Better Than Traditional Scraping:")
    advantages = [
        "✅ Real-time: Gets tweets within minutes of posting",
        "✅ Reliable: Uses official X/Twitter API through Grok",
        "✅ Filtered: Only gets tweets from verified NBA insiders",
        "✅ Structured: Returns clean JSON data, not HTML to parse",
        "✅ No breaking: Won't break when websites change layout"
    ]
    
    for advantage in advantages:
        print(f"   {advantage}")

def show_timing_analysis():
    """
    Explain why the previous demo was slow
    """
    print(f"\n⏱️  Timing Analysis - Why the Demo Was Slow:\n")
    
    timing_issues = [
        ("API Rate Limits", "X/Twitter limits requests to prevent abuse", "2-5 seconds per request"),
        ("Network Latency", "Real HTTP calls to Twitter servers", "1-3 seconds per call"),
        ("Search Parameters", "Processing 10+ handles with high result limits", "5-10 seconds total"),
        ("Continuous Loop", "Demo ran for 10 minutes checking every 2 minutes", "600 seconds total"),
        ("Error Handling", "API errors cause retries and delays", "10-30 seconds for errors")
    ]
    
    total_time = 0
    for issue, description, time_impact in timing_issues:
        print(f"   • {issue}: {description}")
        print(f"     Time Impact: {time_impact}")
        if "seconds" in time_impact and "-" in time_impact:
            avg_time = sum(map(int, time_impact.split()[0].split("-"))) / 2
            total_time += avg_time
        print()
    
    print(f"📊 Total Expected Time: ~{total_time} seconds ({total_time/60:.1f} minutes)")
    print("🚀 In production, this runs in background with cached results!")

if __name__ == "__main__":
    show_grok_api_usage()
    show_timing_analysis()
