#!/usr/bin/env python3
"""
JSON-Based Parlay Rules Engine - JIRA-NFL-007

Extensible rule engine that loads sport-specific correlation and exclusion rules
from JSON configuration files, supporting both NBA and NFL parlays with
sophisticated rule evaluation and pricing adjustments.

Key Features:
- JSON-based rule configuration for easy sport addition
- Modular exclusion and correlation rule evaluation
- Sport-specific sportsbook rules and constraints
- Detailed violation tagging and reasoning
- Backward compatibility with existing NBA rules
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import re

# Set up logging
logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Validation severity levels for parlay rule violations."""
    HARD_BLOCK = "hard_block"          # Never allowed - reject immediately
    SOFT_BLOCK = "soft_block"          # Allowed with correlation tax/adjustment
    WARNING = "warning"                # Allowed but flagged for monitoring
    ALLOWED = "allowed"                # No restrictions


class ViolationTag(Enum):
    """Tags for categorizing rule violations."""
    LOGICAL_CONTRADICTION = "logical_contradiction"
    PRICING_MODEL_VIOLATION = "pricing_model_violation"
    RELATED_CONTINGENCY = "related_contingency"


@dataclass
class RuleViolation:
    """Represents a rule violation detected during parlay validation."""
    rule_id: str
    rule_type: str
    severity: ValidationLevel
    description: str
    leg1_identifier: str
    leg2_identifier: str
    sportsbook_specific: bool = False
    correlation_score: Optional[float] = None
    suggested_action: Optional[str] = None
    tags: List[ViolationTag] = field(default_factory=list)
    correlation_multiplier: Optional[float] = None


