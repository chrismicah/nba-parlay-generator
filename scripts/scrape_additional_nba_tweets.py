import asyncio
import argparse
import json
from pathlib import Path
from typing import List, Dict, Optional

import pandas as pd
from bs4 import BeautifulSoup
import certifi
from urllib.parse import urljoin
from datetime import datetime, timezone

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, VirtualScrollConfig

try:
    import snscrape.modules.twitter as sntwitter  # optional fallback
    HAS_SNSCRAPE = True
except Exception:
    HAS_SNSCRAPE = False


DEFAULT_ACCOUNTS = [
    "wojespn",
    "ChrisBHaynes",
    "Marc_DAmico",
    "Rotoworld_BK",
    "danbesbris",
    "Underdog__NBA",
    "SteveJonesJr",
]

NITTER_HOSTS = [
    "https://nitter.net",
    "https://nitter.poast.org",
    "https://ntrqq.to",
    "https://nitter.fprivacy.com",
    "https://n.outercloud.com",
]


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


async def _fetch_html(url: str, scrolls: int) -> str:
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url=url,
            config=CrawlerRunConfig(
                virtual_scroll_config=VirtualScrollConfig(
                    container_selector="body",
                    scroll_count=max(1, int(scrolls)),
                    scroll_by="window_height",
                )
            ),
        )
        # Prefer html; fallback to markdown if html missing
        html = getattr(result, "html", None)
        if html:
            return html
        return result.markdown or ""


def _parse_nitter_html(html: str, user: str, max_tweets: int) -> List[Dict]:
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("article.timeline-item, div.timeline-item") or []
    tweets: List[Dict] = []
    for item in items:
        if len(tweets) >= max_tweets:
            break
        content_el = item.select_one(".tweet-content") or item.select_one("blockquote") or item
        if not content_el:
            # Fall back to any paragraph-like text if needed
            content_el = item
        text = content_el.get_text(" ", strip=True)
        if not text:
            continue

        date_a = item.select_one("a.tweet-date")
        url: Optional[str] = None
        ts_raw: Optional[str] = None
        if date_a and date_a.get("href"):
            url = urljoin("https://nitter.net", date_a["href"])  # /user/status/ID
        if date_a and date_a.get("title"):
            ts_raw = date_a["title"]  # often like: "2025-01-05 12:34"

        tweet_id = None
        if url and "/status/" in url:
            try:
                tweet_id = url.rsplit("/", 1)[-1]
            except Exception:
                tweet_id = None

        tweets.append(
            {
                "id": tweet_id,
                "author": user,
                "text": text,
                "url": url,
                "timestamp": ts_raw,  # may be None; we will handle later
                "source": "nitter",
                "scrape_method": "crawl4ai",
            }
        )
    return tweets


def _parse_twitter_html_as_fallback(html: str, user: str, max_tweets: int) -> List[Dict]:
    # Twitter often blocks content without login; this is best-effort only
    soup = BeautifulSoup(html, "html.parser")
    # Extremely loose parsing: collect text blocks that look like tweets
    candidates = soup.select("article, div[role='article']") or soup.find_all("article")
    tweets: List[Dict] = []
    for art in candidates:
        if len(tweets) >= max_tweets:
            break
        text = art.get_text(" ", strip=True)
        if not text:
            continue
        tweets.append(
            {
                "id": None,
                "author": user,
                "text": text,
                "url": None,
                "timestamp": None,
                "source": "twitter",
                "scrape_method": "crawl4ai",
            }
        )
    return tweets


