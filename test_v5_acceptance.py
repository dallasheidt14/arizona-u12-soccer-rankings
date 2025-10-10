#!/usr/bin/env python3
"""
Acceptance tests for the v5 tapered recency window implementation
"""

import requests
import pandas as pd
import sys

API_BASE = "http://localhost:8000"

def test_v5_file_exists():
    """Test that Rankings_v5.csv was generated"""
    print("Testing v5 file exists...")
    try:
        df = pd.read_csv("Rankings_v5.csv")
        print(f"  PASS: Rankings_v5.csv exists with {len(df)} teams")
        
        # Check required columns
        required_cols = ["Rank", "Team", "PowerScore_adj", "PowerScore", "GP_Mult", "GamesPlayed", "Status", "LastGame"]
        for col in required_cols:
            assert col in df.columns, f"Missing column: {col}"
        
        print(f"  PASS: All required columns present")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False

def test_api_uses_v5():
    """Test that API prefers v5 file"""
    print("\nTesting API uses v5 file...")
    try:
        r = requests.get(f"{API_BASE}/api/health")
        health = r.json()
        
        rankings_path = health['rankings']['path']
        print(f"  Rankings file: {rankings_path}")
        
        if 'v5' in rankings_path:
            print("  PASS: API is using v5 file")
            return True
        else:
            print("  WARNING: API is not using v5 file")
            return False
    except Exception as e:
        print(f"  FAIL: {e}")
        return False

def test_meta_has_method():
    """Test that API meta includes method legend"""
    print("\nTesting API meta has method legend...")
    try:
        r = requests.get(f"{API_BASE}/api/rankings?state=AZ&gender=MALE&year=2014&limit=3")
        data = r.json()
        
        meta = data.get('meta', {})
        method = meta.get('method', '')
        
        print(f"  Method: {method}")
        
        if '30' in method and 'reduced influence' in method.lower():
            print("  PASS: Method legend describes v5 algorithm")
            return True
        else:
            print("  WARNING: Method legend missing or incomplete")
            return False
    except Exception as e:
        print(f"  FAIL: {e}")
        return False

def test_high_volume_teams():
    """Test that teams with 25-30 games get appropriate treatment"""
    print("\nTesting high-volume teams...")
    try:
        df = pd.read_csv("Rankings_v5.csv")
        
        # Find teams with 25-30 games
        high_volume = df[(df['GamesPlayed'] >= 25) & (df['GamesPlayed'] <= 30)]
        
        if len(high_volume) > 0:
            print(f"  Found {len(high_volume)} teams with 25-30 games")
            
            # Check that they have GP_Mult = 1.0
            for _, team in high_volume.head(3).iterrows():
                assert team['GP_Mult'] == 1.0, f"{team['Team']} should have GP_Mult=1.0"
                print(f"    {team['Team']}: GP={team['GamesPlayed']}, Mult={team['GP_Mult']}, PS_adj={team['PowerScore_adj']:.3f}")
            
            print("  PASS: High-volume teams processed correctly")
            return True
        else:
            print("  INFO: No teams with 25-30 games in dataset")
            return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False

def test_tapered_weights_applied():
    """Verify tapered weights are being used (spot check)"""
    print("\nTesting tapered weights application...")
    try:
        from rankings.generate_team_rankings_v5 import tapered_weights
        import numpy as np
        
        # Test n=30 case
        w = tapered_weights(30, recent_k=10, recent_share=0.70, full_weight_games=25, enabled=True)
        
        # Verify properties
        assert len(w) == 30, f"Expected length 30, got {len(w)}"
        assert abs(w.sum() - 1.0) < 1e-10, f"Weights should sum to 1.0, got {w.sum()}"
        
        # Verify taper is applied (games 26-30 should be decreasing)
        tapered_section = w[25:30]
        for i in range(1, len(tapered_section)):
            assert tapered_section[i] < tapered_section[i-1], "Tapered weights should be decreasing"
        
        # Verify tapered influence is reasonable (10-20%)
        total_tapered = tapered_section.sum()
        assert 0.10 < total_tapered < 0.25, f"Tapered influence should be 10-25%, got {total_tapered:.3f}"
        
        print(f"  PASS: Tapered weights working correctly")
        print(f"    Tapered influence (games 26-30): {total_tapered:.3f}")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False

