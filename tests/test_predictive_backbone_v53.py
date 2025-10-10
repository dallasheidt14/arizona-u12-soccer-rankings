"""
Comprehensive Test Suite for Predictive Backbone V5.3+

This module provides comprehensive validation tests for the predictive backbone system,
ensuring reliability, calibration, and performance across different configurations.

Key Test Areas:
- Basic functionality and data loading
- Calibration improvement validation
- Feature builder graceful degradation
- Monotonicity and logical consistency
- Split mode validation
- Calibration curve quality
- Edge case handling

Author: Youth Soccer Rankings System
Version: V5.3+
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
import tempfile
import os
from pathlib import Path
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from analytics.predictive_backbone_v53 import (
    load_games_and_rankings,
    prepare_games_data,
    chronological_split,
    kfold_split,
    train_logistic_model,
    apply_platt_scaling,
    apply_isotonic_calibration,
    compute_calibration_curve,
    run_backtest,
    interactive_predict,
    BacktestResult
)
from analytics.feature_builders_v53 import (
    default_feature_builder,
    power_plus_elo_feature_builder,
    comprehensive_feature_builder,
    minimal_feature_builder,
    validate_features,
    compute_feature_statistics
)


@pytest.fixture
def sample_games_data():
    """Create sample games data for testing."""
    return pd.DataFrame({
        'Team A': ['Team A1', 'Team A2', 'Team A3', 'Team A4', 'Team A5'],
        'Team B': ['Team B1', 'Team B2', 'Team B3', 'Team B4', 'Team B5'],
        'Score A': [2, 1, 3, 0, 1],
        'Score B': [1, 2, 1, 2, 0],
        'Date': pd.date_range('2024-01-01', periods=5, freq='D')
    })


@pytest.fixture
def sample_rankings_data():
    """Create sample rankings data for testing."""
    return pd.DataFrame({
        'Team': ['Team A1', 'Team A2', 'Team A3', 'Team A4', 'Team A5', 
                'Team B1', 'Team B2', 'Team B3', 'Team B4', 'Team B5'],
        'PowerScore': [0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0, 0.9],
        'SAO_norm': [0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0, 0.9],
        'SAD_norm': [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1],
        'SOS_norm': [0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0, 0.9, 0.8],
        'SOS_iterative_norm': [0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0, 0.9, 0.8, 0.7]
    })


@pytest.fixture
def sample_prepared_data(sample_games_data, sample_rankings_data):
    """Create sample prepared data for testing."""
    return prepare_games_data(sample_games_data, sample_rankings_data)


class TestDataLoading:
    """Test data loading and validation."""
    
    def test_load_games_and_rankings_success(self, sample_games_data, sample_rankings_data):
        """Test successful data loading."""
        with tempfile.TemporaryDirectory() as temp_dir:
            games_path = os.path.join(temp_dir, 'games.csv')
            rankings_path = os.path.join(temp_dir, 'rankings.csv')
            
            sample_games_data.to_csv(games_path, index=False)
            sample_rankings_data.to_csv(rankings_path, index=False)
            
            games_df, rankings_df = load_games_and_rankings(games_path, rankings_path)
            
            assert len(games_df) == 5
            assert len(rankings_df) == 10
            assert 'Team A' in games_df.columns
            assert 'Team' in rankings_df.columns
    
    def test_load_games_and_rankings_missing_files(self):
        """Test handling of missing files."""
        with pytest.raises(ValueError, match="Error loading data"):
            load_games_and_rankings("nonexistent_games.csv", "nonexistent_rankings.csv")
    
    def test_load_games_and_rankings_missing_columns(self, sample_games_data):
        """Test handling of missing required columns."""
        with tempfile.TemporaryDirectory() as temp_dir:
            games_path = os.path.join(temp_dir, 'games.csv')
            rankings_path = os.path.join(temp_dir, 'rankings.csv')
            
            # Remove required column
            sample_games_data.drop('Date', axis=1).to_csv(games_path, index=False)
            
            # Create minimal rankings file
            pd.DataFrame({'Team': ['Team A1'], 'PowerScore': [0.5]}).to_csv(rankings_path, index=False)
            
            with pytest.raises(ValueError, match="Missing game columns"):
                load_games_and_rankings(games_path, rankings_path)


class TestDataPreparation:
    """Test data preparation and feature computation."""
    
    def test_prepare_games_data_basic(self, sample_games_data, sample_rankings_data):
        """Test basic data preparation."""
        prepared = prepare_games_data(sample_games_data, sample_rankings_data)
        
        assert len(prepared) == 5
        assert 'PowerDiff' in prepared.columns
        assert 'Team_A_Wins' in prepared.columns
        assert 'PowerScore_A' in prepared.columns
        assert 'PowerScore_B' in prepared.columns
    
    def test_prepare_games_data_extended_features(self, sample_games_data, sample_rankings_data):
        """Test extended feature computation."""
        prepared = prepare_games_data(sample_games_data, sample_rankings_data)
        
        # Check extended features
        assert 'SAO_Diff' in prepared.columns
        assert 'SAD_Diff_Inverted' in prepared.columns
        assert 'SOS_Diff' in prepared.columns
        assert 'SOSi_Diff' in prepared.columns
    
    def test_prepare_games_data_winner_determination(self, sample_games_data, sample_rankings_data):
        """Test winner determination logic."""
        prepared = prepare_games_data(sample_games_data, sample_rankings_data)
        
        # Check winner determination
        assert prepared['Team_A_Wins'].dtype == int
        assert prepared['Team_A_Wins'].isin([0, 1]).all()
        
        # Verify specific cases
        assert prepared.iloc[0]['Team_A_Wins'] == 1  # 2 > 1
        assert prepared.iloc[1]['Team_A_Wins'] == 0  # 1 < 2


class TestDataSplitting:
    """Test data splitting functionality."""
    
    def test_chronological_split(self, sample_prepared_data):
        """Test chronological splitting."""
        train_df, test_df = chronological_split(sample_prepared_data, test_ratio=0.4)
        
        assert len(train_df) + len(test_df) == len(sample_prepared_data)
        assert len(test_df) == 2  # 40% of 5 = 2
        assert len(train_df) == 3
        
        # Check chronological order
        assert train_df['Date'].max() <= test_df['Date'].min()
    
    def test_kfold_split(self, sample_prepared_data):
        """Test k-fold splitting."""
        splits = kfold_split(sample_prepared_data, n_folds=3)
        
        assert len(splits) == 3
        
        for train_df, test_df in splits:
            assert len(train_df) + len(test_df) == len(sample_prepared_data)
            assert len(train_df) > 0
            assert len(test_df) > 0


class TestFeatureBuilders:
    """Test feature builder functions."""
    
    def test_default_feature_builder(self, sample_prepared_data):
        """Test default feature builder."""
        X, features = default_feature_builder(sample_prepared_data)
        
        assert 'PowerDiff' in features
        assert isinstance(X, pd.DataFrame)
        assert len(features) >= 1
        assert 'SAO_Diff' in features
        assert 'SAD_Diff_Inverted' in features
        assert 'SOS_Diff' in features
        assert 'SOSi_Diff' in features
    
    def test_power_plus_elo_feature_builder(self, sample_prepared_data):
        """Test ELO-enhanced feature builder."""
        # Add ELO columns
        sample_prepared_data['ELO_Rating_A'] = [1500, 1400, 1300, 1200, 1100]
        sample_prepared_data['ELO_Rating_B'] = [1000, 1100, 1200, 1300, 1400]
        
        X, features = power_plus_elo_feature_builder(sample_prepared_data)
        
        assert 'PowerDiff' in features
        assert isinstance(X, pd.DataFrame)
        assert len(features) >= 1
        assert 'ELO_RatingDiff' in features
    
    def test_minimal_feature_builder(self, sample_prepared_data):
        """Test minimal feature builder."""
        X, features = minimal_feature_builder(sample_prepared_data)
        
        assert features == ['PowerDiff']
        assert isinstance(X, pd.DataFrame)
        assert len(features) == 1
    
    def test_comprehensive_feature_builder(self, sample_prepared_data):
        """Test comprehensive feature builder."""
        X, features = comprehensive_feature_builder(sample_prepared_data)
        
        assert 'PowerDiff' in features
        assert isinstance(X, pd.DataFrame)
        assert len(features) >= 1
        assert len(features) >= 5  # Should include all available features
    
    def test_feature_builder_graceful_degradation(self):
        """Test graceful degradation with missing columns."""
        minimal_data = pd.DataFrame({
            'PowerScore_A': [0.8, 0.6, 0.7],
            'PowerScore_B': [0.5, 0.4, 0.3]
        })
        
        X, features = default_feature_builder(minimal_data)
        assert 'PowerDiff' in features
        assert isinstance(X, pd.DataFrame)
        
        X, features = power_plus_elo_feature_builder(minimal_data)
        assert 'PowerDiff' in features
        assert isinstance(X, pd.DataFrame)


class TestModelTraining:
    """Test model training functionality."""
    
    def test_train_logistic_model(self, sample_prepared_data):
        """Test logistic regression training."""
        X, features = default_feature_builder(sample_prepared_data)
        y = sample_prepared_data['Team_A_Wins']
        
        model = train_logistic_model(X, y)
        
        assert hasattr(model, 'predict')
        assert hasattr(model, 'predict_proba')
        assert hasattr(model, 'coef_')
        
        # Test predictions
        predictions = model.predict(X)
        probabilities = model.predict_proba(X)
        
        assert len(predictions) == len(X)
        assert probabilities.shape == (len(X), 2)
        assert np.allclose(probabilities.sum(axis=1), 1.0)


class TestCalibration:
    """Test calibration methods."""
    
    def test_apply_platt_scaling(self, sample_prepared_data):
        """Test Platt scaling calibration."""
        X, features = default_feature_builder(sample_prepared_data)
        y = sample_prepared_data['Team_A_Wins']
        
        # Train base model
        model = train_logistic_model(X, y)
        
        # Apply Platt scaling
        calibrated_model = apply_platt_scaling(model, X, y)
        
        assert hasattr(calibrated_model, 'predict_proba')
        
        # Test calibrated predictions
        raw_scores = model.decision_function(X)
        calibrated_probs = calibrated_model.predict_proba(raw_scores.reshape(-1, 1))[:, 1]
        
        assert len(calibrated_probs) == len(X)
        assert np.all((calibrated_probs >= 0) & (calibrated_probs <= 1))
    
    def test_apply_isotonic_calibration(self, sample_prepared_data):
        """Test isotonic regression calibration."""
        X, features = default_feature_builder(sample_prepared_data)
        y = sample_prepared_data['Team_A_Wins']
        
        # Train base model
        model = train_logistic_model(X, y)
        
        # Apply isotonic calibration
        calibrated_model = apply_isotonic_calibration(model, X, y)
        
        assert hasattr(calibrated_model, 'transform')
        
        # Test calibrated predictions
        raw_probs = model.predict_proba(X)[:, 1]
        calibrated_probs = calibrated_model.transform(raw_probs)
        
        assert len(calibrated_probs) == len(X)
        assert np.all((calibrated_probs >= 0) & (calibrated_probs <= 1))


class TestCalibrationCurve:
    """Test calibration curve computation."""
    
    def test_compute_calibration_curve(self):
        """Test calibration curve computation."""
        y_true = pd.Series([1, 0, 1, 0, 1, 0, 1, 0, 1, 0])
        y_prob = pd.Series([0.9, 0.1, 0.8, 0.2, 0.7, 0.3, 0.6, 0.4, 0.5, 0.5])
        
        curve_data = compute_calibration_curve(y_true, y_prob, n_bins=5)
        
        assert 'bin_accuracies' in curve_data
        assert 'bin_confidences' in curve_data
        assert 'bin_counts' in curve_data
        assert 'ece' in curve_data
        assert 'n_bins' in curve_data
        
        assert len(curve_data['bin_accuracies']) == 5
        assert len(curve_data['bin_confidences']) == 5
        assert len(curve_data['bin_counts']) == 5
        assert curve_data['n_bins'] == 5


class TestBacktest:
    """Test backtest functionality."""
    
    def test_run_backtest_chronological(self, sample_games_data, sample_rankings_data):
        """Test chronological backtest."""
        result = run_backtest(
            games_df=sample_games_data,
            rankings_df=sample_rankings_data,
            feature_fn=default_feature_builder,
            split_mode='chronological',
            calibrated=True,
            n_bins=5
        )
        
        assert isinstance(result, BacktestResult)
        assert result.brier_score >= 0
        assert result.log_loss >= 0
        assert 0 <= result.auc <= 1
        assert result.n_test > 0
        assert result.n_train > 0
        assert result.split_mode == 'chronological'
        assert result.calibration_method in ['platt', 'isotonic', 'none']
    
    def test_run_backtest_kfold(self, sample_games_data, sample_rankings_data):
        """Test k-fold backtest."""
        result = run_backtest(
            games_df=sample_games_data,
            rankings_df=sample_rankings_data,
            feature_fn=default_feature_builder,
            split_mode='kfold',
            calibrated=True,
            n_bins=5
        )
        
        assert isinstance(result, BacktestResult)
        assert result.brier_score >= 0
        assert result.log_loss >= 0
        assert 0 <= result.auc <= 1
        assert result.split_mode == 'kfold'
    
    def test_run_backtest_no_calibration(self, sample_games_data, sample_rankings_data):
        """Test backtest without calibration."""
        result = run_backtest(
            games_df=sample_games_data,
            rankings_df=sample_rankings_data,
            feature_fn=default_feature_builder,
            split_mode='chronological',
            calibrated=False,
            n_bins=5
        )
        
        assert result.calibration_method == 'none'
        assert result.calibrated_model is None


class TestInteractivePredict:
    """Test interactive prediction functionality."""
    
    def test_interactive_predict_simple(self, sample_rankings_data):
        """Test simple interactive prediction."""
        result = interactive_predict(
            team_a='Team A1',
            team_b='Team B1',
            rankings_df=sample_rankings_data,
            mode='simple'
        )
        
        assert 'P_A_win' in result
        assert 'P_B_win' in result
        assert 'predicted_winner' in result
        assert 'confidence' in result
        
        assert 0 <= result['P_A_win'] <= 1
        assert 0 <= result['P_B_win'] <= 1
        assert abs(result['P_A_win'] + result['P_B_win'] - 1.0) < 1e-6
    
    def test_interactive_predict_advanced(self, sample_rankings_data):
        """Test advanced interactive prediction."""
        result = interactive_predict(
            team_a='Team A1',
            team_b='Team B1',
            rankings_df=sample_rankings_data,
            mode='advanced'
        )
        
        assert 'P_A_win' in result
        assert 'P_Draw' in result
        assert 'P_B_win' in result
        assert 'predicted_winner' in result
        assert 'confidence' in result
        
        assert 0 <= result['P_A_win'] <= 1
        assert 0 <= result['P_Draw'] <= 1
        assert 0 <= result['P_B_win'] <= 1
        
        total_prob = result['P_A_win'] + result['P_Draw'] + result['P_B_win']
        assert abs(total_prob - 1.0) < 1e-6
    
    def test_interactive_predict_with_model(self, sample_rankings_data, sample_prepared_data):
        """Test interactive prediction with trained model."""
        X, features = default_feature_builder(sample_prepared_data)
        y = sample_prepared_data['Team_A_Wins']
        
        model = train_logistic_model(X, y)
        
        result = interactive_predict(
            team_a='Team A1',
            team_b='Team B1',
            rankings_df=sample_rankings_data,
            model=model,
            mode='simple'
        )
        
        assert 'P_A_win' in result
        assert 0 <= result['P_A_win'] <= 1
    
    def test_interactive_predict_team_not_found(self, sample_rankings_data):
        """Test interactive prediction with non-existent team."""
        with pytest.raises(ValueError, match="not found in rankings"):
            interactive_predict(
                team_a='NonExistentTeam',
                team_b='Team B1',
                rankings_df=sample_rankings_data,
                mode='simple'
            )


class TestCalibrationImprovement:
    """Test calibration improvement validation."""
    
    def test_calibration_improvement_platt(self, sample_games_data, sample_rankings_data):
        """Test that Platt scaling improves calibration."""
        # Run backtest with and without calibration
        result_uncalibrated = run_backtest(
            games_df=sample_games_data,
            rankings_df=sample_rankings_data,
            feature_fn=default_feature_builder,
            split_mode='chronological',
            calibrated=False,
            n_bins=5
        )
        
        result_calibrated = run_backtest(
            games_df=sample_games_data,
            rankings_df=sample_rankings_data,
            feature_fn=default_feature_builder,
            split_mode='chronological',
            calibrated=True,
            n_bins=5
        )
        
        # Calibrated model should have better or equal Brier score
        assert result_calibrated.brier_score <= result_uncalibrated.brier_score + 1e-6
        
        # Calibrated model should have calibration method applied
        assert result_calibrated.calibration_method != 'none'
        assert result_calibrated.calibrated_model is not None


class TestMonotonicity:
    """Test monotonicity and logical consistency."""
    
    def test_powerdiff_monotonicity(self, sample_rankings_data):
        """Test that higher PowerDiff leads to higher win probability."""
        # Test with different PowerScore differences
        team_a = 'Team A1'  # PowerScore = 0.8
        team_b_low = 'Team B1'  # PowerScore = 0.3
        team_b_high = 'Team B5'  # PowerScore = 0.9
        
        result_low = interactive_predict(team_a, team_b_low, sample_rankings_data, mode='simple')
        result_high = interactive_predict(team_a, team_b_high, sample_rankings_data, mode='simple')
        
        # Team A should have higher win probability against lower-rated team
        assert result_low['P_A_win'] > result_high['P_A_win']
    
    def test_feature_importance_consistency(self, sample_games_data, sample_rankings_data):
        """Test that feature importance is consistent."""
        result = run_backtest(
            games_df=sample_games_data,
            rankings_df=sample_rankings_data,
            feature_fn=default_feature_builder,
            split_mode='chronological',
            calibrated=False,
            n_bins=5
        )
        
        if result.feature_importance:
            # PowerDiff should have reasonable importance
            assert 'PowerDiff' in result.feature_importance
            assert not np.isnan(result.feature_importance['PowerDiff'])


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_data(self):
        """Test handling of empty data."""
        empty_games = pd.DataFrame(columns=['Team A', 'Team B', 'Score A', 'Score B', 'Date'])
        empty_rankings = pd.DataFrame(columns=['Team', 'PowerScore'])
        
        with pytest.raises(ValueError):
            run_backtest(
                games_df=empty_games,
                rankings_df=empty_rankings,
                feature_fn=default_feature_builder,
                split_mode='chronological',
                calibrated=False
            )
    
    def test_single_game(self):
        """Test handling of single game."""
        single_game = pd.DataFrame({
            'Team A': ['Team A1'],
            'Team B': ['Team B1'],
            'Score A': [2],
            'Score B': [1],
            'Date': [pd.Timestamp('2024-01-01')]
        })
        
        single_rankings = pd.DataFrame({
            'Team': ['Team A1', 'Team B1'],
            'PowerScore': [0.8, 0.3]
        })
        
        # Should handle single game gracefully
        result = run_backtest(
            games_df=single_game,
            rankings_df=single_rankings,
            feature_fn=minimal_feature_builder,
            split_mode='chronological',
            calibrated=False
        )
        
        assert isinstance(result, BacktestResult)
    
    def test_all_ties(self):
        """Test handling of all tied games."""
        tied_games = pd.DataFrame({
            'Team A': ['Team A1', 'Team A2'],
            'Team B': ['Team B1', 'Team B2'],
            'Score A': [1, 2],
            'Score B': [1, 2],
            'Date': pd.date_range('2024-01-01', periods=2, freq='D')
        })
        
        tied_rankings = pd.DataFrame({
            'Team': ['Team A1', 'Team A2', 'Team B1', 'Team B2'],
            'PowerScore': [0.5, 0.5, 0.5, 0.5]
        })
        
        result = run_backtest(
            games_df=tied_games,
            rankings_df=tied_rankings,
            feature_fn=minimal_feature_builder,
            split_mode='chronological',
            calibrated=False
        )
        
        assert isinstance(result, BacktestResult)


class TestFeatureValidation:
    """Test feature validation and statistics."""
    
    def test_validate_features(self, sample_prepared_data):
        """Test feature validation."""
        X, features = default_feature_builder(sample_prepared_data)
        valid_features = validate_features(sample_prepared_data, features)
        
        assert len(valid_features) > 0
        assert all(f in features for f in valid_features)
    
    def test_compute_feature_statistics(self, sample_prepared_data):
        """Test feature statistics computation."""
        X, features = default_feature_builder(sample_prepared_data)
        stats = compute_feature_statistics(sample_prepared_data, features)
        
        assert len(stats) > 0
        
        for feature, stat_dict in stats.items():
            assert 'count' in stat_dict
            assert 'mean' in stat_dict
            assert 'std' in stat_dict
            assert 'min' in stat_dict
            assert 'max' in stat_dict
            assert stat_dict['count'] > 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
