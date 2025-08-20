#!/usr/bin/env python3
"""
SportFactory - JIRA-NFL-009

Implements the audit's "SPORT-AWARE FACTORY PATTERN" recommendation.
Creates sport-specific instances of data fetchers, odds fetchers, and other components.

Key Features:
- Sport-aware component instantiation
- Consistent interface across NBA and NFL
- Extensible for future sports (MLB, NHL, etc.)
- Centralized sport configuration management
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional, Type
from abc import ABC, abstractmethod

# Import individual components with error handling
try:
    from tools.odds_fetcher_tool import OddsFetcherTool
except ImportError:
    OddsFetcherTool = None

try:
    from tools.data_fetcher_tool import DataFetcherTool
except ImportError:
    DataFetcherTool = None

try:
    from tools.parlay_builder import ParlayBuilder
except ImportError:
    ParlayBuilder = None

try:
    from tools.bayesian_confidence_scorer import BayesianConfidenceScorer
except ImportError:
    BayesianConfidenceScorer = None

try:
    from tools.parlay_rules_engine import ParlayRulesEngine
except ImportError:
    ParlayRulesEngine = None

try:
    from tools.arbitrage_detector_tool import ArbitrageDetectorTool
except ImportError:
    ArbitrageDetectorTool = None

logger = logging.getLogger(__name__)


class SportConfig:
    """Configuration for a specific sport."""
    
    def __init__(self, 
                 sport_name: str,
                 odds_api_key: str,
                 data_sources: Dict[str, str],
                 schedule_triggers: Dict[str, Any],
                 default_markets: list):
        self.sport_name = sport_name
        self.odds_api_key = odds_api_key
        self.data_sources = data_sources
        self.schedule_triggers = schedule_triggers
        self.default_markets = default_markets


class SportFactory:
    """
    Factory for creating sport-specific instances of tools and components.
    
    Implements the audit's "SPORT-AWARE FACTORY PATTERN" recommendation.
    """
    
    # Sport configurations
    SPORT_CONFIGS = {
        "nba": SportConfig(
            sport_name="nba",
            odds_api_key="basketball_nba",
            data_sources={
                "primary": "nba_api",
                "odds": "the_odds_api",
                "injuries": "rotoworld",
                "advanced_stats": "basketball_reference"
            },
            schedule_triggers={
                "days": ["tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
                "game_times": ["19:00", "20:00", "20:30", "21:00", "22:00"],
                "season_months": [10, 11, 12, 1, 2, 3, 4, 5, 6]  # Oct-June
            },
            default_markets=["h2h", "spreads", "totals", "player_props"]
        ),
        "nfl": SportConfig(
            sport_name="nfl",
            odds_api_key="americanfootball_nfl",
            data_sources={
                "primary": "api_football",
                "odds": "the_odds_api",
                "injuries": "espn_nfl",
                "advanced_stats": "pro_football_reference"
            },
            schedule_triggers={
                "days": ["thursday", "sunday", "monday"],
                "game_times": ["13:00", "16:25", "20:20"],  # 1pm, 4:25pm, 8:20pm ET
                "season_months": [8, 9, 10, 11, 12, 1, 2]  # Aug-Feb (including playoffs)
            },
            default_markets=["h2h", "spreads", "totals", "player_props", "three_way"]
        )
    }
    
    @classmethod
    def create_data_fetcher(cls, sport: str):
        """
        Create a sport-specific data fetcher.
        
        Args:
            sport: Sport identifier ("nba" or "nfl")
            
        Returns:
            Configured DataFetcherTool instance or Mock if not available
        """
        if DataFetcherTool is None:
            logger.warning("DataFetcherTool not available, creating mock")
            return cls._create_mock_component("DataFetcherTool")
        
        config = cls._get_sport_config(sport)
        
        # Create data fetcher with sport-specific configuration
        data_fetcher = DataFetcherTool()
        
        # Configure for sport-specific data sources
        if sport.lower() == "nfl":
            # NFL uses API Football for primary data
            data_fetcher.primary_source = config.data_sources["primary"]
            logger.info(f"Created NFL DataFetcherTool with primary source: {data_fetcher.primary_source}")
        else:
            # NBA uses NBA API
            data_fetcher.primary_source = config.data_sources["primary"]
            logger.info(f"Created NBA DataFetcherTool with primary source: {data_fetcher.primary_source}")
        
        return data_fetcher
    
    @classmethod
    def create_odds_fetcher(cls, sport: str):
        """
        Create a sport-specific odds fetcher.
        
        Args:
            sport: Sport identifier ("nba" or "nfl")
            
        Returns:
            Configured OddsFetcherTool instance or Mock if not available
        """
        if OddsFetcherTool is None:
            logger.warning("OddsFetcherTool not available, creating mock")
            return cls._create_mock_component("OddsFetcherTool")
        
        config = cls._get_sport_config(sport)
        
        # Create odds fetcher with sport-specific API key
        odds_fetcher = OddsFetcherTool()
        odds_fetcher.default_sport_key = config.odds_api_key
        odds_fetcher.default_markets = config.default_markets
        
        logger.info(f"Created {sport.upper()} OddsFetcherTool with API key: {config.odds_api_key}")
        
        return odds_fetcher
    
    @classmethod
    def create_parlay_builder(cls, sport: str):
        """
        Create a sport-specific parlay builder.
        
        Args:
            sport: Sport identifier ("nba" or "nfl")
            
        Returns:
            Configured ParlayBuilder instance or Mock if not available
        """
        if ParlayBuilder is None:
            logger.warning("ParlayBuilder not available, creating mock")
            return cls._create_mock_component("ParlayBuilder")
        
        config = cls._get_sport_config(sport)
        
        # Create parlay builder with sport-specific settings
        parlay_builder = ParlayBuilder(
            sport_key=config.odds_api_key
        )
        
        logger.info(f"Created {sport.upper()} ParlayBuilder with sport key: {config.odds_api_key}")
        
        return parlay_builder
    
    @classmethod
    def create_confidence_scorer(cls, sport: str):
        """
        Create a sport-specific confidence scorer.
        
        Args:
            sport: Sport identifier ("nba" or "nfl")
            
        Returns:
            Configured BayesianConfidenceScorer instance or Mock if not available
        """
        if BayesianConfidenceScorer is None:
            logger.warning("BayesianConfidenceScorer not available, creating mock")
            return cls._create_mock_component("BayesianConfidenceScorer")
        
        # Sport-specific confidence parameters
        if sport.lower() == "nfl":
            # NFL has higher volatility and wider spreads
            confidence_scorer = BayesianConfidenceScorer(
                base_threshold=0.65,  # Slightly higher threshold for NFL
                odds_movement_sensitivity=0.12  # More sensitive to movement
            )
        else:
            # NBA standard configuration
            confidence_scorer = BayesianConfidenceScorer(
                base_threshold=0.60,
                odds_movement_sensitivity=0.10
            )
        
        logger.info(f"Created {sport.upper()} BayesianConfidenceScorer")
        
        return confidence_scorer
    
    @classmethod
    def create_rules_engine(cls, sport: str):
        """
        Create a sport-specific parlay rules engine.
        
        Args:
            sport: Sport identifier ("nba" or "nfl")
            
        Returns:
            Configured ParlayRulesEngine instance or Mock if not available
        """
        if ParlayRulesEngine is None:
            logger.warning("ParlayRulesEngine not available, creating mock")
            return cls._create_mock_component("ParlayRulesEngine")
        
        rules_engine = ParlayRulesEngine()
        
        # Load sport-specific rules
        try:
            rules_engine.load_rules(sport)
            logger.info(f"Created {sport.upper()} ParlayRulesEngine with {sport} rules loaded")
        except Exception as e:
            logger.warning(f"Could not load {sport} rules: {e}")
        
        return rules_engine
    
    @classmethod
    def create_arbitrage_detector(cls, sport: str):
        """
        Create a sport-specific arbitrage detector.
        
        Args:
            sport: Sport identifier ("nba" or "nfl")
            
        Returns:
            Configured ArbitrageDetectorTool instance or Mock if not available
        """
        if ArbitrageDetectorTool is None:
            logger.warning("ArbitrageDetectorTool not available, creating mock")
            return cls._create_mock_component("ArbitrageDetectorTool")
        
        # Sport-specific arbitrage parameters
        if sport.lower() == "nfl":
            # NFL has wider spreads and higher volatility
            arbitrage_detector = ArbitrageDetectorTool(
                min_profit_threshold=0.008,  # Slightly higher threshold for NFL
                default_slippage_buffer=0.012  # Higher slippage for NFL
            )
        else:
            # NBA standard configuration
            arbitrage_detector = ArbitrageDetectorTool(
                min_profit_threshold=0.005,
                default_slippage_buffer=0.010
            )
        
        logger.info(f"Created {sport.upper()} ArbitrageDetectorTool")
        
        return arbitrage_detector
    
    @classmethod
    def get_sport_config(cls, sport: str) -> SportConfig:
        """
        Get configuration for a specific sport.
        
        Args:
            sport: Sport identifier
            
        Returns:
            SportConfig instance
        """
        return cls._get_sport_config(sport)
    
    @classmethod
    def get_supported_sports(cls) -> list:
        """Get list of supported sports."""
        return list(cls.SPORT_CONFIGS.keys())
    
    @classmethod
    def get_schedule_triggers(cls, sport: str) -> Dict[str, Any]:
        """
        Get APScheduler trigger configuration for a sport.
        
        Args:
            sport: Sport identifier
            
        Returns:
            Dictionary with schedule trigger configuration
        """
        config = cls._get_sport_config(sport)
        return config.schedule_triggers
    
    @classmethod
    def _get_sport_config(cls, sport: str) -> SportConfig:
        """Internal method to get sport configuration with validation."""
        sport_lower = sport.lower()
        
        if sport_lower not in cls.SPORT_CONFIGS:
            raise ValueError(f"Unsupported sport: {sport}. "
                           f"Supported sports: {list(cls.SPORT_CONFIGS.keys())}")
        
        return cls.SPORT_CONFIGS[sport_lower]
    
    @classmethod
    def _create_mock_component(cls, component_name: str):
        """Create a mock component when the real one is not available."""
        class MockComponent:
            def __init__(self):
                self.component_name = component_name
                self.sport = None
                self.primary_source = None
                self.default_sport_key = None
                self.default_markets = []
            
            def __repr__(self):
                return f"Mock{self.component_name}()"
        
        return MockComponent()
    
    @classmethod
    def validate_sport_support(cls, sport: str) -> bool:
        """
        Validate if a sport is supported by the factory.
        
        Args:
            sport: Sport identifier
            
        Returns:
            True if sport is supported, False otherwise
        """
        return sport.lower() in cls.SPORT_CONFIGS
    
    @classmethod
    def create_complete_toolkit(cls, sport: str) -> Dict[str, Any]:
        """
        Create a complete toolkit of components for a sport.
        
        Args:
            sport: Sport identifier
            
        Returns:
            Dictionary containing all sport-specific components
        """
        if not cls.validate_sport_support(sport):
            raise ValueError(f"Sport {sport} is not supported")
        
        logger.info(f"Creating complete {sport.upper()} toolkit...")
        
        toolkit = {
            "data_fetcher": cls.create_data_fetcher(sport),
            "odds_fetcher": cls.create_odds_fetcher(sport),
            "parlay_builder": cls.create_parlay_builder(sport),
            "confidence_scorer": cls.create_confidence_scorer(sport),
            "rules_engine": cls.create_rules_engine(sport),
            "arbitrage_detector": cls.create_arbitrage_detector(sport),
            "sport_config": cls.get_sport_config(sport),
            "schedule_triggers": cls.get_schedule_triggers(sport)
        }
        
        logger.info(f"Complete {sport.upper()} toolkit created with {len(toolkit)} components")
        
        return toolkit


def main():
    """Main function for testing the SportFactory."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🏭 SportFactory - JIRA-NFL-009")
    print("=" * 50)
    
    # Test supported sports
    supported_sports = SportFactory.get_supported_sports()
    print(f"📋 Supported Sports: {', '.join(supported_sports)}")
    
    # Test NBA toolkit creation
    print(f"\n🏀 Creating NBA Toolkit:")
    try:
        nba_toolkit = SportFactory.create_complete_toolkit("nba")
        print(f"✅ NBA toolkit created with {len(nba_toolkit)} components")
        
        nba_config = nba_toolkit["sport_config"]
        print(f"   API Key: {nba_config.odds_api_key}")
        print(f"   Markets: {nba_config.default_markets}")
        print(f"   Schedule: {nba_config.schedule_triggers['days']}")
    except Exception as e:
        print(f"❌ NBA toolkit creation failed: {e}")
    
    # Test NFL toolkit creation
    print(f"\n🏈 Creating NFL Toolkit:")
    try:
        nfl_toolkit = SportFactory.create_complete_toolkit("nfl")
        print(f"✅ NFL toolkit created with {len(nfl_toolkit)} components")
        
        nfl_config = nfl_toolkit["sport_config"]
        print(f"   API Key: {nfl_config.odds_api_key}")
        print(f"   Markets: {nfl_config.default_markets}")
        print(f"   Schedule: {nfl_config.schedule_triggers['days']}")
    except Exception as e:
        print(f"❌ NFL toolkit creation failed: {e}")
    
    # Test invalid sport
    print(f"\n❌ Testing Invalid Sport:")
    try:
        SportFactory.create_complete_toolkit("hockey")
        print("❌ Should have failed for unsupported sport")
    except ValueError as e:
        print(f"✅ Correctly rejected unsupported sport: {e}")
    
    print(f"\n✅ SportFactory testing complete!")
    print(f"🎯 SPORT-AWARE FACTORY PATTERN implemented")


if __name__ == "__main__":
    main()
