import os
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional, Iterable, Tuple
from datetime import datetime, timezone, timedelta
import asyncio

from dotenv import load_dotenv

# Predefined account lists for sports
NFL_HANDLES = [
    "AdamSchefter",     # ESPN Senior NFL Insider 
    "RapSheet",         # Ian Rapoport - NFL Network
    "MikeGarafolo",     # NFL Network
    "CameronWolfe",     # NFL Network
    "NFLInjuryNws",     # NFL Injury News
    "TomPelissero",     # NFL Network
    "JayGlazer",        # Fox Sports NFL
    "ProFootballDoc",   # Dr. David Chao - injury analysis
    "FieldYates"        # ESPN NFL Insider
]

NBA_HANDLES = [
    "ShamsCharania",    # The Athletic NBA insider
    "TheSteinLine",     # Marc Stein - Substack/Independent
    "ChrisBHaynes",     # TNT/Bleacher Report
    "Underdog__NBA",    # Underdog Fantasy NBA
    "NBABet",           # NBA betting insights
    "Rotoworld_BK",     # Rotoworld basketball
    "MarcJSpears",      # ESPN senior writer
    "NBAInjuryR3p0rt",  # NBA Injury Report
    "FantasyLabsNBA",   # FantasyLabs NBA
    "WindhorstESPN"     # Brian Windhorst - ESPN
]

# Sport-specific prompt templates
SPORT_PROMPTS = {
    "nfl": "Show recent tweets related to NFL injuries, inactives, injury reports, or roster moves.",
    "nba": "Show recent tweets related to NBA injuries, lineups, or player availability updates.",
    "general": "Show recent tweets related to sports injuries or lineup updates."
}


def _get_api_key() -> str:
    # Primary: XAI_API_KEY; Fallback: twitter_key (per user's naming)
    value = os.getenv("XAI_API_KEY") or os.getenv("twitter_key")
    if not value:
        print("❌ Missing API key. Set XAI_API_KEY (or twitter_key) in environment or .env", file=sys.stderr)
        sys.exit(1)
    return value


def get_sport_handles(sport: str) -> List[str]:
    """Get predefined handles for a specific sport."""
    sport_lower = sport.lower()
    if sport_lower == "nfl":
        return NFL_HANDLES
    elif sport_lower == "nba":
        return NBA_HANDLES
    else:
        return NFL_HANDLES + NBA_HANDLES  # Return all for general use


def fetch_tweets_from_handle(
    client: Any,
    handle: str,
    min_likes: int = 10,
    min_views: int = 5000,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    sport: str = "general",
) -> Dict[str, Any]:
    # Lazy imports to avoid hard dependency if xai-sdk is not installed yet
    from xai_sdk.chat import user
    from xai_sdk.search import SearchParameters, x_source

    chat = client.chat.create(
        model="grok-4",
        search_parameters=SearchParameters(
            mode="on",
            sources=[
                x_source(
                    included_x_handles=[handle],
                    post_favorite_count=min_likes,
                    post_view_count=min_views,
                )
            ],
            from_date=from_date,
            to_date=to_date,
        ),
    )

    # Use sport-specific prompt
    prompt = SPORT_PROMPTS.get(sport.lower(), SPORT_PROMPTS["general"])
    chat.append(user(f"Show recent tweets from @{handle}. {prompt}"))
    response = chat.sample()

    # Normalize output to JSON-serializable primitives
    content = getattr(response, "content", None)
    if not isinstance(content, (str, int, float, bool)):
        try:
            # Some SDK objects expose model_dump_json
            content = getattr(content, "model_dump", lambda: str(content))()
        except Exception:
            content = str(content)

    citations = getattr(response, "citations", None)
    if citations is None:
        citations_list: Optional[List[str]] = None
    else:
        try:
            citations_list = [str(c) for c in list(citations)]
        except Exception:
            citations_list = [str(citations)]

    return {
        "handle": handle,
        "content": content,
        "citations": citations_list,
    }


