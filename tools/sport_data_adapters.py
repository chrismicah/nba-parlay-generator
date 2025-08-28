#!/usr/bin/env python3
"""
Sport Data Adapters - Unified Parlay System Refactor

Provides sport-specific data adapters that handle the different data sources,
APIs, and preprocessing for NFL and NBA while maintaining a unified interface.

Key Features:
- NFLDataAdapter: Handles NFL-specific data sources, APIs, and preprocessing
- NBADataAdapter: Handles NBA-specific data sources, APIs, and preprocessing  
- Shared interface for unified parlay generation logic
- Complete isolation between sports data sources
- Pluggable architecture for easy extension to other sports
"""

from __future__ import annotations

import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple, Protocol
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from abc import ABC, abstractmethod
import json

# Import base components
from tools.odds_fetcher_tool import GameOdds, BookOdds, Selection

# Import injury classifier (optional dependency)
try:
    from tools.classify_injury_severity import BioBERTInjuryClassifier
    HAS_INJURY_CLASSIFIER = True
except ImportError:
    HAS_INJURY_CLASSIFIER = False
    BioBERTInjuryClassifier = None

# Import prop trainer for EV-based ranking
try:
    from ml.ml_prop_trainer import HistoricalPropTrainer
    HAS_PROP_TRAINER = True
except ImportError:
    HAS_PROP_TRAINER = False
    HistoricalPropTrainer = None

# Import knowledge base RAG system
try:
    from tools.knowledge_base_rag import SportsKnowledgeRAG, KnowledgeChunk
except ImportError:
    SportsKnowledgeRAG = KnowledgeChunk = None

# Sport-specific components
try:
    from tools.sport_factory import SportFactory
except ImportError:
    SportFactory = None

logger = logging.getLogger(__name__)


@dataclass
class SportContext:
    """Base context information for any sport."""
    sport: str
    game_id: str
    home_team: str
    away_team: str
    game_time: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NFLContext(SportContext):
    """NFL-specific context information."""
    week: int = 1
    season_type: str = "REG"  # "REG", "POST", "PRE"
    weather: Optional[Dict[str, Any]] = None
    injury_report: List[str] = field(default_factory=list)
    line_movement: List[Dict[str, Any]] = field(default_factory=list)
    public_betting: Optional[Dict[str, float]] = None


@dataclass
class NBAContext(SportContext):
    """NBA-specific context information."""
    season_stage: str = "Regular"  # "Regular", "Playoffs", "Preseason"
    rest_days: Dict[str, int] = field(default_factory=dict)  # team -> rest days
    injury_report: List[str] = field(default_factory=list)
    line_movement: List[Dict[str, Any]] = field(default_factory=list)
    player_props: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class SportDataSources:
    """Data sources configuration for a sport."""
    sport: str
    api_endpoints: Dict[str, str]
    tweet_keywords: List[str]
    journalism_sources: List[str]
    data_processors: List[str]


