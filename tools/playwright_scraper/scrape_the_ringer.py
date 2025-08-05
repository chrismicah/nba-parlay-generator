
import asyncio
from tools.scraping_service import ScrapingService

async def main():
    scraper = ScrapingService()
    html = await scraper.scrape_page("https://www.theringer.com/nba")
    if html:
        with open("data/the_ringer.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("✅ Playwright scrape completed for the_ringer")
    else:
        print("❌ Playwright scrape failed for the_ringer")
    await scraper.close_browser()

if __name__ == "__main__":
    asyncio.run(main())
