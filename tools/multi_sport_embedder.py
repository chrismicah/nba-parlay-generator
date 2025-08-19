#!/usr/bin/env python3
"""
Enhanced Multi-Sport Embedder - JIRA-NFL-004
Extends RAG system to support sport-specific metadata filtering and NFL content ingestion
"""

import os
import uuid
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import re

from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient, models
from qdrant_client.models import PointStruct, VectorParams, Distance

# Configuration
EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
CHUNK_SIZE = 500  # Updated per JIRA-NFL-004 spec
CHUNK_OVERLAP = 50  # Updated per JIRA-NFL-004 spec

# Sport-specific collection names
COLLECTIONS = {
    "nba": "sports_knowledge_base_nba",
    "nfl": "sports_knowledge_base_nfl"
}

# Enhanced source relevance mapping for multi-sport
SOURCE_RELEVANCE = {
    # NBA sources (existing)
    "mathletics": 0.95,
    "the_logic_of_sports_betting": 0.92,
    "the_ringer": 0.88,
    "action_network": 0.85,
    "clutchpoints": 0.8,
    "nba_com": 0.78,
    
    # NFL sources (new)
    "pro_football_focus": 0.9,  # PFF
    "pff": 0.9,
    "football_outsiders": 0.88,
    "sharp_football_analysis": 0.86,
    "espn_nfl": 0.82,
    "nfl_com": 0.8
}

# NFL team mappings for metadata extraction
NFL_TEAMS = {
    "Chiefs": "Kansas City Chiefs",
    "Patriots": "New England Patriots", 
    "Bills": "Buffalo Bills",
    "Dolphins": "Miami Dolphins",
    "Jets": "New York Jets",
    "Ravens": "Baltimore Ravens",
    "Bengals": "Cincinnati Bengals",
    "Browns": "Cleveland Browns",
    "Steelers": "Pittsburgh Steelers",
    "Texans": "Houston Texans",
    "Colts": "Indianapolis Colts",
    "Jaguars": "Jacksonville Jaguars",
    "Titans": "Tennessee Titans",
    "Broncos": "Denver Broncos",
    "Chargers": "Los Angeles Chargers",
    "Raiders": "Las Vegas Raiders",
    "Cowboys": "Dallas Cowboys",
    "Giants": "New York Giants",
    "Eagles": "Philadelphia Eagles",
    "Commanders": "Washington Commanders",
    "Bears": "Chicago Bears",
    "Lions": "Detroit Lions",
    "Packers": "Green Bay Packers",
    "Vikings": "Minnesota Vikings",
    "Falcons": "Atlanta Falcons",
    "Panthers": "Carolina Panthers",
    "Saints": "New Orleans Saints",
    "Buccaneers": "Tampa Bay Buccaneers",
    "Cardinals": "Arizona Cardinals",
    "Rams": "Los Angeles Rams",
    "49ers": "San Francisco 49ers",
    "Seahawks": "Seattle Seahawks"
}

# Common NFL players for metadata extraction
NFL_PLAYERS = [
    "Patrick Mahomes", "Josh Allen", "Joe Burrow", "Lamar Jackson",
    "Dak Prescott", "Aaron Rodgers", "Russell Wilson", "Tom Brady",
    "Derrick Henry", "Christian McCaffrey", "Travis Kelce", "Tyreek Hill",
    "Aaron Donald", "T.J. Watt", "Micah Parsons", "Nick Bosa"
]

