import pytest
import asyncio
from tools.data_fetcher_tool import DataFetcherTool, NFLDataFetcher, NBADataFetcher, SportFactory, MarketNormalizer

def test_sport_factory():
    """Test SportFactory creates correct fetchers"""
    nba_fetcher = SportFactory.create_data_fetcher("nba")
    nfl_fetcher = SportFactory.create_data_fetcher("nfl")
    
    assert isinstance(nba_fetcher, NBADataFetcher)
    assert isinstance(nfl_fetcher, NFLDataFetcher)
    
    with pytest.raises(ValueError):
        SportFactory.create_data_fetcher("unsupported")

def test_market_normalizer():
    """Test MarketNormalizer handles team and player aliases"""
    normalizer = MarketNormalizer()
    
    # Test NFL team normalization
    nfl_game = {"home_team": "KC", "away_team": "BAL"}
    normalized = normalizer.normalize_game(nfl_game, "nfl")
    assert normalized["home_team"] == "Kansas City Chiefs"
    assert normalized["away_team"] == "Baltimore Ravens"
    
    # Test NBA team normalization
    nba_game = {"home_team": "LAL", "away_team": "BOS"}
    normalized = normalizer.normalize_game(nba_game, "nba")
    assert normalized["home_team"] == "Los Angeles Lakers"
    assert normalized["away_team"] == "Boston Celtics"
    
    # Test player normalization
    nfl_stats = {"player_name": "Patrick Mahomes"}
    normalized = normalizer.normalize_stats(nfl_stats, "nfl")
    assert normalized["player_name"] == "P. Mahomes"

def test_data_fetcher_initialization():
    """Test DataFetcherTool initialization with different sports"""
    nba_fetcher = DataFetcherTool(sport="nba")
    nfl_fetcher = DataFetcherTool(sport="nfl")
    
    assert nba_fetcher.sport == "nba"
    assert nfl_fetcher.sport == "nfl"
    assert isinstance(nba_fetcher.fetcher, NBADataFetcher)
    assert isinstance(nfl_fetcher.fetcher, NFLDataFetcher)
    assert isinstance(nba_fetcher.normalizer, MarketNormalizer)

def test_nfl_data_fetcher_attributes():
    """Test NFLDataFetcher has correct API key setup"""
    fetcher = NFLDataFetcher()
    # Should have api_key attribute (even if None when not set)
    assert hasattr(fetcher, 'api_key')

def test_nba_data_fetcher_attributes():
    """Test NBADataFetcher has correct attributes"""
    fetcher = NBADataFetcher()
    # Should have api_fetcher attribute
    assert hasattr(fetcher, 'api_fetcher')

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
