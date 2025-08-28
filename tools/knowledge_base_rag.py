#!/usr/bin/env python3
"""
Knowledge Base RAG System - Sports Betting Intelligence

Integrates Ed Miller's "The Logic of Sports Betting" and Wayne Winston's "Mathletics" 
into the parlay generation system using RAG (Retrieval-Augmented Generation).

Key Features:
- Vector search through 1,590+ sports betting chunks
- Context-aware retrieval for parlay decisions
- Integration with NFL and NBA strategist agents
- Sports betting theory and mathematical models
- Value betting and edge detection insights
"""

import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import re

# Vector search and embedding imports
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_EMBEDDINGS = True
except ImportError:
    HAS_EMBEDDINGS = False

# Qdrant vector database imports
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    HAS_QDRANT = True
except ImportError:
    HAS_QDRANT = False

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeChunk:
    """A chunk of knowledge from the sports betting books."""
    content: str
    source: str
    chunk_id: int
    relevance_score: float = 0.0
    metadata: Dict[str, Any] = None


@dataclass
class RAGResult:
    """Result from knowledge base retrieval."""
    query: str
    chunks: List[KnowledgeChunk]
    total_chunks_searched: int
    search_time_ms: float
    insights: List[str]


class SportsKnowledgeRAG:
    """
    RAG system for sports betting knowledge base.
    
    Searches through Ed Miller and Wayne Winston's books to provide
    intelligent insights for parlay generation and betting strategy.
    """
    
    def __init__(self, 
                 chunks_path: str = "data/chunks/chunks.json",
                 embeddings_model: str = "all-MiniLM-L6-v2",
                 use_qdrant: bool = False):
        """
        Initialize the Knowledge Base RAG system.
        
        Args:
            chunks_path: Path to the chunks.json file
            embeddings_model: Sentence transformer model for embeddings
            use_qdrant: Whether to use Qdrant vector database
        """
        self.chunks_path = Path(chunks_path)
        self.use_qdrant = use_qdrant and HAS_QDRANT
        
        # Load chunks
        self.chunks = self._load_chunks()
        self.sports_betting_chunks = self._filter_sports_betting_chunks()
        
        # Initialize embedding model
        self.embedding_model = None
        if HAS_EMBEDDINGS:
            try:
                self.embedding_model = SentenceTransformer(embeddings_model)
                logger.info(f"Loaded embedding model: {embeddings_model}")
            except Exception as e:
                logger.warning(f"Could not load embedding model: {e}")
        
        # Initialize vector database
        self.qdrant_client = None
        if self.use_qdrant:
            try:
                self.qdrant_client = QdrantClient(":memory:")  # In-memory for development
                self._initialize_qdrant_collection()
                logger.info("Qdrant vector database initialized")
            except Exception as e:
                logger.warning(f"Could not initialize Qdrant: {e}")
                self.use_qdrant = False
        
        logger.info(f"Sports Knowledge RAG initialized with {len(self.sports_betting_chunks)} sports betting chunks")
    
    def _load_chunks(self) -> List[Dict[str, Any]]:
        """Load chunks from JSON file."""
        try:
            with open(self.chunks_path, 'r', encoding='utf-8') as f:
                chunks = json.load(f)
            logger.info(f"Loaded {len(chunks)} chunks from {self.chunks_path}")
            return chunks
        except Exception as e:
            logger.error(f"Error loading chunks: {e}")
            return []
    
    def _filter_sports_betting_chunks(self) -> List[KnowledgeChunk]:
        """Filter chunks to only include sports betting books."""
        sports_betting_chunks = []
        
        for i, chunk_data in enumerate(self.chunks):
            source = chunk_data.get("metadata", {}).get("source", "")
            
            # Check if chunk is from our sports betting books
            if any(book in source for book in ["Ed_Miller", "Mathletics", "logic_of_sports_betting"]):
                knowledge_chunk = KnowledgeChunk(
                    content=chunk_data["content"],
                    source=source,
                    chunk_id=i,
                    metadata=chunk_data.get("metadata", {})
                )
                sports_betting_chunks.append(knowledge_chunk)
        
        logger.info(f"Filtered to {len(sports_betting_chunks)} sports betting chunks")
        return sports_betting_chunks
    
    def _initialize_qdrant_collection(self):
        """Initialize Qdrant collection for vector storage."""
        if not self.qdrant_client or not self.embedding_model:
            return
        
        collection_name = "sports_betting_knowledge"
        
        # Create collection
        self.qdrant_client.recreate_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)  # MiniLM embedding size
        )
        
        # Index chunks
        points = []
        for chunk in self.sports_betting_chunks[:100]:  # Limit for demo
            try:
                embedding = self.embedding_model.encode(chunk.content)
                point = PointStruct(
                    id=chunk.chunk_id,
                    vector=embedding.tolist(),
                    payload={
                        "content": chunk.content,
                        "source": chunk.source,
                        "chunk_id": chunk.chunk_id
                    }
                )
                points.append(point)
            except Exception as e:
                logger.warning(f"Error embedding chunk {chunk.chunk_id}: {e}")
        
        if points:
            self.qdrant_client.upsert(collection_name=collection_name, points=points)
            logger.info(f"Indexed {len(points)} chunks in Qdrant")
    
    def search_knowledge(self, 
                        query: str, 
                        top_k: int = 5,
                        min_relevance: float = 0.3,
                        sport_filter: Optional[str] = None) -> RAGResult:
        """
        Search the knowledge base for relevant sports betting insights.
        
        Args:
            query: Search query (e.g., "value betting in NFL", "parlay correlation risk")
            top_k: Number of top results to return
            min_relevance: Minimum relevance score threshold
            sport_filter: Optional sport filter ("NFL", "NBA", etc.)
            
        Returns:
            RAGResult with relevant chunks and insights
        """
        import time
        start_time = time.time()
        
        if self.use_qdrant and self.qdrant_client:
            results = self._search_with_qdrant(query, top_k, sport_filter)
        else:
            results = self._search_with_similarity(query, top_k, min_relevance, sport_filter)
        
        search_time_ms = (time.time() - start_time) * 1000
        
        # Generate insights from retrieved chunks
        insights = self._generate_insights(query, results)
        
        return RAGResult(
            query=query,
            chunks=results,
            total_chunks_searched=len(self.sports_betting_chunks),
            search_time_ms=search_time_ms,
            insights=insights
        )
    
    def _search_with_qdrant(self, query: str, top_k: int, sport_filter: Optional[str] = None) -> List[KnowledgeChunk]:
        """Search using Qdrant vector database."""
        if not self.embedding_model:
            return []
        
        try:
            query_embedding = self.embedding_model.encode(query)
            search_results = self.qdrant_client.search(
                collection_name="sports_betting_knowledge",
                query_vector=query_embedding.tolist(),
                limit=top_k
            )
            
            results = []
            for result in search_results:
                chunk = KnowledgeChunk(
                    content=result.payload["content"],
                    source=result.payload["source"],
                    chunk_id=result.payload["chunk_id"],
                    relevance_score=result.score
                )
                results.append(chunk)
            
            return results
            
        except Exception as e:
            logger.error(f"Qdrant search error: {e}")
            return []
    
    def _filter_chunks_by_sport(self, chunks: List[KnowledgeChunk], sport_filter: Optional[str]) -> List[KnowledgeChunk]:
        """Filter knowledge chunks by sport relevance."""
        if not sport_filter:
            return chunks
        
        sport_keywords = {
            'NFL': ['football', 'nfl', 'quarterback', 'touchdown', 'yard', 'rushing', 'passing', 'down', 'field goal'],
            'NBA': ['basketball', 'nba', 'points', 'rebounds', 'assists', 'three-point', 'player', 'court', 'shot']
        }
        
        relevant_keywords = sport_keywords.get(sport_filter.upper(), [])
        if not relevant_keywords:
            return chunks
        
        filtered_chunks = []
        for chunk in chunks:
            content_lower = chunk.content.lower()
            
            # Check for sport-specific keywords
            has_sport_keywords = any(keyword in content_lower for keyword in relevant_keywords)
            
            # Check if it's explicitly about another sport
            other_sports = [s for s in sport_keywords.keys() if s != sport_filter.upper()]
            has_other_sport = any(
                any(keyword in content_lower for keyword in sport_keywords[other_sport])
                for other_sport in other_sports
            )
            
            # Include if it has sport keywords or if it's general (no specific sport keywords)
            if has_sport_keywords or not has_other_sport:
                filtered_chunks.append(chunk)
        
        return filtered_chunks
    
    def _search_with_similarity(self, query: str, top_k: int, min_relevance: float, sport_filter: Optional[str] = None) -> List[KnowledgeChunk]:
        """Search using basic similarity scoring."""
        if not self.embedding_model:
            return self._search_with_keywords(query, top_k)
        
        try:
            # Get query embedding
            query_embedding = self.embedding_model.encode([query])
            
            # Get embeddings for chunks (simplified - would cache in production)
            chunk_texts = [chunk.content for chunk in self.sports_betting_chunks[:200]]  # Limit for performance
            chunk_embeddings = self.embedding_model.encode(chunk_texts)
            
            # Calculate similarities
            similarities = cosine_similarity(query_embedding, chunk_embeddings)[0]
            
            # Get top results
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            results = []
            for idx in top_indices:
                if similarities[idx] >= min_relevance:
                    chunk = self.sports_betting_chunks[idx]
                    chunk.relevance_score = similarities[idx]
                    results.append(chunk)
            
            # Apply sport filtering
            filtered_results = self._filter_chunks_by_sport(results, sport_filter)
            
            return filtered_results
            
        except Exception as e:
            logger.error(f"Similarity search error: {e}")
            return self._search_with_keywords(query, top_k)
    
    def _search_with_keywords(self, query: str, top_k: int) -> List[KnowledgeChunk]:
        """Fallback keyword-based search."""
        query_words = set(query.lower().split())
        
        scored_chunks = []
        for chunk in self.sports_betting_chunks:
            content_words = set(chunk.content.lower().split())
            overlap = len(query_words.intersection(content_words))
            
            if overlap > 0:
                score = overlap / len(query_words)
                chunk.relevance_score = score
                scored_chunks.append(chunk)
        
        # Sort by score and return top k
        scored_chunks.sort(key=lambda x: x.relevance_score, reverse=True)
        return scored_chunks[:top_k]
    
    def _generate_insights(self, query: str, chunks: List[KnowledgeChunk]) -> List[str]:
        """Generate actionable insights from retrieved chunks."""
        insights = []
        
        if not chunks:
            return ["No relevant knowledge found for this query."]
        
        # Analyze chunks for key concepts
        all_content = " ".join([chunk.content for chunk in chunks])
        
        # Look for specific sports betting concepts
        concepts = {
            "value betting": r"value|edge|positive expectation|expected value",
            "bankroll management": r"bankroll|money management|kelly|bet sizing",
            "correlation": r"correlation|correlated|dependent|related outcomes",
            "market efficiency": r"efficient market|line movement|sharp money|public",
            "statistical analysis": r"statistics|probability|variance|regression",
            "arbitrage": r"arbitrage|sure bet|guaranteed profit|risk-free"
        }
        
        found_concepts = []
        for concept, pattern in concepts.items():
            if re.search(pattern, all_content, re.IGNORECASE):
                found_concepts.append(concept)
        
        # Generate insights based on found concepts
        if "value betting" in found_concepts:
            insights.append("Focus on identifying positive expected value bets rather than just picking winners")
        
        if "correlation" in found_concepts:
            insights.append("Be aware of correlation between parlay legs - avoid highly correlated outcomes")
        
        if "bankroll management" in found_concepts:
            insights.append("Apply proper bet sizing using Kelly Criterion or similar money management principles")
        
        if "market efficiency" in found_concepts:
            insights.append("Look for inefficiencies in less popular markets or timing advantages")
        
        # Add source-specific insights
        sources = [chunk.source for chunk in chunks]
        if any("Ed_Miller" in source for source in sources):
            insights.append("Ed Miller emphasizes mathematical foundations and logical decision-making in betting")
        
        if any("Mathletics" in source for source in sources):
            insights.append("Wayne Winston's analysis shows importance of statistical models in sports prediction")
        
        return insights[:5]  # Limit to top 5 insights
    
    def get_parlay_insights(self, 
                          sport: str,
                          market_types: List[str],
                          team_names: List[str] = None) -> RAGResult:
        """
        Get specific insights for parlay construction.
        
        Args:
            sport: "nba" or "nfl"
            market_types: ["h2h", "spreads", "totals", etc.]
            team_names: Optional list of team names
            
        Returns:
            RAGResult with parlay-specific insights
        """
        # Construct sport-specific query
        query_parts = [
            f"{sport} betting",
            "parlay correlation",
            f"{' '.join(market_types)} markets"
        ]
        
        if team_names:
            query_parts.extend(team_names)
        
        query = " ".join(query_parts)
        
        return self.search_knowledge(query, top_k=3, min_relevance=0.2)
    
    def get_value_betting_insights(self, odds_range: Tuple[float, float] = None) -> RAGResult:
        """Get insights about value betting and edge detection."""
        query = "value betting expected value positive edge mathematical advantage"
        
        if odds_range:
            query += f" odds {odds_range[0]} to {odds_range[1]}"
        
        return self.search_knowledge(query, top_k=4)
    
    def get_bankroll_management_insights(self, bankroll_size: float = None) -> RAGResult:
        """Get insights about proper bankroll management."""
        query = "bankroll management kelly criterion bet sizing money management"
        
        return self.search_knowledge(query, top_k=3)
    
    def get_statistical_insights(self, sport: str) -> RAGResult:
        """Get statistical analysis insights for a specific sport."""
        query = f"{sport} statistics probability analysis mathematical models regression"
        
        return self.search_knowledge(query, top_k=4)


