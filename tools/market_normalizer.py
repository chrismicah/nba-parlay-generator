#!/usr/bin/env python3
"""
MarketNormalizer - JIRA-050

Normalizes team names and market types across different sports and sportsbooks.
Handles inconsistencies in naming conventions between data sources.

Key Features:
- NFL team name standardization (e.g., "Kansas City Chiefs" → "KC")
- NBA team name standardization (e.g., "Los Angeles Lakers" → "LAL")
- Market type normalization (e.g., "Moneyline" → "ML", "Point Spread" → "PS")
- Sportsbook-specific naming conventions
- Fuzzy matching for partial team names
"""

import re
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum


class Sport(Enum):
    """Supported sports."""
    NBA = "nba"
    NFL = "nfl"


@dataclass
class TeamMapping:
    """Team name mapping with multiple variations."""
    standard_code: str
    full_name: str
    city: str
    nickname: str
    aliases: List[str]
    sport: Sport


@dataclass
class MarketMapping:
    """Market type mapping with sportsbook variations."""
    standard_code: str
    full_name: str
    aliases: List[str]
    sportsbook_variants: Dict[str, str]


class MarketNormalizer:
    """
    Normalizes team names and market types for consistent arbitrage detection.
    """
    
    def __init__(self):
        """Initialize the normalizer with team and market mappings."""
        self.nfl_teams = self._initialize_nfl_teams()
        self.nba_teams = self._initialize_nba_teams()
        self.market_types = self._initialize_market_types()
        
        # Create lookup dictionaries for fast matching
        self.team_lookup = self._build_team_lookup()
        self.market_lookup = self._build_market_lookup()
    
    def _initialize_nfl_teams(self) -> Dict[str, TeamMapping]:
        """Initialize NFL team mappings."""
        teams = {
            "KC": TeamMapping("KC", "Kansas City Chiefs", "Kansas City", "Chiefs", 
                             ["Chiefs", "KC Chiefs", "Kansas City", "KCC"], Sport.NFL),
            "BUF": TeamMapping("BUF", "Buffalo Bills", "Buffalo", "Bills",
                              ["Bills", "Buffalo", "BUF"], Sport.NFL),
            "DAL": TeamMapping("DAL", "Dallas Cowboys", "Dallas", "Cowboys",
                              ["Cowboys", "Dallas", "America's Team"], Sport.NFL),
            "NYG": TeamMapping("NYG", "New York Giants", "New York", "Giants",
                              ["Giants", "NY Giants", "New York Giants"], Sport.NFL),
            "NE": TeamMapping("NE", "New England Patriots", "New England", "Patriots",
                             ["Patriots", "Pats", "New England", "NE"], Sport.NFL),
            "MIA": TeamMapping("MIA", "Miami Dolphins", "Miami", "Dolphins",
                              ["Dolphins", "Miami", "Fins"], Sport.NFL),
            "NYJ": TeamMapping("NYJ", "New York Jets", "New York", "Jets",
                              ["Jets", "NY Jets", "New York Jets"], Sport.NFL),
            "BAL": TeamMapping("BAL", "Baltimore Ravens", "Baltimore", "Ravens",
                              ["Ravens", "Baltimore", "BAL"], Sport.NFL),
            "PIT": TeamMapping("PIT", "Pittsburgh Steelers", "Pittsburgh", "Steelers",
                              ["Steelers", "Pittsburgh", "PIT"], Sport.NFL),
            "CLE": TeamMapping("CLE", "Cleveland Browns", "Cleveland", "Browns",
                              ["Browns", "Cleveland", "CLE"], Sport.NFL),
            "CIN": TeamMapping("CIN", "Cincinnati Bengals", "Cincinnati", "Bengals",
                              ["Bengals", "Cincinnati", "CIN"], Sport.NFL),
            "GB": TeamMapping("GB", "Green Bay Packers", "Green Bay", "Packers",
                             ["Packers", "Green Bay", "GB"], Sport.NFL),
            "CHI": TeamMapping("CHI", "Chicago Bears", "Chicago", "Bears",
                              ["Bears", "Chicago", "CHI"], Sport.NFL),
            "MIN": TeamMapping("MIN", "Minnesota Vikings", "Minnesota", "Vikings",
                              ["Vikings", "Minnesota", "MIN"], Sport.NFL),
            "DET": TeamMapping("DET", "Detroit Lions", "Detroit", "Lions",
                              ["Lions", "Detroit", "DET"], Sport.NFL),
            "PHI": TeamMapping("PHI", "Philadelphia Eagles", "Philadelphia", "Eagles",
                              ["Eagles", "Philadelphia", "Philly", "PHI"], Sport.NFL),
            "WAS": TeamMapping("WAS", "Washington Commanders", "Washington", "Commanders",
                              ["Commanders", "Washington", "WAS"], Sport.NFL),
            "TB": TeamMapping("TB", "Tampa Bay Buccaneers", "Tampa Bay", "Buccaneers",
                             ["Buccaneers", "Bucs", "Tampa Bay", "TB"], Sport.NFL),
            "ATL": TeamMapping("ATL", "Atlanta Falcons", "Atlanta", "Falcons",
                              ["Falcons", "Atlanta", "ATL"], Sport.NFL),
            "CAR": TeamMapping("CAR", "Carolina Panthers", "Carolina", "Panthers",
                              ["Panthers", "Carolina", "CAR"], Sport.NFL),
            "NO": TeamMapping("NO", "New Orleans Saints", "New Orleans", "Saints",
                             ["Saints", "New Orleans", "NO"], Sport.NFL),
            "SF": TeamMapping("SF", "San Francisco 49ers", "San Francisco", "49ers",
                             ["49ers", "Niners", "San Francisco", "SF"], Sport.NFL),
            "LAR": TeamMapping("LAR", "Los Angeles Rams", "Los Angeles", "Rams",
                              ["Rams", "LA Rams", "Los Angeles Rams", "LAR"], Sport.NFL),
            "SEA": TeamMapping("SEA", "Seattle Seahawks", "Seattle", "Seahawks",
                              ["Seahawks", "Seattle", "SEA"], Sport.NFL),
            "ARI": TeamMapping("ARI", "Arizona Cardinals", "Arizona", "Cardinals",
                              ["Cardinals", "Arizona", "ARI"], Sport.NFL),
            "DEN": TeamMapping("DEN", "Denver Broncos", "Denver", "Broncos",
                              ["Broncos", "Denver", "DEN"], Sport.NFL),
            "LV": TeamMapping("LV", "Las Vegas Raiders", "Las Vegas", "Raiders",
                             ["Raiders", "Las Vegas", "LV", "Oakland Raiders"], Sport.NFL),
            "LAC": TeamMapping("LAC", "Los Angeles Chargers", "Los Angeles", "Chargers",
                              ["Chargers", "LA Chargers", "Los Angeles Chargers", "LAC"], Sport.NFL),
            "TEN": TeamMapping("TEN", "Tennessee Titans", "Tennessee", "Titans",
                              ["Titans", "Tennessee", "TEN"], Sport.NFL),
            "IND": TeamMapping("IND", "Indianapolis Colts", "Indianapolis", "Colts",
                              ["Colts", "Indianapolis", "IND"], Sport.NFL),
            "HOU": TeamMapping("HOU", "Houston Texans", "Houston", "Texans",
                              ["Texans", "Houston", "HOU"], Sport.NFL),
            "JAX": TeamMapping("JAX", "Jacksonville Jaguars", "Jacksonville", "Jaguars",
                              ["Jaguars", "Jags", "Jacksonville", "JAX"], Sport.NFL),
        }
        return teams
    
    def _initialize_nba_teams(self) -> Dict[str, TeamMapping]:
        """Initialize NBA team mappings."""
        teams = {
            "LAL": TeamMapping("LAL", "Los Angeles Lakers", "Los Angeles", "Lakers",
                              ["Lakers", "LA Lakers", "Los Angeles Lakers", "LAL"], Sport.NBA),
            "BOS": TeamMapping("BOS", "Boston Celtics", "Boston", "Celtics",
                              ["Celtics", "Boston", "BOS"], Sport.NBA),
            "GSW": TeamMapping("GSW", "Golden State Warriors", "Golden State", "Warriors",
                              ["Warriors", "Golden State", "GSW", "GS Warriors"], Sport.NBA),
            "BKN": TeamMapping("BKN", "Brooklyn Nets", "Brooklyn", "Nets",
                              ["Nets", "Brooklyn", "BKN"], Sport.NBA),
            "MIA": TeamMapping("MIA", "Miami Heat", "Miami", "Heat",
                              ["Heat", "Miami", "MIA"], Sport.NBA),
            "CHI": TeamMapping("CHI", "Chicago Bulls", "Chicago", "Bulls",
                              ["Bulls", "Chicago", "CHI"], Sport.NBA),
            "NYK": TeamMapping("NYK", "New York Knicks", "New York", "Knicks",
                              ["Knicks", "NY Knicks", "New York Knicks", "NYK"], Sport.NBA),
            "LAC": TeamMapping("LAC", "LA Clippers", "Los Angeles", "Clippers",
                              ["Clippers", "LA Clippers", "Los Angeles Clippers", "LAC"], Sport.NBA),
            "DEN": TeamMapping("DEN", "Denver Nuggets", "Denver", "Nuggets",
                              ["Nuggets", "Denver", "DEN"], Sport.NBA),
            "PHX": TeamMapping("PHX", "Phoenix Suns", "Phoenix", "Suns",
                              ["Suns", "Phoenix", "PHX"], Sport.NBA),
        }
        return teams
    
    def _initialize_market_types(self) -> Dict[str, MarketMapping]:
        """Initialize market type mappings."""
        markets = {
            "ML": MarketMapping("ML", "Moneyline", 
                               ["Moneyline", "ML", "Money Line", "H2H", "Match Winner"],
                               {"draftkings": "moneyline", "fanduel": "h2h", "betmgm": "match_winner"}),
            "PS": MarketMapping("PS", "Point Spread",
                               ["Point Spread", "PS", "Spread", "Line", "Handicap"],
                               {"draftkings": "spread", "fanduel": "point_spread", "betmgm": "handicap"}),
            "OU": MarketMapping("OU", "Over/Under",
                               ["Over/Under", "OU", "Total", "Totals", "Total Points"],
                               {"draftkings": "totals", "fanduel": "over_under", "betmgm": "total_points"}),
            "PP": MarketMapping("PP", "Player Props",
                               ["Player Props", "PP", "Player", "Props"],
                               {"draftkings": "player_props", "fanduel": "player", "betmgm": "props"}),
            "FH": MarketMapping("FH", "First Half",
                               ["First Half", "FH", "1H", "First Half Line"],
                               {"draftkings": "first_half", "fanduel": "1h", "betmgm": "first_half_line"}),
            "3W": MarketMapping("3W", "Three Way",
                               ["Three Way", "3W", "Win/Draw/Loss", "1X2"],
                               {"draftkings": "three_way", "fanduel": "win_draw_loss", "betmgm": "1x2"}),
        }
        return markets
    
    def _build_team_lookup(self) -> Dict[str, Tuple[str, Sport]]:
        """Build a lookup dictionary for fast team name resolution."""
        lookup = {}
        
        # Add NFL teams
        for code, team in self.nfl_teams.items():
            # Add the code itself
            lookup[code.upper()] = (code, team.sport)
            # Add full name
            lookup[team.full_name.upper()] = (code, team.sport)
            # Add city and nickname
            lookup[team.city.upper()] = (code, team.sport)
            lookup[team.nickname.upper()] = (code, team.sport)
            # Add aliases
            for alias in team.aliases:
                lookup[alias.upper()] = (code, team.sport)
        
        # Add NBA teams
        for code, team in self.nba_teams.items():
            lookup[code.upper()] = (code, team.sport)
            lookup[team.full_name.upper()] = (code, team.sport)
            lookup[team.city.upper()] = (code, team.sport)
            lookup[team.nickname.upper()] = (code, team.sport)
            for alias in team.aliases:
                lookup[alias.upper()] = (code, team.sport)
        
        return lookup
    
    def _build_market_lookup(self) -> Dict[str, str]:
        """Build a lookup dictionary for market type resolution."""
        lookup = {}
        
        for code, market in self.market_types.items():
            # Add the code itself
            lookup[code.upper()] = code
            # Add full name
            lookup[market.full_name.upper()] = code
            # Add aliases
            for alias in market.aliases:
                lookup[alias.upper()] = code
            # Add sportsbook variants
            for sportsbook, variant in market.sportsbook_variants.items():
                lookup[variant.upper()] = code
        
        return lookup
    
    def normalize_team_name(self, team_name: str, sport: Optional[Sport] = None) -> Optional[str]:
        """
        Normalize a team name to its standard code.
        
        Args:
            team_name: Raw team name to normalize
            sport: Optional sport filter
            
        Returns:
            Normalized team code, or None if not found
        """
        if not team_name:
            return None
        
        # Clean the input
        clean_name = team_name.strip().upper()
        
        # Direct lookup
        if clean_name in self.team_lookup:
            code, team_sport = self.team_lookup[clean_name]
            if sport is None or team_sport == sport:
                return code
        
        # Fuzzy matching for partial names
        return self._fuzzy_match_team(clean_name, sport)
    
    def _fuzzy_match_team(self, clean_name: str, sport: Optional[Sport] = None) -> Optional[str]:
        """Perform fuzzy matching for team names."""
        # Try to find team name within the string
        for lookup_name, (code, team_sport) in self.team_lookup.items():
            if sport is None or team_sport == sport:
                # Check if the lookup name is contained in the input
                if lookup_name in clean_name or clean_name in lookup_name:
                    return code
        
        # Try regex patterns for common formats
        patterns = [
            r'\b([A-Z]{2,4})\b',  # Team codes like "LAL", "KC"
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',  # Team names like "Lakers", "Golden State"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, team_name)
            for match in matches:
                normalized = self.normalize_team_name(match, sport)
                if normalized:
                    return normalized
        
        return None
    
    def normalize_market_type(self, market_type: str, sportsbook: Optional[str] = None) -> Optional[str]:
        """
        Normalize a market type to its standard code.
        
        Args:
            market_type: Raw market type to normalize
            sportsbook: Optional sportsbook for context
            
        Returns:
            Normalized market code, or None if not found
        """
        if not market_type:
            return None
        
        clean_type = market_type.strip().upper()
        
        # Direct lookup
        if clean_type in self.market_lookup:
            return self.market_lookup[clean_type]
        
        # Sportsbook-specific lookup
        if sportsbook:
            sportsbook_lower = sportsbook.lower()
            for code, market in self.market_types.items():
                if sportsbook_lower in market.sportsbook_variants:
                    variant = market.sportsbook_variants[sportsbook_lower]
                    if variant.upper() == clean_type:
                        return code
        
        # Fuzzy matching
        return self._fuzzy_match_market(clean_type)
    
    def _fuzzy_match_market(self, clean_type: str) -> Optional[str]:
        """Perform fuzzy matching for market types."""
        for lookup_type, code in self.market_lookup.items():
            if lookup_type in clean_type or clean_type in lookup_type:
                return code
        return None
    
    def get_team_info(self, team_code: str, sport: Sport) -> Optional[TeamMapping]:
        """Get detailed team information by code and sport."""
        teams = self.nfl_teams if sport == Sport.NFL else self.nba_teams
        return teams.get(team_code.upper())
    
    def get_market_info(self, market_code: str) -> Optional[MarketMapping]:
        """Get detailed market information by code."""
        return self.market_types.get(market_code.upper())
    
    def standardize_game_matchup(self, home_team: str, away_team: str, sport: Sport) -> Optional[Tuple[str, str]]:
        """
        Standardize a game matchup to normalized team codes.
        
        Args:
            home_team: Home team name
            away_team: Away team name
            sport: Sport type
            
        Returns:
            Tuple of (away_code, home_code) or None if either team not found
        """
        home_code = self.normalize_team_name(home_team, sport)
        away_code = self.normalize_team_name(away_team, sport)
        
        if home_code and away_code:
            return (away_code, home_code)
        return None
    
    def get_sport_teams(self, sport: Sport) -> Dict[str, TeamMapping]:
        """Get all teams for a specific sport."""
        return self.nfl_teams if sport == Sport.NFL else self.nba_teams
    
    def validate_team_in_sport(self, team_name: str, sport: Sport) -> bool:
        """Check if a team exists in the specified sport."""
        normalized = self.normalize_team_name(team_name, sport)
        return normalized is not None
    
    def extract_teams_from_text(self, text: str, sport: Optional[Sport] = None) -> List[Tuple[str, Sport]]:
        """
        Extract all team references from text.
        
        Args:
            text: Text to search for team names
            sport: Optional sport filter
            
        Returns:
            List of (team_code, sport) tuples found in text
        """
        found_teams = []
        text_upper = text.upper()
        
        for lookup_name, (code, team_sport) in self.team_lookup.items():
            if sport is None or team_sport == sport:
                if lookup_name in text_upper:
                    found_teams.append((code, team_sport))
        
        # Remove duplicates while preserving order
        seen = set()
        unique_teams = []
        for team, team_sport in found_teams:
            if (team, team_sport) not in seen:
                seen.add((team, team_sport))
                unique_teams.append((team, team_sport))
        
        return unique_teams


def main():
    """Main function for testing the MarketNormalizer."""
    print("🔧 MarketNormalizer - JIRA-050")
    print("=" * 50)
    
    normalizer = MarketNormalizer()
    
    # Test NFL team normalization
    print("\n🏈 NFL Team Normalization Tests:")
    print("-" * 40)
    nfl_tests = [
        "Kansas City Chiefs",
        "Chiefs", 
        "KC",
        "Dallas Cowboys",
        "Cowboys",
        "New England Patriots",
        "Pats"
    ]
    
    for test_name in nfl_tests:
        normalized = normalizer.normalize_team_name(test_name, Sport.NFL)
        print(f"'{test_name}' → {normalized}")
    
    # Test NBA team normalization  
    print("\n🏀 NBA Team Normalization Tests:")
    print("-" * 40)
    nba_tests = [
        "Los Angeles Lakers",
        "Lakers",
        "LAL", 
        "Golden State Warriors",
        "Warriors",
        "Boston Celtics"
    ]
    
    for test_name in nba_tests:
        normalized = normalizer.normalize_team_name(test_name, Sport.NBA)
        print(f"'{test_name}' → {normalized}")
    
    # Test market type normalization
    print("\n📊 Market Type Normalization Tests:")
    print("-" * 40)
    market_tests = [
        "Moneyline",
        "ML",
        "Point Spread", 
        "Spread",
        "Over/Under",
        "OU",
        "Three Way"
    ]
    
    for test_market in market_tests:
        normalized = normalizer.normalize_market_type(test_market)
        print(f"'{test_market}' → {normalized}")
    
    # Test game matchup standardization
    print("\n🏟️ Game Matchup Standardization:")
    print("-" * 40)
    matchup = normalizer.standardize_game_matchup("Kansas City Chiefs", "Buffalo Bills", Sport.NFL)
    print(f"Chiefs vs Bills → {matchup}")
    
    matchup = normalizer.standardize_game_matchup("Lakers", "Celtics", Sport.NBA)
    print(f"Lakers vs Celtics → {matchup}")
    
    # Test text extraction
    print("\n🔍 Team Extraction from Text:")
    print("-" * 40)
    text = "The Kansas City Chiefs beat the Buffalo Bills 31-17 in a great game."
    teams = normalizer.extract_teams_from_text(text, Sport.NFL)
    print(f"Text: '{text}'")
    print(f"Found teams: {teams}")
    
    print(f"\n✅ MarketNormalizer testing complete!")


if __name__ == "__main__":
    main()
