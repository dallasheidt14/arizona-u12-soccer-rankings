#!/usr/bin/env python3
"""
Core Correctness Tests for V5.3E Enhanced Rankings
===================================================

This module contains essential correctness tests for the enhanced ranking system:
- Schema validation: Verify all required columns exist and are typed correctly
- Determinism: Run ranking job twice on same data, assert identical outputs
- Monotonicity: Adding a clear win should not decrease PowerScore significantly
- Outlier Guard: Verify extreme values are properly capped
- Adaptive K Sanity: Verify adaptive K-factor behaves as expected

Usage:
    python tests/test_v53_enhanced_correctness.py
"""

import pandas as pd
import numpy as np
import hashlib
import subprocess
import tempfile
import os
import shutil
from pathlib import Path
import pytest


def test_schema_validation():
    """Verify all required columns exist and are typed correctly."""
    # First run the enhanced rankings script
    result = subprocess.run([
        "python", "rankings/generate_team_rankings_v53_enhanced.py",
        "--in", "Matched_Games.csv",
        "--out", "Rankings_v53_enhanced.csv"
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        pytest.fail(f"Rankings script failed: {result.stderr}")
    
    # Load and validate the output
    df = pd.read_csv("Rankings_v53_enhanced.csv")
    
    # Required columns
    required = ["Team", "PowerScore", "SAO_norm", "SAD_norm", "SOS_norm", "GamesPlayed"]
    for col in required:
        assert col in df.columns, f"Missing required column: {col}"
    
    # Type checks
    assert df["Team"].dtype == object, "Team column should be object type"
    assert pd.api.types.is_numeric_dtype(df["PowerScore"]), "PowerScore should be numeric"
    assert pd.api.types.is_integer_dtype(df["GamesPlayed"]), "GamesPlayed should be integer"
    
    # Value range checks
    assert df["PowerScore"].min() >= 0, "PowerScore should be non-negative"
    assert df["PowerScore"].max() <= 1, "PowerScore should be <= 1"
    assert df["SAO_norm"].min() >= 0, "SAO_norm should be non-negative"
    assert df["SAO_norm"].max() <= 1, "SAO_norm should be <= 1"
    assert df["SAD_norm"].min() >= 0, "SAD_norm should be non-negative"
    assert df["SAD_norm"].max() <= 1, "SAD_norm should be <= 1"
    assert df["SOS_norm"].min() >= 0, "SOS_norm should be non-negative"
    assert df["SOS_norm"].max() <= 1, "SOS_norm should be <= 1"
    
    # No NaN values in critical columns
    critical_cols = ["Team", "PowerScore", "SAO_norm", "SAD_norm", "SOS_norm"]
    for col in critical_cols:
        assert not df[col].isna().any(), f"Column {col} should not contain NaN values"
    
    print("✓ Schema validation passed")


def test_determinism():
    """Run ranking job twice on same data, assert identical outputs."""
    # Create temporary directory for test
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        
        # Copy required files to temp directory
        shutil.copy("Matched_Games.csv", temp_dir / "Matched_Games.csv")
        shutil.copy("AZ MALE U12 MASTER TEAM LIST.csv", temp_dir / "AZ MALE U12 MASTER TEAM LIST.csv")
        shutil.copy("Team_Game_Histories_COMPREHENSIVE.csv", temp_dir / "Team_Game_Histories_COMPREHENSIVE.csv")
        
        # Change to temp directory
        original_cwd = os.getcwd()
        os.chdir(temp_dir)
        
        try:
            # Run once
            result1 = subprocess.run([
                "python", str(Path(original_cwd) / "rankings" / "generate_team_rankings_v53_enhanced.py"),
                "--in", "Matched_Games.csv",
                "--out", "Rankings_v53_enhanced.csv"
            ], capture_output=True, text=True)
            
            if result1.returncode != 0:
                pytest.fail(f"First run failed: {result1.stderr}")
            
            with open("Rankings_v53_enhanced.csv", "rb") as f:
                hash1 = hashlib.md5(f.read()).hexdigest()
            
            # Run again
            result2 = subprocess.run([
                "python", str(Path(original_cwd) / "rankings" / "generate_team_rankings_v53_enhanced.py"),
                "--in", "Matched_Games.csv",
                "--out", "Rankings_v53_enhanced.csv"
            ], capture_output=True, text=True)
            
            if result2.returncode != 0:
                pytest.fail(f"Second run failed: {result2.stderr}")
            
            with open("Rankings_v53_enhanced.csv", "rb") as f:
                hash2 = hashlib.md5(f.read()).hexdigest()
            
            assert hash1 == hash2, "Rankings are not deterministic"
            
        finally:
            os.chdir(original_cwd)
    
    print("✓ Determinism test passed")


def test_monotonicity():
    """Adding a clear win should not decrease PowerScore significantly."""
    # Load original rankings
    result = subprocess.run([
        "python", "rankings/generate_team_rankings_v53_enhanced.py",
        "--in", "Matched_Games.csv",
        "--out", "Rankings_v53_enhanced.csv"
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        pytest.fail(f"Rankings script failed: {result.stderr}")
    
    df_before = pd.read_csv("Rankings_v53_enhanced.csv")
    
    # Pick a mid-ranked team for testing
    test_team = df_before.iloc[10]["Team"]
    ps_before = df_before[df_before["Team"] == test_team]["PowerScore"].iloc[0]
    
    # Create test games file with synthetic win
    games = pd.read_csv("Matched_Games.csv")
    
    # Add synthetic win for test team
    new_game = {
        "Date": "2025-10-10",
        "Team A": test_team,
        "Team B": "Test Opponent",
        "Score A": 3,
        "Score B": 0,
        "Location": "Test Field",
        "Competition": "Test League"
    }
    
    # Add required columns if they don't exist
    for col in ["Location", "Competition"]:
        if col not in games.columns:
            games[col] = "Unknown"
    
    games_with_win = pd.concat([games, pd.DataFrame([new_game])], ignore_index=True)
    games_with_win.to_csv("Matched_Games_test.csv", index=False)
    
    # Rerun rankings with synthetic win
    result = subprocess.run([
        "python", "rankings/generate_team_rankings_v53_enhanced.py",
        "--in", "Matched_Games_test.csv",
        "--out", "Rankings_v53_enhanced_test.csv"
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        pytest.fail(f"Test rankings script failed: {result.stderr}")
    
    df_after = pd.read_csv("Rankings_v53_enhanced_test.csv")
    
    # Assert PowerScore increased (or at least didn't decrease significantly)
    ps_after = df_after[df_after["Team"] == test_team]["PowerScore"].iloc[0]
    
    assert ps_after >= ps_before - 0.001, f"PowerScore decreased: {ps_before} -> {ps_after}"
    
    # Clean up test files
    os.remove("Matched_Games_test.csv")
    os.remove("Rankings_v53_enhanced_test.csv")
    
    print(f"✓ Monotonicity test passed: {test_team} PowerScore {ps_before:.3f} -> {ps_after:.3f}")


def test_outlier_guard_blowout():
    """Verify 15-0 blowout produces same result as 6-0 (due to GD cap)."""
    # Create test games with extreme blowout
    games = pd.read_csv("Matched_Games.csv")
    
    # Add required columns if they don't exist
    for col in ["Location", "Competition"]:
        if col not in games.columns:
            games[col] = "Unknown"
    
    # Pick a test team that exists in rankings
    test_team = "AZEV B2014 (WHITE) AYSO United (AZ)"
    
    # Add 15-0 blowout
    blowout_game = {
        "Date": "2025-10-10",
        "Team A": test_team,
        "Team B": "Weak Opponent",
        "Score A": 15,
        "Score B": 0,
        "Location": "Test Field",
        "Competition": "Test League"
    }
    
    games_blowout = pd.concat([games, pd.DataFrame([blowout_game])], ignore_index=True)
    games_blowout.to_csv("Matched_Games_blowout.csv", index=False)
    
    # Add 6-0 capped game
    capped_game = {
        "Date": "2025-10-10",
        "Team A": test_team,
        "Team B": "Weak Opponent",
        "Score A": 6,
        "Score B": 0,
        "Location": "Test Field",
        "Competition": "Test League"
    }
    
    games_capped = pd.concat([games, pd.DataFrame([capped_game])], ignore_index=True)
    games_capped.to_csv("Matched_Games_capped.csv", index=False)
    
    # Run rankings for both scenarios
    result1 = subprocess.run([
        "python", "rankings/generate_team_rankings_v53_enhanced.py",
        "--in", "Matched_Games_blowout.csv",
        "--out", "Rankings_blowout.csv"
    ], capture_output=True, text=True)
    
    result2 = subprocess.run([
        "python", "rankings/generate_team_rankings_v53_enhanced.py",
        "--in", "Matched_Games_capped.csv",
        "--out", "Rankings_capped.csv"
    ], capture_output=True, text=True)
    
    if result1.returncode != 0 or result2.returncode != 0:
        pytest.fail("Rankings scripts failed")
    
    df_blowout = pd.read_csv("Rankings_blowout.csv")
    df_capped = pd.read_csv("Rankings_capped.csv")
    
    ps_blowout = df_blowout[df_blowout["Team"] == test_team]["PowerScore"].iloc[0]
    ps_capped = df_capped[df_capped["Team"] == test_team]["PowerScore"].iloc[0]
    
    assert abs(ps_blowout - ps_capped) < 0.01, f"GD cap not working: {ps_blowout} vs {ps_capped}"
    
    # Clean up test files
    for file in ["Matched_Games_blowout.csv", "Matched_Games_capped.csv", 
                 "Rankings_blowout.csv", "Rankings_capped.csv"]:
        if os.path.exists(file):
            os.remove(file)
    
    print("✓ Outlier guard blowout test passed")


def test_outlier_guard_zscore():
    """Verify single extreme Adj_GF is clipped to reasonable range."""
    # This test is more complex as it requires injecting extreme values
    # For now, we'll test that the outlier guard function works correctly
    
    from rankings.generate_team_rankings_v53_enhanced import clip_to_zscore
    
    # Create test series with extreme outlier
    normal_values = np.random.normal(2.0, 0.5, 20)
    extreme_values = np.concatenate([normal_values, [20.0]])  # Add extreme outlier
    
    series = pd.Series(extreme_values)
    clipped = clip_to_zscore(series, z=2.5)
    
    # Verify outlier was clipped
    assert clipped.max() < 20.0, "Extreme outlier was not clipped"
    assert clipped.max() < series.max(), "Clipping should reduce maximum value"
    
    print("✓ Outlier guard z-score test passed")


def test_adaptive_k_low_games():
    """Teams with <8 games should have smaller Elo updates."""
    from rankings.generate_team_rankings_v53_enhanced import adaptive_multiplier
    
    # Test adaptive multiplier for low games
    low_games_mult = adaptive_multiplier(
        team_strength=0.7, opp_strength=0.5, games_used=5,
        min_games=8, alpha=0.5, beta=0.6
    )
    
    high_games_mult = adaptive_multiplier(
        team_strength=0.7, opp_strength=0.5, games_used=20,
        min_games=8, alpha=0.5, beta=0.6
    )
    
    assert low_games_mult < high_games_mult, "Low games should have smaller multiplier"
    assert low_games_mult < 1.0, "Low games multiplier should be < 1.0"
    assert high_games_mult <= 1.0, "High games multiplier should be <= 1.0"
    
    print("✓ Adaptive K low games test passed")


def test_adaptive_k_weak_opponent():
    """Much weaker opponent should result in smaller K-factor."""
    from rankings.generate_team_rankings_v53_enhanced import adaptive_multiplier
    
    # Test adaptive multiplier for weak opponent
    weak_opp_mult = adaptive_multiplier(
        team_strength=0.8, opp_strength=0.2, games_used=15,
        min_games=8, alpha=0.5, beta=0.6
    )
    
    strong_opp_mult = adaptive_multiplier(
        team_strength=0.8, opp_strength=0.7, games_used=15,
        min_games=8, alpha=0.5, beta=0.6
    )
    
    assert weak_opp_mult < strong_opp_mult, "Weak opponent should have smaller multiplier"
    assert weak_opp_mult < 1.0, "Weak opponent multiplier should be < 1.0"
    
    print("✓ Adaptive K weak opponent test passed")


def test_connectivity_report():
    """Verify connectivity report is generated correctly."""
    # Run the enhanced rankings script
    result = subprocess.run([
        "python", "rankings/generate_team_rankings_v53_enhanced.py",
        "--in", "Matched_Games.csv",
        "--out", "Rankings_v53_enhanced.csv"
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        pytest.fail(f"Rankings script failed: {result.stderr}")
    
    # Check if connectivity report was generated
    assert os.path.exists("connectivity_report_v53e.csv"), "Connectivity report not generated"
    
    # Load and validate connectivity report
    connectivity_df = pd.read_csv("connectivity_report_v53e.csv")
    
    required_cols = ["Team", "ComponentID", "ComponentSize", "Degree"]
    for col in required_cols:
        assert col in connectivity_df.columns, f"Missing column in connectivity report: {col}"
    
    # Verify data types
    assert pd.api.types.is_integer_dtype(connectivity_df["ComponentID"]), "ComponentID should be integer"
    assert pd.api.types.is_integer_dtype(connectivity_df["ComponentSize"]), "ComponentSize should be integer"
    assert pd.api.types.is_integer_dtype(connectivity_df["Degree"]), "Degree should be integer"
    
    # Verify reasonable values
    assert connectivity_df["ComponentSize"].min() >= 1, "ComponentSize should be >= 1"
    assert connectivity_df["Degree"].min() >= 0, "Degree should be >= 0"
    
    print("✓ Connectivity report test passed")


if __name__ == "__main__":
    # Run all tests
    print("Running V5.3E Enhanced Rankings Correctness Tests")
    print("=" * 60)
    
    try:
        test_schema_validation()
        test_determinism()
        test_monotonicity()
        test_outlier_guard_blowout()
        test_outlier_guard_zscore()
        test_adaptive_k_low_games()
        test_adaptive_k_weak_opponent()
        test_connectivity_report()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
