import pytest
import asyncio
from tools.web_scraper_tool import WebScraperTool

@pytest.mark.asyncio
async def test_scrape_injuries_basic():
    scraper = WebScraperTool()
    data = await scraper.scrape_injuries(max_retries=3)
    assert isinstance(data, list)
    assert len(data) > 0
    sample = data[0]
    for key in ["team", "player", "position", "injury", "status", "updated"]:
        assert key in sample 