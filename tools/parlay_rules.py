#!/usr/bin/env python3
"""
Parlay Rules Engine - JIRA-022

Static rule engine that enforces compatibility rules for parlay construction.
Prevents correlated props, mutually exclusive legs, and implements sportsbook-specific
restrictions based on known house rules.

Key Features:
- Universal hard blocks for mutually exclusive combinations
- Strongly correlated blocks for SGP considerations
- Soft correlation tracking for monitoring
- Sportsbook-specific exception handling
- Comprehensive validation with detailed reasoning
"""

from __future__ import annotations

import logging
from typing import Dict, List, Tuple, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum

# Set up logging
logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Validation severity levels for parlay rule violations."""
    HARD_BLOCK = "hard_block"          # Never allowed - reject immediately
    SOFT_BLOCK = "soft_block"          # Allowed with correlation tax/adjustment
    WARNING = "warning"                # Allowed but flagged for monitoring
    ALLOWED = "allowed"                # No restrictions


@dataclass
class RuleViolation:
    """Represents a rule violation detected during parlay validation."""
    rule_type: str
    severity: ValidationLevel
    description: str
    leg1_identifier: str
    leg2_identifier: str
    sportsbook_specific: bool = False
    correlation_score: Optional[float] = None
    suggested_action: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of parlay rule validation."""
    is_valid: bool
    violations: List[RuleViolation] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    correlation_tax_multiplier: float = 1.0
    
    def has_hard_blocks(self) -> bool:
        """Check if any hard block violations exist."""
        return any(v.severity == ValidationLevel.HARD_BLOCK for v in self.violations)
    
    def get_rejection_reason(self) -> Optional[str]:
        """Get the primary reason for rejection if parlay is invalid."""
        if not self.is_valid:
            hard_blocks = [v for v in self.violations if v.severity == ValidationLevel.HARD_BLOCK]
            if hard_blocks:
                return hard_blocks[0].description
        return None


