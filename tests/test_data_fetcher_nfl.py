import pytest
import asyncio
import json
from unittest.mock import patch, AsyncMock, MagicMock
from tools.data_fetcher_tool import DataFetcherTool, NFLDataFetcher, NBADataFetcher, SportFactory, MarketNormalizer

@pytest.mark.asyncio
async def test_nfl_game_schedule():
    """Test NFL game schedule fetching with API-NFL"""
    fetcher = DataFetcherTool(sport="nfl")
    
    # Mock response for API-NFL
    mock_response = {
        "response": [
            {
                "game": {"id": 12345, "date": "2025-09-05T20:00:00Z"},
                "teams": {
                    "home": {"name": "Kansas City Chiefs"},
                    "away": {"name": "Baltimore Ravens"}
                }
            }
        ]
    }
    
    with patch('aiohttp.ClientSession') as mock_session_cls:
        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session
        
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aenter__.return_value = mock_resp
        
        games = await fetcher.get_game_schedule("2025-09-05")
        
        assert len(games) > 0
        assert all(key in games[0] for key in ["game_id", "home_team", "away_team", "game_time"])
        assert games[0]["home_team"] == "Kansas City Chiefs"
        assert games[0]["away_team"] == "Baltimore Ravens"


@pytest.mark.asyncio
async def test_nfl_game_schedule_espn_fallback():
    """Test NFL game schedule fallback to ESPN when API-NFL fails"""
    fetcher = DataFetcherTool(sport="nfl")
    
    # Mock ESPN response
    mock_espn_response = {
        "events": [
            {
                "id": "12345",
                "date": "2025-09-05T20:00:00Z",
                "competitions": [{
                    "competitors": [
                        {"homeAway": "home", "team": {"name": "Kansas City Chiefs"}},
                        {"homeAway": "away", "team": {"name": "Baltimore Ravens"}}
                    ]
                }]
            }
        ]
    }
    
    with patch('aiohttp.ClientSession.get') as mock_get:
        # First call (API-NFL) fails, second call (ESPN) succeeds
        def side_effect(*args, **kwargs):
            url = args[0] if args else kwargs.get('url', '')
            if 'american-football.api-sports.io' in url:
                mock_resp = AsyncMock()
                mock_resp.status = 429  # Rate limit
                mock_resp.json = AsyncMock(side_effect=Exception("Rate limited"))
                return mock_resp
            else:  # ESPN
                mock_resp = AsyncMock()
                mock_resp.status = 200
                mock_resp.json = AsyncMock(return_value=mock_espn_response)
                return mock_resp
        
        mock_get.return_value.__aenter__.side_effect = side_effect
        
        games = await fetcher.get_game_schedule("2025-09-05")
        
        assert len(games) > 0
        assert games[0]["game_id"] == "12345"


@pytest.mark.asyncio
async def test_nfl_player_stats():
    """Test NFL player stats fetching"""
    fetcher = DataFetcherTool(sport="nfl")
    
    mock_response = {
        "response": [
            {
                "player": {"id": 12345, "name": "Patrick Mahomes"},
                "statistics": {"passing_yards": 4839, "touchdowns": 41}
            }
        ]
    }
    
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=mock_response)
        mock_get.return_value.__aenter__.return_value = mock_resp
        
        stats = await fetcher.get_player_stats(["12345"], "2024")
        
        assert len(stats) > 0
        assert "player_id" in stats[0]
        assert "stats" in stats[0]
        assert stats[0]["player_id"] == "12345"


@pytest.mark.asyncio
async def test_nfl_team_stats():
    """Test NFL team stats fetching"""
    fetcher = DataFetcherTool(sport="nfl")
    
    mock_response = {
        "response": {
            "team": {"id": 1, "name": "Kansas City Chiefs"},
            "statistics": {"wins": 14, "losses": 3}
        }
    }
    
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=mock_response)
        mock_get.return_value.__aenter__.return_value = mock_resp
        
        stats = await fetcher.get_team_stats(["1"], "2024")
        
        assert len(stats) > 0
        assert "team_id" in stats[0]
        assert "stats" in stats[0]


@pytest.mark.asyncio
async def test_nba_unchanged():
    """Test that NBA functionality remains unchanged"""
    fetcher = DataFetcherTool(sport="nba")
    
    # Mock BallDontLie response
    mock_response = {
        "data": [
            {
                "id": 12345,
                "date": "2025-10-20T19:00:00.000Z",
                "home_team": {"full_name": "Los Angeles Lakers"},
                "visitor_team": {"full_name": "Boston Celtics"}
            }
        ]
    }
    
    with patch.object(fetcher.fetcher.api_fetcher, 'fetch', return_value=mock_response):
        games = await fetcher.get_game_schedule("2025-10-20")
        
        assert len(games) > 0
        assert "Lakers" in games[0]["home_team"] or "Lakers" in games[0]["away_team"]
        assert "Celtics" in games[0]["home_team"] or "Celtics" in games[0]["away_team"]


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


@pytest.mark.asyncio
async def test_caching():
    """Test Redis caching functionality"""
    fetcher = DataFetcherTool(sport="nfl")
    
    # Mock Redis
    with patch.object(fetcher, 'redis_client') as mock_redis:
        mock_redis.get.return_value = None
        mock_redis.setex.return_value = True
        
        # Mock API response
        mock_response = {
            "response": [{
                "game": {"id": 1, "date": "2025-09-05"},
                "teams": {"home": {"name": "Chiefs"}, "away": {"name": "Ravens"}}
            }]
        }
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_response)
            mock_get.return_value.__aenter__.return_value = mock_resp
            
            games = await fetcher.get_game_schedule("2025-09-05")
            
            # Verify cache was checked and set
            mock_redis.get.assert_called_once()
            mock_redis.setex.assert_called_once()


@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling when both primary and fallback fail"""
    fetcher = DataFetcherTool(sport="nfl")
    
    with patch('aiohttp.ClientSession.get') as mock_get:
        # Both API-NFL and ESPN fail
        mock_resp = AsyncMock()
        mock_resp.status = 500
        mock_resp.json = AsyncMock(side_effect=Exception("Server error"))
        mock_get.return_value.__aenter__.return_value = mock_resp
        
        games = await fetcher.get_game_schedule("2025-09-05")
        
        # Should return empty list when all sources fail
        assert games == []


def test_data_fetcher_initialization():
    """Test DataFetcherTool initialization with different sports"""
    nba_fetcher = DataFetcherTool(sport="nba")
    nfl_fetcher = DataFetcherTool(sport="nfl")
    
    assert nba_fetcher.sport == "nba"
    assert nfl_fetcher.sport == "nfl"
    assert isinstance(nba_fetcher.fetcher, NBADataFetcher)
    assert isinstance(nfl_fetcher.fetcher, NFLDataFetcher)
    assert isinstance(nba_fetcher.normalizer, MarketNormalizer)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
