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

# Import parlay rules engine (JIRA-022) with error handling
try:
    from tools.parlay_rules_engine import ParlayRulesEngine, ValidationResult as RulesValidationResult
except ImportError:
    try:
        from tools.parlay_rules_engine import ParlayRulesEngine
        # Create a basic ValidationResult class if not available
        class RulesValidationResult:
            def __init__(self, is_valid=True, violations=None):
                self.is_valid = is_valid
                self.violations = violations or []
    except ImportError:
        ParlayRulesEngine = None
        RulesValidationResult = None

# Import confidence classifier (JIRA-019) - optional dependency
try:
    from tools.parlay_confidence_predictor import ParlayConfidencePredictor, ParlayConfidenceIntegration
    from tools.parlay_strategist_agent import EnhancedParlayStrategistAgent
    HAS_CONFIDENCE_CLASSIFIER = True
except ImportError:
    HAS_CONFIDENCE_CLASSIFIER = False
    logger.warning("Confidence classifier not available. Install transformers for confidence prediction.")

# Import correlation model (optional dependency)
try:
    from tools.correlation_model import DynamicCorrelationModel, BetNode
    HAS_CORRELATION_MODEL = True
except ImportError:
    HAS_CORRELATION_MODEL = False
    logger.warning("Correlation model not available. Install PyTorch Geometric for correlation detection.")

# Import prop trainer (ML-PROP-001)
try:
    from ml.ml_prop_trainer import HistoricalPropTrainer
    HAS_PROP_TRAINER = True
except ImportError:
    HAS_PROP_TRAINER = False
    logger.warning("Prop trainer not available.")

# Import parlay optimizer (ML-OPTIMIZER-001)
try:
    from ml.ml_parlay_optimizer import ParlayOptimizer, OptimizedParlay
    HAS_PARLAY_OPTIMIZER = True
except ImportError:
    HAS_PARLAY_OPTIMIZER = False

# Import Q-Learning agent (ML-QLEARNING-001) - experimental
try:
    from ml.ml_qlearning_agent import QLearningParlayAgent, QLearningConfig
    HAS_QLEARNING_AGENT = True
