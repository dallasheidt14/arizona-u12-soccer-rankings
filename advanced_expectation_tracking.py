"""
Advanced Expectation Tracking - Level 2 Opponent-Adjusted Model
Clean, vectorized implementation with calibration and impact buckets
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Tuple, Optional
import config

@dataclass
class ExpectationCalib:
    """Calibration parameters for expectation model."""
    gamma: float = 1.0  # slope
    delta: float = 0.0  # intercept
    calibrated: bool = False
    sample_count: int = 0

def _robust_minmax(series: pd.Series) -> pd.Series:
    """Robust min-max normalization with outlier protection."""
    if len(series) == 0:
        return series
    
    # Use percentiles to avoid extreme outliers
    p5, p95 = series.quantile([0.05, 0.95])
    
    if p5 == p95:
        return pd.Series([0.5] * len(series), index=series.index)
    
    # Clip extreme values and normalize
    clipped = series.clip(lower=p5, upper=p95)
    normalized = (clipped - p5) / (p95 - p5)
    
    return normalized

def _merge_team_components(long_games_df: pd.DataFrame, team_components_df: pd.DataFrame) -> pd.DataFrame:
    """Merge team offensive/defensive components into games data."""
    # Prepare components lookup - use GFPG and GAPG if Off_norm/Def_norm not available
    if "Off_norm" in team_components_df.columns and "Def_norm" in team_components_df.columns:
        comp = team_components_df[["Team", "Off_norm", "Def_norm"]].copy()
        comp_A = comp.rename(columns={"Team": "Team_A", "Off_norm": "Off_norm_A", "Def_norm": "Def_norm_A"})
        comp_B = comp.rename(columns={"Team": "Opponent", "Off_norm": "Off_norm_B", "Def_norm": "Def_norm_B"})
    else:
        # Fallback to GFPG/GAPG and normalize on the fly
        comp = team_components_df[["Team", "GFPG", "GAPG"]].copy()
        # Normalize GFPG and GAPG to 0-1 range
        comp["Off_norm"] = _robust_minmax(comp["GFPG"])
        comp["Def_norm"] = _robust_minmax(1.0 / (1.0 + comp["GAPG"]))
        comp_A = comp.rename(columns={"Team": "Team_A", "Off_norm": "Off_norm_A", "Def_norm": "Def_norm_A"})
        comp_B = comp.rename(columns={"Team": "Opponent", "Off_norm": "Off_norm_B", "Def_norm": "Def_norm_B"})

    df = long_games_df.copy()
    df = df.merge(comp_A, left_on="Team", right_on="Team_A", how="left")
    df = df.merge(comp_B, on="Opponent", how="left")
    return df

def _raw_expected_gd(df: pd.DataFrame, alpha: float, beta: float) -> pd.Series:
    """
    Calculate raw expected goal differential.
    
    Formula: EGD_raw = α*(Off_A - Def_B) - β*(Off_B - Def_A)
    """
    return alpha * (df["Off_norm_A"] - df["Def_norm_B"]) - beta * (df["Off_norm_B"] - df["Def_norm_A"])

def _fit_calibration(df: pd.DataFrame, window_days: int) -> ExpectationCalib:
    """
    Fit calibration parameters to match expected GD to actual GD.
    
    Uses simple OLS: actual_gd ≈ gamma * EGD_raw + delta
    """
    # Filter to calibration window with valid data
    now = pd.Timestamp.now()
    cutoff = now - pd.Timedelta(days=window_days)
    
    use = df[
        (df["Date"] >= cutoff) & 
        df["Goals For"].notna() & 
        df["Goals Against"].notna() &
        df["EGD_raw"].notna()
    ].copy()
    
    if len(use) < config.EXPECT_CALIB_MIN_SAMPLES or use["EGD_raw"].std(ddof=1) == 0:
        return ExpectationCalib(calibrated=False, sample_count=len(use))
    
    # Simple OLS: y ≈ gamma*x + delta
    y = (use["Goals For"] - use["Goals Against"]).values
    x = use["EGD_raw"].values
    
    X = np.vstack([x, np.ones_like(x)]).T
    try:
        gamma, delta = np.linalg.lstsq(X, y, rcond=None)[0]
        return ExpectationCalib(
            gamma=float(gamma), 
            delta=float(delta), 
            calibrated=True,
            sample_count=len(use)
        )
    except np.linalg.LinAlgError:
        return ExpectationCalib(calibrated=False, sample_count=len(use))

def add_expected_gd_advanced(
    long_games_df: pd.DataFrame,
    team_stats_df: pd.DataFrame,
    alpha: float = None,
    beta: float = None,
    clip_abs: float = None,
    calibrate: bool = None,
    calib_window_days: int = None,
    impact_thresholds: Tuple[float, float] = None
) -> Tuple[pd.DataFrame, ExpectationCalib]:
    """
    Add advanced opponent-adjusted expected goal differential to games data.
    
    Args:
        long_games_df: DataFrame with game data (Team, Opponent, Goals For, Goals Against, Date)
        team_stats_df: DataFrame with team stats (Team, Off_norm, Def_norm)
        alpha: Weight on (Off_A - Def_B)
        beta: Weight on (Off_B - Def_A), subtracted
        clip_abs: Cap on absolute expected GD
        calibrate: Whether to calibrate to actual goal scale
        calib_window_days: Days to use for calibration
        impact_thresholds: (low, high) thresholds for impact buckets
        
    Returns:
        Tuple of (enhanced_df, calibration_info)
    """
    # Use config defaults if not provided
    alpha = alpha or config.EXPECT_ALPHA
    beta = beta or config.EXPECT_BETA
    clip_abs = clip_abs or config.EXPECT_GOAL_CLIP
    calibrate = calibrate if calibrate is not None else config.EXPECT_CALIBRATE
    calib_window_days = calib_window_days or config.EXPECT_CALIB_WINDOW_DAYS
    impact_thresholds = impact_thresholds or config.IMPACT_THRESHOLDS
    
    # Merge team components
    df = _merge_team_components(long_games_df, team_stats_df)
    
    # Compute raw expected GD
    df["EGD_raw"] = _raw_expected_gd(df, alpha, beta)
    
    # Handle missing components
    needs = ["Off_norm_A", "Def_norm_A", "Off_norm_B", "Def_norm_B"]
    mask_missing = df[needs].isna().any(axis=1)
    
    # Initialize expected_gd and gd_delta columns
    df["expected_gd"] = np.nan
    df["gd_delta"] = np.nan
    df["impact_bucket"] = "no_data"
    
    # Calibration
    calib = ExpectationCalib()
    if calibrate and not mask_missing.all():
        calib = _fit_calibration(df, calib_window_days)
        
        # Try fallback window if calibration failed
        if not calib.calibrated and config.EXPECT_CALIB_FALLBACK_WINDOW_DAYS:
            calib = _fit_calibration(df, config.EXPECT_CALIB_FALLBACK_WINDOW_DAYS)
    
    # Apply calibration to non-missing data
    valid_mask = ~mask_missing
    if valid_mask.any():
        df.loc[valid_mask, "expected_gd"] = (
            calib.gamma * df.loc[valid_mask, "EGD_raw"] + calib.delta
        )
        
        # Optional clipping
        if clip_abs:
            df.loc[valid_mask, "expected_gd"] = df.loc[valid_mask, "expected_gd"].clip(
                lower=-clip_abs, upper=clip_abs
            )
        
        # Calculate actual vs expected
        df.loc[valid_mask, "actual_gd"] = (
            df.loc[valid_mask, "Goals For"] - df.loc[valid_mask, "Goals Against"]
        )
        df.loc[valid_mask, "gd_delta"] = (
            df.loc[valid_mask, "actual_gd"] - df.loc[valid_mask, "expected_gd"]
        )
        
        # Impact buckets
        lo, hi = impact_thresholds
        df.loc[valid_mask, "impact_bucket"] = pd.cut(
            df.loc[valid_mask, "gd_delta"],
            bins=[-np.inf, lo, hi, np.inf],
            labels=["weak", "neutral", "good"]
        )
    
    # Round for UI display
    df["expected_gd"] = df["expected_gd"].round(2)
    df["gd_delta"] = df["gd_delta"].round(2)
    
    return df, calib

def add_expected_gd_simple(
    long_games_df: pd.DataFrame,
    team_stats_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Simple expectation tracking (legacy method).
    
    This is the original simple implementation for backward compatibility.
    """
    df = long_games_df.copy()
    
    # Simple expectation calculation
    expected_gds = []
    gd_deltas = []
    impact_buckets = []
    
    for _, row in df.iterrows():
        team_a = row["Team"]
        team_b = row["Opponent"]
        actual_gd = row["Goals For"] - row["Goals Against"]
        
        # Get team statistics
        stats_a = team_stats_df[team_stats_df["Team"] == team_a]
        stats_b = team_stats_df[team_stats_df["Team"] == team_b]
        
        if stats_a.empty or stats_b.empty:
            expected_gds.append(np.nan)
            gd_deltas.append(np.nan)
            impact_buckets.append("no_data")
            continue
        
        # Simple model: expected goals = offensive rating * (1 - opponent defensive rating)
        off_a = stats_a.iloc[0].get("Off_norm", 0.5)
        def_a = stats_a.iloc[0].get("Def_norm", 0.5)
        off_b = stats_b.iloc[0].get("Off_norm", 0.5)
        def_b = stats_b.iloc[0].get("Def_norm", 0.5)
        
        scale_factor = 2.0
        exp_goals_a = off_a * (1 - def_b) * scale_factor
        exp_goals_b = off_b * (1 - def_a) * scale_factor
        exp_gd = exp_goals_a - exp_goals_b
        
        expected_gds.append(exp_gd)
        
        # Calculate delta
        gd_delta = actual_gd - exp_gd
        gd_deltas.append(gd_delta)
        
        # Categorize impact
        if gd_delta <= config.IMPACT_THRESHOLDS[0]:
            impact_buckets.append("weak")
        elif gd_delta >= config.IMPACT_THRESHOLDS[1]:
            impact_buckets.append("good")
        else:
            impact_buckets.append("neutral")
    
    # Add columns
    df["expected_gd"] = expected_gds
    df["gd_delta"] = gd_deltas
    df["impact_bucket"] = impact_buckets
    
    return df