async def scrape_account_with_crawl4ai(user: str, max_tweets: int, scrolls: int) -> List[Dict]:
    # Prefer nitter to avoid login wall. Try multiple mirrors.
    for host in NITTER_HOSTS:
        try:
            nitter_url = f"{host}/{user}"
        except Exception:
            continue
        html = await _fetch_html(nitter_url, scrolls)
        tweets = _parse_nitter_html(html, user, max_tweets)
        if tweets:
            return tweets

    # Fallback to twitter.com best-effort
    twitter_url = f"https://twitter.com/{user}"
    html2 = await _fetch_html(twitter_url, scrolls)
    tw = _parse_twitter_html_as_fallback(html2, user, max_tweets)
    if tw:
        return tw

    # Final fallback: snscrape if available
    if HAS_SNSCRAPE:
        try:
            rows: List[Dict] = []
            query = f"from:{user}"
            scraper = sntwitter.TwitterSearchScraper(query)
            # Ensure SSL uses certifi bundle (mirrors tools/tweet_scraper.py)
            try:
                scraper._session.verify = certifi.where()
            except Exception:
                pass
            for i, tweet in enumerate(scraper.get_items()):
                if i >= max_tweets:
                    break
                rows.append(
                    {
                        "id": tweet.id,
                        "author": tweet.user.username,
                        "text": tweet.content,
                        "url": tweet.url,
                        "timestamp": tweet.date.strftime("%Y-%m-%d %H:%M:%S%z"),
                        "source": "snscrape",
                        "scrape_method": "snscrape",
                    }
                )
            if rows:
                return rows
        except Exception:
            pass

    return []


def _load_shams_from_json(json_path: Path) -> List[Dict]:
    if not json_path.exists():
        return []
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Normalize keys
        tweets: List[Dict] = []
        for t in data:
            tweets.append(
                {
                    "id": t.get("id") or t.get("tweet_id"),
                    "author": t.get("author") or "ShamsCharania",
                    "text": t.get("text") or t.get("content"),
                    "url": t.get("url"),
                    "timestamp": t.get("timestamp") or t.get("date"),
                    "source": t.get("source") or "json",
                    "scrape_method": t.get("scrape_method") or "x_api_or_unknown",
                }
            )
        return tweets
    except Exception:
        return []


def _fallback_scrape_shams_with_snscrape(max_tweets: int) -> List[Dict]:
    if not HAS_SNSCRAPE:
        return []
    tweets: List[Dict] = []
    query = f"from:ShamsCharania"
    try:
        for i, tweet in enumerate(sntwitter.TwitterSearchScraper(query).get_items()):
            if i >= max_tweets:
                break
            tweets.append(
                {
                    "id": tweet.id,
                    "author": tweet.user.username,
                    "text": tweet.content,
                    "url": tweet.url,
                    "timestamp": tweet.date.strftime("%Y-%m-%d %H:%M:%S%z"),
                    "source": "snscrape",
                    "scrape_method": "snscrape",
                }
            )
    except Exception:
        return []
    return tweets


