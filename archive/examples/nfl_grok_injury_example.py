#!/usr/bin/env python3
"""
NFL Injury Monitoring with Grok API - Real Example

This shows how the Grok API works for NFL injury updates using real data
patterns from your NFL injury tweet dataset.
"""

import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

def demonstrate_nfl_grok_integration():
    """
    Show how Grok API integrates with NFL injury monitoring
    """
    print("🏈 NFL Injury Monitoring with Grok API\n")
    
    print("1️⃣ NFL Reporter Handles (from your dataset):")
    nfl_handles = [
        "AdamSchefter",     # ESPN Senior NFL Insider (in your data!)
        "RapSheet",         # Ian Rapoport - NFL Network
        "MikeGarafolo",     # NFL Network (in your data!)
        "CameronWolfe",     # NFL Network (in your data!)
        "FieldYates",       # ESPN NFL Insider
        "JayGlazer",        # Fox Sports NFL
        "TomPelissero",     # NFL Network
        "NFLInjuryNws",     # NFL Injury News (in your data!)
        "ProFootballDoc",   # Dr. David Chao - injury analysis
        "MySportsUpdate"    # Injury updates
    ]
    
    for handle in nfl_handles:
        print(f"   📱 @{handle}")
    
    print(f"\n2️⃣ Real NFL Injury Tweets (from your data):")
    
    # These are actual tweets from your dataset!
    real_nfl_injury_tweets = [
        {
            "author": "AdamSchefter",
            "text": "Dolphins RB De'Von Achane is dealing with a calf injury and likely will not practice this week",
            "timestamp": "Mon Aug 18 19:27:10 +0000 2025",
            "severity": "day-to-day"
        },
        {
            "author": "AdamSchefter", 
            "text": "For the Falcons' preseason finale Friday vs. the Cowboys, QB Emory Jones is in concussion protocol",
            "timestamp": "Mon Aug 18 14:42:28 +0000 2025",
            "severity": "protocol"
        },
        {
            "author": "MikeGarafolo",
            "text": "Kyle Shanahan says Dominick Puni has a possible PCL (knee) injury and might miss \"a few\" weeks",
            "timestamp": "Sat Aug 16 23:18:17 +0000 2025", 
            "severity": "weeks"
        },
        {
            "author": "CameronWolfe",
            "text": "Dolphins RB De'Von Achane has a soft tissue lower body injury that will keep him out between \"days & weeks\"",
            "timestamp": "Sat Aug 16 21:23:02 +0000 2025",
            "severity": "questionable"
        }
    ]
    
    print("   These are REAL tweets from your dataset:")
    for tweet in real_nfl_injury_tweets:
        print(f"   🚨 @{tweet['author']}: {tweet['text'][:80]}...")
        print(f"      Severity: {tweet['severity'].upper()}")
        print()
    
    print("3️⃣ How Grok API Fetches NFL Injuries:")
    print("""
    from tools.grok_tweet_fetcher import fetch_tweets_batch
    from xai_sdk import Client
    
    client = Client(api_key="your_xai_api_key")
    
    # Fetch recent NFL injury tweets
    nfl_tweets = fetch_tweets_batch(
        client=client,
        handles=["AdamSchefter", "RapSheet", "MikeGarafolo"],
        min_likes=10,           # NFL news gets high engagement  
        min_views=5000,         # Filter for important news
        from_date="2024-09-15T14:00:00Z",  # Game day - 2 hours
        to_date="2024-09-15T16:00:00Z",    # Game day kickoff
        max_search_results=25   # Stay under API limit
    )
    """)
    
    print("4️⃣ NFL-Specific Injury Detection:")
    
    # NFL injury keywords (more specific than NBA)
    nfl_injury_keywords = {
        'status': ['out', 'questionable', 'doubtful', 'probable', 'ruled out', 'inactive'],
        'injuries': ['concussion', 'protocol', 'knee', 'ankle', 'hamstring', 'shoulder', 
                    'groin', 'calf', 'back', 'hip', 'wrist', 'finger', 'ribs'],
        'severity': ['day-to-day', 'week-to-week', 'month-to-month', 'season-ending', 
                    'IR', 'PUP', 'NFI', 'reserve'],
        'positions': ['QB', 'RB', 'WR', 'TE', 'OL', 'DL', 'LB', 'CB', 'S', 'K', 'P']
    }
    
    def classify_nfl_injury(tweet_text):
        text_lower = tweet_text.lower()
        
        # Extract status
        status = "UNKNOWN"
        for s in nfl_injury_keywords['status']:
            if s in text_lower:
                status = s.upper()
                break
        
        # Extract injury type
        injury_type = "UNSPECIFIED"
        for inj in nfl_injury_keywords['injuries']:
            if inj in text_lower:
                injury_type = inj.upper()
                break
                
        # Extract position
        position = "UNKNOWN"
        for pos in nfl_injury_keywords['positions']:
            if f" {pos.lower()} " in text_lower or f" {pos} " in text_lower:
                position = pos
                break
        
        return {
            'status': status,
            'injury_type': injury_type, 
            'position': position,
            'fantasy_impact': get_fantasy_impact(position, status)
        }
    
    def get_fantasy_impact(position, status):
        high_impact_positions = ['QB', 'RB', 'WR', 'TE']
        if position in high_impact_positions:
            if status in ['OUT', 'RULED OUT']:
                return 'HIGH'
            elif status in ['QUESTIONABLE', 'DOUBTFUL']:
                return 'MEDIUM'
        return 'LOW'
    
    print(f"   Example NFL Injury Analysis:")
    for tweet in real_nfl_injury_tweets:
        analysis = classify_nfl_injury(tweet['text'])
        print(f"   📊 @{tweet['author']}:")
        print(f"      Status: {analysis['status']}")
        print(f"      Injury: {analysis['injury_type']}")
        print(f"      Position: {analysis['position']}")
        print(f"      Fantasy Impact: {analysis['fantasy_impact']}")
        print()