@dataclass
class ValidationResult:
    """Result of parlay rule validation."""
    is_valid: bool
    violations: List[RuleViolation] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    correlation_tax_multiplier: float = 1.0
    sport: Optional[str] = None
    
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
    JSON-based parlay rules engine supporting multiple sports.
    
    Loads sport-specific rules from JSON configuration files and provides
    comprehensive validation with detailed violation reporting.
    """
    
    def __init__(self, config_dir: str = "config"):
        """
        Initialize the rules engine.
        
        Args:
            config_dir: Directory containing sport configuration JSON files
        """
        self.config_dir = Path(config_dir)
        self.sport_configs: Dict[str, Dict] = {}
        self.loaded_sports: Set[str] = set()
        
        logger.info(f"ParlayRulesEngine initialized with config directory: {config_dir}")
    
    def load_rules(self, sport: str) -> Dict[str, Any]:
        """
        Load rules configuration for a specific sport.
        
        Args:
            sport: Sport identifier (e.g., 'nba', 'nfl')
            
        Returns:
            Dictionary containing sport configuration
            
        Raises:
            FileNotFoundError: If sport config file doesn't exist
            ValueError: If config file is invalid
        """
        sport_lower = sport.lower()
        
        # Return cached config if already loaded
        if sport_lower in self.sport_configs:
            return self.sport_configs[sport_lower]
        
        config_file = self.config_dir / f"{sport_lower}_markets.json"
        
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            # Validate config structure
            required_keys = ['sport', 'market_definitions', 'parlay_rules', 'sportsbook_rules']
            missing_keys = [key for key in required_keys if key not in config]
            if missing_keys:
                raise ValueError(f"Missing required keys in {config_file}: {missing_keys}")
            
            self.sport_configs[sport_lower] = config
            self.loaded_sports.add(sport_lower)
            
            logger.info(f"Loaded rules for {sport.upper()}: "
                       f"{len(config['parlay_rules'])} rules, "
                       f"{len(config['market_definitions'])} markets")
            
            return config
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            raise ValueError(f"Invalid configuration file {config_file}: {e}")
    
    def validate_parlay(self, legs: List[Dict[str, Any]], 
                       sport: str, 
                       sportsbook: str = "DRAFTKINGS") -> ValidationResult:
        """
        Validate a parlay against sport-specific rules.
        
        Args:
            legs: List of parlay legs with market info
            sport: Sport identifier
            sportsbook: Target sportsbook for sportsbook-specific rules
            
        Returns:
            ValidationResult with validation outcome and details
        """
        # Load sport configuration first to catch missing sports early
        try:
            config = self.load_rules(sport)
        except (FileNotFoundError, ValueError) as e:
            return ValidationResult(
                is_valid=False,
                warnings=[f"Failed to load {sport} rules: {e}"],
                sport=sport
            )
        
        if not legs:
            return ValidationResult(
                is_valid=False, 
                warnings=["No legs provided for validation"],
                sport=sport
            )
        
        if len(legs) < 2:
            return ValidationResult(
                is_valid=False, 
                warnings=["Parlay must have at least 2 legs"],
                sport=sport
            )
        
        logger.info(f"Validating {len(legs)} leg {sport.upper()} parlay for {sportsbook}")
        
        violations = []
        warnings = []
        correlation_tax = 1.0
        
        # Apply exclusion rules
        exclusion_violations = self.apply_exclusion_rules(legs, config)
        violations.extend(exclusion_violations)
        
        # Evaluate correlation rules
        correlation_violations, tax_multiplier = self.evaluate_correlation_rules(legs, config)
        violations.extend(correlation_violations)
        correlation_tax *= tax_multiplier
        
        # Check sportsbook-specific rules
        sportsbook_violations, sportsbook_warnings = self._check_sportsbook_rules(
            legs, sportsbook, config
        )
        violations.extend(sportsbook_violations)
        warnings.extend(sportsbook_warnings)
        
        # Determine if parlay is valid (no hard blocks)
        has_hard_blocks = any(v.severity == ValidationLevel.HARD_BLOCK for v in violations)
        is_valid = not has_hard_blocks
        
        result = ValidationResult(
            is_valid=is_valid,
            violations=violations,
            warnings=warnings,
            correlation_tax_multiplier=correlation_tax,
            sport=sport
        )
        
        # Log summary
        if violations:
            logger.warning(f"{sport.upper()} parlay validation found {len(violations)} violations "
                          f"(valid: {is_valid})")
        else:
            logger.info(f"{sport.upper()} parlay validation passed - no rule violations detected")
        
        return result
    
    def apply_exclusion_rules(self, legs: List[Dict[str, Any]], 
                             config: Dict[str, Any]) -> List[RuleViolation]:
        """
        Apply exclusion rules to detect hard block violations.
        
        Args:
            legs: List of parlay legs
            config: Sport configuration
            
        Returns:
            List of exclusion rule violations
        """
        violations = []
        exclusion_rules = [rule for rule in config['parlay_rules'] if rule['type'] == 'EXCLUSION']
        
        for rule in exclusion_rules:
            rule_violations = self._evaluate_exclusion_rule(legs, rule, config)
            violations.extend(rule_violations)
        
        return violations
    
    def evaluate_correlation_rules(self, legs: List[Dict[str, Any]], 
                                  config: Dict[str, Any]) -> Tuple[List[RuleViolation], float]:
        """
        Evaluate correlation rules and calculate pricing adjustments.
        
        Args:
            legs: List of parlay legs
            config: Sport configuration
            
        Returns:
            Tuple of (correlation violations, tax multiplier)
        """
        violations = []
        correlation_tax = 1.0
        correlation_rules = [rule for rule in config['parlay_rules'] if rule['type'] == 'CORRELATION']
        
        for rule in correlation_rules:
            rule_violations, rule_tax = self._evaluate_correlation_rule(legs, rule, config)
            violations.extend(rule_violations)
            correlation_tax *= rule_tax
        
        return violations, correlation_tax
    
    def _evaluate_exclusion_rule(self, legs: List[Dict[str, Any]], 
                                rule: Dict[str, Any], 
                                config: Dict[str, Any]) -> List[RuleViolation]:
        """Evaluate a specific exclusion rule against the parlay legs."""
        violations = []
        conditions = rule['conditions']
        constraints = rule['constraints']
        
        # Find legs that match the rule conditions
        matching_pairs = []
        
        if 'all' in conditions:
            # All conditions must be met
            matching_pairs = self._find_matching_leg_pairs_all(legs, conditions['all'], config)
        elif 'any' in conditions:
            # Any condition can trigger the rule
            matching_pairs = self._find_matching_leg_pairs_any(legs, conditions['any'], config)
        
        # Check constraints for each matching pair
        for leg1, leg2 in matching_pairs:
            if self._check_constraints(leg1, leg2, constraints):
                severity = ValidationLevel.HARD_BLOCK if rule.get('severity') == 'HARD_BLOCK' else ValidationLevel.SOFT_BLOCK
                
                violation = RuleViolation(
                    rule_id=rule['ruleId'],
                    rule_type="EXCLUSION",
                    severity=severity,
                    description=rule['description'],
                    leg1_identifier=self._get_leg_identifier(leg1),
                    leg2_identifier=self._get_leg_identifier(leg2),
                    suggested_action="Remove one of the conflicting legs",
                    tags=[self._get_violation_tag(rule)]
                )
                violations.append(violation)
        
        return violations
    
    def _evaluate_correlation_rule(self, legs: List[Dict[str, Any]], 
                                  rule: Dict[str, Any], 
                                  config: Dict[str, Any]) -> Tuple[List[RuleViolation], float]:
        """Evaluate a specific correlation rule against the parlay legs."""
        violations = []
        correlation_tax = 1.0
        
        conditions = rule['conditions']
        constraints = rule['constraints']
        correlation_adj = rule.get('correlation_adjustment', {})
        
        # Find legs that match the rule conditions
        matching_pairs = []
        
        if 'all' in conditions:
            matching_pairs = self._find_matching_leg_pairs_all(legs, conditions['all'], config)
        
        # Apply correlation adjustments for each matching pair
        for leg1, leg2 in matching_pairs:
            if self._check_constraints(leg1, leg2, constraints):
                multiplier = correlation_adj.get('multiplier', 1.0)
                correlation_tax *= multiplier
                
                severity_map = {
                    'HARD_BLOCK': ValidationLevel.HARD_BLOCK,
                    'SOFT_BLOCK': ValidationLevel.SOFT_BLOCK,
                    'WARNING': ValidationLevel.WARNING
                }
                severity = severity_map.get(rule.get('severity', 'WARNING'), ValidationLevel.WARNING)
                
                violation = RuleViolation(
                    rule_id=rule['ruleId'],
                    rule_type="CORRELATION",
                    severity=severity,
                    description=rule['description'],
                    leg1_identifier=self._get_leg_identifier(leg1),
                    leg2_identifier=self._get_leg_identifier(leg2),
                    correlation_score=1.0 - multiplier,  # Higher correlation = lower multiplier
                    correlation_multiplier=multiplier,
                    suggested_action=f"Correlation adjustment applied (multiplier: {multiplier:.3f})",
                    tags=[self._get_violation_tag(rule)]
                )
                violations.append(violation)
        
        return violations, correlation_tax
    
    def _find_matching_leg_pairs_all(self, legs: List[Dict[str, Any]], 
                                    conditions: List[Dict], 
                                    config: Dict[str, Any]) -> List[Tuple[Dict, Dict]]:
        """Find pairs of legs that match ALL specified conditions."""
        pairs = []
        
        for i, leg1 in enumerate(legs):
            for leg2 in legs[i+1:]:
                if self._legs_match_all_conditions(leg1, leg2, conditions, config):
                    pairs.append((leg1, leg2))
        
        return pairs
    
    def _find_matching_leg_pairs_any(self, legs: List[Dict[str, Any]], 
                                    conditions: List[Dict], 
                                    config: Dict[str, Any]) -> List[Tuple[Dict, Dict]]:
        """Find pairs of legs that match ANY specified conditions."""
        pairs = []
        
        for i, leg1 in enumerate(legs):
            for leg2 in legs[i+1:]:
                if self._legs_match_any_conditions(leg1, leg2, conditions, config):
                    pairs.append((leg1, leg2))
        
        return pairs
    
    def _legs_match_all_conditions(self, leg1: Dict, leg2: Dict, 
                                  conditions: List[Dict], 
                                  config: Dict[str, Any]) -> bool:
        """Check if two legs match all specified conditions."""
        leg1_matches = []
        leg2_matches = []
        
        for condition in conditions:
            leg1_matches.append(self._leg_matches_condition(leg1, condition, config))
            leg2_matches.append(self._leg_matches_condition(leg2, condition, config))
        
        # For "all" conditions, we need each condition to match exactly one leg
        # and all conditions to be covered by different legs
        if len(conditions) == 2:
            # Two conditions: one leg matches condition 1, other matches condition 2
            return ((leg1_matches[0] and leg2_matches[1]) or 
                    (leg1_matches[1] and leg2_matches[0]))
        
        # For more complex cases, ensure all conditions are covered
        for i, condition in enumerate(conditions):
            if not (leg1_matches[i] or leg2_matches[i]):
                return False
        
        # Ensure both legs contribute to the match
        return any(leg1_matches) and any(leg2_matches)
    
    def _legs_match_any_conditions(self, leg1: Dict, leg2: Dict, 
                                  conditions: List[Dict], 
                                  config: Dict[str, Any]) -> bool:
        """Check if two legs match any specified conditions."""
        for condition in conditions:
            if (self._leg_matches_condition(leg1, condition, config) and 
                self._leg_matches_condition(leg2, condition, config)):
                return True
        return False
    
    def _leg_matches_condition(self, leg: Dict, condition: Dict, config: Dict[str, Any]) -> bool:
        """Check if a single leg matches a condition."""
        # Market key matching
        if 'market_key' in condition:
            return leg.get('market_type') == condition['market_key']
        
        if 'market_keys' in condition:
            return leg.get('market_type') in condition['market_keys']
        
        # Market group matching
        if 'market_group' in condition:
            market_type = leg.get('market_type')
            if market_type in config['market_definitions']:
                market_def = config['market_definitions'][market_type]
                return market_def.get('group') == condition['market_group']
        
        # Selection matching
        if 'selection' in condition:
            selection = leg.get('selection_name', '').upper()
            return condition['selection'].upper() in selection
        
        if 'selections' in condition:
            selection = leg.get('selection_name', '').upper()
            return any(sel.upper() in selection for sel in condition['selections'])
        
        return False
    
    def _check_constraints(self, leg1: Dict, leg2: Dict, constraints: Dict) -> bool:
        """Check if two legs satisfy the rule constraints."""
        # Same game constraint
        if constraints.get('same_game'):
            if leg1.get('game_id') != leg2.get('game_id'):
                return False
        
        # Same team constraint
        if constraints.get('same_team'):
            team1 = self._extract_team_name(leg1)
            team2 = self._extract_team_name(leg2)
            
            # If explicit team names found, check they match
            if team1 and team2:
                if team1 != team2:
                    return False
            else:
                # If no explicit team names, check if same game (common for player props)
                game1 = leg1.get('game_id', '')
                game2 = leg2.get('game_id', '')
                if game1 and game2 and game1 == game2:
                    # Same game implies same teams involved - allow it
                    pass
                else:
                    # Can't determine team relationship
                    return False
        
        # Opposite teams constraint
        if constraints.get('opposite_teams'):
            team1 = self._extract_team_name(leg1)
            team2 = self._extract_team_name(leg2)
            if not team1 or not team2 or team1 == team2:
                return False
        
        # Same player constraint
        if constraints.get('same_player'):
            player1 = self._extract_player_name(leg1)
            player2 = self._extract_player_name(leg2)
            if not player1 or not player2 or player1 != player2:
                return False
        
        # Different players constraint
        if constraints.get('different_players'):
            player1 = self._extract_player_name(leg1)
            player2 = self._extract_player_name(leg2)
            if player1 and player2 and player1 == player2:
                return False
            # If we can't extract player names, assume they're different (common case)
            # This allows correlation rules to still fire for different player props
        
        # Opposite selections constraint (Over/Under)
        if constraints.get('opposite_selections'):
            sel1 = leg1.get('selection_name', '').upper()
            sel2 = leg2.get('selection_name', '').upper()
            if ('OVER' in sel1 and 'UNDER' in sel2) or ('UNDER' in sel1 and 'OVER' in sel2):
                return True
            return False
        
        return True
    
    def _check_sportsbook_rules(self, legs: List[Dict[str, Any]], 
                               sportsbook: str, 
                               config: Dict[str, Any]) -> Tuple[List[RuleViolation], List[str]]:
        """Check sportsbook-specific rules."""
        violations = []
        warnings = []
        
        sportsbook_rules = config.get('sportsbook_rules', {})
        if sportsbook not in sportsbook_rules:
            warnings.append(f"Unknown sportsbook '{sportsbook}' - using default rules")
            return violations, warnings
        
        rules = sportsbook_rules[sportsbook]
        
        # Check max legs limit
        max_legs = rules.get('max_legs', 20)
        if len(legs) > max_legs:
            violations.append(RuleViolation(
                rule_id="MAX_LEGS_EXCEEDED",
                rule_type="SPORTSBOOK_LIMIT",
                severity=ValidationLevel.HARD_BLOCK,
                description=f"Parlay exceeds {sportsbook} maximum of {max_legs} legs",
                leg1_identifier="ALL_LEGS",
                leg2_identifier="ALL_LEGS",
                sportsbook_specific=True,
                suggested_action=f"Reduce to {max_legs} legs or fewer"
            ))
        
        # Check minimum odds requirements
        min_odds = rules.get('min_odds_per_leg', 1.10)
        for leg in legs:
            odds = leg.get('odds_decimal', 0)
            if odds > 0 and odds < min_odds:
                violations.append(RuleViolation(
                    rule_id="MIN_ODDS_VIOLATION",
                    rule_type="SPORTSBOOK_LIMIT",
                    severity=ValidationLevel.HARD_BLOCK,
                    description=f"Leg odds {odds:.2f} below {sportsbook} minimum {min_odds:.2f}",
                    leg1_identifier=self._get_leg_identifier(leg),
                    leg2_identifier="N/A",
                    sportsbook_specific=True,
                    suggested_action=f"Find selections with odds >= {min_odds:.2f}"
                ))
        
        # Check prohibited combinations
        prohibited = rules.get('prohibited_combinations', [])
        for combo in prohibited:
            if self._has_prohibited_combination(legs, combo):
                violations.append(RuleViolation(
                    rule_id="SPORTSBOOK_PROHIBITED",
                    rule_type="SPORTSBOOK_LIMIT",
                    severity=ValidationLevel.HARD_BLOCK,
                    description=f"{sportsbook} prohibits combination: {' + '.join(combo)}",
                    leg1_identifier="MULTIPLE",
                    leg2_identifier="MULTIPLE",
                    sportsbook_specific=True,
                    suggested_action=f"Not allowed on {sportsbook} - try different sportsbook"
                ))
        
        return violations, warnings
    
    def _has_prohibited_combination(self, legs: List[Dict], prohibited_combo: List[str]) -> bool:
        """Check if legs contain a prohibited combination."""
        leg_markets = [leg.get('market_type', '') for leg in legs]
        
        # Check if all prohibited markets are present
        return all(market in leg_markets for market in prohibited_combo)
    
    def _extract_team_name(self, leg: Dict) -> Optional[str]:
        """Extract team name from leg data."""
        # Try to get team from selection name or game context
        selection = leg.get('selection_name', '')
        
        # Common team name patterns
        team_patterns = [
            r'\b(Lakers|Celtics|Warriors|Nets|Heat|Bulls|Knicks|Clippers|Nuggets|Suns)\b',
            r'\b(Chiefs|Bills|Patriots|Dolphins|Ravens|Steelers|Browns|Bengals)\b',
            r'\b(Cowboys|Giants|Eagles|Commanders|Packers|Bears|Lions|Vikings)\b',
            r'\bDallas\s+Cowboys\b',
            r'\bKansas\s+City\s+Chiefs\b',
            r'\bNew\s+York\s+Giants\b'
        ]
        
        for pattern in team_patterns:
            match = re.search(pattern, selection, re.IGNORECASE)
            if match:
                team_name = match.group(1) if match.groups() else match.group(0)
                # Normalize team names
                if 'Cowboys' in team_name:
                    return 'Cowboys'
                elif 'Chiefs' in team_name:
                    return 'Chiefs'
                elif 'Giants' in team_name:
                    return 'Giants'
                return team_name
        
        return None
    
    def _extract_player_name(self, leg: Dict) -> Optional[str]:
        """Extract player name from leg data."""
        selection = leg.get('selection_name', '')
        
        # Remove common betting terms but keep name-like parts
        clean_name = selection
        for term in ['Over', 'Under', 'Points', 'Yards', 'Assists', 'Rebounds', 'Touchdowns']:
            clean_name = re.sub(f'\\b{term}\\b', '', clean_name, flags=re.IGNORECASE).strip()
        
        # Remove numbers and decimal values (like 275.5)
        clean_name = re.sub(r'\b\d+(?:\.\d+)?\b', '', clean_name).strip()
        
        # Look for player name pattern (First Last)
        name_match = re.search(r'\b([A-Z][a-z]+ [A-Z][a-z]+)\b', clean_name)
        if name_match:
            return name_match.group(1)
        
        # Try simpler patterns for cases like "Patrick Mahomes" or "Travis Kelce"
        simple_match = re.search(r'\b([A-Z]\w+ [A-Z]\w+)\b', selection)
        if simple_match:
            name = simple_match.group(1)
            # Filter out common team words
            if not any(word in name.upper() for word in ['OVER', 'UNDER', 'POINTS', 'YARDS']):
                return name
        
        return None
    
    def _get_leg_identifier(self, leg: Dict) -> str:
        """Get a string identifier for a parlay leg."""
        return f"{leg.get('market_type', 'Unknown')}:{leg.get('selection_name', 'Unknown')}"
    
    def _get_violation_tag(self, rule: Dict) -> ViolationTag:
        """Get the appropriate violation tag for a rule."""
        rule_id = rule.get('ruleId', '').upper()
        
        if 'EXCLUSION' in rule_id or 'OPPOSITE' in rule_id:
            return ViolationTag.LOGICAL_CONTRADICTION
        elif 'CORRELATION' in rule_id:
            return ViolationTag.PRICING_MODEL_VIOLATION
        else:
            return ViolationTag.RELATED_CONTINGENCY
    
    def is_parlay_valid(self, legs: List[Dict[str, Any]], 
                       sport: str,
                       sportsbook: str = "DRAFTKINGS") -> Tuple[bool, str]:
        """
        Simple validation interface that returns validity and reason.
        
        Args:
            legs: List of parlay legs
            sport: Sport identifier
            sportsbook: Target sportsbook
            
        Returns:
            Tuple of (is_valid, rejection_reason)
        """
        result = self.validate_parlay(legs, sport, sportsbook)
        return result.is_valid, result.get_rejection_reason() or "Valid parlay"
    
    def get_supported_sports(self) -> List[str]:
        """Get list of supported sports based on available config files."""
        sports = []
        for config_file in self.config_dir.glob("*_markets.json"):
            sport_name = config_file.stem.replace("_markets", "")
            sports.append(sport_name)
        return sorted(sports)


def create_sample_nfl_legs() -> List[Dict[str, Any]]:
    """Create sample NFL legs for testing."""
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
        },
        {
            "game_id": "cowboys_vs_giants",
            "market_type": "moneyline",
            "selection_name": "Dallas Cowboys",
            "odds_decimal": 1.75
        }
    ]


def create_sample_nba_legs() -> List[Dict[str, Any]]:
    """Create sample NBA legs for testing."""
    return [
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
        },
        {
            "game_id": "warriors_vs_nets",
            "market_type": "totals",
            "selection_name": "Over 220.5",
            "odds_decimal": 1.95,
            "line": 220.5
        }
    ]


def main():
    """Main function for testing the enhanced rules engine."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🏈🏀 Enhanced Parlay Rules Engine - JIRA-NFL-007")
    print("=" * 70)
    
    try:
        # Initialize engine
        engine = ParlayRulesEngine()
        
        # Test supported sports
        supported_sports = engine.get_supported_sports()
        print(f"📋 Supported Sports: {', '.join(supported_sports)}")
        
        # Test NFL parlay
        print(f"\n🏈 Testing NFL Parlay Rules:")
        print("-" * 40)
        
        nfl_legs = create_sample_nfl_legs()
        for i, leg in enumerate(nfl_legs, 1):
            print(f"  {i}. {leg['selection_name']} @ {leg['odds_decimal']}")
        
        nfl_result = engine.validate_parlay(nfl_legs, "nfl", "DRAFTKINGS")
        
        print(f"\nNFL Validation Results:")
        print(f"  Valid: {nfl_result.is_valid}")
        print(f"  Violations: {len(nfl_result.violations)}")
        print(f"  Correlation Tax: {nfl_result.correlation_tax_multiplier:.3f}x")
        
        if nfl_result.violations:
            print(f"\n⚠️ NFL Rule Violations:")
            for violation in nfl_result.violations:
                print(f"  • {violation.severity.value.upper()}: {violation.description}")
                if violation.correlation_multiplier:
                    print(f"    💰 Pricing adjustment: {violation.correlation_multiplier:.3f}x")
        
        # Test NBA parlay (backward compatibility)
        print(f"\n🏀 Testing NBA Parlay Rules (Backward Compatibility):")
        print("-" * 40)
        
        nba_legs = create_sample_nba_legs()
        for i, leg in enumerate(nba_legs, 1):
            print(f"  {i}. {leg['selection_name']} @ {leg['odds_decimal']}")
        
        nba_result = engine.validate_parlay(nba_legs, "nba", "DRAFTKINGS")
        
        print(f"\nNBA Validation Results:")
        print(f"  Valid: {nba_result.is_valid}")
        print(f"  Violations: {len(nba_result.violations)}")
        print(f"  Correlation Tax: {nba_result.correlation_tax_multiplier:.3f}x")
        
        if nba_result.violations:
            print(f"\n⚠️ NBA Rule Violations:")
            for violation in nba_result.violations:
                print(f"  • {violation.severity.value.upper()}: {violation.description}")
        
        print(f"\n✅ JIRA-NFL-007 Implementation Complete!")
        print(f"🎯 Enhanced Parlay Rules Engine Features:")
        print(f"  • JSON-based rule configuration")
        print(f"  • Multi-sport support (NBA, NFL)")
        print(f"  • Modular exclusion and correlation evaluation")
        print(f"  • Detailed violation tagging and reasoning")
        print(f"  • Backward compatibility with existing NBA rules")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        print(f"❌ Test failed: {e}")


if __name__ == "__main__":
    main()