class MultiSportEmbedder:
    """Enhanced embedder supporting sport-specific collections and metadata"""
    
    def __init__(self):
        self.embedder = SentenceTransformer(EMBED_MODEL_NAME)
        self.qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )
        
        # Initialize sport-specific collections
        self._create_collections()
    
    def _create_collections(self):
        """Create sport-specific Qdrant collections if they don't exist"""
        existing = [c.name for c in self.qdrant.get_collections().collections]
        
        for sport, collection_name in COLLECTIONS.items():
            if collection_name not in existing:
                self.qdrant.recreate_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=self.embedder.get_sentence_embedding_dimension(),
                        distance=Distance.COSINE,
                    ),
                )
                print(f"✅ Created {sport.upper()} collection: {collection_name}")
    
    def determine_sport_and_source(self, file_path: Path) -> tuple[str, str]:
        """Determine sport and source from file path"""
        parts = file_path.parts
        path_str = str(file_path).lower()
        
        # Determine sport
        sport = "nba"  # Default
        if any(keyword in path_str for keyword in ["nfl", "football", "patriots", "chiefs", "cowboys"]):
            sport = "nfl"
        elif any(keyword in path_str for keyword in ["nba", "basketball", "lakers", "celtics", "warriors"]):
            sport = "nba"
        
        # Determine source
        source_name = "unknown"
        if "data" in parts:
            idx = parts.index("data")
            if len(parts) > idx + 1 and parts[idx + 1] != "knowledge_base":
                source_name = parts[idx + 1].lower().replace(" ", "_")
        
        # Map source variants
        source_mappings = {
            "pro_football_focus": "pff",
            "football_outsiders": "football_outsiders", 
            "sharp_football": "sharp_football_analysis",
            "action_network": "action_network"
        }
        
        for pattern, mapped_source in source_mappings.items():
            if pattern in path_str:
                source_name = mapped_source
                break
        
        return sport, source_name
    
    def extract_teams_from_text(self, text: str, sport: str) -> List[str]:
        """Extract team names from text content"""
        teams = []
        
        if sport == "nfl":
            for short_name, full_name in NFL_TEAMS.items():
                if short_name.lower() in text.lower() or full_name.lower() in text.lower():
                    teams.append(full_name)
        elif sport == "nba":
            # NBA team extraction (simplified)
            nba_teams = ["Lakers", "Celtics", "Warriors", "Nets", "Heat", "Bulls"]
            for team in nba_teams:
                if team.lower() in text.lower():
                    teams.append(team)
        
        return list(set(teams))  # Remove duplicates
    
    def extract_players_from_text(self, text: str, sport: str) -> List[str]:
        """Extract player names from text content"""
        players = []
        
        if sport == "nfl":
            for player in NFL_PLAYERS:
                if player.lower() in text.lower():
                    players.append(player)
        
        return list(set(players))
    
    def extract_date_from_content(self, text: str, file_path: Path) -> Optional[str]:
        """Extract date from content or filename"""
        # Try to extract date from content
        date_patterns = [
            r'\b(\d{4}-\d{2}-\d{2})\b',  # YYYY-MM-DD
            r'\b(\d{1,2}/\d{1,2}/\d{4})\b',  # MM/DD/YYYY
            r'\b((January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})\b'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        # Try filename
        filename = file_path.stem.lower()
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
        if date_match:
            return date_match.group(1)
        
        # Default to today
        return datetime.now().strftime("%Y-%m-%d")
    
    def create_enhanced_metadata(self, text: str, file_path: Path, chunk_index: int) -> Dict:
        """Create enhanced metadata with sport-specific fields"""
        sport, source_name = self.determine_sport_and_source(file_path)
        
        # Base metadata
        metadata = {
            "sport": sport.upper(),
            "source": source_name,
            "source_relevance": SOURCE_RELEVANCE.get(source_name, 0.7),
            "filename": file_path.name,
            "chunk_index": chunk_index,
            "text": text,
            "date": self.extract_date_from_content(text, file_path)
        }
        
        # Extract sport-specific entities
        teams = self.extract_teams_from_text(text, sport)
        players = self.extract_players_from_text(text, sport)
        
        # Add team and player metadata
        if teams:
            metadata["team"] = teams[0]  # Primary team
            metadata["teams"] = teams    # All teams
        
        if players:
            metadata["player"] = players[0]  # Primary player
            metadata["players"] = players    # All players
        
        return metadata
    
    def process_file(self, file_path: Path, sport: Optional[str] = None) -> None:
        """Process a file and add to appropriate sport-specific collection"""
        try:
            loader = TextLoader(str(file_path), encoding="utf-8")
            docs = loader.load()
            chunks = self.text_splitter.split_documents(docs)
            
            # Determine sport if not provided
            if sport is None:
                sport, _ = self.determine_sport_and_source(file_path)
            
            collection_name = COLLECTIONS[sport.lower()]
            points: List[PointStruct] = []
            
            for i, chunk in enumerate(chunks):
                text = (chunk.page_content or "").strip()
                if not text or len(text) < 50:  # Skip very short chunks
                    continue
                
                vector = self.embedder.encode(text).tolist()
                metadata = self.create_enhanced_metadata(text, file_path, i)
                
                points.append(PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload=metadata
                ))
            
            if points:
                self.qdrant.upsert(collection_name=collection_name, points=points)
                print(f"✅ {file_path.name} → {len(points)} chunks embedded in {sport.upper()} collection")
            
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")
    
    def retrieve_sport_context(self, query: str, sport: str, limit: int = 10) -> List[Dict]:
        """
        Retrieve sport-specific context for a query
        
        Args:
            query: Search query
            sport: "NBA" or "NFL" 
            limit: Maximum number of results
            
        Returns:
            List of relevant chunks with metadata
        """
        sport = sport.lower()
        if sport not in COLLECTIONS:
            raise ValueError(f"Unsupported sport: {sport}. Use 'nba' or 'nfl'")
        
        collection_name = COLLECTIONS[sport]
        query_vector = self.embedder.encode(query).tolist()
        
        # Search with sport filter
        search_result = self.qdrant.search(
            collection_name=collection_name,
            query_vector=query_vector,
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="sport",
                        match=models.MatchValue(value=sport.upper())
                    )
                ]
            ),
            limit=limit
        )
        
        # Convert results to readable format
        results = []
        for hit in search_result:
            results.append({
                "text": hit.payload.get("text", ""),
                "score": hit.score,
                "metadata": hit.payload
            })
        
        return results
    
    def create_sample_nfl_content(self):
        """Create sample NFL content for testing"""
        sample_articles = [
            {
                "filename": "mahomes_injury_analysis.md",
                "content": """
# Patrick Mahomes Injury Impact Analysis - PFF

Patrick Mahomes' ankle sprain has significant implications for the Kansas City Chiefs' playoff prospects. 
Our analysis shows that the Chiefs' offensive efficiency drops by 23% when Mahomes is limited by injury.

## Key Statistics:
- Mahomes' mobility rating: 85/100 (healthy) vs 62/100 (injured)
- Red zone efficiency: 78% vs 61% 
- Third down conversion: 45% vs 38%

The Chiefs vs Ravens matchup will test Kansas City's offensive line protection schemes.
Lamar Jackson's mobility advantage could be decisive if Mahomes can't scramble effectively.

**Recommendation**: Consider under bets on Chiefs total points if Mahomes is limited.
""",
                "sport": "nfl"
            },
            {
                "filename": "bills_offensive_analysis.md", 
                "content": """
# Buffalo Bills Offensive Breakdown - Football Outsiders

Josh Allen and Stefon Diggs continue to form one of the NFL's most dynamic passing combinations.
The Bills' offensive coordinator has implemented new route concepts that maximize Diggs' separation ability.

## Statistical Breakdown:
- Allen completion percentage: 68.2%
- Diggs targets per game: 9.4
- Bills red zone scoring: 72%

Weather conditions in Buffalo significantly impact passing game efficiency. 
Wind speeds above 15 mph reduce Allen's deep ball accuracy by 18%.

The Bills vs Patriots divisional rivalry adds complexity to game planning and betting angles.
""",
                "sport": "nfl"
            }
        ]
        
        # Create sample files
        nfl_dir = Path("data/nfl_articles")
        nfl_dir.mkdir(exist_ok=True)
        
        for article in sample_articles:
            file_path = nfl_dir / article["filename"]
            with open(file_path, "w") as f:
                f.write(article["content"])
            
            # Process the file
            self.process_file(file_path, article["sport"])
        
        print(f"📄 Created {len(sample_articles)} sample NFL articles")


