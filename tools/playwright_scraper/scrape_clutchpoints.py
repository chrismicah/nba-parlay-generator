
import asyncio
from tools.scraping_service import ScrapingService

async def main():
    scraper = ScrapingService()
    html, screenshot = await scraper.scrape_page("https://clutchpoints.com/nba/", screenshot_path="data/clutchpoints.png")
    if html:
        with open("data/clutchpoints.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("✅ Playwright scrape completed for clutchpoints")
        if screenshot:
            print(f"🖼️ Screenshot saved to {screenshot}")
    else:
        print("❌ Playwright scrape failed for clutchpoints")
    await scraper.close_browser()

if __name__ == "__main__":
    asyncio.run(main())
