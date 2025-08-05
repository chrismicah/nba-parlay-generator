import os
import time
import json
from pathlib import Path
from tools.scraping_service import ScrapingService
from dotenv import load_dotenv
from pprint import pprint

load_dotenv()

SCRAPE_SOURCES = {
    "nba_com": "https://www.nba.com/news",
    "the_ringer": "https://www.theringer.com/nba",
    "action_network": "https://www.actionnetwork.com/nba",
    "clutchpoints": "https://clutchpoints.com/nba/",
}

PLAYWRIGHT_SOURCES = ['the_ringer', 'action_network', 'clutchpoints']

def save_documents_to_file(source_name, documents):
    os.makedirs("data/firecrawl", exist_ok=True)
    output_path = f"data/firecrawl/{source_name}.json"
    with open(output_path, "w") as f:
        json.dump(documents, f, indent=2)
    print(f"📦 Saved {len(documents)} documents to {output_path}")

async def scrape_and_save(source_name: str):
    if source_name not in SCRAPE_SOURCES:
        raise ValueError(f"Unknown source: {source_name}")

    scraper = ScrapingService()

    if source_name in PLAYWRIGHT_SOURCES:
        html = await scraper.scrape_page(SCRAPE_SOURCES[source_name])
        if html:
            with open(f"data/{source_name}.html", "w", encoding="utf-8") as f:
                f.write(html)
            print(f"✅ Playwright scrape completed for {source_name}")
        else:
            print(f"❌ Playwright scrape failed for {source_name}")
        return

    print(f"🔍 Scraping: {source_name} ({SCRAPE_SOURCES[source_name]})")
    result = await scraper.firecrawl_crawl(
        url=SCRAPE_SOURCES[source_name],
        crawl_options={"limit": 10, "scrape_options": {"formats": ["markdown"]}},
    )
    crawl_id = result.data[0].metadata.get('scrapeId')
    print("📋 Crawl started. Job ID:", crawl_id)
    for attempt in range(1, 61):
        print(f"⏳ Waiting for results... (attempt {attempt}/60)")
        status = await scraper.firecrawl_check_crawl_status(crawl_id)
        # 🔍 Dump full status so we can examine what's going on
        print("📋 FULL STATUS:")
        pprint(status.model_dump())
        # 🛠 Extract documents
        if isinstance(status.data, list):
            documents = status.data
        elif isinstance(status.data, dict) and "data" in status.data:
            documents = status.data["data"]
        else:
            documents = []
        print(f"📄 Retrieved {len(documents)} documents.")
        if getattr(status, "status", None) == "completed":
            print("✅ Crawl completed.")
            if not documents:
                # Fallback for nba_com: try direct scrape_url
                if source_name == "nba_com":
                    print(f"📡 Switching to direct scrape mode for {source_name}")
                    try:
                        result = await scraper.firecrawl_scrape("https://www.nba.com/news", scrape_options={"formats": ["markdown", "html"]})
                        markdown = result.markdown
                        if not markdown:
                            raise RuntimeError("❌ scrape_url() returned no markdown.")
                        output_path = os.path.join("data", f"{source_name}.md")
                        with open(output_path, "w", encoding="utf-8") as f:
                            f.write(markdown)
                        print(f"✅ Saved scraped markdown to: {output_path}")
                        print("📄 Preview:\n", markdown[:500])
                    except Exception as e:
                        print(f"❌ Error during scrape: {str(e)}")
                    exit(0)
                raise RuntimeError("❌ No documents returned after crawl completion.")
            save_documents_to_file(source_name, documents)
            print(f"📄 Saved {len(documents)} documents.")
            print("\n🔍 First snippet:\n", documents[0].get("markdown", "")[:500])
            return
        time.sleep(5)
    raise RuntimeError("❌ Timed out waiting for crawl results.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scrape NBA content using Firecrawl or Playwright")
    parser.add_argument(
        "--source",
        choices=list(SCRAPE_SOURCES.keys()),
        help="Source to scrape (e.g., nba_com, the_ringer)"
    )
    args = parser.parse_args()
    if args.source:
        import asyncio
        asyncio.run(scrape_and_save(args.source))
    else:
        parser.error("You must provide --source.")
