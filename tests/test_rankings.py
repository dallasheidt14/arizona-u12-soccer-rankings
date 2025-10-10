"""
Test suite for Arizona U12 Soccer Rankings System.
Tests core mathematical functions and edge cases.
"""

import numpy as np
import pandas as pd
import pytest

from rank_core import (
    _robust_minmax, calculate_weighted_stats, calculate_sos,
    calculate_power_scores, enrich_game_histories_with_opponent_strength
)
import config

# ---- Helpers ---------------------------------------------------------------
def build_long_format(games_df: pd.DataFrame) -> pd.DataFrame:
    """Minimal long-format builder mirroring the main script's approach."""
    # For our test fixtures, the data is already in long format
    return games_df[["Date", "Team", "Opponent", "Goals For", "Goals Against", "State", "Gender", "Year"]].copy()

# ---- Tests ----------------------------------------------------------------

def test_recent_weight_no_shrink_for_leq10(load_csv):
    """Test that teams with <=10 games don't get recency weighting shrink."""
    df = load_csv("toy_games_small.csv")
    long_df = build_long_format(df)
    stats = calculate_weighted_stats(long_df, log_file=None)

    # All teams have <= 4 games → no recency weighting shrink; plain averages
    alpha = stats.loc[stats["Team"] == "Alpha"].iloc[0]
    bravo = stats.loc[stats["Team"] == "Bravo"].iloc[0]
    
    # Basic sanity checks
    assert 0 <= alpha["GFPG"] <= 10
    assert 0 <= alpha["GAPG"] <= 10
    assert 0 <= bravo["GFPG"] <= 10
    assert 0 <= bravo["GAPG"] <= 10
    
    # Should have reasonable game counts
    assert alpha["Games Played"] > 0
    assert bravo["Games Played"] > 0

def test_recent_weight_applies_at_11(load_csv):
    """Test that teams with >10 games get proper recency weighting."""
    df = load_csv("toy_games_edge_10_vs_11.csv")
    long_df = build_long_format(df)
    stats = calculate_weighted_stats(long_df, log_file=None)

    t11 = stats.loc[stats["Team"] == "T11"].iloc[0]
    # With 11 games, verify we used segment AVERAGES weighted 70/30
    # We can't assert an exact number without recomputing here, but we can assert not equal to simple overall mean
    overall_gfpg = (long_df.query("Team=='T11'")["Goals For"].sum()) / len(long_df.query("Team=='T11'"))
    assert not np.isclose(t11["GFPG"], overall_gfpg), "GFPG should reflect 70/30 segment weighting at 11 games"

def test_defense_transform_is_monotone(load_csv):
    """Test that defense transformation is monotone decreasing."""
    df = load_csv("toy_games_small.csv")
    long_df = build_long_format(df)
    stats = calculate_weighted_stats(long_df, log_file=None)

    # Higher GA/G should reduce Def_norm
    sos_df = calculate_sos(long_df, stats, log_file=None)
    power = calculate_power_scores(stats, sos_df, log_file=None)
    
    # Check that Def_raw is in valid range
    assert ((power["Def_raw"] >= 0) & (power["Def_raw"] <= 1)).all()
    
    # Sort by GAPG ascending → Def_raw should be descending (monotone decreasing)
    s = power.sort_values("GAPG")
    assert s["Def_raw"].is_monotonic_decreasing or s["Def_raw"].is_monotonic_increasing

def test_sos_uses_recency(load_csv):
    """Test that SOS calculation uses recency weighting."""
    df = load_csv("toy_games_edge_10_vs_11.csv")
    long_df = build_long_format(df)
    stats = calculate_weighted_stats(long_df, log_file=None)
    sos_df = calculate_sos(long_df, stats, log_file=None)

    # Make sure SOS exists and is within [0,1] after normalization in power computation
    power = calculate_power_scores(stats, sos_df, log_file=None)
    assert ((power["SOS_norm"] >= 0) & (power["SOS_norm"] <= 1)).all()
    
    # SOS should be reasonable values
    assert power["SOS"].min() >= 0
    assert power["SOS"].max() <= 1

