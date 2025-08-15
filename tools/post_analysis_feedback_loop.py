#!/usr/bin/env python3
"""
Post-Analysis Feedback Loop System - JIRA-020B

Automates weekly analysis of bet performance vs confidence scores to:
- Flag poor-performing high-confidence bets for review
- Identify successful reasoning patterns for few-shot learning
- Trigger RoBERTa model retraining with new labeled data
- Maintain feedback loop for continuous improvement
"""

import logging
import sqlite3
import json
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
import re
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)


@dataclass
class BetPerformanceAnalysis:
    """Analysis of bet performance metrics."""
    bet_id: str
    confidence_score: float
    bayesian_confidence: float
    predicted_outcome: str
    actual_outcome: str
    win_loss: bool
    reasoning_text: str
    reasoning_length: int
    confidence_accuracy: float  # How well confidence predicted outcome
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReasoningPattern:
    """Identified reasoning pattern for analysis."""
    pattern_id: str
    pattern_type: str  # "successful", "failing", "keyword", "structure"
    pattern_text: str
    confidence_range: Tuple[float, float]
    win_rate: float
    sample_count: int
    avg_confidence: float
    examples: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FeedbackReport:
    """Weekly feedback analysis report."""
    analysis_period: str
    total_bets: int
    overall_win_rate: float
    confidence_calibration: Dict[str, float]
    flagged_patterns: List[ReasoningPattern]
    successful_patterns: List[ReasoningPattern]
    few_shot_candidates: List[Dict[str, Any]]
    retraining_recommendation: bool
    retraining_data_size: int
    improvement_suggestions: List[str]
    timestamp: str


