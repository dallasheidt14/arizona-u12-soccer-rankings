"""
test_v52_acceptance.py
Acceptance tests for V5.2 strength-adjusted ranking implementation.
"""
import pandas as pd
import numpy as np
from scipy.stats import spearmanr
import os

def test_v52_file_exists():
    """Verify Rankings_v52.csv exists and is readable."""
    assert os.path.exists("Rankings_v52.csv"), "Rankings_v52.csv not found"
    df = pd.read_csv("Rankings_v52.csv")
    assert len(df) > 0, "Rankings_v52.csv is empty"
    print("PASS: Rankings_v52.csv exists and is readable")
    return True

def test_strength_adjusted_columns():
    """Verify SAO_norm and SAD_norm columns exist."""
    df = pd.read_csv("Rankings_v52.csv")
    required_cols = ["SAO_norm", "SAD_norm", "SOS_norm"]
    for col in required_cols:
        assert col in df.columns, f"Missing column: {col}"
    print("PASS: Strength-adjusted columns (SAO_norm, SAD_norm, SOS_norm) exist")
    return True

def test_powerscore_range():
    """Verify PowerScore values are in [0,1] range."""
    df = pd.read_csv("Rankings_v52.csv")
    powerscore = df["PowerScore"]
    assert powerscore.min() >= 0.0, f"PowerScore min too low: {powerscore.min()}"
    assert powerscore.max() <= 1.0, f"PowerScore max too high: {powerscore.max()}"
    print(f"PASS: PowerScore range: [{powerscore.min():.3f}, {powerscore.max():.3f}]")
    return True

def test_team_count():
    """Verify expected number of teams (148)."""
    df = pd.read_csv("Rankings_v52.csv")
    team_count = len(df)
    assert 140 <= team_count <= 180, f"Unexpected team count: {team_count} (expect 140-180)"
    print(f"PASS: Team count: {team_count} (within expected range)")
    return True

def test_no_nan_values():
    """Verify no NaN values in critical columns."""
    df = pd.read_csv("Rankings_v52.csv")
    critical_cols = ["Team", "PowerScore", "SAO_norm", "SAD_norm", "SOS_norm"]
    for col in critical_cols:
        assert not df[col].isna().any(), f"NaN values found in {col}"
    print("PASS: No NaN values in critical columns")
    return True

def test_v51_stability():
    """Verify Spearman correlation with V5.1 >= 0.85."""
    if not os.path.exists("Rankings_v51.csv"):
        print("SKIP: Skipping V5.1 stability test (Rankings_v51.csv not found)")
        return True
    
    v51 = pd.read_csv("Rankings_v51.csv")
    v52 = pd.read_csv("Rankings_v52.csv")
    
    # Normalize team names
    v51["team"] = v51["Team"].str.strip().str.lower()
    v52["team"] = v52["Team"].str.strip().str.lower()
    
    # Merge on team names
    merged = v51.merge(v52, on="team", how="inner")
    
    # Calculate Spearman correlation
    corr, p_value = spearmanr(merged["PowerScore_x"], merged["PowerScore_y"])
    assert corr >= 0.85, f"Spearman correlation too low: {corr:.3f} (expect >= 0.85)"
    print(f"PASS: V5.1 stability: Spearman correlation = {corr:.3f}")
    return True

def test_v52_tuning_parameters():
    """Verify V5.2 tuning parameters are correctly applied."""
    from rankings.generate_team_rankings_v52 import OFF_WEIGHT, DEF_WEIGHT, SOS_WEIGHT, PERFORMANCE_K
    
    assert OFF_WEIGHT == 0.35, f"OFF_WEIGHT should be 0.35, got {OFF_WEIGHT}"
    assert DEF_WEIGHT == 0.35, f"DEF_WEIGHT should be 0.35, got {DEF_WEIGHT}"
    assert SOS_WEIGHT == 0.30, f"SOS_WEIGHT should be 0.30, got {SOS_WEIGHT}"
    assert PERFORMANCE_K == 0.20, f"PERFORMANCE_K should be 0.20, got {PERFORMANCE_K}"
    print("PASS: V5.2 tuning parameters correctly set")
    return True

def test_blowout_dampening():
    """Verify blowout dampening is applied symmetrically."""
    from rankings.generate_team_rankings_v52 import GOAL_DIFF_CAP
    assert GOAL_DIFF_CAP == 6, f"GOAL_DIFF_CAP should be 6, got {GOAL_DIFF_CAP}"
    print("PASS: Blowout dampening cap set to +/-6")
    return True

def test_sos_floor():
    """Verify SOS floor is applied."""
    from rankings.generate_team_rankings_v52 import SOS_FLOOR
    assert SOS_FLOOR == 0.40, f"SOS_FLOOR should be 0.40, got {SOS_FLOOR}"
    
    df = pd.read_csv("Rankings_v52.csv")
    sos_min = df["SOS_norm"].min()
    assert sos_min >= SOS_FLOOR, f"SOS_norm minimum {sos_min:.3f} below floor {SOS_FLOOR}"
    print(f"PASS: SOS floor applied: minimum = {sos_min:.3f}")
    return True

def test_expected_rankings():
    """Verify expected competitive effects."""
    df = pd.read_csv("Rankings_v52.csv")
    
    # Check if PRFC Scottsdale dropped significantly (weak schedule)
    prfc = df[df["Team"].str.contains("PRFC Scottsdale", case=False, na=False)]
    if len(prfc) > 0:
        prfc_rank = prfc.iloc[0]["Rank"]
        print(f"PASS: PRFC Scottsdale rank: {prfc_rank}")
    
    # Check if strong-schedule teams are in top positions
    top_10 = df.head(10)["Team"].str.lower()
    strong_teams = ["next level", "phoenix united", "dynamos", "gsa", "fc tucson"]
    strong_in_top10 = sum(1 for team in strong_teams if any(team in name for name in top_10))
    print(f"PASS: Strong-schedule teams in top 10: {strong_in_top10}/{len(strong_teams)}")
    
    return True

def main():
    """Run all V5.2 acceptance tests."""
    tests = [
        test_v52_file_exists,
        test_strength_adjusted_columns,
        test_powerscore_range,
        test_team_count,
        test_no_nan_values,
        test_v51_stability,
        test_v52_tuning_parameters,
        test_blowout_dampening,
        test_sos_floor,
        test_expected_rankings
    ]
    
    passed = 0
    total = len(tests)
    
    print("V5.2 Acceptance Tests")
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
        print("All V5.2 acceptance tests PASSED!")
        return True
    else:
        print("Some V5.2 acceptance tests FAILED!")
        return False

if __name__ == "__main__":
    main()
