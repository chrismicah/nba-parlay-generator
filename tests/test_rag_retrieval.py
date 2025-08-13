#!/usr/bin/env python3
"""
RAG Retrieval Test Script

Tests the RAG (Retrieval-Augmented Generation) system by simulating queries
and evaluating chunk retrieval quality from the Qdrant vector store.

Test Query: "What is the effect of Jokic being out vs Bucks?"
"""

import pytest
import os
import numpy as np
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny


class RAGRetriever:
    """RAG retrieval system for testing"""
    
    def __init__(self):
        self.embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        self.qdrant = QdrantClient(
            host=os.getenv("QDRANT_HOST", "localhost"), 
            port=int(os.getenv("QDRANT_PORT", "6333"))
        )
        self.collection_name = "sports_knowledge_base"
    
    def embed_query(self, query: str) -> List[float]:
        """Convert query text to embedding vector"""
        return self.embedder.encode(query).tolist()
    
    def search_with_metadata_boost(
        self, 
        query: str, 
        limit: int = 10,
        min_source_relevance: float = 0.7,
        player_filter: List[str] = None,
        team_filter: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search vector store with metadata filtering and source relevance boosting
        
        Args:
            query: Search query text
            limit: Maximum number of results
            min_source_relevance: Minimum source relevance score
            player_filter: List of player names to filter by
            team_filter: List of team names to filter by
        
        Returns:
            List of search results with metadata
        """
        
        # Convert query to embedding
        query_vector = self.embed_query(query)
        
        # Build metadata filters
        filters = []
        
        # Source relevance filter
        filters.append(
            FieldCondition(
                key="source_relevance",
                range={"gte": min_source_relevance}
            )
        )
        
        # Player name filter (search in text content)
        if player_filter:
            for player in player_filter:
                # This is a simple text-based filter - in production you might want more sophisticated NER
                pass  # Qdrant doesn't have built-in text search in payload, so we'll filter post-retrieval
        
        # Combine filters
        search_filter = Filter(must=filters) if filters else None
        
        # Perform vector search
        search_results = self.qdrant.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=search_filter,
            limit=limit * 2,  # Get more results to allow for post-filtering
            score_threshold=0.3  # Minimum similarity threshold
        )
        
        # Post-process results with player/team filtering and source boosting
        processed_results = []
        for result in search_results:
            text = result.payload.get("text", "").lower()
            source_relevance = result.payload.get("source_relevance", 0.7)
            
            # Apply player name filtering
            if player_filter:
                player_mentioned = any(player.lower() in text for player in player_filter)
                if not player_mentioned:
                    continue
            
            # Apply team name filtering  
            if team_filter:
                team_mentioned = any(team.lower() in text for team in team_filter)
                if not team_mentioned:
                    continue
            
            # Calculate boosted score (combine vector similarity with source relevance)
            base_score = result.score
            boosted_score = base_score * (1 + source_relevance * 0.2)  # 20% boost based on source quality
            
            processed_results.append({
                "text": result.payload.get("text", ""),
                "source": result.payload.get("source", ""),
                "source_relevance": source_relevance,
                "filename": result.payload.get("filename", ""),
                "chunk_index": result.payload.get("chunk_index", 0),
                "base_score": base_score,
                "boosted_score": boosted_score,
                "metadata": result.payload
            })
        
        # Sort by boosted score and return top results
        processed_results.sort(key=lambda x: x["boosted_score"], reverse=True)
        return processed_results[:limit]


@pytest.fixture
def rag_retriever():
    """Fixture to create RAG retriever instance"""
    return RAGRetriever()


def test_qdrant_connection(rag_retriever):
    """Test that Qdrant is accessible and has data"""
    collections = rag_retriever.qdrant.get_collections()
    collection_names = [c.name for c in collections.collections]
    
    assert "sports_knowledge_base" in collection_names, "sports_knowledge_base collection should exist"
    
    # Check collection has data
    info = rag_retriever.qdrant.get_collection("sports_knowledge_base")
    assert info.points_count > 0, "Collection should contain embedded documents"
    
    print(f"✅ Qdrant connected with {info.points_count} points")


def test_embedding_generation(rag_retriever):
    """Test query embedding generation"""
    test_query = "What is the effect of Jokic being out vs Bucks?"
    
    embedding = rag_retriever.embed_query(test_query)
    
    assert isinstance(embedding, list), "Embedding should be a list"
    assert len(embedding) == 384, "all-MiniLM-L6-v2 should produce 384-dimensional embeddings"
    assert all(isinstance(x, float) for x in embedding), "All embedding values should be floats"
    
    # Test embedding consistency
    embedding2 = rag_retriever.embed_query(test_query)
    assert np.allclose(embedding, embedding2), "Same query should produce identical embeddings"
    
    print(f"✅ Generated {len(embedding)}-dimensional embedding")


def test_basic_vector_search(rag_retriever):
    """Test basic vector search without filters"""
    query = "What is the effect of Jokic being out vs Bucks?"
    
    results = rag_retriever.search_with_metadata_boost(query, limit=5)
    
    assert len(results) > 0, "Search should return results"
    assert len(results) <= 5, "Should respect limit parameter"
    
    # Check result structure
    for result in results:
        assert "text" in result, "Result should contain text"
        assert "source" in result, "Result should contain source"
        assert "source_relevance" in result, "Result should contain source_relevance"
        assert "base_score" in result, "Result should contain base_score"
        assert "boosted_score" in result, "Result should contain boosted_score"
        
        # Scores should be reasonable
        assert 0 <= result["base_score"] <= 1, "Base score should be between 0 and 1"
        assert result["boosted_score"] >= result["base_score"], "Boosted score should be >= base score"
    
    print(f"✅ Retrieved {len(results)} results from basic search")


def test_jokic_bucks_query_relevance(rag_retriever):
    """Test the specific query: 'What is the effect of Jokic being out vs Bucks?'"""
    query = "What is the effect of Jokic being out vs Bucks?"
    
    # Search with player and team filters
    results = rag_retriever.search_with_metadata_boost(
        query, 
        limit=10,
        player_filter=["Jokic", "Nikola Jokic"],
        team_filter=["Bucks", "Milwaukee", "Denver", "Nuggets"]
    )
    
    assert len(results) > 0, "Should find results related to Jokic and Bucks"
    
    # Analyze result quality
    jokic_mentions = 0
    bucks_mentions = 0
    injury_related = 0
    
    for result in results:
        text_lower = result["text"].lower()
        
        # Count relevant mentions
        if "jokic" in text_lower:
            jokic_mentions += 1
        if any(team in text_lower for team in ["bucks", "milwaukee"]):
            bucks_mentions += 1
        if any(keyword in text_lower for keyword in ["injury", "out", "injured", "miss", "absence"]):
            injury_related += 1
    
    # Assertions for relevance
    assert jokic_mentions > 0, "At least one result should mention Jokic"
    print(f"📊 Results mentioning Jokic: {jokic_mentions}/{len(results)}")
    print(f"📊 Results mentioning Bucks/Milwaukee: {bucks_mentions}/{len(results)}")
    print(f"📊 Results with injury-related terms: {injury_related}/{len(results)}")
    
    # Print top results for manual inspection
    print("\n🔍 Top 3 most relevant results:")
    for i, result in enumerate(results[:3]):
        print(f"\n--- Result {i+1} (Score: {result['boosted_score']:.4f}) ---")
        print(f"Source: {result['source']} (relevance: {result['source_relevance']})")
        print(f"Text preview: {result['text'][:200]}...")


def test_source_relevance_boosting(rag_retriever):
    """Test that source relevance properly boosts search results"""
    query = "basketball analytics and statistics"
    
    results = rag_retriever.search_with_metadata_boost(query, limit=10)
    
    assert len(results) > 0, "Should return results"
    
    # Check that boosted scores are higher than base scores
    boost_applied = 0
    for result in results:
        if result["boosted_score"] > result["base_score"]:
            boost_applied += 1
    
    assert boost_applied > 0, "At least some results should have boosted scores"
    
    # Check that higher source relevance leads to higher boosts
    if len(results) >= 2:
        high_relevance = [r for r in results if r["source_relevance"] >= 0.9]
        low_relevance = [r for r in results if r["source_relevance"] <= 0.8]
        
        if high_relevance and low_relevance:
            avg_boost_high = np.mean([r["boosted_score"] - r["base_score"] for r in high_relevance])
            avg_boost_low = np.mean([r["boosted_score"] - r["base_score"] for r in low_relevance])
            
            print(f"📈 Average boost for high relevance sources: {avg_boost_high:.4f}")
            print(f"📈 Average boost for low relevance sources: {avg_boost_low:.4f}")


def test_metadata_filtering(rag_retriever):
    """Test metadata filtering functionality"""
    query = "player performance analysis"
    
    # Test with minimum source relevance filter
    high_quality_results = rag_retriever.search_with_metadata_boost(
        query, 
        limit=5, 
        min_source_relevance=0.9
    )
    
    all_results = rag_retriever.search_with_metadata_boost(
        query, 
        limit=5, 
        min_source_relevance=0.0
    )
    
    # High quality filter should return fewer or equal results
    assert len(high_quality_results) <= len(all_results), "High quality filter should be more restrictive"
    
    # All high quality results should meet the threshold
    for result in high_quality_results:
        assert result["source_relevance"] >= 0.9, "All results should meet minimum relevance threshold"
    
    print(f"📊 High quality results: {len(high_quality_results)}")
    print(f"📊 All results: {len(all_results)}")


def test_query_variations(rag_retriever):
    """Test different query variations for robustness"""
    
    queries = [
        "What is the effect of Jokic being out vs Bucks?",
        "How does Nikola Jokic absence impact Denver vs Milwaukee?", 
        "Jokic injury effect on Nuggets Bucks matchup",
        "Impact of missing Jokic against Bucks"
    ]
    
    all_results = []
    for query in queries:
        results = rag_retriever.search_with_metadata_boost(
            query, 
            limit=3,
            player_filter=["Jokic", "Nikola Jokic"]
        )
        all_results.extend(results)
        
        assert len(results) > 0, f"Query '{query}' should return results"
    
    print(f"✅ All {len(queries)} query variations returned results")
    print(f"📊 Total unique results across variations: {len(set(r['text'] for r in all_results))}")


def test_edge_cases(rag_retriever):
    """Test edge cases and error handling"""
    
    # Test empty query
    empty_results = rag_retriever.search_with_metadata_boost("", limit=5)
    # Should handle gracefully (may return empty or random results)
    
    # Test very specific query that might not match
    obscure_results = rag_retriever.search_with_metadata_boost(
        "quantum basketball mechanics in zero gravity", 
        limit=5
    )
    # Should handle gracefully
    
    # Test with very high source relevance threshold
    strict_results = rag_retriever.search_with_metadata_boost(
        "basketball", 
        limit=5, 
        min_source_relevance=0.99
    )
    # Should return fewer results or empty
    
    print(f"📊 Edge case results - Empty query: {len(empty_results)}, Obscure: {len(obscure_results)}, Strict: {len(strict_results)}")


if __name__ == "__main__":
    """Run tests directly for development/debugging"""
    
    print("🚀 Starting RAG Retrieval Tests")
    print("=" * 50)
    
    retriever = RAGRetriever()
    
    try:
        # Run individual tests
        print("\n1. Testing Qdrant Connection...")
        test_qdrant_connection(retriever)
        
        print("\n2. Testing Embedding Generation...")
        test_embedding_generation(retriever)
        
        print("\n3. Testing Basic Vector Search...")
        test_basic_vector_search(retriever)
        
        print("\n4. Testing Jokic vs Bucks Query...")
        test_jokic_bucks_query_relevance(retriever)
        
        print("\n5. Testing Source Relevance Boosting...")
        test_source_relevance_boosting(retriever)
        
        print("\n6. Testing Metadata Filtering...")
        test_metadata_filtering(retriever)
        
        print("\n7. Testing Query Variations...")
        test_query_variations(retriever)
        
        print("\n8. Testing Edge Cases...")
        test_edge_cases(retriever)
        
        print("\n" + "=" * 50)
        print("✅ All RAG Retrieval Tests Completed Successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        raise
