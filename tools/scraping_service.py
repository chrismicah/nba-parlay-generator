
import asyncio
from playwright.async_api import async_playwright, Browser
from bs4 import BeautifulSoup
import logging
from typing import List, Dict
import os

logging.basicConfig(level=logging.INFO)

class ScrapingService:
    ESPN_INJURIES_URL = "https://www.espn.com/nba/injuries"

    def __init__(self, browser: Browser, cache_get=None, cache_set=None):
        self.browser = browser
        self.cache_get = cache_get
        self.cache_set = cache_set

    async def scrape_page(
        self,
        url: str,
        *,
        wait_until: str = "networkidle",
        timeout_ms: int = 90000,
        retries: int = 2,
        scroll_passes: int = 3,
    ):
        """Navigate to a URL and return the rendered HTML.

        Args:
            url: Page URL to load.
            wait_until: Playwright wait strategy (e.g., "domcontentloaded", "load", "networkidle").
            timeout_ms: Navigation timeout in milliseconds.
            retries: Number of retry attempts on failure.
            scroll_passes: How many lazy-load scroll passes to perform.
        """
        user_agent = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )

        last_exception = None
        for attempt in range(1, retries + 1):
            context = None
            page = None
            try:
                context = await self.browser.new_context(
                    user_agent=user_agent,
                    viewport={"width": 1366, "height": 768},
                    device_scale_factor=1,
                    java_script_enabled=True,
                    ignore_https_errors=True,
                )
                # Basic stealth: hide webdriver flag and set languages/platform
                await context.add_init_script(
                    """
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                    Object.defineProperty(navigator, 'platform', { get: () => 'MacIntel' });
                    """
                )
                page = await context.new_page()
                await page.goto(url, wait_until=wait_until, timeout=timeout_ms)
                # Extra waits for JS-heavy sites
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_timeout(min(5000, timeout_ms // 6))

                # Trigger lazy loading by scrolling
                for _ in range(max(0, scroll_passes)):
                    await page.mouse.wheel(0, 2000)
                    await page.wait_for_timeout(1000)

                content = await page.content()
                return content
            except Exception as exc:
                last_exception = exc
                logging.error(f"Error scraping {url} (attempt {attempt}): {exc}")
                await asyncio.sleep(1.5)
            finally:
                if page is not None:
                    try:
                        await page.close()
                    except Exception:
                        pass
                if context is not None:
                    try:
                        await context.close()
                    except Exception:
                        pass
        logging.error(f"Failed to scrape {url} after retries: {last_exception}")
        return None

    def parse_html(self, html: str):
        if not html:
            return None
        return BeautifulSoup(html, "html.parser")

    async def scrape_injuries(self, max_retries: int = 3, backoff_base: float = 1.5, filter_out_season: bool = False) -> List[Dict]:
        last_exc = None
        for attempt in range(max_retries):
            try:
                html = await self.scrape_page(self.ESPN_INJURIES_URL)
                if not html:
                    raise Exception("Failed to fetch page content")
                soup = self.parse_html(html)
                data = self._parse_injuries(soup, filter_out_season=filter_out_season)
                if self.cache_set:
                    self.cache_set("espn_nba_injuries", data)
                return data
            except Exception as exc:
                logging.warning(f"Scrape attempt {attempt+1} failed: {exc}")
                last_exc = exc
                await asyncio.sleep(backoff_base ** attempt)
        if self.cache_get:
            cached = self.cache_get("espn_nba_injuries")
            if cached:
                logging.info("Returning cached ESPN NBA injuries data.")
                return cached
        raise Exception(f"Failed to scrape ESPN NBA injuries after {max_retries} attempts.") from last_exc

    def _parse_injuries(self, soup, filter_out_season=False) -> List[Dict]:
        injuries = []
        team_headers = soup.find_all("h2")
        tables = soup.find_all("table", class_="Table")

        if len(team_headers) != len(tables):
            print("Warning: Number of team headers and tables do not match.")

        for team_header, table in zip(team_headers, tables):
            team_name = team_header.text.strip()
            for row in table.select("tbody tr"):
                cols = row.find_all("td")
                if len(cols) < 5:
                    continue
                player = cols[0].text.strip()
                position = cols[1].text.strip()
                injury = cols[2].text.strip()
                status = cols[3].text.strip()
                updated = cols[4].text.strip()

                if filter_out_season and "Out for Season" in status:
                    continue

                injuries.append({
                    "team": self._normalize_team_name(team_name),
                    "player": player,
                    "position": position,
                    "injury": injury,
                    "status": status,
                    "updated": updated
                })

        return injuries

    def _normalize_team_name(self, name: str) -> str:
        return name.strip()