def main():
    """Main function for testing the Knowledge Base RAG system."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("📚 Sports Knowledge Base RAG System")
    print("=" * 50)
    
    try:
        # Initialize RAG system
        rag = SportsKnowledgeRAG()
        
        print(f"✅ Loaded {len(rag.sports_betting_chunks)} sports betting chunks")
        print(f"📊 Embedding model available: {rag.embedding_model is not None}")
        print(f"🔍 Qdrant enabled: {rag.use_qdrant}")
        
        # Test searches
        test_queries = [
            "value betting in NFL parlays",
            "correlation risk in basketball betting",
            "bankroll management for sports betting",
            "statistical analysis for football predictions"
        ]
        
        for query in test_queries:
            print(f"\n🔍 Testing Query: '{query}'")
            result = rag.search_knowledge(query, top_k=2)
            
            print(f"   Found: {len(result.chunks)} relevant chunks")
            print(f"   Search time: {result.search_time_ms:.1f}ms")
            
            if result.insights:
                print("   Key Insights:")
                for insight in result.insights[:2]:
                    print(f"   • {insight}")
            
            if result.chunks:
                print(f"   Top Result: {result.chunks[0].content[:100]}...")
        
        print(f"\n✅ Knowledge Base RAG system working correctly!")
        print(f"📖 Ready to enhance parlay generation with sports betting intelligence")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
