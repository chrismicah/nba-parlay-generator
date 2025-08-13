#!/usr/bin/env python3
"""
Tests for performance reporter functionality.
"""

import json
import pytest
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

from scripts.performance_reporter import (
    infer_bet_type, infer_bookmaker, compute_leg_profit, 
    rollup_metrics, summarize_clv, get_leaders_laggards
)


class TestPerformanceReporter:
    """Test suite for performance reporter functionality."""
    
    @pytest.fixture
    def temp_db_path(self, tmp_path):
        """Create temporary database path."""
        return tmp_path / "test_performance.sqlite"
    
    @pytest.fixture
    def sample_rows(self):
        """Create sample bet rows for testing."""
        # Mock sqlite3.Row objects
        rows = []
        
        # Win bets
        row1 = MagicMock()
        row1.__getitem__ = lambda self, key: {
            'bet_id': 1,
            'parlay_id': 'parlay1',
            'game_id': 'game1',
            'leg_description': 'LAL -2.5 spread',
            'odds': 1.91,
            'stake': 10.0,
            'is_win': 1,
            'created_at': '2025-01-15T19:30:00Z',
            'actual_outcome': 'win',
            'clv_percentage': 3.2
        }[key]
        row1.keys = lambda: ['clv_percentage']
        rows.append(row1)
        
        row2 = MagicMock()
        row2.__getitem__ = lambda self, key: {
            'bet_id': 2,
            'parlay_id': 'parlay1',
            'game_id': 'game1',
            'leg_description': 'Over 220.5 total',
            'odds': 1.87,
            'stake': 10.0,
            'is_win': 1,
            'created_at': '2025-01-15T19:30:00Z',
            'actual_outcome': 'win',
            'clv_percentage': 1.5
        }[key]
        row2.keys = lambda: ['clv_percentage']
        rows.append(row2)
        
        # Loss bets
        row3 = MagicMock()
        row3.__getitem__ = lambda self, key: {
            'bet_id': 3,
            'parlay_id': 'parlay2',
            'game_id': 'game2',
            'leg_description': 'GSW moneyline',
            'odds': 2.10,
            'stake': 15.0,
            'is_win': 0,
            'created_at': '2025-01-16T20:00:00Z',
            'actual_outcome': 'loss',
            'clv_percentage': -2.1
        }[key]
        row3.keys = lambda: ['clv_percentage']
        rows.append(row3)
        
        row4 = MagicMock()
        row4.__getitem__ = lambda self, key: {
            'bet_id': 4,
            'parlay_id': 'parlay2',
            'game_id': 'game2',
            'leg_description': 'Jokic 25 points',
            'odds': 1.95,
            'stake': 12.0,
            'is_win': 0,
            'created_at': '2025-01-16T20:00:00Z',
            'actual_outcome': 'loss',
            'clv_percentage': -1.8
        }[key]
        row4.keys = lambda: ['clv_percentage']
        rows.append(row4)
        
        # Push bet
        row5 = MagicMock()
        row5.__getitem__ = lambda self, key: {
            'bet_id': 5,
            'parlay_id': 'parlay3',
            'game_id': 'game3',
            'leg_description': 'BOS +3.5 spread',
            'odds': 1.90,
            'stake': 8.0,
            'is_win': 0,
            'created_at': '2025-01-17T18:30:00Z',
            'actual_outcome': 'push',
            'clv_percentage': 0.5
        }[key]
        row5.keys = lambda: ['clv_percentage']
        rows.append(row5)
        
        # Open bet
        row6 = MagicMock()
        row6.__getitem__ = lambda self, key: {
            'bet_id': 6,
            'parlay_id': 'parlay4',
            'game_id': 'game4',
            'leg_description': 'Under 215.5 total',
            'odds': 1.88,
            'stake': 20.0,
            'is_win': None,
            'created_at': '2025-01-18T21:00:00Z',
            'actual_outcome': None,
            'clv_percentage': None
        }[key]
        row6.keys = lambda: ['clv_percentage']
        rows.append(row6)
        
        # Zero stake bet (should be skipped)
        row7 = MagicMock()
        row7.__getitem__ = lambda self, key: {
            'bet_id': 7,
            'parlay_id': 'parlay5',
            'game_id': 'game5',
            'leg_description': 'Some random bet',
            'odds': 1.85,
            'stake': 0.0,
            'is_win': 1,
            'created_at': '2025-01-19T19:00:00Z',
            'actual_outcome': 'win',
            'clv_percentage': 0.0
        }[key]
        row7.keys = lambda: ['clv_percentage']
        rows.append(row7)
        
        return rows
    
    def test_infer_bet_type(self):
        """Test bet type inference from leg descriptions."""
        # Test h2h/moneyline
        assert infer_bet_type("LAL moneyline") == "h2h"
        assert infer_bet_type("GSW h2h") == "h2h"
        assert infer_bet_type("BOS ML") == "h2h"
        
        # Test spreads
        assert infer_bet_type("LAL -2.5 spread") == "spreads"
        assert infer_bet_type("GSW +3.5 line") == "spreads"
        assert infer_bet_type("BOS +2 pts") == "spreads"
        assert infer_bet_type("ATS pick") == "spreads"
        
        # Test totals
        assert infer_bet_type("Over 220.5 total") == "totals"
        assert infer_bet_type("Under 215.5") == "totals"
        assert infer_bet_type("O/ 225.5") == "totals"
        assert infer_bet_type("U/ 210.5") == "totals"
        
        # Test player props
        assert infer_bet_type("Jokic 25 points") == "player_prop"
        assert infer_bet_type("LeBron 8 assists") == "player_prop"
        assert infer_bet_type("Curry 5 rebounds") == "player_prop"
        assert infer_bet_type("PRA over 35") == "player_prop"
        assert infer_bet_type("stat line") == "player_prop"
        
        # Test unknown
        assert infer_bet_type("Unknown bet") == "unknown"
    
    def test_infer_bookmaker(self):
        """Test bookmaker inference from leg descriptions."""
        assert infer_bookmaker("LAL -2.5 [Book: FanDuel]") == "FanDuel"
        assert infer_bookmaker("GSW +3.5 Book: DraftKings") == "DraftKings"
        assert infer_bookmaker("Over 220.5 [Book: BetMGM]") == "BetMGM"
        assert infer_bookmaker("No bookmaker info") == ""
    
    def test_compute_leg_profit(self):
        """Test profit computation for different bet outcomes."""
        # Win bet
        profit = compute_leg_profit(1.91, 10.0, 1, "win")
        assert profit == 10.0 * (1.91 - 1)  # 9.10
        
        # Loss bet
        profit = compute_leg_profit(2.10, 15.0, 0, "loss")
        assert profit == -15.0
        
        # Push bet
        profit = compute_leg_profit(1.90, 8.0, 0, "push")
        assert profit == 0.0
        
        # Open bet
        profit = compute_leg_profit(1.88, 20.0, None, None)
        assert profit is None
        
        # Push with different case
        profit = compute_leg_profit(1.90, 8.0, 0, "PUSH")
        assert profit == 0.0
    
    def test_rollup_metrics_by_bet_type(self, sample_rows):
        """Test metrics rollup grouped by bet type."""
        groups = rollup_metrics(sample_rows, "bet_type", include_open=False)
        
        # Check that we have the expected groups (zero stake bet is skipped)
        assert "spreads" in groups
        assert "totals" in groups
        assert "h2h" in groups
        assert "player_prop" in groups
        # Note: "unknown" group won't exist because the zero stake bet is skipped
        
        # Check spreads group (1 win, 1 push)
        spreads = groups["spreads"]
        assert spreads['count_total'] == 2
        assert spreads['count_decided'] == 2
        assert spreads['wins'] == 1
        assert spreads['losses'] == 0
        assert spreads['pushes'] == 1
        assert spreads['stake_sum'] == 18.0  # 10 + 8
        assert spreads['profit_sum'] == 9.10  # win profit only (push = 0)
        assert spreads['roi_pct'] == pytest.approx(50.56, rel=1e-2)  # 9.10/18.0 * 100
        assert spreads['hit_rate_pct'] == 100.0  # 1 win / (1 win + 0 loss)
        
        # Check totals group (1 win, 1 open)
        totals = groups["totals"]
        assert totals['count_total'] == 2
        assert totals['count_decided'] == 1  # open bet excluded
        assert totals['count_open'] == 1
        assert totals['wins'] == 1
        assert totals['losses'] == 0
        assert totals['stake_sum'] == 30.0  # 10 + 20
        assert totals['profit_sum'] == pytest.approx(8.70, rel=1e-2)  # 10 * (1.87 - 1)
        assert totals['roi_pct'] == pytest.approx(29.0, rel=1e-2)  # 8.70/30.0 * 100
        assert totals['hit_rate_pct'] == 100.0
    
    def test_rollup_metrics_include_open(self, sample_rows):
        """Test metrics rollup with open bets included."""
        groups = rollup_metrics(sample_rows, "bet_type", include_open=True)
        
        # Check totals group with open bets included
        totals = groups["totals"]
        assert totals['count_total'] == 2
        assert totals['count_decided'] == 1
        assert totals['count_open'] == 1
        assert totals['stake_sum'] == 30.0  # Both bets counted
        assert totals['profit_sum'] == pytest.approx(8.70, rel=1e-2)  # Only decided bet counted
    
    def test_rollup_metrics_by_day(self, sample_rows):
        """Test metrics rollup grouped by day."""
        groups = rollup_metrics(sample_rows, "day", include_open=False)
        
        # Check that we have the expected date groups
        assert "2025-01-15" in groups
        assert "2025-01-16" in groups
        assert "2025-01-17" in groups
        assert "2025-01-18" in groups
        
        # Check 2025-01-15 (2 wins)
        day1 = groups["2025-01-15"]
        assert day1['count_total'] == 2
        assert day1['count_decided'] == 2
        assert day1['wins'] == 2
        assert day1['losses'] == 0
        assert day1['profit_sum'] == pytest.approx(17.80, rel=1e-2)  # 9.10 + 8.70
    
    def test_rollup_metrics_by_bookmaker(self, sample_rows):
        """Test metrics rollup grouped by bookmaker."""
        groups = rollup_metrics(sample_rows, "bookmaker", include_open=False)
        
        # All bets should be "unknown" since no bookmaker info in descriptions
        assert "unknown" in groups
        assert len(groups) == 1
    
    def test_rollup_metrics_zero_stake_skipped(self, sample_rows):
        """Test that zero stake bets are skipped with warning."""
        with patch('scripts.performance_reporter.logger') as mock_logger:
            groups = rollup_metrics(sample_rows, "bet_type", include_open=False)
            
            # Check that warning was logged
            mock_logger.warning.assert_called_with("Zero or missing stake for bet_id 7")
            
            # Check that the bet was not included in any group
            total_bets = sum(g['count_total'] for g in groups.values())
            assert total_bets == 6  # 7 total bets - 1 zero stake = 6
    
    def test_summarize_clv_present(self, sample_rows):
        """Test CLV summary when CLV data is present."""
        clv_summary = summarize_clv(sample_rows)
        
        assert clv_summary is not None
        assert clv_summary['count_clv'] == 5  # 5 bets with CLV data
        assert clv_summary['clv_min'] == -2.1
        assert clv_summary['clv_max'] == 3.2
        assert clv_summary['clv_mean'] == pytest.approx(0.26, rel=1e-2)  # (3.2+1.5-2.1-1.8+0.5)/5
        assert clv_summary['clv_median'] == 0.5
    
    def test_summarize_clv_missing(self):
        """Test CLV summary when CLV data is missing."""
        # Create rows without CLV data
        rows = [
            MagicMock(**{
                'bet_id': 1,
                'keys': lambda: ['other_column'],
                'clv_percentage': None
            })
        ]
        
        clv_summary = summarize_clv(rows)
        assert clv_summary is None
    
    def test_get_leaders_laggards(self, sample_rows):
        """Test getting top and bottom performing legs."""
        groups = rollup_metrics(sample_rows, "bet_type", include_open=False)
        leaders, laggards = get_leaders_laggards(groups, top_n=3)
        
        # Check leaders (sorted by profit descending)
        assert len(leaders) == 3
        assert leaders[0]['profit'] == pytest.approx(9.10, rel=1e-2)  # LAL -2.5 spread win
        assert leaders[1]['profit'] == pytest.approx(8.70, rel=1e-2)  # Over 220.5 total win
        assert leaders[2]['profit'] == 0.0  # Push bet
        
        # Check laggards (sorted by profit ascending)
        assert len(laggards) == 3
        assert laggards[0]['profit'] == -15.0  # GSW moneyline loss
        assert laggards[1]['profit'] == -12.0  # Jokic 25 points loss
        assert laggards[2]['profit'] == 0.0  # Push bet
    
    def test_roi_and_hit_rate_overall(self, sample_rows):
        """Test overall ROI and hit rate calculations."""
        groups = rollup_metrics(sample_rows, "bet_type", include_open=False)
        
        # Calculate overall metrics
        overall = {
            'count_total': sum(g['count_total'] for g in groups.values()),
            'count_decided': sum(g['count_decided'] for g in groups.values()),
            'wins': sum(g['wins'] for g in groups.values()),
            'losses': sum(g['losses'] for g in groups.values()),
            'pushes': sum(g['pushes'] for g in groups.values()),
            'stake_sum': sum(g['stake_sum'] for g in groups.values()),
            'profit_sum': sum(g['profit_sum'] for g in groups.values())
        }
        
        # Expected values:
        # Total bets: 6 (excluding zero stake)
        # Decided bets: 5 (excluding open bet)
        # Wins: 2, Losses: 2, Pushes: 1
        # Total stake: 75.0 (10+10+15+12+8+20)
        # Total profit: -9.20 (9.10+8.70-15.0-12.0+0.0)
        
        assert overall['count_total'] == 6
        assert overall['count_decided'] == 5
        assert overall['wins'] == 2
        assert overall['losses'] == 2
        assert overall['pushes'] == 1
        assert overall['stake_sum'] == 75.0
        assert overall['profit_sum'] == pytest.approx(-9.20, rel=1e-2)  # 9.10+8.70-15.0-12.0+0.0
        
        # Calculate ROI and hit rate
        roi_pct = (overall['profit_sum'] / overall['stake_sum']) * 100
        hit_rate_pct = (overall['wins'] / (overall['wins'] + overall['losses'])) * 100
        
        assert roi_pct == pytest.approx(-12.27, rel=1e-2)  # -9.20/75.0 * 100
        assert hit_rate_pct == 50.0  # 2 wins / (2 wins + 2 losses) * 100
    
    def test_push_excluded_from_hit_rate_and_profit_zero(self, sample_rows):
        """Test that pushes are excluded from hit rate and have zero profit."""
        groups = rollup_metrics(sample_rows, "bet_type", include_open=False)
        
        # Check spreads group (1 win, 1 push)
        spreads = groups["spreads"]
        assert spreads['wins'] == 1
        assert spreads['losses'] == 0
        assert spreads['pushes'] == 1
        assert spreads['profit_sum'] == pytest.approx(9.10, rel=1e-2)  # Only win profit, push = 0
        assert spreads['hit_rate_pct'] == 100.0  # 1 win / (1 win + 0 loss), push excluded
    
    def test_include_open_flag_counts_open_but_excludes_from_metrics(self, sample_rows):
        """Test that include_open flag works correctly."""
        groups = rollup_metrics(sample_rows, "bet_type", include_open=True)
        
        # Check totals group (1 win, 1 open)
        totals = groups["totals"]
        assert totals['count_total'] == 2  # Both bets counted
        assert totals['count_decided'] == 1  # Only decided bet
        assert totals['count_open'] == 1  # Open bet counted
        assert totals['stake_sum'] == 30.0  # Both stakes included
        assert totals['profit_sum'] == pytest.approx(8.70, rel=1e-2)  # Only decided bet profit
        assert totals['roi_pct'] == pytest.approx(29.0, rel=1e-2)  # 8.70/30.0 * 100
    
    def test_zero_stake_skipped_with_warning(self, sample_rows):
        """Test that zero stake bets are skipped with warning."""
        with patch('scripts.performance_reporter.logger') as mock_logger:
            rollup_metrics(sample_rows, "bet_type", include_open=False)
            
            # Check that warning was logged for zero stake bet
            mock_logger.warning.assert_called_with("Zero or missing stake for bet_id 7")
    
    def test_clv_summary_present_when_columns_exist_and_data_available(self, sample_rows):
        """Test CLV summary when columns exist and data is available."""
        clv_summary = summarize_clv(sample_rows)
        
        assert clv_summary is not None
        assert clv_summary['count_clv'] == 5
        assert clv_summary['clv_min'] == -2.1
        assert clv_summary['clv_max'] == 3.2
        assert clv_summary['clv_median'] == 0.5
        assert clv_summary['clv_mean'] == pytest.approx(0.26, rel=1e-2)
    
    def test_exports_csv_and_json_shapes(self, sample_rows):
        """Test CSV and JSON export functionality."""
        from scripts.performance_reporter import write_csv, write_json
        
        groups = rollup_metrics(sample_rows, "bet_type", include_open=False)
        
        # Test CSV export
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            csv_path = f.name
        
        try:
            write_csv(groups, csv_path)
            
            # Check CSV content
            with open(csv_path, 'r') as f:
                lines = f.readlines()
                assert len(lines) > 1  # Header + data rows
                assert 'group_key,count_total,count_decided' in lines[0]  # Header
        finally:
            Path(csv_path).unlink()
        
        # Test JSON export
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json_path = f.name
        
        try:
            overall = {
                'count_total': 6,
                'count_decided': 5,
                'wins': 2,
                'losses': 2,
                'pushes': 1,
                'stake_sum': 67.0,
                'profit_sum': -9.20,
                'roi_pct': -13.73,
                'hit_rate_pct': 50.0
            }
            
            leaders, laggards = get_leaders_laggards(groups, top_n=3)
            clv_summary = summarize_clv(sample_rows)
            
            write_json(overall, groups, leaders, laggards, clv_summary, json_path)
            
            # Check JSON content
            with open(json_path, 'r') as f:
                data = json.loads(f.read())
                assert 'overall' in data
                assert 'groups' in data
                assert 'leaders' in data
                assert 'laggards' in data
                assert 'clv_summary' in data
        finally:
            Path(json_path).unlink()
