import os
import json
import argparse
import csv
from pathlib import Path
from typing import List, Dict, Any

from apify_client import ApifyClient


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
            w.writerow(["id", "author", "timestamp", "text", "url", "favoriteCount", "retweetCount", "replyCount", "viewCount"])
        for r in rows:
            w.writerow([
                r.get("id"), r.get("author"), r.get("timestamp"), r.get("text"), r.get("url"),
                r.get("favoriteCount"), r.get("retweetCount"), r.get("replyCount"), r.get("viewCount"),
            ])


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape tweets via Apify Tweet Scraper using official client")
    parser.add_argument("--handles", nargs="*", default=[
        "wojespn", "ShamsCharania", "MarcJSpears", "ChrisBHaynes", "ZachLowe_NBA",
    ], help="X handles without @")
    parser.add_argument("--per-handle", type=int, default=1000, help="Requested tweets per handle")
    parser.add_argument("--actor-id", type=str, default="61RPP7dywgiy0JPD0", help="Apify actor ID")
    parser.add_argument("--lang", type=str, default="en")
    parser.add_argument("--sort", type=str, default="Latest", choices=["Latest", "Top"]) 
    parser.add_argument("--out-jsonl", type=str, default=str(Path("data/tweets/apify_tweets_v2.jsonl")))
    parser.add_argument("--out-csv", type=str, default=str(Path("data/tweets/apify_tweets_v2.csv")))
    parser.add_argument("--append", action="store_true")
    args = parser.parse_args()

    token = os.getenv("APIFY_TOKEN")
    if not token:
        raise SystemExit("APIFY_TOKEN not set in environment")

    # Initialize the ApifyClient
    client = ApifyClient(token)

    out_jsonl = Path(args.out_jsonl)
    out_csv = Path(args.out_csv) if args.out_csv else None

    seen_ids = set()
    total_saved = 0

    # Prepare the Actor input using the correct parameters
    run_input = {
        "twitterHandles": args.handles,  # Use twitterHandles instead of searchTerms
        "maxItems": len(args.handles) * args.per_handle,
        "sort": args.sort,
        "tweetLanguage": args.lang,
    }
    
    print(f"Starting Apify actor for handles: {', '.join(args.handles)}")
    print(f"Requesting {args.per_handle} tweets per handle ({len(args.handles) * args.per_handle} total)")
    
    # Run the Actor and wait for it to finish
    run = client.actor(args.actor_id).call(run_input=run_input)
    
    print(f"Actor run completed. Dataset ID: {run['defaultDatasetId']}")
    
    # Fetch and process results
    batch: List[Dict[str, Any]] = []
    items_count = 0
    
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        items_count += 1
        norm = normalize_item(item)
        
        # De-duplicate by id if present, else by (author, text)
        key = norm.get("id") or (norm.get("author"), norm.get("text"))
        if key in seen_ids:
            continue
        seen_ids.add(key)
        batch.append(norm)
        
        # Print first few items for debugging
        if items_count <= 3:
            print(f"Sample item {items_count}: {norm.get('author')} - {norm.get('text', '')[:100]}...")

    if batch:
        save_jsonl(batch, out_jsonl, append=args.append)
        if out_csv:
            save_csv(batch, out_csv, append=args.append)
        total_saved = len(batch)
        print(f"✅ Saved {total_saved} unique tweets")
    else:
        print("❌ No tweets found")

    print(f"Raw items processed: {items_count}")
    print(f"Unique tweets saved: {total_saved}")
    print(f"JSONL: {out_jsonl}")
    if out_csv:
        print(f"CSV: {out_csv}")


if __name__ == "__main__":
    main()
