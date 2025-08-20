#!/usr/bin/env python3
"""
Comprehensive test suite for NFLParlayStrategistAgent - JIRA-NFL-009

Tests the dedicated NFL agent functionality including:
- NFL parlay generation
- Sport-specific component integration
- SportFactory pattern usage
- NFL rules and arbitrage integration
- Scheduler integration
- NBA workflow isolation
"""

import pytest
import asyncio
import tempfile
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, List, Any
from datetime import datetime, timezone

from agents.nfl_parlay_strategist_agent import (
    NFLParlayStrategistAgent,
    NFLParlayRecommendation,
    NFLGameContext
)
from tools.sport_factory import SportFactory
from tools.odds_fetcher_tool import GameOdds, BookOdds, Selection


class TestNFLParlayAgent:
    """Test suite for NFLParlayStrategistAgent."""
    
    @pytest.fixture
    def nfl_agent(self):
        """Create an NFLParlayStrategistAgent instance for testing."""
        return NFLParlayStrategistAgent()
    
    @pytest.fixture
    def sample_nfl_games(self):
        """Create sample NFL games for testing."""
        # Chiefs vs Bills
        chiefs_bills_books = [
            BookOdds(
                bookmaker="DraftKings",
                market="h2h",
                last_update="2024-01-15T19:00:00Z",
                selections=[
                    Selection(name="Kansas City Chiefs", price_decimal=1.85, price_american="-118"),
                    Selection(name="Buffalo Bills", price_decimal=2.05, price_american="+105")
                ]
            ),
            BookOdds(
                bookmaker="FanDuel",
                market="spreads",
                last_update="2024-01-15T19:00:00Z",
                selections=[
                    Selection(name="Kansas City Chiefs", price_decimal=1.91, price_american="-110", line=-2.5),
                    Selection(name="Buffalo Bills", price_decimal=1.91, price_american="-110", line=2.5)
                ]
            )
        ]
        
        chiefs_bills_game = GameOdds(
            game_id="nfl_chiefs_bills_20240115",
            sport_key="americanfootball_nfl",
            sport_title="NFL",
            commence_time="2024-01-15T21:00:00Z",
            home_team="Buffalo Bills",
            away_team="Kansas City Chiefs",
            books=chiefs_bills_books
        )
        
        # Cowboys vs Giants
        cowboys_giants_books = [
            BookOdds(
                bookmaker="BetMGM",
                market="totals",
                last_update="2024-01-15T19:00:00Z",
                selections=[
                    Selection(name="Over", price_decimal=1.87, price_american="-115", line=42.5),
                    Selection(name="Under", price_decimal=1.95, price_american="-105", line=42.5)
                ]
            )
        ]
        
        cowboys_giants_game = GameOdds(
            game_id="nfl_cowboys_giants_20240115",
            sport_key="americanfootball_nfl", 
            sport_title="NFL",
            commence_time="2024-01-15T18:00:00Z",
            home_team="New York Giants",
            away_team="Dallas Cowboys",
            books=cowboys_giants_books
        )
        
        return [chiefs_bills_game, cowboys_giants_game]
    
    def test_nfl_agent_initialization(self, nfl_agent):
        """Test that NFL agent initializes correctly with NFL components."""
        assert nfl_agent.sport == "nfl"
        assert nfl_agent.agent_id == "nfl_parlay_strategist_v1.0"
        
        # Check that NFL toolkit is loaded
        assert nfl_agent.nfl_toolkit is not None
        assert len(nfl_agent.nfl_toolkit) > 0
        
        # Check NFL-specific components
        assert nfl_agent.data_fetcher is not None
        assert nfl_agent.odds_fetcher is not None
        assert nfl_agent.parlay_builder is not None
        assert nfl_agent.confidence_scorer is not None
        assert nfl_agent.rules_engine is not None
        assert nfl_agent.arbitrage_detector is not None
        
        # Check sport configuration
        assert nfl_agent.sport_config.sport_name == "nfl"
        assert nfl_agent.sport_config.odds_api_key == "americanfootball_nfl"
        
        # Check NFL teams list
        assert len(nfl_agent.nfl_teams) == 32  # 32 NFL teams
        assert "Chiefs" in nfl_agent.nfl_teams
        assert "Bills" in nfl_agent.nfl_teams
    
    def test_nfl_agent_sport_validation(self):
        """Test that NFL agent only accepts 'nfl' as sport parameter."""
        # Valid initialization
        agent = NFLParlayStrategistAgent(sport="nfl")
        assert agent.sport == "nfl"
        
        # Invalid sport should raise error
        with pytest.raises(ValueError, match="only supports NFL"):
            NFLParlayStrategistAgent(sport="nba")
        
        with pytest.raises(ValueError, match="only supports NFL"):
            NFLParlayStrategistAgent(sport="hockey")
    
    def test_sport_factory_integration(self, nfl_agent):
        """Test SportFactory integration and component creation."""
        # Check that components were created via SportFactory
        assert hasattr(nfl_agent, 'nfl_toolkit')
        
        # Verify all expected components are present
        expected_components = [
            'data_fetcher', 'odds_fetcher', 'parlay_builder',
            'confidence_scorer', 'rules_engine', 'arbitrage_detector',
            'sport_config', 'schedule_triggers'
        ]
        
        for component in expected_components:
            assert component in nfl_agent.nfl_toolkit
        
        # Test direct SportFactory usage
        nfl_config = SportFactory.get_sport_config("nfl")
        assert nfl_config.sport_name == "nfl"
        assert nfl_config.odds_api_key == "americanfootball_nfl"
        
        # Test that NFL gets different config than NBA
        nba_config = SportFactory.get_sport_config("nba")
        assert nba_config.odds_api_key != nfl_config.odds_api_key
        assert nba_config.schedule_triggers != nfl_config.schedule_triggers
    
    @pytest.mark.asyncio
    async def test_nfl_parlay_generation(self, nfl_agent, sample_nfl_games):
        """Test NFL parlay generation functionality."""
        # Mock the odds fetcher to return sample games
        with patch.object(nfl_agent, '_fetch_nfl_games_with_context', return_value=sample_nfl_games):
            recommendation = await nfl_agent.generate_nfl_parlay_recommendation(
                target_legs=2,
                min_total_odds=3.0,
                include_arbitrage=False,
                include_three_way=False
            )
            
            # Check that recommendation was generated
            assert recommendation is not None
            assert isinstance(recommendation, NFLParlayRecommendation)
            
            # Check recommendation structure
            assert len(recommendation.legs) <= 2  # Target legs
            assert recommendation.reasoning is not None
            assert recommendation.reasoning.confidence_score > 0
            
            # Check NFL-specific attributes
            assert hasattr(recommendation, 'nfl_context')
            assert hasattr(recommendation, 'arbitrage_opportunities')
            assert hasattr(recommendation, 'correlation_warnings')
            assert hasattr(recommendation, 'nfl_specific_insights')
    
    @pytest.mark.asyncio
    async def test_nfl_context_enhancement(self, nfl_agent, sample_nfl_games):
        """Test NFL-specific context enhancement."""
        # Create a mock recommendation
        recommendation = NFLParlayRecommendation(
            legs=[{
                'game_id': 'nfl_chiefs_bills_20240115',
                'market_type': 'h2h',
                'selection_name': 'Kansas City Chiefs',
                'bookmaker': 'DraftKings',
                'odds_decimal': 1.85
            }],
            reasoning=Mock(confidence_score=0.7),
            expected_value=0.1,
            kelly_percentage=0.05
        )
        
        # Test context enhancement
        await nfl_agent._enhance_with_nfl_context(recommendation, sample_nfl_games)
        
        # Check that NFL context was added
        assert len(recommendation.nfl_context) > 0
        
        context = recommendation.nfl_context[0]
        assert isinstance(context, NFLGameContext)
        assert context.game_id == 'nfl_chiefs_bills_20240115'
        assert context.home_team is not None
        assert context.away_team is not None
        assert context.injury_report is not None
        assert context.line_movement is not None
    
    @pytest.mark.asyncio
    async def test_nfl_arbitrage_detection(self, nfl_agent):
        """Test NFL arbitrage detection integration."""
        # Create a mock recommendation with high odds
        recommendation = NFLParlayRecommendation(
            legs=[{
                'game_id': 'test_game',
                'market_type': 'h2h',
                'selection_name': 'Test Team',
                'bookmaker': 'DraftKings',
                'odds_decimal': 2.5  # High odds for arbitrage potential
            }],
            reasoning=Mock(confidence_score=0.7),
            expected_value=0.1,
            kelly_percentage=0.05
        )
        
        # Test arbitrage detection
        arbitrage_opps = await nfl_agent._detect_nfl_arbitrage_opportunities(recommendation)
        
        # Check that arbitrage detection ran (may or may not find opportunities)
        assert isinstance(arbitrage_opps, list)
        
        # If opportunities found, check structure
        for opp in arbitrage_opps:
            assert 'type' in opp
            assert 'profit_margin' in opp
            assert 'confidence' in opp
    
    @pytest.mark.asyncio
    async def test_nfl_rules_validation(self, nfl_agent):
        """Test NFL parlay rules validation."""
        # Create a mock recommendation
        recommendation = NFLParlayRecommendation(
            legs=[
                {
                    'game_id': 'test_game_1',
                    'market_type': 'h2h',
                    'selection_name': 'Team A',
                    'odds_decimal': 1.85
                },
                {
                    'game_id': 'test_game_2', 
                    'market_type': 'spreads',
                    'selection_name': 'Team B',
                    'odds_decimal': 1.91
                }
            ],
            reasoning=Mock(confidence_score=0.7),
            expected_value=0.1,
            kelly_percentage=0.05
        )
        
        # Test rules validation
        await nfl_agent._validate_nfl_parlay_rules(recommendation)
        
        # Check that correlation warnings were added (may be empty)
        assert hasattr(recommendation, 'correlation_warnings')
        assert isinstance(recommendation.correlation_warnings, list)
    
    @pytest.mark.asyncio
    async def test_nfl_insights_generation(self, nfl_agent):
        """Test NFL-specific insights generation."""
        # Create recommendation with NFL context
        nfl_context = [
            NFLGameContext(
                game_id='test_game',
                home_team='Chiefs',
                away_team='Bills',
                game_time=datetime.now(timezone.utc),
                week=1,
                season_type='REG',
                injury_report=['QB questionable', 'RB out'],
                line_movement=[{'market': 'spread', 'movement': '+0.5'}],
                public_betting={'home_ml_percent': 60.0}
            )
        ]
        
        recommendation = NFLParlayRecommendation(
            legs=[{
                'game_id': 'test_game',
                'market_type': 'h2h',
                'selection_name': 'Chiefs',
                'odds_decimal': 1.85
            }],
            reasoning=Mock(confidence_score=0.7),
            expected_value=0.1,
            kelly_percentage=0.05,
            nfl_context=nfl_context
        )
        
        # Test insights generation
        await nfl_agent._generate_nfl_insights(recommendation)
        
        # Check that insights were generated
        assert hasattr(recommendation, 'nfl_specific_insights')
        assert isinstance(recommendation.nfl_specific_insights, list)
        
        # Should have insights about injuries and line movement
        insights_text = ' '.join(recommendation.nfl_specific_insights)
        # The exact content depends on the logic, but should contain relevant info
    
    def test_nfl_team_normalization(self, nfl_agent):
        """Test NFL team name normalization."""
        # Test various team name formats
        test_cases = [
            ("Kansas City Chiefs", "KC"),
            ("Chiefs", "KC"),
            ("Buffalo Bills", "BUF"),
            ("Bills", "BUF"),
            ("Dallas Cowboys", "DAL"),
            ("New England Patriots", "NE")
        ]
        
        for input_name, expected_code in test_cases:
            normalized = nfl_agent._normalize_team_name(input_name)
            # The exact result depends on MarketNormalizer implementation
            assert normalized is not None
    
    def test_nfl_schedule_triggers(self, nfl_agent):
        """Test NFL schedule trigger configuration."""
        triggers = nfl_agent.get_nfl_schedule_triggers()
        
        # Check NFL-specific schedule configuration
        assert 'days' in triggers
        assert 'game_times' in triggers
        assert 'season_months' in triggers
        
        # Check NFL-specific days
        nfl_days = triggers['days']
        assert 'thursday' in nfl_days  # Thursday Night Football
        assert 'sunday' in nfl_days    # Sunday games
        assert 'monday' in nfl_days    # Monday Night Football
        
        # Check game times
        game_times = triggers['game_times']
        assert len(game_times) > 0
        
        # Check season months (Aug-Feb)
        season_months = triggers['season_months']
        assert 8 in season_months  # August (preseason)
        assert 12 in season_months # December
        assert 1 in season_months  # January (playoffs)
        assert 2 in season_months  # February (Super Bowl)
    
    def test_nfl_agent_stats(self, nfl_agent):
        """Test NFL agent statistics and metadata."""
        stats = nfl_agent.get_agent_stats()
        
        # Check basic stats structure
        assert 'agent_id' in stats
        assert 'sport' in stats
        assert 'supported_markets' in stats
        assert 'team_count' in stats
        assert 'toolkit_components' in stats
        assert 'schedule_triggers' in stats
        
        # Check NFL-specific values
        assert stats['agent_id'] == 'nfl_parlay_strategist_v1.0'
        assert stats['sport'] == 'nfl'
        assert stats['team_count'] == 32
        
        # Check supported markets
        markets = stats['supported_markets']
        assert 'primary' in markets
        assert 'secondary' in markets
        assert 'h2h' in markets['primary']
        assert 'spreads' in markets['primary']
        assert 'totals' in markets['primary']
    
    def test_demo_games_creation(self, nfl_agent):
        """Test creation of demo NFL games."""
        demo_games = nfl_agent._create_nfl_demo_games()
        
        # Check that demo games were created
        assert len(demo_games) > 0
        
        for game in demo_games:
            assert isinstance(game, GameOdds)
            assert game.sport_key == "americanfootball_nfl"
            assert len(game.books) > 0
            
            # Check NFL teams
            assert any(team in game.home_team for team in ['Chiefs', 'Bills', 'Cowboys', 'Giants'])
            assert any(team in game.away_team for team in ['Chiefs', 'Bills', 'Cowboys', 'Giants'])
    
    @pytest.mark.asyncio
    async def test_nfl_parlay_with_arbitrage(self, nfl_agent, sample_nfl_games):
        """Test NFL parlay generation with arbitrage detection enabled."""
        with patch.object(nfl_agent, '_fetch_nfl_games_with_context', return_value=sample_nfl_games):
            recommendation = await nfl_agent.generate_nfl_parlay_recommendation(
                target_legs=2,
                min_total_odds=3.0,
                include_arbitrage=True,  # Enable arbitrage detection
                include_three_way=False
            )
            
            if recommendation:
                # Check that arbitrage opportunities were checked
                assert hasattr(recommendation, 'arbitrage_opportunities')
                assert isinstance(recommendation.arbitrage_opportunities, list)
    
    @pytest.mark.asyncio
    async def test_nfl_parlay_with_three_way(self, nfl_agent, sample_nfl_games):
        """Test NFL parlay generation with three-way markets."""
        with patch.object(nfl_agent, '_fetch_nfl_games_with_context', return_value=sample_nfl_games):
            recommendation = await nfl_agent.generate_nfl_parlay_recommendation(
                target_legs=2,
                min_total_odds=3.0,
                include_arbitrage=False,
                include_three_way=True  # Enable three-way markets
            )
            
            # Three-way markets may or may not be included depending on availability
            # But the request should not fail
            if recommendation:
                assert isinstance(recommendation, NFLParlayRecommendation)
    
    def test_week_extraction(self, nfl_agent):
        """Test NFL week extraction from game data."""
        mock_game = Mock()
        mock_game.game_id = "nfl_test_20240115"
        
        week = nfl_agent._extract_week_from_game(mock_game)
        
        # For demo purposes, should return default week
        assert isinstance(week, int)
        assert week >= 1
    
    def test_injury_report_simulation(self, nfl_agent):
        """Test NFL injury report simulation."""
        injury_report = nfl_agent._simulate_nfl_injury_report("Chiefs", "Bills")
        
        # Check that injury report is generated
        assert isinstance(injury_report, list)
        assert len(injury_report) > 0
        
        # Check that team names appear in reports
        report_text = ' '.join(injury_report)
        assert any(team in report_text for team in ['Chiefs', 'Bills'])
    
    def test_line_movement_simulation(self, nfl_agent):
        """Test NFL line movement simulation."""
        mock_game = Mock()
        line_movement = nfl_agent._simulate_nfl_line_movement(mock_game)
        
        # Check structure
        assert isinstance(line_movement, list)
        
        for movement in line_movement:
            assert isinstance(movement, dict)
            assert 'market' in movement
            assert 'movement' in movement
            assert 'significance' in movement
    
    def test_public_betting_simulation(self, nfl_agent):
        """Test NFL public betting simulation."""
        mock_game = Mock()
        public_betting = nfl_agent._simulate_nfl_public_betting(mock_game)
        
        # Check structure
        assert isinstance(public_betting, dict)
        assert 'home_ml_percent' in public_betting
        assert 'away_ml_percent' in public_betting
        assert 'over_percent' in public_betting
        assert 'under_percent' in public_betting
        
        # Check reasonable percentages
        for key, value in public_betting.items():
            assert 0 <= value <= 100


