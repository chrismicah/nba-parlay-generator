#!/usr/bin/env python3
"""
Parlay Reasoning Dataset Generator - JIRA-019

Generates synthetic parlay reasoning data with historical outcomes for training
a RoBERTa confidence classifier.

Creates realistic parlay reasoning scenarios with win/loss outcomes and
confidence labels (high_confidence, low_confidence) for machine learning training.
"""

import json
import random
import logging
from typing import List, Dict, Any, Tuple
from pathlib import Path
from datetime import datetime, timedelta
import sqlite3

# Set up logging
logger = logging.getLogger(__name__)


class ParlayReasoningDatasetGenerator:
    """Generates synthetic parlay reasoning datasets for confidence classification."""
    
    def __init__(self, output_path: str = "data/parlay_reasoning_dataset.jsonl"):
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # NBA teams for realistic scenarios
        self.nba_teams = [
            'Lakers', 'Celtics', 'Warriors', 'Nets', 'Heat', 'Bulls', 'Knicks',
            'Clippers', 'Nuggets', 'Suns', 'Mavericks', 'Rockets', 'Spurs',
            'Thunder', 'Jazz', 'Blazers', 'Kings', 'Timberwolves', 'Pelicans',
            'Magic', 'Hawks', 'Hornets', 'Pistons', 'Pacers', 'Cavaliers',
            'Raptors', 'Wizards', 'Bucks', '76ers', 'Grizzlies'
        ]
        
        # Star players for injury scenarios
        self.star_players = [
            'LeBron James', 'Steph Curry', 'Kevin Durant', 'Giannis Antetokounmpo',
            'Luka Doncic', 'Jayson Tatum', 'Joel Embiid', 'Nikola Jokic',
            'Kawhi Leonard', 'Jimmy Butler', 'Damian Lillard', 'Anthony Davis',
            'Ja Morant', 'Zion Williamson', 'Trae Young', 'Devin Booker'
        ]
        
        # Common betting markets
        self.markets = ['moneyline', 'spread', 'total', 'player_props']
        
    def generate_dataset(self, num_samples: int = 1000) -> None:
        """
        Generate a complete parlay reasoning dataset.
        
        Args:
            num_samples: Number of parlay reasoning samples to generate
        """
        logger.info(f"Generating {num_samples} parlay reasoning samples...")
        
        samples = []
        
        # Generate high confidence samples (40% of dataset)
        high_conf_samples = int(num_samples * 0.4)
        for i in range(high_conf_samples):
            sample = self._generate_high_confidence_sample(i)
            samples.append(sample)
        
        # Generate low confidence samples (35% of dataset)
        low_conf_samples = int(num_samples * 0.35)
        for i in range(low_conf_samples):
            sample = self._generate_low_confidence_sample(i)
            samples.append(sample)
        
        # Generate medium confidence samples (25% of dataset)
        med_conf_samples = num_samples - high_conf_samples - low_conf_samples
        for i in range(med_conf_samples):
            sample = self._generate_medium_confidence_sample(i)
            samples.append(sample)
        
        # Shuffle the dataset
        random.shuffle(samples)
        
        # Save to file
        self._save_dataset(samples)
        
        logger.info(f"Dataset saved to {self.output_path}")
        logger.info(f"Generated {len(samples)} samples:")
        logger.info(f"- High confidence: {high_conf_samples}")
        logger.info(f"- Medium confidence: {med_conf_samples}")
        logger.info(f"- Low confidence: {low_conf_samples}")
    
    def _generate_high_confidence_sample(self, sample_id: int) -> Dict[str, Any]:
        """Generate a high-confidence parlay reasoning sample."""
        teams = random.sample(self.nba_teams, 3)
        
        # High confidence scenarios
        scenarios = [
            self._create_dominant_favorite_scenario(teams),
            self._create_sharp_money_scenario(teams),
            self._create_statistical_edge_scenario(teams),
            self._create_balanced_matchup_scenario(teams)
        ]
        
        scenario = random.choice(scenarios)
        
        # High confidence typically results in wins (70-80% win rate)
        outcome = 'win' if random.random() < 0.75 else 'loss'
        
        return {
            'parlay_id': f"high_conf_{sample_id}",
            'reasoning': scenario,
            'outcome': outcome,
            'confidence_label': 'high_confidence',
            'generated_at': self._random_timestamp().isoformat(),
            'legs_count': random.randint(2, 4),
            'total_odds': round(random.uniform(2.5, 6.0), 2)
        }
    
    def _generate_low_confidence_sample(self, sample_id: int) -> Dict[str, Any]:
        """Generate a low-confidence parlay reasoning sample."""
        teams = random.sample(self.nba_teams, 3)
        
        # Low confidence scenarios
        scenarios = [
            self._create_injury_concern_scenario(teams),
            self._create_public_money_trap_scenario(teams),
            self._create_balanced_matchup_scenario(teams)  # Reuse for variety
        ]
        
        scenario = random.choice(scenarios)
        
        # Low confidence typically results in losses (30-40% win rate)
        outcome = 'win' if random.random() < 0.35 else 'loss'
        
        return {
            'parlay_id': f"low_conf_{sample_id}",
            'reasoning': scenario,
            'outcome': outcome,
            'confidence_label': 'low_confidence',
            'generated_at': self._random_timestamp().isoformat(),
            'legs_count': random.randint(2, 5),
            'total_odds': round(random.uniform(3.0, 12.0), 2)
        }
    
    def _generate_medium_confidence_sample(self, sample_id: int) -> Dict[str, Any]:
        """Generate a medium-confidence parlay reasoning sample."""
        teams = random.sample(self.nba_teams, 3)
        
        # Medium confidence scenarios
        scenarios = [
            self._create_balanced_matchup_scenario(teams),
            self._create_sharp_money_scenario(teams),  # Reuse with different weighting
            self._create_statistical_edge_scenario(teams)  # Reuse for variety
        ]
        
        scenario = random.choice(scenarios)
        
        # Medium confidence results in moderate win rate (50-60%)
        outcome = 'win' if random.random() < 0.55 else 'loss'
        
        # Randomly assign to high or low confidence for training variety
        confidence_label = random.choice(['high_confidence', 'low_confidence'])
        
        return {
            'parlay_id': f"med_conf_{sample_id}",
            'reasoning': scenario,
            'outcome': outcome,
            'confidence_label': confidence_label,
            'generated_at': self._random_timestamp().isoformat(),
            'legs_count': random.randint(2, 4),
            'total_odds': round(random.uniform(2.8, 8.0), 2)
        }
    
    def _create_dominant_favorite_scenario(self, teams: List[str]) -> str:
        """Create a high-confidence scenario with dominant favorites."""
        team1, team2, team3 = teams
        player1 = random.choice(self.star_players)
        
        return f"""PARLAY ANALYSIS (3 legs):

LEG 1: {team1} Moneyline (-180)
Odds: 1.56 at DraftKings
• {team1} are 12-2 at home this season with dominant defense
• Opponent missing their starting point guard and shooting guard
• {team1} have won 8 straight games by average margin of 14 points
• Vegas opened at -165, moved to -180 despite balanced public money indicating sharp action

LEG 2: {team2} -4.5 (-110)
Odds: 1.91 at FanDuel
• {team2} are 18-6 ATS as favorites this season
• Opponent playing back-to-back after overtime game last night
• {player1} confirmed healthy after questionable tag, team at full strength
• Line movement from -3.5 to -4.5 shows sharp money backing {team2}

LEG 3: {team3} vs Opponent Under 218.5 (-105)
Odds: 1.95 at BetMGM
• Both teams rank bottom-5 in pace, average combined 208 points in last 6 meetings
• Weather conditions: 25mph winds affecting outdoor arena ventilation
• Both teams shoot poorly on road (sub-33% from three combined)
• Total opened at 221, moved down to 218.5 on sharp under action

OVERALL ASSESSMENT:
Combined odds: 5.98
Risk assessment: Low risk - All legs backed by strong fundamentals
Value assessment: Strong value with multiple confirming factors
Confidence factors: Injury advantages, sharp money alignment, statistical edges all favorable"""
    
    def _create_injury_concern_scenario(self, teams: List[str]) -> str:
        """Create a low-confidence scenario with injury concerns."""
        team1, team2, team3 = teams
        player1, player2 = random.sample(self.star_players, 2)
        
        return f"""PARLAY ANALYSIS (3 legs):

LEG 1: {team1} +3.5 (-110)
Odds: 1.91 at DraftKings
• {player1} listed as questionable with ankle injury, practiced limitedly yesterday
• Injury Intel: Team medical staff "optimistic" but no official confirmation
• {team1} are 2-8 ATS without {player1} this season
• Public betting 70% on {team1} but line hasn't moved, concerning sign

LEG 2: {team2} Moneyline (+140)
Odds: 2.40 at FanDuel
• {player2} probable with knee soreness, but played 42 minutes last game
• Team on 4-game road trip, fatigue concerns mounting
• Opponent well-rested with 3 days off and home court advantage
• Recent form: {team2} lost 5 of last 7, averaging just 98 points per game

LEG 3: {team3} Team Total Over 108.5 (-115)
Odds: 1.87 at BetMGM
• {team3} averaging 106.2 PPG over last 10 games, below season average
• Starting center ruled out with back injury, backup is defensively limited
• Opponent allows 4th-fewest points in paint, will exploit {team3}'s weakness
• Weather: Heavy rain may affect shooting in domed arena with roof leak issues

OVERALL ASSESSMENT:
Combined odds: 8.63
Risk assessment: High risk - Multiple injury concerns and unfavorable matchups
Value assessment: Limited value - proceed with caution
Injury concerns: 3 players with injury designations across parlay legs"""
    
    def _create_sharp_money_scenario(self, teams: List[str]) -> str:
        """Create a high-confidence scenario following sharp money."""
        team1, team2 = teams[:2]
        
        return f"""PARLAY ANALYSIS (2 legs):

LEG 1: {team1} -2.5 (-108)
Odds: 1.93 at DraftKings
• Line opened at {team1} -1, moved to -2.5 despite 65% public money on opponent
• Sharp money indicators: Steam moves at multiple offshore books
• {team1} are 15-4 ATS off a loss this season, motivated spot
• Reverse line movement classic sign of professional money

LEG 2: {team2} vs Opponent Under 215.5 (-110)
Odds: 1.91 at FanDuel
• Total opened at 218.5, sharp under action moved it to 215.5
• Both teams missing key offensive players, pace will be slow
• Referee crew averaging 8 fewer points than season average
• Professional bettors targeting under in similar situations this season

OVERALL ASSESSMENT:
Combined odds: 3.69
Risk assessment: Low risk - Following sharp money with clear reasoning
Value assessment: Strong value - Line movement confirms professional interest
Sharp money alignment: Both legs show classic reverse line movement patterns
Historical performance: Similar situations have 68% win rate this season"""
    
    def _create_balanced_matchup_scenario(self, teams: List[str]) -> str:
        """Create a medium-confidence scenario with mixed signals."""
        team1, team2, team3 = teams
        
        return f"""PARLAY ANALYSIS (3 legs):

LEG 1: {team1} Moneyline (-125)
Odds: 1.80 at DraftKings
• {team1} slight home favorites in evenly matched contest
• Head-to-head: Teams split season series 1-1, games decided by 3 and 5 points
• Both teams healthy but some rotation uncertainty
• Line movement minimal, suggesting balanced betting action

LEG 2: {team2} +6.5 (-110)
Odds: 1.91 at FanDuel
• {team2} getting generous number as road underdogs
• Recent form mixed: 5-5 in last 10 with inconsistent offensive output
• Opponent favored but has struggled ATS at home (8-12 this season)
• Line movement: Opened +6, now +6.5, slight value but not overwhelming

LEG 3: {team3} vs Opponent Over 210.5 (-105)
Odds: 1.95 at BetMGM
• Both teams average pace suggests total around 208-212 points
• Weather conditions neutral, no significant environmental factors
• Injury report clean but some players nursing minor issues
• Total moved slightly from 211 to 210.5, minimal sharp action detected

OVERALL ASSESSMENT:
Combined odds: 6.42
Risk assessment: Medium risk - Balanced selections with moderate confidence
Value assessment: Moderate value with some concerns
Mixed signals: Some favorable indicators balanced by uncertainty factors"""
    
    def _create_public_money_trap_scenario(self, teams: List[str]) -> str:
        """Create a low-confidence scenario that looks like a public money trap."""
        team1, team2 = teams[:2]
        player = random.choice(self.star_players)
        
        return f"""PARLAY ANALYSIS (2 legs):

LEG 1: {team1} -7.5 (-110)
Odds: 1.91 at DraftKings
• {team1} heavily favored but public betting 85% on them
• Line opened at -6.5, moved to -7.5 - unusual movement with heavy public money
• {player} expected to play but on minutes restriction after recent injury
• Opponent desperate for wins, fighting for playoff positioning
• Classic "public fade" setup - too much public attention on favorite

LEG 2: {team2} vs Opponent Over 225.5 (-115)
Odds: 1.87 at FanDuel
• Public loves high-scoring games, 78% of bets on over
• Total moved UP from 223 to 225.5 despite heavy over action - red flag
• Both teams played yesterday, tired legs typically mean under performance
• Last 3 meetings between these teams averaged just 218 points
• Pace projections suggest 220 total, making 225.5 inflated

OVERALL ASSESSMENT:
Combined odds: 3.57
Risk assessment: High risk - Appears to be public money trap
Value assessment: Poor value - line movement against heavy public money
Public betting concerns: Heavy recreational money on both legs with suspicious line movement
Fade indicators: Classic spots where sportsbooks profit from public overreaction"""
    
    def _create_statistical_edge_scenario(self, teams: List[str]) -> str:
        """Create a high-confidence scenario based on statistical analysis."""
        team1, team2, team3 = teams
        
        return f"""PARLAY ANALYSIS (3 legs):

LEG 1: {team1} Team Total Under 112.5 (-110)
Odds: 1.91 at DraftKings
• {team1} averaging 108.4 PPG in last 15 games vs top-10 defenses
• Opponent allows 4th-fewest points per game (106.8) this season
• Pace projection: {team1} plays slow (28th in pace) vs defense-first opponent
• Historical trend: {team1} under 112.5 in 12 of last 16 vs similar opponents

LEG 2: {team2} -3.5 (-105)
Odds: 1.95 at FanDuel
• {team2} are 21-9 ATS as home favorites between 1-6 points this season
• Advanced metrics favor {team2}: +8.2 net rating vs opponent's -2.1
• Rest advantage: {team2} had 2 days off vs opponent on back-to-back
• Shooting variance correction: Opponent shot 48% from three last game (unsustainable)

LEG 3: {team3} vs Opponent 1st Quarter Under 52.5 (-110)
Odds: 1.91 at BetMGM
• Both teams average 48.3 combined 1Q points in last 20 games
• Early game tip-off (12pm) historically produces lower 1Q scoring
• {team3} are slow starters: 29th in 1st quarter net rating this season
• Opponent shoots 28% from three in 1st quarters (league worst)

OVERALL ASSESSMENT:
Combined odds: 7.12
Risk assessment: Low risk - Strong statistical foundation for all legs
Value assessment: Excellent value - Multiple statistical edges identified
Data-driven confidence: Historical trends and advanced metrics strongly support all selections"""
    
    def _random_timestamp(self) -> datetime:
        """Generate a random timestamp within the last 90 days."""
        start_date = datetime.now() - timedelta(days=90)
        random_days = random.randint(0, 90)
        random_hours = random.randint(0, 23)
        random_minutes = random.randint(0, 59)
        
        return start_date + timedelta(days=random_days, hours=random_hours, minutes=random_minutes)
    
    def _save_dataset(self, samples: List[Dict[str, Any]]) -> None:
        """Save the dataset to a JSONL file."""
        with open(self.output_path, 'w', encoding='utf-8') as f:
            for sample in samples:
                f.write(json.dumps(sample) + '\n')
    
    def load_dataset(self) -> List[Dict[str, Any]]:
        """Load the dataset from the JSONL file."""
        if not self.output_path.exists():
            logger.error(f"Dataset file not found: {self.output_path}")
            return []
        
        samples = []
        with open(self.output_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    samples.append(json.loads(line))
        
        return samples
    
    def get_dataset_stats(self) -> Dict[str, Any]:
        """Get statistics about the generated dataset."""
        samples = self.load_dataset()
        
        if not samples:
            return {"error": "No dataset found"}
        
        # Calculate statistics
        total_samples = len(samples)
        high_conf = len([s for s in samples if s['confidence_label'] == 'high_confidence'])
        low_conf = len([s for s in samples if s['confidence_label'] == 'low_confidence'])
        
        wins = len([s for s in samples if s['outcome'] == 'win'])
        losses = len([s for s in samples if s['outcome'] == 'loss'])
        
        high_conf_wins = len([s for s in samples 
                            if s['confidence_label'] == 'high_confidence' and s['outcome'] == 'win'])
        low_conf_wins = len([s for s in samples 
                           if s['confidence_label'] == 'low_confidence' and s['outcome'] == 'win'])
        
        avg_odds = sum(s['total_odds'] for s in samples) / total_samples
        avg_legs = sum(s['legs_count'] for s in samples) / total_samples
        
        return {
            'total_samples': total_samples,
            'confidence_distribution': {
                'high_confidence': high_conf,
                'low_confidence': low_conf,
                'high_conf_percentage': round(high_conf / total_samples * 100, 1),
                'low_conf_percentage': round(low_conf / total_samples * 100, 1)
            },
            'outcome_distribution': {
                'wins': wins,
                'losses': losses,
                'win_percentage': round(wins / total_samples * 100, 1)
            },
            'win_rates_by_confidence': {
                'high_confidence_win_rate': round(high_conf_wins / high_conf * 100, 1) if high_conf > 0 else 0,
                'low_confidence_win_rate': round(low_conf_wins / low_conf * 100, 1) if low_conf > 0 else 0
            },
            'averages': {
                'avg_total_odds': round(avg_odds, 2),
                'avg_legs_count': round(avg_legs, 1)
            }
        }


def main():
    """Main function for dataset generation."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        print("📊 Parlay Reasoning Dataset Generator - JIRA-019")
        print("=" * 60)
        
        # Initialize generator
        generator = ParlayReasoningDatasetGenerator()
        
        # Generate dataset
        print("🔄 Generating parlay reasoning dataset...")
        generator.generate_dataset(num_samples=1000)
        
        # Show statistics
        print("\n📈 Dataset Statistics:")
        stats = generator.get_dataset_stats()
        
        print(f"Total Samples: {stats['total_samples']}")
        print(f"High Confidence: {stats['confidence_distribution']['high_confidence']} "
              f"({stats['confidence_distribution']['high_conf_percentage']}%)")
        print(f"Low Confidence: {stats['confidence_distribution']['low_confidence']} "
              f"({stats['confidence_distribution']['low_conf_percentage']}%)")
        print(f"Overall Win Rate: {stats['outcome_distribution']['win_percentage']}%")
        print(f"High Conf Win Rate: {stats['win_rates_by_confidence']['high_confidence_win_rate']}%")
        print(f"Low Conf Win Rate: {stats['win_rates_by_confidence']['low_confidence_win_rate']}%")
        print(f"Average Odds: {stats['averages']['avg_total_odds']}")
        print(f"Average Legs: {stats['averages']['avg_legs_count']}")
        
        # Show sample
        samples = generator.load_dataset()
        if samples:
            print(f"\n📋 Sample High-Confidence Reasoning:")
            print("=" * 50)
            high_conf_sample = next(s for s in samples if s['confidence_label'] == 'high_confidence')
            print(high_conf_sample['reasoning'][:500] + "...")
            
            print(f"\n📋 Sample Low-Confidence Reasoning:")
            print("=" * 50)
            low_conf_sample = next(s for s in samples if s['confidence_label'] == 'low_confidence')
            print(low_conf_sample['reasoning'][:500] + "...")
        
        print(f"\n✅ Dataset generation complete!")
        print(f"📁 Dataset saved to: {generator.output_path}")
        print(f"🎯 Ready for RoBERTa confidence classification training")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
