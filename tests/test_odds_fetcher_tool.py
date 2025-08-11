import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any
import os

from tools.odds_fetcher_tool import (
    OddsFetcherTool, 
    OddsFetcherError, 
    GameOdds, 
    BookOdds, 
    Selection
)


class TestOddsFetcherTool:
    """Test suite for OddsFetcherTool."""
    
    @pytest.fixture
    def odds_fetcher(self):
        """Create an OddsFetcherTool instance for testing."""
        return OddsFetcherTool()
    
    @pytest.fixture
    def sample_api_response(self) -> List[Dict[str, Any]]:
        """Sample API response for testing."""
        return [
            {
                "id": "test_game_1",
                "commence_time": "2024-01-15T19:30:00Z",
                "bookmakers": [
                    {
                        "title": "DraftKings",
                        "markets": [
                            {
                                "key": "h2h",
                                "outcomes": [
                                    {"name": "Los Angeles Lakers", "price": 1.91},
                                    {"name": "Golden State Warriors", "price": 1.91}
                                ]
                            },
                            {
                                "key": "spreads",
                                "outcomes": [
                                    {"name": "Los Angeles Lakers", "price": 1.91, "point": -2.5},
                                    {"name": "Golden State Warriors", "price": 1.91, "point": 2.5}
                                ]
                            }
                        ]
                    },
                    {
                        "title": "FanDuel",
                        "markets": [
                            {
                                "key": "totals",
                                "outcomes": [
                                    {"name": "Over", "price": 1.91, "point": 220.5},
                                    {"name": "Under", "price": 1.91, "point": 220.5}
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    
    @pytest.fixture
    def sample_fallback_response(self) -> List[Dict[str, Any]]:
        """Sample fallback API response with American odds."""
        return [
            {
                "id": "test_game_1",
                "commence_time": "2024-01-15T19:30:00Z",
                "bookmakers": [
                    {
                        "title": "Bet365",
                        "markets": [
                            {
                                "key": "h2h",
                                "outcomes": [
                                    {"name": "Los Angeles Lakers", "price": 120},  # American odds
                                    {"name": "Golden State Warriors", "price": -150}  # American odds
                                ]
                            }
                        ]
                    }
                ]
            }
        ]

    def test_american_to_decimal_conversion(self, odds_fetcher):
        """Test American to decimal odds conversion."""
        # Test positive American odds
        assert odds_fetcher.american_to_decimal(120) == pytest.approx(2.2, rel=1e-3)
        assert odds_fetcher.american_to_decimal(200) == pytest.approx(3.0, rel=1e-3)
        
        # Test negative American odds
        assert odds_fetcher.american_to_decimal(-150) == pytest.approx(1.6667, rel=1e-3)
        assert odds_fetcher.american_to_decimal(-200) == pytest.approx(1.5, rel=1e-3)

    def test_safe_float_conversion(self, odds_fetcher):
        """Test safe float conversion utility."""
        assert odds_fetcher._safe_float("1.91") == 1.91
        assert odds_fetcher._safe_float(1.91) == 1.91
        assert odds_fetcher._safe_float(None) is None
        assert odds_fetcher._safe_float("invalid") is None

    def test_normalize_selection_decimal(self, odds_fetcher):
        """Test selection normalization with decimal odds."""
        outcome = {
            "name": "Los Angeles Lakers",
            "price": 1.91,
            "point": -2.5
        }
        
        selection = odds_fetcher._normalize_selection(outcome, "decimal")
        
        assert selection.name == "Los Angeles Lakers"
        assert selection.price_decimal == 1.91
        assert selection.line == -2.5

    def test_normalize_selection_american(self, odds_fetcher):
        """Test selection normalization with American odds conversion."""
        outcome = {
            "name": "Los Angeles Lakers",
            "price": 120,  # American odds
            "point": -2.5
        }
        
        selection = odds_fetcher._normalize_selection(outcome, "american")
        
        assert selection.name == "Los Angeles Lakers"
        assert selection.price_decimal == pytest.approx(2.2, rel=1e-3)
        assert selection.line == -2.5

    def test_normalize_selection_no_line(self, odds_fetcher):
        """Test selection normalization without a line (h2h market)."""
        outcome = {
            "name": "Los Angeles Lakers",
            "price": 1.91
            # No point field
        }
        
        selection = odds_fetcher._normalize_selection(outcome, "decimal")
        
        assert selection.name == "Los Angeles Lakers"
        assert selection.price_decimal == 1.91
        assert selection.line is None

    def test_get_game_odds_success(self, odds_fetcher, sample_api_response):
        """Test successful odds fetching."""
        # Mock the existing API fetcher's fetch method
        with patch.object(odds_fetcher.api_fetcher, 'fetch') as mock_fetch:
            mock_fetch.return_value = sample_api_response
            
            # Call the method
            result = odds_fetcher.get_game_odds("basketball_nba", "us", ["h2h", "spreads"])
            
            # Verify the result
            assert len(result) == 1
            game = result[0]
            assert game.sport_key == "basketball_nba"
            assert game.game_id == "test_game_1"
            assert game.commence_time == "2024-01-15T19:30:00Z"
            assert len(game.books) == 3  # 2 markets from DraftKings + 1 from FanDuel
            
            # Verify API was called correctly
            mock_fetch.assert_called_once()
            call_args = mock_fetch.call_args
            assert "basketball_nba" in call_args[0][0]  # URL contains sport_key
            assert call_args[1]["params"]["oddsFormat"] == "decimal"
            assert call_args[1]["params"]["markets"] == "h2h,spreads"

    def test_get_game_odds_default_markets(self, odds_fetcher):
        """Test that default markets are used when none provided."""
        with patch.object(odds_fetcher.api_fetcher, 'fetch') as mock_fetch:
            mock_fetch.return_value = []
            
            odds_fetcher.get_game_odds("basketball_nba", "us")
            
            # Verify default markets were used
            call_args = mock_fetch.call_args
            assert call_args[1]["params"]["markets"] == "h2h,spreads,totals"

    def test_get_game_odds_with_fallback(self, sample_fallback_response):
        """Test odds fetching with fallback when primary fails."""
        # Mock environment variables for fallback
        with patch.dict('os.environ', {
            'FALLBACK_ODDS_API_KEY': 'fallback_key',
            'FALLBACK_ODDS_BASE_URL': 'https://api.fallback.com'
        }):
            odds_fetcher = OddsFetcherTool()
            
            # Mock primary API failure
            with patch.object(odds_fetcher.api_fetcher, 'fetch') as mock_primary_fetch:
                mock_primary_fetch.side_effect = Exception("Primary API failed")
                
                # Mock fallback API success by patching the _fetch_fallback_odds method
                with patch.object(odds_fetcher, '_fetch_fallback_odds') as mock_fallback:
                    mock_fallback.return_value = odds_fetcher._normalize_response(
                        sample_fallback_response, "basketball_nba", odds_format="american"
                    )
                    
                    # Call the method
                    result = odds_fetcher.get_game_odds("basketball_nba", "us", ["h2h"])
                    
                    # Verify fallback was used and American odds were converted
                    assert len(result) == 1
                    game = result[0]
                    assert len(game.books) == 1
                    book = game.books[0]
                    assert book.bookmaker == "Bet365"
                    assert len(book.selections) == 2
                    
                    # Verify American odds were converted to decimal
                    lakers_selection = next(s for s in book.selections if s.name == "Los Angeles Lakers")
                    warriors_selection = next(s for s in book.selections if s.name == "Golden State Warriors")
                    
                    assert lakers_selection.price_decimal == pytest.approx(2.2, rel=1e-3)  # +120 -> 2.2
                    assert warriors_selection.price_decimal == pytest.approx(1.6667, rel=1e-3)  # -150 -> 1.6667

    def test_get_game_odds_both_apis_fail(self):
        """Test that OddsFetcherError is raised when both primary and fallback fail."""
        # Mock environment variables for fallback
        with patch.dict('os.environ', {
            'FALLBACK_ODDS_API_KEY': 'fallback_key',
            'FALLBACK_ODDS_BASE_URL': 'https://api.fallback.com'
        }):
            odds_fetcher = OddsFetcherTool()
            
            # Mock primary API failure
            with patch.object(odds_fetcher.api_fetcher, 'fetch') as mock_primary_fetch:
                mock_primary_fetch.side_effect = Exception("Primary API failed")
                
                # Mock fallback API failure
                with patch.object(odds_fetcher, '_fetch_fallback_odds') as mock_fallback:
                    mock_fallback.side_effect = Exception("Fallback API failed")
                    
                    # Call the method and expect an error
                    with pytest.raises(OddsFetcherError) as exc_info:
                        odds_fetcher.get_game_odds("basketball_nba", "us", ["h2h"])
                    
                    assert "All odds providers failed" in str(exc_info.value)

    def test_get_game_odds_no_fallback_configured(self, odds_fetcher):
        """Test that primary API failure raises error when no fallback is configured."""
        # Mock primary API failure
        with patch.object(odds_fetcher.api_fetcher, 'fetch') as mock_fetch:
            mock_fetch.side_effect = Exception("Primary API failed")
            
            # Call the method and expect an error
            with pytest.raises(OddsFetcherError) as exc_info:
                odds_fetcher.get_game_odds("basketball_nba", "us", ["h2h"])
            
            assert "All odds providers failed" in str(exc_info.value)

    def test_get_game_odds_sync_wrapper(self, odds_fetcher):
        """Test the sync wrapper method."""
        with patch.object(odds_fetcher, 'get_game_odds') as mock_get_odds:
            mock_get_odds.return_value = []
            
            odds_fetcher.get_game_odds_sync("basketball_nba", "us", ["h2h"])
            
            # Verify the sync wrapper calls the main method
            mock_get_odds.assert_called_once_with("basketball_nba", "us", ["h2h"])

    def test_normalize_book_odds(self, odds_fetcher):
        """Test bookmaker odds normalization."""
        bookmaker_data = {
            "title": "DraftKings",
            "markets": [
                {
                    "key": "h2h",
                    "outcomes": [
                        {"name": "Team A", "price": 1.91},
                        {"name": "Team B", "price": 1.91}
                    ]
                }
            ]
        }
        
        result = odds_fetcher._normalize_book_odds(bookmaker_data, "decimal")
        
        assert len(result) == 1
        book = result[0]
        assert book.bookmaker == "DraftKings"
        assert book.market == "h2h"
        assert len(book.selections) == 2

    def test_normalize_response(self, odds_fetcher):
        """Test complete response normalization."""
        response_data = [
            {
                "id": "game_1",
                "commence_time": "2024-01-15T19:30:00Z",
                "bookmakers": [
                    {
                        "title": "DraftKings",
                        "markets": [
                            {
                                "key": "h2h",
                                "outcomes": [
                                    {"name": "Team A", "price": 1.91},
                                    {"name": "Team B", "price": 1.91}
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
        
        result = odds_fetcher._normalize_response(response_data, "basketball_nba", "decimal")
        
        assert len(result) == 1
        game = result[0]
        assert game.sport_key == "basketball_nba"
        assert game.game_id == "game_1"
        assert game.commence_time == "2024-01-15T19:30:00Z"
        assert len(game.books) == 1

    def test_odds_fetcher_error(self):
        """Test custom OddsFetcherError exception."""
        error = OddsFetcherError("Test error", 429)
        assert str(error) == "Test error"
        assert error.status_code == 429
        
        error_no_status = OddsFetcherError("Test error")
        assert error_no_status.status_code is None

    def test_fetch_fallback_odds_not_configured(self, odds_fetcher):
        """Test that fallback fetch raises error when not configured."""
        with pytest.raises(OddsFetcherError) as exc_info:
            odds_fetcher._fetch_fallback_odds("basketball_nba", "us", "h2h")
        
        assert "Fallback API not configured" in str(exc_info.value)

    def test_fetch_fallback_odds_configured(self, sample_fallback_response):
        """Test fallback odds fetching when configured."""
        # Mock environment variables for fallback
        with patch.dict('os.environ', {
            'FALLBACK_ODDS_API_KEY': 'fallback_key',
            'FALLBACK_ODDS_BASE_URL': 'https://api.fallback.com'
        }):
            odds_fetcher = OddsFetcherTool()
            
            # Mock the fallback API fetcher
            with patch('tools.odds_fetcher_tool.ApiFetcher') as mock_api_fetcher_class:
                mock_fetcher = Mock()
                mock_fetcher.fetch.return_value = sample_fallback_response
                mock_api_fetcher_class.return_value = mock_fetcher
                
                result = odds_fetcher._fetch_fallback_odds("basketball_nba", "us", "h2h")
                
                assert len(result) == 1
                game = result[0]
                assert game.sport_key == "basketball_nba"
                assert len(game.books) == 1
