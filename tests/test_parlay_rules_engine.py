#!/usr/bin/env python3
"""
Test suite for Parlay Rules Engine - JIRA-022

Comprehensive tests for the static rules engine that validates parlay compatibility
and enforces sportsbook-specific restrictions.
"""

import pytest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools.parlay_rules import ParlayRulesEngine, ValidationLevel, RuleViolation
from tools.parlay_builder import ParlayBuilder, ParlayLeg


class TestParlayRulesEngine:
    """Test cases for the ParlayRulesEngine class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = ParlayRulesEngine(correlation_threshold=0.75)
    
    def test_mutually_exclusive_same_player_over_under(self):
        """Test detection of mutually exclusive same player over/under."""
        legs = [
            {
                "game_id": "game_1",
                "market_type": "player_points_over",
                "selection_name": "LeBron James",
                "odds_decimal": 1.85
            },
            {
                "game_id": "game_1",
                "market_type": "player_points_under",
                "selection_name": "LeBron James",
                "odds_decimal": 1.95
            }
        ]
        
        result = self.engine.validate_parlay(legs)
        
        assert not result.is_valid
        assert result.has_hard_blocks()
        assert any(v.rule_type == "MUTUALLY_EXCLUSIVE" for v in result.violations)
    
    def test_mutually_exclusive_same_total_over_under(self):
        """Test detection of mutually exclusive game total over/under."""
        legs = [
            {
                "game_id": "game_1",
                "market_type": "totals",
                "selection_name": "Over",
                "odds_decimal": 1.90,
                "line": 220.5
            },
            {
                "game_id": "game_1",
                "market_type": "totals",
                "selection_name": "Under",
                "odds_decimal": 1.90,
                "line": 220.5
            }
        ]
        
        result = self.engine.validate_parlay(legs)
        
        assert not result.is_valid
        assert result.has_hard_blocks()
    
    def test_mutually_exclusive_opposite_team_outcomes(self):
        """Test detection of opposite team outcomes in same game."""
        legs = [
            {
                "game_id": "game_1",
                "market_type": "h2h",
                "selection_name": "Los Angeles Lakers",
                "odds_decimal": 1.85
            },
            {
                "game_id": "game_1",
                "market_type": "h2h",
                "selection_name": "Boston Celtics",
                "odds_decimal": 1.95
            }
        ]
        
        result = self.engine.validate_parlay(legs)
        
        assert not result.is_valid
        assert result.has_hard_blocks()
    
    def test_strongly_correlated_team_ml_spread(self):
        """Test detection of team ML + spread correlation."""
        legs = [
            {
                "game_id": "game_1",
                "market_type": "h2h",
                "selection_name": "Los Angeles Lakers",
                "odds_decimal": 1.85
            },
            {
                "game_id": "game_1",
                "market_type": "spreads",
                "selection_name": "Los Angeles Lakers",
                "odds_decimal": 1.90,
                "line": -5.5
            }
        ]
        
        result = self.engine.validate_parlay(legs)
        
        # Should be soft blocked (not hard invalid but flagged)
        soft_violations = [v for v in result.violations if v.severity == ValidationLevel.SOFT_BLOCK]
        assert len(soft_violations) > 0
        assert any("correlation" in v.description.lower() for v in soft_violations)
    
    def test_player_team_correlation(self):
        """Test detection of player performance + team outcome correlation."""
        legs = [
            {
                "game_id": "game_1",
                "market_type": "player_points_over",
                "selection_name": "LeBron James",
                "odds_decimal": 1.85,
                "line": 25.5
            },
            {
                "game_id": "game_1",
                "market_type": "h2h",
                "selection_name": "Los Angeles Lakers",
                "odds_decimal": 1.90
            }
        ]
        
        result = self.engine.validate_parlay(legs)
        
        # Should detect correlation but not hard block
        correlation_violations = [v for v in result.violations 
                                if v.severity in [ValidationLevel.SOFT_BLOCK, ValidationLevel.WARNING]]
        assert len(correlation_violations) > 0
    
    def test_soft_correlation_tax_calculation(self):
        """Test correlation tax calculation for soft correlations."""
        legs = [
            {
                "game_id": "game_1",
                "market_type": "player_points_over",
                "selection_name": "LeBron James",
                "odds_decimal": 1.85
            },
            {
                "game_id": "game_1",
                "market_type": "player_assists_over",
                "selection_name": "Anthony Davis",
                "odds_decimal": 1.90
            }
        ]
        
        result = self.engine.validate_parlay(legs)
        
        # Should apply correlation tax
        assert result.correlation_tax_multiplier > 1.0
    
    def test_sportsbook_specific_espn_bet_restrictions(self):
        """Test ESPN Bet specific restrictions."""
        legs = [
            {
                "game_id": "game_1",
                "market_type": "h2h",
                "selection_name": "Los Angeles Lakers",
                "odds_decimal": 1.85
            },
            {
                "game_id": "game_1",
                "market_type": "spreads",
                "selection_name": "Los Angeles Lakers",
                "odds_decimal": 1.90
            }
        ]
        
        # Should pass on DraftKings
        result_dk = self.engine.validate_parlay(legs, "DRAFTKINGS")
        
        # Should be restricted on ESPN Bet (if they prohibit ML + spread)
        result_espn = self.engine.validate_parlay(legs, "ESPN_BET")
        
        # ESPN Bet has stricter rules for ML + spread combinations
        espn_violations = [v for v in result_espn.violations if v.sportsbook_specific]
        # Note: Based on our rules, ESPN_BET prohibits this combination
        assert len(espn_violations) > 0 or not result_espn.is_valid
    
    def test_max_legs_limit_enforcement(self):
        """Test enforcement of maximum legs limits."""
        # Create a parlay with too many legs
        legs = []
        for i in range(25):  # Exceeds most sportsbook limits
            legs.append({
                "game_id": f"game_{i}",
                "market_type": "h2h",
                "selection_name": f"Team_{i}",
                "odds_decimal": 1.90
            })
        
        result = self.engine.validate_parlay(legs, "ESPN_BET")  # Max 20 legs
        
        # Should violate max legs limit
        max_legs_violations = [v for v in result.violations if v.rule_type == "MAX_LEGS_EXCEEDED"]
        assert len(max_legs_violations) > 0
        assert not result.is_valid
    
    def test_minimum_odds_enforcement(self):
        """Test enforcement of minimum odds per leg."""
        legs = [
            {
                "game_id": "game_1",
                "market_type": "h2h",
                "selection_name": "Heavy Favorite",
                "odds_decimal": 1.05  # Very low odds
            },
            {
                "game_id": "game_2",
                "market_type": "h2h",
                "selection_name": "Normal Pick",
                "odds_decimal": 1.85
            }
        ]
        
        result = self.engine.validate_parlay(legs, "POINTSBET")  # Min 1.25 odds
        
        # Should violate minimum odds requirement
        min_odds_violations = [v for v in result.violations if v.rule_type == "MIN_ODDS_VIOLATION"]
        assert len(min_odds_violations) > 0
        assert not result.is_valid
    
    def test_valid_parlay_passes(self):
        """Test that a valid parlay passes all checks."""
        legs = [
            {
                "game_id": "game_1",
                "market_type": "h2h",
                "selection_name": "Los Angeles Lakers",
                "odds_decimal": 1.85
            },
            {
                "game_id": "game_2",
                "market_type": "h2h",
                "selection_name": "Boston Celtics",
                "odds_decimal": 1.90
            },
            {
                "game_id": "game_3",
                "market_type": "totals",
                "selection_name": "Over",
                "odds_decimal": 1.95,
                "line": 215.5
            }
        ]
        
        result = self.engine.validate_parlay(legs, "DRAFTKINGS")
        
        # Should be valid with minimal violations
        assert result.is_valid
        hard_blocks = [v for v in result.violations if v.severity == ValidationLevel.HARD_BLOCK]
        assert len(hard_blocks) == 0
    
    def test_correlation_score_calculation(self):
        """Test correlation score calculation accuracy."""
        # Same player, same game (high correlation)
        legs_high = [
            {
                "game_id": "game_1",
                "market_type": "player_points_over",
                "selection_name": "LeBron James",
                "odds_decimal": 1.85
            },
            {
                "game_id": "game_1",
                "market_type": "player_assists_over",
                "selection_name": "LeBron James",
                "odds_decimal": 1.90
            }
        ]
        
        # Different games, different players (low correlation)
        legs_low = [
            {
                "game_id": "game_1",
                "market_type": "h2h",
                "selection_name": "Los Angeles Lakers",
                "odds_decimal": 1.85
            },
            {
                "game_id": "game_2",
                "market_type": "h2h",
                "selection_name": "Boston Celtics",
                "odds_decimal": 1.90
            }
        ]
        
        result_high = self.engine.validate_parlay(legs_high)
        result_low = self.engine.validate_parlay(legs_low)
        
        # High correlation case should have higher tax multiplier
        assert result_high.correlation_tax_multiplier > result_low.correlation_tax_multiplier
    
    def test_empty_parlay_validation(self):
        """Test validation of empty parlay."""
        result = self.engine.validate_parlay([])
        
        assert not result.is_valid
        assert len(result.warnings) > 0
    
    def test_single_leg_parlay_validation(self):
        """Test validation of single leg parlay."""
        legs = [
            {
                "game_id": "game_1",
                "market_type": "h2h",
                "selection_name": "Los Angeles Lakers",
                "odds_decimal": 1.85
            }
        ]
        
        result = self.engine.validate_parlay(legs)
        
        assert not result.is_valid
        assert len(result.warnings) > 0
    
    def test_unknown_sportsbook_handling(self):
        """Test handling of unknown sportsbook."""
        legs = [
            {
                "game_id": "game_1",
                "market_type": "h2h",
                "selection_name": "Los Angeles Lakers",
                "odds_decimal": 1.85
            },
            {
                "game_id": "game_2",
                "market_type": "h2h",
                "selection_name": "Boston Celtics",
                "odds_decimal": 1.90
            }
        ]
        
        result = self.engine.validate_parlay(legs, "UNKNOWN_BOOK")
        
        # Should still validate but with warnings
        assert len(result.warnings) > 0
        assert any("unknown" in w.lower() for w in result.warnings)
    
    def test_convenience_method_is_parlay_valid(self):
        """Test the convenience method is_parlay_valid."""
        valid_legs = [
            {
                "game_id": "game_1",
                "market_type": "h2h",
                "selection_name": "Los Angeles Lakers",
                "odds_decimal": 1.85
            },
            {
                "game_id": "game_2",
                "market_type": "h2h",
                "selection_name": "Boston Celtics",
                "odds_decimal": 1.90
            }
        ]
        
        invalid_legs = [
            {
                "game_id": "game_1",
                "market_type": "player_points_over",
                "selection_name": "LeBron James",
                "odds_decimal": 1.85
            },
            {
                "game_id": "game_1",
                "market_type": "player_points_under",
                "selection_name": "LeBron James",
                "odds_decimal": 1.95
            }
        ]
        
        valid, reason_valid = self.engine.is_parlay_valid(valid_legs)
        invalid, reason_invalid = self.engine.is_parlay_valid(invalid_legs)
        
        assert valid
        assert not invalid
        assert "valid" in reason_valid.lower()
        assert len(reason_invalid) > 0


class TestParlayBuilderIntegration:
    """Test integration of rules engine with ParlayBuilder."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.builder = ParlayBuilder(default_sportsbook="DRAFTKINGS")
    
    def test_parlay_builder_rules_integration(self):
        """Test that ParlayBuilder properly integrates rules validation."""
        # Create legs that violate rules
        legs = [
            ParlayLeg(
                game_id="game_1",
                market_type="player_points_over", 
                selection_name="LeBron James",
                bookmaker="DraftKings",
                odds_decimal=1.85,
                line=25.5
            ),
            ParlayLeg(
                game_id="game_1",
                market_type="player_points_under",
                selection_name="LeBron James", 
                bookmaker="DraftKings",
                odds_decimal=1.95,
                line=25.5
            )
        ]
        
        # Test quick validation
        valid, reason = self.builder.is_parlay_valid(legs)
        assert not valid
        assert len(reason) > 0
    
    def test_parlay_builder_sportsbook_handling(self):
        """Test sportsbook-specific validation in ParlayBuilder."""
        legs = [
            ParlayLeg(
                game_id="game_1",
                market_type="h2h",
                selection_name="Los Angeles Lakers",
                bookmaker="DraftKings",
                odds_decimal=1.85
            ),
            ParlayLeg(
                game_id="game_2",
                market_type="h2h",
                selection_name="Boston Celtics",
                bookmaker="DraftKings", 
                odds_decimal=1.90
            )
        ]
        
        # Should work for DraftKings
        valid_dk, _ = self.builder.is_parlay_valid(legs, "DRAFTKINGS")
        
        # Test with ESPN Bet
        valid_espn, _ = self.builder.is_parlay_valid(legs, "ESPN_BET")
        
        # Both should handle the legs (these are simple non-conflicting legs)
        # The specific validation depends on the sportsbook rules
        assert isinstance(valid_dk, bool)
        assert isinstance(valid_espn, bool)


