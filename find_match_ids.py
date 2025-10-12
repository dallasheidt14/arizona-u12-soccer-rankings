#!/usr/bin/env python3
"""
Find the correct match API IDs for Arizona U11 teams
The ranking API uses different IDs than the match API
"""
import pandas as pd
import requests
import time
from pathlib import Path
from datetime import datetime

def search_for_match_id(team_name, ranking_id):
    """Try to find the match API ID for a team"""
    
    # Try different search approaches
    search_urls = [
        f"https://system.gotsport.com/api/v1/teams/{ranking_id}",
        f"https://system.gotsport.com/api/v1/teams/{ranking_id}/profile",
        f"https://system.gotsport.com/api/v1/teams/{ranking_id}/details"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Origin': 'https://rankings.gotsport.com',
        'Referer': 'https://rankings.gotsport.com/'
    }
    
    for url in search_urls:
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"    Found data for {team_name}: {url}")
                print(f"    Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                
                # Look for match_id or similar field
                if isinstance(data, dict):
                    for key, value in data.items():
                        if 'match' in key.lower() or 'id' in key.lower():
                            print(f"    {key}: {value}")
                
                return data
        except Exception as e:
            continue
    
    return None

def main():
    print("Searching for match API IDs for Arizona U11 teams...")
    
    # Load Arizona teams
    az_file = Path("data/master/U11 2015 BOYS MASTER TEAM LIST/by_state/AZ_teams.csv")
    df = pd.read_csv(az_file)
    
    print(f"Loaded {len(df)} Arizona U11 teams")
    
    # Test with first 5 teams
    test_teams = df.head(5)
    
    results = []
    
    for idx, row in test_teams.iterrows():
        team_name = row['display_name']
        ranking_id = row['gotsport_team_id']
        
        print(f"\n{idx + 1}/5: {team_name} (Ranking ID: {ranking_id})")
        
        data = search_for_match_id(team_name, ranking_id)
        
        results.append({
            'team_name': team_name,
            'ranking_id': ranking_id,
            'found_data': data is not None,
            'data': data
        })
        
        time.sleep(1)
    
    # Show results
    print(f"\nResults:")
    for result in results:
        print(f"  {result['team_name']}: {'Found' if result['found_data'] else 'Not found'}")
    
    # Try a different approach - search by team name
    print(f"\nTrying team name search...")
    
    # Test with the working team ID we know (163451)
    test_url = "https://system.gotsport.com/api/v1/teams/163451"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Origin': 'https://rankings.gotsport.com',
        'Referer': 'https://rankings.gotsport.com/'
    }
    
    try:
        response = requests.get(test_url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"Working team (163451) data structure:")
            print(f"  Keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            if isinstance(data, dict):
                for key, value in data.items():
                    print(f"  {key}: {value}")
    except Exception as e:
        print(f"Error testing working team: {e}")
    
    print(f"\nSearch complete!")

if __name__ == "__main__":
    main()


