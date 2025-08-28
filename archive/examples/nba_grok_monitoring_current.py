#!/usr/bin/env python3
"""
Current NBA Injury Monitoring Setup with Grok API

Shows exactly which accounts are monitored and how the system works for NBA.
"""

import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

def show_current_nba_setup():
    """
    Display the current NBA monitoring configuration
    """
    print("🏀 Current NBA Injury Monitoring with Grok API\n")
    
    print("1️⃣ NBA Accounts Currently Monitored:")
    
    # These are the exact handles from grok_tweet_fetcher.py
    current_nba_handles = [
        "ShamsCharania",    # The Athletic NBA insider  
        "wojespn",          # Adrian Wojnarowski - ESPN
        "Underdog__NBA",    # Underdog Fantasy NBA
        "NBABet",           # NBA betting insights
        "Rotoworld_BK",     # Rotoworld basketball
        "BobbyMarks42",     # ESPN salary cap expert
        "MarcJSpears"       # ESPN senior writer
    ]
    
    # Account details and why they're important
    account_details = {
        "ShamsCharania": {
            "name": "Shams Charania", 
            "outlet": "The Athletic",
            "role": "NBA Insider",
            "followers": "1.9M",
            "why_important": "Primary competitor to Woj, breaks major NBA news",
            "injury_focus": "High - reports all major injury news"
        },
        "wojespn": {
            "name": "Adrian Wojnarowski",
            "outlet": "ESPN", 
            "role": "Senior NBA Insider",
            "followers": "6.1M",
            "why_important": "Most trusted NBA reporter, breaks everything first",
            "injury_focus": "High - official injury reports and updates"
        },
        "Underdog__NBA": {
            "name": "Underdog Fantasy NBA",
            "outlet": "Underdog Fantasy",
            "role": "Fantasy/Betting Content",
            "followers": "127K",
            "why_important": "Fantasy-focused injury updates, lineup news",
            "injury_focus": "Medium - fantasy impact focused"
        },
        "NBABet": {
            "name": "NBA Bet",
            "outlet": "Independent",
            "role": "NBA Betting News",
            "followers": "45K", 
            "why_important": "Betting-specific injury news and implications",
            "injury_focus": "High - betting impact analysis"
        },
        "Rotoworld_BK": {
            "name": "Rotoworld Basketball",
            "outlet": "NBC Sports",
            "role": "Fantasy Basketball",
            "followers": "38K",
            "why_important": "Fantasy basketball updates and injury analysis", 
            "injury_focus": "High - detailed fantasy impact"
        },
        "BobbyMarks42": {
            "name": "Bobby Marks",
            "outlet": "ESPN",
            "role": "Salary Cap/Trade Expert",
            "followers": "511K",
            "why_important": "Salary cap implications of injuries, roster moves",
            "injury_focus": "Low - more focused on cap/trades"
        },
        "MarcJSpears": {
            "name": "Marc J. Spears", 
            "outlet": "ESPN",
            "role": "Senior NBA Writer",
            "followers": "673K",
            "why_important": "Veteran NBA reporter, good injury coverage",
            "injury_focus": "Medium - general NBA news including injuries"
        }
    }
    
    for handle in current_nba_handles:
        details = account_details[handle]
        print(f"   📱 @{handle}")
        print(f"      👤 {details['name']} - {details['outlet']}")
        print(f"      👥 {details['followers']} followers")
        print(f"      📝 {details['why_important']}")
        print(f"      🚨 Injury Focus: {details['injury_focus']}")
        print()

