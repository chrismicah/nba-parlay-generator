import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from tools.multi_sport_embedder import MultiSportEmbedder, COLLECTIONS, NFL_TEAMS, NFL_PLAYERS

class TestMultiSportEmbedder:
    """Test suite for multi-sport RAG embedder"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.embedder = MultiSportEmbedder()
        
    def test_collection_creation(self):
        """Test that sport-specific collections are configured correctly"""
        assert "nba" in COLLECTIONS
        assert "nfl" in COLLECTIONS
        assert COLLECTIONS["nba"] == "sports_knowledge_base_nba"
        assert COLLECTIONS["nfl"] == "sports_knowledge_base_nfl"
    
    def test_sport_determination_from_path(self):
        """Test sport detection from file paths"""
        test_cases = [
            (Path("data/nfl_articles/mahomes_analysis.md"), "nfl"),
            (Path("data/pro_football_focus/chiefs_report.md"), "nfl"),
            (Path("data/football_outsiders/bills_stats.md"), "nfl"),
            (Path("data/nba_articles/lebron_analysis.md"), "nba"),
            (Path("data/the_ringer/lakers_report.md"), "nba"),
            (Path("data/action_network/patriots_game.md"), "nfl"),  # Could be either, but NFL if contains patriots
        ]
        
        for file_path, expected_sport in test_cases:
            sport, _ = self.embedder.determine_sport_and_source(file_path)
            assert sport == expected_sport, f"Expected {expected_sport} for {file_path}, got {sport}"
    
    def test_nfl_team_extraction(self):
        """Test NFL team extraction from text"""
        test_texts = [
            ("Chiefs quarterback Patrick Mahomes threw for 300 yards", ["Kansas City Chiefs"]),
            ("The Patriots and Bills have a historic rivalry", ["New England Patriots", "Buffalo Bills"]),
            ("Ravens defense dominated the game", ["Baltimore Ravens"]),
            ("No teams mentioned in this generic text", []),
        ]
        
        for text, expected_teams in test_texts:
            teams = self.embedder.extract_teams_from_text(text, "nfl")
            
            # Check that all expected teams are found
            for expected_team in expected_teams:
                assert expected_team in teams, f"Expected team {expected_team} not found in {teams}"
    
    def test_nfl_player_extraction(self):
        """Test NFL player extraction from text"""
        test_texts = [
            ("Patrick Mahomes threw three touchdowns", ["Patrick Mahomes"]),
            ("Josh Allen and Joe Burrow are elite quarterbacks", ["Josh Allen", "Joe Burrow"]),
            ("Travis Kelce caught the winning pass", ["Travis Kelce"]),
            ("The offensive line played well", []),
        ]
        
        for text, expected_players in test_texts:
            players = self.embedder.extract_players_from_text(text, "nfl")
            
            # Check that all expected players are found
            for expected_player in expected_players:
                assert expected_player in players, f"Expected player {expected_player} not found in {players}"
    
    def test_metadata_creation(self):
        """Test enhanced metadata creation for NFL content"""
        test_file = Path("data/nfl_analysis/chiefs_mahomes_report.md")
        test_text = """
        Patrick Mahomes and the Kansas City Chiefs are preparing for their playoff matchup.
        The quarterback's ankle injury is a major concern for the team's Super Bowl aspirations.
        Travis Kelce remains the primary target in the red zone.
        """
        
        metadata = self.embedder.create_enhanced_metadata(test_text, test_file, 0)
        
        # Check required fields
        assert metadata["sport"] == "NFL"
        assert metadata["filename"] == "chiefs_mahomes_report.md"
        assert metadata["chunk_index"] == 0
        assert "source_relevance" in metadata
        assert "date" in metadata
        
        # Check entity extraction
        assert "team" in metadata
        assert "player" in metadata
        assert metadata["team"] == "Kansas City Chiefs"
        assert metadata["player"] in ["Patrick Mahomes", "Travis Kelce"]
    
    def test_date_extraction(self):
        """Test date extraction from content and filenames"""
        test_cases = [
            ("Article published on 2025-01-15", "2025-01-15"),
            ("Game scheduled for January 20, 2025", "January 20, 2025"),
            ("Updated 1/15/2025", "1/15/2025"),
        ]
        
        for text, expected_date in test_cases:
            date = self.embedder.extract_date_from_content(text, Path("test.md"))
            assert date == expected_date
    
    @patch('tools.multi_sport_embedder.QdrantClient')
    def test_sport_specific_retrieval(self, mock_qdrant_class):
        """Test sport-specific context retrieval"""
        # Mock Qdrant client
        mock_qdrant = MagicMock()
        mock_qdrant_class.return_value = mock_qdrant
        
        # Mock search results
        mock_hit = MagicMock()
        mock_hit.payload = {
            "text": "Chiefs quarterback Mahomes is injured",
            "sport": "NFL",
            "team": "Kansas City Chiefs",
            "player": "Patrick Mahomes"
        }
        mock_hit.score = 0.95
        mock_qdrant.search.return_value = [mock_hit]
        
        # Create new embedder with mocked client
        embedder = MultiSportEmbedder()
        embedder.qdrant = mock_qdrant
        
        # Test NFL query
        results = embedder.retrieve_sport_context("Mahomes injury impact", "nfl")
        
        assert len(results) == 1
        assert results[0]["text"] == "Chiefs quarterback Mahomes is injured"
        assert results[0]["metadata"]["sport"] == "NFL"
        assert results[0]["score"] == 0.95
        
        # Verify correct collection was searched
        mock_qdrant.search.assert_called_once()
        call_args = mock_qdrant.search.call_args
        assert call_args[1]["collection_name"] == "sports_knowledge_base_nfl"
    
    def test_nfl_teams_mapping(self):
        """Test that NFL teams mapping is comprehensive"""
        # Test that we have all 32 NFL teams represented
        assert len(NFL_TEAMS) == 32
        
        # Test some key teams
        expected_teams = {
            "Chiefs": "Kansas City Chiefs",
            "Patriots": "New England Patriots",
            "Cowboys": "Dallas Cowboys",
            "Packers": "Green Bay Packers"
        }
        
        for short_name, full_name in expected_teams.items():
            assert NFL_TEAMS[short_name] == full_name
    
    def test_nfl_players_list(self):
        """Test that NFL players list contains key players"""
        key_players = [
            "Patrick Mahomes",
            "Josh Allen", 
            "Joe Burrow",
            "Aaron Rodgers",
            "Travis Kelce"
        ]
        
        for player in key_players:
            assert player in NFL_PLAYERS, f"Key player {player} missing from NFL_PLAYERS list"

class TestRAGIngestionWorkflow:
    """Test complete RAG ingestion workflow for NFL content"""
    
    def setup_method(self):
        """Setup test fixtures with temporary directory"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        self.embedder = MultiSportEmbedder()
    
    def teardown_method(self):
        """Clean up temporary files"""
        shutil.rmtree(self.temp_dir)
    
    def test_nfl_chunking_and_embedding(self):
        """Test NFL article chunking and embedding process"""
        # Create sample NFL article
        nfl_content = """
        # Chiefs vs Ravens Analysis - Pro Football Focus
        
        Patrick Mahomes' ankle injury significantly impacts the Kansas City Chiefs' offensive capabilities.
        The quarterback's mobility is reduced by approximately 30% based on practice footage analysis.
        
        ## Offensive Line Impact
        The Chiefs' offensive line must provide additional protection for the injured quarterback.
        Travis Kelce becomes an even more critical target in short-yardage situations.
        
        ## Ravens Defense Strategy
        Lamar Jackson and the Baltimore Ravens defense will likely exploit Mahomes' limited mobility.
        Roquan Smith leads a Ravens linebacker corps that excels in coverage.
        
        ## Betting Implications
        - Chiefs total points: Under 24.5 recommended
        - Mahomes passing yards: Under 275.5 
        - Game total: Under 47.5 due to weather conditions
        """
        
        # Write to temporary file
        nfl_file = self.temp_path / "chiefs_ravens_analysis.md"
        nfl_file.write_text(nfl_content)
        
        # Mock the Qdrant operations to avoid actual database calls
        with patch.object(self.embedder, 'qdrant') as mock_qdrant:
            mock_qdrant.upsert.return_value = None
            
            # Process the file
            self.embedder.process_file(nfl_file, "nfl")
            
            # Verify upsert was called
            mock_qdrant.upsert.assert_called_once()
            
            # Check the call arguments
            call_args = mock_qdrant.upsert.call_args
            assert call_args[1]["collection_name"] == "sports_knowledge_base_nfl"
            
            points = call_args[1]["points"]
            assert len(points) > 0
            
            # Check metadata of first point
            first_point = points[0]
            metadata = first_point.payload
            
            assert metadata["sport"] == "NFL"
            assert metadata["filename"] == "chiefs_ravens_analysis.md"
            assert "Kansas City Chiefs" in metadata.get("teams", [])
            assert "Patrick Mahomes" in metadata.get("players", [])
    
    def test_query_filtering_by_sport(self):
        """Test that queries only retrieve sport-specific chunks"""
        # This test would verify that NFL queries don't return NBA content
        with patch.object(self.embedder, 'qdrant') as mock_qdrant:
            # Mock NFL-specific search results
            mock_hit = MagicMock()
            mock_hit.payload = {
                "text": "Mahomes injury analysis from NFL source",
                "sport": "NFL",
                "source": "pff"
            }
            mock_hit.score = 0.9
            mock_qdrant.search.return_value = [mock_hit]
            
            # Perform NFL query
            results = self.embedder.retrieve_sport_context("Mahomes injury", "nfl")
            
            # Verify results are NFL-specific
            assert len(results) == 1
            assert results[0]["metadata"]["sport"] == "NFL"
            
            # Verify correct filter was applied
            search_call = mock_qdrant.search.call_args
            query_filter = search_call[1]["query_filter"]
            
            # The filter should ensure only NFL content is returned
            assert query_filter is not None

