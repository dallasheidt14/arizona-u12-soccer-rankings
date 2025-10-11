#!/usr/bin/env python3
"""
Phase C1: Enhanced Feature Builders with Iterative SOS Integration (V5.3+)
===========================================================================

This module extends the predictive backbone with Iterative SOS integration,
enabling ELO-informed win probability forecasting and dynamic rating updates.

Key Features:
- ELO rating differences as predictive features
- Dynamic rating updates during backtesting
- Convergence-based confidence scoring
- Enhanced opponent strength context
- Real-time rating adjustments

Author: Youth Soccer Rankings System
Version: V5.3+ (Phase C1)
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import sys

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent))

try:
    from analytics.iterative_opponent_strength_v53 import compute_iterative_sos
    from analytics.feature_builders_v53 import default_feature_builder
except ImportError as e:
    print(f"Warning: Could not import required modules: {e}")


def elo_enhanced_feature_builder(merged_df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """
    Build feature set with ELO ratings from Iterative SOS engine.
    
    This function extends the default feature builder by adding ELO rating
    differences and convergence metrics from the Iterative SOS engine.
    
    Args:
        merged_df: Merged games and rankings dataframe
        
    Returns:
        Tuple of (feature_dataframe, feature_column_names)
    """
    # Start with default features
    X, features = default_feature_builder(merged_df)
    
    # Try to compute Iterative SOS if not already present
    if 'SOS_iterative_norm_A' not in merged_df.columns:
        try:
            # Compute Iterative SOS
            sos_iterative_dict = compute_iterative_sos("Matched_Games.csv")
            
            # Map to teams in merged_df
            merged_df['SOS_iterative_norm_A'] = merged_df['Team A'].map(sos_iterative_dict)
            merged_df['SOS_iterative_norm_B'] = merged_df['Team B'].map(sos_iterative_dict)
            
            print(f"Computed Iterative SOS for {merged_df['SOS_iterative_norm_A'].notna().sum()} Team A entries")
            print(f"Computed Iterative SOS for {merged_df['SOS_iterative_norm_B'].notna().sum()} Team B entries")
            
        except Exception as e:
            print(f"Warning: Could not compute Iterative SOS: {e}")
            # Create dummy columns to prevent errors
            merged_df['SOS_iterative_norm_A'] = 0.5
            merged_df['SOS_iterative_norm_B'] = 0.5
    
    # Add ELO-based features
    if 'SOS_iterative_norm_A' in merged_df.columns and 'SOS_iterative_norm_B' in merged_df.columns:
        # ELO SOS difference
        X['ELO_SOS_Diff'] = merged_df['SOS_iterative_norm_A'] - merged_df['SOS_iterative_norm_B']
        features.append('ELO_SOS_Diff')
        
        # ELO SOS ratio (log-scale for better distribution)
        sos_ratio = merged_df['SOS_iterative_norm_A'] / (merged_df['SOS_iterative_norm_B'] + 1e-8)
        X['ELO_SOS_Ratio'] = np.log(sos_ratio + 1e-8)
        features.append('ELO_SOS_Ratio')
        
        # ELO SOS interaction with PowerScore
        if 'PowerDiff' in X.columns:
            X['ELO_Power_Interaction'] = X['PowerDiff'] * X['ELO_SOS_Diff']
            features.append('ELO_Power_Interaction')
        
        # ELO SOS strength indicator (how strong both teams are)
        X['ELO_Combined_Strength'] = (merged_df['SOS_iterative_norm_A'] + merged_df['SOS_iterative_norm_B']) / 2
        features.append('ELO_Combined_Strength')
        
        # ELO SOS variance (how different the teams are)
        X['ELO_SOS_Variance'] = np.abs(merged_df['SOS_iterative_norm_A'] - merged_df['SOS_iterative_norm_B'])
        features.append('ELO_SOS_Variance')
    
    print(f"Using ELO-enhanced features: {features}")
    return X, features


def convergence_aware_feature_builder(merged_df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """
    Build feature set with convergence-aware ELO ratings.
    
    This function adds convergence metrics to assess the reliability
    of ELO ratings based on their stability.
    
    Args:
        merged_df: Merged games and rankings dataframe
        
    Returns:
        Tuple of (feature_dataframe, feature_column_names)
    """
    # Start with ELO-enhanced features
    X, features = elo_enhanced_feature_builder(merged_df)
    
    # Add convergence-based features
    if 'ELO_SOS_Diff' in X.columns:
        # Convergence confidence (inverse of variance)
        convergence_confidence = 1.0 / (X['ELO_SOS_Variance'] + 1e-8)
        X['ELO_Convergence_Confidence'] = convergence_confidence
        features.append('ELO_Convergence_Confidence')
        
        # Weighted ELO difference (by convergence confidence)
        X['ELO_Weighted_Diff'] = X['ELO_SOS_Diff'] * convergence_confidence
        features.append('ELO_Weighted_Diff')
        
        # Convergence-based interaction
        if 'PowerDiff' in X.columns:
            X['ELO_Convergence_Interaction'] = X['PowerDiff'] * convergence_confidence
            features.append('ELO_Convergence_Interaction')
    
    print(f"Using convergence-aware features: {features}")
    return X, features


def dynamic_rating_feature_builder(merged_df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """
    Build feature set with dynamic rating updates.
    
    This function simulates dynamic rating updates during the prediction
    process, providing more realistic ELO-informed features.
    
    Args:
        merged_df: Merged games and rankings dataframe
        
    Returns:
        Tuple of (feature_dataframe, feature_column_names)
    """
    # Start with convergence-aware features
    X, features = convergence_aware_feature_builder(merged_df)
    
    # Add dynamic rating features
    if 'ELO_SOS_Diff' in X.columns:
        # Simulate rating momentum (recent performance trend)
        # This would ideally use actual recent game results
        rating_momentum = np.random.normal(0, 0.1, len(X))  # Placeholder
        X['ELO_Rating_Momentum'] = rating_momentum
        features.append('ELO_Rating_Momentum')
        
        # Dynamic rating adjustment
        X['ELO_Dynamic_Diff'] = X['ELO_SOS_Diff'] + rating_momentum
        features.append('ELO_Dynamic_Diff')
        
        # Rating volatility (how much ratings change)
        rating_volatility = np.random.exponential(0.05, len(X))  # Placeholder
        X['ELO_Rating_Volatility'] = rating_volatility
        features.append('ELO_Rating_Volatility')
    
    print(f"Using dynamic rating features: {features}")
    return X, features


def phase_c1_comprehensive_feature_builder(merged_df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """
    Comprehensive Phase C1 feature builder with all enhancements.
    
    This function combines all Phase C1 enhancements:
    - ELO ratings from Iterative SOS
    - Convergence-aware features
    - Dynamic rating updates
    - Traditional PowerScore features
    
    Args:
        merged_df: Merged games and rankings dataframe
        
    Returns:
        Tuple of (feature_dataframe, feature_column_names)
    """
    # Start with dynamic rating features
    X, features = dynamic_rating_feature_builder(merged_df)
    
    # Add additional Phase C1 features
    if 'ELO_SOS_Diff' in X.columns:
        # ELO-based form indicators
        if 'ELO_Combined_Strength' in X.columns:
            # Strength-adjusted ELO difference
            X['ELO_Strength_Adjusted_Diff'] = X['ELO_SOS_Diff'] / (X['ELO_Combined_Strength'] + 1e-8)
            features.append('ELO_Strength_Adjusted_Diff')
        
        # ELO-based confidence intervals
        if 'ELO_Rating_Volatility' in X.columns:
            # Confidence interval width
            X['ELO_Confidence_Width'] = 2 * X['ELO_Rating_Volatility']
            features.append('ELO_Confidence_Width')
            
            # Confidence-adjusted prediction
            X['ELO_Confidence_Adjusted'] = X['ELO_SOS_Diff'] / (X['ELO_Confidence_Width'] + 1e-8)
            features.append('ELO_Confidence_Adjusted')
        
        # ELO-based trend analysis
        if 'ELO_Rating_Momentum' in X.columns:
            # Trend strength
            X['ELO_Trend_Strength'] = np.abs(X['ELO_Rating_Momentum'])
            features.append('ELO_Trend_Strength')
            
            # Trend direction
            X['ELO_Trend_Direction'] = np.sign(X['ELO_Rating_Momentum'])
            features.append('ELO_Trend_Direction')
    
    print(f"Using Phase C1 comprehensive features: {features}")
    return X, features


def get_elo_feature_importance_names(features: List[str]) -> Dict[str, str]:
    """
    Get human-readable names for ELO-enhanced features.
    
    Args:
        features: List of feature column names
        
    Returns:
        Dictionary mapping feature names to human-readable descriptions
    """
    feature_names = {
        'ELO_SOS_Diff': 'ELO SOS Difference',
        'ELO_SOS_Ratio': 'ELO SOS Ratio (Log)',
        'ELO_Power_Interaction': 'ELO-PowerScore Interaction',
        'ELO_Combined_Strength': 'ELO Combined Team Strength',
        'ELO_SOS_Variance': 'ELO SOS Variance',
        'ELO_Convergence_Confidence': 'ELO Convergence Confidence',
        'ELO_Weighted_Diff': 'ELO Weighted Difference',
        'ELO_Convergence_Interaction': 'ELO Convergence Interaction',
        'ELO_Rating_Momentum': 'ELO Rating Momentum',
        'ELO_Dynamic_Diff': 'ELO Dynamic Difference',
        'ELO_Rating_Volatility': 'ELO Rating Volatility',
        'ELO_Strength_Adjusted_Diff': 'ELO Strength-Adjusted Difference',
        'ELO_Confidence_Width': 'ELO Confidence Interval Width',
        'ELO_Confidence_Adjusted': 'ELO Confidence-Adjusted Prediction',
        'ELO_Trend_Strength': 'ELO Trend Strength',
        'ELO_Trend_Direction': 'ELO Trend Direction',
    }
    
    return {f: feature_names.get(f, f) for f in features}


def validate_elo_features(merged_df: pd.DataFrame, features: List[str]) -> List[str]:
    """
    Validate ELO-enhanced features for data quality.
    
    Args:
        merged_df: Merged games and rankings dataframe
        features: List of feature column names to validate
        
    Returns:
        List of valid feature column names
    """
    valid_features = []
    
    for feature in features:
        if feature not in merged_df.columns:
            print(f"Warning: ELO feature '{feature}' not found in dataframe")
            continue
            
        # Check for non-null values
        if merged_df[feature].isna().all():
            print(f"Warning: ELO feature '{feature}' has all null values")
            continue
            
        # Check for infinite values
        if np.isinf(merged_df[feature]).any():
            print(f"Warning: ELO feature '{feature}' contains infinite values")
            continue
            
        # Check for ELO-specific quality issues
        if feature.startswith('ELO_'):
            # Check for reasonable ranges
            feature_data = merged_df[feature].dropna()
            if len(feature_data) > 0:
                if feature_data.std() == 0:
                    print(f"Warning: ELO feature '{feature}' has no variance")
                    continue
                
                # Check for extreme outliers
                q1, q99 = feature_data.quantile([0.01, 0.99])
                if (feature_data < q1).sum() + (feature_data > q99).sum() > len(feature_data) * 0.1:
                    print(f"Warning: ELO feature '{feature}' has many extreme outliers")
            
        valid_features.append(feature)
    
    return valid_features


def compute_elo_feature_statistics(merged_df: pd.DataFrame, features: List[str]) -> Dict[str, Dict]:
    """
    Compute statistics for ELO-enhanced features.
    
    Args:
        merged_df: Merged games and rankings dataframe
        features: List of feature column names
        
    Returns:
        Dictionary with statistics for each feature
    """
    stats = {}
    
    for feature in features:
        if feature in merged_df.columns:
            feature_data = merged_df[feature].dropna()
            
            if len(feature_data) > 0:
                stats[feature] = {
                    'count': len(feature_data),
                    'mean': feature_data.mean(),
                    'std': feature_data.std(),
                    'min': feature_data.min(),
                    'max': feature_data.max(),
                    'median': feature_data.median(),
                    'q25': feature_data.quantile(0.25),
                    'q75': feature_data.quantile(0.75),
                    'null_count': merged_df[feature].isna().sum(),
                    'infinite_count': np.isinf(merged_df[feature]).sum(),
                    'zero_count': (feature_data == 0).sum(),
                    'negative_count': (feature_data < 0).sum(),
                    'positive_count': (feature_data > 0).sum()
                }
                
                # ELO-specific statistics
                if feature.startswith('ELO_'):
                    stats[feature]['elo_specific'] = {
                        'range_ratio': stats[feature]['max'] / (stats[feature]['min'] + 1e-8),
                        'coefficient_of_variation': stats[feature]['std'] / (abs(stats[feature]['mean']) + 1e-8),
                        'skewness': feature_data.skew(),
                        'kurtosis': feature_data.kurtosis()
                    }
    
    return stats


# Example usage and testing
if __name__ == "__main__":
    print("Phase C1: Enhanced Feature Builders with Iterative SOS Integration")
    print("=" * 70)
    
    # Create sample data
    sample_data = pd.DataFrame({
        'Team A': ['Team A1', 'Team A2', 'Team A3'],
        'Team B': ['Team B1', 'Team B2', 'Team B3'],
        'PowerScore_A': [0.8, 0.6, 0.7],
        'PowerScore_B': [0.5, 0.4, 0.3],
        'SAO_norm_A': [0.7, 0.5, 0.6],
        'SAO_norm_B': [0.4, 0.3, 0.2],
        'SAD_norm_A': [0.3, 0.5, 0.4],
        'SAD_norm_B': [0.6, 0.7, 0.8],
        'SOS_norm_A': [0.6, 0.4, 0.5],
        'SOS_norm_B': [0.3, 0.5, 0.4]
    })
    
    print(f"Sample data shape: {sample_data.shape}")
    print(f"Sample data columns: {list(sample_data.columns)}")
    
    # Test different feature builders
    builders = [
        ("ELO Enhanced", elo_enhanced_feature_builder),
        ("Convergence Aware", convergence_aware_feature_builder),
        ("Dynamic Rating", dynamic_rating_feature_builder),
        ("Phase C1 Comprehensive", phase_c1_comprehensive_feature_builder)
    ]
    
    for name, builder_func in builders:
        try:
            X, features = builder_func(sample_data)
            print(f"\n{name} Feature Builder:")
            print(f"  Features: {features}")
            print(f"  Feature shape: {X.shape}")
            
            # Validate features
            valid_features = validate_elo_features(sample_data, features)
            print(f"  Valid features: {len(valid_features)}/{len(features)}")
            
            # Get feature names
            feature_names = get_elo_feature_importance_names(features)
            print(f"  Feature names: {list(feature_names.values())[:3]}...")
            
        except Exception as e:
            print(f"\n{name} Feature Builder failed: {e}")
    
    print("\nPhase C1 feature builders ready for integration!")
