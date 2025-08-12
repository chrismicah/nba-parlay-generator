import os
import time
import json
import argparse
import csv
from pathlib import Path
from typing import List, Dict, Any, Iterable

import requests


APIFY_ACTOR_ID_DEFAULT = "apidojo~tweet-scraper"
MAX_QUERIES_PER_RUN = 5  # Apify Tweet Scraper V2 limit


def chunked(items: List[str], size: int) -> Iterable[List[str]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def start_actor_run(token: str, actor_id: str, payload: Dict[str, Any]) -> str:
    url = f"https://api.apify.com/v2/acts/{actor_id}/runs?token={token}"
    resp = requests.post(url, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data["data"]["id"]


def poll_run_status(token: str, run_id: str, interval_sec: int = 8, timeout_sec: int = 1800) -> str:
    url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={token}"
    start = time.time()
    while True:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        status = resp.json()["data"]["status"]
        if status in {"SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"}:
            return status
        if time.time() - start > timeout_sec:
            return "TIMED-OUT"
        time.sleep(max(2, interval_sec))


def download_items(token: str, run_id: str) -> List[Dict[str, Any]]:
    url = f"https://api.apify.com/v2/actor-runs/{run_id}/dataset/items?token={token}"
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return resp.json()  # list of items


def normalize_item(raw: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": raw.get("id") or raw.get("tweetId"),
        "author": (raw.get("author", {}) or {}).get("userName") or raw.get("username"),
        "timestamp": raw.get("createdAt") or raw.get("date"),
        "text": raw.get("text"),
        "url": raw.get("url") or raw.get("tweetUrl"),
        "favoriteCount": raw.get("favoriteCount"),
        "retweetCount": raw.get("retweetCount"),
        "replyCount": raw.get("replyCount"),
        "viewCount": raw.get("viewCount"),
        "raw": raw,
    }


def save_jsonl(rows: List[Dict[str, Any]], path: Path, append: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append and path.exists() else "w"
    with open(path, mode, encoding="utf-8") as f:
        for r in rows:
            json.dump(r, f, ensure_ascii=False, default=str)
            f.write("\n")


def save_csv(rows: List[Dict[str, Any]], path: Path, append: bool) -> None:
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
    parser = argparse.ArgumentParser(description="Scrape tweets via Apify Tweet Scraper V2 in batches")
    parser.add_argument("--handles", nargs="*", default=[
        "wojespn", "ShamsCharania", "MarcJSpears", "ChrisBHaynes", "ZachLowe_NBA",
    ], help="X handles without @")
    parser.add_argument("--per-handle", type=int, default=1000, help="Requested tweets per handle")
    parser.add_argument("--actor-id", type=str, default=APIFY_ACTOR_ID_DEFAULT)
    parser.add_argument("--lang", type=str, default="en")
    parser.add_argument("--sort", type=str, default="Latest", choices=["Latest", "Top"]) 
    parser.add_argument("--out-jsonl", type=str, default=str(Path("data/tweets/apify_tweets.jsonl")))
    parser.add_argument("--out-csv", type=str, default=str(Path("data/tweets/apify_tweets.csv")))
    parser.add_argument("--append", action="store_true")
    parser.add_argument("--poll-interval", type=int, default=8)
    parser.add_argument("--poll-timeout", type=int, default=1800)
    args = parser.parse_args()

    token = os.getenv("APIFY_TOKEN")
    if not token:
        raise SystemExit("APIFY_TOKEN not set in environment")

    out_jsonl = Path(args.out_jsonl)
    out_csv = Path(args.out_csv) if args.out_csv else None

    seen_ids = set()
    total_saved = 0

    for group in chunked(args.handles, MAX_QUERIES_PER_RUN):
        search_terms = [f"from:{h}" for h in group]
        payload = {
            "searchTerms": search_terms,
            "tweetLanguage": args.lang,
            "sort": args.sort,
            "maxItems": len(group) * max(1, int(args.per_handle)),
        }
        print(f"Starting actor run for: {', '.join(group)}")
        run_id = start_actor_run(token, args.actor_id, payload)
        status = poll_run_status(token, run_id, interval_sec=args.poll_interval, timeout_sec=args.poll_timeout)
        print(f"Run {run_id} status: {status}")
        if status != "SUCCEEDED":
            continue
        items = download_items(token, run_id)
        norm = [normalize_item(it) for it in items]
        # de-dupe by id if present else by (author,text)
        batch: List[Dict[str, Any]] = []
        for r in norm:
            key = r.get("id") or (r.get("author"), r.get("text"))
            if key in seen_ids:
                continue
            seen_ids.add(key)
            batch.append(r)

        if not batch:
            continue
        save_jsonl(batch, out_jsonl, append=args.append or total_saved > 0)
        if out_csv:
            save_csv(batch, out_csv, append=args.append or total_saved > 0)
        total_saved += len(batch)
        print(f"Saved {len(batch)} tweets (total={total_saved})")

    print(f"✅ Done. Total saved: {total_saved}. JSONL: {out_jsonl}{' CSV: ' + str(out_csv) if out_csv else ''}")


if __name__ == "__main__":
    main()


