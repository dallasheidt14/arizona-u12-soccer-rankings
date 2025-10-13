#!/usr/bin/env python3
"""
Test AZ U11 Game History Scraping
==================================

Test the API with just a few teams to see if it's working.
"""

import requests
import pandas as pd
from pathlib import Path
import json

def test_az_u11_scraping():
    """Test scraping with just a few AZ U11 teams."""
    
    print("Testing AZ U11 Game History Scraping")
    print("=" * 40)
    
    # Load AZ teams
    az_teams_file = Path("data/master/U11 BOYS/AZ/AZ_teams.csv")
    if not az_teams_file.exists():
        print(f"[ERROR] AZ teams file not found: {az_teams_file}")
        return False
    
    az_teams = pd.read_csv(az_teams_file)
    print(f"[INFO] Loaded {len(az_teams)} AZ U11 teams")
    
    # Test with just the first 5 teams
    test_teams = az_teams.head(5)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Origin': 'https://rankings.gotsport.com',
        'Referer': 'https://rankings.gotsport.com/'
    }
    
    for idx, team in test_teams.iterrows():
        team_id = team['gotsport_team_id']
        team_name = team['team_name']
        
        print(f"\n[{idx+1}/5] Testing {team_name} (ID: {team_id})")
        
        try:
            url = f"https://system.gotsport.com/api/v1/teams/{team_id}/matches?past=true"
            print(f"  URL: {url}")
            
            response = requests.get(url, headers=headers, timeout=30)
            print(f"  Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"  Response type: {type(data)}")
                
                if isinstance(data, list):
                    print(f"  Found {len(data)} matches (list format)")
                    if len(data) > 0:
                        print(f"  Sample match keys: {list(data[0].keys())}")
                elif isinstance(data, dict):
                    print(f"  Response keys: {list(data.keys())}")
                    if 'matches' in data:
                        matches = data['matches']
                        print(f"  Found {len(matches)} matches (dict format)")
                        if len(matches) > 0:
                            print(f"  Sample match keys: {list(matches[0].keys())}")
                    else:
                        print(f"  No 'matches' key found")
                else:
                    print(f"  Unexpected data format: {data}")
            else:
                print(f"  ERROR: HTTP {response.status_code}")
                print(f"  Response: {response.text[:200]}...")
                
        except Exception as e:
            print(f"  ERROR: {e}")
    
    return True

if __name__ == "__main__":
    test_az_u11_scraping()
