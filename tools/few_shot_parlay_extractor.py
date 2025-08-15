#!/usr/bin/env python3
"""
Few-Shot Parlay Extractor - JIRA-020

Extracts high-confidence successful parlays from the parlay reasoning dataset
and converts them into few-shot learning examples for improving the ParlayStrategistAgent.
"""

import json
import logging
from typing import Dict, List, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class FewShotExample:
    """Structure for a few-shot learning example."""
    example_id: str
    input_data: Dict[str, Any]
    reasoning: str
    generated_parlay: Dict[str, Any]
    outcome: str
    confidence_score: float
    success_metrics: Dict[str, Any]


class FewShotParlayExtractor:
    """Extracts and formats successful parlays for few-shot learning."""
    
    def __init__(self, dataset_path: str = "data/parlay_reasoning_dataset.jsonl"):
        self.dataset_path = Path(dataset_path)
        self.few_shot_examples: List[FewShotExample] = []
        
    def load_dataset(self) -> List[Dict[str, Any]]:
        """Load the parlay reasoning dataset."""
        if not self.dataset_path.exists():
            logger.error(f"Dataset file not found: {self.dataset_path}")
            return []
        
        samples = []
        with open(self.dataset_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    samples.append(json.loads(line))
        
        logger.info(f"Loaded {len(samples)} samples from dataset")
        return samples
    
    def extract_successful_examples(self, num_examples: int = 10) -> List[FewShotExample]:
        """
        Extract the most successful high-confidence parlays for few-shot learning.
        
        Args:
            num_examples: Number of examples to extract
            
        Returns:
            List of few-shot examples sorted by success metrics
        """
        samples = self.load_dataset()
        
        # Filter for high-confidence winning parlays
        successful_parlays = [
            sample for sample in samples 
            if sample['confidence_label'] == 'high_confidence' and sample['outcome'] == 'win'
        ]
        
        logger.info(f"Found {len(successful_parlays)} high-confidence winning parlays")
        
        # Score parlays by multiple success factors
        scored_parlays = []
        for parlay in successful_parlays:
            success_score = self._calculate_success_score(parlay)
            scored_parlays.append((parlay, success_score))
        
        # Sort by success score (descending)
        scored_parlays.sort(key=lambda x: x[1], reverse=True)
        
        # Extract top examples
        few_shot_examples = []
        for i, (parlay, score) in enumerate(scored_parlays[:num_examples]):
            example = self._create_few_shot_example(parlay, score, i + 1)
            few_shot_examples.append(example)
        
        self.few_shot_examples = few_shot_examples
        logger.info(f"Extracted {len(few_shot_examples)} few-shot examples")
        
        return few_shot_examples
    
    def _calculate_success_score(self, parlay: Dict[str, Any]) -> float:
        """
        Calculate a success score for ranking parlays.
        
        Higher scores indicate better examples for few-shot learning.
        """
        score = 0.0
        
        # Base score for winning
        score += 1.0
        
        # Bonus for higher odds (but not too high)
        odds = parlay.get('total_odds', 1.0)
        if 2.0 <= odds <= 8.0:
            # Sweet spot for parlay odds
            score += min(0.5, (odds - 2.0) / 12.0)
        elif odds > 8.0:
            # Penalty for very high odds (less reliable)
            score -= 0.2
        
        # Bonus for optimal leg count
        legs_count = parlay.get('legs_count', 2)
        if 2 <= legs_count <= 4:
            score += 0.3
        elif legs_count > 4:
            score -= 0.1
        
        # Bonus for reasoning quality indicators
        reasoning = parlay.get('reasoning', '')
        if 'sharp money' in reasoning.lower():
            score += 0.2
        if 'statistical edge' in reasoning.lower():
            score += 0.2
        if 'injury' in reasoning.lower() and 'advantage' in reasoning.lower():
            score += 0.1
        if 'line movement' in reasoning.lower():
            score += 0.1
        
        # Penalty for concerning factors
        if 'injury concerns' in reasoning.lower():
            score -= 0.1
        if 'public money trap' in reasoning.lower():
            score -= 0.3
        
        return score
    
    def _create_few_shot_example(self, parlay: Dict[str, Any], success_score: float, rank: int) -> FewShotExample:
        """Create a structured few-shot example from a successful parlay."""
        
        # Extract structured input data from reasoning
        input_data = self._extract_input_data_from_reasoning(parlay['reasoning'])
        
        # Extract parlay structure
        generated_parlay = self._extract_parlay_structure(parlay['reasoning'])
        
        # Success metrics
        success_metrics = {
            'success_score': success_score,
            'rank': rank,
            'total_odds': parlay.get('total_odds', 0.0),
            'legs_count': parlay.get('legs_count', 0),
            'outcome': parlay['outcome'],
            'confidence_label': parlay['confidence_label']
        }
        
        return FewShotExample(
            example_id=f"few_shot_{rank:02d}",
            input_data=input_data,
            reasoning=parlay['reasoning'],
            generated_parlay=generated_parlay,
            outcome=parlay['outcome'],
            confidence_score=self._extract_confidence_from_reasoning(parlay['reasoning']),
            success_metrics=success_metrics
        )
    
    def _extract_input_data_from_reasoning(self, reasoning: str) -> Dict[str, Any]:
        """Extract structured input data from reasoning text."""
        lines = reasoning.split('\n')
        
        input_data = {
            'available_games': [],
            'market_conditions': {},
            'injury_intel': [],
            'line_movements': [],
            'statistical_insights': []
        }
        
        current_leg = None
        for line in lines:
            line = line.strip()
            
            if line.startswith('LEG '):
                # New leg
                leg_info = self._parse_leg_info(line)
                if leg_info:
                    input_data['available_games'].append(leg_info)
                    current_leg = leg_info
            elif line.startswith('•') and current_leg:
                # Leg detail
                detail = line[1:].strip()
                if 'injury' in detail.lower():
                    input_data['injury_intel'].append(detail)
                elif 'line moved' in detail.lower() or 'movement' in detail.lower():
                    input_data['line_movements'].append(detail)
                elif any(term in detail.lower() for term in ['statistical', 'average', 'trend', 'historical']):
                    input_data['statistical_insights'].append(detail)
                else:
                    current_leg.setdefault('factors', []).append(detail)
        
        return input_data
    
    def _parse_leg_info(self, leg_line: str) -> Dict[str, Any]:
        """Parse leg information from reasoning text."""
        try:
            # Example: "LEG 1: Lakers ML @ 1.85 [Book: DraftKings]"
            parts = leg_line.split(': ', 1)
            if len(parts) < 2:
                return None
            
            leg_content = parts[1]
            
            # Extract basic info
            leg_info = {
                'selection': leg_content.split(' @ ')[0] if ' @ ' in leg_content else leg_content,
                'market_type': 'unknown',
                'team': 'unknown',
                'factors': []
            }
            
            # Determine market type
            if ' ML' in leg_content or 'Moneyline' in leg_content:
                leg_info['market_type'] = 'moneyline'
            elif any(spread in leg_content for spread in ['+', '-']) and not 'Over' in leg_content and not 'Under' in leg_content:
                leg_info['market_type'] = 'spread'
            elif 'Over' in leg_content or 'Under' in leg_content:
                leg_info['market_type'] = 'totals'
            elif 'Team Total' in leg_content:
                leg_info['market_type'] = 'team_total'
            elif 'Quarter' in leg_content:
                leg_info['market_type'] = 'quarter_prop'
            
            # Extract team name (first word before ML, +/-, etc.)
            words = leg_content.split()
            if words:
                leg_info['team'] = words[0]
            
            return leg_info
            
        except Exception as e:
            logger.warning(f"Could not parse leg info: {leg_line}, error: {e}")
            return None
    
    def _extract_parlay_structure(self, reasoning: str) -> Dict[str, Any]:
        """Extract the parlay structure from reasoning text."""
        lines = reasoning.split('\n')
        
        parlay = {
            'legs': [],
            'total_odds': 0.0,
            'risk_assessment': '',
            'value_assessment': ''
        }
        
        current_leg = {}
        for line in lines:
            line = line.strip()
            
            if line.startswith('LEG '):
                if current_leg:
                    parlay['legs'].append(current_leg)
                current_leg = {'description': line, 'odds': 0.0, 'reasoning_points': []}
            
            elif line.startswith('Odds: ') and current_leg:
                try:
                    odds_text = line.replace('Odds: ', '').split(' at ')[0]
                    current_leg['odds'] = float(odds_text)
                except:
                    pass
            
            elif line.startswith('•') and current_leg:
                current_leg['reasoning_points'].append(line[1:].strip())
            
            elif line.startswith('Combined odds: '):
                try:
                    parlay['total_odds'] = float(line.replace('Combined odds: ', ''))
                except:
                    pass
            
            elif line.startswith('Risk assessment: '):
                parlay['risk_assessment'] = line.replace('Risk assessment: ', '')
            
            elif line.startswith('Value assessment: '):
                parlay['value_assessment'] = line.replace('Value assessment: ', '')
        
        # Add final leg
        if current_leg:
            parlay['legs'].append(current_leg)
        
        return parlay
    
    def _extract_confidence_from_reasoning(self, reasoning: str) -> float:
        """Extract confidence score from reasoning indicators."""
        confidence = 0.5  # Base confidence
        
        # Positive indicators
        if 'strong value' in reasoning.lower():
            confidence += 0.2
        if 'sharp money' in reasoning.lower():
            confidence += 0.15
        if 'statistical edge' in reasoning.lower():
            confidence += 0.15
        if 'low risk' in reasoning.lower():
            confidence += 0.1
        
        # Negative indicators
        if 'high risk' in reasoning.lower():
            confidence -= 0.2
        if 'injury concerns' in reasoning.lower():
            confidence -= 0.1
        if 'public money trap' in reasoning.lower():
            confidence -= 0.3
        
        return max(0.1, min(0.9, confidence))
    
    def format_for_few_shot_prompting(self) -> str:
        """Format the examples for few-shot prompting in the strategist."""
        if not self.few_shot_examples:
            logger.warning("No few-shot examples available. Run extract_successful_examples() first.")
            return ""
        
        prompt_sections = []
        
        # Header
        prompt_sections.append("=== HIGH-CONFIDENCE SUCCESSFUL PARLAY EXAMPLES ===")
        prompt_sections.append("The following are examples of successful high-confidence parlays with detailed reasoning:")
        prompt_sections.append("")
        
        # Examples
        for i, example in enumerate(self.few_shot_examples[:5], 1):  # Top 5 examples
            prompt_sections.append(f"EXAMPLE {i} (Success Score: {example.success_metrics['success_score']:.2f}):")
            prompt_sections.append("Input Context:")
            
            # Summarize input data
            if example.input_data['injury_intel']:
                prompt_sections.append(f"- Injury Intel: {len(example.input_data['injury_intel'])} factors identified")
            if example.input_data['line_movements']:
                prompt_sections.append(f"- Line Movement: {len(example.input_data['line_movements'])} movements detected")
            if example.input_data['statistical_insights']:
                prompt_sections.append(f"- Statistical Insights: {len(example.input_data['statistical_insights'])} trends found")
            
            prompt_sections.append("")
            prompt_sections.append("Generated Reasoning:")
            prompt_sections.append(example.reasoning)
            prompt_sections.append("")
            prompt_sections.append(f"Outcome: {example.outcome.upper()} (Confidence: {example.confidence_score:.2f})")
            prompt_sections.append(f"Parlay Details: {example.success_metrics['legs_count']} legs, {example.success_metrics['total_odds']:.2f} total odds")
            prompt_sections.append("")
            prompt_sections.append("-" * 80)
            prompt_sections.append("")
        
        # Footer guidance
        prompt_sections.append("GUIDANCE FOR NEW PARLAYS:")
        prompt_sections.append("- Focus on statistical edges and sharp money movements")
        prompt_sections.append("- Prefer 2-4 leg parlays with odds between 2.0-8.0")
        prompt_sections.append("- Weight injury advantages and line movement heavily")
        prompt_sections.append("- Avoid public money traps and high-risk scenarios")
        prompt_sections.append("- Generate detailed reasoning with specific factors")
        prompt_sections.append("")
        
        return "\n".join(prompt_sections)
    
    def save_few_shot_examples(self, output_path: str = "data/few_shot_parlay_examples.json") -> None:
        """Save few-shot examples to a JSON file."""
        if not self.few_shot_examples:
            logger.warning("No few-shot examples to save")
            return
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dict format for JSON serialization
        examples_data = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'total_examples': len(self.few_shot_examples),
                'source_dataset': str(self.dataset_path)
            },
            'examples': [asdict(example) for example in self.few_shot_examples],
            'prompt_template': self.format_for_few_shot_prompting()
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(examples_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(self.few_shot_examples)} few-shot examples to {output_file}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the extracted few-shot examples."""
        if not self.few_shot_examples:
            return {"error": "No few-shot examples available"}
        
        total_examples = len(self.few_shot_examples)
        avg_odds = sum(ex.success_metrics['total_odds'] for ex in self.few_shot_examples) / total_examples
        avg_legs = sum(ex.success_metrics['legs_count'] for ex in self.few_shot_examples) / total_examples
        avg_confidence = sum(ex.confidence_score for ex in self.few_shot_examples) / total_examples
        avg_success_score = sum(ex.success_metrics['success_score'] for ex in self.few_shot_examples) / total_examples
        
        market_types = {}
        for example in self.few_shot_examples:
            for game in example.input_data.get('available_games', []):
                market_type = game.get('market_type', 'unknown')
                market_types[market_type] = market_types.get(market_type, 0) + 1
        
        return {
            'total_examples': total_examples,
            'averages': {
                'odds': round(avg_odds, 2),
                'legs_count': round(avg_legs, 1),
                'confidence_score': round(avg_confidence, 3),
                'success_score': round(avg_success_score, 3)
            },
            'market_type_distribution': market_types,
            'success_score_range': {
                'min': min(ex.success_metrics['success_score'] for ex in self.few_shot_examples),
                'max': max(ex.success_metrics['success_score'] for ex in self.few_shot_examples)
            }
        }


def main():
    """Main function for few-shot example extraction."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        print("🎯 Few-Shot Parlay Extractor - JIRA-020")
        print("=" * 60)
        
        # Initialize extractor
        extractor = FewShotParlayExtractor()
        
        # Extract successful examples
        print("🔍 Extracting successful high-confidence parlays...")
        examples = extractor.extract_successful_examples(num_examples=10)
        
        if not examples:
            print("❌ No successful examples found!")
            return
        
        # Show statistics
        stats = extractor.get_stats()
        print(f"\n📈 Few-Shot Examples Statistics:")
        print(f"Total Examples: {stats['total_examples']}")
        print(f"Average Odds: {stats['averages']['odds']}")
        print(f"Average Legs: {stats['averages']['legs_count']}")
        print(f"Average Confidence: {stats['averages']['confidence_score']}")
        print(f"Average Success Score: {stats['averages']['success_score']}")
        print(f"Success Score Range: {stats['success_score_range']['min']:.2f} - {stats['success_score_range']['max']:.2f}")
        
        print(f"\nMarket Type Distribution:")
        for market_type, count in stats['market_type_distribution'].items():
            print(f"  {market_type}: {count}")
        
        # Save examples
        print(f"\n💾 Saving few-shot examples...")
        extractor.save_few_shot_examples()
        
        # Show sample prompt format
        print(f"\n📝 Sample Few-Shot Prompt Format:")
        print("=" * 50)
        sample_prompt = extractor.format_for_few_shot_prompting()
        print(sample_prompt[:1000] + "..." if len(sample_prompt) > 1000 else sample_prompt)
        
        print(f"\n✅ Few-shot extraction complete!")
        print(f"📁 Examples saved to: data/few_shot_parlay_examples.json")
        print(f"🎯 Ready for integration into ParlayStrategistAgent")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
