#!/usr/bin/env python3
"""
Specialized NFL Injury Tweet Scraper using Apify API
Targets specific NFL injury and news accounts with optimized parameters
"""

import os
import pandas as pd
from apify_client import ApifyClient
import argparse
from datetime import datetime
import json

class NFLInjuryTweetScraper:
    def __init__(self):
        self.apify_token = os.getenv("APIFY_TOKEN")
        if not self.apify_token:
            raise ValueError("APIFY_TOKEN not found in environment variables")
        
        self.client = ApifyClient(self.apify_token)
        
        # NFL injury-focused accounts with credibility scores
        self.injury_accounts = {
            'NFLInjuryNws': 1.0,      # Primary injury news
            'AdamSchefter': 1.0,       # Top NFL insider
            'RapSheet': 1.0,           # Ian Rapoport  
            'MikeGarafolo': 0.9,       # NFL Network insider
            'ESPNNFL': 0.8,            # ESPN NFL
            'NFL': 0.7,                # Official NFL
            'NFLNetwork': 0.8,         # NFL Network
            'FieldYates': 0.8,         # ESPN insider
            'ProFootballTalk': 0.7,    # PFT
            'CBSSportsNFL': 0.7,       # CBS Sports
        }
        
        # Team accounts (lower priority for injury news)
        self.team_accounts = {
            'Chiefs': 0.6,
            'Bengals': 0.6,
            'packers': 0.6,
            'dallascowboys': 0.6,
            'Browns': 0.6,
            'steelers': 0.6,
            'ravens': 0.6,
            'patriots': 0.6
        }
    
    def scrape_injury_accounts(self, max_tweets_per_account=2000, include_teams=False):
        """Scrape NFL injury-focused accounts"""
        print("🏥 Starting NFL Injury Tweet Scraping...")
        
        # Choose accounts to scrape
        accounts_to_scrape = list(self.injury_accounts.keys())
        if include_teams:
            accounts_to_scrape.extend(list(self.team_accounts.keys()))
        
        print(f"   Targeting {len(accounts_to_scrape)} accounts:")
        for account in accounts_to_scrape:
            credibility = self.injury_accounts.get(account, self.team_accounts.get(account, 0.5))
            print(f"     @{account} (credibility: {credibility})")
        
        # Run Apify actor with optimized settings for injury content
        run_input = {
            "handles": accounts_to_scrape,
            "tweetsDesired": max_tweets_per_account,
            "proxyConfig": {"useApifyProxy": True},
            "language": "en",
            "searchTerms": ["injury", "injured", "IR", "out", "questionable", "doubtful", "ruled out", "status"],
            "sort": "Latest",
            "tweetLanguage": "en",
            "includeSearchTerms": False,  # Don't restrict to only search terms
            "maxRequestRetries": 3,
            "maxTweetsPerQuery": max_tweets_per_account
        }
        
        print(f"   Requesting up to {max_tweets_per_account} tweets per account...")
        print(f"   Total target: {len(accounts_to_scrape) * max_tweets_per_account:,} tweets")
        
        try:
            # Run the Twitter scraper actor
            run = self.client.actor("61RPP7dywgiy0JPD0").call(run_input=run_input)
            
            # Get results
            results = []
            for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
                # Add credibility score and sport tag
                credibility = self.injury_accounts.get(item.get('author', ''), 
                                                     self.team_accounts.get(item.get('author', ''), 0.5))
                item['credibility_score'] = credibility
                item['sport'] = 'nfl'
                item['scraped_at'] = datetime.now().isoformat()
                results.append(item)
            
            print(f"   ✅ Collected {len(results)} tweets")
            return results
            
        except Exception as e:
            print(f"   ❌ Error during scraping: {e}")
            return []
    
    def filter_injury_related(self, tweets):
        """Filter tweets for injury-related content"""
        print("🔍 Filtering for injury-related content...")
        
        injury_keywords = [
            'injury', 'injured', 'hurt', 'pain', 'strain', 'sprain',
            'ir', 'injured reserve', 'pup', 'physically unable',
            'out', 'ruled out', 'questionable', 'doubtful', 'probable',
            'status', 'update', 'designated to return', 'activated',
            'knee', 'ankle', 'shoulder', 'hamstring', 'groin', 'back',
            'concussion', 'head', 'neck', 'wrist', 'hip', 'foot',
            'surgery', 'mri', 'scan', 'x-ray', 'rehab', 'recovery',
            'week-to-week', 'day-to-day', 'limited', 'full practice',
            'dnp', 'did not practice', 'rest day', 'maintenance'
        ]
        
        injury_tweets = []
        for tweet in tweets:
            text = tweet.get('text', '').lower()
            if any(keyword in text for keyword in injury_keywords):
                tweet['injury_related'] = True
                injury_tweets.append(tweet)
            else:
                tweet['injury_related'] = False
        
        print(f"   ✅ Found {len(injury_tweets)} injury-related tweets out of {len(tweets)} total")
        return injury_tweets
    
    def save_results(self, tweets, output_file='data/tweets/nfl_injury_tweets_enhanced.csv'):
        """Save results to CSV and JSONL"""
        if not tweets:
            print("   ⚠️  No tweets to save")
            return
        
        # Create DataFrame
        df = pd.DataFrame(tweets)
        
        # Clean and organize columns
        columns_order = [
            'id', 'author', 'timestamp', 'text', 'url', 
            'favoriteCount', 'retweetCount', 'replyCount', 'viewCount',
            'credibility_score', 'sport', 'injury_related', 'scraped_at'
        ]
        
        # Ensure all columns exist
        for col in columns_order:
            if col not in df.columns:
                df[col] = None
        
        df = df[columns_order]
        
        # Save CSV
        df.to_csv(output_file, index=False)
        
        # Save JSONL
        jsonl_file = output_file.replace('.csv', '.jsonl')
        df.to_json(jsonl_file, orient='records', lines=True)
        
        print(f"   ✅ Saved {len(df)} tweets to:")
        print(f"      CSV: {output_file}")
        print(f"      JSONL: {jsonl_file}")
        
        # Print summary statistics
        print(f"\n📊 Collection Summary:")
        print(f"   Total tweets: {len(df)}")
        print(f"   Injury-related: {df['injury_related'].sum()}")
        print(f"   Account distribution:")
        account_counts = df['author'].value_counts().head(10)
        for account, count in account_counts.items():
            credibility = df[df['author'] == account]['credibility_score'].iloc[0]
            print(f"     @{account}: {count} tweets (credibility: {credibility})")
        
        return output_file

