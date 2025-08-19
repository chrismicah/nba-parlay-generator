#!/usr/bin/env python3
"""
Apify NFL Tweet Scraper - JIRA-NFL-003
Uses Apify API to scrape tweets from NFL accounts specified in the audit
"""

import os
import json
import argparse
import csv
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime, timedelta

from apify_client import ApifyClient

# NFL accounts from audit recommendation
NFL_ACCOUNTS = [
    "AdamSchefter",
    "RapSheet", 
    "RotoWireNFL",
    "FantasyLabsNFL",
    "NFLInjuryNws"
]

# NBA accounts (existing)
NBA_ACCOUNTS = [
    "wojespn", 
    "ShamsCharania", 
    "MarcJSpears", 
    "ChrisBHaynes", 
    "ZachLowe_NBA"
]

# Credibility scores
CREDIBILITY_SCORES = {
    # NFL accounts
    "AdamSchefter": 1.0,
    "RapSheet": 1.0,
    "RotoWireNFL": 0.8,
    "FantasyLabsNFL": 0.8,
    "NFLInjuryNws": 0.8,
    # NBA accounts
    "wojespn": 1.0,
    "ShamsCharania": 1.0,
    "MarcJSpears": 0.8,
    "ChrisBHaynes": 0.8,
    "ZachLowe_NBA": 0.8
}

