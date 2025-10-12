#!/usr/bin/env python3
"""
Test the corrected team_ids with matches API
"""
import requests
import pandas as pd

def test_team_ids():
    """Test if the corrected team_ids work with matches API"""
    df = pd.read_csv('AZ_teams_CORRECTED_20251011_233516.csv')
    
    print("Testing corrected team_ids with matches API...")
    print("=" * 60)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Origin': 'https://rankings.gotsport.com',
        'Referer': 'https://rankings.gotsport.com/'
    }
    
    working_teams = []
    
    for i, row in df.head(5).iterrows():  # Test first 5 teams
        team_id = row['team_id']
        team_name = row['team_name']
        
        url = f"https://system.gotsport.com/api/v1/teams/{team_id}/matches?past=true"
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                match_count = len(data) if isinstance(data, list) else 0
                print(f"SUCCESS: {team_name}")
                print(f"  Team ID: {team_id}")
                print(f"  Matches found: {match_count}")
                working_teams.append({
                    'team_name': team_name,
                    'team_id': team_id,
                    'matches_found': match_count
                })
            else:
                print(f"FAILED: {team_name}")
                print(f"  Team ID: {team_id}")
                print(f"  Status: {response.status_code}")
        except Exception as e:
            print(f"ERROR: {team_name}")
            print(f"  Team ID: {team_id}")
            print(f"  Error: {e}")
        
        print()
    
    print("=" * 60)
    print(f"SUMMARY: {len(working_teams)}/{min(5, len(df))} teams have working match IDs")
    
    if working_teams:
        print("\nWorking teams:")
        for team in working_teams:
            print(f"  {team['team_name']}: {team['matches_found']} matches")
    
    return working_teams

if __name__ == "__main__":
    test_team_ids()

