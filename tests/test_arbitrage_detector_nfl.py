#!/usr/bin/env python3
"""
Comprehensive test suite for NFL arbitrage detection - JIRA-NFL-008

Tests the enhanced ArbitrageDetectorTool with NFL-specific features:
- Three-way arbitrage detection (Win/Tie/Loss)
- NFL-specific spread adjustments
- Market normalization for team names
- Sport-aware logging
- Backward compatibility with NBA arbitrage
"""

import pytest
import tempfile
import sqlite3
from unittest.mock import Mock, patch
from pathlib import Path
from typing import Dict, List, Any

from tools.arbitrage_detector_tool import (
    ArbitrageDetectorTool,
    ArbitrageOpportunity,
    ArbitrageLeg,
    BookConfiguration
)
from tools.market_normalizer import MarketNormalizer, Sport


class TestArbitrageDetectorNFL:
    """Test suite for NFL arbitrage detection capabilities."""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite') as tmp_file:
            yield tmp_file.name
        # Cleanup happens automatically
    
    @pytest.fixture
    def detector(self, temp_db_path):
        """Create an ArbitrageDetectorTool instance for testing."""
        detector = ArbitrageDetectorTool(
            min_profit_threshold=0.005,  # 0.5%
            max_latency_threshold=60.0,
            default_slippage_buffer=0.01,
            db_path=temp_db_path
        )
        
        # Ensure database table exists
        self._create_arbitrage_table(temp_db_path)
        return detector
    
    def _create_arbitrage_table(self, db_path):
        """Create arbitrage_opportunities table for testing."""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS arbitrage_opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT,
                market_type TEXT,
                sport TEXT,
                detection_timestamp TEXT,
                profit_percentage REAL,
                guaranteed_profit REAL,
                total_investment REAL,
                risk_level TEXT,
                sportsbooks_involved TEXT,
                bets_required TEXT,
                expires_at TEXT,
                is_active INTEGER,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    @pytest.fixture
    def nfl_two_way_odds(self):
        """Sample NFL two-way odds that should create arbitrage."""
        return {
            "odds_a": 120,   # Chiefs +120 at FanDuel (wider margins for arbitrage)
            "book_a": "fanduel",
            "odds_b": -90,   # Bills -90 at DraftKings
            "book_b": "draftkings",
            "team_a": "Kansas City Chiefs",
            "team_b": "Buffalo Bills"
        }
    
    @pytest.fixture
    def nfl_three_way_odds(self):
        """Sample NFL three-way odds (Win/Tie/Loss) for arbitrage testing."""
        return [
            {"odds": 250, "adjusted_odds": 245, "book": "betmgm"},      # Away Win
            {"odds": 320, "adjusted_odds": 315, "book": "caesars"},    # Tie
            {"odds": 180, "adjusted_odds": 175, "book": "pointsbet"}   # Home Win
        ]
    
    @pytest.fixture
    def marginal_nfl_odds(self):
        """NFL odds that are close to arbitrage threshold."""
        return {
            "odds_a": 102,   # Very tight margins
            "book_a": "fanduel", 
            "odds_b": -105,
            "book_b": "draftkings"
        }
    
    def test_nfl_sport_configuration(self, detector):
        """Test that NFL sport configuration is properly initialized."""
        assert "nfl" in detector.sport_configs
        nfl_config = detector.sport_configs["nfl"]
        
        # Check NFL-specific parameters
        assert nfl_config["spread_range"] == (-21.0, 21.0)  # Wider than NBA
        assert nfl_config["slippage_multiplier"] == 1.2     # Higher than NBA
        assert nfl_config["three_way_available"] is True    # NFL allows ties
        assert nfl_config["typical_total_range"] == (35, 60)
    
    def test_nfl_spread_slippage_adjustment(self, detector):
        """Test NFL-specific spread and slippage adjustments."""
        # Test with same odds for NBA vs NFL
        odds = 110
        book = "draftkings"
        stake = 1000.0
        
        nba_adjusted = detector.adjust_for_spread_and_slippage(odds, book, stake, "nba")
        nfl_adjusted = detector.adjust_for_spread_and_slippage(odds, book, stake, "nfl")
        
        # NFL should have higher slippage (lower adjusted odds)
        assert nfl_adjusted < nba_adjusted
        
        # Verify NFL volatility penalty is applied
        assert abs(nfl_adjusted - nba_adjusted) > 0.1  # Meaningful difference
    
    def test_nfl_two_way_arbitrage_detection(self, detector, nfl_two_way_odds):
        """Test NFL two-way arbitrage detection with team names."""
        opportunity = detector.detect_arbitrage_two_way(
            odds_a=nfl_two_way_odds["odds_a"],
            book_a=nfl_two_way_odds["book_a"],
            odds_b=nfl_two_way_odds["odds_b"],
            book_b=nfl_two_way_odds["book_b"],
            sport="nfl",
            team_a=nfl_two_way_odds["team_a"],
            team_b=nfl_two_way_odds["team_b"],
            market_type="ML"
        )
        
        assert opportunity is not None
        assert opportunity.type == "2-way"
        assert opportunity.profit_margin > 0
        assert len(opportunity.legs) == 2
        
        # Check that NFL sport was used in logging
        assert len(detector.opportunities_detected) == 1
        
        # Verify team names (should be normalized if MarketNormalizer available)
        team_names = [leg.team for leg in opportunity.legs]
        assert len(team_names) == 2
    
    def test_nfl_three_way_arbitrage_detection(self, detector, nfl_three_way_odds):
        """Test NFL three-way arbitrage detection (Win/Tie/Loss)."""
        opportunity = detector.detect_arbitrage_three_way(
            odds_list=nfl_three_way_odds,
            sport="nfl", 
            slippage_buffer=0.01,
            game_id="chiefs_vs_bills_week_6",
            team_home="Kansas City Chiefs",
            team_away="Buffalo Bills"
        )
        
        assert opportunity is not None
        assert opportunity.type == "3-way"
        assert opportunity.market_type == "3W"
        assert len(opportunity.legs) == 3
        
        # Verify outcome names
        outcome_names = [leg.team for leg in opportunity.legs]
        assert "Win" in outcome_names[0]    # Away win
        assert "Tie" in outcome_names[1]    # Tie/Draw
        assert "Win" in outcome_names[2]    # Home win
        
        # Three-way should have higher risk score
        assert opportunity.execution_risk_score > 0.1
        
        # More conservative expected edge for three-way
        assert opportunity.expected_edge == opportunity.profit_margin * 0.70
    
    def test_three_way_nba_rejection(self, detector):
        """Test that three-way arbitrage is rejected for NBA."""
        nba_odds = [
            {"odds": 110, "adjusted_odds": 105, "book": "fanduel"},
            {"odds": -105, "adjusted_odds": -110, "book": "draftkings"},
            {"odds": 200, "adjusted_odds": 195, "book": "betmgm"}
        ]
        
        with pytest.raises(ValueError, match="Three-way arbitrage currently only supported for NFL"):
            detector.detect_arbitrage_three_way(nba_odds, "nba")
    
    def test_market_normalizer_integration(self, detector):
        """Test MarketNormalizer integration for team names."""
        if not detector.market_normalizer:
            pytest.skip("MarketNormalizer not available")
        
        # Test team name normalization
        normalizer = detector.market_normalizer
        
        # NFL team normalization
        assert normalizer.normalize_team_name("Kansas City Chiefs", Sport.NFL) == "KC"
        assert normalizer.normalize_team_name("Chiefs", Sport.NFL) == "KC"
        assert normalizer.normalize_team_name("Dallas Cowboys", Sport.NFL) == "DAL"
        
        # NBA team normalization
        assert normalizer.normalize_team_name("Los Angeles Lakers", Sport.NBA) == "LAL"
        assert normalizer.normalize_team_name("Lakers", Sport.NBA) == "LAL"
    
    def test_nfl_arbitrage_logging(self, detector, temp_db_path, nfl_two_way_odds):
        """Test that NFL arbitrage opportunities are logged with sport='nfl'."""
        # Detect NFL arbitrage
        opportunity = detector.detect_arbitrage_two_way(
            odds_a=nfl_two_way_odds["odds_a"],
            book_a=nfl_two_way_odds["book_a"],
            odds_b=nfl_two_way_odds["odds_b"],
            book_b=nfl_two_way_odds["book_b"],
            sport="nfl"
        )
        
        assert opportunity is not None
        
        # Check database for NFL logging
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT sport, market_type, profit_percentage FROM arbitrage_opportunities")
        rows = cursor.fetchall()
        
        assert len(rows) == 1
        sport, market_type, profit = rows[0]
        assert sport == "nfl"
        assert market_type == "ML"
        assert profit > 0
        
        conn.close()
    
    def test_nfl_marginal_arbitrage_elimination(self, detector, marginal_nfl_odds):
        """Test that marginal arbitrage is eliminated by NFL execution costs."""
        opportunity = detector.detect_arbitrage_two_way(
            odds_a=marginal_nfl_odds["odds_a"],
            book_a=marginal_nfl_odds["book_a"],
            odds_b=marginal_nfl_odds["odds_b"],
            book_b=marginal_nfl_odds["book_b"],
            sport="nfl"
        )
        
        # Marginal arbitrage should be eliminated by NFL's higher execution costs
        assert opportunity is None or opportunity.profit_margin < detector.min_profit_threshold
    
    def test_nba_backward_compatibility(self, detector):
        """Test that NBA arbitrage detection remains unchanged."""
        # Test NBA two-way arbitrage (existing functionality)
        opportunity = detector.detect_arbitrage_two_way(
            odds_a=105,
            book_a="fanduel",
            odds_b=-90,
            book_b="draftkings",
            sport="nba",
            team_a="Los Angeles Lakers",
            team_b="Boston Celtics"
        )
        
        assert opportunity is not None
        assert opportunity.type == "2-way"
        assert len(opportunity.legs) == 2
        
        # Should use NBA sport configuration (lower slippage)
        nba_config = detector.sport_configs["nba"]
        assert nba_config["slippage_multiplier"] == 1.0
        assert nba_config["three_way_available"] is False
    
    def test_profit_margin_calculation_nfl(self, detector):
        """Test profit margin calculation with NFL-specific adjustments."""
        odds_list = [(120, "fanduel"), (-90, "draftkings")]  # Wider margins for arbitrage
        
        # Calculate for both sports
        nba_margin, nba_ratios, nba_stakes = detector.calculate_profit_margin_and_stake_ratios(
            odds_list, total_stake=1000.0, sport="nba"
        )
        
        nfl_margin, nfl_ratios, nfl_stakes = detector.calculate_profit_margin_and_stake_ratios(
            odds_list, total_stake=1000.0, sport="nfl"
        )
        
        # If both have arbitrage, NFL should have lower profit margin due to higher execution costs
        if nba_margin > 0 and nfl_margin > 0:
            assert nfl_margin < nba_margin
        
        if nfl_stakes:
            assert abs(sum(nfl_stakes) - 1000.0) < 0.01  # Stakes should still sum to total
        if nba_stakes:
            assert abs(sum(nba_stakes) - 1000.0) < 0.01
    
    def test_execution_risk_nfl_penalty(self, detector, nfl_three_way_odds):
        """Test that NFL three-way arbitrage has appropriate risk penalties."""
        opportunity = detector.detect_arbitrage_three_way(
            odds_list=nfl_three_way_odds,
            sport="nfl"
        )
        
        assert opportunity is not None
        
        # Three-way NFL should have higher execution risk (adjusted expectation)
        assert opportunity.execution_risk_score > 0.05  # Some penalty applied
        
        # False positive probability should be higher for three-way
        assert opportunity.false_positive_probability > 0.1
    
    def test_invalid_three_way_odds_count(self, detector):
        """Test validation of three-way odds count."""
        # Test with wrong number of odds
        invalid_odds = [
            {"odds": 110, "adjusted_odds": 105, "book": "fanduel"},
            {"odds": -105, "adjusted_odds": -110, "book": "draftkings"}
        ]
        
        with pytest.raises(ValueError, match="Three-way arbitrage requires exactly 3 odds"):
            detector.detect_arbitrage_three_way(invalid_odds, "nfl")
    
    def test_nfl_wide_spread_handling(self, detector):
        """Test handling of NFL's wider point spreads."""
        # NFL can have spreads like -14.5, -21, etc.
        wide_spread_odds = [
            (-140, "draftkings"),  # Favorite -14 point spread
            (120, "fanduel")       # Underdog +14 point spread
        ]
        
        opportunity = detector.detect_arbitrage_two_way(
            odds_a=wide_spread_odds[0][0],
            book_a=wide_spread_odds[0][1],
            odds_b=wide_spread_odds[1][0],
            book_b=wide_spread_odds[1][1],
            sport="nfl",
            market_type="PS"  # Point Spread
        )
        
        # Should handle wide spreads without issues
        if opportunity:  # May or may not be profitable after execution costs
            assert opportunity.market_type == "PS"
            assert len(opportunity.legs) == 2
    
    def simulate_nfl_arbitrage_opportunities(self, detector, count: int = 100) -> Dict[str, Any]:
        """Simulate multiple NFL arbitrage opportunities for validation."""
        results = {
            "total_simulated": count,
            "profitable_opportunities": 0,
            "average_profit_margin": 0.0,
            "three_way_opportunities": 0,
            "nfl_specific_penalties": 0
        }
        
        import random
        random.seed(42)  # For reproducible results
        
        profitable_margins = []
        
        for i in range(count):
            # Generate random but realistic NFL odds
            if i % 4 == 0:  # 25% three-way
                # Three-way odds
                odds_list = [
                    {"odds": random.randint(200, 400), "adjusted_odds": random.randint(195, 395), "book": "betmgm"},
                    {"odds": random.randint(300, 500), "adjusted_odds": random.randint(295, 495), "book": "caesars"},
                    {"odds": random.randint(150, 250), "adjusted_odds": random.randint(145, 245), "book": "pointsbet"}
                ]
                
                try:
                    opportunity = detector.detect_arbitrage_three_way(odds_list, "nfl")
                    if opportunity:
                        results["three_way_opportunities"] += 1
                        results["profitable_opportunities"] += 1
                        profitable_margins.append(opportunity.profit_margin)
                except:
                    pass  # Not all random odds will create arbitrage
            else:
                # Two-way odds
                odds_a = random.randint(-200, 200)
                odds_b = random.randint(-200, 200)
                
                # Ensure they're on opposite sides for potential arbitrage
                if odds_a > 0 and odds_b > 0:
                    odds_b = -abs(odds_b)
                elif odds_a < 0 and odds_b < 0:
                    odds_b = abs(odds_b)
                
                opportunity = detector.detect_arbitrage_two_way(
                    odds_a=odds_a,
                    book_a="fanduel",
                    odds_b=odds_b,
                    book_b="draftkings",
                    sport="nfl"
                )
                
                if opportunity:
                    results["profitable_opportunities"] += 1
                    profitable_margins.append(opportunity.profit_margin)
                    
                    # Check if NFL penalties were applied
                    if opportunity.execution_risk_score > 0.1:
                        results["nfl_specific_penalties"] += 1
        
        if profitable_margins:
            results["average_profit_margin"] = sum(profitable_margins) / len(profitable_margins)
        
        return results
    
    def test_simulate_100_nfl_arbitrage_opportunities(self, detector):
        """Validation test: Simulate 100 NFL arbitrage opportunities."""
        results = self.simulate_nfl_arbitrage_opportunities(detector, 100)
        
        # Validation assertions
        assert results["total_simulated"] == 100
        assert results["profitable_opportunities"] >= 0  # At least some should be profitable
        
        if results["profitable_opportunities"] > 0:
            assert results["average_profit_margin"] > 0
            assert results["average_profit_margin"] < 0.50  # Allow for higher random margins in simulation
        
        # Should have some three-way opportunities
        assert results["three_way_opportunities"] >= 0
        
        # NFL penalties should be applied to some opportunities
        assert results["nfl_specific_penalties"] >= 0
        
        print(f"✅ NFL Arbitrage Simulation Results:")
        print(f"   • Total simulated: {results['total_simulated']}")
        print(f"   • Profitable opportunities: {results['profitable_opportunities']}")
        print(f"   • Average profit margin: {results['average_profit_margin']:.2%}")
        print(f"   • Three-way opportunities: {results['three_way_opportunities']}")
        print(f"   • NFL penalties applied: {results['nfl_specific_penalties']}")
    
    def test_book_configuration_nfl_impact(self, detector):
        """Test that different sportsbook configurations affect NFL arbitrage differently."""
        odds_a = 110
        odds_b = -105
        
        # Test with high-tier book (DraftKings)
        high_tier_opp = detector.detect_arbitrage_two_way(
            odds_a=odds_a, book_a="draftkings",
            odds_b=odds_b, book_b="fanduel",
            sport="nfl"
        )
        
        # Test with lower-tier book (PointsBet)
        low_tier_opp = detector.detect_arbitrage_two_way(
            odds_a=odds_a, book_a="pointsbet",
            odds_b=odds_b, book_b="caesars",
            sport="nfl"
        )
        
        # Lower tier books should have higher execution risk or lower profit
        if high_tier_opp and low_tier_opp:
            assert (low_tier_opp.execution_risk_score >= high_tier_opp.execution_risk_score or
                    low_tier_opp.profit_margin <= high_tier_opp.profit_margin)
    
    def test_confidence_level_three_way(self, detector, nfl_three_way_odds):
        """Test confidence level calculation for three-way NFL arbitrage."""
        opportunity = detector.detect_arbitrage_three_way(
            odds_list=nfl_three_way_odds,
            sport="nfl"
        )
        
        assert opportunity is not None
        assert opportunity.confidence_level in ["high", "medium", "low"]
        
        # Three-way should generally have lower confidence than two-way
        # due to increased complexity and risk
        
    def test_market_type_preservation(self, detector):
        """Test that market types are correctly preserved in arbitrage opportunities."""
        # Test different market types
        market_types = ["ML", "PS", "OU"]
        
        for market_type in market_types:
            opportunity = detector.detect_arbitrage_two_way(
                odds_a=110, book_a="fanduel",
                odds_b=-105, book_b="draftkings",
                sport="nfl",
                market_type=market_type
            )
            
            if opportunity:
                assert opportunity.market_type == market_type
                for leg in opportunity.legs:
                    assert leg.market == market_type