def test_filtered_data_usage():
    """Test that Off_raw/Def_raw and GamesPlayed use filtered data only."""
    print("\nTesting filtered data usage...")
    
    # Load the corrected Rankings_v5.csv
    df = pd.read_csv("Rankings_v5.csv")
    
    # Test 1: GamesPlayed should be ≤ 30 (filtered count)
    max_games_played = df["GamesPlayed"].max()
    assert max_games_played <= 30, f"GamesPlayed max is {max_games_played}, should be ≤ 30"
    print(f"  PASS: GamesPlayed max: {max_games_played} (<= 30)")
    
    # Test 2: GamesTotal should be ≥ GamesPlayed (all-time ≥ filtered)
    invalid_pairs = df[df["GamesTotal"] < df["GamesPlayed"]]
    assert len(invalid_pairs) == 0, f"Found {len(invalid_pairs)} teams where GamesTotal < GamesPlayed"
    print(f"  PASS: All teams have GamesTotal >= GamesPlayed")
    
    # Test 3: GP_Mult should be based on GamesPlayed (filtered count)
    teams_with_1_game = df[df["GamesPlayed"] == 1]
    assert all(teams_with_1_game["GP_Mult"] == 0.75), "Teams with 1 game should have GP_Mult = 0.75"
    print(f"  PASS: GP_Mult correctly applied to filtered GamesPlayed count")
    
    # Test 4: Teams with 27+ games should have GP_Mult = 1.0
    teams_with_27_plus = df[df["GamesPlayed"] >= 27]
    assert all(teams_with_27_plus["GP_Mult"] == 1.0), "Teams with 27+ games should have GP_Mult = 1.0"
    print(f"  PASS: Teams with 27+ games have GP_Mult = 1.0")
    
    print("  PASS: All filtered data usage tests passed!")
    return True

def test_sanity_metrics():
    """Test expected metrics after V5 spec alignment."""
    print("\nTesting sanity metrics...")
    
    # Load the corrected Rankings_v5.csv
    df = pd.read_csv("Rankings_v5.csv")
    
    # Test 1: Team count should be 140-180 (AZ U12 only)
    team_count = len(df)
    assert 140 <= team_count <= 180, f"Expected 140-180 AZ U12 teams, got {team_count}"
    print(f"  PASS: {team_count} AZ U12 teams ranked (expected 140-180)")
    
    # Test 2: GamesPlayed should be capped at 30
    max_games = df["GamesPlayed"].max()
    assert max_games <= 30, f"Max GamesPlayed is {max_games}, should be <= 30"
    print(f"  PASS: Max GamesPlayed: {max_games} (<= 30)")
    
    # Test 3: Average games per team should increase to 20-30 (more games per team after filtering)
    avg_games = df["GamesPlayed"].mean()
    assert 20 <= avg_games <= 30, f"Avg games per team is {avg_games:.1f}, expected 20-30"
    print(f"  PASS: Avg games per team: {avg_games:.1f} (expected 20-30)")
    
    # Test 4: Total games counted should be reasonable (filtered to 30 per team)
    total_games = df["GamesPlayed"].sum()
    assert total_games >= 3000, f"Total games is {total_games}, expected at least 3,000"
    print(f"  PASS: Total games counted: {total_games} (filtered to 30 per team)")
    
    # Test 5: Inactive teams should be filtered out
    active_teams = df[df["is_active"] == True]
    inactive_teams = df[df["is_active"] == False]
    assert len(inactive_teams) == 0, f"Found {len(inactive_teams)} inactive teams in rankings"
    print(f"  PASS: {len(active_teams)} active teams, {len(inactive_teams)} inactive teams")
    
    # Test 6: GamesTotal should be >= GamesPlayed for all teams
    invalid_pairs = df[df["GamesTotal"] < df["GamesPlayed"]]
    assert len(invalid_pairs) == 0, f"Found {len(invalid_pairs)} teams where GamesTotal < GamesPlayed"
    print(f"  PASS: All teams have GamesTotal >= GamesPlayed")
    
    print("  PASS: All sanity metrics tests passed!")
    return True

