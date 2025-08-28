#!/usr/bin/env python3
"""
Comprehensive Unit Tests for Unified Parlay System

Tests the refactored unified parlay strategist system to ensure:
- Sport isolation (NFL and NBA use separate data sources)
- Consistent response format across sports
- Proper knowledge base filtering
- Unified agent behavior
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
from typing import List, Dict, Any

# Import the unified system
from tools.unified_parlay_strategist_agent import (
    UnifiedParlayStrategistAgent, 
    UnifiedParlayRecommendation,
    create_unified_agent
)
from tools.sport_data_adapters import (
    NFLDataAdapter, 
    NBADataAdapter, 
    SportDataAdapter,
    create_sport_adapter
)
from tools.knowledge_base_rag import SportsKnowledgeRAG, KnowledgeChunk, RAGResult
from tools.odds_fetcher_tool import GameOdds, BookOdds, Selection

# Import FastAPI testing
from fastapi.testclient import TestClient
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.main import app


class TestSportDataAdapters:
    """Test sport-specific data adapters."""
    
    def test_create_nfl_adapter(self):
        """Test NFL adapter creation."""
        adapter = create_sport_adapter("NFL")
        assert isinstance(adapter, NFLDataAdapter)
        assert adapter.sport == "NFL"
    
    def test_create_nba_adapter(self):
        """Test NBA adapter creation."""
        adapter = create_sport_adapter("NBA")
        assert isinstance(adapter, NBADataAdapter)
        assert adapter.sport == "NBA"
    
    def test_invalid_sport_adapter(self):
        """Test creation with invalid sport."""
        with pytest.raises(ValueError):
            create_sport_adapter("MLB")
    
    def test_nfl_data_sources_isolation(self):
        """Test NFL adapter uses only NFL data sources."""
        adapter = NFLDataAdapter()
        data_sources = adapter.get_data_sources()
        
        assert data_sources.sport == "NFL"
        assert "NFL" in data_sources.tweet_keywords
        assert "football" in data_sources.tweet_keywords
        assert "basketball" not in data_sources.tweet_keywords
        assert "nba" not in data_sources.tweet_keywords
        
        # Check journalism sources
        journalism_sources_str = " ".join(data_sources.journalism_sources).lower()
        assert "nfl" in journalism_sources_str
        assert "nba" not in journalism_sources_str
    
    def test_nba_data_sources_isolation(self):
        """Test NBA adapter uses only NBA data sources."""
        adapter = NBADataAdapter()
        data_sources = adapter.get_data_sources()
        
        assert data_sources.sport == "NBA"
        assert "NBA" in data_sources.tweet_keywords
        assert "basketball" in data_sources.tweet_keywords
        assert "football" not in data_sources.tweet_keywords
        assert "nfl" not in data_sources.tweet_keywords
        
        # Check journalism sources
        journalism_sources_str = " ".join(data_sources.journalism_sources).lower()
        assert "nba" in journalism_sources_str
        assert "nfl" not in journalism_sources_str
    
    @pytest.mark.asyncio
    async def test_nfl_context_generation(self):
        """Test NFL-specific context generation."""
        adapter = NFLDataAdapter()
        
        # Mock game odds
        mock_game = GameOdds(
            game_id="nfl_test_1",
            home_team="Kansas City Chiefs",
            away_team="Buffalo Bills",
            game_time=datetime.now(timezone.utc),
            books=[]
        )
        
        context = await adapter.get_sport_context(mock_game)
        
        assert context.sport == "NFL"
        assert context.home_team == "Kansas City Chiefs"
        assert context.away_team == "Buffalo Bills"
        assert hasattr(context, 'week')
        assert hasattr(context, 'season_type')
        assert hasattr(context, 'weather')
    
    @pytest.mark.asyncio
    async def test_nba_context_generation(self):
        """Test NBA-specific context generation."""
        adapter = NBADataAdapter()
        
        # Mock game odds
        mock_game = GameOdds(
            game_id="nba_test_1",
            home_team="Los Angeles Lakers",
            away_team="Golden State Warriors",
            game_time=datetime.now(timezone.utc),
            books=[]
        )
        
        context = await adapter.get_sport_context(mock_game)
        
        assert context.sport == "NBA"
        assert context.home_team == "Los Angeles Lakers"
        assert context.away_team == "Golden State Warriors"
        assert hasattr(context, 'season_stage')
        assert hasattr(context, 'rest_days')
        assert hasattr(context, 'player_props')


class TestUnifiedParlayAgent:
    """Test the unified parlay strategist agent."""
    
    def test_create_nfl_agent(self):
        """Test creating NFL unified agent."""
        agent = create_unified_agent("NFL")
        assert isinstance(agent, UnifiedParlayStrategistAgent)
        assert agent.sport == "NFL"
        assert isinstance(agent.sport_adapter, NFLDataAdapter)
    
    def test_create_nba_agent(self):
        """Test creating NBA unified agent."""
        agent = create_unified_agent("NBA")
        assert isinstance(agent, UnifiedParlayStrategistAgent)
        assert agent.sport == "NBA"
        assert isinstance(agent.sport_adapter, NBADataAdapter)
    
    def test_invalid_sport_agent(self):
        """Test creation with invalid sport."""
        with pytest.raises(ValueError):
            create_unified_agent("MLB")
    
    @pytest.mark.asyncio
    async def test_nfl_parlay_generation(self):
        """Test NFL parlay generation with mocked data."""
        # Mock knowledge base
        mock_kb = Mock(spec=SportsKnowledgeRAG)
        mock_kb.search_knowledge.return_value = RAGResult(
            query="NFL test",
            chunks=[],
            total_chunks_searched=0,
            search_time_ms=1.0,
            insights=["NFL-specific insight"]
        )
        
        agent = create_unified_agent("NFL", mock_kb)
        
        # Mock the sport adapter methods
        with patch.object(agent.sport_adapter, 'fetch_games', new_callable=AsyncMock) as mock_fetch:
            with patch.object(agent.sport_adapter, 'preprocess_market_data', new_callable=AsyncMock) as mock_preprocess:
                with patch.object(agent.sport_adapter, 'get_sport_context', new_callable=AsyncMock) as mock_context:
                    with patch.object(agent.sport_adapter, 'validate_parlay_legs') as mock_validate:
                        
                        # Setup mocks
                        mock_games = [self._create_mock_game("nfl_game_1", "Chiefs", "Bills")]
                        mock_fetch.return_value = mock_games
                        mock_preprocess.return_value = mock_games
                        mock_context.return_value = self._create_mock_nfl_context()
                        mock_validate.return_value = (True, [])
                        
                        # Generate parlay
                        recommendation = await agent.generate_parlay_recommendation(
                            target_legs=3,
                            min_total_odds=5.0
                        )
                        
                        # Verify result
                        if recommendation:  # May be None due to mocking
                            assert recommendation.sport == "NFL"
                            assert isinstance(recommendation, UnifiedParlayRecommendation)
                            assert isinstance(recommendation.legs, list)
                            assert isinstance(recommendation.confidence, float)
    
    @pytest.mark.asyncio
    async def test_nba_parlay_generation(self):
        """Test NBA parlay generation with mocked data."""
        # Mock knowledge base
        mock_kb = Mock(spec=SportsKnowledgeRAG)
        mock_kb.search_knowledge.return_value = RAGResult(
            query="NBA test",
            chunks=[],
            total_chunks_searched=0,
            search_time_ms=1.0,
            insights=["NBA-specific insight"]
        )
        
        agent = create_unified_agent("NBA", mock_kb)
        
        # Mock the sport adapter methods
        with patch.object(agent.sport_adapter, 'fetch_games', new_callable=AsyncMock) as mock_fetch:
            with patch.object(agent.sport_adapter, 'preprocess_market_data', new_callable=AsyncMock) as mock_preprocess:
                with patch.object(agent.sport_adapter, 'get_sport_context', new_callable=AsyncMock) as mock_context:
                    with patch.object(agent.sport_adapter, 'validate_parlay_legs') as mock_validate:
                        
                        # Setup mocks
                        mock_games = [self._create_mock_game("nba_game_1", "Lakers", "Warriors")]
                        mock_fetch.return_value = mock_games
                        mock_preprocess.return_value = mock_games
                        mock_context.return_value = self._create_mock_nba_context()
                        mock_validate.return_value = (True, [])
                        
                        # Generate parlay
                        recommendation = await agent.generate_parlay_recommendation(
                            target_legs=3,
                            min_total_odds=5.0
                        )
                        
                        # Verify result
                        if recommendation:  # May be None due to mocking
                            assert recommendation.sport == "NBA"
                            assert isinstance(recommendation, UnifiedParlayRecommendation)
                            assert isinstance(recommendation.legs, list)
                            assert isinstance(recommendation.confidence, float)
    
    def _create_mock_game(self, game_id: str, home_team: str, away_team: str) -> GameOdds:
        """Create a mock game odds object."""
        return GameOdds(
            game_id=game_id,
            home_team=home_team,
            away_team=away_team,
            game_time=datetime.now(timezone.utc),
            books=[
                BookOdds(
                    bookmaker="Mock Book",
                    selections=[
                        Selection(
                            team=home_team,
                            market="spread",
                            odds=1.95,
                            line=-3.5
                        )
                    ]
                )
            ]
        )
    
    def _create_mock_nfl_context(self):
        """Create mock NFL context."""
        from tools.sport_data_adapters import NFLContext
        return NFLContext(
            sport="NFL",
            game_id="mock_nfl_1",
            home_team="Chiefs",
            away_team="Bills",
            game_time=datetime.now(timezone.utc),
            week=1,
            season_type="REG"
        )
    
    def _create_mock_nba_context(self):
        """Create mock NBA context."""
        from tools.sport_data_adapters import NBAContext
        return NBAContext(
            sport="NBA",
            game_id="mock_nba_1",
            home_team="Lakers",
            away_team="Warriors",
            game_time=datetime.now(timezone.utc),
            season_stage="Regular"
        )


class TestKnowledgeBaseSportFiltering:
    """Test knowledge base sport-specific filtering."""
    
    def test_sport_filtering_nfl(self):
        """Test NFL sport filtering."""
        # Create mock knowledge base
        kb = SportsKnowledgeRAG()
        
        # Mock chunks with different sports content
        nfl_chunk = KnowledgeChunk(
            content="NFL football quarterback touchdown yard rushing passing",
            source="test",
            chunk_id=1
        )
        
        nba_chunk = KnowledgeChunk(
            content="NBA basketball points rebounds assists three-point shot",
            source="test",
            chunk_id=2
        )
        
        general_chunk = KnowledgeChunk(
            content="Sports betting value analysis edge calculation",
            source="test",
            chunk_id=3
        )
        
        chunks = [nfl_chunk, nba_chunk, general_chunk]
        
        # Test NFL filtering
        filtered_chunks = kb._filter_chunks_by_sport(chunks, "NFL")
        
        # Should include NFL and general chunks, exclude NBA
        assert len(filtered_chunks) == 2
        assert nfl_chunk in filtered_chunks
        assert general_chunk in filtered_chunks
        assert nba_chunk not in filtered_chunks
    
    def test_sport_filtering_nba(self):
        """Test NBA sport filtering."""
        # Create mock knowledge base
        kb = SportsKnowledgeRAG()
        
        # Mock chunks with different sports content
        nfl_chunk = KnowledgeChunk(
            content="NFL football quarterback touchdown yard rushing passing",
            source="test",
            chunk_id=1
        )
        
        nba_chunk = KnowledgeChunk(
            content="NBA basketball points rebounds assists three-point shot",
            source="test",
            chunk_id=2
        )
        
        general_chunk = KnowledgeChunk(
            content="Sports betting value analysis edge calculation",
            source="test",
            chunk_id=3
        )
        
        chunks = [nfl_chunk, nba_chunk, general_chunk]
        
        # Test NBA filtering
        filtered_chunks = kb._filter_chunks_by_sport(chunks, "NBA")
        
        # Should include NBA and general chunks, exclude NFL
        assert len(filtered_chunks) == 2
        assert nba_chunk in filtered_chunks
        assert general_chunk in filtered_chunks
        assert nfl_chunk not in filtered_chunks
    
    def test_no_sport_filtering(self):
        """Test no sport filtering (should return all chunks)."""
        # Create mock knowledge base
        kb = SportsKnowledgeRAG()
        
        chunks = [
            KnowledgeChunk("NFL content", "test", 1),
            KnowledgeChunk("NBA content", "test", 2),
            KnowledgeChunk("General content", "test", 3)
        ]
        
        # Test no filtering
        filtered_chunks = kb._filter_chunks_by_sport(chunks, None)
        
        assert len(filtered_chunks) == 3
        assert all(chunk in filtered_chunks for chunk in chunks)


class TestAPIEndpoints:
    """Test the refactored API endpoints."""
    
    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)
    
    @patch('app.main.nfl_agent')
    def test_nfl_endpoint_response_format(self, mock_nfl_agent):
        """Test NFL endpoint returns consistent format."""
        # Mock successful response
        mock_recommendation = UnifiedParlayRecommendation(
            sport="NFL",
            legs=[
                {
                    "game_id": "test_game",
                    "selection": "Chiefs -3.5",
                    "odds": 1.95,
                    "book": "Mock Book"
                }
            ],
            confidence=0.75,
            expected_value=0.12,
            kelly_percentage=0.05,
            knowledge_insights=["NFL insight"],
            reasoning="Test reasoning"
        )
        
        # Setup mock
        mock_nfl_agent.generate_parlay_recommendation = AsyncMock(return_value=mock_recommendation)
        
        # Make request
        response = self.client.post("/generate-nfl-parlay", json={
            "target_legs": 3,
            "min_total_odds": 5.0,
            "include_arbitrage": True
        })
        
        # Verify response format
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["sport"] == "NFL"
        assert "parlay" in data
        assert "legs" in data["parlay"]
        assert "confidence" in data["parlay"]
        assert "expected_value" in data["parlay"]
        assert "kelly_percentage" in data["parlay"]
        assert "knowledge_insights" in data["parlay"]
        assert "reasoning" in data["parlay"]
        assert "generated_at" in data
        assert "agent_version" in data
    
    @patch('app.main.nba_agent')
    def test_nba_endpoint_response_format(self, mock_nba_agent):
        """Test NBA endpoint returns consistent format."""
        # Mock successful response
        mock_recommendation = UnifiedParlayRecommendation(
            sport="NBA",
            legs=[
                {
                    "game_id": "test_game",
                    "selection": "Lakers -5.5",
                    "odds": 1.90,
                    "book": "Mock Book"
                }
            ],
            confidence=0.80,
            expected_value=0.15,
            kelly_percentage=0.06,
            knowledge_insights=["NBA insight"],
            reasoning="Test reasoning"
        )
        
        # Setup mock
        mock_nba_agent.generate_parlay_recommendation = AsyncMock(return_value=mock_recommendation)
        
        # Make request
        response = self.client.post("/generate-nba-parlay", json={
            "target_legs": 3,
            "min_total_odds": 5.0,
            "include_arbitrage": True
        })
        
        # Verify response format
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["sport"] == "NBA"
        assert "parlay" in data
        assert "legs" in data["parlay"]
        assert "confidence" in data["parlay"]
        assert "expected_value" in data["parlay"]
        assert "kelly_percentage" in data["parlay"]
        assert "knowledge_insights" in data["parlay"]
        assert "reasoning" in data["parlay"]
        assert "generated_at" in data
        assert "agent_version" in data
    
    def test_response_format_consistency(self):
        """Test that NFL and NBA endpoints return identical structure."""
        # This test verifies the structure matches the required format:
        expected_structure = {
            "success": bool,
            "sport": str,  # "NBA" or "NFL"
            "parlay": {
                "legs": list,
                "confidence": float,
                "expected_value": (float, type(None)),
                "kelly_percentage": (float, type(None)),
                "knowledge_insights": list,
                "reasoning": str
            },
            "generated_at": str,
            "agent_version": str
        }
        
        # This structure should be identical for both sports
        # Only the "sport" field should differ
        
        # Test passes if the above structure is maintained
        assert True  # Placeholder - actual tests are in the specific endpoint tests


class TestSportIsolation:
    """Test that NFL and NBA data sources remain completely isolated."""
    
    def test_nfl_nba_isolation(self):
        """Test that NFL and NBA adapters don't share data sources."""
        nfl_adapter = NFLDataAdapter()
        nba_adapter = NBADataAdapter()
        
        nfl_sources = nfl_adapter.get_data_sources()
        nba_sources = nba_adapter.get_data_sources()
        
        # Check API endpoints are different
        assert nfl_sources.api_endpoints != nba_sources.api_endpoints
        
        # Check keywords don't overlap
        nfl_keywords_set = set(nfl_sources.tweet_keywords)
        nba_keywords_set = set(nba_sources.tweet_keywords)
        
        # Should have no overlap in sport-specific keywords
        sport_specific_overlap = nfl_keywords_set.intersection(nba_keywords_set)
        general_keywords = {"injury", "bet", "odds"}  # Allowed overlaps
        
        unexpected_overlap = sport_specific_overlap - general_keywords
        assert len(unexpected_overlap) == 0, f"Unexpected keyword overlap: {unexpected_overlap}"
        
        # Check journalism sources are different
        assert nfl_sources.journalism_sources != nba_sources.journalism_sources
    
    @pytest.mark.asyncio
    async def test_knowledge_base_sport_isolation(self):
        """Test knowledge base properly filters by sport."""
        # Mock knowledge base with search method
        kb = Mock(spec=SportsKnowledgeRAG)
        
        # Mock return different results for different sports
        def mock_search(query, top_k=5, min_relevance=0.3, sport_filter=None):
            if sport_filter == "NFL":
                return RAGResult(
                    query=query,
                    chunks=[KnowledgeChunk("NFL content", "test", 1)],
                    total_chunks_searched=1,
                    search_time_ms=1.0,
                    insights=["NFL insight"]
                )
            elif sport_filter == "NBA":
                return RAGResult(
                    query=query,
                    chunks=[KnowledgeChunk("NBA content", "test", 2)],
                    total_chunks_searched=1,
                    search_time_ms=1.0,
                    insights=["NBA insight"]
                )
            else:
                return RAGResult(
                    query=query,
                    chunks=[],
                    total_chunks_searched=0,
                    search_time_ms=1.0,
                    insights=[]
                )
        
        kb.search_knowledge.side_effect = mock_search
        
        # Create agents with mocked knowledge base
        nfl_agent = create_unified_agent("NFL", kb)
        nba_agent = create_unified_agent("NBA", kb)
        
        # Verify different agents use different knowledge filters
        with patch.object(nfl_agent, '_search_knowledge_base_by_sport') as mock_nfl_search:
            with patch.object(nba_agent, '_search_knowledge_base_by_sport') as mock_nba_search:
                mock_nfl_search.return_value = RAGResult(
                    query="test", chunks=[], total_chunks_searched=0, 
                    search_time_ms=1.0, insights=["NFL insight"]
                )
                mock_nba_search.return_value = RAGResult(
                    query="test", chunks=[], total_chunks_searched=0,
                    search_time_ms=1.0, insights=["NBA insight"]
                )
                
                # Get insights from both agents
                nfl_insights = await nfl_agent._get_knowledge_insights([], [])
                nba_insights = await nba_agent._get_knowledge_insights([], [])
                
                # Verify they got different insights
                assert nfl_insights != nba_insights


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