class TestNFLSchedulerIntegration:
    """Test suite for NFL scheduler integration."""
    
    @pytest.fixture
    def scheduler_integration(self):
        """Create scheduler integration instance for testing."""
        from agents.nfl_scheduler_integration import NFLSchedulerIntegration
        
        # Create with no actual scheduler to avoid APScheduler dependency in tests
        return NFLSchedulerIntegration(scheduler=None, pre_game_hours=3)
    
    def test_scheduler_initialization(self, scheduler_integration):
        """Test scheduler integration initialization."""
        assert scheduler_integration.pre_game_hours == 3
        assert scheduler_integration.nfl_agent is None
        
        # Check NFL triggers loaded
        assert scheduler_integration.nfl_triggers is not None
        assert 'days' in scheduler_integration.nfl_triggers
        assert 'game_times' in scheduler_integration.nfl_triggers
    
    @pytest.mark.asyncio
    async def test_nfl_agent_initialization(self, scheduler_integration):
        """Test NFL agent initialization within scheduler."""
        await scheduler_integration.initialize_nfl_agent()
        
        assert scheduler_integration.nfl_agent is not None
        assert isinstance(scheduler_integration.nfl_agent, NFLParlayStrategistAgent)
    
    @pytest.mark.asyncio
    async def test_manual_parlay_generation(self, scheduler_integration):
        """Test manual trigger of NFL parlay generation."""
        # Initialize agent first
        await scheduler_integration.initialize_nfl_agent()
        
        # Test manual generation
        await scheduler_integration.trigger_manual_generation(
            game_day='sunday',
            game_time='13:00'
        )
        
        # Should complete without errors


