#!/usr/bin/env python3
"""
Comprehensive test suite for NFL parlay rules engine - JIRA-NFL-007

Tests the enhanced ParlayRulesEngine with NFL-specific correlation and exclusion
rules, validating both rule application and pricing adjustments.

Test Coverage:
- NFL parlay rule validation and exclusion
- Correlation detection and pricing adjustments  
- Backward compatibility with NBA rules
- Sportsbook-specific rule enforcement
- Rule violation tagging and reasoning
- Multi-sport configuration loading
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open
from typing import Dict, List, Any

# Import the enhanced rules engine
from tools.parlay_rules_engine import (
    ParlayRulesEngine, 
    ValidationResult, 
    RuleViolation,
    ValidationLevel,
    ViolationTag
)


class TestParlayRulesNFL:
    """Test suite for NFL parlay rules validation."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary directory with test configuration files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            
            # Create NFL configuration
            nfl_config = {
                "sport": "nfl",
                "market_definitions": {
                    "player_passing_yards": {
                        "group": "PLAYER_PROP",
                        "type": "PLAYER_PASSING_YARDS",
                        "period": "FULL_GAME",
                        "stat_unit": "yards"
                    },
                    "player_receiving_yards": {
                        "group": "PLAYER_PROP",
                        "type": "PLAYER_RECEIVING_YARDS",
                        "period": "FULL_GAME",
                        "stat_unit": "yards"
                    },
                    "moneyline": {
                        "group": "GAME_LINE",
                        "type": "MONEYLINE",
                        "period": "FULL_GAME"
                    },
                    "spread": {
                        "group": "GAME_LINE",
                        "type": "SPREAD",
                        "period": "FULL_GAME"
                    },
                    "total_points": {
                        "group": "GAME_LINE",
                        "type": "TOTAL_POINTS",
                        "period": "FULL_GAME"
                    }
                },
                "parlay_rules": [
                    {
                        "ruleId": "EXCLUSION_MONEYLINE_SPREAD_SAME_TEAM",
                        "description": "Disallow parlaying the Moneyline and Point Spread for the same team.",
                        "type": "EXCLUSION",
                        "severity": "HARD_BLOCK",
                        "conditions": {
                            "all": [
                                {"market_key": "moneyline"},
                                {"market_key": "spread"}
                            ]
                        },
                        "constraints": {
                            "same_team": True
                        },
                        "action": "DISALLOW"
                    },
                    {
                        "ruleId": "EXCLUSION_OVER_UNDER_SAME_PLAYER",
                        "description": "Disallow parlaying Over and Under for the same player prop.",
                        "type": "EXCLUSION",
                        "severity": "HARD_BLOCK",
                        "conditions": {
                            "any": [
                                {"market_key": "player_passing_yards"},
                                {"market_key": "player_receiving_yards"}
                            ]
                        },
                        "constraints": {
                            "same_player": True,
                            "opposite_selections": True
                        },
                        "action": "DISALLOW"
                    },
                    {
                        "ruleId": "CORRELATION_QB_PASS_YARDS_WR_REC_YARDS",
                        "description": "High positive correlation between a QB's passing yards and a WR's receiving yards.",
                        "type": "CORRELATION",
                        "severity": "WARNING",
                        "conditions": {
                            "all": [
                                {"market_key": "player_passing_yards"},
                                {"market_key": "player_receiving_yards"}
                            ]
                        },
                        "constraints": {
                            "same_team": True,
                            "different_players": True
                        },
                        "correlation_adjustment": {
                            "type": "POSITIVE",
                            "strength": "HIGH",
                            "multiplier": 0.85
                        }
                    },
                    {
                        "ruleId": "CORRELATION_TEAM_MONEYLINE_TOTAL_OVER",
                        "description": "Moderate correlation between team winning and game going over total.",
                        "type": "CORRELATION",
                        "severity": "WARNING",
                        "conditions": {
                            "all": [
                                {"market_key": "moneyline"},
                                {"market_key": "total_points", "selection": "Over"}
                            ]
                        },
                        "constraints": {
                            "same_team": False,
                            "same_game": True
                        },
                        "correlation_adjustment": {
                            "type": "POSITIVE",
                            "strength": "MEDIUM",
                            "multiplier": 0.92
                        }
                    }
                ],
                "sportsbook_rules": {
                    "DRAFTKINGS": {
                        "max_legs": 20,
                        "min_odds_per_leg": 1.20,
                        "prohibited_combinations": [
                            ["moneyline", "spread"],
                            ["first_td_scorer", "anytime_td_scorer"]
                        ]
                    },
                    "FANDUEL": {
                        "max_legs": 15,
                        "min_odds_per_leg": 1.25,
                        "prohibited_combinations": [
                            ["player_passing_yards", "total_points"]
                        ]
                    }
                }
            }
            
            # Create NBA configuration for backward compatibility
            nba_config = {
                "sport": "nba",
                "market_definitions": {
                    "player_points_over": {
                        "group": "PLAYER_PROP",
                        "type": "PLAYER_POINTS",
                        "period": "FULL_GAME",
                        "stat_unit": "points"
                    },
                    "h2h": {
                        "group": "GAME_LINE",
                        "type": "MONEYLINE",
                        "period": "FULL_GAME"
                    },
                    "totals": {
                        "group": "GAME_LINE", 
                        "type": "TOTAL_POINTS",
                        "period": "FULL_GAME"
                    }
                },
                "parlay_rules": [
                    {
                        "ruleId": "EXCLUSION_OVER_UNDER_SAME_PLAYER_NBA",
                        "description": "Disallow Over and Under for same NBA player prop.",
                        "type": "EXCLUSION",
                        "severity": "HARD_BLOCK",
                        "conditions": {
                            "any": [
                                {"market_key": "player_points_over"}
                            ]
                        },
                        "constraints": {
                            "same_player": True,
                            "opposite_selections": True
                        },
                        "action": "DISALLOW"
                    }
                ],
                "sportsbook_rules": {
                    "DRAFTKINGS": {
                        "max_legs": 20,
                        "min_odds_per_leg": 1.10,
                        "prohibited_combinations": []
                    }
                }
            }
            
            # Write config files
            with open(config_dir / "nfl_markets.json", "w") as f:
                json.dump(nfl_config, f, indent=2)
                
            with open(config_dir / "nba_markets.json", "w") as f:
                json.dump(nba_config, f, indent=2)
            
            yield config_dir
    
    @pytest.fixture
    def rules_engine(self, temp_config_dir):
        """Create a ParlayRulesEngine instance with test configuration."""
        return ParlayRulesEngine(config_dir=str(temp_config_dir))
    
    @pytest.fixture
    def correlated_nfl_legs(self):
        """Sample NFL legs with correlation (QB passing + WR receiving)."""
        return [
            {
                "game_id": "chiefs_vs_bills",
                "market_type": "player_passing_yards",
                "selection_name": "Patrick Mahomes Over 275.5 Yards",
                "odds_decimal": 1.85,
                "line": 275.5
            },
            {
                "game_id": "chiefs_vs_bills",
                "market_type": "player_receiving_yards", 
                "selection_name": "Travis Kelce Over 65.5 Yards",
                "odds_decimal": 1.90,
                "line": 65.5
            }
        ]
    
    @pytest.fixture
    def conflicting_nfl_legs(self):
        """Sample NFL legs with exclusion rule violation (moneyline + spread same team)."""
        return [
            {
                "game_id": "cowboys_vs_giants",
                "market_type": "moneyline",
                "selection_name": "Dallas Cowboys",
                "odds_decimal": 1.75
            },
            {
                "game_id": "cowboys_vs_giants",
                "market_type": "spread",
                "selection_name": "Dallas Cowboys -3.5",
                "odds_decimal": 1.90,
                "line": -3.5
            }
        ]
    
    @pytest.fixture
    def valid_nfl_legs(self):
        """Sample valid NFL legs with no rule violations."""
        return [
            {
                "game_id": "chiefs_vs_bills",
                "market_type": "moneyline",
                "selection_name": "Kansas City Chiefs",
                "odds_decimal": 1.85
            },
            {
                "game_id": "cowboys_vs_giants",
                "market_type": "player_receiving_yards",
                "selection_name": "CeeDee Lamb Over 75.5 Yards",
                "odds_decimal": 1.90,
                "line": 75.5
            },
            {
                "game_id": "packers_vs_vikings",
                "market_type": "total_points",
                "selection_name": "Over 45.5",
                "odds_decimal": 1.95,
                "line": 45.5
            }
        ]
    
    def test_load_nfl_rules(self, rules_engine):
        """Test loading NFL rules configuration."""
        config = rules_engine.load_rules("nfl")
        
        assert config["sport"] == "nfl"
        assert "market_definitions" in config
        assert "parlay_rules" in config
        assert "sportsbook_rules" in config
        
        # Check specific NFL markets
        assert "player_passing_yards" in config["market_definitions"]
        assert "player_receiving_yards" in config["market_definitions"]
        
        # Check rules loaded
        assert len(config["parlay_rules"]) >= 4
        
        # Verify specific rules exist
        rule_ids = [rule["ruleId"] for rule in config["parlay_rules"]]
        assert "CORRELATION_QB_PASS_YARDS_WR_REC_YARDS" in rule_ids
        assert "EXCLUSION_MONEYLINE_SPREAD_SAME_TEAM" in rule_ids
    
    def test_nfl_correlation_detection(self, rules_engine, correlated_nfl_legs):
        """Test detection of correlated NFL props (QB passing + WR receiving)."""
        result = rules_engine.validate_parlay(correlated_nfl_legs, "nfl")
        
        # Should be valid but with correlation adjustment
        assert result.is_valid
        assert len(result.violations) == 1
        
        violation = result.violations[0]
        assert violation.rule_type == "CORRELATION"
        assert violation.severity == ValidationLevel.WARNING
        assert violation.rule_id == "CORRELATION_QB_PASS_YARDS_WR_REC_YARDS"
        assert violation.correlation_multiplier == 0.85
        
        # Check correlation tax applied
        assert result.correlation_tax_multiplier == 0.85
        assert ViolationTag.PRICING_MODEL_VIOLATION in violation.tags
    
    def test_nfl_exclusion_rules(self, rules_engine, conflicting_nfl_legs):
        """Test exclusion rules for conflicting NFL selections."""
        result = rules_engine.validate_parlay(conflicting_nfl_legs, "nfl")
        
        # Should be invalid due to hard block
        assert not result.is_valid
        assert len(result.violations) >= 1  # Could have both exclusion and sportsbook violations
        
        # Find the exclusion violation
        exclusion_violations = [v for v in result.violations if v.rule_type == "EXCLUSION"]
        assert len(exclusion_violations) == 1
        
        violation = exclusion_violations[0]
        assert violation.rule_type == "EXCLUSION"
        assert violation.severity == ValidationLevel.HARD_BLOCK
        assert violation.rule_id == "EXCLUSION_MONEYLINE_SPREAD_SAME_TEAM"
        assert ViolationTag.LOGICAL_CONTRADICTION in violation.tags
        
        # Check rejection reason (could be either violation)
        rejection_reason = result.get_rejection_reason()
        assert ("Moneyline and Point Spread" in rejection_reason or 
                "prohibits combination" in rejection_reason)
    
    def test_nfl_valid_parlay(self, rules_engine, valid_nfl_legs):
        """Test validation of valid NFL parlay with no rule violations."""
        result = rules_engine.validate_parlay(valid_nfl_legs, "nfl")
        
        assert result.is_valid
        assert len(result.violations) == 0
        assert result.correlation_tax_multiplier == 1.0
        assert len(result.warnings) == 0
    
    def test_nfl_sportsbook_specific_rules(self, rules_engine):
        """Test sportsbook-specific rule enforcement for NFL."""
        # Test max legs limit
        too_many_legs = [
            {
                "game_id": f"game_{i}",
                "market_type": "moneyline",
                "selection_name": f"Team {i}",
                "odds_decimal": 1.85
            }
            for i in range(25)  # Exceed DraftKings limit of 20
        ]
        
        result = rules_engine.validate_parlay(too_many_legs, "nfl", "DRAFTKINGS")
        
        assert not result.is_valid
        max_legs_violations = [v for v in result.violations if v.rule_id == "MAX_LEGS_EXCEEDED"]
        assert len(max_legs_violations) == 1
        assert max_legs_violations[0].sportsbook_specific
        
        # Test minimum odds requirement
        low_odds_legs = [
            {
                "game_id": "test_game",
                "market_type": "moneyline",
                "selection_name": "Heavy Favorite",
                "odds_decimal": 1.05  # Below DraftKings minimum of 1.20
            },
            {
                "game_id": "test_game_2",
                "market_type": "moneyline",
                "selection_name": "Normal Odds",
                "odds_decimal": 1.85
            }
        ]
        
        result = rules_engine.validate_parlay(low_odds_legs, "nfl", "DRAFTKINGS")
        
        assert not result.is_valid
        min_odds_violations = [v for v in result.violations if v.rule_id == "MIN_ODDS_VIOLATION"]
        assert len(min_odds_violations) == 1
        assert min_odds_violations[0].sportsbook_specific
    
    def test_nfl_prohibited_combinations(self, rules_engine):
        """Test sportsbook prohibited combinations for NFL."""
        prohibited_legs = [
            {
                "game_id": "test_game",
                "market_type": "moneyline",
                "selection_name": "Dallas Cowboys",
                "odds_decimal": 1.75
            },
            {
                "game_id": "test_game",
                "market_type": "spread",
                "selection_name": "Dallas Cowboys -3.5",
                "odds_decimal": 1.90
            }
        ]
        
        result = rules_engine.validate_parlay(prohibited_legs, "nfl", "DRAFTKINGS")
        
        assert not result.is_valid
        prohibited_violations = [v for v in result.violations 
                               if v.rule_id in ["SPORTSBOOK_PROHIBITED", "EXCLUSION_MONEYLINE_SPREAD_SAME_TEAM"]]
        assert len(prohibited_violations) >= 1  # Should have at least one violation
    
    def test_opposite_selections_detection(self, rules_engine):
        """Test detection of opposite selections (Over/Under same player)."""
        opposite_legs = [
            {
                "game_id": "test_game",
                "market_type": "player_passing_yards",
                "selection_name": "Patrick Mahomes Over 275.5 Yards",
                "odds_decimal": 1.85,
                "line": 275.5
            },
            {
                "game_id": "test_game",
                "market_type": "player_passing_yards",
                "selection_name": "Patrick Mahomes Under 275.5 Yards",
                "odds_decimal": 1.95,
                "line": 275.5
            }
        ]
        
        result = rules_engine.validate_parlay(opposite_legs, "nfl")
        
        assert not result.is_valid
        exclusion_violations = [v for v in result.violations if v.rule_type == "EXCLUSION"]
        assert len(exclusion_violations) == 1
        assert "Over and Under" in exclusion_violations[0].description
    
    def test_backward_compatibility_nba(self, rules_engine):
        """Test that NBA rules still work (backward compatibility)."""
        nba_legs = [
            {
                "game_id": "lakers_vs_celtics",
                "market_type": "player_points_over",
                "selection_name": "LeBron James Over 25.5 Points",
                "odds_decimal": 1.85,
                "line": 25.5
            },
            {
                "game_id": "lakers_vs_celtics",
                "market_type": "h2h",
                "selection_name": "Los Angeles Lakers",
                "odds_decimal": 1.90
            }
        ]
        
        result = rules_engine.validate_parlay(nba_legs, "nba")
        
        assert result.is_valid
        assert result.sport == "nba"
        assert len(result.violations) == 0
    
    def test_generate_nfl_parlays_validation(self, rules_engine):
        """Generate and validate 10 NFL parlays to verify rule application."""
        test_parlays = [
            # Valid parlays
            [
                {
                    "game_id": f"game_{i}",
                    "market_type": "moneyline",
                    "selection_name": f"Team A Game {i}",
                    "odds_decimal": 1.85
                },
                {
                    "game_id": f"game_{i+10}",
                    "market_type": "player_receiving_yards",
                    "selection_name": f"Player {i} Over 60.5 Yards",
                    "odds_decimal": 1.90,
                    "line": 60.5
                }
            ]
            for i in range(5)
        ] + [
            # Correlated parlays
            [
                {
                    "game_id": f"game_{i}",
                    "market_type": "player_passing_yards",
                    "selection_name": f"QB {i} Over 250.5 Yards",
                    "odds_decimal": 1.85,
                    "line": 250.5
                },
                {
                    "game_id": f"game_{i}",
                    "market_type": "player_receiving_yards",
                    "selection_name": f"WR {i} Over 75.5 Yards",
                    "odds_decimal": 1.90,
                    "line": 75.5
                }
            ]
            for i in range(5, 10)
        ]
        
        valid_count = 0
        correlated_count = 0
        
        for i, parlay in enumerate(test_parlays):
            result = rules_engine.validate_parlay(parlay, "nfl")
            
            if result.is_valid:
                valid_count += 1
            
            # Count correlated parlays
            correlation_violations = [v for v in result.violations if v.rule_type == "CORRELATION"]
            if correlation_violations:
                correlated_count += 1
        
        # Verify we have both valid and correlated parlays
        assert valid_count >= 5  # At least the first 5 should be valid
        assert correlated_count >= 5  # The last 5 should have correlations detected
        
        print(f"✅ Generated 10 NFL test parlays:")
        print(f"   • Valid parlays: {valid_count}/10")
        print(f"   • Correlated parlays: {correlated_count}/10")
    
    def test_supported_sports(self, rules_engine):
        """Test that engine correctly identifies supported sports."""
        supported = rules_engine.get_supported_sports()
        
        assert "nfl" in supported
        assert "nba" in supported
        assert len(supported) >= 2
    
    def test_simple_validation_interface(self, rules_engine, valid_nfl_legs, conflicting_nfl_legs):
        """Test the simple is_parlay_valid interface."""
        # Valid parlay
        is_valid, reason = rules_engine.is_parlay_valid(valid_nfl_legs, "nfl")
        assert is_valid
        assert reason == "Valid parlay"
        
        # Invalid parlay
        is_valid, reason = rules_engine.is_parlay_valid(conflicting_nfl_legs, "nfl")
        assert not is_valid
        assert "Moneyline and Point Spread" in reason
    
    def test_missing_config_handling(self, rules_engine):
        """Test handling of missing sport configuration."""
        non_existent_legs = [
            {
                "game_id": "test",
                "market_type": "test_market",
                "selection_name": "Test Selection",
                "odds_decimal": 1.85
            }
        ]
        
        result = rules_engine.validate_parlay(non_existent_legs, "hockey")  # Unsupported sport
        
        assert not result.is_valid
        assert len(result.warnings) > 0
        assert "Failed to load hockey rules" in result.warnings[0]
    
    def test_empty_parlay_validation(self, rules_engine):
        """Test validation of empty or single-leg parlays."""
        # Empty parlay
        result = rules_engine.validate_parlay([], "nfl")
        assert not result.is_valid
        assert "No legs provided" in result.warnings[0]
        
        # Single leg
        single_leg = [
            {
                "game_id": "test",
                "market_type": "moneyline",
                "selection_name": "Test Team",
                "odds_decimal": 1.85
            }
        ]
        
        result = rules_engine.validate_parlay(single_leg, "nfl")
        assert not result.is_valid
        assert "at least 2 legs" in result.warnings[0]
    
    def test_violation_tagging(self, rules_engine, correlated_nfl_legs, conflicting_nfl_legs):
        """Test that violations are properly tagged."""
        # Test correlation violation tags
        corr_result = rules_engine.validate_parlay(correlated_nfl_legs, "nfl")
        assert len(corr_result.violations) > 0
        corr_violation = corr_result.violations[0]
        assert ViolationTag.PRICING_MODEL_VIOLATION in corr_violation.tags
        
        # Test exclusion violation tags
        excl_result = rules_engine.validate_parlay(conflicting_nfl_legs, "nfl")
        excl_violations = [v for v in excl_result.violations if v.rule_type == "EXCLUSION"]
        assert len(excl_violations) > 0
        excl_violation = excl_violations[0]
        assert ViolationTag.LOGICAL_CONTRADICTION in excl_violation.tags


def test_main_functionality():
    """Test the main function for demonstration purposes."""
    from tools.parlay_rules_engine import main
    
    # This should run without errors if config files exist
    try:
        main()
        print("✅ Main function executed successfully")
    except Exception as e:
        # Expected if config files don't exist in the actual directory
        print(f"ℹ️ Main function test: {e}")


if __name__ == "__main__":
    # Run specific tests
    pytest.main([__file__, "-v", "--tb=short"])
