#!/usr/bin/env python3
"""
Enhanced Multi-Sport Tweet Scraper - JIRA-NFL-003
Extends Apify tweet scraper to support both NBA and NFL with sport-specific accounts and credibility scoring
"""

import os
import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import asyncio
from crawl4ai import AsyncWebCrawler

# NFL Accounts (from audit recommendation)
NFL_ACCOUNTS = [
    "AdamSchefter",
    "RapSheet", 
    "RotoWireNFL",
    "FantasyLabsNFL",
    "NFLInjuryNws"
]

# NBA Accounts (existing)
NBA_ACCOUNTS = [
    "ShamsCharania",
    "ChrisBHaynes", 
    "Rotoworld_BK",
    "FantasyLabsNBA",
    "InStreetClothes"
]

# Credibility scores for both sports
CREDIBILITY_SCORES = {
    # NFL accounts
    "AdamSchefter": 1.0,
    "RapSheet": 1.0,
    "RotoWireNFL": 0.8,
    "FantasyLabsNFL": 0.8,
    "NFLInjuryNws": 0.8,
    # NBA accounts (existing, unchanged)
    "ShamsCharania": 1.0,
    "ChrisBHaynes": 0.8,
    "Rotoworld_BK": 0.8,
    "FantasyLabsNBA": 0.8,
    "InStreetClothes": 0.7
}

