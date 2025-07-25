import time
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from tools.data_fetcher_tool import DataFetcherTool


def test_get_player_stats_lebron():
    fetcher = DataFetcherTool()
    player_id = 2544  # LeBron James
    season = 2023
    stats = fetcher.get_player_stats([player_id], season)
    assert player_id in stats
    games = stats[player_id]
    assert isinstance(games, list)
    assert len(games) > 0
    # Check for expected keys in the first game
    first_game = games[0]
    assert 'PTS' in first_game
    assert 'REB' in first_game
    time.sleep(1.5)  # Avoid rate-limiting 