class TestIntegrationWithExistingRAG:
    """Test integration with existing NBA RAG system"""
    
    def test_nba_queries_unaffected(self):
        """Test that NBA queries still work and don't return NFL content"""
        embedder = MultiSportEmbedder()
        
        with patch.object(embedder, 'qdrant') as mock_qdrant:
            # Mock NBA-specific search results
            mock_hit = MagicMock()
            mock_hit.payload = {
                "text": "LeBron James Lakers analysis",
                "sport": "NBA",
                "source": "the_ringer"
            }
            mock_hit.score = 0.88
            mock_qdrant.search.return_value = [mock_hit]
            
            # Perform NBA query
            results = embedder.retrieve_sport_context("LeBron injury impact", "nba")
            
            # Verify NBA collection was searched
            search_call = mock_qdrant.search.call_args
            assert search_call[1]["collection_name"] == "sports_knowledge_base_nba"
            
            # Verify NBA-specific filter
            query_filter = search_call[1]["query_filter"]
            assert query_filter is not None
    
    def test_separate_collections_maintained(self):
        """Test that NBA and NFL content is stored in separate collections"""
        assert COLLECTIONS["nba"] != COLLECTIONS["nfl"]
        assert "nba" in COLLECTIONS["nba"]
        assert "nfl" in COLLECTIONS["nfl"]

def test_sample_nfl_content_creation():
    """Test creation of sample NFL content for validation"""
    embedder = MultiSportEmbedder()
    
    with patch.object(embedder, 'process_file') as mock_process:
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.write.return_value = None
            
            # Create sample content
            embedder.create_sample_nfl_content()
            
            # Verify process_file was called for each sample article
            assert mock_process.call_count >= 2  # At least 2 sample articles

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