def _chunked(seq: List[str], size: int) -> Iterable[List[str]]:
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    try:
        # Accept YYYY-MM-DD or full ISO; make timezone-aware UTC
        dt = datetime.fromisoformat(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def fetch_tweets_batch(
    client: Any,
    handles: List[str],
    min_likes: int = 0,
    min_views: int = 0,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    max_search_results: int = 50,
    sport: str = "general",
) -> List[Dict[str, Any]]:
    """Fetch raw tweets for up to 10 handles at once. Returns list of tweet dicts.

    The response is requested as JSON only, containing array of objects with
    keys: author, timestamp, text, url, likes, views (when available).
    """
    from xai_sdk.chat import user
    from xai_sdk.search import SearchParameters, x_source

    batched: List[Dict[str, Any]] = []

    # Build x_source with included_x_handles (max 10 per request)
    source = x_source(
        included_x_handles=handles,
        post_favorite_count=min_likes if min_likes else None,
        post_view_count=min_views if min_views else None,
    )

    # Coerce date strings to datetime objects per SDK expectation
    from_dt = _parse_date(from_date)
    to_dt = _parse_date(to_date)

    chat = client.chat.create(
        model="grok-4",
        search_parameters=SearchParameters(
            mode="on",
            sources=[source],
            from_date=from_dt,
            to_date=to_dt,
            max_search_results=max_search_results,
        ),
    )

    # Use sport-specific prompt
    sport_prompt = SPORT_PROMPTS.get(sport.lower(), SPORT_PROMPTS["general"])
    instruction = (
        f"Return JSON only. No prose. {sport_prompt} "
        "Format as an array of objects. Each object must have "
        "keys: author, timestamp, text, url, likes, views."
    )
    chat.append(user(instruction))
    resp = chat.sample()

    content = getattr(resp, "content", None)
    # Attempt to coerce to list[dict]
    tweets: List[Dict[str, Any]] = []
    if isinstance(content, list):
        for item in content:
            try:
                tweets.append(
                    {
                        "author": str(item.get("author")),
                        "timestamp": item.get("timestamp"),
                        "text": str(item.get("text")),
                        "url": item.get("url"),
                        "likes": item.get("likes"),
                        "views": item.get("views"),
                    }
                )
            except Exception:
                continue
    elif isinstance(content, str):
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict):
                        tweets.append(
                            {
                                "author": str(item.get("author")),
                                "timestamp": item.get("timestamp"),
                                "text": str(item.get("text")),
                                "url": item.get("url"),
                                "likes": item.get("likes"),
                                "views": item.get("views"),
                            }
                        )
        except Exception:
            # Fallback: store as a single blob with unknown author
            tweets.append({"author": None, "timestamp": None, "text": content, "url": None, "likes": None, "views": None})
    else:
        # Fallback to string representation
        tweets.append({"author": None, "timestamp": None, "text": str(content), "url": None, "likes": None, "views": None})

    return tweets


def save_tweets(rows: List[Dict[str, Any]], output_file: Path, append: bool = False) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append and output_file.exists() else "w"
    with open(output_file, mode, encoding="utf-8") as f:
        for row in rows:
            json.dump(row, f, ensure_ascii=False, default=str)
            f.write("\n")


