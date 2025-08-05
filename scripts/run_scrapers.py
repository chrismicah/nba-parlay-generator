import os
import asyncio
from tools.scraping_service import ScrapingService
from playwright.async_api import async_playwright
from dotenv import load_dotenv
import html2text
import argparse

load_dotenv()

SCRAPE_SOURCES = {
    "nba_com": "https://www.nba.com/news",
    "the_ringer": "https://www.theringer.com/nba",
    "action_network": "https://www.actionnetwork.com/nba",
    "clutchpoints": "https://clutchpoints.com/nba/",
}

async def scrape_and_save(source_name: str):
    """Scrapes a given source using Playwright and saves the content as Markdown."""
    if source_name not in SCRAPE_SOURCES:
        raise ValueError(f"Unknown source: {source_name}")

    url = SCRAPE_SOURCES[source_name]
    print(f"🔍 Scraping with Playwright: {source_name} ({url})")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        scraper = ScrapingService(browser)
        html = await scraper.scrape_page(url)

        if not html:
            print(f"❌ Playwright scrape failed for {source_name}. No HTML content found.")
            return

        # Convert HTML to Markdown
        h = html2text.HTML2Text()
        h.ignore_links = False
        markdown = h.handle(html)

        # Save the markdown
        output_dir = "data"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{source_name}.md")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown)

        print(f"✅ Playwright scrape completed for {source_name}")
        print(f"📄 Saved scraped markdown to: {output_path}")
        print("📄 Preview:\n", markdown[:500])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape NBA content using Playwright")
    parser.add_argument(
        "--source",
        choices=list(SCRAPE_SOURCES.keys()),
        required=True,
        help="Source to scrape (e.g., nba_com, the_ringer)"
    )
    args = parser.parse_args()
    asyncio.run(scrape_and_save(args.source))