class ParlayRulesEngine:
    """
    Static rule engine for parlay validation and compatibility checking.
    
    Implements sportsbook house rules and correlation detection to prevent
    invalid parlay combinations from being constructed.
    """
    
    # Universal Hard Blocks - Always Illegal Combinations
    MUTUALLY_EXCLUSIVE = [
        ("PLAYER_POINTS_OVER", "PLAYER_POINTS_UNDER"),
        ("PLAYER_REBOUNDS_OVER", "PLAYER_REBOUNDS_UNDER"),
        ("PLAYER_ASSISTS_OVER", "PLAYER_ASSISTS_UNDER"),
        ("TEAM_TOTAL_OVER", "TEAM_TOTAL_UNDER"),
        ("GAME_TOTAL_OVER", "GAME_TOTAL_UNDER"),
        ("FIRST_BASKET_SCORER", "FIRST_BASKET_SCORER"),  # Different players
        ("TEAM_WIN", "TEAM_LOSE"),
        ("TEAM_MONEYLINE_HOME", "TEAM_MONEYLINE_AWAY"),
        ("SPREAD_COVER", "SPREAD_NOT_COVER"),  # Same team, same spread
    ]
    
    # Strongly Correlated Blocks - Typically Disallowed Unless SGP Adjusts Odds
    RELATED_CONTINGENCIES = [
        ("TEAM_MONEYLINE", "TEAM_SPREAD_COVER"),        # Lakers ML + Lakers +6.5
        ("TEAM_MONEYLINE", "CORRECT_SCORE"),            # ML + specific score outcome
        ("TEAM_MONEYLINE", "TEAM_TOTAL_OVER"),          # Team win + team total over
        ("PLAYER_POINTS_OVER", "TEAM_TOTAL_OVER"),      # Player performance + team total
        ("PLAYER_ASSISTS_OVER", "TEAM_WIN"),            # Player stats + team outcome
        ("DOUBLE_DOUBLE", "PLAYER_POINTS_OVER"),        # Double-double + points over
        ("TRIPLE_DOUBLE", "PLAYER_ASSISTS_OVER"),       # Triple-double + specific stat
        ("FIRST_QUARTER_LEAD", "GAME_WINNER"),          # Early lead + final outcome
        ("HALFTIME_LEAD", "FINAL_MARGIN"),              # Half lead + final margin
    ]
    
    # Soft Correlations - Allowed But Heavily Taxed/Monitored
    SOFTLY_CORRELATED = [
        ("PLAYER_POINTS_OVER", "TEAM_MONEYLINE"),       # Star player + team win
        ("PG_ASSISTS_OVER", "SG_POINTS_OVER"),          # Different positions, same team
        ("TOTAL_POINTS_OVER", "MULTIPLE_PLAYERS_OVER"), # Game total + multiple player props
        ("TEAM_REBOUNDS_OVER", "OPPONENT_FG_UNDER"),    # Defensive correlation
        ("PACE_OVER", "TOTAL_POINTS_OVER"),             # Game pace + scoring total
        ("PLAYER_USAGE_HIGH", "PLAYER_POINTS_OVER"),    # Usage rate + scoring
    ]
    
    # Sportsbook-Specific Rules
    SPORTSBOOK_RULES = {
        "ESPN_BET": {
            "prohibited_combinations": [
                ("TEAM_MONEYLINE", "TEAM_SPREAD"),
                ("PLAYER_PROPS", "ALT_LINES"),  # No alt lines with props
            ],
            "sgp_settlement": "recalculate_on_void",
            "max_legs": 20,
            "min_odds_per_leg": 1.20,
        },
        "BET365": {
            "prohibited_combinations": [
                ("SAME_GAME_MULTIPLE_TOTALS", "PLAYER_PROPS"),
            ],
            "sgp_settlement": "void_entire_parlay_on_push", 
            "max_legs": 25,
            "min_odds_per_leg": 1.15,
        },
        "POINTSBET": {
            "prohibited_combinations": [
                ("QUARTER_PROPS", "HALFTIME_PROPS"),
            ],
            "avoid_push_prone_props": True,
            "max_legs": 15,
            "min_odds_per_leg": 1.25,
        },
        "DRAFTKINGS": {
            "prohibited_combinations": [],  # Most permissive
            "sgp_settlement": "grade_remaining_legs",
            "max_legs": 20,
            "min_odds_per_leg": 1.10,
        },
        "FANDUEL": {
            "prohibited_combinations": [
                ("PLAYER_ASSISTS", "PLAYER_TURNOVERS"),  # Same player
            ],
            "sgp_settlement": "recalculate_on_void",
            "max_legs": 25,
            "min_odds_per_leg": 1.12,
        },
    }
    
    def __init__(self, correlation_threshold: float = 0.75):
        """
        Initialize the parlay rules engine.
        
        Args:
            correlation_threshold: Threshold above which correlations trigger soft blocks
        """
        self.correlation_threshold = correlation_threshold
        logger.info(f"ParlayRulesEngine initialized with correlation threshold: {correlation_threshold}")
    
    def validate_parlay(self, legs: List[Dict[str, Any]], 
                       sportsbook: str = "DRAFTKINGS") -> ValidationResult:
        """
        Validate a complete parlay against all rule sets.
        
        Args:
            legs: List of parlay legs (each should have market_type, selection_name, etc.)
            sportsbook: Target sportsbook for sportsbook-specific rules
            
        Returns:
            ValidationResult with validation outcome and details
        """
        if not legs:
            return ValidationResult(is_valid=False, warnings=["No legs provided for validation"])
        
        if len(legs) < 2:
            return ValidationResult(is_valid=False, warnings=["Parlay must have at least 2 legs"])
        
        logger.info(f"Validating {len(legs)} leg parlay for {sportsbook}")
        
        violations = []
        warnings = []
        correlation_tax = 1.0
        
        # Check universal hard blocks
        violations.extend(self._check_mutually_exclusive(legs))
        
        # Check strongly correlated combinations
        violations.extend(self._check_related_contingencies(legs))
        
        # Check soft correlations
        soft_violations, tax_multiplier = self._check_soft_correlations(legs)
        violations.extend(soft_violations)
        correlation_tax *= tax_multiplier
        
        # Check sportsbook-specific rules
        sportsbook_violations, sportsbook_warnings = self._check_sportsbook_rules(legs, sportsbook)
        violations.extend(sportsbook_violations)
        warnings.extend(sportsbook_warnings)
        
        # Check leg count limits
        max_legs = self.SPORTSBOOK_RULES.get(sportsbook, {}).get("max_legs", 20)
        if len(legs) > max_legs:
            violations.append(RuleViolation(
                rule_type="MAX_LEGS_EXCEEDED",
                severity=ValidationLevel.HARD_BLOCK,
                description=f"Parlay exceeds {sportsbook} maximum of {max_legs} legs",
                leg1_identifier="ALL_LEGS",
                leg2_identifier="ALL_LEGS",
                sportsbook_specific=True,
                suggested_action=f"Reduce to {max_legs} legs or fewer"
            ))
        
        # Determine if parlay is valid (no hard blocks)
        has_hard_blocks = any(v.severity == ValidationLevel.HARD_BLOCK for v in violations)
        is_valid = not has_hard_blocks
        
        result = ValidationResult(
            is_valid=is_valid,
            violations=violations,
            warnings=warnings,
            correlation_tax_multiplier=correlation_tax
        )
        
        # Log summary
        if violations:
            logger.warning(f"Parlay validation found {len(violations)} violations "
                          f"(valid: {is_valid})")
        else:
            logger.info(f"Parlay validation passed - no rule violations detected")
        
        return result
    
    def _check_mutually_exclusive(self, legs: List[Dict[str, Any]]) -> List[RuleViolation]:
        """Check for mutually exclusive combinations."""
        violations = []
        
        for i, leg1 in enumerate(legs):
            for leg2 in legs[i+1:]:
                if self._are_mutually_exclusive(leg1, leg2):
                    violations.append(RuleViolation(
                        rule_type="MUTUALLY_EXCLUSIVE",
                        severity=ValidationLevel.HARD_BLOCK,
                        description=f"Mutually exclusive: {leg1.get('selection_name', 'Unknown')} "
                                   f"and {leg2.get('selection_name', 'Unknown')}",
                        leg1_identifier=self._get_leg_identifier(leg1),
                        leg2_identifier=self._get_leg_identifier(leg2),
                        suggested_action="Remove one of the conflicting legs"
                    ))
        
        return violations
    
    def _check_related_contingencies(self, legs: List[Dict[str, Any]]) -> List[RuleViolation]:
        """Check for strongly correlated combinations that should be blocked."""
        violations = []
        
        for i, leg1 in enumerate(legs):
            for leg2 in legs[i+1:]:
                if self._are_strongly_correlated(leg1, leg2):
                    violations.append(RuleViolation(
                        rule_type="STRONGLY_CORRELATED",
                        severity=ValidationLevel.SOFT_BLOCK,
                        description=f"Strong correlation: {leg1.get('selection_name', 'Unknown')} "
                                   f"and {leg2.get('selection_name', 'Unknown')}",
                        leg1_identifier=self._get_leg_identifier(leg1),
                        leg2_identifier=self._get_leg_identifier(leg2),
                        correlation_score=0.85,  # High correlation assumed
                        suggested_action="Consider SGP pricing or remove correlation"
                    ))
        
        return violations
    
    def _check_soft_correlations(self, legs: List[Dict[str, Any]]) -> Tuple[List[RuleViolation], float]:
        """Check for soft correlations that require monitoring/tax."""
        violations = []
        correlation_tax = 1.0
        
        for i, leg1 in enumerate(legs):
            for leg2 in legs[i+1:]:
                if self._are_softly_correlated(leg1, leg2):
                    correlation_score = self._calculate_correlation_score(leg1, leg2)
                    
                    # Apply correlation tax
                    tax_factor = 1.1 + (correlation_score * 0.2)  # 10-20% tax based on correlation
                    correlation_tax *= tax_factor
                    
                    violations.append(RuleViolation(
                        rule_type="SOFT_CORRELATION",
                        severity=ValidationLevel.WARNING,
                        description=f"Soft correlation detected: {leg1.get('selection_name', 'Unknown')} "
                                   f"and {leg2.get('selection_name', 'Unknown')} "
                                   f"(score: {correlation_score:.3f})",
                        leg1_identifier=self._get_leg_identifier(leg1),
                        leg2_identifier=self._get_leg_identifier(leg2),
                        correlation_score=correlation_score,
                        suggested_action=f"Monitor for pricing adjustment (tax: {tax_factor:.2f}x)"
                    ))
        
        return violations, correlation_tax
    
    def _check_sportsbook_rules(self, legs: List[Dict[str, Any]], 
                               sportsbook: str) -> Tuple[List[RuleViolation], List[str]]:
        """Check sportsbook-specific rules."""
        violations = []
        warnings = []
        
        if sportsbook not in self.SPORTSBOOK_RULES:
            warnings.append(f"Unknown sportsbook '{sportsbook}' - using default rules")
            return violations, warnings
        
        rules = self.SPORTSBOOK_RULES[sportsbook]
        
        # Check prohibited combinations
        prohibited = rules.get("prohibited_combinations", [])
        for i, leg1 in enumerate(legs):
            for leg2 in legs[i+1:]:
                if self._matches_prohibited_combination(leg1, leg2, prohibited):
                    violations.append(RuleViolation(
                        rule_type="SPORTSBOOK_PROHIBITED",
                        severity=ValidationLevel.HARD_BLOCK,
                        description=f"{sportsbook} prohibits combination: "
                                   f"{leg1.get('market_type', 'Unknown')} + "
                                   f"{leg2.get('market_type', 'Unknown')}",
                        leg1_identifier=self._get_leg_identifier(leg1),
                        leg2_identifier=self._get_leg_identifier(leg2),
                        sportsbook_specific=True,
                        suggested_action=f"Not allowed on {sportsbook} - try different sportsbook"
                    ))
        
        # Check minimum odds requirements
        min_odds = rules.get("min_odds_per_leg", 1.10)
        for leg in legs:
            odds = leg.get("odds_decimal", 0)
            if odds > 0 and odds < min_odds:
                violations.append(RuleViolation(
                    rule_type="MIN_ODDS_VIOLATION",
                    severity=ValidationLevel.HARD_BLOCK,
                    description=f"Leg odds {odds:.2f} below {sportsbook} minimum {min_odds:.2f}",
                    leg1_identifier=self._get_leg_identifier(leg),
                    leg2_identifier="N/A",
                    sportsbook_specific=True,
                    suggested_action=f"Find selections with odds >= {min_odds:.2f}"
                ))
        
        # Add sportsbook-specific warnings
        if rules.get("avoid_push_prone_props"):
            warnings.append(f"{sportsbook} recommends avoiding push-prone props")
        
        settlement_policy = rules.get("sgp_settlement", "unknown")
        if settlement_policy == "void_entire_parlay_on_push":
            warnings.append(f"{sportsbook} voids entire SGP on any push - consider push protection")
        
        return violations, warnings
    
    def _are_mutually_exclusive(self, leg1: Dict[str, Any], leg2: Dict[str, Any]) -> bool:
        """Check if two legs are mutually exclusive."""
        # Same player, opposite directions (over/under)
        if self._same_player_opposite_direction(leg1, leg2):
            return True
        
        # Same game, opposite team outcomes
        if self._same_game_opposite_teams(leg1, leg2):
            return True
        
        # Same total, opposite directions
        if self._same_total_opposite_direction(leg1, leg2):
            return True
        
        return False
    
    def _are_strongly_correlated(self, leg1: Dict[str, Any], leg2: Dict[str, Any]) -> bool:
        """Check if two legs have strong correlation."""
        # Team ML + Team spread/total (same team)
        if self._team_outcome_correlation(leg1, leg2):
            return True
        
        # Player prop + team outcome (key player)
        if self._player_team_correlation(leg1, leg2):
            return True
        
        # Same game, related markets
        if self._same_game_related_markets(leg1, leg2):
            return True
        
        return False
    
    def _are_softly_correlated(self, leg1: Dict[str, Any], leg2: Dict[str, Any]) -> bool:
        """Check if two legs have soft correlation."""
        # Different players, same team
        if self._same_team_different_players(leg1, leg2):
            return True
        
        # Game pace related props
        if self._pace_related_props(leg1, leg2):
            return True
        
        return False
    
    def _same_player_opposite_direction(self, leg1: Dict[str, Any], leg2: Dict[str, Any]) -> bool:
        """Check if legs are same player with opposite over/under."""
        player1 = self._extract_player_name(leg1.get("selection_name", ""))
        player2 = self._extract_player_name(leg2.get("selection_name", ""))
        
        if player1 and player2 and player1 == player2:
            market1 = leg1.get("market_type", "").upper()
            market2 = leg2.get("market_type", "").upper()
            
            # Check for opposite directions in same stat category
            stat_categories = ["POINTS", "REBOUNDS", "ASSISTS", "STEALS", "BLOCKS"]
            for stat in stat_categories:
                if (f"{stat}_OVER" in market1 and f"{stat}_UNDER" in market2) or \
                   (f"{stat}_UNDER" in market1 and f"{stat}_OVER" in market2):
                    return True
        
        return False
    
    def _same_game_opposite_teams(self, leg1: Dict[str, Any], leg2: Dict[str, Any]) -> bool:
        """Check if legs are same game with opposite team outcomes."""
        game1 = leg1.get("game_id", "")
        game2 = leg2.get("game_id", "")
        
        if game1 and game2 and game1 == game2:
            market1 = leg1.get("market_type", "").upper()
            market2 = leg2.get("market_type", "").upper()
            
            # Check for opposite team outcomes
            if ("MONEYLINE" in market1 and "MONEYLINE" in market2) or \
               ("WIN" in market1 and "WIN" in market2):
                # Different teams in same game selecting to win
                team1 = self._extract_team_name(leg1.get("selection_name", ""))
                team2 = self._extract_team_name(leg2.get("selection_name", ""))
                if team1 and team2 and team1 != team2:
                    return True
        
        return False
    
    def _same_total_opposite_direction(self, leg1: Dict[str, Any], leg2: Dict[str, Any]) -> bool:
        """Check if legs are same total with opposite over/under."""
        if leg1.get("market_type", "").upper() == "TOTALS" and \
           leg2.get("market_type", "").upper() == "TOTALS":
            
            # Same game, opposite directions
            if leg1.get("game_id") == leg2.get("game_id"):
                sel1 = leg1.get("selection_name", "").upper()
                sel2 = leg2.get("selection_name", "").upper()
                
                if ("OVER" in sel1 and "UNDER" in sel2) or \
                   ("UNDER" in sel1 and "OVER" in sel2):
                    return True
        
        return False
    
    def _team_outcome_correlation(self, leg1: Dict[str, Any], leg2: Dict[str, Any]) -> bool:
        """Check for team outcome correlations (ML + spread, etc.)."""
        # Same team, ML + spread
        team1 = self._extract_team_name(leg1.get("selection_name", ""))
        team2 = self._extract_team_name(leg2.get("selection_name", ""))
        
        if team1 and team2 and team1 == team2:
            market1 = leg1.get("market_type", "").upper()
            market2 = leg2.get("market_type", "").upper()
            
            # ML + Spread correlation
            if ("MONEYLINE" in market1 or "H2H" in market1) and "SPREAD" in market2:
                return True
            if "SPREAD" in market1 and ("MONEYLINE" in market2 or "H2H" in market2):
                return True
            
            # Team outcome + team total
            if ("MONEYLINE" in market1 or "H2H" in market1) and "TOTAL" in market2:
                return True
        
        return False
    
    def _player_team_correlation(self, leg1: Dict[str, Any], leg2: Dict[str, Any]) -> bool:
        """Check for player performance + team outcome correlation."""
        # Player prop + team outcome in same game
        game1 = leg1.get("game_id", "")
        game2 = leg2.get("game_id", "")
        
        if game1 and game2 and game1 == game2:
            market1 = leg1.get("market_type", "").upper()
            market2 = leg2.get("market_type", "").upper()
            
            # Player prop + team ML/spread
            player_markets = ["PLAYER_POINTS", "PLAYER_ASSISTS", "PLAYER_REBOUNDS"]
            team_markets = ["MONEYLINE", "H2H", "SPREAD"]
            
            is_player1 = any(pm in market1 for pm in player_markets)
            is_team2 = any(tm in market2 for tm in team_markets)
            is_player2 = any(pm in market2 for pm in player_markets)
            is_team1 = any(tm in market1 for tm in team_markets)
            
            if (is_player1 and is_team2) or (is_player2 and is_team1):
                return True
        
        return False
    
    def _same_game_related_markets(self, leg1: Dict[str, Any], leg2: Dict[str, Any]) -> bool:
        """Check for related markets in same game."""
        game1 = leg1.get("game_id", "")
        game2 = leg2.get("game_id", "")
        
        if game1 and game2 and game1 == game2:
            # First quarter + final outcome
            market1 = leg1.get("market_type", "").upper()
            market2 = leg2.get("market_type", "").upper()
            
            if ("FIRST_QUARTER" in market1 or "Q1" in market1) and \
               ("MONEYLINE" in market2 or "FINAL" in market2):
                return True
            
            # Halftime + final margin
            if ("HALFTIME" in market1 or "HALF" in market1) and \
               ("MARGIN" in market2 or "SPREAD" in market2):
                return True
        
        return False
    
    def _same_team_different_players(self, leg1: Dict[str, Any], leg2: Dict[str, Any]) -> bool:
        """Check for different players on same team."""
        # Extract team from game context or player names
        # This would need more sophisticated team mapping in practice
        game1 = leg1.get("game_id", "")
        game2 = leg2.get("game_id", "")
        
        if game1 and game2 and game1 == game2:
            player1 = self._extract_player_name(leg1.get("selection_name", ""))
            player2 = self._extract_player_name(leg2.get("selection_name", ""))
            
            # Different players, both player props
            if player1 and player2 and player1 != player2:
                market1 = leg1.get("market_type", "").upper()
                market2 = leg2.get("market_type", "").upper()
                
                if "PLAYER" in market1 and "PLAYER" in market2:
                    return True
        
        return False
    
    def _pace_related_props(self, leg1: Dict[str, Any], leg2: Dict[str, Any]) -> bool:
        """Check for pace-related correlations."""
        market1 = leg1.get("market_type", "").upper()
        market2 = leg2.get("market_type", "").upper()
        
        # Game total + multiple player overs (pace correlation)
        if "TOTAL" in market1 and "PLAYER" in market2 and "OVER" in market2:
            return True
        if "TOTAL" in market2 and "PLAYER" in market1 and "OVER" in market1:
            return True
        
        return False
    
    def _matches_prohibited_combination(self, leg1: Dict[str, Any], leg2: Dict[str, Any], 
                                      prohibited: List[Tuple[str, str]]) -> bool:
        """Check if legs match any prohibited combinations."""
        market1 = leg1.get("market_type", "").upper()
        market2 = leg2.get("market_type", "").upper()
        
        for combo1, combo2 in prohibited:
            if (combo1 in market1 and combo2 in market2) or \
               (combo2 in market1 and combo1 in market2):
                return True
        
        return False
    
    def _calculate_correlation_score(self, leg1: Dict[str, Any], leg2: Dict[str, Any]) -> float:
        """Calculate correlation score between two legs."""
        # Simplified correlation scoring - in practice this could be ML-based
        score = 0.0
        
        # Same game increases correlation
        if leg1.get("game_id") == leg2.get("game_id"):
            score += 0.3
        
        # Same team increases correlation
        team1 = self._extract_team_name(leg1.get("selection_name", ""))
        team2 = self._extract_team_name(leg2.get("selection_name", ""))
        if team1 and team2 and team1 == team2:
            score += 0.4
        
        # Same player maximizes correlation
        player1 = self._extract_player_name(leg1.get("selection_name", ""))
        player2 = self._extract_player_name(leg2.get("selection_name", ""))
        if player1 and player2 and player1 == player2:
            score += 0.5
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _extract_player_name(self, selection_name: str) -> Optional[str]:
        """Extract player name from selection string."""
        # Simplified extraction - would need more sophisticated parsing
        if not selection_name:
            return None
        
        # Remove common suffixes/prefixes
        name = selection_name.replace("Over", "").replace("Under", "").strip()
        name = name.replace("Points", "").replace("Assists", "").replace("Rebounds", "").strip()
        
        # If it looks like a player name (has space and capital letters)
        if " " in name and any(c.isupper() for c in name):
            return name
        
        return None
    
    def _extract_team_name(self, selection_name: str) -> Optional[str]:
        """Extract team name from selection string."""
        if not selection_name:
            return None
        
        # Common NBA team names - in practice this would be more comprehensive
        nba_teams = [
            "Lakers", "Celtics", "Warriors", "Nets", "Heat", "Bulls", "Knicks",
            "Clippers", "Nuggets", "Suns", "Mavericks", "Rockets", "Spurs",
            "Thunder", "Jazz", "Trail Blazers", "Kings", "Timberwolves", 
            "Pelicans", "Magic", "Hawks", "Hornets", "Pistons", "Pacers",
            "Cavaliers", "Raptors", "Wizards", "Bucks", "76ers", "Grizzlies"
        ]
        
        selection_lower = selection_name.lower()
        for team in nba_teams:
            if team.lower() in selection_lower:
                return team
        
        return None
    
    def _get_leg_identifier(self, leg: Dict[str, Any]) -> str:
        """Get a string identifier for a parlay leg."""
        return f"{leg.get('market_type', 'Unknown')}:{leg.get('selection_name', 'Unknown')}"
    
    def is_parlay_valid(self, legs: List[Dict[str, Any]], 
                       sportsbook: str = "DRAFTKINGS") -> Tuple[bool, str]:
        """
        Simple validation interface that returns validity and reason.
        
        Args:
            legs: List of parlay legs
            sportsbook: Target sportsbook
            
        Returns:
            Tuple of (is_valid, rejection_reason)
        """
        result = self.validate_parlay(legs, sportsbook)
        return result.is_valid, result.get_rejection_reason() or "Valid parlay"


