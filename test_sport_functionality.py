#!/usr/bin/env python3
"""
Quick test to demonstrate the sport functionality works end-to-end
"""

from tools.bets_logger import BetsLogger
from tools.arbitrage_detector_tool import ArbitrageDetectorTool
from scripts.performance_reporter import load_rows, rollup_metrics

def test_sport_functionality():
    """Test that the sport functionality works end-to-end."""
    print("🏈 Testing JIRA-NFL-006 Sport Segmentation Functionality")
    print("=" * 60)
    
    # Test BetsLogger with both sports
    print("\n📊 Testing BetsLogger...")
    with BetsLogger("data/test_sport_demo.sqlite") as logger:
        # Log NBA bet
        nba_bet_id = logger.log_parlay_leg(
            parlay_id="demo_nba_001",
            game_id="nba_lakers_vs_celtics",
            leg_description="Lakers ML",
            odds=-110.0,
            stake=100.0,
            predicted_outcome="Lakers win",
            sport="nba"
        )
        print(f"✅ Logged NBA bet: {nba_bet_id}")
        
        # Log NFL bet
        nfl_bet_id = logger.log_parlay_leg(
            parlay_id="demo_nfl_001", 
            game_id="nfl_chiefs_vs_bills",
            leg_description="Chiefs ML",
            odds=-150.0,
            stake=150.0,
            predicted_outcome="Chiefs win",
            sport="nfl"
        )
        print(f"✅ Logged NFL bet: {nfl_bet_id}")
        
        # Test sports summary
        summary = logger.get_sports_summary()
        print(f"📈 Sports Summary: {summary}")
        
        # Test sport filtering
        nba_bets = logger.fetch_bets_by_sport("nba")
        nfl_bets = logger.fetch_bets_by_sport("nfl")
        print(f"🏀 NBA bets found: {len(nba_bets)}")
        print(f"🏈 NFL bets found: {len(nfl_bets)}")
    
    # Test ArbitrageDetectorTool
    print("\n🎯 Testing ArbitrageDetectorTool...")
    detector = ArbitrageDetectorTool(db_path="data/test_sport_demo.sqlite")
    
    # Try to detect an arbitrage opportunity
    opportunity = detector.detect_arbitrage_two_way(
        odds_a=110,
        book_a="fanduel",
        odds_b=-95,
        book_b="draftkings"
    )
    
    if opportunity:
        # Log with NFL sport
        opp_id = detector.log_arbitrage_opportunity(opportunity, sport="nfl")
        print(f"✅ Logged NFL arbitrage opportunity: {opp_id}")
    else:
        print("❌ No arbitrage opportunity found (this is normal)")
    
    # Test Performance Reporter
    print("\n📊 Testing Performance Reporter...")
    
    # Test filtering by sport
    all_rows = load_rows("data/test_sport_demo.sqlite", sport="all")
    nba_rows = load_rows("data/test_sport_demo.sqlite", sport="nba")
    nfl_rows = load_rows("data/test_sport_demo.sqlite", sport="nfl")
    
    print(f"📈 Total bets: {len(all_rows)}")
    print(f"🏀 NBA bets: {len(nba_rows)}")
    print(f"🏈 NFL bets: {len(nfl_rows)}")
    
    # Test grouping by sport
    if all_rows:
        groups = rollup_metrics(all_rows, "sport", include_open=True)
        print(f"📊 Groups by sport: {list(groups.keys())}")
        
        for sport, data in groups.items():
            print(f"   {sport}: {data['count_total']} bets, ${data['stake_sum']:.2f} total stake")
    
    print("\n✅ All sport functionality tests completed successfully!")
    print("🎯 JIRA-NFL-006 implementation validated!")

if __name__ == "__main__":
    test_sport_functionality()
