#!/usr/bin/env python3
"""
ParlayBuilder Integration Example - JIRA-021

This example demonstrates how to integrate the ParlayBuilder tool into a 
ParlayStrategistAgent workflow to ensure only available markets are selected.

The workflow follows the JIRA-021 requirements:
1. ParlayStrategistAgent generates potential valuable legs
2. ParlayBuilder validates legs against current market availability
3. Only validated legs are included in the final parlay
"""

import sys
import os
from typing import List, Dict, Any
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.parlay_builder import ParlayBuilder, ParlayLeg, ParlayValidation
from tools.odds_fetcher_tool import GameOdds


class MockParlayStrategistAgent:
    """
    Mock ParlayStrategistAgent that generates potential valuable legs.
    
    In a real implementation, this would analyze games, player stats, 
    injury reports, etc. to identify valuable betting opportunities.
    """
    
    def __init__(self):
        self.name = "MockParlayStrategistAgent"
    
    def generate_potential_legs(self, current_games: List[GameOdds]) -> List[ParlayLeg]:
        """
        Generate potential parlay legs based on current games.
        
        Args:
            current_games: List of current games with odds
            
        Returns:
            List of potential ParlayLeg objects
        """
        potential_legs = []
        
        if not current_games:
            print("⚠️ No current games available - generating sample legs for demonstration")
            return self._generate_sample_legs()
        
        print(f"🧠 Analyzing {len(current_games)} games for valuable opportunities...")
        
        # Strategy 1: Look for favorable moneyline bets
        for game in current_games[:3]:  # Limit to first 3 games for demo
            for book in game.books:
                if book.market == "h2h" and book.selections:
                    # Simple strategy: prefer underdogs with decent odds
                    for selection in book.selections:
                        if 1.8 <= selection.price_decimal <= 2.5:
                            potential_legs.append(ParlayLeg(
                                game_id=game.game_id,
                                market_type="h2h",
                                selection_name=selection.name,
                                bookmaker=book.bookmaker,
                                odds_decimal=selection.price_decimal
                            ))
                            print(f"  💡 Found value: {selection.name} @ {selection.price_decimal} ({book.bookmaker})")
                            break  # One per game
                    break  # One book per game
        
        # Strategy 2: Look for spread bets
        for game in current_games[:2]:  # Different games for spreads
            for book in game.books:
                if book.market == "spreads" and book.selections:
                    for selection in book.selections:
                        if selection.line and abs(selection.line) <= 7.5:  # Small spreads
                            potential_legs.append(ParlayLeg(
                                game_id=game.game_id,
                                market_type="spreads",
                                selection_name=selection.name,
                                bookmaker=book.bookmaker,
                                odds_decimal=selection.price_decimal,
                                line=selection.line
                            ))
                            print(f"  📊 Spread value: {selection.name} {selection.line:+.1f} @ {selection.price_decimal}")
                            break
                    break
        
        # Strategy 3: Look for totals
        for game in current_games[:1]:  # One total bet
            for book in game.books:
                if book.market == "totals" and book.selections:
                    over_selection = next((s for s in book.selections if s.name.lower() == "over"), None)
                    if over_selection and over_selection.line:
                        potential_legs.append(ParlayLeg(
                            game_id=game.game_id,
                            market_type="totals",
                            selection_name="Over",
                            bookmaker=book.bookmaker,
                            odds_decimal=over_selection.price_decimal,
                            line=over_selection.line
                        ))
                        print(f"  🎯 Total value: Over {over_selection.line} @ {over_selection.price_decimal}")
                        break
                    break
        
        print(f"🎲 Generated {len(potential_legs)} potential legs")
        return potential_legs
    
    def _generate_sample_legs(self) -> List[ParlayLeg]:
        """Generate sample legs when no real games are available."""
        return [
            ParlayLeg(
                game_id="demo_game_1",
                market_type="h2h",
                selection_name="Los Angeles Lakers",
                bookmaker="DraftKings",
                odds_decimal=2.10
            ),
            ParlayLeg(
                game_id="demo_game_2",
                market_type="spreads", 
                selection_name="Boston Celtics",
                bookmaker="FanDuel",
                odds_decimal=1.91,
                line=-4.5
            ),
            ParlayLeg(
                game_id="demo_game_3",
                market_type="totals",
                selection_name="Over",
                bookmaker="BetMGM",
                odds_decimal=1.95,
                line=218.5
            )
        ]


