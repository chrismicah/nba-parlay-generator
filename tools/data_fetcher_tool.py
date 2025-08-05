from typing import List, Dict, Callable
from tools.cache_utils import redis_cache
from tools.api_fetcher import ApiFetcher
from config import BALLDONTLIE_API_KEY
import json
import logging
from nba_api.stats.endpoints import playergamelog, leaguedashteamstats, playergamelogs

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
    def __init__(self):
        self.api_fetcher = ApiFetcher()

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
            return self.api_fetcher.fetch(url, headers, params)

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
                gamelog = playergamelogs.PlayerGameLogs(player_id_nullable=pid, season_nullable=season, season_type_nullable='Regular Season')
                games = gamelog.get_data_frames()[0].to_dict('records')
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