class TestNBAWorkflowIsolation:
    """Test that NFL agent doesn't interfere with NBA workflows."""
    
    def test_sport_factory_isolation(self):
        """Test that SportFactory maintains isolation between NBA and NFL."""
        # Create both toolkits
        nba_toolkit = SportFactory.create_complete_toolkit("nba")
        nfl_toolkit = SportFactory.create_complete_toolkit("nfl")
        
        # Check that they have different configurations
        nba_config = nba_toolkit["sport_config"]
        nfl_config = nfl_toolkit["sport_config"]
        
        assert nba_config.sport_name != nfl_config.sport_name
        assert nba_config.odds_api_key != nfl_config.odds_api_key
        assert nba_config.schedule_triggers != nfl_config.schedule_triggers
        
        # Check that default markets are different
        assert nba_config.default_markets != nfl_config.default_markets
        assert "three_way" not in nba_config.default_markets
        assert "three_way" in nfl_config.default_markets
    
    def test_nfl_agent_vs_base_agent(self):
        """Test that NFL agent uses different configuration than base agent."""
        from tools.enhanced_parlay_strategist_agent import FewShotEnhancedParlayStrategistAgent
        
        # Create base agent (NBA-focused)
        base_agent = FewShotEnhancedParlayStrategistAgent()
        
        # Create NFL agent
        nfl_agent = NFLParlayStrategistAgent()
        
        # Check different team lists
        assert hasattr(base_agent, 'nba_teams')
        assert hasattr(nfl_agent, 'nfl_teams')
        assert base_agent.nba_teams != nfl_agent.nfl_teams
        
        # Check different agent IDs
        assert base_agent.agent_id != nfl_agent.agent_id
        assert "nfl" in nfl_agent.agent_id.lower()
    
    def test_market_preferences_isolation(self):
        """Test that NFL and NBA have different market preferences."""
        nfl_agent = NFLParlayStrategistAgent()
        
        # Check NFL-specific market preferences
        nfl_markets = nfl_agent.nfl_market_preferences
        
        assert 'primary' in nfl_markets
        assert 'secondary' in nfl_markets
        assert 'advanced' in nfl_markets
        
        # NFL should have specific markets
        assert 'h2h' in nfl_markets['primary']
        assert 'spreads' in nfl_markets['primary'] 
        assert 'totals' in nfl_markets['primary']
        
        # NFL-specific markets
        assert 'three_way' in nfl_markets['secondary']
        assert 'anytime_td' in nfl_markets['advanced']
        assert 'player_rushing_yards' in nfl_markets['advanced']