class ParlayWorkflow:
    """
    Complete parlay building workflow that integrates ParlayStrategistAgent 
    with ParlayBuilder for market validation.
    """
    
    def __init__(self):
        self.strategist = MockParlayStrategistAgent()
        self.builder = ParlayBuilder()
        self.workflow_id = f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def build_validated_parlay(self, min_legs: int = 2, max_legs: int = 5) -> Dict[str, Any]:
        """
        Complete workflow to build a validated parlay.
        
        Args:
            min_legs: Minimum legs required for viable parlay
            max_legs: Maximum legs to include in parlay
            
        Returns:
            Dictionary with workflow results
        """
        print(f"🚀 Starting Parlay Workflow: {self.workflow_id}")
        print("=" * 60)
        
        workflow_result = {
            "workflow_id": self.workflow_id,
            "timestamp": datetime.now().isoformat(),
            "success": False,
            "parlay": None,
            "steps": []
        }
        
        try:
            # Step 1: Get current market snapshot
            print("📡 Step 1: Fetching current market data...")
            current_games = self.builder._get_fresh_market_snapshot()
            
            step1_result = {
                "step": "market_snapshot",
                "success": True,
                "games_found": len(current_games),
                "total_markets": sum(len(game.books) for game in current_games)
            }
            workflow_result["steps"].append(step1_result)
            
            print(f"✅ Found {len(current_games)} games with {step1_result['total_markets']} markets")
            
            # Step 2: Generate potential legs
            print("\n🧠 Step 2: Generating potential valuable legs...")
            potential_legs = self.strategist.generate_potential_legs(current_games)
            
            step2_result = {
                "step": "leg_generation",
                "success": True,
                "potential_legs": len(potential_legs),
                "legs_summary": [
                    {
                        "selection": leg.selection_name,
                        "market": leg.market_type,
                        "odds": leg.odds_decimal,
                        "bookmaker": leg.bookmaker
                    }
                    for leg in potential_legs[:max_legs]  # Limit for display
                ]
            }
            workflow_result["steps"].append(step2_result)
            
            if not potential_legs:
                print("❌ No potential legs generated")
                return workflow_result
            
            # Step 3: Validate legs against current markets
            print(f"\n🔍 Step 3: Validating {len(potential_legs)} legs against current markets...")
            validation = self.builder.validate_parlay_legs(potential_legs[:max_legs])
            
            step3_result = {
                "step": "leg_validation",
                "success": True,
                "original_legs": len(validation.original_legs),
                "valid_legs": len(validation.valid_legs),
                "invalid_legs": len(validation.invalid_legs),
                "success_rate": validation.success_rate(),
                "total_odds": validation.total_odds
            }
            workflow_result["steps"].append(step3_result)
            
            print(f"✅ Validation complete: {len(validation.valid_legs)}/{len(validation.original_legs)} legs valid")
            print(f"📊 Success rate: {validation.success_rate():.1f}%")
            
            # Step 4: Check if parlay is viable
            print(f"\n🎯 Step 4: Checking parlay viability (min {min_legs} legs)...")
            
            if validation.is_viable(min_legs):
                print(f"✅ Parlay is viable with {len(validation.valid_legs)} legs")
                print(f"💰 Total odds: {validation.total_odds:.2f}")
                
                # Calculate potential payout for $100 bet
                potential_payout = 100 * validation.total_odds
                profit = potential_payout - 100
                
                print(f"💵 $100 bet would return ${potential_payout:.2f} (${profit:.2f} profit)")
                
                workflow_result["success"] = True
                workflow_result["parlay"] = {
                    "legs": [leg.to_dict() for leg in validation.valid_legs],
                    "total_odds": validation.total_odds,
                    "leg_count": len(validation.valid_legs),
                    "potential_payout_100": potential_payout,
                    "validation_timestamp": validation.validation_timestamp
                }
                
                # Show valid legs
                print(f"\n🏆 Final Parlay Legs:")
                for i, leg in enumerate(validation.valid_legs, 1):
                    line_str = f" {leg.line:+.1f}" if leg.line else ""
                    print(f"  {i}. {leg.selection_name}{line_str} @ {leg.odds_decimal} ({leg.bookmaker})")
                
            else:
                print(f"❌ Parlay not viable: only {len(validation.valid_legs)} valid legs (need {min_legs})")
                
                # Show what went wrong
                if validation.invalid_legs:
                    print(f"\n🚫 Invalid legs:")
                    for invalid in validation.invalid_legs:
                        print(f"  • {invalid.leg.selection_name}: {invalid.reason}")
                        if invalid.alternative_bookmakers:
                            print(f"    💡 Available at: {', '.join(invalid.alternative_bookmakers)}")
            
            step4_result = {
                "step": "viability_check",
                "success": True,
                "is_viable": validation.is_viable(min_legs),
                "final_leg_count": len(validation.valid_legs)
            }
            workflow_result["steps"].append(step4_result)
            
        except Exception as e:
            print(f"❌ Workflow failed: {e}")
            workflow_result["steps"].append({
                "step": "error",
                "success": False,
                "error": str(e)
            })
        
        return workflow_result
    
    def generate_workflow_report(self, result: Dict[str, Any]) -> str:
        """Generate a summary report of the workflow."""
        report = []
        report.append(f"📋 PARLAY WORKFLOW REPORT")
        report.append(f"=" * 50)
        report.append(f"Workflow ID: {result['workflow_id']}")
        report.append(f"Timestamp: {result['timestamp']}")
        report.append(f"Success: {'✅ YES' if result['success'] else '❌ NO'}")
        report.append("")
        
        # Steps summary
        report.append(f"📊 WORKFLOW STEPS:")
        for step in result['steps']:
            status = "✅" if step['success'] else "❌"
            report.append(f"  {status} {step['step'].replace('_', ' ').title()}")
        
        report.append("")
        
        # Parlay details if successful
        if result['success'] and result['parlay']:
            parlay = result['parlay']
            report.append(f"🏆 FINAL PARLAY:")
            report.append(f"  Legs: {parlay['leg_count']}")
            report.append(f"  Total Odds: {parlay['total_odds']:.2f}")
            report.append(f"  Potential Payout ($100): ${parlay['potential_payout_100']:.2f}")
            report.append("")
            
            report.append(f"📋 LEG DETAILS:")
            for i, leg in enumerate(parlay['legs'], 1):
                line_str = f" {leg['line']:+.1f}" if leg['line'] else ""
                report.append(f"  {i}. {leg['selection_name']}{line_str}")
                report.append(f"     Market: {leg['market_type']} | Odds: {leg['odds_decimal']} | Book: {leg['bookmaker']}")
        
        return "\n".join(report)


