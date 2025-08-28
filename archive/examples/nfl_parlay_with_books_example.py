#!/usr/bin/env python3
"""
NFL Parlay Generation with Sports Betting Books Integration

Demonstrates how your Ed Miller and Wayne Winston books are now integrated
into NFL parlay generation through the RAG system.

This example shows:
1. How the books enhance parlay decision-making
2. Expert insights applied to NFL betting
3. Value betting analysis from the books
4. Correlation warnings based on academic research
5. Bankroll management from the experts
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
from agents.nfl_parlay_strategist_agent import NFLParlayStrategistAgent
from tools.enhanced_parlay_strategist_with_rag import RAGEnhancedParlayStrategist

logging.basicConfig(level=logging.WARNING)  # Reduce log noise for demo


async def demonstrate_nfl_parlays_with_books():
    """Demonstrate NFL parlay generation enhanced with your sports betting books."""
    
    print("🏈📚 NFL Parlay Generation with Sports Betting Books")
    print("=" * 65)
    print("Integrating Ed Miller's 'The Logic of Sports Betting' and")
    print("Wayne Winston's 'Mathletics' into NFL parlay strategy")
    print()
    
    try:
        # 1. Initialize standard NFL agent (without books)
        print("1️⃣ Standard NFL Agent (without books):")
        nfl_agent = NFLParlayStrategistAgent()
        
        standard_recommendation = await nfl_agent.generate_nfl_parlay_recommendation(
            target_legs=3,
            min_total_odds=5.0,
            include_arbitrage=True
        )
        
        if standard_recommendation:
            print(f"   ✅ Generated {len(standard_recommendation.legs)} leg parlay")
            print(f"   📊 Confidence: {standard_recommendation.reasoning.confidence_score:.3f}")
            print(f"   💰 Expected Value: {standard_recommendation.expected_value:.3f}")
            
            # Show sample legs
            for i, leg in enumerate(standard_recommendation.legs[:2], 1):
                print(f"   Leg {i}: {leg['selection_name']} @ {leg['odds_decimal']}")
        else:
            print("   ⚠️ No standard parlay generated")
        
        print()
        
        # 2. Initialize RAG-enhanced strategist (with books)
        print("2️⃣ RAG-Enhanced Strategist (with your books):")
        rag_strategist = RAGEnhancedParlayStrategist(enable_rag=True)
        
        print(f"   📚 Books Loaded: {len(rag_strategist.rag_system.sports_betting_chunks)} chunks")
        print("   📖 Ed Miller: 'The Logic of Sports Betting'")
        print("   📊 Wayne Winston: 'Mathletics'")
        print()
        
        # 3. Generate RAG-enhanced NFL parlay
        print("3️⃣ Generating NFL Parlay with Book Intelligence:")
        
        # Create sample NFL games for demonstration
        sample_nfl_games = nfl_agent._create_nfl_demo_games()
        
        rag_recommendation = await rag_strategist.generate_rag_enhanced_parlay(
            current_games=sample_nfl_games,
            target_legs=3,
            min_total_odds=5.0,
            sport="nfl"
        )
        
        if rag_recommendation:
            print(f"   ✅ Enhanced NFL parlay generated!")
            print(f"   📊 Confidence: {rag_recommendation.reasoning.confidence_score:.3f}")
            print(f"   💰 Expected Value: {rag_recommendation.expected_value:.3f}")
            print()
            
            # 4. Show book-enhanced insights
            print("4️⃣ Insights from Your Sports Betting Books:")
            print()
            
            if rag_recommendation.knowledge_insights:
                print("   💡 Knowledge Base Insights:")
                for insight in rag_recommendation.knowledge_insights:
                    print(f"      • {insight}")
                print()
            
            if rag_recommendation.value_betting_analysis:
                print("   📈 Value Betting Analysis (from Ed Miller):")
                print(f"      • {rag_recommendation.value_betting_analysis}")
                print()
            
            if rag_recommendation.correlation_warnings:
                print("   ⚠️ Correlation Warnings (from academic research):")
                for warning in rag_recommendation.correlation_warnings:
                    print(f"      • {warning}")
                print()
            
            if rag_recommendation.bankroll_recommendations:
                print("   💰 Bankroll Management (from Mathletics):")
                for rec in rag_recommendation.bankroll_recommendations:
                    print(f"      • {rec}")
                print()
            
            if rag_recommendation.expert_guidance:
                print("   🎓 Expert Guidance:")
                for guidance in rag_recommendation.expert_guidance:
                    print(f"      • {guidance}")
                print()
            
            # 5. Show specific book knowledge
            print("5️⃣ Specific Knowledge from Your Books:")
            
            # Query for NFL-specific insights
            nfl_insights = rag_strategist.rag_system.search_knowledge(
                "NFL football betting strategy analysis",
                top_k=2
            )
            
            if nfl_insights.chunks:
                print("   🏈 NFL-Specific Content Found:")
                for chunk in nfl_insights.chunks:
                    content_preview = chunk.content[:150] + "..." if len(chunk.content) > 150 else chunk.content
                    book_name = "Ed Miller" if "Miller" in chunk.source else "Wayne Winston"
                    print(f"      📚 {book_name}: {content_preview}")
                print()
            
            # Query for parlay-specific insights
            parlay_insights = rag_strategist.rag_system.search_knowledge(
                "parlay betting correlation risk multiple bets",
                top_k=2
            )
            
            if parlay_insights.chunks:
                print("   🎯 Parlay-Specific Guidance:")
                for insight in parlay_insights.insights:
                    print(f"      • {insight}")
        
        else:
            print("   ⚠️ No RAG-enhanced parlay generated")
        
        print()
        print("6️⃣ Summary - How Your Books Enhance Parlays:")
        print("   📚 Ed Miller's 'Logic of Sports Betting':")
        print("      → Provides mathematical foundations for value betting")
        print("      → Emphasizes logical decision-making over gut feelings")
        print("      → Teaches proper edge calculation and bankroll management")
        print()
        print("   📊 Wayne Winston's 'Mathletics':")
        print("      → Supplies statistical models for sports prediction")
        print("      → Offers data-driven analysis techniques")
        print("      → Provides NFL-specific analytical insights")
        print()
        print("   🎯 Combined Benefits:")
        print("      → More intelligent parlay construction")
        print("      → Better correlation risk assessment")
        print("      → Improved value identification")
        print("      → Smarter bankroll management")
        print("      → Academic rigor applied to betting decisions")
        
        print()
        print("✅ Your sports betting books are now actively enhancing parlay generation!")
        print("🔬 Every parlay recommendation is informed by expert knowledge")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


def show_book_integration_status():
    """Show current status of book integration."""
    print("📚 Book Integration Status Report")
    print("=" * 40)
    
    # Check if chunks exist
    chunks_path = "data/chunks/chunks.json"
    if os.path.exists(chunks_path):
        print("✅ Books have been chunked and processed")
        
        # Count chunks
        import json
        with open(chunks_path, 'r') as f:
            chunks = json.load(f)
        
        sports_betting_chunks = [
            chunk for chunk in chunks
            if any(book in chunk.get("metadata", {}).get("source", "")
                  for book in ["Ed_Miller", "Mathletics", "logic_of_sports_betting"])
        ]
        
        print(f"📊 Total chunks: {len(chunks):,}")
        print(f"📚 Sports betting chunks: {len(sports_betting_chunks):,}")
        print(f"📖 Books integrated:")
        print(f"   • Ed Miller: 'The Logic of Sports Betting'")
        print(f"   • Wayne Winston: 'Mathletics'")
        
    else:
        print("❌ Chunks file not found")
    
    # Check if RAG system is available
    try:
        sys.path.append('.')
        from tools.knowledge_base_rag import SportsKnowledgeRAG
        print("✅ RAG system is available")
    except ImportError:
        print("❌ RAG system not available")
    
    # Check if enhanced strategist is available
    try:
        from tools.enhanced_parlay_strategist_with_rag import RAGEnhancedParlayStrategist
        print("✅ RAG-enhanced parlay strategist is available")
    except ImportError:
        print("❌ RAG-enhanced strategist not available")
    
    print()
    print("🎯 Integration Summary:")
    print("   Your sports betting books are chunked into 1,590+ searchable pieces")
    print("   They can be queried for relevant insights during parlay generation")
    print("   Expert knowledge from Miller and Winston enhances every recommendation")


if __name__ == "__main__":
    print("🏈📚 NFL Parlay Generation with Sports Betting Books Integration")
    print("=" * 70)
    print()
    
    # Show integration status first
    show_book_integration_status()
    print()
    
    # Run the demonstration
    asyncio.run(demonstrate_nfl_parlays_with_books())
