import os
import argparse
from pathlib import Path
from typing import List, Dict

import pandas as pd
import tweepy


DEFAULT_ACCOUNTS = [
    "ShamsCharania",
    "ChrisBHaynes",
    "Marc_DAmico",
    "Rotoworld_BK",
    "danbesbris",
    "Underdog__NBA",
    "SteveJonesJr",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Scrape tweets via the X (Twitter) API using Tweepy")
    p.add_argument(
        "--accounts",
        nargs="*",
        default=DEFAULT_ACCOUNTS,
        help="Handles to scrape (without @)",
    )
    p.add_argument(
        "--max-tweets",
        type=int,
        default=1000,
        help="Max tweets per account",
    )
    p.add_argument(
        "--out-csv",
        type=str,
        default=str(Path("data/tweets/nba_tweets_expanded_dataset.csv")),
        help="Output CSV path",
    )
    return p.parse_args()


def ensure_client() -> tweepy.Client:
    bearer = os.environ.get("TWITTER_BEARER_TOKEN")
    if not bearer:
        raise RuntimeError("TWITTER_BEARER_TOKEN not set in environment")
    # App-only bearer token is sufficient for recent tweets
    return tweepy.Client(bearer_token=bearer, wait_on_rate_limit=True)


def fetch_user_id(client: tweepy.Client, username: str) -> str:
    resp = client.get_user(username=username)
    if resp is None or resp.data is None:
        raise RuntimeError(f"User not found: {username}")
    return str(resp.data.id)


def fetch_tweets_for_user(client: tweepy.Client, user_id: str, username: str, max_tweets: int) -> List[Dict]:
    rows: List[Dict] = []
    pagination_token = None

    while len(rows) < max_tweets:
        resp = client.get_users_tweets(
            id=user_id,
            max_results=100,
            pagination_token=pagination_token,
            tweet_fields=["created_at", "lang", "public_metrics"],
            expansions=None,
            exclude=None,  # keep replies/retweets; adjust if needed
        )
        if resp is None or resp.data is None:
            break

        for t in resp.data:
            rows.append(
                {
                    "id": str(t.id),
                    "author": username,
                    "text": t.text,
                    "url": f"https://twitter.com/{username}/status/{t.id}",
                    "timestamp": t.created_at.isoformat() if getattr(t, "created_at", None) else None,
                    "source": "x_api",
                    "scrape_method": "tweepy",
                }
            )
            if len(rows) >= max_tweets:
                break

        pagination_token = resp.meta.get("next_token") if resp and hasattr(resp, "meta") else None
        if not pagination_token:
            break

    return rows


def main() -> None:
    args = parse_args()
    out_csv = Path(args.out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    client = ensure_client()

    all_rows: List[Dict] = []
    for username in args.accounts:
        try:
            print(f"🔍 API: @{username}")
            user_id = fetch_user_id(client, username)
            rows = fetch_tweets_for_user(client, user_id, username, args.max_tweets)
            print(f"  ↪️  {len(rows)} tweets")
            all_rows.extend(rows)
        except Exception as e:
            print(f"  ⚠️ API error for @{username}: {e}")

    if not all_rows:
        print("⚠️ No tweets collected. Nothing to save.")
        return

    df = pd.DataFrame(all_rows)
    # Deduplicate (id)
    if "id" in df.columns:
        df = df.drop_duplicates(subset=["id"])  # stable order
    df.to_csv(out_csv, index=False)
    print(f"✅ Saved {len(df)} rows → {out_csv}")


if __name__ == "__main__":
    main()



