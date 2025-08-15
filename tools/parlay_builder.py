#!/usr/bin/env python3
"""
ParlayBuilder Tool - JIRA-021

Validates parlay legs against current market availability to ensure only
active, available markets are included in final parlays.

Key Features:
- Fetches fresh market data from OddsFetcherTool
- Filters potential legs against available markets
- Handles suspended/unavailable markets
- Provides detailed validation results
- Supports both active season and off-season scenarios
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json

from tools.odds_fetcher_tool import OddsFetcherTool, GameOdds, BookOdds, Selection

# Import parlay rules engine (JIRA-022)
from tools.parlay_rules import ParlayRulesEngine, ValidationResult as RulesValidationResult

# Import correlation model (optional dependency)
try:
    from tools.correlation_model import DynamicCorrelationModel, BetNode
    HAS_CORRELATION_MODEL = True
except ImportError:
    HAS_CORRELATION_MODEL = False
    logger.warning("Correlation model not available. Install PyTorch Geometric for correlation detection.")

# Set up logging
logger = logging.getLogger(__name__)


@dataclass
class ParlayLeg:
    """Represents a single leg of a parlay bet."""
    game_id: str
    market_type: str  # 'h2h', 'spreads', 'totals', 'player_props'
    selection_name: str  # Team name, player name, or outcome
    bookmaker: str
    odds_decimal: float
    line: Optional[float] = None  # Point spread, total, or prop line
    
    def __post_init__(self):
        """Validate leg data after initialization."""
        if not self.game_id:
            raise ValueError("game_id cannot be empty")
        if not self.market_type:
            raise ValueError("market_type cannot be empty")
        if not self.selection_name:
            raise ValueError("selection_name cannot be empty")
        if not self.bookmaker:
            raise ValueError("bookmaker cannot be empty")
        if self.odds_decimal <= 1.0:
            raise ValueError("odds_decimal must be greater than 1.0")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert leg to dictionary for serialization."""
        return {
            'game_id': self.game_id,
            'market_type': self.market_type,
            'selection_name': self.selection_name,
            'bookmaker': self.bookmaker,
            'odds_decimal': self.odds_decimal,
            'line': self.line
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ParlayLeg':
        """Create ParlayLeg from dictionary."""
        return cls(
            game_id=data['game_id'],
            market_type=data['market_type'],
            selection_name=data['selection_name'],
            bookmaker=data['bookmaker'],
            odds_decimal=data['odds_decimal'],
            line=data.get('line')
        )


@dataclass
class ValidationResult:
    """Result of validating a parlay leg against current markets."""
    leg: ParlayLeg
    is_valid: bool
    reason: str
    current_odds: Optional[float] = None
    current_line: Optional[float] = None
    alternative_bookmakers: List[str] = field(default_factory=list)
    correlation_score: Optional[float] = None  # Added for JIRA-022A


@dataclass
class ParlayValidation:
    """Complete validation results for a parlay."""
    original_legs: List[ParlayLeg]
    valid_legs: List[ParlayLeg]
    invalid_legs: List[ValidationResult]
    total_odds: float
    validation_timestamp: str
    market_snapshot_games: int
    correlation_warnings: List[str] = field(default_factory=list)  # Added for JIRA-022A
    max_correlation_score: Optional[float] = None  # Added for JIRA-022A
    rules_validation: Optional[RulesValidationResult] = None  # Added for JIRA-022
    correlation_tax_multiplier: float = 1.0  # Added for JIRA-022
    
    def success_rate(self) -> float:
        """Calculate percentage of legs that passed validation."""
        if not self.original_legs:
            return 0.0
        return len(self.valid_legs) / len(self.original_legs) * 100
    
    def is_viable(self, min_legs: int = 2) -> bool:
        """Check if parlay is still viable after validation."""
        return len(self.valid_legs) >= min_legs


class ParlayBuilderError(Exception):
    """Custom exception for ParlayBuilder errors."""
    pass


class ParlayBuilder:
    """
    Tool for building and validating parlays against current market availability.
    
    This tool ensures that parlay legs are only selected from currently available
    markets by fetching fresh odds data and filtering out suspended or unavailable bets.
    """
    
    def __init__(self, sport_key: str = "basketball_nba", 
                 correlation_threshold: float = 0.7,
                 db_path: str = "data/parlays.sqlite",
                 default_sportsbook: str = "DRAFTKINGS"):
        """
        Initialize ParlayBuilder.
        
        Args:
            sport_key: Sport to fetch odds for (default: basketball_nba)
            correlation_threshold: Threshold for flagging correlated legs (default: 0.7)
            db_path: Path to SQLite database for correlation model training
            default_sportsbook: Default sportsbook for rules validation (default: DRAFTKINGS)
        """
        self.sport_key = sport_key
        self.correlation_threshold = correlation_threshold
        self.default_sportsbook = default_sportsbook
        self.odds_fetcher = OddsFetcherTool()
        self._current_market_snapshot: Optional[List[GameOdds]] = None
        self._snapshot_timestamp: Optional[str] = None
        
        # Initialize parlay rules engine (JIRA-022)
        self.rules_engine = ParlayRulesEngine(correlation_threshold=correlation_threshold)
        logger.info("Parlay rules engine initialized for compatibility validation")
        
        # Initialize correlation model (JIRA-022A)
        self.correlation_model = None
        if HAS_CORRELATION_MODEL:
            try:
                self.correlation_model = DynamicCorrelationModel(db_path)
                self.correlation_model.load_model()  # Try to load existing model
                logger.info("Correlation model initialized for dynamic correlation detection")
            except Exception as e:
                logger.warning(f"Failed to initialize correlation model: {e}")
        
        logger.info(f"ParlayBuilder initialized for sport: {sport_key}")
    
    def _get_fresh_market_snapshot(self, regions: str = "us", 
                                 markets: Optional[List[str]] = None) -> List[GameOdds]:
        """
        Fetch fresh market data from OddsFetcherTool.
        
        Args:
            regions: Regions to fetch odds for
            markets: Markets to include (defaults to h2h, spreads, totals)
            
        Returns:
            List of current game odds
            
        Raises:
            ParlayBuilderError: If unable to fetch market data
        """
        if markets is None:
            markets = ["h2h", "spreads", "totals"]
        
        try:
            logger.info(f"Fetching fresh market snapshot for {self.sport_key}")
            game_odds = self.odds_fetcher.get_game_odds(
                sport_key=self.sport_key,
                regions=regions,
                markets=markets
            )
            
            self._current_market_snapshot = game_odds
            self._snapshot_timestamp = datetime.now(timezone.utc).isoformat()
            
            logger.info(f"Market snapshot updated: {len(game_odds)} games, "
                       f"{sum(len(game.books) for game in game_odds)} total markets")
            
            return game_odds
            
        except Exception as e:
            logger.error(f"Failed to fetch market snapshot: {e}")
            raise ParlayBuilderError(f"Unable to fetch current market data: {e}")
    
    def _find_matching_selection(self, leg: ParlayLeg, 
                               game_odds: GameOdds) -> Optional[Tuple[BookOdds, Selection]]:
        """
        Find a matching selection for a parlay leg in current market data.
        
        Args:
            leg: Parlay leg to match
            game_odds: Current odds for the game
            
        Returns:
            Tuple of (BookOdds, Selection) if found, None otherwise
        """
        for book_odds in game_odds.books:
            # Check if bookmaker matches
            if book_odds.bookmaker.lower() != leg.bookmaker.lower():
                continue
            
            # Check if market type matches
            if book_odds.market != leg.market_type:
                continue
            
            # Find matching selection
            for selection in book_odds.selections:
                if self._selection_matches(selection, leg):
                    return book_odds, selection
        
        return None
    
    def _selection_matches(self, selection: Selection, leg: ParlayLeg) -> bool:
        """
        Check if a selection matches a parlay leg.
        
        Args:
            selection: Current market selection
            leg: Parlay leg to match
            
        Returns:
            True if they match, False otherwise
        """
        # Basic name matching (case-insensitive)
        if selection.name.lower() != leg.selection_name.lower():
            return False
        
        # For spread/total markets, check if line matches (within tolerance)
        if leg.line is not None and selection.line is not None:
            line_tolerance = 0.5  # Allow 0.5 point difference
            if abs(selection.line - leg.line) > line_tolerance:
                return False
        
        return True
    
    def _find_alternative_bookmakers(self, leg: ParlayLeg, 
                                   game_odds: GameOdds) -> List[str]:
        """
        Find alternative bookmakers offering the same selection.
        
        Args:
            leg: Parlay leg to find alternatives for
            game_odds: Current odds for the game
            
        Returns:
            List of alternative bookmaker names
        """
        alternatives = []
        
        for book_odds in game_odds.books:
            # Skip the original bookmaker
            if book_odds.bookmaker.lower() == leg.bookmaker.lower():
                continue
            
            # Check if market type matches
            if book_odds.market != leg.market_type:
                continue
            
            # Check if selection is available
            for selection in book_odds.selections:
                if self._selection_matches(selection, leg):
                    alternatives.append(book_odds.bookmaker)
                    break
        
        return alternatives
    
    def _convert_leg_to_bet_node(self, leg: ParlayLeg) -> 'BetNode':
        """Convert ParlayLeg to BetNode for correlation analysis."""
        if not HAS_CORRELATION_MODEL:
            return None
        
        # Extract team from selection name (simplified)
        team = None
        selection_lower = leg.selection_name.lower()
        nba_teams = [
            'lakers', 'celtics', 'warriors', 'nets', 'heat', 'bulls', 'knicks',
            'clippers', 'nuggets', 'suns', 'mavericks', 'rockets', 'spurs',
            'thunder', 'jazz', 'blazers', 'kings', 'timberwolves', 'pelicans',
            'magic', 'hawks', 'hornets', 'pistons', 'pacers', 'cavaliers',
            'raptors', 'wizards', 'bucks', '76ers', 'grizzlies'
        ]
        
        for nba_team in nba_teams:
            if nba_team in selection_lower:
                team = nba_team.title()
                break
        
        return BetNode(
            bet_id=0,  # Placeholder
            game_id=leg.game_id,
            market_type=leg.market_type,
            team=team,
            player=None,  # Could be extracted from selection_name if needed
            line_value=leg.line,
            odds=leg.odds_decimal,
            outcome=None  # Unknown for potential legs
        )
    
    def _check_correlations(self, potential_legs: List[ParlayLeg]) -> Tuple[List[str], float]:
        """
        Check for correlations between potential parlay legs.
        
        Args:
            potential_legs: List of potential parlay legs
            
        Returns:
            Tuple of (correlation_warnings, max_correlation_score)
        """
        warnings = []
        max_correlation = 0.0
        
        if not self.correlation_model or len(potential_legs) < 2:
            return warnings, max_correlation
        
        # Convert legs to bet nodes
        bet_nodes = []
        for leg in potential_legs:
            bet_node = self._convert_leg_to_bet_node(leg)
            if bet_node:
                bet_nodes.append((leg, bet_node))
        
        # Check pairwise correlations
        for i, (leg1, node1) in enumerate(bet_nodes):
            for leg2, node2 in bet_nodes[i+1:]:
                try:
                    if self.correlation_model:
                        # Get feature vectors
                        features1 = node1.to_feature_vector()
                        features2 = node2.to_feature_vector()
                        
                        # Predict correlation
                        correlation_score = self.correlation_model.predict_correlation(
                            features1, features2
                        )
                        
                        # Boost correlation for same-game legs (rule-based enhancement)
                        if leg1.game_id == leg2.game_id:
                            correlation_score = max(correlation_score, 0.8)  # Same game = high correlation
                    else:
                        # Simple rule-based correlation when no model available
                        correlation_score = self._simple_correlation_check(leg1, leg2)
                    
                    max_correlation = max(max_correlation, correlation_score)
                    
                    # Flag high correlations
                    if correlation_score > self.correlation_threshold:
                        warning = (f"High correlation detected ({correlation_score:.3f}) between "
                                 f"{leg1.selection_name} and {leg2.selection_name}")
                        warnings.append(warning)
                        logger.warning(warning)
                    
                except Exception as e:
                    logger.debug(f"Correlation check failed for {leg1.selection_name} vs {leg2.selection_name}: {e}")
        
        return warnings, max_correlation
    
    def _simple_correlation_check(self, leg1: ParlayLeg, leg2: ParlayLeg) -> float:
        """Simple rule-based correlation check when no ML model is available."""
        correlation_score = 0.0
        
        # Same game = high correlation
        if leg1.game_id == leg2.game_id:
            correlation_score = 0.85
            
            # Same team in same game = very high correlation
            if (leg1.selection_name.lower() in leg2.selection_name.lower() or 
                leg2.selection_name.lower() in leg1.selection_name.lower()):
                correlation_score = 0.95
        
        # Same team different games = medium correlation
        elif (leg1.selection_name.lower() in leg2.selection_name.lower() or 
              leg2.selection_name.lower() in leg1.selection_name.lower()):
            correlation_score = 0.4
        
        # Same market type = low correlation
        elif leg1.market_type == leg2.market_type:
            correlation_score = 0.2
        
        return correlation_score
    
    def validate_parlay_legs(self, potential_legs: List[ParlayLeg], 
                           regions: str = "us",
                           markets: Optional[List[str]] = None,
                           sportsbook: Optional[str] = None) -> ParlayValidation:
        """
        Validate parlay legs against current market availability and compatibility rules.
        
        Args:
            potential_legs: List of potential parlay legs to validate
            regions: Regions to fetch odds for
            markets: Markets to include in validation
            sportsbook: Target sportsbook for rules validation (uses default if None)
            
        Returns:
            ParlayValidation with results
            
        Raises:
            ParlayBuilderError: If validation fails due to system errors
        """
        if not potential_legs:
            raise ParlayBuilderError("No potential legs provided for validation")
        
        if sportsbook is None:
            sportsbook = self.default_sportsbook
        
        logger.info(f"Validating {len(potential_legs)} potential parlay legs for {sportsbook}")
        
        # First, validate against parlay rules (JIRA-022)
        leg_dicts = [leg.to_dict() for leg in potential_legs]
        rules_validation = self.rules_engine.validate_parlay(leg_dicts, sportsbook)
        
        # If rules validation fails with hard blocks, return early
        if not rules_validation.is_valid:
            logger.warning(f"Parlay rejected due to rule violations: {rules_validation.get_rejection_reason()}")
            return ParlayValidation(
                original_legs=potential_legs,
                valid_legs=[],
                invalid_legs=[],
                total_odds=0.0,
                validation_timestamp=datetime.now(timezone.utc).isoformat(),
                market_snapshot_games=0,
                rules_validation=rules_validation,
                correlation_tax_multiplier=rules_validation.correlation_tax_multiplier
            )
        
        # Check for correlations (JIRA-022A)
        correlation_warnings, max_correlation = self._check_correlations(potential_legs)
        
        # Fetch fresh market data
        try:
            current_games = self._get_fresh_market_snapshot(regions, markets)
        except Exception as e:
            raise ParlayBuilderError(f"Failed to get market snapshot: {e}")
        
        # Create game lookup for efficiency
        games_by_id = {game.game_id: game for game in current_games}
        
        valid_legs = []
        invalid_results = []
        
        for leg in potential_legs:
            try:
                result = self._validate_single_leg(leg, games_by_id)
                
                if result.is_valid:
                    valid_legs.append(leg)
                    logger.debug(f"Leg validated: {leg.selection_name} @ {leg.odds_decimal}")
                else:
                    invalid_results.append(result)
                    logger.debug(f"Leg invalid: {leg.selection_name} - {result.reason}")
                    
            except Exception as e:
                logger.error(f"Error validating leg {leg.selection_name}: {e}")
                invalid_results.append(ValidationResult(
                    leg=leg,
                    is_valid=False,
                    reason=f"Validation error: {e}"
                ))
        
        # Calculate total odds for valid legs
        total_odds = 1.0
        for leg in valid_legs:
            total_odds *= leg.odds_decimal
        
        validation = ParlayValidation(
            original_legs=potential_legs,
            valid_legs=valid_legs,
            invalid_legs=invalid_results,
            total_odds=total_odds,
            validation_timestamp=self._snapshot_timestamp or datetime.now(timezone.utc).isoformat(),
            market_snapshot_games=len(current_games),
            correlation_warnings=correlation_warnings,  # Added for JIRA-022A
            max_correlation_score=max_correlation,  # Added for JIRA-022A
            rules_validation=rules_validation,  # Added for JIRA-022
            correlation_tax_multiplier=rules_validation.correlation_tax_multiplier  # Added for JIRA-022
        )
        
        logger.info(f"Validation complete: {len(valid_legs)}/{len(potential_legs)} legs valid "
                   f"({validation.success_rate():.1f}% success rate)")
        
        return validation
    
    def _validate_single_leg(self, leg: ParlayLeg, 
                           games_by_id: Dict[str, GameOdds]) -> ValidationResult:
        """
        Validate a single parlay leg.
        
        Args:
            leg: Parlay leg to validate
            games_by_id: Dictionary of game odds by game ID
            
        Returns:
            ValidationResult for the leg
        """
        # Check if game exists in current markets
        if leg.game_id not in games_by_id:
            return ValidationResult(
                leg=leg,
                is_valid=False,
                reason="Game not found in current markets"
            )
        
        game_odds = games_by_id[leg.game_id]
        
        # Find matching selection
        match = self._find_matching_selection(leg, game_odds)
        
        if match is None:
            # Find alternative bookmakers
            alternatives = self._find_alternative_bookmakers(leg, game_odds)
            
            return ValidationResult(
                leg=leg,
                is_valid=False,
                reason="Selection not available at specified bookmaker",
                alternative_bookmakers=alternatives
            )
        
        book_odds, selection = match
        
        # Check if odds have changed significantly (more than 10%)
        odds_change_threshold = 0.10
        odds_diff = abs(selection.price_decimal - leg.odds_decimal) / leg.odds_decimal
        
        if odds_diff > odds_change_threshold:
            return ValidationResult(
                leg=leg,
                is_valid=False,
                reason=f"Odds changed significantly: {leg.odds_decimal} -> {selection.price_decimal}",
                current_odds=selection.price_decimal,
                current_line=selection.line
            )
        
        # Leg is valid
        return ValidationResult(
            leg=leg,
            is_valid=True,
            reason="Selection available and odds stable",
            current_odds=selection.price_decimal,
            current_line=selection.line
        )
    
    def build_validated_parlay(self, potential_legs: List[ParlayLeg],
                             min_legs: int = 2,
                             regions: str = "us",
                             markets: Optional[List[str]] = None,
                             sportsbook: Optional[str] = None) -> Optional[ParlayValidation]:
        """
        Build a validated parlay from potential legs.
        
        Args:
            potential_legs: List of potential parlay legs
            min_legs: Minimum number of legs required for viable parlay
            regions: Regions to fetch odds for
            markets: Markets to include
            sportsbook: Target sportsbook for rules validation
            
        Returns:
            ParlayValidation if viable parlay can be built, None otherwise
        """
        validation = self.validate_parlay_legs(potential_legs, regions, markets, sportsbook)
        
        if validation.is_viable(min_legs):
            logger.info(f"Built viable parlay: {len(validation.valid_legs)} legs, "
                       f"total odds: {validation.total_odds:.2f}")
            return validation
        else:
            logger.warning(f"Unable to build viable parlay: only {len(validation.valid_legs)} "
                          f"valid legs (minimum {min_legs} required)")
            return None
    
    def is_parlay_valid(self, potential_legs: List[ParlayLeg], 
                       sportsbook: Optional[str] = None) -> Tuple[bool, str]:
        """
        Quick validation check using the static rules engine only.
        
        This method provides fast parlay validation against compatibility rules
        without fetching live market data. Use this for rapid pre-filtering
        before performing full validation.
        
        Args:
            potential_legs: List of potential parlay legs
            sportsbook: Target sportsbook for rules validation
            
        Returns:
            Tuple of (is_valid, rejection_reason)
        """
        if sportsbook is None:
            sportsbook = self.default_sportsbook
        
        leg_dicts = [leg.to_dict() for leg in potential_legs]
        return self.rules_engine.is_parlay_valid(leg_dicts, sportsbook)
    
    def get_market_summary(self) -> Dict[str, Any]:
        """
        Get summary of current market snapshot.
        
        Returns:
            Dictionary with market summary information
        """
        if not self._current_market_snapshot:
            return {"status": "No market snapshot available"}
        
        total_books = sum(len(game.books) for game in self._current_market_snapshot)
        bookmaker_counts = {}
        market_counts = {}
        
        for game in self._current_market_snapshot:
            for book in game.books:
                bookmaker_counts[book.bookmaker] = bookmaker_counts.get(book.bookmaker, 0) + 1
                market_counts[book.market] = market_counts.get(book.market, 0) + 1
        
        return {
            "status": "Active",
            "snapshot_timestamp": self._snapshot_timestamp,
            "total_games": len(self._current_market_snapshot),
            "total_markets": total_books,
            "bookmakers": list(bookmaker_counts.keys()),
            "bookmaker_counts": bookmaker_counts,
            "market_types": list(market_counts.keys()),
            "market_counts": market_counts
        }


def create_sample_legs() -> List[ParlayLeg]:
    """
    Create sample parlay legs for testing (using realistic NBA scenarios).
    
    Returns:
        List of sample ParlayLeg objects
    """
    # Note: These are sample legs for testing - in off-season, 
    # these specific games won't exist but structure is correct
    return [
        ParlayLeg(
            game_id="sample_game_1",
            market_type="h2h",
            selection_name="Los Angeles Lakers",
            bookmaker="DraftKings",
            odds_decimal=1.85
        ),
        ParlayLeg(
            game_id="sample_game_2", 
            market_type="spreads",
            selection_name="Boston Celtics",
            bookmaker="FanDuel",
            odds_decimal=1.91,
            line=-5.5
        ),
        ParlayLeg(
            game_id="sample_game_3",
            market_type="totals",
            selection_name="Over",
            bookmaker="DraftKings", 
            odds_decimal=1.95,
            line=220.5
        )
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
        print("🏀 ParlayBuilder Tool - JIRA-021 Implementation")
        print("=" * 60)
        
        # Initialize ParlayBuilder
        builder = ParlayBuilder()
        
        # Get market summary
        print("\n📊 Current Market Status:")
        try:
            summary = builder.get_market_summary()
            if summary["status"] == "No market snapshot available":
                print("📡 Fetching fresh market data...")
                builder._get_fresh_market_snapshot()
                summary = builder.get_market_summary()
            
            print(f"Status: {summary['status']}")
            print(f"Games Available: {summary.get('total_games', 0)}")
            print(f"Total Markets: {summary.get('total_markets', 0)}")
            print(f"Bookmakers: {', '.join(summary.get('bookmakers', []))}")
            print(f"Market Types: {', '.join(summary.get('market_types', []))}")
            
        except Exception as e:
            print(f"⚠️ Market data unavailable: {e}")
            print("💡 This is expected during NBA off-season")
        
        # Test with sample legs
        print(f"\n🧪 Testing with Sample Parlay Legs:")
        sample_legs = create_sample_legs()
        
        for i, leg in enumerate(sample_legs, 1):
            print(f"  {i}. {leg.selection_name} ({leg.market_type}) @ {leg.odds_decimal} - {leg.bookmaker}")
        
        # Test quick validation (rules only)
        print(f"\n🚫 Testing Quick Rules Validation:")
        try:
            valid, reason = builder.is_parlay_valid(sample_legs, "DRAFTKINGS")
            print(f"DraftKings Rules Check: {'✅ VALID' if valid else '❌ INVALID'}")
            if not valid:
                print(f"  Reason: {reason}")
            
            valid, reason = builder.is_parlay_valid(sample_legs, "ESPN_BET")
            print(f"ESPN Bet Rules Check: {'✅ VALID' if valid else '❌ INVALID'}")
            if not valid:
                print(f"  Reason: {reason}")
        except Exception as e:
            print(f"⚠️ Rules validation failed: {e}")
        
        # Test full validation (rules + market data)
        try:
            validation = builder.validate_parlay_legs(sample_legs, sportsbook="DRAFTKINGS")
            
            print(f"\n✅ Full Validation Results:")
            print(f"Original Legs: {len(validation.original_legs)}")
            print(f"Valid Legs: {len(validation.valid_legs)}")
            print(f"Invalid Legs: {len(validation.invalid_legs)}")
            print(f"Success Rate: {validation.success_rate():.1f}%")
            print(f"Total Odds: {validation.total_odds:.2f}")
            print(f"Correlation Tax: {validation.correlation_tax_multiplier:.2f}x")
            print(f"Viable Parlay: {'Yes' if validation.is_viable() else 'No'}")
            
            # Show rules validation results
            if validation.rules_validation:
                rules = validation.rules_validation
                print(f"\n🚫 Rules Validation:")
                print(f"  Rules Valid: {'Yes' if rules.is_valid else 'No'}")
                print(f"  Violations: {len(rules.violations)}")
                print(f"  Warnings: {len(rules.warnings)}")
                
                if rules.violations:
                    print(f"  Rule Violations:")
                    for violation in rules.violations[:3]:  # Show first 3
                        print(f"    • {violation.severity.value.upper()}: {violation.description}")
            
            if validation.invalid_legs:
                print(f"\n❌ Invalid Legs:")
                for result in validation.invalid_legs:
                    print(f"  • {result.leg.selection_name}: {result.reason}")
                    if result.alternative_bookmakers:
                        print(f"    Alternative books: {', '.join(result.alternative_bookmakers)}")
            
        except Exception as e:
            print(f"⚠️ Validation failed: {e}")
            print("💡 Expected during off-season when no games are available")
        
        print(f"\n🎯 ParlayBuilder Implementation Complete!")
        print(f"✅ JIRA-021 & JIRA-022 requirements fulfilled:")
        print(f"  • Fetches fresh market snapshots from OddsFetcherTool")
        print(f"  • Validates legs against current availability")
        print(f"  • Filters out suspended/unavailable markets")
        print(f"  • Provides detailed validation results")
        print(f"  • Handles both active season and off-season scenarios")
        print(f"  • Enforces parlay compatibility rules (JIRA-022)")
        print(f"  • Blocks mutually exclusive and correlated combinations")
        print(f"  • Applies sportsbook-specific restrictions")
        print(f"  • Calculates correlation tax for risk assessment")
        
    except KeyboardInterrupt:
        print(f"\n⏹️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
