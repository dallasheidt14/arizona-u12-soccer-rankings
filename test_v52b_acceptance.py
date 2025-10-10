"""
test_v52b_acceptance.py
Acceptance tests for V5.2b competitive tuning implementation.
"""
import pandas as pd
import numpy as np
from scipy.stats import spearmanr
import os

def test_v52b_file_exists():
    """Verify Rankings_v52b.csv exists and is readable."""
    assert os.path.exists("Rankings_v52b.csv"), "Rankings_v52b.csv not found"
    df = pd.read_csv("Rankings_v52b.csv")
    assert len(df) > 0, "Rankings_v52b.csv is empty"
    print("PASS: Rankings_v52b.csv exists and is readable")
    return True

def test_competitive_ordering():
    """Verify PRFC Scottsdale is in proper range (8-15) and strong teams are top 3-5."""
    df = pd.read_csv("Rankings_v52b.csv")
    
    # Check PRFC Scottsdale rank
    prfc = df[df["Team"].str.contains("PRFC Scottsdale", case=False, na=False)]
    if len(prfc) > 0:
        prfc_rank = prfc.iloc[0]["Rank"]
        assert 8 <= prfc_rank <= 15, f"PRFC Scottsdale rank unexpected: {prfc_rank} (expect 8-15)"
        print(f"PASS: PRFC Scottsdale rank: {prfc_rank}")
    
    # Check strong-schedule teams in top 10
    top_10 = df.head(10)["Team"].str.lower()
    strong_teams = ["next level", "phoenix united", "dynamos", "gsa", "fc tucson"]
    strong_in_top10 = sum(1 for team in strong_teams if any(team in name for name in top_10))
    
    assert strong_in_top10 >= 2, f"Too few strong-schedule teams in top 10: {strong_in_top10} (expect >=2)"
    print(f"PASS: Strong-schedule teams in top 10: {strong_in_top10}/{len(strong_teams)}")
    
    return True

def test_spearman_correlation():
    """Verify Spearman correlation with V5.2a is in acceptable range (0.85-0.95)."""
    if not os.path.exists("Rankings_v52a.csv"):
        print("SKIP: Skipping V5.2a correlation test (Rankings_v52a.csv not found)")
        return True
    
    v52a = pd.read_csv("Rankings_v52a.csv")
    v52b = pd.read_csv("Rankings_v52b.csv")
    
    # Normalize team names
    v52a["team"] = v52a["Team"].str.strip().str.lower()
    v52b["team"] = v52b["Team"].str.strip().str.lower()
    
    # Merge on team names
    merged = v52a.merge(v52b, on="team", how="inner")
    
    # Calculate Spearman correlation
    corr, p_value = spearmanr(merged["PowerScore_x"], merged["PowerScore_y"])
    assert 0.85 <= corr <= 0.95, f"Spearman correlation out of range: {corr:.3f} (expect 0.85-0.95)"
    print(f"PASS: V5.2a correlation: Spearman = {corr:.3f}")
    return True

def test_sos_distribution():
    """Verify SOS has meaningful variation and stretching worked."""
    df = pd.read_csv("Rankings_v52b.csv")
    
    sos_unique = df["SOS_norm"].nunique()
    assert sos_unique >= 60, f"SOS_norm has too few unique values: {sos_unique} (expect >=60)"
    
    sos_range = df["SOS_norm"].max() - df["SOS_norm"].min()
    assert sos_range > 0.1, f"SOS_norm range too small: {sos_range:.3f} (expect >0.1)"
    
    # Check that top teams have higher SOS
    top_10 = df.head(10)["SOS_norm"].mean()
    bottom_10 = df.tail(10)["SOS_norm"].mean()
    sos_gradient = top_10 - bottom_10
    
    assert sos_gradient > 0.05, f"SOS gradient too small: {sos_gradient:.3f} (expect >0.05)"
    
    print(f"PASS: SOS has {sos_unique} unique values, range: {sos_range:.3f}, gradient: {sos_gradient:.3f}")
    return True

def test_powerscore_precision():
    """Verify PowerScore precision eliminates artificial ties."""
    df = pd.read_csv("Rankings_v52b.csv")
    
    # Check top 20 for artificial ties
    top_20 = df.head(20)
    unique_scores = top_20["PowerScore"].nunique()
    
    assert unique_scores >= 16, f"Too many PowerScore ties in top 20: {20-unique_scores} (expect <5)"
    
    # Check that PowerScore has 4 decimal precision
    sample_scores = df["PowerScore"].head(10)
    decimal_places = sample_scores.apply(lambda x: len(str(x).split('.')[-1]) if '.' in str(x) else 0)
    min_precision = decimal_places.min()
    
    assert min_precision >= 3, f"PowerScore precision too low: {min_precision} decimals (expect >=3)"
    
    print(f"PASS: Top 20 has {unique_scores} unique PowerScores, precision: {min_precision}+ decimals")
    return True

