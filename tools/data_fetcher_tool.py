import os
from typing import Optional, List, Dict, Callable
from datetime import datetime
import aiohttp
import json
import logging
try:
    from tools.cache_utils import redis_cache
except ImportError:
    # Fallback decorator when redis is not available
    def redis_cache(ttl: int = 600):
        def decorator(func):
            return func  # Just return the function unchanged
        return decorator
from tools.api_fetcher import ApiFetcher
from config import BALLDONTLIE_API_KEY, API_SPORTS_KEY
from nba_api.stats.endpoints import playergamelog, leaguedashteamstats, playergamelogs

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logging.basicConfig(level=logging.INFO)

class DataUnavailableError(Exception):
    pass

class DataSourceManager:
    def __init__(self, sport: str):
        self.sport = sport
        self.primary = SportFactory.create_data_fetcher(sport)
        self.fallback = SportFactory.create_data_fetcher(sport) if sport == "nfl" else None

    async def get_game_schedule(self, date: str):
        try:
            return await self.primary.get_game_schedule(date)
        except Exception as e:
            logging.warning(f"Primary data source failed for {self.sport} game schedule: {e}")
            if self.fallback:
                return await self.fallback.get_game_schedule(date)
            raise e

    async def get_player_stats(self, player_ids: List[str], season: str):
        try:
            return await self.primary.get_player_stats(player_ids, season)
        except Exception as e:
            logging.warning(f"Primary data source failed for {self.sport} player stats: {e}")
            if self.fallback:
                return await self.fallback.get_player_stats(player_ids, season)
            raise e

    async def get_team_stats(self, team_ids: List[str], season: str):
        try:
            return await self.primary.get_team_stats(team_ids, season)
        except Exception as e:
            logging.warning(f"Primary data source failed for {self.sport} team stats: {e}")
            if self.fallback:
                return await self.fallback.get_team_stats(team_ids, season)
            raise e


# Legacy DataSourceManager for backward compatibility
class LegacyDataSourceManager:
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

class MarketNormalizer:
    def __init__(self):
        self.team_aliases = {
            "nba": {
                "LAL": "Los Angeles Lakers", "BOS": "Boston Celtics", "GSW": "Golden State Warriors",
                "MIA": "Miami Heat", "CHI": "Chicago Bulls", "NYK": "New York Knicks",
                "BRK": "Brooklyn Nets", "PHI": "Philadelphia 76ers", "TOR": "Toronto Raptors",
                "MIL": "Milwaukee Bucks", "CLE": "Cleveland Cavaliers", "DET": "Detroit Pistons",
                "IND": "Indiana Pacers", "ATL": "Atlanta Hawks", "CHA": "Charlotte Hornets",
                "ORL": "Orlando Magic", "WAS": "Washington Wizards", "DEN": "Denver Nuggets",
                "MIN": "Minnesota Timberwolves", "OKC": "Oklahoma City Thunder", "POR": "Portland Trail Blazers",
                "UTA": "Utah Jazz", "DAL": "Dallas Mavericks", "HOU": "Houston Rockets",
                "MEM": "Memphis Grizzlies", "NOP": "New Orleans Pelicans", "SAS": "San Antonio Spurs",
                "LAC": "Los Angeles Clippers", "PHX": "Phoenix Suns", "SAC": "Sacramento Kings"
            },
            "nfl": {
                "KC": "Kansas City Chiefs", "GB": "Green Bay Packers", "NE": "New England Patriots",
                "DAL": "Dallas Cowboys", "PIT": "Pittsburgh Steelers", "BAL": "Baltimore Ravens",
                "SF": "San Francisco 49ers", "SEA": "Seattle Seahawks", "DEN": "Denver Broncos",
                "LV": "Las Vegas Raiders", "LAC": "Los Angeles Chargers", "BUF": "Buffalo Bills",
                "MIA": "Miami Dolphins", "NYJ": "New York Jets", "CIN": "Cincinnati Bengals",
                "CLE": "Cleveland Browns", "HOU": "Houston Texans", "IND": "Indianapolis Colts",
                "JAX": "Jacksonville Jaguars", "TEN": "Tennessee Titans", "PHI": "Philadelphia Eagles",
                "NYG": "New York Giants", "WAS": "Washington Commanders", "CHI": "Chicago Bears",
                "DET": "Detroit Lions", "MIN": "Minnesota Vikings", "ATL": "Atlanta Falcons",
                "CAR": "Carolina Panthers", "NO": "New Orleans Saints", "TB": "Tampa Bay Buccaneers",
                "ARI": "Arizona Cardinals", "LAR": "Los Angeles Rams"
            }
        }
        self.player_aliases = {
            "nba": {"LeBron James": "L. James", "Stephen Curry": "S. Curry"},
            "nfl": {"Patrick Mahomes": "P. Mahomes", "Josh Allen": "J. Allen"}
        }

    def normalize_game(self, game: dict, sport: str):
        team_map = self.team_aliases.get(sport.lower(), {})
        if "home_team" in game:
            game["home_team"] = team_map.get(game["home_team"], game["home_team"])
        if "away_team" in game:
            game["away_team"] = team_map.get(game["away_team"], game["away_team"])
        return game

    def normalize_stats(self, stats: dict, sport: str):
        player_map = self.player_aliases.get(sport.lower(), {})
        if "player_name" in stats:
            stats["player_name"] = player_map.get(stats["player_name"], stats["player_name"])
        return stats