def show_missing_nba_accounts():
    """
    Show important NBA accounts that could be added
    """
    print("2️⃣ Important NBA Accounts NOT Currently Monitored:")
    
    missing_accounts = [
        {
            "handle": "TheSteinLine",
            "name": "Marc Stein",
            "outlet": "Substack/Independent", 
            "why_add": "Veteran NBA reporter, excellent injury analysis",
            "priority": "HIGH"
        },
        {
            "handle": "ChrisBHaynes", 
            "name": "Chris Haynes",
            "outlet": "TNT/Bleacher Report",
            "why_add": "Breaking news specialist, player relationships",
            "priority": "HIGH"
        },
        {
            "handle": "JaredWeissNBA",
            "name": "Jared Weiss", 
            "outlet": "The Athletic",
            "why_add": "The Athletic NBA writer, detailed injury reports",
            "priority": "MEDIUM"
        },
        {
            "handle": "WindhorstESPN",
            "name": "Brian Windhorst",
            "outlet": "ESPN",
            "why_add": "Senior ESPN reporter, LeBron/Lakers expert", 
            "priority": "MEDIUM"
        },
        {
            "handle": "NBAInjuryR3p0rt",
            "name": "NBA Injury Report",
            "outlet": "Independent",
            "why_add": "Dedicated NBA injury tracking account",
            "priority": "HIGH"
        },
        {
            "handle": "FantasyLabsNBA",
            "name": "FantasyLabs NBA",
            "outlet": "FantasyLabs", 
            "why_add": "DFS-focused injury analysis and projections",
            "priority": "MEDIUM"
        }
    ]
    
    for acc in missing_accounts:
        priority_emoji = "🔴" if acc["priority"] == "HIGH" else "🟡"
        print(f"   {priority_emoji} @{acc['handle']} ({acc['priority']} priority)")
        print(f"      👤 {acc['name']} - {acc['outlet']}")
        print(f"      ➕ Why add: {acc['why_add']}")
        print()

def show_nba_monitoring_parameters():
    """
    Show current monitoring parameters for NBA
    """
    print("3️⃣ Current NBA Monitoring Parameters:")
    
    params = {
        "min_likes": 10,
        "min_views": 5000,
        "max_search_results": 25,  # Fixed from the API error
        "target_count": 2000,
        "window_days": 7,
        "max_windows": 52
    }
    
    print(f"   📊 Current Settings:")
    for param, value in params.items():
        print(f"      • {param}: {value}")
    
    print(f"\n   🎯 What This Means:")
    print(f"      • Only tweets with 10+ likes and 5K+ views")
    print(f"      • Filters out low-engagement/spam content") 
    print(f"      • Focuses on tweets that got significant attention")
    print(f"      • 25 results max per API call (avoids rate limits)")
    
    print(f"\n   ⚡ Optimization Suggestions:")
    print(f"      • Lower min_likes to 5 for breaking injury news")
    print(f"      • Lower min_views to 2000 for faster injury detection")
    print(f"      • Add real-time mode with 15-minute windows")

def demonstrate_nba_injury_detection():
    """
    Show how NBA injury detection works with current setup
    """
    print("4️⃣ NBA Injury Detection Process:")
    
    print(f"   🔍 Step 1: Fetch tweets from monitored accounts")
    print(f"   🧠 Step 2: Filter for NBA injury keywords")
    print(f"   👤 Step 3: Extract player names and teams")
    print(f"   📊 Step 4: Classify injury severity") 
    print(f"   ⚠️  Step 5: Alert parlay system if needed")
    
    # NBA-specific keywords
    nba_keywords = {
        'injury_terms': [
            'injury', 'injured', 'out', 'questionable', 'probable',
            'ruled out', 'game-time decision', 'DNP', 'rest',
            'load management', 'sore', 'soreness', 'strain'
        ],
        'body_parts': [
            'ankle', 'knee', 'back', 'shoulder', 'wrist', 'finger',
            'hamstring', 'groin', 'calf', 'hip', 'foot', 'elbow'
        ],
        'severity_indicators': [
            'day-to-day', 'week-to-week', 'month-to-month',
            'season-ending', 'surgery', 'MRI', 'X-ray'
        ]
    }
    
    print(f"\n   🎯 NBA-Specific Keywords:")
    for category, keywords in nba_keywords.items():
        print(f"      • {category.replace('_', ' ').title()}: {len(keywords)} terms")
        print(f"        Examples: {', '.join(keywords[:5])}...")
        print()

