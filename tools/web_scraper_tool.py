import asyncio
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import logging
import time
import bs4
import random
from playwright.sync_api import sync_playwright
from utils.headers import get_random_user_agent

logging.basicConfig(level=logging.INFO)

class WebScraperTool:
    """
    Scrapes NBA injury data from ESPN using Playwright.
    Provides robust loading, parsing, and fallback logic.
    """
    ESPN_INJURIES_URL = "https://www.espn.com/nba/injuries"

    def __init__(self, cache_get=None, cache_set=None):
        """
        Optionally provide cache_get and cache_set callables for fallback.
        """
        self.cache_get = cache_get
        self.cache_set = cache_set

    async def scrape_injuries(self, max_retries: int = 3, backoff_base: float = 1.5, filter_out_season: bool = False) -> List[Dict]:
        """
        Scrape NBA injury data from ESPN.

        Args:
            max_retries (int): Number of retries on failure.
            backoff_base (float): Exponential backoff base seconds.
            filter_out_season (bool): If True, filter out 'Out for Season' players.
        Returns:
            List[Dict]: List of injury dicts with keys: team, player, position, injury, status, updated.
        Raises:
            Exception: If scraping fails after retries and no cache is available.
        """
        last_exc = None
        for attempt in range(max_retries):
            try:
                data = await self._scrape_injuries_once(filter_out_season=filter_out_season)
                if self.cache_set:
                    self.cache_set("espn_nba_injuries", data)
                return data
            except Exception as exc:
                logging.warning(f"Scrape attempt {attempt+1} failed: {exc}")
                last_exc = exc
                await asyncio.sleep(backoff_base ** attempt)
        # Fallback to cache if available
        if self.cache_get:
            cached = self.cache_get("espn_nba_injuries")
            if cached:
                logging.info("Returning cached ESPN NBA injuries data.")
                return cached
        raise Exception(f"Failed to scrape ESPN NBA injuries after {max_retries} attempts.") from last_exc

    async def _scrape_injuries_once(self, filter_out_season=False) -> List[Dict]:
        """
        Scrape NBA injury data from ESPN's main injuries page.

        Args:
            filter_out_season (bool): If True, filter out players 'Out for Season'.

        Returns:
            List[Dict]: List of injury dicts with keys: team, player, position, injury, status, updated.
        """
        from playwright.async_api import async_playwright
        from bs4 import BeautifulSoup

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto("https://www.espn.com/nba/injuries", timeout=60000)
            await page.wait_for_selector("h2", timeout=20000)  # Wait for team headers

            html = await page.content()
            await browser.close()

        soup = BeautifulSoup(html, "html.parser")
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
                    "team": self._normalize_team_name(team_name) if hasattr(self, '_normalize_team_name') else team_name,
                    "player": player,
                    "position": position,
                    "injury": injury,
                    "status": status,
                    "updated": updated
                })

        return injuries

    def _normalize_team_name(self, name: str) -> str:
        """
        Normalize team names for consistency with sportsbook data.
        Args:
            name (str): Raw team name from ESPN.
        Returns:
            str: Normalized team name.
        """
        # Stub: Add mapping as needed
        return name.strip()

def run_web_scraper_tool():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=get_random_user_agent())
        page = context.new_page()

        try:
            page.goto("https://www.espn.com/nba/injuries")

            # Wait until the injuries table loads
            page.wait_for_selector("section[class*='Injuries']")

            # Add a small human-like delay
            page.wait_for_timeout(random.uniform(1200, 2400))  # milliseconds

            # Scrape data here...
            content = page.content()
            return content

        except Exception as e:
            print(f"Error during scraping: {str(e)}")
            return None
        finally:
            browser.close()

        # Add delay between requests if making multiple
        time.sleep(random.uniform(1.2, 2.4))

# Example usage (async):
# scraper = WebScraperTool()
# data = asyncio.run(scraper.scrape_injuries())
# print(data) 