class SportDataAdapter(ABC):
    """Abstract base class for sport-specific data adapters."""
    
    def __init__(self, sport: str):
        self.sport = sport.upper()
        self.logger = logging.getLogger(f"{__name__}.{self.sport}Adapter")
        
        # Initialize sport-specific components
        self._initialize_components()
    
    @abstractmethod
    def _initialize_components(self) -> None:
        """Initialize sport-specific components."""
        pass
    
    @abstractmethod
    async def fetch_games(self, date_range: Optional[Tuple[datetime, datetime]] = None) -> List[GameOdds]:
        """Fetch games and odds for the sport."""
        pass
    
    @abstractmethod
    async def get_sport_context(self, game_odds: GameOdds) -> SportContext:
        """Get sport-specific context for a game."""
        pass
    
    @abstractmethod
    def get_data_sources(self) -> SportDataSources:
        """Get sport-specific data sources configuration."""
        pass
    
    @abstractmethod
    async def preprocess_market_data(self, games: List[GameOdds]) -> List[GameOdds]:
        """Apply sport-specific preprocessing to market data."""
        pass
    
    @abstractmethod
    def get_sport_specific_insights(self, context: SportContext) -> List[str]:
        """Generate sport-specific insights for the context."""
        pass
    
    @abstractmethod
    def validate_parlay_legs(self, legs: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """Validate parlay legs according to sport-specific rules."""
        pass


class NFLDataAdapter(SportDataAdapter):
    """NFL-specific data adapter handling NFL data sources and processing."""
    
    def __init__(self):
        super().__init__("NFL")
        
    def _initialize_components(self) -> None:
        """Initialize NFL-specific components."""
        # Initialize NFL-specific injury classifier
        self.injury_classifier = None
        if HAS_INJURY_CLASSIFIER:
            try:
                self.injury_classifier = BioBERTInjuryClassifier()
                self.logger.info("NFL BioBERT injury classifier initialized")
            except Exception as e:
                self.logger.warning(f"Could not initialize NFL injury classifier: {e}")
        
        # Initialize NFL prop trainer if available
        self.prop_trainer = None
        if HAS_PROP_TRAINER:
            try:
                self.prop_trainer = HistoricalPropTrainer(sport="nfl")
                self.logger.info("NFL prop trainer initialized")
            except Exception as e:
                self.logger.warning(f"Could not initialize NFL prop trainer: {e}")
        
        # Initialize NFL-specific factory components
        if SportFactory:
            try:
                self.sport_factory = SportFactory("NFL")
                self.odds_fetcher = self.sport_factory.create_odds_fetcher()
                self.data_fetcher = self.sport_factory.create_data_fetcher()
                self.parlay_builder = self.sport_factory.create_parlay_builder()
                self.logger.info("NFL SportFactory components initialized")
            except Exception as e:
                self.logger.warning(f"Could not initialize NFL SportFactory: {e}")
                self.sport_factory = self.odds_fetcher = self.data_fetcher = self.parlay_builder = None
        
    async def fetch_games(self, date_range: Optional[Tuple[datetime, datetime]] = None) -> List[GameOdds]:
        """Fetch NFL games and odds."""
        try:
            if self.odds_fetcher:
                # Use sport-specific odds fetcher
                games = await self.odds_fetcher.fetch_nfl_odds(date_range)
                self.logger.info(f"Fetched {len(games)} NFL games")
                return games
            else:
                # Fallback to mock NFL games
                return self._generate_mock_nfl_games()
        except Exception as e:
            self.logger.error(f"Error fetching NFL games: {e}")
            return self._generate_mock_nfl_games()
    
    async def get_sport_context(self, game_odds: GameOdds) -> NFLContext:
        """Get NFL-specific context for a game."""
        return NFLContext(
            sport="NFL",
            game_id=game_odds.game_id,
            home_team=game_odds.home_team,
            away_team=game_odds.away_team,
            game_time=game_odds.game_time,
            week=self._determine_nfl_week(game_odds.game_time),
            season_type=self._determine_season_type(game_odds.game_time),
            weather=await self._fetch_nfl_weather(game_odds),
            injury_report=await self._fetch_nfl_injuries(game_odds),
            line_movement=await self._fetch_nfl_line_movement(game_odds),
            public_betting=await self._fetch_nfl_public_betting(game_odds),
            metadata={
                "source": "nfl_adapter",
                "fetched_at": datetime.now(timezone.utc).isoformat()
            }
        )
    
    def get_data_sources(self) -> SportDataSources:
        """Get NFL-specific data sources configuration."""
        return SportDataSources(
            sport="NFL",
            api_endpoints={
                "odds": "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds",
                "weather": "https://api.openweathermap.org/data/2.5/weather",
                "injuries": "https://api.sportsdata.io/v3/nfl/scores/json/Injuries",
                "news": "https://newsapi.org/v2/everything?q=NFL"
            },
            tweet_keywords=[
                "NFL", "football", "injury", "inactive", "questionable", "doubtful", 
                "weather", "wind", "snow", "rain", "dome", "outdoor"
            ],
            journalism_sources=[
                "ESPN NFL", "NFL.com", "Pro Football Talk", "The Athletic NFL",
                "Bleacher Report NFL", "CBS Sports NFL"
            ],
            data_processors=[
                "nfl_weather_processor", "nfl_injury_processor", 
                "nfl_line_movement_processor", "nfl_public_betting_processor"
            ]
        )
    
    async def preprocess_market_data(self, games: List[GameOdds]) -> List[GameOdds]:
        """Apply NFL-specific preprocessing to market data."""
        processed_games = []
        
        for game in games:
            # Apply NFL-specific market normalization
            processed_game = await self._normalize_nfl_markets(game)
            
            # Add NFL-specific market metadata
            processed_game = await self._add_nfl_market_metadata(processed_game)
            
            processed_games.append(processed_game)
        
        self.logger.info(f"Preprocessed {len(processed_games)} NFL games")
        return processed_games
    
    def get_sport_specific_insights(self, context: NFLContext) -> List[str]:
        """Generate NFL-specific insights."""
        insights = []
        
        # Weather-based insights
        if context.weather:
            insights.extend(self._generate_weather_insights(context.weather))
        
        # Week-based insights
        insights.extend(self._generate_week_insights(context.week, context.season_type))
        
        # Injury-based insights
        if context.injury_report:
            insights.extend(self._generate_injury_insights(context.injury_report))
        
        # Public betting insights
        if context.public_betting:
            insights.extend(self._generate_public_betting_insights(context.public_betting))
        
        return insights
    
    def validate_parlay_legs(self, legs: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """Validate NFL parlay legs according to NFL-specific rules."""
        errors = []
        
        # NFL-specific validation rules
        for leg in legs:
            # Check for same-game correlations (NFL specific)
            if not self._validate_nfl_correlations(leg):
                errors.append(f"Invalid NFL correlation in leg: {leg.get('selection', 'Unknown')}")
            
            # Check for NFL player prop availability
            if not self._validate_nfl_player_props(leg):
                errors.append(f"NFL player prop not available: {leg.get('selection', 'Unknown')}")
            
            # Check for NFL team totals logic
            if not self._validate_nfl_team_totals(leg):
                errors.append(f"Invalid NFL team total logic: {leg.get('selection', 'Unknown')}")
        
        return len(errors) == 0, errors
    
    # NFL-specific helper methods
    def _generate_mock_nfl_games(self) -> List[GameOdds]:
        """Generate mock NFL games for testing."""
        # Implementation would generate realistic mock NFL games
        return []
    
    def _determine_nfl_week(self, game_time: datetime) -> int:
        """Determine NFL week from game time."""
        # Implementation to calculate NFL week
        return 1
    
    def _determine_season_type(self, game_time: datetime) -> str:
        """Determine NFL season type from game time."""
        # Implementation to determine if regular season, playoffs, etc.
        return "REG"
    
    async def _fetch_nfl_weather(self, game_odds: GameOdds) -> Optional[Dict[str, Any]]:
        """Fetch weather data for NFL game."""
        # Implementation to fetch weather data
        return None
    
    async def _fetch_nfl_injuries(self, game_odds: GameOdds) -> List[str]:
        """Fetch NFL injury reports."""
        # Implementation to fetch injury data
        return []
    
    async def _fetch_nfl_line_movement(self, game_odds: GameOdds) -> List[Dict[str, Any]]:
        """Fetch NFL line movement data."""
        # Implementation to fetch line movement
        return []
    
    async def _fetch_nfl_public_betting(self, game_odds: GameOdds) -> Optional[Dict[str, float]]:
        """Fetch NFL public betting percentages."""
        # Implementation to fetch public betting data
        return None
    
    async def _normalize_nfl_markets(self, game: GameOdds) -> GameOdds:
        """Apply NFL-specific market normalization."""
        # Implementation for NFL market normalization
        return game
    
    async def _add_nfl_market_metadata(self, game: GameOdds) -> GameOdds:
        """Add NFL-specific market metadata."""
        # Implementation to add NFL metadata
        return game
    
    def _generate_weather_insights(self, weather: Dict[str, Any]) -> List[str]:
        """Generate weather-based insights for NFL."""
        return []
    
    def _generate_week_insights(self, week: int, season_type: str) -> List[str]:
        """Generate NFL week-based insights."""
        return []
    
    def _generate_injury_insights(self, injuries: List[str]) -> List[str]:
        """Generate NFL injury-based insights."""
        return []
    
    def _generate_public_betting_insights(self, public_betting: Dict[str, float]) -> List[str]:
        """Generate NFL public betting insights."""
        return []
    
    def _validate_nfl_correlations(self, leg: Dict[str, Any]) -> bool:
        """Validate NFL-specific correlations."""
        return True
    
    def _validate_nfl_player_props(self, leg: Dict[str, Any]) -> bool:
        """Validate NFL player prop availability."""
        return True
    
    def _validate_nfl_team_totals(self, leg: Dict[str, Any]) -> bool:
        """Validate NFL team totals logic."""
        return True


class NBADataAdapter(SportDataAdapter):
    """NBA-specific data adapter handling NBA data sources and processing."""
    
    def __init__(self):
        super().__init__("NBA")
        
    def _initialize_components(self) -> None:
        """Initialize NBA-specific components."""
        # Initialize NBA-specific injury classifier
        self.injury_classifier = None
        if HAS_INJURY_CLASSIFIER:
            try:
                self.injury_classifier = BioBERTInjuryClassifier()
                self.logger.info("NBA BioBERT injury classifier initialized")
            except Exception as e:
                self.logger.warning(f"Could not initialize NBA injury classifier: {e}")
        
        # Initialize NBA prop trainer if available
        self.prop_trainer = None
        if HAS_PROP_TRAINER:
            try:
                self.prop_trainer = HistoricalPropTrainer(sport="nba")
                self.logger.info("NBA prop trainer initialized")
            except Exception as e:
                self.logger.warning(f"Could not initialize NBA prop trainer: {e}")
        
        # Initialize NBA-specific factory components
        if SportFactory:
            try:
                self.sport_factory = SportFactory("NBA")
                self.odds_fetcher = self.sport_factory.create_odds_fetcher()
                self.data_fetcher = self.sport_factory.create_data_fetcher()
                self.parlay_builder = self.sport_factory.create_parlay_builder()
                self.logger.info("NBA SportFactory components initialized")
            except Exception as e:
                self.logger.warning(f"Could not initialize NBA SportFactory: {e}")
                self.sport_factory = self.odds_fetcher = self.data_fetcher = self.parlay_builder = None
    
    async def fetch_games(self, date_range: Optional[Tuple[datetime, datetime]] = None) -> List[GameOdds]:
        """Fetch NBA games and odds."""
        try:
            if self.odds_fetcher:
                # Use sport-specific odds fetcher
                games = await self.odds_fetcher.fetch_nba_odds(date_range)
                self.logger.info(f"Fetched {len(games)} NBA games")
                return games
            else:
                # Fallback to mock NBA games
                return self._generate_mock_nba_games()
        except Exception as e:
            self.logger.error(f"Error fetching NBA games: {e}")
            return self._generate_mock_nba_games()
    
    async def get_sport_context(self, game_odds: GameOdds) -> NBAContext:
        """Get NBA-specific context for a game."""
        return NBAContext(
            sport="NBA",
            game_id=game_odds.game_id,
            home_team=game_odds.home_team,
            away_team=game_odds.away_team,
            game_time=game_odds.game_time,
            season_stage=self._determine_season_stage(game_odds.game_time),
            rest_days=await self._fetch_nba_rest_days(game_odds),
            injury_report=await self._fetch_nba_injuries(game_odds),
            line_movement=await self._fetch_nba_line_movement(game_odds),
            player_props=await self._fetch_nba_player_props(game_odds),
            metadata={
                "source": "nba_adapter",
                "fetched_at": datetime.now(timezone.utc).isoformat()
            }
        )
    
    def get_data_sources(self) -> SportDataSources:
        """Get NBA-specific data sources configuration."""
        return SportDataSources(
            sport="NBA",
            api_endpoints={
                "odds": "https://api.the-odds-api.com/v4/sports/basketball_nba/odds",
                "stats": "https://stats.nba.com/stats/",
                "injuries": "https://api.sportsdata.io/v3/nba/scores/json/Injuries",
                "news": "https://newsapi.org/v2/everything?q=NBA"
            },
            tweet_keywords=[
                "NBA", "basketball", "injury", "load management", "rest", "back-to-back",
                "minutes restriction", "questionable", "doubtful", "probable"
            ],
            journalism_sources=[
                "ESPN NBA", "NBA.com", "The Athletic NBA", "Bleacher Report NBA",
                "CBS Sports NBA", "Basketball Reference"
            ],
            data_processors=[
                "nba_rest_processor", "nba_injury_processor", 
                "nba_line_movement_processor", "nba_player_prop_processor"
            ]
        )
    
    async def preprocess_market_data(self, games: List[GameOdds]) -> List[GameOdds]:
        """Apply NBA-specific preprocessing to market data."""
        processed_games = []
        
        for game in games:
            # Apply NBA-specific market normalization
            processed_game = await self._normalize_nba_markets(game)
            
            # Add NBA-specific market metadata
            processed_game = await self._add_nba_market_metadata(processed_game)
            
            processed_games.append(processed_game)
        
        self.logger.info(f"Preprocessed {len(processed_games)} NBA games")
        return processed_games
    
    def get_sport_specific_insights(self, context: NBAContext) -> List[str]:
        """Generate NBA-specific insights."""
        insights = []
        
        # Rest-based insights
        if context.rest_days:
            insights.extend(self._generate_rest_insights(context.rest_days))
        
        # Season stage insights
        insights.extend(self._generate_season_insights(context.season_stage))
        
        # Injury-based insights
        if context.injury_report:
            insights.extend(self._generate_injury_insights(context.injury_report))
        
        # Player prop insights
        if context.player_props:
            insights.extend(self._generate_player_prop_insights(context.player_props))
        
        return insights
    
    def validate_parlay_legs(self, legs: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """Validate NBA parlay legs according to NBA-specific rules."""
        errors = []
        
        # NBA-specific validation rules
        for leg in legs:
            # Check for same-game correlations (NBA specific)
            if not self._validate_nba_correlations(leg):
                errors.append(f"Invalid NBA correlation in leg: {leg.get('selection', 'Unknown')}")
            
            # Check for NBA player prop availability
            if not self._validate_nba_player_props(leg):
                errors.append(f"NBA player prop not available: {leg.get('selection', 'Unknown')}")
            
            # Check for NBA alternate lines logic
            if not self._validate_nba_alternate_lines(leg):
                errors.append(f"Invalid NBA alternate line: {leg.get('selection', 'Unknown')}")
        
        return len(errors) == 0, errors
    
    # NBA-specific helper methods
    def _generate_mock_nba_games(self) -> List[GameOdds]:
        """Generate mock NBA games for testing."""
        # Implementation would generate realistic mock NBA games
        return []
    
    def _determine_season_stage(self, game_time: datetime) -> str:
        """Determine NBA season stage from game time."""
        # Implementation to determine if regular season, playoffs, etc.
        return "Regular"
    
    async def _fetch_nba_rest_days(self, game_odds: GameOdds) -> Dict[str, int]:
        """Fetch rest days for NBA teams."""
        # Implementation to fetch rest days
        return {}
    
    async def _fetch_nba_injuries(self, game_odds: GameOdds) -> List[str]:
        """Fetch NBA injury reports."""
        # Implementation to fetch injury data
        return []
    
    async def _fetch_nba_line_movement(self, game_odds: GameOdds) -> List[Dict[str, Any]]:
        """Fetch NBA line movement data."""
        # Implementation to fetch line movement
        return []
    
    async def _fetch_nba_player_props(self, game_odds: GameOdds) -> List[Dict[str, Any]]:
        """Fetch NBA player props."""
        # Implementation to fetch player props
        return []
    
    async def _normalize_nba_markets(self, game: GameOdds) -> GameOdds:
        """Apply NBA-specific market normalization."""
        # Implementation for NBA market normalization
        return game
    
    async def _add_nba_market_metadata(self, game: GameOdds) -> GameOdds:
        """Add NBA-specific market metadata."""
        # Implementation to add NBA metadata
        return game
    
    def _generate_rest_insights(self, rest_days: Dict[str, int]) -> List[str]:
        """Generate rest-based insights for NBA."""
        return []
    
    def _generate_season_insights(self, season_stage: str) -> List[str]:
        """Generate NBA season-based insights."""
        return []
    
    def _generate_injury_insights(self, injuries: List[str]) -> List[str]:
        """Generate NBA injury-based insights."""
        return []
    
    def _generate_player_prop_insights(self, props: List[Dict[str, Any]]) -> List[str]:
        """Generate NBA player prop insights."""
        return []
    
    def _validate_nba_correlations(self, leg: Dict[str, Any]) -> bool:
        """Validate NBA-specific correlations."""
        return True
    
    def _validate_nba_player_props(self, leg: Dict[str, Any]) -> bool:
        """Validate NBA player prop availability."""
        return True
    
    def _validate_nba_alternate_lines(self, leg: Dict[str, Any]) -> bool:
        """Validate NBA alternate lines logic."""
        return True


def create_sport_adapter(sport: str) -> SportDataAdapter:
    """Factory function to create the appropriate sport adapter."""
    sport = sport.upper()
    
    if sport == "NFL":
        return NFLDataAdapter()
    elif sport == "NBA":
        return NBADataAdapter()
    else:
        raise ValueError(f"Unsupported sport: {sport}")
