#!/usr/bin/env python3
"""
Simple Parlay Creation Example

This example shows the basic steps of how parlays are created in this NBA project
in a simplified, easy-to-understand format.
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from tools.parlay_builder import ParlayBuilder, ParlayLeg
from tools.odds_fetcher_tool import OddsFetcherTool


def create_simple_parlay_example():
    """
    Simple example of how to create a parlay step by step.
    """
    print("🏀 Simple NBA Parlay Creation Example")
    print("=" * 50)
    
    # Step 1: Create the tools we need
    print("🔧 Step 1: Initialize tools")
    odds_fetcher = OddsFetcherTool()
    parlay_builder = ParlayBuilder()
    print("✅ Tools initialized")
    
    # Step 2: Get current NBA games and odds
    print("\n📡 Step 2: Fetch current NBA games")
    try:
        games = odds_fetcher.get_game_odds("basketball_nba", markets=["h2h", "spreads", "totals"])
        print(f"✅ Found {len(games)} NBA games with odds")
        
        # Show first few games
        print("\n📋 Available games:")
        for i, game in enumerate(games[:3]):
            print(f"  {i+1}. Game {game.game_id}")
            for book in game.books[:1]:  # Show first book
                print(f"     {book.bookmaker} - {book.market}")
                for selection in book.selections[:2]:  # Show first 2 selections
                    line_str = f" {selection.line:+.1f}" if selection.line else ""
                    print(f"       • {selection.name}{line_str} @ {selection.price_decimal}")
    
    except Exception as e:
        print(f"⚠️ No live games found (off-season): {e}")
        print("🎲 Using sample data for demonstration")
        games = []
    
    # Step 3: Create parlay legs manually (most common approach)
    print("\n🎯 Step 3: Create parlay legs")
    
    if games:
        # Use real data if available
        sample_legs = create_legs_from_real_data(games)
    else:
        # Use sample data for demonstration
        sample_legs = create_sample_legs()
    
    print(f"✅ Created {len(sample_legs)} parlay legs")
    for i, leg in enumerate(sample_legs, 1):
        line_str = f" {leg.line:+.1f}" if leg.line else ""
        print(f"  {i}. {leg.selection_name}{line_str} @ {leg.odds_decimal} ({leg.bookmaker})")
    
    # Step 4: Validate the parlay
    print("\n🔍 Step 4: Validate parlay against current markets")
    validation = parlay_builder.validate_parlay_legs(sample_legs)
    
    print(f"✅ Validation complete:")
    print(f"  • Original legs: {len(validation.original_legs)}")
    print(f"  • Valid legs: {len(validation.valid_legs)}")
    print(f"  • Invalid legs: {len(validation.invalid_legs)}")
    print(f"  • Success rate: {validation.success_rate():.1f}%")
    print(f"  • Total odds: {validation.total_odds:.2f}")
    
    # Step 5: Calculate potential payout
    print("\n💰 Step 5: Calculate potential payout")
    stake = 100  # $100 bet
    potential_payout = stake * validation.total_odds
    profit = potential_payout - stake
    
    print(f"  • Stake: ${stake}")
    print(f"  • Potential payout: ${potential_payout:.2f}")
    print(f"  • Potential profit: ${profit:.2f}")
    
    # Step 6: Show final parlay
    if validation.is_viable(min_legs=2):
        print(f"\n🏆 Final Parlay Summary")
        print(f"  • {len(validation.valid_legs)} legs")
        print(f"  • Total odds: {validation.total_odds:.2f}")
        print(f"  • Risk: ${stake}")
        print(f"  • Reward: ${profit:.2f}")
        
        print(f"\n📋 Parlay Details:")
        for i, leg in enumerate(validation.valid_legs, 1):
            line_str = f" {leg.line:+.1f}" if leg.line else ""
            print(f"  {i}. {leg.selection_name}{line_str}")
            print(f"     Market: {leg.market_type} | Odds: {leg.odds_decimal} | Book: {leg.bookmaker}")
        
        return validation
    else:
        print(f"\n❌ Parlay not viable (need at least 2 valid legs)")
        return None


def create_legs_from_real_data(games):
    """Create parlay legs from real NBA game data."""
    legs = []
    
    # Take legs from first few games
    for game in games[:3]:
        for book in game.books:
            if book.bookmaker.lower() == "draftkings":  # Prefer DraftKings
                
                # Add a moneyline bet (h2h)
                if book.market == "h2h" and book.selections:
                    for selection in book.selections:
                        if selection.price_decimal >= 1.8:  # Good value
                            legs.append(ParlayLeg(
                                game_id=game.game_id,
                                market_type="h2h",
                                selection_name=selection.name,
                                bookmaker=book.bookmaker,
                                odds_decimal=selection.price_decimal
                            ))
                            break
                
                # Add a spread bet
                elif book.market == "spreads" and book.selections:
                    for selection in book.selections:
                        if selection.line and abs(selection.line) <= 6:  # Small spread
                            legs.append(ParlayLeg(
                                game_id=game.game_id,
                                market_type="spreads",
                                selection_name=selection.name,
                                bookmaker=book.bookmaker,
                                odds_decimal=selection.price_decimal,
                                line=selection.line
                            ))
                            break
                
                # Add a total bet
                elif book.market == "totals" and book.selections:
                    over_selection = next((s for s in book.selections if "over" in s.name.lower()), None)
                    if over_selection and over_selection.line:
                        legs.append(ParlayLeg(
                            game_id=game.game_id,
                            market_type="totals",
                            selection_name="Over",
                            bookmaker=book.bookmaker,
                            odds_decimal=over_selection.price_decimal,
                            line=over_selection.line
                        ))
                        break
                
                if len(legs) >= 3:  # Limit to 3 legs
                    break
        
        if len(legs) >= 3:
            break
    
    return legs[:3]  # Return first 3 legs


def create_sample_legs():
    """Create sample parlay legs for demonstration."""
    return [
        ParlayLeg(
            game_id="nba_lal_vs_bos",
            market_type="h2h",
            selection_name="Los Angeles Lakers",
            bookmaker="DraftKings",
            odds_decimal=2.10  # Lakers to win at +110
        ),
        ParlayLeg(
            game_id="nba_gsw_vs_mia",
            market_type="spreads",
            selection_name="Golden State Warriors",
            bookmaker="FanDuel", 
            odds_decimal=1.91,  # Warriors +3.5 at -110
            line=3.5
        ),
        ParlayLeg(
            game_id="nba_den_vs_phx",
            market_type="totals",
            selection_name="Over",
            bookmaker="BetMGM",
            odds_decimal=1.95,  # Over 220.5 at -105
            line=220.5
        )
    ]


def show_parlay_creation_methods():
    """Show different ways parlays can be created in this system."""
    print("\n" + "=" * 60)
    print("🎯 DIFFERENT WAYS TO CREATE PARLAYS IN THIS SYSTEM")
    print("=" * 60)
    
    methods = [
        {
            "name": "Manual Creation",
            "description": "Create ParlayLeg objects manually with specific selections",
            "use_case": "When you have specific bets in mind",
            "file": "This example (simple_parlay_creation_example.py)"
        },
        {
            "name": "ParlayStrategistAgent",
            "description": "AI agent analyzes games and suggests valuable legs with reasoning",
            "use_case": "AI-powered parlay recommendations with injury analysis",
            "file": "tools/parlay_strategist_agent.py"
        },
        {
            "name": "Enhanced ParlayStrategistAgent",
            "description": "Advanced AI with few-shot learning and confidence scoring",
            "use_case": "Most sophisticated parlay generation with ML confidence",
            "file": "tools/enhanced_parlay_strategist_agent.py"
        },
        {
            "name": "Market Discrepancy Detection",
            "description": "Find arbitrage and value opportunities across sportsbooks",
            "use_case": "Finding market inefficiencies for profitable bets",
            "file": "tools/market_discrepancy_detector.py"
        },
        {
            "name": "Correlation-Aware Building",
            "description": "Build parlays while avoiding highly correlated legs",
            "use_case": "Building diversified parlays with proper risk management",
            "file": "tools/correlation_model.py"
        }
    ]
    
    for i, method in enumerate(methods, 1):
        print(f"\n{i}. {method['name']}")
        print(f"   📄 {method['description']}")
        print(f"   🎯 Use case: {method['use_case']}")
        print(f"   📁 Implementation: {method['file']}")


def show_workflow_summary():
    """Show the complete parlay workflow."""
    print("\n" + "=" * 60)
    print("🔄 COMPLETE PARLAY CREATION WORKFLOW")
    print("=" * 60)
    
    steps = [
        "1. 📡 Fetch Current Odds - Get live NBA game odds from multiple sportsbooks",
        "2. 🧠 Generate Ideas - Use AI agents or manual selection to identify valuable bets",
        "3. 🔍 Validate Markets - Ensure all selected bets are still available",
        "4. ⚖️ Check Rules - Verify parlay follows sportsbook rules (same game, correlation)",
        "5. 📊 Analyze Correlation - Detect and warn about highly correlated legs",
        "6. 💰 Calculate Odds - Compute total parlay odds and potential payout",
        "7. 📝 Log Bet - Record the parlay in database for tracking",
        "8. 🚨 Final Verification - Last-minute check before placing bet (JIRA-024)",
        "9. 📤 Place Bet - Send to sportsbook or alert user",
        "10. 📈 Track Results - Monitor outcomes and calculate performance"
    ]
    
    for step in steps:
        print(f"   {step}")


def main():
    """Main function demonstrating parlay creation."""
    
    # Show the simple example
    parlay = create_simple_parlay_example()
    
    # Show different creation methods  
    show_parlay_creation_methods()
    
    # Show complete workflow
    show_workflow_summary()
    
    print("\n" + "=" * 60)
    print("🎉 SUMMARY")
    print("=" * 60)
    print("This NBA parlay project provides multiple sophisticated ways to create parlays:")
    print("• 🤖 AI-powered recommendations with reasoning")
    print("• 🔍 Real-time market validation")
    print("• ⚖️ Correlation analysis and risk management")
    print("• 📊 Performance tracking and analysis")
    print("• 🚨 Final verification before bet placement")
    print("• 💰 Arbitrage and value opportunity detection")
    
    if parlay:
        print(f"\n🏆 Successfully created example parlay with {len(parlay.valid_legs)} legs!")
    else:
        print(f"\n⚠️ Example used sample data (no live games available)")


if __name__ == "__main__":
    main()

