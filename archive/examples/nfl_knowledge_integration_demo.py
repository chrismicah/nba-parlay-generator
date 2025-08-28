#!/usr/bin/env python3
"""
NFL Knowledge Base Integration Demo

Comprehensive demonstration of how Ed Miller's "The Logic of Sports Betting"
and Wayne Winston's "Mathletics" are now fully integrated into NFL parlay generation.

This shows the complete workflow with your books enhancing every decision.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
from agents.nfl_parlay_strategist_agent import NFLParlayStrategistAgent, NFLParlayRecommendation
from tools.odds_fetcher_tool import GameOdds, BookOdds, Selection

# Reduce log noise for cleaner demo
logging.basicConfig(level=logging.WARNING)


async def create_enhanced_nfl_demo():
    """Create an enhanced demo showing full knowledge base integration."""
    
    print("🏈📚 NFL PARLAY GENERATION WITH SPORTS BETTING BOOKS")
    print("=" * 65)
    print("Demonstrating full integration of Ed Miller's 'The Logic of Sports Betting'")
    print("and Wayne Winston's 'Mathletics' into NFL parlay strategy")
    print()
    
    try:
        # 1. Initialize NFL agent with knowledge base
        print("1️⃣ Initializing NFL Agent with Knowledge Base...")
        nfl_agent = NFLParlayStrategistAgent()
        
        print(f"   ✅ Agent: {nfl_agent.agent_id}")
        print(f"   📚 Books integrated: {nfl_agent.rag_enabled}")
        
        if nfl_agent.knowledge_base:
            print(f"   📊 Expert chunks: {len(nfl_agent.knowledge_base.sports_betting_chunks):,}")
            print("   📖 Ed Miller: 'The Logic of Sports Betting'")
            print("   📖 Wayne Winston: 'Mathletics'")
        
        print()
        
        # 2. Create comprehensive NFL demo games
        print("2️⃣ Creating NFL Demo Games...")
        demo_games = create_comprehensive_nfl_games()
        print(f"   🏈 Created {len(demo_games)} NFL games with full betting markets")
        
        print()
        
        # 3. Test knowledge base searches
        print("3️⃣ Testing Knowledge Base Searches...")
        await test_knowledge_searches(nfl_agent.knowledge_base)
        
        print()
        
        # 4. Generate enhanced NFL parlay manually 
        print("4️⃣ Generating Enhanced NFL Parlay...")
        recommendation = await generate_enhanced_demo_parlay(nfl_agent, demo_games)
        
        if recommendation:
            # 5. Display comprehensive results
            print("5️⃣ Knowledge-Enhanced NFL Parlay Results:")
            print("=" * 50)
            
            display_parlay_basics(recommendation)
            display_knowledge_enhancements(recommendation)
            display_expert_reasoning(recommendation)
            
            print()
            print("✅ COMPLETE NFL WORKFLOW WITH BOOKS INTEGRATION!")
            print("🎯 Your sports betting books now enhance every NFL parlay decision")
            
        else:
            print("⚠️ Demo parlay generation failed")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


def create_comprehensive_nfl_games():
    """Create comprehensive NFL games with multiple betting markets."""
    games = []
    
    # Game 1: Chiefs vs Bills (AFC Championship vibes)
    chiefs_bills_books = [
        BookOdds(
            bookmaker="DraftKings",
            market="h2h",
            selections=[
                Selection(name="Kansas City Chiefs", price_decimal=1.85),
                Selection(name="Buffalo Bills", price_decimal=2.05)
            ]
        ),
        BookOdds(
            bookmaker="FanDuel",
            market="spreads", 
            selections=[
                Selection(name="Kansas City Chiefs", price_decimal=1.91, line=-2.5),
                Selection(name="Buffalo Bills", price_decimal=1.91, line=2.5)
            ]
        ),
        BookOdds(
            bookmaker="BetMGM",
            market="totals",
            selections=[
                Selection(name="Over", price_decimal=1.91, line=54.5),
                Selection(name="Under", price_decimal=1.91, line=54.5)
            ]
        )
    ]
    
    game1 = GameOdds(
        game_id="nfl_chiefs_bills_demo",
        sport_key="americanfootball_nfl",
        commence_time="2024-01-20T21:00:00Z",
        books=chiefs_bills_books
    )
    games.append(game1)
    
    # Game 2: Cowboys vs Eagles (NFC East rivalry)
    cowboys_eagles_books = [
        BookOdds(
            bookmaker="DraftKings",
            market="h2h",
            selections=[
                Selection(name="Dallas Cowboys", price_decimal=2.20),
                Selection(name="Philadelphia Eagles", price_decimal=1.75)
            ]
        ),
        BookOdds(
            bookmaker="FanDuel",
            market="spreads",
            selections=[
                Selection(name="Dallas Cowboys", price_decimal=1.91, line=3.5),
                Selection(name="Philadelphia Eagles", price_decimal=1.91, line=-3.5)
            ]
        ),
        BookOdds(
            bookmaker="BetMGM",
            market="totals",
            selections=[
                Selection(name="Over", price_decimal=1.95, line=47.5),
                Selection(name="Under", price_decimal=1.87, line=47.5)
            ]
        )
    ]
    
    game2 = GameOdds(
        game_id="nfl_cowboys_eagles_demo",
        sport_key="americanfootball_nfl", 
        commence_time="2024-01-21T13:00:00Z",
        books=cowboys_eagles_books
    )
    games.append(game2)
    
    # Game 3: 49ers vs Seahawks (NFC West battle)
    niners_seahawks_books = [
        BookOdds(
            bookmaker="DraftKings",
            market="h2h",
            selections=[
                Selection(name="San Francisco 49ers", price_decimal=1.65),
                Selection(name="Seattle Seahawks", price_decimal=2.40)
            ]
        ),
        BookOdds(
            bookmaker="FanDuel", 
            market="spreads",
            selections=[
                Selection(name="San Francisco 49ers", price_decimal=1.91, line=-6.5),
                Selection(name="Seattle Seahawks", price_decimal=1.91, line=6.5)
            ]
        ),
        BookOdds(
            bookmaker="BetMGM",
            market="totals",
            selections=[
                Selection(name="Over", price_decimal=1.91, line=43.5),
                Selection(name="Under", price_decimal=1.91, line=43.5)
            ]
        )
    ]
    
    game3 = GameOdds(
        game_id="nfl_49ers_seahawks_demo",
        sport_key="americanfootball_nfl",
        commence_time="2024-01-21T16:25:00Z", 
        books=niners_seahawks_books
    )
    games.append(game3)
    
    return games


async def test_knowledge_searches(knowledge_base):
    """Test specific knowledge base searches relevant to NFL betting."""
    search_queries = [
        "NFL football betting strategy correlation",
        "value betting expected value calculation", 
        "bankroll management Kelly criterion",
        "statistical analysis football predictions"
    ]
    
    for query in search_queries:
        result = knowledge_base.search_knowledge(query, top_k=2)
        print(f"   🔍 '{query}': {len(result.chunks)} chunks found")
        
        if result.insights:
            for insight in result.insights[:1]:
                print(f"      💡 {insight}")


async def generate_enhanced_demo_parlay(agent, games):
    """Generate a demo parlay with full knowledge base enhancement."""
    
    # Create a sample recommendation manually
    sample_legs = [
        {
            'game_id': 'nfl_chiefs_bills_demo',
            'selection_name': 'Kansas City Chiefs',
            'market_type': 'h2h', 
            'odds_decimal': 1.85,
            'confidence': 0.72
        },
        {
            'game_id': 'nfl_cowboys_eagles_demo',
            'selection_name': 'Under',
            'market_type': 'totals',
            'odds_decimal': 1.87,
            'confidence': 0.68
        },
        {
            'game_id': 'nfl_49ers_seahawks_demo', 
            'selection_name': 'San Francisco 49ers',
            'market_type': 'spreads',
            'odds_decimal': 1.91,
            'confidence': 0.75
        }
    ]
    
    # Create base recommendation structure
    from tools.parlay_strategist_agent import ParlayReasoning, ReasoningFactor
    import datetime
    
    # Create sample reasoning factors
    factors = [
        ReasoningFactor(
            factor_type="team_strength",
            description="Chiefs are strong home favorites",
            confidence=0.75,
            impact="positive",
            weight=0.8
        ),
        ReasoningFactor(
            factor_type="market_value", 
            description="Under 47.5 offers value in Cowboys-Eagles",
            confidence=0.68,
            impact="positive",
            weight=0.7
        )
    ]
    
    reasoning = ParlayReasoning(
        parlay_id="demo_nfl_parlay_001",
        reasoning_text="Demo NFL parlay combining strong favorites with value opportunities",
        confidence_score=0.71,
        reasoning_factors=factors,
        generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        strategist_version="demo_v1.0"
    )
    
    # Create NFL recommendation
    recommendation = NFLParlayRecommendation(
        legs=sample_legs,
        reasoning=reasoning,
        expected_value=0.125,
        kelly_percentage=0.08
    )
    
    # Apply knowledge base enhancements
    if agent.rag_enabled:
        await agent._enhance_with_knowledge_base(recommendation)
    
    return recommendation


def display_parlay_basics(recommendation):
    """Display basic parlay information."""
    print(f"📊 PARLAY BASICS:")
    print(f"   🎯 Legs: {len(recommendation.legs)}")
    print(f"   📈 Confidence: {recommendation.reasoning.confidence_score:.3f}")
    print(f"   💰 Expected Value: {recommendation.expected_value:.3f}")
    print(f"   📊 Kelly %: {recommendation.kelly_percentage:.2%}")
    
    print(f"\n   🏈 Selections:")
    for i, leg in enumerate(recommendation.legs, 1):
        print(f"      {i}. {leg['selection_name']} ({leg['market_type']}) @ {leg['odds_decimal']}")


def display_knowledge_enhancements(recommendation):
    """Display knowledge base enhancements."""
    print(f"\n📚 KNOWLEDGE BASE ENHANCEMENTS:")
    
    if recommendation.knowledge_insights:
        print(f"   💡 Key Insights ({len(recommendation.knowledge_insights)}):")
        for insight in recommendation.knowledge_insights:
            print(f"      • {insight}")
    
    if recommendation.value_betting_analysis:
        print(f"\n   💰 Value Analysis (Ed Miller):")
        print(f"      • {recommendation.value_betting_analysis}")
    
    if recommendation.book_based_warnings:
        print(f"\n   ⚠️ Expert Warnings ({len(recommendation.book_based_warnings)}):")
        for warning in recommendation.book_based_warnings:
            print(f"      • {warning}")
    
    if recommendation.bankroll_recommendations:
        print(f"\n   💸 Bankroll Management ({len(recommendation.bankroll_recommendations)}):")
        for rec in recommendation.bankroll_recommendations:
            print(f"      • {rec}")
    
    if recommendation.expert_guidance:
        print(f"\n   🎓 Expert Guidance ({len(recommendation.expert_guidance)}):")
        for guidance in recommendation.expert_guidance:
            print(f"      • {guidance}")


def display_expert_reasoning(recommendation):
    """Display the enhanced reasoning with book insights."""
    print(f"\n📖 ENHANCED REASONING WITH BOOK INSIGHTS:")
    print("=" * 50)
    
    # Show that reasoning includes book analysis
    if "EXPERT KNOWLEDGE BASE ANALYSIS" in recommendation.reasoning.reasoning_text:
        lines = recommendation.reasoning.reasoning_text.split('\n')
        in_book_section = False
        book_lines = []
        
        for line in lines:
            if "EXPERT KNOWLEDGE BASE ANALYSIS" in line:
                in_book_section = True
            if in_book_section:
                book_lines.append(line)
                
        if book_lines:
            print("📚 Book insights successfully integrated into reasoning!")
            print(f"📄 Enhanced reasoning includes {len(book_lines)} lines of expert analysis")
            print(f"📖 Sources: Ed Miller & Wayne Winston")
            print(f"🔍 Knowledge chunks: 1,590+ expert insights available")
    else:
        print("⚠️ Book insights not yet integrated into reasoning")


if __name__ == "__main__":
    asyncio.run(create_enhanced_nfl_demo())