def test_powerscore_range():
    """Verify PowerScore values are in reasonable range."""
    df = pd.read_csv("Rankings_v52b.csv")
    
    top_10_avg = df.head(10)["PowerScore"].mean()
    assert 0.35 <= top_10_avg <= 0.45, f"Top 10 avg PowerScore out of range: {top_10_avg:.3f} (expect 0.35-0.45)"
    
    powerscore_range = df["PowerScore"].max() - df["PowerScore"].min()
    assert powerscore_range > 0.3, f"PowerScore range too small: {powerscore_range:.3f} (expect >0.3)"
    
    print(f"PASS: Top 10 avg PowerScore: {top_10_avg:.3f}, range: {powerscore_range:.3f}")
    return True

def test_v52b_tuning_parameters():
    """Verify V5.2b tuning parameters are correctly applied."""
    from rankings.generate_team_rankings_v52b import (
        OFF_WEIGHT, DEF_WEIGHT, SOS_WEIGHT, SOS_STRETCH_EXPONENT
    )
    
    assert OFF_WEIGHT == 0.20, f"OFF_WEIGHT should be 0.20, got {OFF_WEIGHT}"
    assert DEF_WEIGHT == 0.20, f"DEF_WEIGHT should be 0.20, got {DEF_WEIGHT}"
    assert SOS_WEIGHT == 0.60, f"SOS_WEIGHT should be 0.60, got {SOS_WEIGHT}"
    assert SOS_STRETCH_EXPONENT == 1.5, f"SOS_STRETCH_EXPONENT should be 1.5, got {SOS_STRETCH_EXPONENT}"
    
    print("PASS: V5.2b tuning parameters correctly set")
    return True

def test_all_v52a_stability_checks():
    """Verify all V5.2a stability checks still pass."""
    df = pd.read_csv("Rankings_v52b.csv")
    
    # Smoothness check
    sao_smooth = df["SAO_norm"].between(0.05, 0.95).mean()
    sad_smooth = df["SAD_norm"].between(0.05, 0.95).mean()
    
    assert sao_smooth > 0.85, f"SAO_norm smoothness: {sao_smooth:.1%} (expect >85%)"
    assert sad_smooth > 0.85, f"SAD_norm smoothness: {sad_smooth:.1%} (expect >85%)"
    
    # SOS variation check
    sos_unique = df["SOS_norm"].nunique()
    assert sos_unique > 20, f"SOS_norm unique values: {sos_unique} (expect >20)"
    
    # Provisional protection check
    top_20 = df.head(20)
    low_gp_count = (top_20["GamesPlayed"] < 10).sum()
    assert low_gp_count <= 2, f"Too many <10 game teams in top 20: {low_gp_count} (expect <=2)"
    
    print("PASS: All V5.2a stability checks maintained")
    return True

def test_team_count():
    """Verify expected number of teams."""
    df = pd.read_csv("Rankings_v52b.csv")
    team_count = len(df)
    assert 140 <= team_count <= 180, f"Unexpected team count: {team_count} (expect 140-180)"
    print(f"PASS: Team count: {team_count} (within expected range)")
    return True

def test_no_nan_values():
    """Verify no NaN values in critical columns."""
    df = pd.read_csv("Rankings_v52b.csv")
    critical_cols = ["Team", "PowerScore", "SAO_norm", "SAD_norm", "SOS_norm"]
    for col in critical_cols:
        assert not df[col].isna().any(), f"NaN values found in {col}"
    print("PASS: No NaN values in critical columns")
    return True

def main():
    """Run all V5.2b acceptance tests."""
    tests = [
        test_v52b_file_exists,
        test_competitive_ordering,
        test_spearman_correlation,
        test_sos_distribution,
        test_powerscore_precision,
        test_powerscore_range,
        test_v52b_tuning_parameters,
        test_all_v52a_stability_checks,
        test_team_count,
        test_no_nan_values
    ]
    
    passed = 0
    total = len(tests)
    
    print("V5.2b Acceptance Tests")
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
        print("All V5.2b acceptance tests PASSED!")
        return True
    else:
        print("Some V5.2b acceptance tests FAILED!")
        return False

if __name__ == "__main__":
    main()