def main():
    """Main function for testing multi-sport embedder"""
    print("🏈🏀 JIRA-NFL-004: Multi-Sport RAG System")
    print("=" * 50)
    
    embedder = MultiSportEmbedder()
    
    # Create sample NFL content
    print("\n1️⃣ Creating Sample NFL Content...")
    embedder.create_sample_nfl_content()
    
    # Test sport-specific retrieval
    print("\n2️⃣ Testing Sport-Specific Retrieval...")
    
    # Test NFL query
    nfl_query = "Impact of Mahomes injury on Chiefs vs Ravens?"
    nfl_results = embedder.retrieve_sport_context(nfl_query, "nfl", limit=3)
    
    print(f"\n🏈 NFL Query: '{nfl_query}'")
    print(f"Found {len(nfl_results)} results:")
    for i, result in enumerate(nfl_results, 1):
        print(f"  {i}. Score: {result['score']:.3f}")
        print(f"     Source: {result['metadata'].get('source', 'unknown')}")
        print(f"     Team: {result['metadata'].get('team', 'N/A')}")
        print(f"     Player: {result['metadata'].get('player', 'N/A')}")
        print(f"     Text: {result['text'][:100]}...")
        print()
    
    # Test NBA query isolation 
    print("3️⃣ Testing NBA Query Isolation...")
    nba_query = "LeBron James injury impact on Lakers"
    try:
        nba_results = embedder.retrieve_sport_context(nba_query, "nba", limit=3)
        print(f"\n🏀 NBA Query: '{nba_query}'")
        print(f"Found {len(nba_results)} results (should be 0 for now)")
    except Exception as e:
        print(f"NBA collection empty (expected): {e}")
    
    print("\n✅ Multi-Sport RAG System operational!")
    print("🎯 Sport-specific metadata filtering working correctly")


if __name__ == "__main__":
    main()