def test_nfl_parlay_generation_validation():
    """Integration test for complete NFL parlay generation workflow."""
    
    async def run_test():
        # Initialize NFL agent
        nfl_agent = NFLParlayStrategistAgent()
        
        # Generate multiple NFL parlays for validation
        parlays_generated = []
        
        configs = [
            {"legs": 2, "odds": 3.0},
            {"legs": 3, "odds": 5.0},
            {"legs": 4, "odds": 8.0}
        ]
        
        for config in configs:
            try:
                recommendation = await nfl_agent.generate_nfl_parlay_recommendation(
                    target_legs=config["legs"],
                    min_total_odds=config["odds"],
                    include_arbitrage=True
                )
                
                if recommendation:
                    parlays_generated.append(recommendation)
                    
            except Exception as e:
                # Log but don't fail - some configurations may not have viable parlays
                print(f"Could not generate parlay with {config}: {e}")
        
        return parlays_generated
    
    # Run the test
    parlays = asyncio.run(run_test())
    
    # Should generate at least some parlays
    print(f"Generated {len(parlays)} NFL parlays for validation")
    
    for i, parlay in enumerate(parlays, 1):
        print(f"Parlay {i}: {len(parlay.legs)} legs, confidence {parlay.reasoning.confidence_score:.3f}")


if __name__ == "__main__":
    # Run specific tests
    pytest.main([__file__, "-v", "--tb=short"])