def add_pk_handling(games_df: pd.DataFrame) -> pd.DataFrame:
    """
    Add PK handling to games data.
    
    Uses regulation score for ranking, annotates PK results for UI.
    """
    if not config.ENABLE_PK_HANDLING:
        return games_df
    
    enhanced_df = games_df.copy()
    
    # Initialize PK columns
    enhanced_df["decider"] = "regulation"
    enhanced_df["pk_annotation"] = ""
    
    # Check for PK indicators in the data
    # This is a simplified implementation - adapt based on your data structure
    pk_indicators = ["PK", "penalty", "shootout", "SO"]
    
    for idx, row in enhanced_df.iterrows():
        # Check if this was decided by PKs (simplified detection)
        # In practice, you'd have a specific column or pattern to detect this
        if any(indicator.lower() in str(row.get("Notes", "")).lower() for indicator in pk_indicators):
            enhanced_df.at[idx, "decider"] = "PK"
            enhanced_df.at[idx, "pk_annotation"] = "Decided by PKs"
            
            # For ranking purposes, treat PK wins as regulation ties (GD = 0)
            if row["Goals For"] != row["Goals Against"]:
                enhanced_df.at[idx, "Goals For"] = row["Goals Against"]  # Set to tie for ranking
                enhanced_df.at[idx, "pk_annotation"] = f"Won on PKs (regulation: {row['Goals For']}-{row['Goals Against']})"
    
    return enhanced_df