def normalize_item(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Convert raw Apify tweet data to our standard format"""
    return {
        "id": raw.get("id") or raw.get("tweetId"),
        "author": (raw.get("author", {}) or {}).get("userName") or raw.get("username") or raw.get("handle"),
        "timestamp": raw.get("createdAt") or raw.get("date") or raw.get("timestamp"),
        "text": raw.get("text") or raw.get("full_text"),
        "url": raw.get("url") or raw.get("tweetUrl"),
        "favoriteCount": raw.get("favoriteCount") or raw.get("favorite_count"),
        "retweetCount": raw.get("retweetCount") or raw.get("retweet_count"),
        "replyCount": raw.get("replyCount") or raw.get("reply_count"),
        "viewCount": raw.get("viewCount") or raw.get("view_count"),
        "raw": raw,
    }

def enhance_with_metadata(tweet: Dict[str, Any], sport: str) -> Dict[str, Any]:
    """Add sport-specific metadata to tweet"""
    author = tweet.get("author", "")
    
    enhanced = tweet.copy()
    enhanced.update({
        "sport": sport,
        "author_credibility": CREDIBILITY_SCORES.get(author, 0.5),
        "timestamp_weight": calculate_timestamp_weight(tweet.get("timestamp", "")),
        "scraped_at": datetime.now().isoformat()
    })
    
    return enhanced

def calculate_timestamp_weight(timestamp_str: str) -> float:
    """Calculate weight based on tweet recency"""
    try:
        # Try different timestamp formats
        formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ", 
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d"
        ]
        
        tweet_time = None
        for fmt in formats:
            try:
                tweet_time = datetime.strptime(timestamp_str, fmt)
                break
            except:
                continue
        
        if not tweet_time:
            return 0.5
            
        days_old = (datetime.now() - tweet_time).days
        
        if days_old <= 1:
            return 1.0
        elif days_old <= 7:
            return 0.8
        elif days_old <= 30:
            return 0.6
        else:
            return 0.3
    except:
        return 0.5

def save_jsonl(rows: List[Dict[str, Any]], path: Path, append: bool) -> None:
    """Save data to JSONL format"""
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append and path.exists() else "w"
    with open(path, mode, encoding="utf-8") as f:
        for r in rows:
            json.dump(r, f, ensure_ascii=False, default=str)
            f.write("\n")

def save_csv(rows: List[Dict[str, Any]], path: Path, append: bool) -> None:
    """Save data to CSV format"""
    if not path:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not append or not path.exists()
    mode = "a" if append and path.exists() else "w"
    with open(path, mode, newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow([
                "id", "author", "timestamp", "text", "url", "favoriteCount", 
                "retweetCount", "replyCount", "viewCount", "sport", 
                "author_credibility", "timestamp_weight", "scraped_at"
            ])
        for r in rows:
            w.writerow([
                r.get("id"), r.get("author"), r.get("timestamp"), r.get("text"), 
                r.get("url"), r.get("favoriteCount"), r.get("retweetCount"), 
                r.get("replyCount"), r.get("viewCount"), r.get("sport"),
                r.get("author_credibility"), r.get("timestamp_weight"), r.get("scraped_at")
            ])

def scrape_nfl_tweets_apify(per_handle: int = 1000, actor_id: str = "61RPP7dywgiy0JPD0") -> List[Dict[str, Any]]:
    """Scrape NFL tweets using Apify API"""
    
    token = os.getenv("APIFY_TOKEN")
    if not token:
        raise SystemExit("❌ APIFY_TOKEN not set in environment")
    
    # Initialize the ApifyClient
    client = ApifyClient(token)
    
    print(f"🏈 Scraping NFL tweets from {len(NFL_ACCOUNTS)} accounts...")
    print(f"📱 Accounts: {', '.join(['@' + acc for acc in NFL_ACCOUNTS])}")
    
    # Prepare the Actor input
    run_input = {
        "twitterHandles": NFL_ACCOUNTS,
        "maxItems": len(NFL_ACCOUNTS) * per_handle,
        "sort": "Latest",
        "tweetLanguage": "en",
    }
    
    print(f"🚀 Starting Apify actor {actor_id}...")
    print(f"📊 Requesting {per_handle} tweets per handle ({len(NFL_ACCOUNTS) * per_handle} total)")
    
    # Run the Actor and wait for it to finish
    try:
        run = client.actor(actor_id).call(run_input=run_input)
        print(f"✅ Actor run completed. Dataset ID: {run['defaultDatasetId']}")
    except Exception as e:
        print(f"❌ Apify actor failed: {e}")
        return []
    
    # Fetch and process results
    seen_ids = set()
    all_tweets = []
    items_count = 0
    
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        items_count += 1
        norm = normalize_item(item)
        
        # De-duplicate by id if present, else by (author, text)
        key = norm.get("id") or (norm.get("author"), norm.get("text"))
        if key in seen_ids:
            continue
        seen_ids.add(key)
        
        # Add NFL-specific metadata
        enhanced = enhance_with_metadata(norm, "nfl")
        all_tweets.append(enhanced)
        
        # Print first few items for debugging
        if items_count <= 3:
            text = enhanced.get('text') or ''
            author = enhanced.get('author') or 'Unknown'
            credibility = enhanced.get('author_credibility', 0.0)
            print(f"📝 Sample {items_count}: @{author} (credibility: {credibility}) - {text[:80]}...")
    
    print(f"🔢 Raw items processed: {items_count}")
    print(f"🎯 Unique NFL tweets: {len(all_tweets)}")
    
    return all_tweets

def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape NFL tweets via Apify API")
    parser.add_argument("--sport", choices=["nfl", "nba"], default="nfl", help="Sport to scrape")
    parser.add_argument("--per-handle", type=int, default=1000, help="Requested tweets per handle")
    parser.add_argument("--actor-id", type=str, default="61RPP7dywgiy0JPD0", help="Apify actor ID")
    parser.add_argument("--out-jsonl", type=str, default="data/tweets/nfl_apify_tweets.jsonl")
    parser.add_argument("--out-csv", type=str, default="data/tweets/nfl_apify_tweets.csv")
    parser.add_argument("--append", action="store_true", help="Append to existing files")
    args = parser.parse_args()

    # Select accounts based on sport
    if args.sport == "nfl":
        accounts = NFL_ACCOUNTS
        tweets = scrape_nfl_tweets_apify(args.per_handle, args.actor_id)
    else:
        accounts = NBA_ACCOUNTS
        # Use existing NBA logic (would need to implement)
        print("NBA scraping not implemented in this script")
        return

    if tweets:
        out_jsonl = Path(args.out_jsonl)
        out_csv = Path(args.out_csv) if args.out_csv else None
        
        # Save results
        save_jsonl(tweets, out_jsonl, append=args.append)
        if out_csv:
            save_csv(tweets, out_csv, append=args.append)
        
        print(f"💾 Saved {len(tweets)} tweets")
        print(f"📄 JSONL: {out_jsonl}")
        if out_csv:
            print(f"📊 CSV: {out_csv}")
        
        # Show credibility distribution
        credibility_dist = {}
        for tweet in tweets:
            cred = tweet.get('author_credibility', 0.0)
            author = tweet.get('author', 'Unknown')
            if author not in credibility_dist:
                credibility_dist[author] = {'count': 0, 'credibility': cred}
            credibility_dist[author]['count'] += 1
        
        print(f"\n📊 Author Distribution:")
        for author, data in credibility_dist.items():
            print(f"  @{author}: {data['count']} tweets (credibility: {data['credibility']})")
    else:
        print("❌ No tweets retrieved")

if __name__ == "__main__":
    main()