except ImportError:
    HAS_QLEARNING_AGENT = False
    QLearningParlayAgent = QLearningConfig = None
    logger.warning("Parlay optimizer not available. Install PuLP for optimization features.")

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
    confidence_analysis: Optional[Dict[str, Any]] = None  # Added for JIRA-019
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
        if ParlayRulesEngine:
            try:
                self.rules_engine = ParlayRulesEngine()
            except Exception as e:
                logger.warning(f"Failed to initialize ParlayRulesEngine: {e}")
                self.rules_engine = None
        else:
            self.rules_engine = None
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
        
        # Initialize confidence classifier (JIRA-019)
        self.confidence_predictor = None
        self.parlay_strategist = None
        if HAS_CONFIDENCE_CLASSIFIER:
            try:
                self.confidence_predictor = ParlayConfidencePredictor()
                self.parlay_strategist = EnhancedParlayStrategistAgent(use_injury_classifier=False)
                logger.info("Confidence classifier and strategist initialized")
            except Exception as e:
                logger.warning(f"Could not initialize confidence classifier: {e}")
        
        # Initialize prop trainers for EV-based ranking (ML-PROP-001)
        self.prop_trainers = {}
        if HAS_PROP_TRAINER:
            try:
                # Determine sport from sport_key
                if "basketball" in sport_key.lower() or "nba" in sport_key.lower():
                    self.prop_trainers['nba'] = HistoricalPropTrainer("nba")
                    try:
                        self.prop_trainers['nba'].load_model()
                        logger.info("NBA prop trainer loaded for EV-based ranking")
                    except FileNotFoundError:
                        logger.info("NBA prop model not found - train with ml_prop_trainer.py first")
                        
                elif "football" in sport_key.lower() or "nfl" in sport_key.lower():
                    self.prop_trainers['nfl'] = HistoricalPropTrainer("nfl")
                    try:
                        self.prop_trainers['nfl'].load_model()
                        logger.info("NFL prop trainer loaded for EV-based ranking")
                    except FileNotFoundError:
                        logger.info("NFL prop model not found - train with ml_prop_trainer.py first")
                        
                else:
                    # Load both for multi-sport support
                    for sport in ['nba', 'nfl']:
                        self.prop_trainers[sport] = HistoricalPropTrainer(sport)
                        try:
                            self.prop_trainers[sport].load_model()
                            logger.info(f"{sport.upper()} prop trainer loaded")
                        except FileNotFoundError:
                            logger.info(f"{sport.upper()} prop model not found - train first")
                            
            except Exception as e:
                logger.warning(f"Failed to initialize prop trainers: {e}")
                self.prop_trainers = {}
        
        # Initialize parlay optimizer (ML-OPTIMIZER-001)
        self.parlay_optimizer = None
        if HAS_PARLAY_OPTIMIZER:
            try:
                self.parlay_optimizer = ParlayOptimizer(
                    max_legs=5,
                    max_correlation_threshold=0.3,
                    min_ev_threshold=0.02
                )
                logger.info("Parlay optimizer initialized for LP-based optimization")
            except Exception as e:
                logger.warning(f"Failed to initialize parlay optimizer: {e}")
        else:
            logger.info("Parlay optimizer not available - install PuLP for optimization features")
        
        # Initialize Q-Learning agent (ML-QLEARNING-001) - experimental
        self.qlearning_agent = None
        self.qlearning_enabled = False
        if HAS_QLEARNING_AGENT:
            try:
                config = QLearningConfig()
                self.qlearning_agent = QLearningParlayAgent(config)
                
                # Try to load pre-trained model
                if self.qlearning_agent.load_model():
                    self.qlearning_enabled = True
                    logger.info("Q-Learning parlay agent loaded successfully")
                else:
                    logger.info("Q-Learning agent initialized but not trained - train with ml_qlearning_agent.py")
                    
            except Exception as e:
                logger.warning(f"Failed to initialize Q-Learning agent: {e}")
        else:
            logger.info("Q-Learning agent not available - install gymnasium and torch for RL features")
        
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
    
    def build_qlearning_parlay(self, candidate_legs: List[Dict[str, Any]], 
                              max_legs: int = 5, 
                              experimental: bool = False) -> Optional[List[Dict[str, Any]]]:
        """
        Build parlay using Q-Learning reinforcement learning agent.
        
        This experimental method uses a trained Deep Q-Network to select optimal
        parlay combinations based on Expected Value, correlation patterns, and
        learned strategies from historical data simulation.
        
        Args:
            candidate_legs: List of candidate leg dictionaries with odds, EV, etc.
            max_legs: Maximum number of legs in parlay (default: 5)
            experimental: Flag to enable experimental Q-Learning features
            
        Returns:
            List of selected leg dictionaries or None if agent unavailable
        """
        if not experimental:
            logger.info("Q-Learning parlay building requires experimental=True flag")
            return None
        
        if not self.qlearning_enabled or not self.qlearning_agent:
            logger.warning("Q-Learning agent not available or not trained")
            return None
        
        if not candidate_legs:
            logger.warning("No candidate legs provided for Q-Learning agent")
            return []
        
        try:
            logger.info(f"🤖 Building Q-Learning parlay from {len(candidate_legs)} candidates...")
            
            # Ensure candidate legs have required fields
            enriched_legs = []
            for i, leg in enumerate(candidate_legs):
                enriched_leg = {
                    'leg_id': leg.get('leg_id', f'qlearning_leg_{i}'),
                    'odds': leg.get('odds', 0.0),
                    'expected_value': leg.get('expected_value', 0.0),
                    'market_type': leg.get('market_type', 'unknown'),
                    'player_name': leg.get('player_name', ''),
                    'sport': leg.get('sport', 'nba'),
                    'selection_name': leg.get('selection_name', ''),
                    'game_id': leg.get('game_id', ''),
                    'sportsbook': leg.get('sportsbook', self.default_sportsbook)
                }
                enriched_legs.append(enriched_leg)
            
            # Use Q-Learning agent to infer optimal parlay
            selected_legs = self.qlearning_agent.infer_parlay(enriched_legs, max_legs)
            
            if selected_legs:
                logger.info(f"✅ Q-Learning agent selected {len(selected_legs)} legs")
                
                # Log selection reasoning
                total_ev = sum(leg.get('expected_value', 0) for leg in selected_legs)
                avg_odds = sum(leg.get('odds', 0) for leg in selected_legs) / len(selected_legs)
                
                logger.info(f"  • Total Expected Value: {total_ev:.3f}")
                logger.info(f"  • Average Odds: {avg_odds:.1f}")
                logger.info(f"  • Selected markets: {[leg.get('market_type') for leg in selected_legs]}")
                
                return selected_legs
            else:
                logger.warning("Q-Learning agent returned no selections")
                return []
                
        except Exception as e:
            logger.error(f"Error in Q-Learning parlay building: {e}")
            return None
    
    def compare_parlay_strategies(self, candidate_legs: List[Dict[str, Any]], 
                                max_legs: int = 5) -> Dict[str, Any]:
        """
        Compare different parlay building strategies including Q-Learning.
        
        Args:
            candidate_legs: Candidate legs for comparison
            max_legs: Maximum legs per parlay
            
        Returns:
            Dictionary with strategy comparison results
        """
        strategies = {}
        
        # Strategy 1: Q-Learning (if available)
        if self.qlearning_enabled:
            try:
                qlearning_parlay = self.build_qlearning_parlay(
                    candidate_legs, max_legs, experimental=True
                )
                if qlearning_parlay:
                    strategies['qlearning'] = {
                        'legs': qlearning_parlay,
                        'count': len(qlearning_parlay),
                        'total_ev': sum(leg.get('expected_value', 0) for leg in qlearning_parlay),
                        'method': 'Reinforcement Learning (DQN)'
                    }
            except Exception as e:
                logger.warning(f"Q-Learning strategy failed: {e}")
        
        # Strategy 2: Optimizer (if available)
        if self.parlay_optimizer:
            try:
                optimizer_parlays = self.optimize_parlays(candidate_legs, 1, max_legs)
                if optimizer_parlays:
                    strategies['optimizer'] = {
                        'legs': optimizer_parlays[0].get('legs', []),
                        'count': len(optimizer_parlays[0].get('legs', [])),
                        'total_ev': optimizer_parlays[0].get('total_ev', 0),
                        'method': 'Linear Programming Optimization'
                    }
            except Exception as e:
                logger.warning(f"Optimizer strategy failed: {e}")
        
        # Strategy 3: Random baseline
        import random
        random_selection = random.sample(
            candidate_legs, 
            min(random.randint(2, max_legs), len(candidate_legs))
        )
        strategies['random'] = {
            'legs': random_selection,
            'count': len(random_selection),
            'total_ev': sum(leg.get('expected_value', 0) for leg in random_selection),
            'method': 'Random Selection'
        }
        
        # Strategy 4: Highest EV selection
        sorted_by_ev = sorted(candidate_legs, 
                             key=lambda x: x.get('expected_value', 0), 
                             reverse=True)
        ev_selection = sorted_by_ev[:min(max_legs, len(sorted_by_ev))]
        strategies['highest_ev'] = {
            'legs': ev_selection,
            'count': len(ev_selection),
            'total_ev': sum(leg.get('expected_value', 0) for leg in ev_selection),
            'method': 'Highest Expected Value'
        }
        
        return {
            'strategies': strategies,
            'comparison_summary': {
                'best_ev_strategy': max(strategies.keys(), 
                                       key=lambda k: strategies[k]['total_ev']),
                'strategy_count': len(strategies),
                'qlearning_available': self.qlearning_enabled
            }
        }
    
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
    
    def generate_ai_parlay_recommendation(self, target_legs: int = 3,
                                        min_total_odds: float = 3.0,
                                        min_confidence: float = 0.6,
                                        regions: str = "us",
                                        markets: Optional[List[str]] = None,
                                        sportsbook: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Generate AI-powered parlay recommendation with confidence analysis (JIRA-019).
        
        Combines the enhanced strategist agent with confidence classification
        to produce high-quality parlay recommendations.
        
        Args:
            target_legs: Number of legs to include in parlay
            min_total_odds: Minimum acceptable total odds
            min_confidence: Minimum confidence score threshold
            regions: Regions to fetch odds for
            markets: Markets to include in analysis
            sportsbook: Target sportsbook for validation
            
        Returns:
            AI-generated parlay recommendation with confidence analysis or None
        """
        if not HAS_CONFIDENCE_CLASSIFIER:
            logger.warning("Confidence classifier not available - cannot generate AI recommendations")
            return None
        
        if self.parlay_strategist is None or self.confidence_predictor is None:
            logger.warning("AI components not initialized")
            return None
        
        try:
            # Get fresh market data
            current_games = self._get_fresh_market_snapshot(regions, markets)
            
            if not current_games:
                logger.warning("No games available for AI recommendation")
                return None
            
            # Generate parlay recommendation with reasoning
            recommendation = self.parlay_strategist.generate_parlay_with_reasoning(
                current_games=current_games,
                target_legs=target_legs,
                min_total_odds=min_total_odds
            )
            
            if not recommendation:
                logger.info("No viable parlay recommendation generated by strategist")
                return None
            
            # Analyze confidence
            confidence_analysis = self.confidence_predictor.analyze_parlay_reasoning(
                recommendation.reasoning.reasoning_text
            )
            
            # Check confidence threshold
            confidence_score = confidence_analysis["confidence_prediction"]["max_confidence_score"]
            if confidence_score < min_confidence:
                logger.info(f"Recommendation confidence {confidence_score:.3f} below threshold {min_confidence}")
                return None
            
            # Convert strategist recommendation to parlay legs
            parlay_legs = []
            for leg_data in recommendation.legs:
                leg = ParlayLeg(
                    game_id=leg_data['game_id'],
                    market_type=leg_data['market_type'],
                    selection_name=leg_data['selection_name'],
                    bookmaker=leg_data['bookmaker'],
                    odds_decimal=leg_data['odds_decimal'],
                    line=leg_data.get('line')
                )
                parlay_legs.append(leg)
            
            # Validate using standard pipeline
            validation = self.validate_parlay_legs(
                parlay_legs,
                regions=regions,
                markets=markets,
                sportsbook=sportsbook
            )
            
            # Add confidence analysis to validation
            validation.confidence_analysis = confidence_analysis
            
            # Create enhanced recommendation
            ai_recommendation = {
                "ai_generated": True,
                "strategist_recommendation": recommendation,
                "validation_results": validation,
                "confidence_analysis": confidence_analysis,
                "total_odds": validation.total_odds,
                "confidence_score": confidence_score,
                "bet_recommendation": confidence_analysis["recommendation"],
                "model_certainty": confidence_analysis["confidence_prediction"]["prediction_certainty"],
                "reasoning_text": recommendation.reasoning.reasoning_text,
                "expected_value": recommendation.expected_value,
                "kelly_percentage": recommendation.kelly_percentage,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Generated AI parlay recommendation with {len(validation.valid_legs)} valid legs, "
                       f"confidence: {confidence_score:.3f}")
            
            return ai_recommendation
            
        except Exception as e:
            logger.error(f"Failed to generate AI parlay recommendation: {e}")
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
    
    def rank_legs_by_prop_ev(self, potential_legs: List[Dict[str, Any]], 
                           top_k: int = 10) -> List[Tuple[Dict[str, Any], float, float]]:
        """
        Rank parlay legs by Expected Value using trained prop prediction models.
        
        This method uses sport-specific HistoricalPropTrainer models to predict
        the probability of each leg hitting, then calculates Expected Value
        based on the bookmaker odds vs. predicted probability.
        
        Args:
            potential_legs: List of leg dictionaries with features
            top_k: Number of top legs to return
            
        Returns:
            List of tuples: (leg_dict, predicted_probability, expected_value)
            Sorted by Expected Value (highest first)
        """
        if not self.prop_trainers:
            logger.warning("No prop trainers available for EV ranking")
            return [(leg, 0.5, 0.0) for leg in potential_legs[:top_k]]
        
        ranked_legs = []
        
        for leg in potential_legs:
            try:
                # Determine sport from leg data
                sport = self._determine_leg_sport(leg)
                
                if sport not in self.prop_trainers:
                    logger.warning(f"No trainer available for sport: {sport}")
                    continue
                
                # Extract features for prediction
                features = self._extract_prop_features(leg, sport)
                
                # Get prediction probability
                hit_probability = self.prop_trainers[sport].predict(features)
                
                # Calculate Expected Value
                odds = leg.get('odds', 2.0)
                if isinstance(odds, str):
                    # Handle American odds format
                    odds = self._convert_american_to_decimal(odds)
                
                # EV = (Probability of Win * Payout) - (Probability of Loss * Stake)
                payout = odds - 1  # Profit on $1 bet
                expected_value = (hit_probability * payout) - ((1 - hit_probability) * 1)
                
                ranked_legs.append((leg, hit_probability, expected_value))
                
            except Exception as e:
                logger.warning(f"Error calculating EV for leg {leg.get('selection', 'unknown')}: {e}")
                ranked_legs.append((leg, 0.5, 0.0))
        
        # Sort by Expected Value (descending)
        ranked_legs.sort(key=lambda x: x[2], reverse=True)
        
        logger.info(f"Ranked {len(ranked_legs)} legs by prop EV, returning top {top_k}")
        
        return ranked_legs[:top_k]
    
    def _determine_leg_sport(self, leg: Dict[str, Any]) -> str:
        """Determine sport from leg data."""
        # Try to infer from sport_key or game info
        if 'sport_key' in leg:
            if 'basketball' in leg['sport_key'].lower() or 'nba' in leg['sport_key'].lower():
                return 'nba'
            elif 'football' in leg['sport_key'].lower() or 'nfl' in leg['sport_key'].lower():
                return 'nfl'
        
        # Try to infer from game or team names
        game = leg.get('game', '').lower()
        if any(team in game for team in ['lakers', 'celtics', 'warriors', 'bulls', 'knicks']):
            return 'nba'
        elif any(team in game for team in ['chiefs', 'cowboys', 'patriots', 'packers', 'steelers']):
            return 'nfl'
        
        # Default based on sport_key of ParlayBuilder
        if 'basketball' in self.sport_key.lower() or 'nba' in self.sport_key.lower():
            return 'nba'
        else:
            return 'nfl'
    
    def _extract_prop_features(self, leg: Dict[str, Any], sport: str) -> Dict[str, Any]:
        """Extract features from leg data for prop prediction."""
        features = {}
        
        if sport == 'nba':
            # NBA-specific feature extraction
            features.update({
                'points_scored': leg.get('projected_points', 20.0),
                'rebounds': leg.get('projected_rebounds', 5.0),
                'assists': leg.get('projected_assists', 3.0),
                'opponent_def_rating': leg.get('opponent_def_rating', 110.0),
                'minutes_played': leg.get('projected_minutes', 30.0),
                'field_goal_attempts': leg.get('projected_fga', 15.0),
                'three_point_attempts': leg.get('projected_3pa', 5.0),
                'free_throw_attempts': leg.get('projected_fta', 3.0),
                'turnovers': leg.get('projected_turnovers', 2.0),
                'home_away': leg.get('home_away', 'home'),
                'days_rest': leg.get('days_rest', 1),
                'season_avg_points': leg.get('season_avg_points', 20.0),
                'last_5_avg_points': leg.get('last_5_avg_points', 20.0),
                'opponent_points_allowed': leg.get('opponent_points_allowed', 110.0),
                'pace': leg.get('pace', 100.0),
                'usage_rate': leg.get('usage_rate', 25.0)
            })
        
        else:  # NFL
            # NFL-specific feature extraction
            features.update({
                'passing_yards': leg.get('projected_passing_yards', 0.0),
                'rushing_yards': leg.get('projected_rushing_yards', 0.0),
                'receiving_yards': leg.get('projected_receiving_yards', 0.0),
                'passing_touchdowns': leg.get('projected_passing_tds', 0.0),
                'rushing_touchdowns': leg.get('projected_rushing_tds', 0.0),
                'receptions': leg.get('projected_receptions', 0.0),
                'targets': leg.get('projected_targets', 0.0),
                'opponent_def_rating': leg.get('opponent_def_rating', 100.0),
                'weather_conditions': leg.get('weather', 'clear'),
                'dome_game': leg.get('dome_game', 0),
                'position': leg.get('position', 'RB'),
                'home_away': leg.get('home_away', 'home'),
                'division_game': leg.get('division_game', 0),
                'season_avg_yards': leg.get('season_avg_yards', 50.0),
                'last_4_avg_yards': leg.get('last_4_avg_yards', 50.0),
                'opponent_yards_allowed': leg.get('opponent_yards_allowed', 350.0),
                'snap_count': leg.get('projected_snaps', 50),
                'red_zone_targets': leg.get('projected_rz_targets', 1)
            })
        
        return features
    
    def _convert_american_to_decimal(self, american_odds: str) -> float:
        """Convert American odds format to decimal."""
        try:
            odds_int = int(american_odds.replace('+', ''))
            if odds_int > 0:
                return (odds_int / 100) + 1
            else:
                return (100 / abs(odds_int)) + 1
        except:
            return 2.0  # Default odds
    
    def optimize_parlays(self, candidate_legs: List[Dict[str, Any]], 
                        num_solutions: int = 3, 
                        max_legs: int = None,
                        max_correlation: float = None) -> List[Dict[str, Any]]:
        """
        Optimize parlay construction using linear programming.
        
        This method uses the integrated ParlayOptimizer to find optimal combinations
        of legs that maximize Expected Value while respecting correlation constraints.
        
        Args:
            candidate_legs: List of leg dictionaries with required fields
            num_solutions: Number of optimized solutions to return
            max_legs: Override default max legs per parlay
            max_correlation: Override default max correlation threshold
            
        Returns:
            List of optimized parlay dictionaries
        """
        if not self.parlay_optimizer:
            logger.warning("Parlay optimizer not available - install PuLP for optimization")
            return []
        
        if not candidate_legs:
            logger.warning("No candidate legs provided for optimization")
            return []
        
        try:
            # Update optimizer parameters if provided
            if max_legs is not None:
                self.parlay_optimizer.max_legs = max_legs
            if max_correlation is not None:
                self.parlay_optimizer.max_correlation_threshold = max_correlation
            
            # Enhance candidate legs with prop predictions if available
            enhanced_legs = self._enhance_legs_with_predictions(candidate_legs)
            
            # Run optimization
            logger.info(f"Running LP optimization on {len(enhanced_legs)} candidate legs")
            optimized_parlays = self.parlay_optimizer.optimize_parlays(
                enhanced_legs, num_solutions
            )
            
            # Convert to dictionary format for API compatibility
            result_parlays = []
            for parlay in optimized_parlays:
                parlay_dict = parlay.to_dict()
                
                # Add ParlayBuilder-specific enhancements
                parlay_dict['builder_validation'] = self._validate_optimized_parlay(parlay)
                parlay_dict['market_availability'] = self._check_market_availability(parlay.legs)
                
                result_parlays.append(parlay_dict)
            
            logger.info(f"Generated {len(result_parlays)} optimized parlays with LP")
            return result_parlays
            
        except Exception as e:
            logger.error(f"Parlay optimization failed: {e}")
            return []
    
    def _enhance_legs_with_predictions(self, candidate_legs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enhance candidate legs with ML predictions if prop trainers available."""
        enhanced_legs = []
        
        for leg in candidate_legs:
            enhanced_leg = leg.copy()
            
            # Add ML prediction if not present and prop trainer available
            if 'predicted_prob' not in enhanced_leg:
                sport = enhanced_leg.get('sport', 'nba').lower()
                if sport in self.prop_trainers:
                    try:
                        # Extract features and predict
                        features = self._extract_prop_features_from_leg(enhanced_leg, sport)
                        predicted_prob = self.prop_trainers[sport].predict(features)
                        enhanced_leg['predicted_prob'] = predicted_prob
                        
                        logger.debug(f"Enhanced {leg.get('leg_id', 'unknown')} with ML prediction: {predicted_prob:.3f}")
                        
                    except Exception as e:
                        logger.warning(f"Failed to enhance leg with ML prediction: {e}")
                        enhanced_leg['predicted_prob'] = 0.5  # Default 50%
                else:
                    enhanced_leg['predicted_prob'] = 0.5  # Default 50%
            
            # Ensure all required fields are present
            enhanced_leg.setdefault('sport', 'nba')
            enhanced_leg.setdefault('market_type', 'points')
            enhanced_leg.setdefault('player_name', 'Unknown Player')
            enhanced_leg.setdefault('line_value', 0.0)
            enhanced_leg.setdefault('game_id', 'unknown_game')
            enhanced_leg.setdefault('bookmaker', 'draftkings')
            
            enhanced_legs.append(enhanced_leg)
        
        return enhanced_legs
    
    def _extract_prop_features_from_leg(self, leg: Dict[str, Any], sport: str) -> Dict[str, Any]:
        """Extract features from leg dictionary for prop prediction."""
        features = {}
        
        # Get common features
        market_type = leg.get('market_type', '').lower()
        line_value = leg.get('line_value', 0)
        
        if sport == 'nba':
            # NBA-specific feature extraction
            features.update({
                'points_scored': line_value if 'points' in market_type else 20.0,
                'rebounds': line_value if 'rebound' in market_type else 5.0,
                'assists': line_value if 'assist' in market_type else 3.0,
                'opponent_def_rating': leg.get('opponent_def_rating', 110.0),
                'minutes_played': leg.get('projected_minutes', 30.0),
                'field_goal_attempts': leg.get('projected_fga', 15.0),
                'three_point_attempts': line_value if 'three' in market_type else 5.0,
                'free_throw_attempts': leg.get('projected_fta', 3.0),
                'turnovers': leg.get('projected_turnovers', 2.0),
                'home_away': leg.get('home_away', 'home'),
                'days_rest': leg.get('days_rest', 1),
                'season_avg_points': leg.get('season_avg_points', line_value if 'points' in market_type else 20.0),
                'last_5_avg_points': leg.get('last_5_avg_points', line_value if 'points' in market_type else 20.0),
                'opponent_points_allowed': leg.get('opponent_points_allowed', 110.0),
                'pace': leg.get('pace', 100.0),
                'usage_rate': leg.get('usage_rate', 25.0)
            })
        
        else:  # NFL
            # NFL-specific feature extraction
            features.update({
                'passing_yards': line_value if 'passing' in market_type else 0.0,
                'rushing_yards': line_value if 'rushing' in market_type else 0.0,
                'receiving_yards': line_value if 'receiving' in market_type else 0.0,
                'passing_touchdowns': line_value if 'td' in market_type and 'passing' in market_type else 0.0,
                'rushing_touchdowns': line_value if 'td' in market_type and 'rushing' in market_type else 0.0,
                'receptions': line_value if 'reception' in market_type else 0.0,
                'targets': leg.get('projected_targets', 0.0),
                'opponent_def_rating': leg.get('opponent_def_rating', 100.0),
                'weather_conditions': leg.get('weather', 'clear'),
                'dome_game': leg.get('dome_game', 0),
                'position': leg.get('position', 'RB'),
                'home_away': leg.get('home_away', 'home'),
                'division_game': leg.get('division_game', 0),
                'season_avg_yards': leg.get('season_avg_yards', line_value),
                'last_4_avg_yards': leg.get('last_4_avg_yards', line_value),
                'opponent_yards_allowed': leg.get('opponent_yards_allowed', 350.0),
                'snap_count': leg.get('projected_snaps', 50),
                'red_zone_targets': leg.get('projected_rz_targets', 1)
            })
        
        return features
    
    def _validate_optimized_parlay(self, parlay) -> Dict[str, Any]:
        """Validate optimized parlay using existing rules engine."""
        if not self.rules_engine:
            return {"valid": True, "warnings": ["Rules engine not available"]}
        
        try:
            # Convert OptimizedParlay legs to format expected by rules engine
            leg_dicts = []
            for leg in parlay.legs:
                leg_dict = {
                    'game_id': leg.game_id,
                    'market_type': leg.market_type,
                    'selection_name': f"{leg.player_name} {leg.market_type}",
                    'bookmaker': leg.bookmaker,
                    'odds_decimal': leg.odds,
                    'line': leg.line_value
                }
                leg_dicts.append(leg_dict)
            
            # Validate using rules engine (determine sport from first leg)
            sport = parlay.legs[0].sport if parlay.legs else 'nba'
            is_valid, rejection_reason = self.rules_engine.is_parlay_valid(leg_dicts, sport)
            
            return {
                "valid": is_valid,
                "rejection_reason": rejection_reason if not is_valid else None,
                "warnings": []
            }
            
        except Exception as e:
            logger.warning(f"Parlay validation failed: {e}")
            return {"valid": False, "warnings": [f"Validation error: {e}"]}
    
    def _check_market_availability(self, legs: List) -> Dict[str, Any]:
        """Check if markets for optimized legs are currently available."""
        try:
            if not self._current_market_snapshot:
                self._get_fresh_market_snapshot()
            
            available_markets = set()
            for game in self._current_market_snapshot or []:
                for book in game.books:
                    available_markets.add(f"{game.sport_key}_{book.market}")
            
            leg_availability = {}
            unavailable_count = 0
            
            for leg in legs:
                market_key = f"{leg.sport}_{leg.market_type}"
                is_available = market_key in available_markets
                leg_availability[leg.leg_id] = is_available
                if not is_available:
                    unavailable_count += 1
            
            return {
                "all_available": unavailable_count == 0,
                "unavailable_count": unavailable_count,
                "leg_availability": leg_availability,
                "warning": f"{unavailable_count} legs may not be available" if unavailable_count > 0 else None
            }
            
        except Exception as e:
            logger.warning(f"Market availability check failed: {e}")
            return {"all_available": False, "warning": "Could not verify market availability"}


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

        # Test AI-powered parlay generation (JIRA-019)
        print(f"\n🤖 Testing AI-Powered Parlay Generation (JIRA-019)...")
        if HAS_CONFIDENCE_CLASSIFIER:
            try:
                ai_recommendation = builder.generate_ai_parlay_recommendation(
                    target_legs=2,
                    min_total_odds=2.5,
                    min_confidence=0.5
                )
                
                if ai_recommendation:
                    print(f"🎯 AI Generated Parlay:")
                    print(f"  Confidence Score: {ai_recommendation['confidence_score']:.3f}")
                    print(f"  Model Certainty: {ai_recommendation['model_certainty']:.3f}")
                    print(f"  Bet Recommendation: {ai_recommendation['bet_recommendation']}")
                    print(f"  Total Odds: {ai_recommendation['total_odds']:.2f}")
                    print(f"  Expected Value: {ai_recommendation.get('expected_value', 'N/A')}")
                    print(f"  Kelly %: {ai_recommendation.get('kelly_percentage', 'N/A')}")
                    
                    print(f"\n📝 AI Reasoning (excerpt):")
                    reasoning_excerpt = ai_recommendation['reasoning_text'][:300] + "..."
                    print(f"  {reasoning_excerpt}")
                else:
                    print(f"⚠️ No AI recommendation generated (no suitable opportunities found)")
                    
            except Exception as e:
                print(f"⚠️ AI recommendation failed: {e}")
        else:
            print(f"⚠️ AI features not available (install transformers and torch)")
        
        print(f"\n🎯 ParlayBuilder Implementation Complete!")
        print(f"✅ JIRA-021, JIRA-022 & JIRA-019 requirements fulfilled:")
        print(f"  • Fetches fresh market snapshots from OddsFetcherTool")
        print(f"  • Validates legs against current availability")
        print(f"  • Filters out suspended/unavailable markets")
        print(f"  • Provides detailed validation results")
        print(f"  • Handles both active season and off-season scenarios")
        print(f"  • Enforces parlay compatibility rules (JIRA-022)")
        print(f"  • Blocks mutually exclusive and correlated combinations")
        print(f"  • Applies sportsbook-specific restrictions")
        print(f"  • Calculates correlation tax for risk assessment")
        print(f"  • AI-powered parlay generation with confidence analysis (JIRA-019)")
        print(f"  • RoBERTa-based confidence prediction and reasoning")
        
    except KeyboardInterrupt:
        print(f"\n⏹️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