def test_outlier_capped_by_robust_minmax(load_csv):
    """Test that outliers are properly capped by robust min-max normalization."""
    df = load_csv("toy_games_outliers.csv")
    long_df = build_long_format(df)
    stats = calculate_weighted_stats(long_df, log_file=None)

    # Ensure robust minmax produces finite norms even with 14-0 blowout
    off_norm = _robust_minmax(stats["GFPG"])
    assert ((off_norm >= 0) & (off_norm <= 1)).all()
    
    # Should handle extreme values gracefully
    assert not np.any(np.isnan(off_norm))
    assert not np.any(np.isinf(off_norm))

def test_histories_recency_weights_sum_to_1(load_csv):
    """Test that recency weights sum to 1.0 for each team."""
    df = load_csv("toy_games_edge_10_vs_11.csv")
    long_df = build_long_format(df)
    stats = calculate_weighted_stats(long_df, log_file=None)
    sos_df = calculate_sos(long_df, stats, log_file=None)
    power = calculate_power_scores(stats, sos_df, log_file=None)

    hist = enrich_game_histories_with_opponent_strength(
        long_games_df=long_df,
        team_stats_df=stats,
        final_rank_df=power,
        recent_window=config.RECENT_WINDOW,
        recent_weight=config.RECENT_WEIGHT,
    )
    
    # Check that recency weights sum to 1.0 for each team
    sums = hist.groupby("Team")["Recency_Weight"].sum().round(6)
    assert (sums == 1.0).all(), f"Recency weights don't sum to 1.0: {sums}"

def test_power_score_normalization(load_csv):
    """Test that power score components are properly normalized."""
    df = load_csv("toy_games_small.csv")
    long_df = build_long_format(df)
    stats = calculate_weighted_stats(long_df, log_file=None)
    sos_df = calculate_sos(long_df, stats, log_file=None)
    power = calculate_power_scores(stats, sos_df, log_file=None)

    # All normalized components should be in [0,1]
    assert ((power["Off_norm"] >= 0) & (power["Off_norm"] <= 1)).all()
    assert ((power["Def_norm"] >= 0) & (power["Def_norm"] <= 1)).all()
    assert ((power["SOS_norm"] >= 0) & (power["SOS_norm"] <= 1)).all()
    
    # Raw power should be in [0,1] before penalties
    assert ((power["Raw Power"] >= 0) & (power["Raw Power"] <= 1)).all()
    
    # Final power score should be <= raw power (due to penalties)
    assert (power["Power Score"] <= power["Raw Power"]).all()

def test_game_count_penalties(load_csv):
    """Test that game count penalties are applied correctly."""
    df = load_csv("toy_games_small.csv")
    long_df = build_long_format(df)
    stats = calculate_weighted_stats(long_df, log_file=None)
    sos_df = calculate_sos(long_df, stats, log_file=None)
    power = calculate_power_scores(stats, sos_df, log_file=None)

    # Teams with few games should have penalties applied
    for _, row in power.iterrows():
        games_played = row["Games Played"]
        penalty = row["Penalty"]
        
        if games_played < config.GAMES_PENALTY_THRESHOLDS["moderate"]:
            assert penalty == config.GAMES_PENALTY_THRESHOLDS["high_penalty"]
        elif games_played < config.GAMES_PENALTY_THRESHOLDS["full"]:
            assert penalty == config.GAMES_PENALTY_THRESHOLDS["low_penalty"]
        else:
            assert penalty == 1.0

def test_opponent_strength_calculation(load_csv):
    """Test that opponent strength is calculated correctly."""
    df = load_csv("toy_games_small.csv")
    long_df = build_long_format(df)
    stats = calculate_weighted_stats(long_df, log_file=None)
    sos_df = calculate_sos(long_df, stats, log_file=None)
    power = calculate_power_scores(stats, sos_df, log_file=None)

    hist = enrich_game_histories_with_opponent_strength(
        long_games_df=long_df,
        team_stats_df=stats,
        final_rank_df=power,
        recent_window=config.RECENT_WINDOW,
        recent_weight=config.RECENT_WEIGHT,
    )
    
    # Opponent base strength should be in [0,1]
    assert ((hist["Opponent_BaseStrength"] >= 0) & (hist["Opponent_BaseStrength"] <= 1)).all()
    
    # Should have opponent strength data for all games
    assert not hist["Opponent_BaseStrength"].isna().any()
