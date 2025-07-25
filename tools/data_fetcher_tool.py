from typing import List, Dict, Callable
from tools.cache_utils import redis_cache
import requests
from config import BALLDONTLIE_API_KEY
import time
import logging
from nba_api.stats.endpoints import playergamelog, leaguedashteamstats

logging.basicConfig(level=logging.INFO)

class DataUnavailableError(Exception):
    pass

class DataSourceManager:
    def __init__(self, sources: List[Callable]):
        self.sources = sources

    def get(self, *args, **kwargs):
        last_exception = None
        for source in self.sources:
            try:
                return source(*args, **kwargs)
            except Exception as e:
                last_exception = e
        raise DataUnavailableError("All data sources failed") from last_exception

class DataFetcherTool:
    def _api_request_with_error_handling(self, url, headers, params=None, max_retries=3, backoff_factor=2):
        """
        Make a GET request to the specified URL with error handling for common API issues.

        Parameters:
            url (str): The API endpoint URL.
            headers (dict): HTTP headers to include in the request.
            params (dict, optional): Query parameters for the request.
            max_retries (int, optional): Maximum number of retries for rate limiting or connection errors. Default is 3.
            backoff_factor (int, optional): Exponential backoff multiplier. Default is 2.

        Returns:
            dict: The JSON response from the API.

        Raises:
            DataUnavailableError: If the request fails after all retries or encounters a handled error.
        """
        retries = 0
        delay = 1
        while retries < max_retries:
            try:
                response = requests.get(url, headers=headers, params=params, timeout=10)
                if response.status_code == 401:
                    logging.error(f"401 Unauthorized: {url}")
                    raise DataUnavailableError("Unauthorized: Check your API key and permissions.")
                if response.status_code == 404:
                    logging.error(f"404 Not Found: {url}")
                    raise DataUnavailableError("Not Found: The requested resource does not exist.")
                if response.status_code == 429:
                    logging.warning(f"429 Rate Limit: {url}. Retrying in {delay} seconds...")
                    time.sleep(delay)
                    retries += 1
                    delay *= backoff_factor
                    continue
                response.raise_for_status()
                return response.json()
            except requests.exceptions.Timeout:
                logging.error(f"Timeout occurred for {url}. Retrying in {delay} seconds...")
                time.sleep(delay)
                retries += 1
                delay *= backoff_factor
            except requests.exceptions.ConnectionError:
                logging.error(f"Connection error for {url}. Retrying in {delay} seconds...")
                time.sleep(delay)
                retries += 1
                delay *= backoff_factor
            except Exception as e:
                logging.error(f"Unexpected error for {url}: {e}")
                raise DataUnavailableError(str(e))
        raise DataUnavailableError(f"Failed after {max_retries} retries: {url}")

    @redis_cache()
    def get_game_schedule(self, date: str) -> dict:
        """
        Fetch the NBA game schedule for a given date using the BallDon'tLie API.
        Utilizes Redis caching and automatic fallback if the primary source fails.

        Parameters:
            date (str): The date for which to fetch the game schedule (format: 'YYYY-MM-DD').

        Returns:
            dict: The API response containing game schedule data.

        Raises:
            DataUnavailableError: If all data sources fail or the API returns an error.

        Example:
            >>> fetcher = DataFetcherTool()
            >>> schedule = fetcher.get_game_schedule('2024-06-01')
            >>> print(schedule)
        """
        def primary_source(date):
            url = "https://api.balldontlie.io/v1/games"
            headers = {"Authorization": BALLDONTLIE_API_KEY}
            params = {"dates[]": date}
            return self._api_request_with_error_handling(url, headers, params)

        def fallback_source(date):
            logging.warning("Using fallback source for get_game_schedule.")
            return {"data": [], "meta": {"next_cursor": None, "per_page": 25}, "source": "fallback"}

        manager = DataSourceManager([primary_source, fallback_source])
        return manager.get(date)

    def get_player_stats(self, player_ids: List[int], season: int) -> dict:
        """
        Fetch player statistics for a list of player IDs and a given season using nba_api.

        Parameters:
            player_ids (List[int]): List of player IDs to fetch stats for.
            season (int): The NBA season year.

        Returns:
            dict: Mapping of player_id to recent games (list of dicts).
        """
        result = {}
        for pid in player_ids:
            try:
                gamelog = playergamelog.PlayerGameLog(player_id=pid, season=season)
                games = gamelog.get_normalized_dict()["PlayerGameLog"]
                result[pid] = games
            except Exception as e:
                logging.error(f"Failed to fetch stats for player {pid}: {e}")
                result[pid] = []
        return result

    def get_team_stats(self, team_ids: List[int], season: int) -> dict:
        """
        Fetch team statistics for a list of team IDs and a given season using nba_api.

        Parameters:
            team_ids (List[int]): List of team IDs to fetch stats for.
            season (int): The NBA season year.

        Returns:
            dict: Mapping of team_id to team stats (dict).
        """
        try:
            stats = leaguedashteamstats.LeagueDashTeamStats(season=season)
            all_teams = stats.get_normalized_dict()["LeagueDashTeamStats"]
            filtered = [team for team in all_teams if team["TEAM_ID"] in team_ids]
            return {team["TEAM_ID"]: team for team in filtered}
        except Exception as e:
            logging.error(f"Failed to fetch team stats: {e}")
            return {} 