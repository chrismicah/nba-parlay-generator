# tools/tweet_scraper.py

import os
import csv
import ssl
import certifi
from datetime import datetime
from pathlib import Path
import snscrape.modules.twitter as sntwitter

# Configure SSL context
ssl_context = ssl.create_default_context(cafile=certifi.where())

OUTPUT_DIR = Path("data/tweets")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def scrape_tweets(keywords=None, usernames=None, since="2023-01-01", until=None, max_tweets=500, output_name="tweets"):
    """
    Scrape tweets using snscrape based on keywords or usernames.

    Args:
        keywords (list[str]): keywords to search for in tweets.
        usernames (list[str]): Twitter handles (without @).
        since (str): Start date (YYYY-MM-DD).
        until (str): End date (optional).
        max_tweets (int): Max tweets per query.
        output_name (str): CSV filename prefix.
    """
    queries = []

    if keywords:
        queries += [f'{kw} since:{since}' + (f' until:{until}' if until else '') for kw in keywords]

    if usernames:
        queries += [f'from:{user} since:{since}' + (f' until:{until}' if until else '') for user in usernames]

    all_tweets = []

    for query in queries:
        print(f"🔍 Scraping: {query}")
        try:
            scraper = sntwitter.TwitterSearchScraper(query)
            scraper._session.verify = certifi.where()  # Use certifi for SSL verification
            
            for i, tweet in enumerate(scraper.get_items()):
                if i >= max_tweets:
                    break
                all_tweets.append({
                    "id": tweet.id,
                    "date": tweet.date.strftime("%Y-%m-%d %H:%M:%S"),
                    "user": tweet.user.username,
                    "content": tweet.content,
                    "url": tweet.url
                })
        except Exception as e:
            print(f"⚠️ Error scraping query '{query}': {str(e)}")
            continue

    if not all_tweets:
        print("⚠️ No tweets found")
        return

    output_file = OUTPUT_DIR / f"{output_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    with open(output_file, "w", newline='', encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=all_tweets[0].keys())
        writer.writeheader()
        writer.writerows(all_tweets)

    print(f"✅ Scraped {len(all_tweets)} tweets → {output_file}")