def main():
    parser = argparse.ArgumentParser(description="NFL Injury Tweet Scraper")
    parser.add_argument('--max-tweets', type=int, default=1500, 
                       help='Maximum tweets per account')
    parser.add_argument('--include-teams', action='store_true', 
                       help='Include team accounts')
    parser.add_argument('--output', type=str, 
                       default='data/tweets/nfl_injury_tweets_enhanced.csv',
                       help='Output file path')
    parser.add_argument('--filter-only', action='store_true',
                       help='Only filter for injury content, get all tweets')
    
    args = parser.parse_args()
    
    try:
        scraper = NFLInjuryTweetScraper()
        
        # Scrape tweets
        tweets = scraper.scrape_injury_accounts(
            max_tweets_per_account=args.max_tweets,
            include_teams=args.include_teams
        )
        
        if not tweets:
            print("❌ No tweets collected")
            return
        
        # Filter for injury content if requested
        if not args.filter_only:
            injury_tweets = scraper.filter_injury_related(tweets)
            final_tweets = injury_tweets if injury_tweets else tweets
        else:
            final_tweets = tweets
        
        # Save results
        output_file = scraper.save_results(final_tweets, args.output)
        
        print(f"\n🎉 NFL injury tweet scraping complete!")
        print(f"   Output saved to: {output_file}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
