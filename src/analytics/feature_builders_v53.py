"""
Feature Builders for Predictive Backbone V5.3+

This module provides feature extraction functions for the predictive system,
with graceful degradation based on available data columns.

Key Features:
- Default feature builder with PowerDiff + optional decompositions
- ELO-aware feature builder with Iterative SOS support
- Graceful degradation when columns are missing
- Consistent feature naming and computation

Author: Youth Soccer Rankings System
Version: V5.3+
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple


def default_feature_builder(merged_df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """
    Build default feature set with graceful degradation.
    
    Features included (if available):
    - PowerDiff: Difference in PowerScore between teams
    - SAO_Diff: Difference in Strength-Adjusted Offense
    - SAD_Diff_Inverted: Inverted difference in Strength-Adjusted Defense
    - SOS_Diff: Difference in Strength of Schedule
    - SOSi_Diff: Difference in Iterative SOS (if available)
    
    Args:
        merged_df: Merged games and rankings dataframe
        
    Returns:
        Tuple of (feature_dataframe, feature_column_names)
    """
    feats = {}
    def diff(a, b): return merged_df[a] - merged_df[b]
    
    # Always try PowerScore first
    if {"PowerScore_A", "PowerScore_B"} <= set(merged_df.columns):
        feats["PowerDiff"] = diff("PowerScore_A", "PowerScore_B")
    else:
        # Fallback: simple goal diff (if ranking columns not available)
        if {"Score A", "Score B"} <= set(merged_df.columns):
            feats["GoalDiff"] = diff("Score A", "Score B")
        else:
            # Emergency: constant feature to prevent empty DataFrame crash
            feats["BiasOnly"] = np.zeros(len(merged_df))
    
    # Optional additional diffs (only add if columns exist)
    if {"SAO_norm_A","SAO_norm_B"} <= set(merged_df.columns):
        feats["SAO_Diff"] = diff("SAO_norm_A","SAO_norm_B")
    if {"SAD_norm_A","SAD_norm_B"} <= set(merged_df.columns):
        feats["SAD_Diff_Inverted"] = (1.0 - merged_df["SAD_norm_A"]) - (1.0 - merged_df["SAD_norm_B"])
    if {"SOS_norm_A","SOS_norm_B"} <= set(merged_df.columns):
        feats["SOS_Diff"] = diff("SOS_norm_A","SOS_norm_B")
    if {"SOS_iterative_norm_A","SOS_iterative_norm_B"} <= set(merged_df.columns):
        feats["SOSi_Diff"] = diff("SOS_iterative_norm_A","SOS_iterative_norm_B")

    X = pd.DataFrame(feats)
    return X, list(X.columns)


def power_plus_elo_feature_builder(merged_df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """
    Build feature set with optional ELO support.
    
    This function extends the default feature builder by adding ELO rating
    differences when available from the Iterative SOS engine.
    
    Args:
        merged_df: Merged games and rankings dataframe
        
    Returns:
        Tuple of (feature_dataframe, feature_column_names)
    """
    # Start with default features
    X, features = default_feature_builder(merged_df)
    
    # Check for ELO ratings (from Iterative SOS)
    elo_cols = ['ELO_Rating_A', 'ELO_Rating_B', 'Rating_A', 'Rating_B']
    if any(col in merged_df.columns for col in elo_cols):
        if 'ELO_Rating_A' in merged_df.columns:
            X['ELO_RatingDiff'] = merged_df['ELO_Rating_A'] - merged_df['ELO_Rating_B']
            features.append('ELO_RatingDiff')
        elif 'Rating_A' in merged_df.columns:
            X['ELO_RatingDiff'] = merged_df['Rating_A'] - merged_df['Rating_B']
            features.append('ELO_RatingDiff')
    
    return X, features


def minimal_feature_builder(merged_df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """
    Build minimal feature set with only PowerDiff.
    
    This is a fallback feature builder that only uses the basic PowerScore
    difference when other features are not available.
    
    Args:
        merged_df: Merged games and rankings dataframe
        
    Returns:
        Tuple of (feature_dataframe, feature_column_names)
    """
    feats = {}
    def diff(a, b): return merged_df[a] - merged_df[b]
    
    # Always try PowerScore first
    if {"PowerScore_A", "PowerScore_B"} <= set(merged_df.columns):
        feats["PowerDiff"] = diff("PowerScore_A", "PowerScore_B")
    else:
        # Fallback: simple goal diff (if ranking columns not available)
        if {"Score A", "Score B"} <= set(merged_df.columns):
            feats["GoalDiff"] = diff("Score A", "Score B")
        else:
            # Emergency: constant feature to prevent empty DataFrame crash
            feats["BiasOnly"] = np.zeros(len(merged_df))
    
    X = pd.DataFrame(feats)
    return X, list(X.columns)


def comprehensive_feature_builder(merged_df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """
    Build comprehensive feature set with all available features.
    
    This function attempts to include all possible features, including
    any custom or experimental features that might be added in the future.
    
    Args:
        merged_df: Merged games and rankings dataframe
        
    Returns:
        Tuple of (feature_dataframe, feature_column_names)
    """
    # Start with default features
    X, features = default_feature_builder(merged_df)
    
    # Add ELO features if available
    if 'ELO_RatingDiff' in merged_df.columns:
        X['ELO_RatingDiff'] = merged_df['ELO_RatingDiff']
        features.append('ELO_RatingDiff')
    
    # Add any other potential features
    potential_features = [
        'Form_Diff',  # Form-based features
        'Recent_Win_Rate_Diff',  # Recent performance
        'Home_Away_Diff',  # Venue-based features
        'Tournament_Pressure_Diff',  # Tournament context
        'Head_to_Head_Diff',  # Historical matchup
        'Season_Phase_Diff',  # Timing-based features
    ]
    
    for feature in potential_features:
        if feature in merged_df.columns:
            X[feature] = merged_df[feature]
            features.append(feature)
    
    return X, features


def get_feature_importance_names(features: List[str]) -> Dict[str, str]:
    """
    Get human-readable names for features.
    
    Args:
        features: List of feature column names
        
    Returns:
        Dictionary mapping feature names to human-readable descriptions
    """
    feature_names = {
        'PowerDiff': 'PowerScore Difference',
        'SAO_Diff': 'Offensive Strength Difference',
        'SAD_Diff_Inverted': 'Defensive Strength Difference (Inverted)',
        'SOS_Diff': 'Strength of Schedule Difference',
        'SOSi_Diff': 'Iterative SOS Difference',
        'ELO_RatingDiff': 'ELO Rating Difference',
        'Form_Diff': 'Recent Form Difference',
        'Recent_Win_Rate_Diff': 'Recent Win Rate Difference',
        'Home_Away_Diff': 'Home/Away Advantage Difference',
        'Tournament_Pressure_Diff': 'Tournament Pressure Difference',
        'Head_to_Head_Diff': 'Head-to-Head History Difference',
        'Season_Phase_Diff': 'Season Phase Difference',
    }
    
    return {f: feature_names.get(f, f) for f in features}


def validate_features(merged_df: pd.DataFrame, features: List[str]) -> List[str]:
    """
    Validate that all features exist and have valid data.
    
    Args:
        merged_df: Merged games and rankings dataframe
        features: List of feature column names to validate
        
    Returns:
        List of valid feature column names
    """
    valid_features = []
    
    for feature in features:
        if feature not in merged_df.columns:
            print(f"Warning: Feature '{feature}' not found in dataframe")
            continue
            
        # Check for non-null values
        if merged_df[feature].isna().all():
            print(f"Warning: Feature '{feature}' has all null values")
            continue
            
        # Check for infinite values
        if np.isinf(merged_df[feature]).any():
            print(f"Warning: Feature '{feature}' contains infinite values")
            continue
            
        valid_features.append(feature)
    
    return valid_features


def compute_feature_statistics(merged_df: pd.DataFrame, features: List[str]) -> Dict[str, Dict]:
    """
    Compute basic statistics for features.
    
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
                'infinite_count': np.isinf(merged_df[feature]).sum()
            }
    
    return stats