def add_expectation_tracking(
    long_games_df: pd.DataFrame,
    team_stats_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Main function to add expectation tracking based on configured model.
    
    Args:
        long_games_df: DataFrame with game data
        team_stats_df: DataFrame with team statistics
        
    Returns:
        Enhanced DataFrame with expectation columns
    """
    if not config.ENABLE_EXPECTATION_TRACKING:
        return long_games_df
    
    # Add PK handling first
    enhanced_df = add_pk_handling(long_games_df)
    
    if config.EXPECTATION_MODEL == "opponent_adjusted_v1":
        enhanced_df, calib = add_expected_gd_advanced(enhanced_df, team_stats_df)
        
        # Log calibration info
        if calib.calibrated:
            print(f"Expectation calibration: gamma={calib.gamma:.3f}, delta={calib.delta:.3f}, samples={calib.sample_count}")
        else:
            print(f"Expectation calibration failed: using raw values, samples={calib.sample_count}")
        
        return enhanced_df
    elif config.EXPECTATION_MODEL == "simple":
        return add_expected_gd_simple(enhanced_df, team_stats_df)
    else:
        raise ValueError(f"Unknown expectation model: {config.EXPECTATION_MODEL}")

def validate_expectation_model(df: pd.DataFrame) -> dict:
    """
    Validate expectation model quality.
    
    Returns:
        Dictionary with validation metrics
    """
    metrics = {}
    
    # Check calibration quality
    if config.EXPECT_CALIBRATE:
        valid_data = df[df["expected_gd"].notna()]
        if len(valid_data) > 0:
            mean_expected = valid_data["expected_gd"].mean()
            metrics["mean_expected_gd"] = mean_expected
            metrics["calibration_centered"] = abs(mean_expected) < 0.15
            
            # Check correlation
            correlation = valid_data["expected_gd"].corr(valid_data["actual_gd"])
            metrics["expected_actual_correlation"] = correlation
            metrics["correlation_positive"] = correlation > 0
    
    # Check impact bucket distribution
    bucket_counts = df["impact_bucket"].value_counts()
    total_valid = bucket_counts.sum()
    
    if total_valid > 0:
        for bucket in ["good", "neutral", "weak", "no_data"]:
            if bucket in bucket_counts:
                metrics[f"{bucket}_percentage"] = bucket_counts[bucket] / total_valid * 100
                metrics[f"{bucket}_not_extreme"] = bucket_counts[bucket] / total_valid < 0.8
    
    return metrics
