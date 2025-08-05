
import asyncio
from tools.scraping_service import ScrapingService

async def main():
    scraper = ScrapingService()
    html, screenshot = await scraper.scrape_page("https://www.actionnetwork.com/nba", screenshot_path="data/action_network.png")
    if html:
        with open("data/action_network.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("✅ Playwright scrape completed for action_network")
        if screenshot:
            print(f"🖼️ Screenshot saved to {screenshot}")
    else:
        print("❌ Playwright scrape failed for action_network")
    await scraper.close_browser()

if __name__ == "__main__":
    asyncio.run(main())