def create_feature_correlation_matrix(merged_df: pd.DataFrame, features: List[str]) -> pd.DataFrame:
    """
    Create correlation matrix for features.
    
    Args:
        merged_df: Merged games and rankings dataframe
        features: List of feature column names
        
    Returns:
        Correlation matrix as DataFrame
    """
    # Filter to only existing features
    existing_features = [f for f in features if f in merged_df.columns]
    
    if not existing_features:
        return pd.DataFrame()
    
    # Compute correlation matrix
    corr_matrix = merged_df[existing_features].corr()
    
    return corr_matrix


def suggest_feature_engineering(merged_df: pd.DataFrame) -> List[str]:
    """
    Suggest additional features based on available data.
    
    Args:
        merged_df: Merged games and rankings dataframe
        
    Returns:
        List of suggested feature engineering operations
    """
    suggestions = []
    
    # Check for date-based features
    if 'Date' in merged_df.columns:
        suggestions.append("Consider adding 'Days_Since_Last_Game' feature")
        suggestions.append("Consider adding 'Season_Phase' feature (early/mid/late)")
    
    # Check for score-based features
    if 'Score A' in merged_df.columns and 'Score B' in merged_df.columns:
        suggestions.append("Consider adding 'Goal_Differential' feature")
        suggestions.append("Consider adding 'Total_Goals' feature")
        suggestions.append("Consider adding 'Close_Game' binary feature (diff <= 1)")
    
    # Check for team-specific features
    if 'Team A' in merged_df.columns and 'Team B' in merged_df.columns:
        suggestions.append("Consider adding 'Head_to_Head_History' feature")
        suggestions.append("Consider adding 'Recent_Form' feature (last 5 games)")
    
    # Check for venue features
    if 'Venue' in merged_df.columns or 'Home_Away' in merged_df.columns:
        suggestions.append("Consider adding 'Home_Advantage' feature")
    
    # Check for tournament features
    if 'Tournament' in merged_df.columns or 'Competition' in merged_df.columns:
        suggestions.append("Consider adding 'Tournament_Importance' feature")
    
    return suggestions