def _coerce_timestamp(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    # Try multiple known formats; be permissive
    fmts = [
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S%z",
        "%a %b %d %H:%M:%S %z %Y",
        "%Y-%m-%d",
    ]
    for fmt in fmts:
        try:
            dt = datetime.strptime(ts, fmt)
            # If tz-naive, treat as UTC
            if not dt.tzinfo:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            continue
    return None


def _assign_timestamp_weights(df: pd.DataFrame) -> pd.DataFrame:
    now = _now_utc()
    times: List[Optional[datetime]] = []
    for ts in df["timestamp"].tolist():
        times.append(_coerce_timestamp(ts))

    # If many timestamps are missing (Crawl4AI limitations), assign mock recency order
    if all(t is None for t in times):
        # Newer accounts first in input order; within account, keep scraped order
        # Assign a simple decreasing weight from 1.0 down to ~0.1
        n = len(df)
        if n > 0:
            df["timestamp_weight"] = [max(0.1, 1.0 - i / max(10, n)) for i in range(n)]
        else:
            df["timestamp_weight"] = []
        return df

    weights: List[float] = []
    for t in times:
        if t is None:
            weights.append(0.5)  # neutral for missing
            continue
        days = (now - t).total_seconds() / 86400.0
        # Simple recency decay: recent => ~1.0, older => lower
        w = 1.0 / (1.0 + max(0.0, days) / 90.0)
        weights.append(float(w))
    df["timestamp_weight"] = weights
    return df


async def main_async(
    accounts: List[str], max_tweets: int, out_csv: Path, scrolls: int, shams_json_path: Path, mode: str
) -> None:
    all_rows: List[Dict] = []

    if mode == "snscrape":
        # Use snscrape for everything including Shams
        if not HAS_SNSCRAPE:
            print("❌ snscrape not available. Install snscrape to use --mode snscrape.")
            return
        for user in accounts:
            print(f"🔍 Scraping @{user} via snscrape …")
            try:
                rows: List[Dict] = []
                query = f"from:{user}"
                scraper = sntwitter.TwitterSearchScraper(query)
                try:
                    scraper._session.verify = certifi.where()
                except Exception:
                    pass
                for i, tweet in enumerate(scraper.get_items()):
                    if i >= max_tweets:
                        break
                    rows.append(
                        {
                            "id": tweet.id,
                            "author": tweet.user.username,
                            "text": tweet.content,
                            "url": tweet.url,
                            "timestamp": tweet.date.strftime("%Y-%m-%d %H:%M:%S%z"),
                            "source": "snscrape",
                            "scrape_method": "snscrape",
                        }
                    )
                print(f"  ↪️  {len(rows)} tweets scraped for @{user}")
                all_rows.extend(rows)
            except Exception as e:
                print(f"  ⚠️ snscrape error for @{user}: {e}")
    else:
        # Auto mode: use existing JSON for Shams or snscrape fallback, then crawl others
        shams_rows = _load_shams_from_json(shams_json_path)
        if not shams_rows:
            shams_rows = _fallback_scrape_shams_with_snscrape(max_tweets=max_tweets)
        if shams_rows:
            all_rows.extend(shams_rows)

        for user in accounts:
            if user.lower() == "shamscharania":
                continue
            print(f"🔍 Scraping @{user} via Crawl4AI/Nitter …")
            rows = await scrape_account_with_crawl4ai(user, max_tweets=max_tweets, scrolls=scrolls)
            print(f"  ↪️  {len(rows)} tweets scraped for @{user}")
            all_rows.extend(rows)

    if not all_rows:
        print("⚠️ No tweets collected. Nothing to save.")
        return

    # Build DataFrame and de-duplicate
    df = pd.DataFrame(all_rows)
    # Normalize columns
    expected_cols = ["id", "author", "text", "url", "timestamp", "source", "scrape_method"]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None

    # Deduplicate by id if present, else by (author, text)
    if df["id"].notna().any():
        df = df.sort_values(by=["author"], kind="stable").drop_duplicates(subset=["id"], keep="first")
    else:
        df = df.sort_values(by=["author"], kind="stable").drop_duplicates(subset=["author", "text"], keep="first")

    # Assign timestamp weights (with mock fallback)
    df = _assign_timestamp_weights(df)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)
    print(f"✅ Saved {len(df)} rows → {out_csv}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Scrape additional NBA tweets and build expanded dataset.")
    p.add_argument(
        "--accounts",
        nargs="*",
        default=DEFAULT_ACCOUNTS,
        help="Twitter handles to scrape (without @).",
    )
    p.add_argument(
        "--max-tweets",
        type=int,
        default=1000,
        help="Max tweets per account to collect.",
    )
    p.add_argument(
        "--scrolls",
        type=int,
        default=25,
        help="Virtual scroll passes per account page (Crawl4AI).",
    )
    p.add_argument(
        "--out-csv",
        type=str,
        default=str(Path("data/tweets/nba_tweets_expanded_dataset.csv")),
        help="Output CSV path.",
    )
    p.add_argument(
        "--shams-json",
        type=str,
        default=str(Path("data/tweets/shams_tweets.json")),
        help="Optional existing Shams tweets JSON to append.",
    )
    p.add_argument(
        "--mode",
        choices=["auto", "snscrape"],
        default="auto",
        help="Choose 'snscrape' to force snscrape for all accounts; 'auto' uses Crawl4AI/Nitter with snscrape fallback.",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    out_csv = Path(args.out_csv)
    shams_json = Path(args.shams_json)
    asyncio.run(
        main_async(
            accounts=list(args.accounts),
            max_tweets=int(args.max_tweets),
            out_csv=out_csv,
            scrolls=int(args.scrolls),
            shams_json_path=shams_json,
            mode=str(args.mode),
        )
    )


if __name__ == "__main__":
    main()


