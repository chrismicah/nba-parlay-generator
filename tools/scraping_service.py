
import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO)

class ScrapingService:
    def __init__(self, browser=None):
        self.browser = browser

    async def launch_browser(self):
        if not self.browser:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=True)
        return self.browser

    async def close_browser(self):
        if self.browser:
            await self.browser.close()
            self.browser = None

    async def scrape_page(self, url: str):
        browser = await self.launch_browser()
        page = await browser.new_page()
        try:
            await page.goto(url, timeout=60000)
            await page.wait_for_timeout(3000)
            content = await page.content()
            return content
        except Exception as e:
            logging.error(f"Error scraping {url}: {e}")
            return None
        finally:
            await page.close()

    def parse_html(self, html: str):
        if not html:
            return None
        soup = BeautifulSoup(html, "html.parser")
        return soup

    async def firecrawl_scrape(self, url: str, scrape_options: dict = None):
        from firecrawl import FirecrawlApp
        api_key = os.getenv("FIRECRAWL_API_KEY")
        if not api_key:
            raise ValueError("Missing FIRECRAWL_API_KEY in .env")
        app = FirecrawlApp(api_key=api_key)
        return app.scrape_url(url, params=scrape_options)

    async def firecrawl_crawl(self, url: str, crawl_options: dict = None):
        from firecrawl import FirecrawlApp
        api_key = os.getenv("FIRECRAWL_API_KEY")
        if not api_key:
            raise ValueError("Missing FIRECRAWL_API_KEY in .env")
        app = FirecrawlApp(api_key=api_key)
        return app.crawl_url(url, params=crawl_options)

    async def firecrawl_check_crawl_status(self, crawl_id: str):
        from firecrawl import FirecrawlApp
        api_key = os.getenv("FIRECRAWL_API_KEY")
        if not api_key:
            raise ValueError("Missing FIRECRAWL_API_KEY in .env")
        app = FirecrawlApp(api_key=api_key)
        return app.check_crawl_status(crawl_id)