if __name__ == "__main__":
    # Example usage
    print("Feature Builders V5.3+ - Example Usage")
    print("=" * 50)
    
    # Create sample data
    sample_data = pd.DataFrame({
        'PowerDiff': [0.1, -0.2, 0.3, -0.1, 0.0],
        'SAO_Diff': [0.05, -0.15, 0.25, -0.05, 0.0],
        'SAD_Diff_Inverted': [0.02, -0.08, 0.12, -0.02, 0.0],
        'SOS_Diff': [0.03, -0.10, 0.18, -0.03, 0.0],
        'SOSi_Diff': [0.04, -0.12, 0.20, -0.04, 0.0],
        'ELO_RatingDiff': [50, -100, 150, -50, 0],
        'Team_A_Wins': [1, 0, 1, 0, 1]
    })
    
    print(f"Sample data shape: {sample_data.shape}")
    print(f"Sample data columns: {list(sample_data.columns)}")
    
    # Test different feature builders
    builders = [
        ("Default", default_feature_builder),
        ("Power + ELO", power_plus_elo_feature_builder),
        ("Minimal", minimal_feature_builder),
        ("Comprehensive", comprehensive_feature_builder)
    ]
    
    for name, builder_func in builders:
        features = builder_func(sample_data)
        print(f"\n{name} Feature Builder:")
        print(f"  Features: {features}")
        
        # Validate features
        valid_features = validate_features(sample_data, features)
        print(f"  Valid features: {valid_features}")
        
        # Get feature names
        feature_names = get_feature_importance_names(features)
        print(f"  Feature names: {feature_names}")
    
    # Compute feature statistics
    all_features = comprehensive_feature_builder(sample_data)
    stats = compute_feature_statistics(sample_data, all_features)
    
    print(f"\nFeature Statistics:")
    for feature, stat_dict in stats.items():
        print(f"  {feature}: mean={stat_dict['mean']:.3f}, std={stat_dict['std']:.3f}")
    
    # Create correlation matrix
    corr_matrix = create_feature_correlation_matrix(sample_data, all_features)
    print(f"\nCorrelation Matrix:")
    print(corr_matrix.round(3))
    
    # Suggest feature engineering
    suggestions = suggest_feature_engineering(sample_data)
    print(f"\nFeature Engineering Suggestions:")
    for suggestion in suggestions:
        print(f"  - {suggestion}")
