import pytest
from tools.scraping_service import ScrapingService

@pytest.mark.asyncio
async def test_scrape_injuries():
    scraper = ScrapingService()
    injuries = await scraper.scrape_injuries()
    assert isinstance(injuries, list)
    if injuries:
        assert "team" in injuries[0]
        assert "player" in injuries[0]
        assert "position" in injuries[0]
        assert "injury" in injuries[0]
        assert "status" in injuries[0]
        assert "updated" in injuries[0]