async def fetch_injury_updates(
    sport: str, 
    handles: Optional[List[str]] = None, 
    min_likes: int = 5, 
    min_views: int = 2000,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    max_search_results: int = 25
) -> Dict[str, Any]:
    """
    App-friendly function to fetch real-time injury updates for a specific sport.
    
    Args:
        sport: "nba" or "nfl"
        handles: Optional list of X handles to override defaults
        min_likes: Minimum likes for X posts
        min_views: Minimum views for X posts
        from_date: Optional from date (YYYY-MM-DD or ISO format)
        to_date: Optional to date (YYYY-MM-DD or ISO format)
        max_search_results: Maximum results per API call
        
    Returns:
        Dict with 'tweets', 'sport', 'handles_used', 'timestamp'
    """
    # Use predefined handles if none provided
    if handles is None:
        handles = get_sport_handles(sport)
    
    # Get API key
    api_key = _get_api_key()
    
    # Import and initialize client
    try:
        from xai_sdk import Client
    except ImportError:
        raise ImportError("xai-sdk is not installed. Run: pip install xai-sdk")
    
    client = Client(api_key=api_key)
    
    # Set default date range if not provided
    if from_date is None and to_date is None:
        to_dt = datetime.now(timezone.utc)
        from_dt = to_dt - timedelta(hours=2)  # Last 2 hours for real-time monitoring
        from_date = from_dt.isoformat()
        to_date = to_dt.isoformat()
    
    # Fetch tweets
    tweets = fetch_tweets_batch(
        client=client,
        handles=handles,
        min_likes=min_likes,
        min_views=min_views,
        from_date=from_date,
        to_date=to_date,
        max_search_results=max_search_results,
        sport=sport
    )
    
    return {
        "tweets": tweets,
        "sport": sport,
        "handles_used": handles,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(tweets),
        "from_date": from_date,
        "to_date": to_date
    }


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Fetch tweets via xAI Grok and save as JSONL/CSV")
    parser.add_argument(
        "--sport",
        choices=["nfl", "nba", "general"],
        default="nba",
        help="Sport to monitor (nfl, nba, or general for both)"
    )
    parser.add_argument(
        "--handles",
        nargs="*",
        default=None,
        help="List of X handles (without @). If not provided, uses predefined handles for the sport.",
    )
    parser.add_argument("--min-likes", type=int, default=10)
    parser.add_argument("--min-views", type=int, default=5000)
    parser.add_argument("--from-date", type=str, default=None, help="YYYY-MM-DD (optional)")
    parser.add_argument("--to-date", type=str, default=None, help="YYYY-MM-DD (optional)")
    parser.add_argument(
        "--out",
        type=str,
        default=str(Path("data/tweets/grok_scraped.jsonl")),
        help="Output JSONL path",
    )
    parser.add_argument("--csv", type=str, default=None, help="Optional CSV path to also write [author,timestamp,text]")
    parser.add_argument("--append", action="store_true", help="Append to existing output files instead of overwrite")
    parser.add_argument("--target-count", type=int, default=2000, help="Stop when at least this many tweets collected")
    parser.add_argument("--window-days", type=int, default=7, help="Days per time window when backfilling")
    parser.add_argument("--max-windows", type=int, default=52, help="Safety cap for number of windows to scan")
    parser.add_argument("--max-search-results", type=int, default=50)
    args = parser.parse_args()

    # Use predefined handles if none provided
    if args.handles is None:
        args.handles = get_sport_handles(args.sport)
        print(f"Using predefined {args.sport.upper()} handles: {', '.join('@' + h for h in args.handles)}")

    # Require API key
    api_key = _get_api_key()

    # Lazy import to avoid ImportError before pip install
    try:
        from xai_sdk import Client
    except Exception as e:
        print("❌ xai-sdk is not installed. Run: pip install xai-sdk", file=sys.stderr)
        sys.exit(1)

    client = Client(api_key=api_key)

    # Build rolling windows and fetch until target-count reached
    to_dt = _parse_date(args.to_date) or datetime.now(timezone.utc)
    window = timedelta(days=max(1, args.window_days))
    collected: List[Dict[str, Any]] = []
    seen: set = set()

    def _key(t: Dict[str, Any]) -> Tuple:
        return (
            t.get("url") or "",
            t.get("author") or "",
            t.get("timestamp") or "",
            (t.get("text") or "")[:120],
        )

    windows_scanned = 0
    while len(collected) < args.target_count and windows_scanned < max(1, args.max_windows):
        from_dt = to_dt - window
        from_str = from_dt.date().isoformat()
        to_str = to_dt.date().isoformat()
        print(f"Window {windows_scanned+1}: {from_str} → {to_str}")

        window_batch: List[Dict[str, Any]] = []
        for batch in _chunked(args.handles, 10):
            print(f"Fetching batch: {', '.join('@'+h for h in batch)} …")
            try:
                tweets = fetch_tweets_batch(
                    client,
                    batch,
                    min_likes=args.min_likes,
                    min_views=args.min_views,
                    from_date=from_str,
                    to_date=to_str,
                    max_search_results=min(25, args.max_search_results),
                    sport=args.sport,
                )
                for t in tweets:
                    k = _key(t)
                    if k in seen:
                        continue
                    seen.add(k)
                    window_batch.append(t)
            except Exception as e:
                print(f"⚠️ Failed batch {batch}: {e}")

        if window_batch:
            collected.extend(window_batch)
            # Save incrementally when appending requested
            if args.append:
                save_tweets(window_batch, Path(args.out), append=True)
                if args.csv:
                    import csv
                    csv_path = Path(args.csv)
                    header_needed = not csv_path.exists()
                    with open(csv_path, "a", newline="", encoding="utf-8") as f:
                        w = csv.writer(f)
                        if header_needed:
                            w.writerow(["author", "timestamp", "text"]) 
                        for t in window_batch:
                            w.writerow([t.get("author"), t.get("timestamp"), t.get("text")])

        # Move window backward
        to_dt = from_dt - timedelta(seconds=1)
        windows_scanned += 1

    # If not appending during loop, write once at end
    if not args.append:
        save_tweets(collected, Path(args.out), append=False)
        if args.csv:
            import csv
            csv_path = Path(args.csv)
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["author", "timestamp", "text"]) 
                for t in collected:
                    w.writerow([t.get("author"), t.get("timestamp"), t.get("text")])

    print(f"✅ Collected {len(collected)} unique tweets across {windows_scanned} window(s) → {args.out}{' and ' + args.csv if args.csv else ''}")


if __name__ == "__main__":
    main()


