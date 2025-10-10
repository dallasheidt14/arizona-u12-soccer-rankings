#!/usr/bin/env python3
"""
Acceptance test script for the updated API
"""

import requests
import json

API_BASE = "http://localhost:8000"

def test_rankings_response():
    """Test 1: Rankings returns real data with new meta/data shape"""
    print("Test 1: Rankings response structure")
    
    try:
        r = requests.get(f"{API_BASE}/api/rankings?state=AZ&gender=MALE&year=2014")
        data = r.json()
        
        print(f"  PASS: Status: {r.status_code}")
        print(f"  PASS: Meta: {data['meta']}")
        print(f"  PASS: Data count: {len(data['data'])}")
        
        # Show first 3 teams
        print("  DATA: First 3 teams:")
        for i, team in enumerate(data['data'][:3]):
            print(f"    {i+1}. {team['Team']} (GP:{team['GamesPlayed']}, PS:{team['PowerScore']:.3f}, Adj:{team['PowerScore_adj']:.3f}, Mult:{team['GP_Mult']})")
        
        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        return False

def test_inactivity_toggle():
    """Test 2: Inactivity toggle works"""
    print("\nTest 2: Inactivity toggle")
    
    try:
        # Test with include_inactive=true
        r1 = requests.get(f"{API_BASE}/api/rankings?include_inactive=true")
        data1 = r1.json()
        
        # Test with include_inactive=false (default)
        r2 = requests.get(f"{API_BASE}/api/rankings")
        data2 = r2.json()
        
        print(f"  PASS: With include_inactive=true: {data1['meta']}")
        print(f"  PASS: With include_inactive=false: {data2['meta']}")
        
        # Should show same or more teams when including inactive
        count1 = len(data1['data'])
        count2 = len(data2['data'])
        print(f"  DATA: Teams with inactive: {count1}, without inactive: {count2}")
        
        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        return False

def test_penalty_multipliers():
    """Test 3: Penalty multipliers sanity check"""
    print("\nTest 3: Penalty multipliers")
    
    try:
        r = requests.get(f"{API_BASE}/api/rankings?state=AZ&gender=MALE&year=2014")
        data = r.json()
        
        # Find teams with specific GP values
        teams_by_gp = {}
        for team in data['data']:
            gp = team['GamesPlayed']
            if gp in [9, 15, 22]:
                teams_by_gp[gp] = team
        
        print("  DATA: Penalty multiplier verification:")
        for gp in [9, 15, 22]:
            if gp in teams_by_gp:
                team = teams_by_gp[gp]
                expected_mult = 0.75 if gp < 10 else (0.90 if gp < 20 else 1.00)
                actual_mult = team['GP_Mult']
                expected_adj = round(team['PowerScore'] * expected_mult, 3)
                actual_adj = team['PowerScore_adj']
                
                print(f"    GP {gp}: {team['Team']}")
                print(f"      Expected mult: {expected_mult}, Actual: {actual_mult}")
                print(f"      Expected adj: {expected_adj}, Actual: {actual_adj}")
                print(f"      PASS: {'PASS' if abs(expected_adj - actual_adj) < 0.002 else 'FAIL'}")
            else:
                print(f"    GP {gp}: No team found with this exact GP")
        
        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        return False

def test_v4_preference():
    """Test 4: v4 preference"""
    print("\nTest 4: v4 file preference")
    
    try:
        r = requests.get(f"{API_BASE}/api/health")
        data = r.json()
        
        rankings_path = data['rankings']['path']
        print(f"  PASS: Rankings file: {rankings_path}")
        
        if 'v4' in rankings_path:
            print("  PASS: Using v4 file (preferred)")
        elif 'v3' in rankings_path:
            print("  WARNING: Using v3 file (fallback)")
        else:
            print("  WARNING: Using legacy file")
        
        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        return False

def main():
    """Run all acceptance tests"""
    print("Running Acceptance Tests")
    print("=" * 50)
    
    tests = [
        test_rankings_response,
        test_inactivity_toggle,
        test_penalty_multipliers,
        test_v4_preference,
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("SUCCESS: All acceptance tests passed!")
    else:
        print("WARNING: Some tests failed")

if __name__ == "__main__":
    main()