class NBADataFetcher:
    def __init__(self):
        self.api_fetcher = ApiFetcher()

    async def get_game_schedule(self, date: str):
        """Fetch NBA game schedule using BallDontLie API"""
        def primary_source(date):
            url = "https://api.balldontlie.io/v1/games"
            headers = {"Authorization": BALLDONTLIE_API_KEY}
            params = {"dates[]": date}
            response = self.api_fetcher.fetch(url, headers, params)
            return [
                {
                    "game_id": str(game["id"]),
                    "home_team": game["home_team"]["full_name"],
                    "away_team": game["visitor_team"]["full_name"],
                    "game_time": game["date"]
                } for game in response.get("data", [])
            ]
        
        def fallback_source(date):
            logging.warning("Using NBA API fallback for game schedule.")
            from nba_api.stats.endpoints import leaguegamefinder
            games = leaguegamefinder.LeagueGameFinder(date_from_nullable=date).get_data_frames()[0]
            return [
                {
                    "game_id": str(game["GAME_ID"]),
                    "home_team": game["MATCHUP"].split(" vs. ")[0] if " vs. " in game["MATCHUP"] else game["TEAM_NAME"],
                    "away_team": game["MATCHUP"].split(" @ ")[0] if " @ " in game["MATCHUP"] else game["TEAM_NAME"],
                    "game_time": game["GAME_DATE"]
                } for game in games.to_dict("records")
            ]
        
        manager = LegacyDataSourceManager([primary_source, fallback_source])
        return manager.get(date)

    async def get_player_stats(self, player_ids: List[str], season: str):
        """Fetch NBA player stats using nba_api"""
        result = []
        for player_id in player_ids:
            try:
                gamelog = playergamelogs.PlayerGameLogs(player_id_nullable=int(player_id), season_nullable=season, season_type_nullable='Regular Season')
                games = gamelog.get_data_frames()[0].to_dict('records')
                result.append({"player_id": player_id, "stats": games})
            except Exception as e:
                logging.error(f"Failed to fetch NBA stats for player {player_id}: {e}")
                result.append({"player_id": player_id, "stats": []})
        return result

    async def get_team_stats(self, team_ids: List[str], season: str):
        """Fetch NBA team stats using nba_api"""
        try:
            stats = leaguedashteamstats.LeagueDashTeamStats(season=season)
            all_teams = stats.get_normalized_dict()["LeagueDashTeamStats"]
            team_ids_int = [int(tid) for tid in team_ids]
            filtered = [team for team in all_teams if team["TEAM_ID"] in team_ids_int]
            return [{"team_id": str(team["TEAM_ID"]), "stats": team} for team in filtered]
        except Exception as e:
            logging.error(f"Failed to fetch NBA team stats: {e}")
            return []