class MultiSportTweetScraper:
    """Enhanced tweet scraper supporting both NBA and NFL"""
    
    def __init__(self):
        self.accounts = {
            "nba": NBA_ACCOUNTS,
            "nfl": NFL_ACCOUNTS
        }
        self.credibility_scores = CREDIBILITY_SCORES
        
    def calculate_timestamp_weight(self, timestamp_str: str, current_time: datetime) -> float:
        """Calculate weight based on recency (newer tweets have higher weight)"""
        try:
            tweet_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            days_old = (current_time - tweet_time).days
            
            # Weight decreases exponentially with age
            if days_old <= 1:
                return 1.0
            elif days_old <= 7:
                return 0.8
            elif days_old <= 30:
                return 0.6
            else:
                return 0.3
        except:
            return 0.5  # Default weight if parsing fails
    
    async def scrape_tweets(self, sport: str = "nba", max_tweets: int = 1000) -> List[Dict[str, Any]]:
        """
        Scrape tweets for specified sport with enhanced metadata
        
        Args:
            sport: "nba" or "nfl"
            max_tweets: Maximum tweets per account
            
        Returns:
            List of tweet dictionaries with sport-specific metadata
        """
        sport = sport.lower()
        if sport not in self.accounts:
            raise ValueError(f"Unsupported sport: {sport}. Use 'nba' or 'nfl'")
        
        accounts = self.accounts[sport]
        all_tweets = []
        
        print(f"🏀🏈 Scraping {sport.upper()} tweets from {len(accounts)} accounts...")
        
        async with AsyncWebCrawler() as crawler:
            for account in accounts:
                print(f"📱 Scraping @{account}...")
                url = f"https://x.com/{account}"
                
                try:
                    result = await crawler.arun(
                        url=url,
                        bypass_cache=True,
                        css_selector="article div[lang]",
                        max_elements=max_tweets
                    )
                    
                    if result.success and result.extracted_content:
                        current_time = datetime.now()
                        
                        for i, tweet in enumerate(result.extracted_content):
                            # Generate mock timestamp (in real implementation, extract from tweet)
                            mock_timestamp = (current_time - timedelta(days=i % 30)).strftime("%Y-%m-%d %H:%M:%S")
                            
                            tweet_data = {
                                "account": account,
                                "text": tweet.strip(),
                                "timestamp": mock_timestamp,
                                "timestamp_weight": self.calculate_timestamp_weight(mock_timestamp, current_time),
                                "author_credibility": self.credibility_scores.get(account, 0.5),
                                "sport": sport
                            }
                            all_tweets.append(tweet_data)
                        
                        print(f"✅ @{account}: {len(result.extracted_content)} tweets")
                    else:
                        print(f"⚠️ @{account}: No tweets found")
                        
                except Exception as e:
                    print(f"❌ @{account}: Error - {e}")
        
        # Save to CSV
        if all_tweets:
            df = pd.DataFrame(all_tweets)
            output_path = f"data/{sport}_tweets_dataset.csv"
            df.to_csv(output_path, index=False)
            print(f"💾 Saved {len(all_tweets)} tweets to {output_path}")
        
        return all_tweets
    
    def generate_sample_nfl_tweets(self) -> List[Dict[str, Any]]:
        """Generate sample NFL tweets for testing and training (until real scraping works)"""
        current_time = datetime.now()
        
        sample_tweets = [
            # Injury News
            {
                "account": "AdamSchefter",
                "text": "Chiefs QB Patrick Mahomes out 2-3 weeks with ankle sprain sustained in practice",
                "label": "injury_news",
                "timestamp": (current_time - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
                "sport": "nfl"
            },
            {
                "account": "RapSheet",
                "text": "Packers RB Aaron Jones day-to-day with knee soreness, expected to play Sunday",
                "label": "injury_news", 
                "timestamp": (current_time - timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S"),
                "sport": "nfl"
            },
            {
                "account": "NFLInjuryNws",
                "text": "Bills WR Stefon Diggs ruled OUT for Week 10 with hamstring injury",
                "label": "injury_news",
                "timestamp": (current_time - timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S"),
                "sport": "nfl"
            },
            
            # Lineup News
            {
                "account": "FantasyLabsNFL",
                "text": "Bills starting lineup: Allen, Diggs, Singletary, Knox confirmed for Sunday",
                "label": "lineup_news",
                "timestamp": (current_time - timedelta(hours=12)).strftime("%Y-%m-%d %H:%M:%S"),
                "sport": "nfl"
            },
            {
                "account": "RotoWireNFL",
                "text": "Eagles start Hurts at QB with Barkley getting bulk of RB carries",
                "label": "lineup_news",
                "timestamp": (current_time - timedelta(hours=15)).strftime("%Y-%m-%d %H:%M:%S"),
                "sport": "nfl"
            },
            {
                "account": "RapSheet",
                "text": "Cowboys expected to start Prescott, Elliott, Lamb in key divisional matchup",
                "label": "lineup_news",
                "timestamp": (current_time - timedelta(hours=18)).strftime("%Y-%m-%d %H:%M:%S"),
                "sport": "nfl"
            },
            
            # General Commentary
            {
                "account": "AdamSchefter",
                "text": "Cowboys defense has been exceptional despite Micah Parsons absence in recent games",
                "label": "general_commentary",
                "timestamp": (current_time - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
                "sport": "nfl"
            },
            {
                "account": "RapSheet",
                "text": "49ers run game thriving with Deebo Samuel's versatility and Christian McCaffrey's return",
                "label": "general_commentary",
                "timestamp": (current_time - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"),
                "sport": "nfl"
            },
            {
                "account": "NFLInjuryNws",
                "text": "Ravens offensive line showing remarkable improvement in pass protection metrics",
                "label": "general_commentary",
                "timestamp": (current_time - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S"),
                "sport": "nfl"
            },
            
            # Irrelevant
            {
                "account": "FantasyLabsNFL",
                "text": "Join our $5K NFL DFS contest this weekend! Sign up with promo code TOUCHDOWN",
                "label": "irrelevant",
                "timestamp": (current_time - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
                "sport": "nfl"
            },
            {
                "account": "RotoWireNFL",
                "text": "Check out our MLB playoff predictions and championship odds breakdown!",
                "label": "irrelevant",
                "timestamp": (current_time - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"),
                "sport": "nfl"
            },
            {
                "account": "NFLInjuryNws",
                "text": "Follow us on Instagram for exclusive behind-the-scenes content @nflinjurynews",
                "label": "irrelevant",
                "timestamp": (current_time - timedelta(days=4)).strftime("%Y-%m-%d %H:%M:%S"),
                "sport": "nfl"
            }
        ]
        
        # Add credibility scores and timestamp weights
        for tweet in sample_tweets:
            tweet["author_credibility"] = self.credibility_scores.get(tweet["account"], 0.5)
            tweet["timestamp_weight"] = self.calculate_timestamp_weight(tweet["timestamp"], current_time)
        
        return sample_tweets
    
    def create_nfl_training_dataset(self) -> str:
        """Create labeled NFL training dataset for RoBERTa fine-tuning"""
        sample_tweets = self.generate_sample_nfl_tweets()
        
        # Convert to DataFrame and save
        df = pd.DataFrame(sample_tweets)
        output_path = "data/nfl_tweets_labeled_training.csv"
        df.to_csv(output_path, index=False)
        
        print(f"📊 Created NFL training dataset with {len(sample_tweets)} labeled tweets")
        print(f"💾 Saved to {output_path}")
        
        # Print distribution
        label_counts = df['label'].value_counts()
        print(f"📈 Label distribution:")
        for label, count in label_counts.items():
            print(f"  {label}: {count}")
        
        return output_path


async def main():
    """Main function for testing the multi-sport tweet scraper"""
    scraper = MultiSportTweetScraper()
    
    print("🏈 JIRA-NFL-003: Multi-Sport Tweet Scraper")
    print("=" * 50)
    
    # Generate sample NFL training data
    print("\n1️⃣ Creating NFL Training Dataset...")
    training_file = scraper.create_nfl_training_dataset()
    
    # Test sport-specific account configuration
    print("\n2️⃣ Testing Sport-Specific Configuration...")
    print(f"NFL Accounts: {scraper.accounts['nfl']}")
    print(f"NBA Accounts: {scraper.accounts['nba']}")
    
    # Test credibility scoring
    print("\n3️⃣ Testing Credibility Scores...")
    for sport in ["nfl", "nba"]:
        print(f"\n{sport.upper()} Credibility Scores:")
        for account in scraper.accounts[sport]:
            score = scraper.credibility_scores.get(account, 0.5)
            print(f"  @{account}: {score}")
    
    print("\n✅ Multi-Sport Tweet Scraper configured successfully!")
    print("🎯 Ready for NFL tweet classification training")


if __name__ == "__main__":
    asyncio.run(main())
