#!/usr/bin/env python3
"""
Find Arizona U11 teams that have match data by testing the matches API
"""
import pandas as pd
import requests
import time
from pathlib import Path
from datetime import datetime

def test_team_matches(team_id, team_name):
    """Test if a team has match data"""
    
    url = f"https://system.gotsport.com/api/v1/teams/{team_id}/matches"
    params = {"past": "true"}
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Origin': 'https://rankings.gotsport.com',
        'Referer': 'https://rankings.gotsport.com/'
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                return True, len(data)
            elif isinstance(data, dict) and ('matches' in data or 'data' in data):
                matches = data.get('matches', data.get('data', []))
                return True, len(matches)
            else:
                return False, 0
        else:
            return False, 0
            
    except Exception as e:
        return False, 0

def main():
    print("Testing Arizona U11 teams for match data...")
    
    # Load Arizona teams
    az_file = Path("data/master/U11 2015 BOYS MASTER TEAM LIST/by_state/AZ_teams.csv")
    df = pd.read_csv(az_file)
    
    print(f"Loaded {len(df)} Arizona U11 teams")
    
    # Test teams with match data
    teams_with_matches = []
    
    # Test first 20 teams
    test_teams = df.head(20)
    
    for idx, row in test_teams.iterrows():
        team_id = row['gotsport_team_id']
        team_name = row['display_name']
        
        print(f"\n{idx + 1}/20: {team_name} (ID: {team_id})")
        
        has_matches, match_count = test_team_matches(team_id, team_name)
        
        if has_matches:
            print(f"  ✅ Found {match_count} matches!")
            teams_with_matches.append({
                'team_name': team_name,
                'team_id': team_id,
                'match_count': match_count,
                'club': row.get('club', '')
            })
        else:
            print(f"  ❌ No matches found")
        
        time.sleep(0.5)  # Be respectful
    
    # Show results
    print(f"\nRESULTS:")
    print(f"Teams with match data: {len(teams_with_matches)}/{len(test_teams)}")
    
    if teams_with_matches:
        print(f"\nTeams with matches:")
        for team in teams_with_matches:
            print(f"  {team['team_name']} - {team['match_count']} matches")
        
        # Save teams with matches
        matches_df = pd.DataFrame(teams_with_matches)
        output_file = Path("az_u11_teams_with_matches.csv")
        matches_df.to_csv(output_file, index=False)
        print(f"\nSaved teams with matches to: {output_file}")
        
        # Test scraping matches for one team
        if teams_with_matches:
            test_team = teams_with_matches[0]
            print(f"\nTesting match scraping for: {test_team['team_name']}")
            
            url = f"https://system.gotsport.com/api/v1/teams/{test_team['team_id']}/matches"
            params = {"past": "true"}
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
                'Accept': 'application/json',
                'Origin': 'https://rankings.gotsport.com',
                'Referer': 'https://rankings.gotsport.com/'
            }
            
            try:
                response = requests.get(url, params=params, headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    print(f"Sample match data:")
                    if isinstance(data, list) and len(data) > 0:
                        match = data[0]
                        print(f"  Match: {match}")
                    else:
                        print(f"  Data structure: {type(data)}")
                        print(f"  Keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            except Exception as e:
                print(f"Error testing match data: {e}")
    
    else:
        print(f"\nNo teams found with match data")
        print("This suggests:")
        print("1. U11 season hasn't started yet")
        print("2. Teams haven't played any games")
        print("3. Different ID system for matches vs rankings")
    
    print(f"\nTest complete!")

if __name__ == "__main__":
    main()


