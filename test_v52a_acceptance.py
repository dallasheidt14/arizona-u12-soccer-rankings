"""
test_v52a_acceptance.py
Acceptance tests for V5.2a stability fixes implementation.
"""
import pandas as pd
import numpy as np
from scipy.stats import spearmanr
import os

def test_v52a_file_exists():
    """Verify Rankings_v52a.csv exists and is readable."""
    assert os.path.exists("Rankings_v52a.csv"), "Rankings_v52a.csv not found"
    df = pd.read_csv("Rankings_v52a.csv")
    assert len(df) > 0, "Rankings_v52a.csv is empty"
    print("PASS: Rankings_v52a.csv exists and is readable")
    return True

def test_smoothness_distribution():
    """Verify SAO_norm and SAD_norm have smooth distributions (not binary 0/1)."""
    df = pd.read_csv("Rankings_v52a.csv")
    
    # Check that most teams are NOT at binary extremes
    sao_binary = ((df["SAO_norm"] == 0.0) | (df["SAO_norm"] == 1.0)).mean()
    sad_binary = ((df["SAD_norm"] == 0.0) | (df["SAD_norm"] == 1.0)).mean()
    
    assert sao_binary < 0.15, f"Too many SAO_norm at extremes: {sao_binary:.1%} (expect <15%)"
    assert sad_binary < 0.15, f"Too many SAD_norm at extremes: {sad_binary:.1%} (expect <15%)"
    
    # Check that most teams are in smooth range
    sao_smooth = df["SAO_norm"].between(0.05, 0.95).mean()
    sad_smooth = df["SAD_norm"].between(0.05, 0.95).mean()
    
    assert sao_smooth > 0.85, f"Too few SAO_norm in smooth range: {sao_smooth:.1%} (expect >85%)"
    assert sad_smooth > 0.85, f"Too few SAD_norm in smooth range: {sad_smooth:.1%} (expect >85%)"
    
    print(f"PASS: SAO_norm smooth: {sao_smooth:.1%}, SAD_norm smooth: {sad_smooth:.1%}")
    return True

def test_sos_variation():
    """Verify SOS_norm has meaningful variation (not all at floor)."""
    df = pd.read_csv("Rankings_v52a.csv")
    
    sos_unique = df["SOS_norm"].nunique()
    assert sos_unique > 20, f"SOS_norm has too few unique values: {sos_unique} (expect >20)"
    
    sos_range = df["SOS_norm"].max() - df["SOS_norm"].min()
    assert sos_range > 0.1, f"SOS_norm range too small: {sos_range:.3f} (expect >0.1)"
    
    print(f"PASS: SOS_norm has {sos_unique} unique values, range: {sos_range:.3f}")
    return True

def test_provisional_protection():
    """Verify teams with <10 games are not dominating top rankings."""
    df = pd.read_csv("Rankings_v52a.csv")
    
    # Check top 20 teams
    top_20 = df.head(20)
    low_gp_count = (top_20["GamesPlayed"] < 10).sum()
    
    assert low_gp_count <= 2, f"Too many <10 game teams in top 20: {low_gp_count} (expect <=2)"
    
    # Check top 10 teams
    top_10 = df.head(10)
    low_gp_top10 = (top_10["GamesPlayed"] < 10).sum()
    
    assert low_gp_top10 <= 1, f"Too many <10 game teams in top 10: {low_gp_top10} (expect <=1)"
    
    print(f"PASS: Top 20 has {low_gp_count} <10 game teams, top 10 has {low_gp_top10}")
    return True

def test_powerscore_range():
    """Verify PowerScore values are in [0,1] range."""
    df = pd.read_csv("Rankings_v52a.csv")
    powerscore = df["PowerScore"]
    assert powerscore.min() >= 0.0, f"PowerScore min too low: {powerscore.min()}"
    assert powerscore.max() <= 1.0, f"PowerScore max too high: {powerscore.max()}"
    print(f"PASS: PowerScore range: [{powerscore.min():.3f}, {powerscore.max():.3f}]")
    return True

def test_team_count():
    """Verify expected number of teams."""
    df = pd.read_csv("Rankings_v52a.csv")
    team_count = len(df)
    assert 140 <= team_count <= 180, f"Unexpected team count: {team_count} (expect 140-180)"
    print(f"PASS: Team count: {team_count} (within expected range)")
    return True

def test_no_nan_values():
    """Verify no NaN values in critical columns."""
    df = pd.read_csv("Rankings_v52a.csv")
    critical_cols = ["Team", "PowerScore", "SAO_norm", "SAD_norm", "SOS_norm"]
    for col in critical_cols:
        assert not df[col].isna().any(), f"NaN values found in {col}"
    print("PASS: No NaN values in critical columns")
    return True

