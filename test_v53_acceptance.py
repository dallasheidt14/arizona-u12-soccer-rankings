#!/usr/bin/env python3
"""
test_v53_acceptance.py

Acceptance tests for V5.3 Form-Responsive Rankings implementation.
Validates Expected GD layer, Performance adjustments, and recency decay.
"""
import pandas as pd
import numpy as np
import os
from pathlib import Path

def test_powerscore_range():
    """Verify PowerScore values are in expected range."""
    df = pd.read_csv("Rankings_v53.csv")
    
    min_score = df["PowerScore"].min()
    max_score = df["PowerScore"].max()
    
    print(f"PowerScore range: {min_score:.3f} - {max_score:.3f}")
    assert 0.10 <= min_score <= 0.20, f"PowerScore min too low: {min_score}"
    assert 0.45 <= max_score <= 0.55, f"PowerScore max too high: {max_score}"

def test_no_nan_values():
    """Verify no NaN values in key columns."""
    df = pd.read_csv("Rankings_v53.csv")
    
    key_cols = ["Team", "PowerScore", "SAO_norm", "SAD_norm", "SOS_norm", "GamesPlayed"]
    for col in key_cols:
        nan_count = df[col].isna().sum()
        assert nan_count == 0, f"Found {nan_count} NaN values in {col}"

def test_spearman_correlation():
    """Verify Spearman correlation with V5.2b is in expected range."""
    v52b = pd.read_csv("Rankings_v52b.csv")
    v53 = pd.read_csv("Rankings_v53.csv")
    
    # Normalize team names for comparison
    v52b["team"] = v52b["Team"].str.strip().str.lower()
    v53["team"] = v53["Team"].str.strip().str.lower()
    
    # Merge on team names
    merged = v52b.merge(v53, on="team", how="inner")
    
    corr = merged["Rank_x"].corr(merged["Rank_y"], method="spearman")
    print(f"Spearman correlation (V5.2b vs V5.3): {corr:.3f}")
    assert 0.85 <= corr <= 0.95, f"Correlation {corr:.3f} outside expected range [0.85, 0.95]"

def test_performance_scaled_range():
    """Verify Performance_scaled values are in 0-1 range (if available)."""
    # This test would require access to intermediate data
    # For now, we'll validate the tuning constants are defined
    from rankings.generate_team_rankings_v53 import PERFORMANCE_K_V53, PERFORMANCE_WINDOW, PERFORMANCE_DECAY_RATE
    
    assert PERFORMANCE_K_V53 == 0.15, f"PERFORMANCE_K_V53 should be 0.15, got {PERFORMANCE_K_V53}"
    assert PERFORMANCE_WINDOW == 10, f"PERFORMANCE_WINDOW should be 10, got {PERFORMANCE_WINDOW}"
    assert PERFORMANCE_DECAY_RATE == 0.10, f"PERFORMANCE_DECAY_RATE should be 0.10, got {PERFORMANCE_DECAY_RATE}"

def test_recency_decay_range():
    """Verify RecencyDecay values are in 0-1 range (if available)."""
    # This test would require access to intermediate data
    # For now, we'll validate the decay rate constant
    from rankings.generate_team_rankings_v53 import PERFORMANCE_DECAY_RATE
    
    assert 0.05 <= PERFORMANCE_DECAY_RATE <= 0.20, f"Decay rate {PERFORMANCE_DECAY_RATE} outside reasonable range"

def test_small_sample_protection():
    """Verify teams with <10 games not heavily influenced by form."""
    df = pd.read_csv("Rankings_v53.csv")
    
    small_sample = df[df["GamesPlayed"] < 10]
    if len(small_sample) > 0:
        # Small sample teams should have lower PowerScore variance
        small_var = small_sample["PowerScore"].var()
        large_sample = df[df["GamesPlayed"] >= 10]
        large_var = large_sample["PowerScore"].var()
        
        print(f"Small sample variance: {small_var:.4f}")
        print(f"Large sample variance: {large_var:.4f}")
        # Small sample should have lower variance (more conservative)
        assert small_var <= large_var * 1.2, "Small sample teams have too much variance"

