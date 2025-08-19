import pytest
from models.game import CanonicalGameObject
from datetime import datetime
from pydantic import ValidationError


def test_nfl_game_object_creation():
    """Test creating NFL game objects with sport field."""
    game = CanonicalGameObject(
        game_id="KC_BAL_2025-09-05",
        sport="nfl",
        home_team="Kansas City Chiefs",
        away_team="Baltimore Ravens",
        game_time=datetime(2025, 9, 5, 20, 0, 0),
        shutdown_probability=0.15
    )
    
    assert game.game_id == "KC_BAL_2025-09-05"
    assert game.sport == "nfl"
    assert game.home_team == "Kansas City Chiefs"
    assert game.away_team == "Baltimore Ravens"
    assert game.shutdown_probability == 0.15


def test_nba_game_object_default_sport():
    """Test NBA game objects default to sport='nba' for backward compatibility."""
    game = CanonicalGameObject(
        game_id="LAL_GSW_2024-12-15",
        home_team="Los Angeles Lakers",
        away_team="Golden State Warriors",
        game_time=datetime(2024, 12, 15, 19, 30, 0),
        shutdown_probability=0.08
    )
    
    assert game.sport == "nba"  # Default value
    assert game.game_id == "LAL_GSW_2024-12-15"


def test_explicit_nba_sport_field():
    """Test explicitly setting sport='nba'."""
    game = CanonicalGameObject(
        game_id="BOS_MIA_2024-12-20",
        sport="nba",
        home_team="Boston Celtics",
        away_team="Miami Heat",
        game_time=datetime(2024, 12, 20, 20, 0, 0)
    )
    
    assert game.sport == "nba"
    assert game.home_team == "Boston Celtics"


def test_nfl_game_with_weather_conditions():
    """Test NFL game with NFL-specific fields using extra='allow'."""
    game = CanonicalGameObject(
        game_id="GB_CHI_2025-12-01",
        sport="nfl",
        home_team="Green Bay Packers",
        away_team="Chicago Bears",
        game_time=datetime(2025, 12, 1, 13, 0, 0),
        weather_conditions={"temperature": 28, "wind_speed": 15, "precipitation": "snow"},
        field_conditions="frozen",
        shutdown_probability=0.12
    )
    
    assert game.sport == "nfl"
    assert hasattr(game, "weather_conditions")
    assert hasattr(game, "field_conditions")
    assert game.weather_conditions["temperature"] == 28
    assert game.field_conditions == "frozen"


def test_nfl_game_with_odds_and_injuries():
    """Test NFL game with comprehensive data."""
    game = CanonicalGameObject(
        game_id="DAL_PHI_2025-10-15",
        sport="nfl",
        home_team="Dallas Cowboys",
        away_team="Philadelphia Eagles",
        game_time=datetime(2025, 10, 15, 16, 25, 0),
        odds={
            "moneyline_home": -120,
            "moneyline_away": 105,
            "spread_home": -2.5,
            "total": 47.5
        },
        injuries={
            "Dallas Cowboys": [
                {"player": "Dak Prescott", "status": "questionable", "injury": "ankle"}
            ],
            "Philadelphia Eagles": [
                {"player": "A.J. Brown", "status": "probable", "injury": "hamstring"}
            ]
        },
        advanced_stats={
            "home_offensive_efficiency": 0.73,
            "away_defensive_efficiency": 0.82,
            "weather_impact_factor": 1.05
        },
        shutdown_probability=0.09
    )
    
    assert game.sport == "nfl"
    assert game.odds["spread_home"] == -2.5
    assert "Dak Prescott" in str(game.injuries)
    assert game.advanced_stats["weather_impact_factor"] == 1.05


def test_sport_field_validation():
    """Test that sport field accepts any string value."""
    # Test with various sport values
    sports_to_test = ["nfl", "nba", "mlb", "nhl", "soccer", "tennis"]
    
    for sport in sports_to_test:
        game = CanonicalGameObject(
            game_id=f"TEAM1_TEAM2_2025-01-01_{sport}",
            sport=sport,
            home_team="Home Team",
            away_team="Away Team",
            game_time=datetime(2025, 1, 1, 12, 0, 0)
        )
        assert game.sport == sport