def show_real_nba_examples():
    """
    Show realistic NBA injury monitoring examples
    """
    print("5️⃣ Realistic NBA Injury Scenarios:")
    
    scenarios = [
        {
            "time": "2 hours before Lakers vs Warriors",
            "tweet": "@wojespn: Lakers' LeBron James (ankle) listed as questionable for tonight vs Warriors. Will be game-time decision.",
            "grok_detection": {
                "player": "LeBron James",
                "team": "Lakers", 
                "injury": "ankle",
                "status": "questionable",
                "confidence": 0.95
            },
            "parlay_impact": "HIGH - LeBron props affected",
            "system_action": "🟡 Alert: Reduce LeBron prop stakes by 50%"
        },
        {
            "time": "30 minutes before Celtics vs Heat", 
            "tweet": "@ShamsCharania: Celtics star Jayson Tatum will not play tonight due to knee soreness, sources tell @TheAthletic.",
            "grok_detection": {
                "player": "Jayson Tatum",
                "team": "Celtics",
                "injury": "knee soreness", 
                "status": "out",
                "confidence": 0.98
            },
            "parlay_impact": "CRITICAL - Tatum props must be cancelled",
            "system_action": "🚫 Cancel: All Tatum-related parlays"
        },
        {
            "time": "90 minutes before Warriors vs Suns",
            "tweet": "@Underdog__NBA: Stephen Curry (wrist) is probable for tonight. No restrictions expected in warmups.",
            "grok_detection": {
                "player": "Stephen Curry",
                "team": "Warriors",
                "injury": "wrist",
                "status": "probable", 
                "confidence": 0.85
            },
            "parlay_impact": "LOW - Proceed with normal stakes",
            "system_action": "✅ Continue: Monitor warmups for confirmation"
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"   📱 Scenario {i}: {scenario['time']}")
        print(f"      Tweet: {scenario['tweet']}")
        print(f"      Detection:")
        for key, value in scenario['grok_detection'].items():
            print(f"        • {key}: {value}")
        print(f"      Impact: {scenario['parlay_impact']}")
        print(f"      Action: {scenario['system_action']}")
        print()

def show_nba_vs_current_data():
    """
    Compare NBA setup to existing data
    """
    print("6️⃣ NBA Setup vs Your Current Data:")
    
    print(f"   📂 Your Current Data Sources:")
    print(f"      • Apify scrapers - General NBA content")
    print(f"      • ESPN scrapers - Official injury reports") 
    print(f"      • ClutchPoints/The Ringer - News articles")
    print(f"      • Action Network - Betting content")
    
    print(f"\n   🚀 Grok API Adds:")
    print(f"      • Real-time Twitter monitoring (not just articles)")
    print(f"      • Direct insider access (Woj, Shams tweets)")
    print(f"      • Immediate injury updates (not waiting for articles)")
    print(f"      • Game-time decision monitoring")
    
    print(f"\n   ⚡ Speed Comparison:")
    print(f"      • Twitter/Grok: 0-5 minutes after injury")
    print(f"      • ESPN articles: 15-30 minutes after injury") 
    print(f"      • General news sites: 30-60 minutes after injury")
    
    print(f"\n   🎯 Perfect for NBA because:")
    print(f"      • NBA games daily = need real-time monitoring")
    print(f"      • Game-time decisions common = last-minute changes")
    print(f"      • Star-driven league = individual player injuries critical")

if __name__ == "__main__":
    show_current_nba_setup()
    show_missing_nba_accounts() 
    show_nba_monitoring_parameters()
    demonstrate_nba_injury_detection()
    show_real_nba_examples()
    show_nba_vs_current_data()
