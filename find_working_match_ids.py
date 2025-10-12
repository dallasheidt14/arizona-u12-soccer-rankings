#!/usr/bin/env python3
"""
Find the correct match IDs for Arizona U11 teams by testing different ID ranges
"""
import requests
import pandas as pd
import time

def test_match_id(team_id):
    """Test if a team ID works with the matches API"""
    url = f"https://system.gotsport.com/api/v1/teams/{team_id}/matches?past=true"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Origin': 'https://rankings.gotsport.com',
        'Referer': 'https://rankings.gotsport.com/'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return True, len(data) if isinstance(data, list) else 0
        else:
            return False, response.status_code
    except Exception as e:
        return False, str(e)

def main():
    # Load Arizona teams
    df = pd.read_csv('data/master/U11 2015 BOYS MASTER TEAM LIST/by_state/AZ_teams.csv')
    
    print("Testing Arizona U11 teams for working match IDs...")
    print("=" * 60)
    
    working_teams = []
    
    # Test first 20 teams
    for i, row in df.head(20).iterrows():
        ranking_id = row['gotsport_team_id']
        team_name = row['display_name']
        
        print(f"Testing {team_name} (Ranking ID: {ranking_id})")
        
        # Test the ranking ID first
        works, result = test_match_id(ranking_id)
        if works:
            print(f"  ✅ Ranking ID {ranking_id} works! Found {result} matches")
            working_teams.append({
                'team_name': team_name,
                'ranking_id': ranking_id,
                'match_id': ranking_id,
                'matches_found': result
            })
        else:
            print(f"  ❌ Ranking ID {ranking_id} failed: {result}")
            
            # Try some variations around the ranking ID
            test_ids = [
                ranking_id - 1000000,  # Try subtracting 1M
                ranking_id - 100000,   # Try subtracting 100K
                ranking_id - 10000,    # Try subtracting 10K
                ranking_id + 1000000,  # Try adding 1M
                ranking_id + 100000,   # Try adding 100K
                ranking_id + 10000,    # Try adding 10K
            ]
            
            for test_id in test_ids:
                works, result = test_match_id(test_id)
                if works:
                    print(f"  ✅ Found working match ID: {test_id} (Found {result} matches)")
                    working_teams.append({
                        'team_name': team_name,
                        'ranking_id': ranking_id,
                        'match_id': test_id,
                        'matches_found': result
                    })
                    break
                else:
                    print(f"  ❌ Test ID {test_id} failed: {result}")
        
        print()
        time.sleep(0.5)  # Be respectful to the server
    
    # Summary
    print("=" * 60)
    print(f"SUMMARY: Found {len(working_teams)} teams with working match IDs")
    
    if working_teams:
        print("\nWorking teams:")
        for team in working_teams:
            print(f"  {team['team_name']}: Ranking ID {team['ranking_id']} -> Match ID {team['match_id']} ({team['matches_found']} matches)")
        
        # Save results
        results_df = pd.DataFrame(working_teams)
        results_df.to_csv('az_u11_working_match_ids.csv', index=False)
        print(f"\nResults saved to: az_u11_working_match_ids.csv")
    else:
        print("No working match IDs found. The ID systems might be completely different.")

if __name__ == "__main__":
    main()