def main():
    """Main demonstration function."""
    print("🏀 ParlayBuilder Integration Example - JIRA-021")
    print("=" * 70)
    print("This example demonstrates the complete workflow:")
    print("1. ParlayStrategistAgent generates potential legs")
    print("2. ParlayBuilder validates against current markets")
    print("3. Only validated legs are included in final parlay")
    print()
    
    try:
        # Create workflow
        workflow = ParlayWorkflow()
        
        # Run the complete workflow
        result = workflow.build_validated_parlay(min_legs=2, max_legs=4)
        
        # Generate and display report
        print("\n" + "=" * 70)
        report = workflow.generate_workflow_report(result)
        print(report)
        
        # Summary
        print("\n" + "=" * 70)
        print("🎯 JIRA-021 IMPLEMENTATION SUMMARY:")
        print("✅ ParlayStrategistAgent generates potential valuable legs")
        print("✅ ParlayBuilder fetches fresh market snapshot")
        print("✅ Legs are validated against current availability")
        print("✅ Suspended/unavailable markets are filtered out")
        print("✅ Only validated legs included in final parlay")
        print("✅ Detailed validation results provided")
        print("✅ Works in both active season and off-season")
        
        if result['success']:
            print(f"\n🏆 SUCCESS: Built viable parlay with {result['parlay']['leg_count']} legs!")
        else:
            print(f"\n⚠️ No viable parlay built (expected during off-season)")
        
    except KeyboardInterrupt:
        print(f"\n⏹️ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
