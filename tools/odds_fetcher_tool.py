from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

from tools.api_fetcher import ApiFetcher
from config import THE_ODDS_API_KEY

# Set up logging
logger = logging.getLogger(__name__)


@dataclass
class Selection:
    """A single betting selection/outcome."""
    name: str
    price_decimal: float
    line: Optional[float] = None


@dataclass
class BookOdds:
    """Odds from a specific bookmaker for a specific market."""
    bookmaker: str
    market: str
    selections: List[Selection]


@dataclass
class GameOdds:
    """Complete odds data for a single game."""
    sport_key: str
    game_id: str
    commence_time: str
    books: List[BookOdds]


class OddsFetcherError(Exception):
    """Custom exception for odds fetching errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class OddsFetcherTool:
    """Tool for fetching and normalizing odds data from The Odds API with fallback support."""
    
    def __init__(self):
        """Initialize the OddsFetcherTool with API configuration."""
        self.api_fetcher = ApiFetcher(api_key=THE_ODDS_API_KEY)
        
        # Optional fallback API configuration
        self.fallback_api_key = os.getenv("FALLBACK_ODDS_API_KEY")
        self.fallback_base_url = os.getenv("FALLBACK_ODDS_BASE_URL", "https://api.fallback-odds.com")
        
        logger.info("OddsFetcherTool initialized")

    def american_to_decimal(self, american_odds: float) -> float:
        """
        Convert American odds to decimal odds.
        
        Args:
            american_odds: American odds (e.g., +120, -150)
            
        Returns:
            Decimal odds (e.g., 2.2, 1.6667)
        """
        if american_odds > 0:
            return (american_odds / 100) + 1
        else:
            return (100 / abs(american_odds)) + 1

    def _safe_float(self, value: Any) -> Optional[float]:
        """
        Safely convert a value to float, returning None if conversion fails.
        
        Args:
            value: Value to convert
            
        Returns:
            Float value or None if conversion fails
        """
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _normalize_selection(self, outcome: Dict[str, Any], odds_format: str = "decimal") -> Selection:
        """
        Normalize a single selection/outcome from API response.
        
        Args:
            outcome: Raw outcome data from API
            odds_format: Format of odds in response
            
        Returns:
            Normalized Selection object
        """
        name = outcome.get("name", "")
        price = outcome.get("price")
        point = outcome.get("point")
        
        # Convert price to decimal if needed
        if odds_format == "american" and price is not None:
            price_decimal = self.american_to_decimal(float(price))
        else:
            price_decimal = self._safe_float(price) or 0.0
        
        # Convert line to float
        line = self._safe_float(point)
        
        return Selection(
            name=name,
            price_decimal=price_decimal,
            line=line
        )

    def _normalize_book_odds(self, bookmaker: Dict[str, Any], odds_format: str = "decimal") -> List[BookOdds]:
        """
        Normalize bookmaker odds from API response.
        
        Args:
            bookmaker: Raw bookmaker data from API
            odds_format: Format of odds in response
            
        Returns:
            List of normalized BookOdds objects
        """
        bookmaker_name = bookmaker.get("title", "")
        markets = bookmaker.get("markets", [])
        
        normalized_books = []
        for market in markets:
            market_key = market.get("key", "")
            outcomes = market.get("outcomes", [])
            
            selections = [
                self._normalize_selection(outcome, odds_format)
                for outcome in outcomes
            ]
            
            normalized_books.append(BookOdds(
                bookmaker=bookmaker_name,
                market=market_key,
                selections=selections
            ))
        
        return normalized_books

    def _normalize_response(self, response: List[Dict[str, Any]], sport_key: str, odds_format: str = "decimal") -> List[GameOdds]:
        """
        Normalize the complete API response.
        
        Args:
            response: Raw API response
            sport_key: Sport key for the request
            odds_format: Format of odds in response
            
        Returns:
            List of normalized GameOdds objects
        """
        normalized_games = []
        
        for game in response:
            game_id = game.get("id", "")
            commence_time = game.get("commence_time", "")
            bookmakers = game.get("bookmakers", [])
            
            all_books = []
            for bookmaker in bookmakers:
                books = self._normalize_book_odds(bookmaker, odds_format)
                all_books.extend(books)
            
            normalized_games.append(GameOdds(
                sport_key=sport_key,
                game_id=game_id,
                commence_time=commence_time,
                books=all_books
            ))
        
        return normalized_games

    def _fetch_fallback_odds(self, sport_key: str, regions: str, markets: str) -> List[GameOdds]:
        """
        Fetch odds from fallback API if configured.
        
        Args:
            sport_key: Sport key for the request
            regions: Regions to fetch odds for
            markets: Markets to fetch odds for
            
        Returns:
            List of normalized GameOdds objects
            
        Raises:
            OddsFetcherError: If fallback is not configured or fails
        """
        if not self.fallback_api_key:
            raise OddsFetcherError("Fallback API not configured")
        
        logger.info("Attempting fallback odds fetch")
        
        try:
            # Create fallback API fetcher
            fallback_fetcher = ApiFetcher(api_key=self.fallback_api_key)
            
            # Construct fallback URL (adjust based on actual fallback API)
            url = f"{self.fallback_base_url}/odds/{sport_key}"
            params = {
                "regions": regions,
                "markets": markets,
                "apiKey": self.fallback_api_key,
                "oddsFormat": "american"  # Fallback might use American odds
            }
            
            response = fallback_fetcher.fetch(url, params=params)
            
            # Normalize with American odds format
            normalized_games = self._normalize_response(response, sport_key, odds_format="american")
            
            logger.info(f"Fallback fetch successful: {len(normalized_games)} games")
            return normalized_games
            
        except Exception as e:
            logger.error(f"Fallback API failed: {e}")
            raise OddsFetcherError(f"Fallback API failed: {e}")

    def get_game_odds(self, sport_key: str, regions: str = "us", markets: Optional[List[str]] = None) -> List[GameOdds]:
        """
        Fetch game odds from The Odds API with fallback support.
        
        Args:
            sport_key: The sport key (e.g., 'basketball_nba')
            regions: The regions to fetch odds for (e.g., 'us')
            markets: The markets to fetch odds for (e.g., ['h2h', 'spreads', 'totals'])
            
        Returns:
            List of normalized GameOdds objects
            
        Raises:
            OddsFetcherError: For API errors (401, 403, 404, 429) or other failures
        """
        # Default markets if none provided
        if markets is None:
            markets = ["h2h", "spreads", "totals"]
        
        # Convert markets list to comma-separated string
        markets_str = ",".join(markets)
        
        logger.info(f"Fetching odds for sport: {sport_key}, regions: {regions}, markets: {markets_str}")
        
        try:
            # Primary API call
            url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
            params = {
                "regions": regions,
                "markets": markets_str,
                "apiKey": self.api_fetcher.api_key,
                "oddsFormat": "decimal",
                "dateFormat": "iso"
            }
            
            response = self.api_fetcher.fetch(url, params=params)
            
            # Normalize the response
            normalized_games = self._normalize_response(response, sport_key, odds_format="decimal")
            
            logger.info(f"Successfully fetched {len(normalized_games)} games with {sum(len(game.books) for game in normalized_games)} total bookmaker markets")
            return normalized_games
            
        except Exception as e:
            logger.warning(f"Primary API failed: {e}")
            
            # Try fallback if primary fails
            try:
                return self._fetch_fallback_odds(sport_key, regions, markets_str)
            except Exception as fallback_error:
                logger.error(f"Both primary and fallback APIs failed. Primary: {e}, Fallback: {fallback_error}")
                raise OddsFetcherError(f"All odds providers failed. Last error: {fallback_error}")

    def get_game_odds_sync(self, sport_key: str, regions: str = "us", markets: Optional[List[str]] = None) -> List[GameOdds]:
        """
        Synchronous wrapper for get_game_odds for CLI/tests.
        
        Args:
            sport_key: The sport key (e.g., 'basketball_nba')
            regions: The regions to fetch odds for (e.g., 'us')
            markets: The markets to fetch odds for (e.g., ['h2h', 'spreads', 'totals'])
            
        Returns:
            List of normalized GameOdds objects
        """
        return self.get_game_odds(sport_key, regions, markets)