def create_test_scenarios():
    """Create comprehensive test scenarios for manual testing."""
    scenarios = {
        "valid_multi_game": [
            {
                "game_id": "lal_vs_bos",
                "market_type": "h2h",
                "selection_name": "Los Angeles Lakers",
                "odds_decimal": 1.85
            },
            {
                "game_id": "gsw_vs_mia",
                "market_type": "h2h", 
                "selection_name": "Golden State Warriors",
                "odds_decimal": 1.90
            },
            {
                "game_id": "dal_vs_den",
                "market_type": "totals",
                "selection_name": "Over",
                "odds_decimal": 1.95,
                "line": 218.5
            }
        ],
        
        "mutually_exclusive": [
            {
                "game_id": "lal_vs_bos",
                "market_type": "player_points_over",
                "selection_name": "LeBron James",
                "odds_decimal": 1.85,
                "line": 25.5
            },
            {
                "game_id": "lal_vs_bos",
                "market_type": "player_points_under",
                "selection_name": "LeBron James",
                "odds_decimal": 1.95,
                "line": 25.5
            }
        ],
        
        "strongly_correlated": [
            {
                "game_id": "lal_vs_bos",
                "market_type": "h2h",
                "selection_name": "Los Angeles Lakers",
                "odds_decimal": 1.85
            },
            {
                "game_id": "lal_vs_bos",
                "market_type": "spreads",
                "selection_name": "Los Angeles Lakers",
                "odds_decimal": 1.90,
                "line": -5.5
            }
        ],
        
        "soft_correlation": [
            {
                "game_id": "lal_vs_bos",
                "market_type": "player_points_over",
                "selection_name": "LeBron James",
                "odds_decimal": 1.85,
                "line": 25.5
            },
            {
                "game_id": "lal_vs_bos",
                "market_type": "player_assists_over",
                "selection_name": "Anthony Davis",
                "odds_decimal": 1.90,
                "line": 8.5
            }
        ]
    }
    
    return scenarios


def run_manual_tests():
    """Run manual tests with different scenarios."""
    print("🧪 Running Manual Parlay Rules Tests")
    print("=" * 50)
    
    engine = ParlayRulesEngine()
    scenarios = create_test_scenarios()
    
    for scenario_name, legs in scenarios.items():
        print(f"\n📋 Testing Scenario: {scenario_name}")
        print("-" * 30)
        
        for i, leg in enumerate(legs, 1):
            print(f"  {i}. {leg['selection_name']} ({leg['market_type']}) @ {leg['odds_decimal']}")
        
        # Test with multiple sportsbooks
        sportsbooks = ["DRAFTKINGS", "ESPN_BET", "BET365"]
        
        for sportsbook in sportsbooks:
            result = engine.validate_parlay(legs, sportsbook)
            status = "✅ VALID" if result.is_valid else "❌ INVALID"
            print(f"  {sportsbook}: {status} ({len(result.violations)} violations, tax: {result.correlation_tax_multiplier:.2f}x)")
            
            if result.violations:
                for violation in result.violations[:2]:  # Show first 2
                    print(f"    • {violation.severity.value}: {violation.description}")


if __name__ == "__main__":
    # Run manual tests if script is executed directly
    run_manual_tests()