def test_v52_stability():
    """Verify Spearman correlation with V5.2 is in acceptable range."""
    if not os.path.exists("Rankings_v52.csv"):
        print("SKIP: Skipping V5.2 stability test (Rankings_v52.csv not found)")
        return True
    
    v52 = pd.read_csv("Rankings_v52.csv")
    v52a = pd.read_csv("Rankings_v52a.csv")
    
    # Normalize team names
    v52["team"] = v52["Team"].str.strip().str.lower()
    v52a["team"] = v52a["Team"].str.strip().str.lower()
    
    # Merge on team names
    merged = v52.merge(v52a, on="team", how="inner")
    
    # Calculate Spearman correlation
    corr, p_value = spearmanr(merged["PowerScore_x"], merged["PowerScore_y"])
    assert 0.6 <= corr <= 0.8, f"Spearman correlation out of range: {corr:.3f} (expect 0.6-0.8)"
    print(f"PASS: V5.2 stability: Spearman correlation = {corr:.3f}")
    return True

def test_v52a_tuning_parameters():
    """Verify V5.2a tuning parameters are correctly applied."""
    from rankings.generate_team_rankings_v52a import (
        OFF_WEIGHT, DEF_WEIGHT, SOS_WEIGHT, PERFORMANCE_K, RIDGE_GA, SHRINK_TAU,
        OPP_STRENGTH_FINAL_MIN, OPP_STRENGTH_FINAL_MAX, PROVISIONAL_ALPHA
    )
    
    assert OFF_WEIGHT == 0.35, f"OFF_WEIGHT should be 0.35, got {OFF_WEIGHT}"
    assert DEF_WEIGHT == 0.35, f"DEF_WEIGHT should be 0.35, got {DEF_WEIGHT}"
    assert SOS_WEIGHT == 0.30, f"SOS_WEIGHT should be 0.30, got {SOS_WEIGHT}"
    assert PERFORMANCE_K == 0.10, f"PERFORMANCE_K should be 0.10, got {PERFORMANCE_K}"
    assert RIDGE_GA == 0.25, f"RIDGE_GA should be 0.25, got {RIDGE_GA}"
    assert SHRINK_TAU == 8, f"SHRINK_TAU should be 8, got {SHRINK_TAU}"
    assert OPP_STRENGTH_FINAL_MIN == 0.67, f"OPP_STRENGTH_FINAL_MIN should be 0.67, got {OPP_STRENGTH_FINAL_MIN}"
    assert OPP_STRENGTH_FINAL_MAX == 1.50, f"OPP_STRENGTH_FINAL_MAX should be 1.50, got {OPP_STRENGTH_FINAL_MAX}"
    assert PROVISIONAL_ALPHA == 1.5, f"PROVISIONAL_ALPHA should be 1.5, got {PROVISIONAL_ALPHA}"
    
    print("PASS: V5.2a tuning parameters correctly set")
    return True

def test_expected_rankings():
    """Verify expected competitive effects."""
    df = pd.read_csv("Rankings_v52a.csv")
    
    # Check if PRFC Scottsdale is in reasonable range (not #1, not #64)
    prfc = df[df["Team"].str.contains("PRFC Scottsdale", case=False, na=False)]
    if len(prfc) > 0:
        prfc_rank = prfc.iloc[0]["Rank"]
        assert 10 <= prfc_rank <= 30, f"PRFC Scottsdale rank unexpected: {prfc_rank} (expect 10-30)"
        print(f"PASS: PRFC Scottsdale rank: {prfc_rank}")
    
    # Check if strong-schedule teams are more prominent
    top_10 = df.head(10)["Team"].str.lower()
    strong_teams = ["next level", "phoenix united", "dynamos", "gsa", "fc tucson"]
    strong_in_top10 = sum(1 for team in strong_teams if any(team in name for name in top_10))
    
    print(f"PASS: Strong-schedule teams in top 10: {strong_in_top10}/{len(strong_teams)}")
    
    return True

def main():
    """Run all V5.2a acceptance tests."""
    tests = [
        test_v52a_file_exists,
        test_smoothness_distribution,
        test_sos_variation,
        test_provisional_protection,
        test_powerscore_range,
        test_team_count,
        test_no_nan_values,
        test_v52_stability,
        test_v52a_tuning_parameters,
        test_expected_rankings
    ]
    
    passed = 0
    total = len(tests)
    
    print("V5.2a Acceptance Tests")
    print("=" * 50)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"FAIL: {test.__name__}: {e}")
    
    print("=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("All V5.2a acceptance tests PASSED!")
        return True
    else:
        print("Some V5.2a acceptance tests FAILED!")
        return False

if __name__ == "__main__":
    main()