class PostAnalysisFeedbackLoop:
    """
    Main feedback loop system for post-analysis and model improvement.
    
    Analyzes bet performance, identifies patterns, and provides feedback
    for improving LLM prompts and RoBERTa calibration.
    """
    
    def __init__(self, 
                 db_path: str = "data/parlays.sqlite",
                 min_confidence_samples: int = 10,
                 high_confidence_threshold: float = 0.8,
                 low_win_rate_threshold: float = 0.4):
        """
        Initialize the feedback loop system.
        
        Args:
            db_path: Path to the bets database
            min_confidence_samples: Minimum samples needed for pattern analysis
            high_confidence_threshold: Threshold for "high confidence" bets
            low_win_rate_threshold: Threshold for flagging poor performance
        """
        self.db_path = Path(db_path)
        self.min_confidence_samples = min_confidence_samples
        self.high_confidence_threshold = high_confidence_threshold
        self.low_win_rate_threshold = low_win_rate_threshold
        
        # Pattern detection settings
        self.keyword_patterns = {
            "sharp_money": ["sharp", "syndicate", "professional", "wise guy"],
            "injury_intel": ["injury", "out", "questionable", "dtd"],
            "line_movement": ["moved", "steam", "line movement"],
            "public_betting": ["public", "casual", "square", "chalk"],
            "model_based": ["model", "algorithm", "projection", "expected"],
            "historical": ["historically", "trend", "pattern", "last"],
            "situational": ["back-to-back", "revenge", "lookahead", "schedule"]
        }
        
        logger.info(f"Initialized PostAnalysisFeedbackLoop with db: {db_path}")
    
    def extract_bet_performance_data(self, 
                                   days_back: int = 7,
                                   min_bets: int = 5) -> List[BetPerformanceAnalysis]:
        """
        Extract bet performance data from the database.
        
        Args:
            days_back: Number of days to look back for analysis
            min_bets: Minimum number of bets required for analysis
            
        Returns:
            List of bet performance analyses
        """
        if not self.db_path.exists():
            logger.warning(f"Database not found: {self.db_path}")
            return []
        
        # Calculate date range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days_back)
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            
            # Query bets with outcomes (use existing schema)
            query = """
            SELECT 
                bet_id as id,
                reasoning,
                confidence_score,
                confidence_score as bayesian_confidence,
                'win' as predicted_outcome,
                CASE 
                    WHEN outcome = 'won' THEN 'win'
                    WHEN outcome = 'lost' THEN 'loss'
                    ELSE outcome
                END as actual_outcome,
                timestamp as created_at,
                '{}' as metadata
            FROM bets 
            WHERE timestamp >= ? 
            AND timestamp <= ?
            AND outcome IS NOT NULL
            ORDER BY timestamp DESC
            """
            
            cursor = conn.execute(query, (start_date.isoformat(), end_date.isoformat()))
            rows = cursor.fetchall()
            
            if len(rows) < min_bets:
                logger.warning(f"Insufficient bet data: {len(rows)} < {min_bets}")
                return []
            
            analyses = []
            for row in rows:
                # Parse metadata
                metadata = {}
                try:
                    if row['metadata']:
                        metadata = json.loads(row['metadata'])
                except (json.JSONDecodeError, KeyError):
                    pass
                
                # Determine win/loss
                win_loss = row['actual_outcome'] == 'win'
                
                # Calculate confidence accuracy (how well confidence predicted outcome)
                confidence_score = row['confidence_score'] or 0.5
                if win_loss:
                    confidence_accuracy = confidence_score
                else:
                    confidence_accuracy = 1.0 - confidence_score
                
                analysis = BetPerformanceAnalysis(
                    bet_id=str(row['id']),
                    confidence_score=confidence_score,
                    bayesian_confidence=row['bayesian_confidence'] or 0.5,
                    predicted_outcome=row['predicted_outcome'] or 'unknown',
                    actual_outcome=row['actual_outcome'],
                    win_loss=win_loss,
                    reasoning_text=row['parlay_reasoning'] or '',
                    reasoning_length=len(row['parlay_reasoning'] or ''),
                    confidence_accuracy=confidence_accuracy,
                    timestamp=row['created_at'],
                    metadata=metadata
                )
                analyses.append(analysis)
            
            conn.close()
            logger.info(f"Extracted {len(analyses)} bet analyses from {days_back} days")
            return analyses
            
        except Exception as e:
            logger.error(f"Failed to extract bet performance data: {e}")
            return []
    
    def analyze_confidence_calibration(self, 
                                     analyses: List[BetPerformanceAnalysis]) -> Dict[str, float]:
        """
        Analyze how well confidence scores are calibrated with actual outcomes.
        
        Args:
            analyses: List of bet performance analyses
            
        Returns:
            Calibration metrics by confidence range
        """
        if not analyses:
            return {}
        
        # Group by confidence ranges
        confidence_bins = {
            "very_low": (0.0, 0.4),
            "low": (0.4, 0.6),
            "medium": (0.6, 0.75),
            "high": (0.75, 0.9),
            "very_high": (0.9, 1.0)
        }
        
        calibration = {}
        
        for bin_name, (min_conf, max_conf) in confidence_bins.items():
            bin_analyses = [a for a in analyses 
                          if min_conf <= a.confidence_score < max_conf]
            
            if len(bin_analyses) >= 3:  # Minimum for meaningful analysis
                win_rate = sum(a.win_loss for a in bin_analyses) / len(bin_analyses)
                avg_confidence = sum(a.confidence_score for a in bin_analyses) / len(bin_analyses)
                
                # Calibration error: how far off is win rate from confidence
                calibration_error = abs(win_rate - avg_confidence)
                
                calibration[bin_name] = {
                    "sample_count": len(bin_analyses),
                    "win_rate": win_rate,
                    "avg_confidence": avg_confidence,
                    "calibration_error": calibration_error,
                    "well_calibrated": calibration_error < 0.1  # Within 10%
                }
        
        return calibration
    
    def identify_failing_patterns(self, 
                                analyses: List[BetPerformanceAnalysis]) -> List[ReasoningPattern]:
        """
        Identify reasoning patterns associated with poor performance.
        
        Args:
            analyses: List of bet performance analyses
            
        Returns:
            List of failing reasoning patterns
        """
        failing_patterns = []
        
        # Focus on high-confidence bets that failed
        high_conf_failures = [a for a in analyses 
                            if a.confidence_score >= self.high_confidence_threshold 
                            and not a.win_loss]
        
        if len(high_conf_failures) < self.min_confidence_samples:
            logger.info("Insufficient high-confidence failures for pattern analysis")
            return failing_patterns
        
        # Analyze keyword patterns
        for pattern_name, keywords in self.keyword_patterns.items():
            pattern_analyses = []
            
            for analysis in high_conf_failures:
                text_lower = analysis.reasoning_text.lower()
                if any(keyword in text_lower for keyword in keywords):
                    pattern_analyses.append(analysis)
            
            if len(pattern_analyses) >= 3:  # Minimum for pattern significance
                win_rate = sum(a.win_loss for a in pattern_analyses) / len(pattern_analyses)
                
                if win_rate < self.low_win_rate_threshold:
                    pattern = ReasoningPattern(
                        pattern_id=f"failing_{pattern_name}",
                        pattern_type="failing",
                        pattern_text=f"Contains keywords: {', '.join(keywords)}",
                        confidence_range=(
                            min(a.confidence_score for a in pattern_analyses),
                            max(a.confidence_score for a in pattern_analyses)
                        ),
                        win_rate=win_rate,
                        sample_count=len(pattern_analyses),
                        avg_confidence=sum(a.confidence_score for a in pattern_analyses) / len(pattern_analyses),
                        examples=[a.reasoning_text[:200] + "..." for a in pattern_analyses[:3]],
                        metadata={
                            "keywords": keywords,
                            "failure_rate": 1.0 - win_rate,
                            "pattern_category": pattern_name
                        }
                    )
                    failing_patterns.append(pattern)
        
        # Analyze structural patterns
        failing_patterns.extend(self._analyze_structural_patterns(high_conf_failures))
        
        return failing_patterns
    
    def identify_successful_patterns(self, 
                                   analyses: List[BetPerformanceAnalysis]) -> List[ReasoningPattern]:
        """
        Identify reasoning patterns associated with strong performance.
        
        Args:
            analyses: List of bet performance analyses
            
        Returns:
            List of successful reasoning patterns
        """
        successful_patterns = []
        
        # Focus on high-confidence bets that succeeded
        high_conf_successes = [a for a in analyses 
                             if a.confidence_score >= self.high_confidence_threshold 
                             and a.win_loss]
        
        if len(high_conf_successes) < self.min_confidence_samples:
            logger.info("Insufficient high-confidence successes for pattern analysis")
            return successful_patterns
        
        # Analyze keyword patterns
        for pattern_name, keywords in self.keyword_patterns.items():
            pattern_analyses = []
            
            for analysis in high_conf_successes:
                text_lower = analysis.reasoning_text.lower()
                if any(keyword in text_lower for keyword in keywords):
                    pattern_analyses.append(analysis)
            
            if len(pattern_analyses) >= 3:  # Minimum for pattern significance
                win_rate = sum(a.win_loss for a in pattern_analyses) / len(pattern_analyses)
                
                if win_rate > 0.75:  # Strong success rate
                    pattern = ReasoningPattern(
                        pattern_id=f"successful_{pattern_name}",
                        pattern_type="successful",
                        pattern_text=f"Contains keywords: {', '.join(keywords)}",
                        confidence_range=(
                            min(a.confidence_score for a in pattern_analyses),
                            max(a.confidence_score for a in pattern_analyses)
                        ),
                        win_rate=win_rate,
                        sample_count=len(pattern_analyses),
                        avg_confidence=sum(a.confidence_score for a in pattern_analyses) / len(pattern_analyses),
                        examples=[a.reasoning_text[:200] + "..." for a in pattern_analyses[:3]],
                        metadata={
                            "keywords": keywords,
                            "success_rate": win_rate,
                            "pattern_category": pattern_name
                        }
                    )
                    successful_patterns.append(pattern)
        
        return successful_patterns
    
    def _analyze_structural_patterns(self, 
                                   analyses: List[BetPerformanceAnalysis]) -> List[ReasoningPattern]:
        """
        Analyze structural patterns in reasoning text.
        
        Args:
            analyses: List of bet performance analyses
            
        Returns:
            List of structural reasoning patterns
        """
        patterns = []
        
        # Analyze by reasoning length
        length_groups = {
            "short": [a for a in analyses if a.reasoning_length < 200],
            "medium": [a for a in analyses if 200 <= a.reasoning_length < 800],
            "long": [a for a in analyses if a.reasoning_length >= 800]
        }
        
        for length_type, group_analyses in length_groups.items():
            if len(group_analyses) >= 3:
                win_rate = sum(a.win_loss for a in group_analyses) / len(group_analyses)
                
                if win_rate < self.low_win_rate_threshold:
                    pattern = ReasoningPattern(
                        pattern_id=f"failing_length_{length_type}",
                        pattern_type="failing",
                        pattern_text=f"Reasoning length: {length_type}",
                        confidence_range=(
                            min(a.confidence_score for a in group_analyses),
                            max(a.confidence_score for a in group_analyses)
                        ),
                        win_rate=win_rate,
                        sample_count=len(group_analyses),
                        avg_confidence=sum(a.confidence_score for a in group_analyses) / len(group_analyses),
                        examples=[],
                        metadata={
                            "structural_type": "length",
                            "length_category": length_type,
                            "avg_length": sum(a.reasoning_length for a in group_analyses) / len(group_analyses)
                        }
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def generate_few_shot_candidates(self, 
                                   successful_patterns: List[ReasoningPattern],
                                   analyses: List[BetPerformanceAnalysis]) -> List[Dict[str, Any]]:
        """
        Generate candidates for few-shot learning updates.
        
        Args:
            successful_patterns: List of successful reasoning patterns
            analyses: List of bet performance analyses
            
        Returns:
            List of few-shot learning candidates
        """
        candidates = []
        
        # Find best examples from successful patterns
        for pattern in successful_patterns:
            if pattern.win_rate > 0.8 and pattern.sample_count >= 5:
                # Find the best examples from this pattern
                pattern_analyses = []
                
                for analysis in analyses:
                    if (analysis.confidence_score >= pattern.confidence_range[0] and
                        analysis.confidence_score <= pattern.confidence_range[1] and
                        analysis.win_loss):
                        
                        # Check if analysis matches pattern keywords
                        if pattern.metadata.get("keywords"):
                            text_lower = analysis.reasoning_text.lower()
                            if any(keyword in text_lower for keyword in pattern.metadata["keywords"]):
                                pattern_analyses.append(analysis)
                
                # Sort by confidence and take top examples
                pattern_analyses.sort(key=lambda x: x.confidence_score, reverse=True)
                
                for analysis in pattern_analyses[:2]:  # Top 2 examples per pattern
                    candidate = {
                        "example_id": f"pattern_{pattern.pattern_id}_{analysis.bet_id}",
                        "reasoning_text": analysis.reasoning_text,
                        "confidence_score": analysis.confidence_score,
                        "actual_outcome": analysis.actual_outcome,
                        "pattern_type": pattern.pattern_type,
                        "pattern_category": pattern.metadata.get("pattern_category"),
                        "win_rate": pattern.win_rate,
                        "quality_score": analysis.confidence_score * pattern.win_rate,
                        "metadata": {
                            "pattern_id": pattern.pattern_id,
                            "pattern_sample_count": pattern.sample_count,
                            "bet_timestamp": analysis.timestamp
                        }
                    }
                    candidates.append(candidate)
        
        # Sort by quality score and return top candidates
        candidates.sort(key=lambda x: x["quality_score"], reverse=True)
        return candidates[:10]  # Top 10 candidates
    
    def assess_retraining_need(self, 
                             analyses: List[BetPerformanceAnalysis],
                             calibration: Dict[str, float]) -> Tuple[bool, int]:
        """
        Assess whether RoBERTa model retraining is needed.
        
        Args:
            analyses: List of bet performance analyses
            calibration: Confidence calibration metrics
            
        Returns:
            Tuple of (should_retrain, data_size)
        """
        if len(analyses) < 50:  # Need sufficient data for retraining
            return False, len(analyses)
        
        # Check calibration quality
        poorly_calibrated_bins = 0
        total_bins = 0
        
        for bin_name, metrics in calibration.items():
            if isinstance(metrics, dict):
                total_bins += 1
                if not metrics.get("well_calibrated", False):
                    poorly_calibrated_bins += 1
        
        # Retrain if more than 50% of bins are poorly calibrated
        calibration_poor = (poorly_calibrated_bins / max(total_bins, 1)) > 0.5
        
        # Check overall accuracy
        correct_predictions = sum(1 for a in analyses if a.confidence_accuracy > 0.6)
        overall_accuracy = correct_predictions / len(analyses)
        accuracy_poor = overall_accuracy < 0.65
        
        # Check data recency (retrain if significant new data)
        recent_analyses = [a for a in analyses 
                         if (datetime.now(timezone.utc) - 
                             datetime.fromisoformat(a.timestamp.replace('Z', '+00:00'))).days <= 14]
        significant_new_data = len(recent_analyses) >= 30
        
        should_retrain = (calibration_poor or accuracy_poor or significant_new_data)
        
        return should_retrain, len(analyses)
    
    def generate_improvement_suggestions(self, 
                                       failing_patterns: List[ReasoningPattern],
                                       calibration: Dict[str, float]) -> List[str]:
        """
        Generate specific improvement suggestions based on analysis.
        
        Args:
            failing_patterns: List of failing reasoning patterns
            calibration: Confidence calibration metrics
            
        Returns:
            List of improvement suggestions
        """
        suggestions = []
        
        # Suggestions based on failing patterns
        for pattern in failing_patterns:
            if pattern.pattern_type == "failing":
                category = pattern.metadata.get("pattern_category", "unknown")
                failure_rate = pattern.metadata.get("failure_rate", 0)
                
                suggestions.append(
                    f"⚠️ {category.title()} patterns show {failure_rate:.1%} failure rate "
                    f"with {pattern.sample_count} high-confidence bets. "
                    f"Consider reducing weight or adding additional validation."
                )
        
        # Suggestions based on calibration
        for bin_name, metrics in calibration.items():
            if isinstance(metrics, dict) and not metrics.get("well_calibrated", True):
                error = metrics.get("calibration_error", 0)
                win_rate = metrics.get("win_rate", 0)
                confidence = metrics.get("avg_confidence", 0)
                
                if win_rate < confidence:
                    suggestions.append(
                        f"📉 {bin_name.title()} confidence bets are overconfident: "
                        f"{confidence:.1%} confidence vs {win_rate:.1%} win rate. "
                        f"Consider lowering confidence thresholds."
                    )
                else:
                    suggestions.append(
                        f"📈 {bin_name.title()} confidence bets are underconfident: "
                        f"{confidence:.1%} confidence vs {win_rate:.1%} win rate. "
                        f"Consider raising confidence scores."
                    )
        
        # General suggestions
        if len(failing_patterns) > 3:
            suggestions.append(
                "🔄 Multiple failing patterns detected. Consider comprehensive "
                "prompt engineering review and additional validation layers."
            )
        
        return suggestions
    
    def run_weekly_analysis(self, days_back: int = 7) -> FeedbackReport:
        """
        Run complete weekly analysis and generate feedback report.
        
        Args:
            days_back: Number of days to analyze
            
        Returns:
            Complete feedback report
        """
        logger.info(f"Starting weekly analysis for last {days_back} days")
        
        # Extract performance data
        analyses = self.extract_bet_performance_data(days_back)
        
        if not analyses:
            logger.warning("No bet data available for analysis")
            return FeedbackReport(
                analysis_period=f"Last {days_back} days",
                total_bets=0,
                overall_win_rate=0.0,
                confidence_calibration={},
                flagged_patterns=[],
                successful_patterns=[],
                few_shot_candidates=[],
                retraining_recommendation=False,
                retraining_data_size=0,
                improvement_suggestions=["No bet data available for analysis"],
                timestamp=datetime.now(timezone.utc).isoformat()
            )
        
        # Perform analyses
        overall_win_rate = sum(a.win_loss for a in analyses) / len(analyses)
        calibration = self.analyze_confidence_calibration(analyses)
        failing_patterns = self.identify_failing_patterns(analyses)
        successful_patterns = self.identify_successful_patterns(analyses)
        few_shot_candidates = self.generate_few_shot_candidates(successful_patterns, analyses)
        should_retrain, data_size = self.assess_retraining_need(analyses, calibration)
        suggestions = self.generate_improvement_suggestions(failing_patterns, calibration)
        
        # Create report
        report = FeedbackReport(
            analysis_period=f"Last {days_back} days",
            total_bets=len(analyses),
            overall_win_rate=overall_win_rate,
            confidence_calibration=calibration,
            flagged_patterns=failing_patterns,
            successful_patterns=successful_patterns,
            few_shot_candidates=few_shot_candidates,
            retraining_recommendation=should_retrain,
            retraining_data_size=data_size,
            improvement_suggestions=suggestions,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        logger.info(f"Weekly analysis complete: {len(analyses)} bets, "
                   f"{overall_win_rate:.1%} win rate, "
                   f"{len(failing_patterns)} failing patterns, "
                   f"{len(successful_patterns)} successful patterns")
        
        return report
    
    def save_report(self, report: FeedbackReport, output_path: str = None) -> str:
        """
        Save feedback report to file.
        
        Args:
            report: Feedback report to save
            output_path: Optional output path
            
        Returns:
            Path where report was saved
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"data/feedback_reports/weekly_analysis_{timestamp}.json"
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert report to JSON-serializable format
        report_dict = asdict(report)
        
        with open(output_file, 'w') as f:
            json.dump(report_dict, f, indent=2, default=str)
        
        logger.info(f"Feedback report saved to {output_file}")
        return str(output_file)
    
    def print_report_summary(self, report: FeedbackReport):
        """Print a human-readable summary of the feedback report."""
        print("📊 WEEKLY FEEDBACK ANALYSIS REPORT")
        print("=" * 50)
        print(f"Analysis Period: {report.analysis_period}")
        print(f"Total Bets Analyzed: {report.total_bets}")
        print(f"Overall Win Rate: {report.overall_win_rate:.1%}")
        
        print(f"\n🎯 CONFIDENCE CALIBRATION")
        print("-" * 30)
        for bin_name, metrics in report.confidence_calibration.items():
            if isinstance(metrics, dict):
                status = "✅" if metrics.get("well_calibrated") else "⚠️"
                print(f"{status} {bin_name.title()}: {metrics['win_rate']:.1%} win rate, "
                      f"{metrics['avg_confidence']:.1%} avg confidence "
                      f"({metrics['sample_count']} bets)")
        
        print(f"\n🚨 FLAGGED PATTERNS ({len(report.flagged_patterns)})")
        print("-" * 30)
        for pattern in report.flagged_patterns:
            print(f"⚠️ {pattern.pattern_id}: {pattern.win_rate:.1%} win rate "
                  f"({pattern.sample_count} samples)")
            print(f"   Pattern: {pattern.pattern_text}")
        
        print(f"\n✅ SUCCESSFUL PATTERNS ({len(report.successful_patterns)})")
        print("-" * 30)
        for pattern in report.successful_patterns:
            print(f"🎯 {pattern.pattern_id}: {pattern.win_rate:.1%} win rate "
                  f"({pattern.sample_count} samples)")
        
        print(f"\n🎓 FEW-SHOT CANDIDATES ({len(report.few_shot_candidates)})")
        print("-" * 30)
        for candidate in report.few_shot_candidates[:3]:  # Show top 3
            print(f"📚 Quality Score: {candidate['quality_score']:.3f} "
                  f"(Confidence: {candidate['confidence_score']:.3f})")
            print(f"   Category: {candidate.get('pattern_category', 'Unknown')}")
        
        print(f"\n🔄 RETRAINING RECOMMENDATION")
        print("-" * 30)
        status = "✅ RECOMMENDED" if report.retraining_recommendation else "⏳ Not needed"
        print(f"{status} - Available data: {report.retraining_data_size} samples")
        
        print(f"\n💡 IMPROVEMENT SUGGESTIONS")
        print("-" * 30)
        for suggestion in report.improvement_suggestions:
            print(f"• {suggestion}")


def main():
    """Main function for testing the feedback loop system."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🔄 Post-Analysis Feedback Loop System - JIRA-020B")
    print("=" * 60)
    
    # Initialize feedback loop
    feedback_loop = PostAnalysisFeedbackLoop(
        db_path="data/parlays.sqlite",
        min_confidence_samples=5,  # Lower for demo
        high_confidence_threshold=0.75,
        low_win_rate_threshold=0.45
    )
    
    # Run weekly analysis
    print("📊 Running weekly analysis...")
    report = feedback_loop.run_weekly_analysis(days_back=30)  # 30 days for demo
    
    # Print summary
    feedback_loop.print_report_summary(report)
    
    # Save report
    report_path = feedback_loop.save_report(report)
    print(f"\n💾 Report saved to: {report_path}")
    
    print(f"\n✅ JIRA-020B Post-Analysis Feedback Loop Complete!")
    print(f"🎯 Automated weekly analysis system ready for deployment")


if __name__ == "__main__":
    main()