def show_nfl_parlay_integration():
    """
    Show how NFL injury monitoring integrates with parlay validation
    """
    print("5️⃣ NFL Parlay Validation Example:")
    
    # Sample NFL parlay (typical Sunday slate)
    nfl_parlay = {
        'game_time': datetime(2024, 9, 15, 17, 0, tzinfo=timezone.utc),  # 1 PM ET
        'legs': [
            {
                'player': 'De\'Von Achane',
                'team': 'Dolphins', 
                'market': 'Rushing Yards',
                'line': 'Over 75.5',
                'odds': -110
            },
            {
                'player': 'Jaylen Waddle',
                'team': 'Dolphins',
                'market': 'Receiving Yards', 
                'line': 'Over 60.5',
                'odds': -115
            },
            {
                'player': 'Tua Tagovailoa',
                'team': 'Dolphins',
                'market': 'Passing Yards',
                'line': 'Over 245.5', 
                'odds': -110
            }
        ]
    }
    
    print(f"   🎯 Sample NFL Parlay:")
    for leg in nfl_parlay['legs']:
        print(f"   • {leg['player']} ({leg['team']}) - {leg['market']} {leg['line']}")
    
    print(f"\n   🔍 Injury Validation (60 minutes before kickoff):")
    
    # Simulate injury check based on real tweets
    injury_alerts = [
        {
            'player': 'De\'Von Achane',
            'status': 'QUESTIONABLE',
            'injury': 'Calf',
            'source': '@AdamSchefter',
            'tweet': 'Dolphins RB De\'Von Achane is dealing with a calf injury and likely will not practice this week',
            'confidence': 0.85
        }
    ]
    
    for alert in injury_alerts:
        affected_legs = [leg for leg in nfl_parlay['legs'] if alert['player'] in leg['player']]
        
        if affected_legs:
            print(f"   ⚠️  INJURY ALERT:")
            print(f"      Player: {alert['player']}")
            print(f"      Status: {alert['status']}")
            print(f"      Injury: {alert['injury']}")
            print(f"      Source: {alert['source']}")
            print(f"      Confidence: {alert['confidence']:.0%}")
            
            # NFL-specific decision logic
            if alert['status'] == 'OUT':
                decision = "🚫 CANCEL parlay"
                reasoning = "Player ruled out"
            elif alert['status'] == 'QUESTIONABLE' and alert['confidence'] > 0.8:
                decision = "⚠️  REDUCE stake by 50%"
                reasoning = "High-confidence questionable status"
            elif alert['status'] == 'DOUBTFUL':
                decision = "🚫 CANCEL parlay"  
                reasoning = "Doubtful typically means out in NFL"
            else:
                decision = "✅ PROCEED with caution"
                reasoning = "Monitor pregame warmups"
            
            print(f"      Decision: {decision}")
            print(f"      Reasoning: {reasoning}")
            print()

def show_nfl_vs_nba_differences():
    """
    Highlight key differences between NFL and NBA injury monitoring
    """
    print("6️⃣ NFL vs NBA Injury Monitoring Differences:")
    
    differences = [
        {
            'aspect': 'Game Schedule',
            'nfl': 'Weekly games (mostly Sunday)',
            'nba': 'Daily games (82-game season)',
            'impact': 'NFL has longer injury assessment windows'
        },
        {
            'aspect': 'Injury Reports',
            'nfl': 'Official Wed/Thu/Fri reports required',
            'nba': 'Game-day injury reports',
            'impact': 'NFL more predictable, NBA more last-minute'
        },
        {
            'aspect': 'Position Impact',
            'nfl': 'QB injuries = massive impact',
            'nba': 'Star player injuries = major impact',
            'impact': 'NFL position-dependent, NBA star-dependent'
        },
        {
            'aspect': 'Injury Terminology',
            'nfl': 'Out/Doubtful/Questionable/Probable',
            'nba': 'Out/Questionable/Probable',
            'impact': 'NFL has more granular status levels'
        },
        {
            'aspect': 'Reporting Timeline',
            'nfl': '3-day injury report cycle',
            'nba': 'Same-day updates common',
            'impact': 'NFL allows more strategic planning'
        }
    ]
    
    for diff in differences:
        print(f"   📊 {diff['aspect']}:")
        print(f"      NFL: {diff['nfl']}")
        print(f"      NBA: {diff['nba']}")
        print(f"      Impact: {diff['impact']}")
        print()
    
    print("   🎯 Key Takeaway:")
    print("   The same Grok API works for both sports, but NFL allows for")
    print("   more strategic injury monitoring due to weekly schedule!")

if __name__ == "__main__":
    demonstrate_nfl_grok_integration()
    show_nfl_parlay_integration()
    show_nfl_vs_nba_differences()
