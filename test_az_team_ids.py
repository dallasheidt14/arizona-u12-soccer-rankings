#!/usr/bin/env python3
"""
Test Arizona U11 team IDs to see if they work with the matches API
"""
import requests
import pandas as pd

def test_team_id(team_id, team_name):
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
        return response.status_code, response.text[:100]
    except Exception as e:
        return f"Error: {e}", ""

def main():
    # Load Arizona teams
    df = pd.read_csv('data/master/U11 2015 BOYS MASTER TEAM LIST/by_state/AZ_teams.csv')
    
    print("Testing first 10 Arizona U11 team IDs:")
    print("=" * 60)
    
    for i, row in df.head(10).iterrows():
        team_id = row['gotsport_team_id']
        team_name = row['display_name']
        
        status, response = test_team_id(team_id, team_name)
        print(f"ID {team_id}: {team_name}")
        print(f"  Status: {status}")
        if status != 200:
            print(f"  Response: {response}")
        print()

if __name__ == "__main__":
    main()


