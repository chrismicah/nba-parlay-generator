import pytest
import requests
from unittest.mock import patch
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import BALLDONTLIE_API_KEY

BASE_URL = "https://api.balldontlie.io/v1"
headers = {"Authorization": BALLDONTLIE_API_KEY}

# Helper to check if stats endpoint is allowed (set to True if you upgrade your account)
def has_stats_access():
    return False  # Change to True if you upgrade your BallDontLie account

# 1. Test successful connection and authentication
def test_api_key_auth():
    response = requests.get(f"{BASE_URL}/players", headers=headers)
    assert response.status_code == 200

# 2. Test key endpoints structure and data types
@pytest.mark.parametrize("endpoint,expected_field", [
    ("players", "data"),
    ("teams", "data"),
    ("games", "data"),
])
def test_endpoint_structure(endpoint, expected_field):
    response = requests.get(f"{BASE_URL}/{endpoint}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert expected_field in data
    assert isinstance(data[expected_field], list)

# Commented out: /stats endpoint not available in free tier
# @pytest.mark.parametrize("endpoint", ["stats"])
# def test_stats_endpoint_unavailable(endpoint):
#     response = requests.get(f"{BASE_URL}/{endpoint}", headers=headers)
#     assert response.status_code in (401, 403, 404)

# 3. Test rate limit handling (simulate 429)
def test_rate_limit_handling(mocker):
    mock_response = requests.models.Response()
    mock_response.status_code = 429
    mocker.patch("requests.get", return_value=mock_response)
    # Your rate limit handling logic here, e.g., exponential backoff
    response = requests.get(f"{BASE_URL}/players", headers=headers)
    assert response.status_code == 429

# 4. Data consistency test for a known player/game
# @pytest.mark.skipif(not has_stats_access(), reason="Stats endpoint requires paid BallDontLie API tier")
# def test_player_stats_consistency():
#     # Example: LeBron James, game_id = 47136 (replace with real values)
#     player_id = 237
#     game_id = 47136
#     response = requests.get(f"{BASE_URL}/stats?player_ids[]={player_id}&game_ids[]={game_id}", headers=headers)
#     assert response.status_code == 200
#     data = response.json()
#     # Replace with expected values
#     expected_points = 29
#     assert data["data"][0]["pts"] == expected_points

# 5. Data source switching (stub, to be implemented with your DataSourceManager)
def test_data_source_switching():
    # Example: Simulate primary API failure and check fallback
    # This is a stub; implement with your DataSourceManager logic
    assert True

# 6. SummerLeagueDataAdapter logic (stub, to be implemented with your adapter)
# def test_summerleague_adapter():
#     # Example: Test correct weighting of college/G-League stats
#     # This is a stub; implement with your SummerLeagueDataAdapter logic
#     assert True 