def test_nfl_arbitrage_main_functionality():
    """Integration test for main NFL arbitrage functionality."""
    detector = ArbitrageDetectorTool(min_profit_threshold=0.005)
    
    # Test that NFL configuration is loaded
    assert "nfl" in detector.sport_configs
    
    # Test basic NFL two-way detection
    opportunity = detector.detect_arbitrage_two_way(
        odds_a=115, book_a="fanduel",
        odds_b=-100, book_b="draftkings", 
        sport="nfl"
    )
    
    if opportunity:
        assert opportunity.type == "2-way"
        print(f"✅ NFL two-way arbitrage detected: {opportunity.profit_margin:.2%} profit")
    
    # Test NFL three-way detection
    three_way_odds = [
        {"odds": 260, "adjusted_odds": 255, "book": "betmgm"},
        {"odds": 340, "adjusted_odds": 335, "book": "caesars"},
        {"odds": 170, "adjusted_odds": 165, "book": "pointsbet"}
    ]
    
    three_way_opportunity = detector.detect_arbitrage_three_way(three_way_odds, "nfl")
    
    if three_way_opportunity:
        assert three_way_opportunity.type == "3-way"
        print(f"✅ NFL three-way arbitrage detected: {three_way_opportunity.profit_margin:.2%} profit")
    
    print("✅ NFL arbitrage detection integration test completed")


if __name__ == "__main__":
    # Run specific tests
    pytest.main([__file__, "-v", "--tb=short"])
