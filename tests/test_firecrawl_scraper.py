import asyncio
from tools.firecrawl_scraper_tool import scrape_and_save, SCRAPE_SOURCES

def test_all_sources():
    """Test scraping from all available sources."""
    for source_name in SCRAPE_SOURCES:
        print(f"\n{'='*50}")
        print(f"Testing source: {source_name}")
        print(f"{'='*50}")
        try:
            asyncio.run(scrape_and_save(source_name))
        except Exception as e:
            print(f"❌ Error scraping {source_name}: {str(e)}")

if __name__ == "__main__":
    test_all_sources()