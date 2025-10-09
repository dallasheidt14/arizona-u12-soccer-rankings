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

if __name__ == "__main__":
    sys.exit(main())
