import csv
import time
import random
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import re

import requests
from bs4 import BeautifulSoup


NITTER_HOSTS = [
    "https://nitter.net",
    "https://nitter.poast.org",
    "https://n.outercloud.com",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_page(
    session: requests.Session,
    host: str,
    user: str,
    cursor: Optional[str],
    use_jina: bool = False,
) -> Tuple[str, Optional[str]]:
    url = f"{host}/{user}"
    if cursor:
        url = f"{url}?cursor={cursor}"
    fetch_url = url
    if use_jina:
        inner = url.replace("https://", "http://")
        fetch_url = f"https://r.jina.ai/{inner}"
    resp = session.get(fetch_url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.text, url


def parse_tweets_and_cursor(html: str, user: str) -> Tuple[List[Dict], Optional[str]]:
    soup = BeautifulSoup(html, "html.parser")
    tweets: List[Dict] = []

    for item in soup.select("div.timeline-item, article.timeline-item"):
        content_el = item.select_one(".tweet-content") or item
        text = content_el.get_text(" ", strip=True)
        if not text:
            continue

        date_a = item.select_one("a.tweet-date")
        url = date_a.get("href") if date_a else None
        if url and url.startswith("/"):
            url = f"https://nitter.net{url}"
        ts = date_a.get("title") if date_a else None

        tweet_id: Optional[str] = None
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
                "timestamp": ts,
                "source": "nitter",
                "scrape_method": "requests",
            }
        )

    # Find "Load more" cursor
    next_cursor = None
    load_more = soup.find("a", href=True, string=lambda s: s and "Load more" in s)
    if load_more:
        href = load_more["href"]
        # href like: /USER?cursor=TOKEN
        if "cursor=" in href:
            next_cursor = href.split("cursor=", 1)[-1]

    return tweets, next_cursor


def parse_markdown_and_cursor(text: str, user: str) -> Tuple[List[Dict], Optional[str]]:
    tweets: List[Dict] = []
    lines = text.splitlines()
    last_text: Optional[str] = None
    status_re = re.compile(rf"https://nitter\.net/{re.escape(user)}/status/(\d+)")
    next_cursor: Optional[str] = None

    for i, line in enumerate(lines):
        if "[Load more](https://nitter.net/" in line and "cursor=" in line:
            try:
                href = line.split("(", 1)[1].split(")", 1)[0]
                if "cursor=" in href:
                    next_cursor = href.split("cursor=", 1)[-1]
            except Exception:
                pass
        m = status_re.search(line)
        if m:
            tid = m.group(1)
            text_buf: List[str] = []
            j = i - 1
            while j >= 0 and lines[j].strip() and not lines[j].strip().startswith("["):
                text_buf.append(lines[j].strip())
                j -= 1
            text_buf.reverse()
            content = " ".join(text_buf).strip() or (last_text or "")
            tweets.append(
                {
                    "id": tid,
                    "author": user,
                    "text": content,
                    "url": f"https://nitter.net/{user}/status/{tid}",
                    "timestamp": None,
                    "source": "nitter",
                    "scrape_method": "jina",
                }
            )
        if line.strip() and not line.strip().startswith("["):
            last_text = line.strip()

    return tweets, next_cursor


def write_csv_rows(csv_path: Path, rows: List[Dict]) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    write_header = not csv_path.exists()
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["id", "author", "text", "url", "timestamp", "source", "scrape_method"],
        )
        if write_header:
            w.writeheader()
        w.writerows(rows)


def scrape_user(
    user: str,
    max_tweets: int,
    out_dir: Path,
    delay_range: Tuple[float, float] = (0.7, 1.6),
    hosts: Optional[List[str]] = None,
    verbose: bool = False,
) -> int:
    session = requests.Session()
    session.headers.update(HEADERS)

    total = 0
    cursor: Optional[str] = None
    host_index = 0
    out_csv = out_dir / f"nitter_{user}.csv"
    seen_ids = set()
    hosts = hosts or NITTER_HOSTS

    while total < max_tweets:
        host = hosts[host_index % len(hosts)]
        host_index += 1
        try:
            html, url = fetch_page(session, host, user, cursor, use_jina=False)
            if verbose:
                print(f"FETCH {url}")
        except Exception:
            # rotate host and continue
            time.sleep(1.0)
            continue

        rows, next_cursor = parse_tweets_and_cursor(html, user)
        if not rows:
            # try jina fallback fetch and parse as markdown/text
            try:
                md_text, _ = fetch_page(session, host, user, cursor, use_jina=True)
                rows, next_cursor = parse_markdown_and_cursor(md_text, user)
                if verbose:
                    print("JINA fallback used")
            except Exception:
                pass
        new_rows: List[Dict] = []
        for r in rows:
            key = r.get("id") or (r.get("author"), r.get("text"))
            if key in seen_ids:
                continue
            seen_ids.add(key)
            new_rows.append(r)

        if new_rows:
            write_csv_rows(out_csv, new_rows)
            total += len(new_rows)
            if verbose:
                print(f"+{len(new_rows)} (total={total})")

        if not next_cursor:
            break
        cursor = next_cursor
        time.sleep(random.uniform(*delay_range))

    return total


def main() -> None:
    p = argparse.ArgumentParser(description="Scrape tweets from Nitter with pagination")
    p.add_argument("--account", required=True)
    p.add_argument("--max-tweets", type=int, default=1000)
    p.add_argument("--out-dir", type=str, default=str(Path("data/tweets")))
    p.add_argument("--host", type=str, help="Force a specific Nitter host, e.g., https://n.outercloud.com")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    hosts = [args.host] if args.host else None
    count = scrape_user(
        args.account,
        args.max_tweets,
        Path(args.out_dir),
        hosts=hosts,
        verbose=args.verbose,
    )
    print(f"✅ @{args.account}: scraped {count} tweets (target={args.max_tweets})")


if __name__ == "__main__":
    main()