class NFLDataFetcher:
    def __init__(self):
        self.api_key = API_SPORTS_KEY or os.getenv("api-football")

    async def get_game_schedule(self, date: str):
        """Fetch NFL game schedule using API-NFL with ESPN fallback"""
        async with aiohttp.ClientSession() as session:
            # Primary: API-NFL
            if self.api_key:
                try:
                    async with session.get(
                        f"https://v1.american-football.api-sports.io/games",
                        headers={"x-apisports-key": self.api_key},
                        params={"season": "2025", "date": date}
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            return [
                                {
                                    "game_id": str(game["game"]["id"]),
                                    "home_team": game["teams"]["home"]["name"],
                                    "away_team": game["teams"]["away"]["name"],
                                    "game_time": game["game"]["date"]
                                } for game in data.get("response", [])
                            ]
                except Exception as e:
                    logging.warning(f"API-NFL failed: {e}, falling back to ESPN")
            
            # Fallback: ESPN API (public endpoint, no auth required)
            try:
                date_formatted = date.replace("-", "")
                async with session.get(
                    f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
                    params={"dates": date_formatted}
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return [
                            {
                                "game_id": str(game["id"]),
                                "home_team": next((c["team"]["name"] for c in game["competitions"][0]["competitors"] if c["homeAway"] == "home"), "Unknown"),
                                "away_team": next((c["team"]["name"] for c in game["competitions"][0]["competitors"] if c["homeAway"] == "away"), "Unknown"),
                                "game_time": game["date"]
                            } for game in data.get("events", [])
                        ]
            except Exception as e:
                logging.error(f"ESPN NFL API fallback failed: {e}")
                return []

    async def get_player_stats(self, player_ids: List[str], season: str):
        """Fetch NFL player stats using API-NFL with ESPN fallback"""
        async with aiohttp.ClientSession() as session:
            stats = []
            for player_id in player_ids:
                # Primary: API-NFL
                if self.api_key:
                    try:
                        async with session.get(
                            f"https://v1.american-football.api-sports.io/players/statistics",
                            headers={"x-apisports-key": self.api_key},
                            params={"id": player_id, "season": season}
                        ) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                stats.append({"player_id": player_id, "stats": data.get("response", [])})
                                continue
                    except Exception as e:
                        logging.warning(f"API-NFL player stats failed for {player_id}: {e}")
                
                # Fallback: ESPN API (public endpoint)
                try:
                    async with session.get(
                        f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/athletes/{player_id}/stats"
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            stats.append({"player_id": player_id, "stats": data})
                        else:
                            stats.append({"player_id": player_id, "stats": []})
                except Exception as e:
                    logging.error(f"ESPN player stats failed for {player_id}: {e}")
                    stats.append({"player_id": player_id, "stats": []})
            return stats

    async def get_team_stats(self, team_ids: List[str], season: str):
        """Fetch NFL team stats using API-NFL with ESPN fallback"""
        async with aiohttp.ClientSession() as session:
            # Primary: API-NFL
            if self.api_key:
                try:
                    stats = []
                    for team_id in team_ids:
                        async with session.get(
                            f"https://v1.american-football.api-sports.io/teams/statistics",
                            headers={"x-apisports-key": self.api_key},
                            params={"id": team_id, "season": season}
                        ) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                stats.append({"team_id": team_id, "stats": data.get("response", {})})
                            else:
                                stats.append({"team_id": team_id, "stats": {}})
                    return stats
                except Exception as e:
                    logging.warning(f"API-NFL team stats failed: {e}, falling back to ESPN")
            
            # Fallback: ESPN API (public endpoint)
            try:
                async with session.get(
                    "https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams"
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        all_teams = data.get("teams", [])
                        return [{"team_id": team_id, "stats": team} for team in all_teams if str(team.get("id")) in team_ids]
            except Exception as e:
                logging.error(f"ESPN team stats fallback failed: {e}")
                return []


class SportFactory:
    @staticmethod
    def create_data_fetcher(sport: str):
        if sport.lower() == "nba":
            return NBADataFetcher()
        elif sport.lower() == "nfl":
            return NFLDataFetcher()
        else:
            raise ValueError(f"Unsupported sport: {sport}")


class DataFetcherTool:
    def __init__(self, sport: str = "nba"):
        self.sport = sport.lower()
        self.fetcher = SportFactory.create_data_fetcher(sport)
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(host="localhost", port=6379, db=0)
            except Exception:
                logging.warning("Redis connection failed, caching disabled")
                self.redis_client = None
        else:
            logging.warning("Redis not installed, caching disabled")
            self.redis_client = None
        self.normalizer = MarketNormalizer()

    async def get_game_schedule(self, date: str):
        """
        Fetch game schedule for a given date.
        Supports NBA and NFL with caching and normalization.

        Parameters:
            date (str): The date for which to fetch the game schedule (format: 'YYYY-MM-DD').

        Returns:
            list: List of normalized game data.
        """
        cache_key = f"{self.sport}:game_schedule:{date}"
        
        # Try cache first
        if self.redis_client:
            try:
                cached = self.redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception:
                pass
        
        # Fetch data
        games = await self.fetcher.get_game_schedule(date)
        normalized_games = [self.normalizer.normalize_game(game, self.sport) for game in games]
        
        # Cache results
        if self.redis_client and normalized_games:
            try:
                self.redis_client.setex(cache_key, 3600, json.dumps(normalized_games))
            except Exception:
                pass
        
        return normalized_games

    async def get_player_stats(self, player_ids: List[str], season: str):
        """
        Fetch player statistics for a list of player IDs and a given season.
        Supports NBA and NFL with caching and normalization.

        Parameters:
            player_ids (List[str]): List of player IDs to fetch stats for.
            season (str): The season year.

        Returns:
            list: List of normalized player stats.
        """
        player_ids_str = ",".join(player_ids)
        cache_key = f"{self.sport}:player_stats:{player_ids_str}:{season}"
        
        # Try cache first
        if self.redis_client:
            try:
                cached = self.redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception:
                pass
        
        # Fetch data
        stats = await self.fetcher.get_player_stats(player_ids, season)
        normalized_stats = [self.normalizer.normalize_stats(stat, self.sport) for stat in stats]
        
        # Cache results
        if self.redis_client and normalized_stats:
            try:
                self.redis_client.setex(cache_key, 3600, json.dumps(normalized_stats))
            except Exception:
                pass
        
        return normalized_stats

    async def get_team_stats(self, team_ids: List[str], season: str):
        """
        Fetch team statistics for a list of team IDs and a given season.
        Supports NBA and NFL with caching and normalization.

        Parameters:
            team_ids (List[str]): List of team IDs to fetch stats for.
            season (str): The season year.

        Returns:
            list: List of normalized team stats.
        """
        team_ids_str = ",".join(team_ids)
        cache_key = f"{self.sport}:team_stats:{team_ids_str}:{season}"
        
        # Try cache first
        if self.redis_client:
            try:
                cached = self.redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception:
                pass
        
        # Fetch data
        stats = await self.fetcher.get_team_stats(team_ids, season)
        normalized_stats = [self.normalizer.normalize_stats(stat, self.sport) for stat in stats]
        
        # Cache results
        if self.redis_client and normalized_stats:
            try:
                self.redis_client.setex(cache_key, 3600, json.dumps(normalized_stats))
            except Exception:
                pass
        
        return normalized_stats