import asyncio
import argparse
import datetime
from pathlib import Path

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, VirtualScrollConfig


def timestamped_output(account: str) -> Path:
    ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    return Path(f"data/tweets/{account}/{ts}.md")


async def scrape_twitter(account: str, scrolls: int = 25) -> None:
    url = f"https://twitter.com/{account}"
    output_path = timestamped_output(account)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url=url,
            config=CrawlerRunConfig(
                virtual_scroll_config=VirtualScrollConfig(
                    container_selector="body",
                    scroll_count=scrolls,
                    scroll_by="window_height",
                    wait_after_scroll=1.0,
                ),
            ),
        )
        output_path.write_text(result.markdown or "")
        print(f"✅ Saved: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", required=True)
    parser.add_argument("--scrolls", type=int, default=25)
    args = parser.parse_args()

    asyncio.run(scrape_twitter(args.account, args.scrolls))


if __name__ == "__main__":
    main()


