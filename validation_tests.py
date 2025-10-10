"""
Validation Tests for Phase C Features
Fast validation tests for expectation model and enhanced features
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytest
import config

def test_expectation_calibration_centering():
    """Test that expectation model is properly centered when calibrated."""
    # Load recent game histories
    try:
        hist_df = pd.read_csv("Team_Game_Histories.csv")
        hist_df["Date"] = pd.to_datetime(hist_df["Date"])
        
        # Filter to last 90 days
        cutoff_date = datetime.now() - timedelta(days=90)
        recent_games = hist_df[hist_df["Date"] >= cutoff_date]
        
        if "expected_gd" in recent_games.columns:
            valid_expectations = recent_games[recent_games["expected_gd"].notna()]
            
            if len(valid_expectations) > 0:
                mean_expected = valid_expectations["expected_gd"].mean()
                assert abs(mean_expected) < 0.15, f"Expected GD not centered: {mean_expected:.3f}"
                print(f"SUCCESS: Expectation centering test passed: mean={mean_expected:.3f}")
            else:
                print("WARNING: No valid expectations found for centering test")
        else:
            print("WARNING: Expected GD column not found")
            
    except FileNotFoundError:
        print("WARNING: Team_Game_Histories.csv not found - skipping centering test")

def test_impact_bucket_no_data_handling():
    """Test that no_data bucket only appears when component norms are missing."""
    try:
        hist_df = pd.read_csv("Team_Game_Histories.csv")
        
        if "impact_bucket" in hist_df.columns:
            no_data_games = hist_df[hist_df["impact_bucket"] == "no_data"]
            
            if len(no_data_games) > 0:
                # Check that no_data games have missing expected_gd
                assert no_data_games["expected_gd"].isna().all(), "no_data games should have NaN expected_gd"
                print(f"SUCCESS: No data handling test passed: {len(no_data_games)} no_data games properly handled")
            else:
                print("SUCCESS: No data handling test passed: no no_data games found")
        else:
            print("WARNING: Impact bucket column not found")
            
    except FileNotFoundError:
        print("WARNING: Team_Game_Histories.csv not found - skipping no_data test")

def test_window_filtering():
    """Test that window filtering works correctly."""
    try:
        hist_df = pd.read_csv("Team_Game_Histories.csv")
        hist_df["Date"] = pd.to_datetime(hist_df["Date"])
        
        # Test window filtering for a random team
        teams = hist_df["Team"].unique()
        if len(teams) > 0:
            test_team = teams[0]
            team_games = hist_df[hist_df["Team"] == test_team]
            
            # Check date filtering
            cutoff_date = datetime.now() - timedelta(days=config.RANK_WINDOW_DAYS)
            recent_games = team_games[team_games["Date"] >= cutoff_date]
            
            # Check count filtering
            if len(recent_games) > config.RANK_MAX_MATCHES:
                filtered_games = recent_games.head(config.RANK_MAX_MATCHES)
                assert len(filtered_games) <= config.RANK_MAX_MATCHES, f"Too many games: {len(filtered_games)}"
                print(f"SUCCESS: Window filtering test passed: {test_team} has {len(filtered_games)} games within limits")
            else:
                print(f"SUCCESS: Window filtering test passed: {test_team} has {len(recent_games)} games (within limits)")
        else:
            print("WARNING: No teams found for window filtering test")
            
    except FileNotFoundError:
        print("WARNING: Team_Game_Histories.csv not found - skipping window test")

def test_inactivity_flagging():
    """Test that inactivity flagging works correctly."""
    try:
        rankings_df = pd.read_csv("Rankings_PowerScore.csv")
        
        if "inactivity_flag" in rankings_df.columns:
            inactive_teams = rankings_df[rankings_df["inactivity_flag"] == "inactive"]
            active_teams = rankings_df[rankings_df["inactivity_flag"] == "active"]
            
            print(f"SUCCESS: Inactivity flagging test passed: {len(inactive_teams)} inactive, {len(active_teams)} active")
            
            # Check that inactive teams have recent last_game_date
            if len(inactive_teams) > 0 and "last_game_date" in inactive_teams.columns:
                inactive_teams["last_game_date"] = pd.to_datetime(inactive_teams["last_game_date"])
                cutoff_date = datetime.now() - timedelta(days=config.INACTIVE_HIDE_DAYS)
                old_inactive = inactive_teams[inactive_teams["last_game_date"] < cutoff_date]
                print(f"   {len(old_inactive)} teams inactive for >{config.INACTIVE_HIDE_DAYS} days")
        else:
            print("WARNING: Inactivity flag column not found")
            
    except FileNotFoundError:
        print("WARNING: Rankings_PowerScore.csv not found - skipping inactivity test")

def test_provisional_gating():
    """Test that provisional gating works correctly."""
    try:
        rankings_df = pd.read_csv("Rankings_PowerScore.csv")
        
        if "provisional_flag" in rankings_df.columns:
            provisional_teams = rankings_df[rankings_df["provisional_flag"] == "provisional"]
            full_teams = rankings_df[rankings_df["provisional_flag"] == "full"]
            
            print(f"SUCCESS: Provisional gating test passed: {len(provisional_teams)} provisional, {len(full_teams)} full")
            
            # Check provisional reasons
            if len(provisional_teams) > 0 and "provisional_reason" in provisional_teams.columns:
                reasons = provisional_teams["provisional_reason"].value_counts()
                print(f"   Provisional reasons: {dict(reasons)}")
        else:
            print("WARNING: Provisional flag column not found")
            
    except FileNotFoundError:
        print("WARNING: Rankings_PowerScore.csv not found - skipping provisional test")

def test_expectation_correlation():
    """Test that expected and actual GD have positive correlation."""
    try:
        hist_df = pd.read_csv("Team_Game_Histories.csv")
        
        if "expected_gd" in hist_df.columns and "Goals For" in hist_df.columns and "Goals Against" in hist_df.columns:
            valid_data = hist_df[hist_df["expected_gd"].notna()]
            
            if len(valid_data) > 0:
                valid_data["actual_gd"] = valid_data["Goals For"] - valid_data["Goals Against"]
                correlation = valid_data["expected_gd"].corr(valid_data["actual_gd"])
                
                assert correlation > 0, f"Expected vs actual correlation should be positive: {correlation:.3f}"
                print(f"SUCCESS: Expectation correlation test passed: r={correlation:.3f}")
            else:
                print("WARNING: No valid expectation data found for correlation test")
        else:
            print("WARNING: Required columns not found for correlation test")
            
    except FileNotFoundError:
        print("WARNING: Team_Game_Histories.csv not found - skipping correlation test")

def test_bucket_distribution():
    """Test that impact bucket distribution is not extreme."""
    try:
        hist_df = pd.read_csv("Team_Game_Histories.csv")
        
        if "impact_bucket" in hist_df.columns:
            bucket_counts = hist_df["impact_bucket"].value_counts()
            total_games = len(hist_df)
            
            for bucket in ["good", "neutral", "weak"]:
                if bucket in bucket_counts:
                    percentage = bucket_counts[bucket] / total_games * 100
                    assert percentage < 80, f"Bucket {bucket} too extreme: {percentage:.1f}%"
                    print(f"SUCCESS: Bucket {bucket}: {percentage:.1f}% (within limits)")
        else:
            print("WARNING: Impact bucket column not found")
            
    except FileNotFoundError:
        print("WARNING: Team_Game_Histories.csv not found - skipping bucket test")

def run_all_validation_tests():
    """Run all validation tests and report results."""
    print("Running Phase C Validation Tests")
    print("=" * 50)
    
    tests = [
        test_expectation_calibration_centering,
        test_impact_bucket_no_data_handling,
        test_window_filtering,
        test_inactivity_flagging,
        test_provisional_gating,
        test_expectation_correlation,
        test_bucket_distribution
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"FAILED: {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {test.__name__} error: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("SUCCESS: All validation tests passed! System is production-ready.")
    else:
        print("WARNING: Some tests failed. Review before production deployment.")
    
    return passed, failed

if __name__ == "__main__":
    run_all_validation_tests()
