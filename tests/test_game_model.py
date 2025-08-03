import pytest
from models.game import CanonicalGameObject
from tools.game_repository import GameRepository
from datetime import datetime
from pydantic import ValidationError

def test_valid_game_model():
    game = CanonicalGameObject(
        game_id="PHX_DEN_2024-12-01",
        home_team="Suns",
        away_team="Nuggets",
        game_time=datetime.now(),
        shutdown_probability=0.1
    )
    assert game.game_id == "PHX_DEN_2024-12-01"
    assert 0.0 <= game.shutdown_probability <= 1.0

def test_invalid_shutdown_probability():
    with pytest.raises(ValidationError):
        CanonicalGameObject(
            game_id="ABC",
            home_team="A",
            away_team="B",
            game_time=datetime.now(),
            shutdown_probability=1.5  # Invalid
        )

def test_game_repository():
    repo = GameRepository()
    game = CanonicalGameObject(
        game_id="LAL_GSW_2024-08-03",
        home_team="Lakers",
        away_team="Warriors",
        game_time=datetime.strptime("2024-08-03T20:00:00", "%Y-%m-%dT%H:%M:%S"),
        odds={"FanDuel": -110, "DraftKings": -115},
        shutdown_probability=0.2
    )
    
    # Test add and get
    repo.add_game(game)
    retrieved = repo.get_game("LAL_GSW_2024-08-03")
    assert retrieved == game
    
    # Test update
    repo.update_game("LAL_GSW_2024-08-03", shutdown_probability=0.3)
    updated = repo.get_game("LAL_GSW_2024-08-03")
    assert updated.shutdown_probability == 0.3
    
    # Test all_games
    assert len(repo.all_games()) == 1 