def test_master_team_filtering():
    """Test that only authorized AZ U12 teams appear in rankings."""
    print("\nTesting master team filtering...")
    
    master_teams = pd.read_csv("AZ MALE U12 MASTER TEAM LIST.csv")
    master_set = set(master_teams["Team Name"].str.strip())
    
    rankings = pd.read_csv("Rankings_v5.csv")
    ranked_set = set(rankings["Team"].str.strip())
    
    # Check all ranked teams are in master list
    invalid = ranked_set - master_set
    assert len(invalid) == 0, f"Non-master teams in rankings: {invalid}"
    
    # Check team count in expected range
    assert 140 <= len(rankings) <= 180, f"Expected 140-180 teams, got {len(rankings)}"
    
    print(f"  PASS: All {len(rankings)} teams are authorized AZ U12 teams")
    print(f"  PASS: Team count {len(rankings)} is within expected range (140-180)")
    return True

def main():
    """Run all v5 acceptance tests"""
    print("Running v5 Acceptance Tests")
    print("=" * 50)
    
    tests = [
        test_v5_file_exists,
        test_api_uses_v5,
        test_meta_has_method,
        test_high_volume_teams,
        test_tapered_weights_applied,
        test_filtered_data_usage,
        test_sanity_metrics,
        test_master_team_filtering,
        test_v51_tuning_parameters,
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("SUCCESS: v5 implementation is production-ready!")
        return 0
    else:
        print("WARNING: Some tests failed - review before deployment")
        return 1

def test_v51_tuning_parameters():
    """Verify V5.1 tuning parameters are correctly applied."""
    print("\nTesting V5.1 tuning parameters...")
    
    # Import the V5.1 constants
    import sys
    sys.path.insert(0, 'rankings')
    from generate_team_rankings_v51 import OFF_WEIGHT, DEF_WEIGHT, SOS_WEIGHT, SOS_FLOOR, GOAL_DIFF_CAP
    
    # Verify weights
    assert OFF_WEIGHT == 0.35, f"OFF_WEIGHT should be 0.35, got {OFF_WEIGHT}"
    assert DEF_WEIGHT == 0.35, f"DEF_WEIGHT should be 0.35, got {DEF_WEIGHT}"
    assert SOS_WEIGHT == 0.30, f"SOS_WEIGHT should be 0.30, got {SOS_WEIGHT}"
    assert OFF_WEIGHT + DEF_WEIGHT + SOS_WEIGHT == 1.0, "Weights must sum to 1.0"
    
    # Verify floor
    assert SOS_FLOOR == 0.40, f"SOS_FLOOR should be 0.40, got {SOS_FLOOR}"
    
    # Verify cap
    assert GOAL_DIFF_CAP == 6, f"GOAL_DIFF_CAP should be 6, got {GOAL_DIFF_CAP}"
    
    print("  PASS: V5.1 tuning parameters correctly configured")
    print(f"    - Weights: Off={OFF_WEIGHT}, Def={DEF_WEIGHT}, SOS={SOS_WEIGHT}")
    print(f"    - SOS Floor: {SOS_FLOOR}")
    print(f"    - Goal Diff Cap: ±{GOAL_DIFF_CAP}")
    return True

if __name__ == "__main__":
    sys.exit(main())