def test_nfl_vs_nba_comparison():
    """Test creating both NFL and NBA games to verify sport tagging."""
    nfl_game = CanonicalGameObject(
        game_id="TB_NO_2025-11-10",
        sport="nfl",
        home_team="Tampa Bay Buccaneers",
        away_team="New Orleans Saints",
        game_time=datetime(2025, 11, 10, 13, 0, 0),
        shutdown_probability=0.14
    )
    
    nba_game = CanonicalGameObject(
        game_id="LAC_DEN_2024-12-10",
        sport="nba",
        home_team="Los Angeles Clippers", 
        away_team="Denver Nuggets",
        game_time=datetime(2024, 12, 10, 21, 0, 0),
        shutdown_probability=0.07
    )
    
    # Verify sport differentiation
    assert nfl_game.sport == "nfl"
    assert nba_game.sport == "nba"
    assert nfl_game.game_id != nba_game.game_id
    
    # Verify both are valid CanonicalGameObjects
    assert isinstance(nfl_game, CanonicalGameObject)
    assert isinstance(nba_game, CanonicalGameObject)


def test_game_repository_with_mixed_sports():
    """Test GameRepository with both NFL and NBA games."""
    from tools.game_repository import GameRepository
    
    repo = GameRepository()
    
    # Add NFL game
    nfl_game = CanonicalGameObject(
        game_id="SF_SEA_2025-09-12",
        sport="nfl", 
        home_team="San Francisco 49ers",
        away_team="Seattle Seahawks",
        game_time=datetime(2025, 9, 12, 16, 25, 0),
        shutdown_probability=0.11
    )
    
    # Add NBA game
    nba_game = CanonicalGameObject(
        game_id="UTA_PHX_2024-12-05",
        sport="nba",
        home_team="Utah Jazz",
        away_team="Phoenix Suns", 
        game_time=datetime(2024, 12, 5, 21, 0, 0),
        shutdown_probability=0.06
    )
    
    # Add both games
    repo.add_game(nfl_game)
    repo.add_game(nba_game)
    
    # Retrieve and verify
    retrieved_nfl = repo.get_game("SF_SEA_2025-09-12")
    retrieved_nba = repo.get_game("UTA_PHX_2024-12-05")
    
    assert retrieved_nfl.sport == "nfl"
    assert retrieved_nba.sport == "nba"
    assert len(repo.all_games()) == 2
    
    # Test filtering by sport (if repository supports it)
    all_games = repo.all_games()
    nfl_games = [g for g in all_games if g.sport == "nfl"]
    nba_games = [g for g in all_games if g.sport == "nba"]
    
    assert len(nfl_games) == 1
    assert len(nba_games) == 1
    assert nfl_games[0].sport == "nfl"
    assert nba_games[0].sport == "nba"


def test_existing_nba_tests_still_work():
    """Test that existing NBA game creation still works with new sport field."""
    # This replicates tests from test_game_model.py to ensure backward compatibility
    game = CanonicalGameObject(
        game_id="PHX_DEN_2024-12-01",
        home_team="Suns",
        away_team="Nuggets", 
        game_time=datetime.now(),
        shutdown_probability=0.1
    )
    
    # Should default to NBA
    assert game.sport == "nba"
    assert game.game_id == "PHX_DEN_2024-12-01"
    assert 0.0 <= game.shutdown_probability <= 1.0


def test_invalid_shutdown_probability_with_sport():
    """Test validation still works with sport field."""
    with pytest.raises(ValidationError):
        CanonicalGameObject(
            game_id="TEST_GAME",
            sport="nfl",
            home_team="Team A",
            away_team="Team B",
            game_time=datetime.now(),
            shutdown_probability=1.5  # Invalid
        )


def test_nfl_game_serialization():
    """Test NFL game can be serialized/deserialized properly."""
    original_game = CanonicalGameObject(
        game_id="BUF_MIA_2025-10-20",
        sport="nfl",
        home_team="Buffalo Bills",
        away_team="Miami Dolphins",
        game_time=datetime(2025, 10, 20, 13, 0, 0),
        odds={"spread": -3.5, "total": 44.0},
        shutdown_probability=0.13,
        # NFL-specific fields via extra="allow"
        weather_conditions={"temp": 45, "wind": 12},
        division_rivalry=True
    )
    
    # Convert to dict and back
    game_dict = original_game.model_dump()
    reconstructed_game = CanonicalGameObject(**game_dict)
    
    assert reconstructed_game.sport == "nfl"
    assert reconstructed_game.game_id == original_game.game_id
    assert reconstructed_game.weather_conditions == original_game.weather_conditions
    assert reconstructed_game.division_rivalry == original_game.division_rivalry