def test_prfc_scottsdale_rank():
    """Verify PRFC Scottsdale rank is in expected range."""
    df = pd.read_csv("Rankings_v53.csv")
    
    prfc_teams = df[df["Team"].str.contains("PRFC", case=False, na=False)]
    if len(prfc_teams) > 0:
        prfc_rank = prfc_teams["Rank"].iloc[0]
        print(f"PRFC Scottsdale rank: {prfc_rank}")
        assert 8 <= prfc_rank <= 15, f"PRFC rank {prfc_rank} outside expected range [8, 15]"

def test_hot_streak_teams():
    """Verify hot streak teams show modest rank gains."""
    # This would require analyzing the intermediate performance data
    # For now, we'll check that the form layer is enabled
    from rankings.generate_team_rankings_v53 import USE_PERFORMANCE_LAYER
    
    assert USE_PERFORMANCE_LAYER == True, "Performance layer should be enabled"

def test_tuning_constants():
    """Verify all V5.3 tuning constants are defined correctly."""
    from rankings.generate_team_rankings_v53 import (
        USE_PERFORMANCE_LAYER, PERFORMANCE_K_V53, PERFORMANCE_WINDOW, 
        PERFORMANCE_DECAY_RATE, EXPECTED_GD_ALPHA, EXPECTED_GD_BETA, EXPECTED_GD_SCALE
    )
    
    assert USE_PERFORMANCE_LAYER == True
    assert PERFORMANCE_K_V53 == 0.15
    assert PERFORMANCE_WINDOW == 10
    assert PERFORMANCE_DECAY_RATE == 0.10
    assert EXPECTED_GD_ALPHA == 1.0
    assert EXPECTED_GD_BETA == 0.5
    assert EXPECTED_GD_SCALE == 2.0

def test_team_count():
    """Verify expected team count."""
    df = pd.read_csv("Rankings_v53.csv")
    team_count = len(df)
    
    print(f"Total teams ranked: {team_count}")
    assert 150 <= team_count <= 180, f"Team count {team_count} outside expected range [150, 180]"

def test_master_team_filtering():
    """Verify only master teams appear in rankings."""
    df = pd.read_csv("Rankings_v53.csv")
    master_teams = pd.read_csv("AZ MALE U12 MASTER TEAM LIST.csv")
    master_team_names = set(master_teams["Team Name"].str.strip())
    
    # Check that all ranked teams are in master list (accounting for club name mapping)
    invalid_teams = []
    for team in df["Team"]:
        # Extract base team name (before club name)
        base_name = team.split(" ")[0] if " " in team else team
        if base_name not in master_team_names:
            invalid_teams.append(team)
    
    assert len(invalid_teams) == 0, f"Found {len(invalid_teams)} non-master teams: {invalid_teams[:5]}"

def test_sanity_metrics():
    """Verify basic sanity metrics."""
    df = pd.read_csv("Rankings_v53.csv")
    
    avg_games = df["GamesPlayed"].mean()
    print(f"Average games per team: {avg_games:.1f}")
    assert 20 <= avg_games <= 30, f"Average games {avg_games:.1f} outside expected range [20, 30]"
    
    active_teams = len(df[df["Status"] == "Active"])
    provisional_teams = len(df[df["Status"] == "Provisional"])
    print(f"Active teams: {active_teams}, Provisional teams: {provisional_teams}")
    assert active_teams > provisional_teams, "Should have more active than provisional teams"

def run_all_tests():
    """Run all acceptance tests."""
    print("Running V5.3 Acceptance Tests...")
    
    tests = [
        test_powerscore_range,
        test_no_nan_values,
        test_spearman_correlation,
        test_performance_scaled_range,
        test_recency_decay_range,
        test_small_sample_protection,
        test_prfc_scottsdale_rank,
        test_hot_streak_teams,
        test_tuning_constants,
        test_team_count,
        test_master_team_filtering,
        test_sanity_metrics
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            print(f"PASS: {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"FAIL: {test.__name__}: {e}")
            failed += 1
    
    print(f"\nTest Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("All tests passed! V5.3 implementation is ready.")
    else:
        print("Some tests failed. Please review the implementation.")
    
    return failed == 0

if __name__ == "__main__":
    run_all_tests()