def create_sample_legs_for_testing() -> List[Dict[str, Any]]:
    """Create sample legs for testing the rules engine."""
    return [
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
        },
        {
            "game_id": "game_2",
            "market_type": "player_points_over",
            "selection_name": "LeBron James",
            "odds_decimal": 1.95,
            "line": 25.5
        }
    ]


def main():
    """Main function for CLI testing."""
    import sys
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        print("🚫 Parlay Rules Engine - JIRA-022 Implementation")
        print("=" * 60)
        
        # Initialize rules engine
        engine = ParlayRulesEngine()
        
        # Test with sample legs
        print("\n🧪 Testing with Sample Parlay Legs:")
        sample_legs = create_sample_legs_for_testing()
        
        for i, leg in enumerate(sample_legs, 1):
            print(f"  {i}. {leg['selection_name']} ({leg['market_type']}) @ {leg['odds_decimal']}")
        
        # Test validation
        print(f"\n✅ Validation Results:")
        result = engine.validate_parlay(sample_legs, "DRAFTKINGS")
        
        print(f"Valid: {result.is_valid}")
        print(f"Violations: {len(result.violations)}")
        print(f"Warnings: {len(result.warnings)}")
        print(f"Correlation Tax: {result.correlation_tax_multiplier:.2f}x")
        
        if result.violations:
            print(f"\n⚠️ Rule Violations:")
            for violation in result.violations:
                print(f"  • {violation.severity.value.upper()}: {violation.description}")
                if violation.suggested_action:
                    print(f"    💡 {violation.suggested_action}")
        
        if result.warnings:
            print(f"\n🔍 Warnings:")
            for warning in result.warnings:
                print(f"  • {warning}")
        
        # Test different sportsbooks
        print(f"\n🏢 Testing Sportsbook-Specific Rules:")
        sportsbooks = ["DRAFTKINGS", "ESPN_BET", "BET365"]
        
        for sportsbook in sportsbooks:
            result = engine.validate_parlay(sample_legs, sportsbook)
            status = "✅ VALID" if result.is_valid else "❌ INVALID"
            print(f"  {sportsbook}: {status} ({len(result.violations)} violations)")
        
        print(f"\n🎯 Parlay Rules Engine Implementation Complete!")
        print(f"✅ JIRA-022 requirements fulfilled:")
        print(f"  • Universal hard blocks for mutually exclusive combinations")
        print(f"  • Strongly correlated blocks with SGP considerations")
        print(f"  • Soft correlation tracking with tax calculation")
        print(f"  • Sportsbook-specific exception handling")
        print(f"  • Comprehensive validation with detailed reasoning")
        
    except KeyboardInterrupt:
        print(f"\n⏹️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
