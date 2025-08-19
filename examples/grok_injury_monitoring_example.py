#!/usr/bin/env python3
"""
Example: Real-time Injury Monitoring using Grok/X Live API

This demonstrates how the Grok API is used for real-time injury updates
in the NBA Parlay Project.
"""

import os
import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from dotenv import load_dotenv

# Import the Grok tweet fetcher
from tools.grok_tweet_fetcher import fetch_tweets_batch, _get_api_key


class RealTimeInjuryMonitor:
    """Example implementation of real-time injury monitoring using Grok API"""
    
    def __init__(self, api_key: str):
        from xai_sdk import Client
        self.client = Client(api_key=api_key)
        
        # NBA injury reporters and insiders
        self.nba_handles = [
            "ShamsCharania",    # The Athletic NBA insider
            "wojespn",          # ESPN Adrian Wojnarowski  
            "Underdog__NBA",    # Underdog Fantasy
            "NBABet",           # NBA betting insights
            "Rotoworld_BK",     # Rotoworld basketball
            "BobbyMarks42",     # ESPN cap expert
            "MarcJSpears",      # ESPN senior writer
            "TheSteinLine",     # Marc Stein
            "ChrisBHaynes",     # TNT/Bleacher Report
            "JaredWeissNBA"     # The Athletic
        ]
        
        # Track recent injury tweets
        self.recent_injuries: List[Dict[str, Any]] = []
        self.processed_tweets: set = set()
    
    def fetch_recent_injury_tweets(self, minutes_back: int = 30) -> List[Dict[str, Any]]:
        """
        Fetch tweets from the last N minutes looking for injury keywords
        """
        print(f"🔍 Fetching tweets from last {minutes_back} minutes...")
        
        # Calculate time window
        to_date = datetime.now(timezone.utc)
        from_date = to_date - timedelta(minutes=minutes_back)
        
        try:
            # Use the Grok API to fetch recent tweets
            tweets = fetch_tweets_batch(
                client=self.client,
                handles=self.nba_handles,
                min_likes=5,           # Lower threshold for faster injury news
                min_views=1000,        # Lower threshold for breaking news
                from_date=from_date.isoformat(),
                to_date=to_date.isoformat(),
                max_search_results=100  # Get more results for real-time monitoring
            )
            
            print(f"✅ Fetched {len(tweets)} tweets from Grok API")
            return tweets
            
        except Exception as e:
            print(f"❌ Error fetching tweets: {e}")
            return []
    
    def filter_injury_tweets(self, tweets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter tweets that likely contain injury information
        """
        injury_keywords = [
            'injury', 'injured', 'out', 'questionable', 'doubtful', 
            'ruled out', 'sidelined', 'strain', 'sprain', 'tear',
            'surgery', 'MRI', 'X-ray', 'ankle', 'knee', 'shoulder',
            'back', 'hamstring', 'groin', 'concussion', 'protocol',
            'day-to-day', 'week-to-week', 'month-to-month'
        ]
        
        injury_tweets = []
        
        for tweet in tweets:
            text = tweet.get('text', '').lower()
            tweet_id = f"{tweet.get('author')}_{tweet.get('timestamp')}_{text[:50]}"
            
            # Skip if already processed
            if tweet_id in self.processed_tweets:
                continue
                
            # Check for injury keywords
            if any(keyword in text for keyword in injury_keywords):
                injury_tweets.append(tweet)
                self.processed_tweets.add(tweet_id)
                print(f"🚨 INJURY DETECTED: @{tweet.get('author')}: {text[:100]}...")
        
        return injury_tweets
    
    def extract_player_info(self, tweet: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract player name and team from injury tweet (simplified example)
        """
        text = tweet.get('text', '')
        
        # Common NBA players for demo (in real implementation, use NLP/NER)
        player_patterns = {
            'LeBron James': ['lebron', 'james'],
            'Stephen Curry': ['curry', 'steph'],
            'Kevin Durant': ['durant', 'kd'],
            'Giannis Antetokounmpo': ['giannis', 'antetokounmpo'],
            'Jayson Tatum': ['tatum', 'jayson'],
            'Luka Doncic': ['luka', 'doncic'],
            'Kawhi Leonard': ['kawhi', 'leonard'],
            'Anthony Davis': ['anthony davis', 'ad'],
            'Jimmy Butler': ['butler', 'jimmy'],
            'Damian Lillard': ['lillard', 'dame']
        }
        
        text_lower = text.lower()
        detected_players = []
        
        for player, patterns in player_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                detected_players.append(player)
        
        return {
            'original_tweet': tweet,
            'detected_players': detected_players,
            'severity_keywords': self._extract_severity(text),
            'timestamp': tweet.get('timestamp'),
            'source': f"@{tweet.get('author')}"
        }
    
    def _extract_severity(self, text: str) -> List[str]:
        """Extract injury severity indicators"""
        text_lower = text.lower()
        severity_indicators = []
        
        if any(word in text_lower for word in ['out', 'ruled out', 'sidelined']):
            severity_indicators.append('OUT')
        if 'questionable' in text_lower:
            severity_indicators.append('QUESTIONABLE')
        if 'doubtful' in text_lower:
            severity_indicators.append('DOUBTFUL')
        if any(word in text_lower for word in ['day-to-day', 'probable']):
            severity_indicators.append('PROBABLE')
            
        return severity_indicators
    
    async def monitor_continuously(self, interval_minutes: int = 5, duration_minutes: int = 60):
        """
        Continuously monitor for injury updates
        """
        print(f"🔄 Starting continuous monitoring (check every {interval_minutes} min for {duration_minutes} min total)")
        
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        while datetime.now() < end_time:
            print(f"\n--- {datetime.now().strftime('%H:%M:%S')} Monitoring Cycle ---")
            
            # Fetch recent tweets
            tweets = self.fetch_recent_injury_tweets(minutes_back=interval_minutes * 2)
            
            # Filter for injury content
            injury_tweets = self.filter_injury_tweets(tweets)
            
            # Process each injury tweet
            for tweet in injury_tweets:
                injury_info = self.extract_player_info(tweet)
                
                if injury_info['detected_players']:
                    self.recent_injuries.append(injury_info)
                    
                    print(f"📊 INJURY ALERT:")
                    print(f"   Players: {', '.join(injury_info['detected_players'])}")
                    print(f"   Severity: {', '.join(injury_info['severity_keywords'])}")
                    print(f"   Source: {injury_info['source']}")
                    print(f"   Text: {injury_info['original_tweet']['text'][:150]}...")
                    print()
            
            if not injury_tweets:
                print("✅ No new injury tweets detected this cycle")
            
            # Wait before next check
            await asyncio.sleep(interval_minutes * 60)
        
        print(f"\n🏁 Monitoring complete. Total injuries detected: {len(self.recent_injuries)}")
        return self.recent_injuries


def demo_real_time_monitoring():
    """
    Demo function showing real-time injury monitoring
    """
    print("=== Grok API Real-Time Injury Monitoring Demo ===\n")
    
    # Load environment variables
    load_dotenv()
    
    try:
        # Get API key
        api_key = _get_api_key()
        print("✅ API key loaded")
        
        # Initialize monitor
        monitor = RealTimeInjuryMonitor(api_key)
        print("✅ Monitor initialized")
        
        # Example 1: One-time fetch
        print("\n1️⃣ ONE-TIME FETCH EXAMPLE:")
        tweets = monitor.fetch_recent_injury_tweets(minutes_back=60)
        injury_tweets = monitor.filter_injury_tweets(tweets)
        
        print(f"Found {len(injury_tweets)} potential injury tweets in last hour")
        for tweet in injury_tweets[:3]:  # Show first 3
            info = monitor.extract_player_info(tweet)
            print(f"   • @{tweet['author']}: {tweet['text'][:100]}...")
            if info['detected_players']:
                print(f"     Players: {', '.join(info['detected_players'])}")
        
        # Example 2: Short continuous monitoring 
        print(f"\n2️⃣ CONTINUOUS MONITORING EXAMPLE:")
        print("Starting 10-minute monitoring session (checking every 2 minutes)...")
        
        # Run continuous monitoring
        asyncio.run(monitor.monitor_continuously(
            interval_minutes=2,    # Check every 2 minutes
            duration_minutes=10    # Run for 10 minutes total
        ))
        
        # Show summary
        print(f"\n📋 MONITORING SUMMARY:")
        print(f"Total injury alerts: {len(monitor.recent_injuries)}")
        
        for i, injury in enumerate(monitor.recent_injuries[-5:], 1):  # Last 5
            print(f"{i}. {', '.join(injury['detected_players'])} - {injury['source']}")
            print(f"   Severity: {', '.join(injury['severity_keywords'])}")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        print("Make sure to set XAI_API_KEY in your environment or .env file")


def demo_integration_with_parlay_system():
    """
    Show how injury monitoring integrates with parlay validation
    """
    print("\n=== Integration with Parlay System ===\n")
    
    # Simulate a parlay that needs validation
    mock_parlay = {
        'legs': [
            {'player': 'LeBron James', 'market': 'points', 'line': 25.5, 'team': 'Lakers'},
            {'player': 'Stephen Curry', 'market': 'threes', 'line': 3.5, 'team': 'Warriors'},
            {'player': 'Jayson Tatum', 'market': 'rebounds', 'line': 7.5, 'team': 'Celtics'}
        ]
    }
    
    print("🎯 Mock Parlay to Validate:")
    for leg in mock_parlay['legs']:
        print(f"   • {leg['player']} ({leg['team']}) - {leg['market']} {leg['line']}")
    
    print(f"\n🔍 Checking for recent injuries...")
    
    # This would use the real Grok API in production
    mock_injury_data = [
        {
            'detected_players': ['LeBron James'],
            'severity_keywords': ['QUESTIONABLE'],
            'source': '@wojespn',
            'original_tweet': {'text': 'LeBron James (ankle) questionable for tonight vs Warriors'}
        }
    ]
    
    # Validate parlay against injuries
    for injury in mock_injury_data:
        affected_legs = []
        
        for leg in mock_parlay['legs']:
            if leg['player'] in injury['detected_players']:
                affected_legs.append(leg)
        
        if affected_legs:
            print(f"\n⚠️  INJURY ALERT AFFECTS PARLAY:")
            print(f"   Player: {', '.join(injury['detected_players'])}")
            print(f"   Status: {', '.join(injury['severity_keywords'])}")
            print(f"   Source: {injury['source']}")
            print(f"   Affected legs: {len(affected_legs)}")
            
            for leg in affected_legs:
                print(f"      • {leg['player']} - {leg['market']} {leg['line']}")
            
            # Decision logic
            if 'OUT' in injury['severity_keywords']:
                print(f"   🚫 RECOMMENDATION: CANCEL parlay (player ruled out)")
            elif 'QUESTIONABLE' in injury['severity_keywords']:
                print(f"   ⚠️  RECOMMENDATION: REDUCE stake or wait for more info")
            elif 'PROBABLE' in injury['severity_keywords']:
                print(f"   ✅ RECOMMENDATION: PROCEED with caution")


if __name__ == "__main__":
    # Run the demo
    demo_real_time_monitoring()
    demo_integration_with_parlay_system()
