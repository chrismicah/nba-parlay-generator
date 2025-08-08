import asyncio
import argparse
from pathlib import Path
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, VirtualScrollConfig


async def _fetch_markdown(url: str, scrolls: int) -> str:
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url=url,
            config=CrawlerRunConfig(
                virtual_scroll_config=VirtualScrollConfig(
                    container_selector="body",
                    scroll_count=scrolls,
                    scroll_by="window_height",
                )
            ),
        )
        return result.markdown or ""


async def scrape_tweets(user: str, scrolls: int) -> None:
    out_dir = Path("data/tweets")
    out_dir.mkdir(parents=True, exist_ok=True)
    output_file = out_dir / f"{user}.md"

    # Try Twitter first
    md = await _fetch_markdown(f"https://twitter.com/{user}", scrolls)
    # If login wall content detected or empty, fallback to Nitter
    if (not md) or ("Log in" in md and "Sign up" in md):
        md = await _fetch_markdown(f"https://nitter.net/{user}", scrolls)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"✅ Saved tweets to {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", required=True)
    parser.add_argument("--scrolls", type=int, default=15)
    args = parser.parse_args()
    asyncio.run(scrape_tweets(args.user, args.scrolls))


