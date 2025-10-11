#!/usr/bin/env python3
"""
Scrape Arizona U11 master team list from GotSport using the correct API endpoint.

Based on network analysis showing POST requests to it.lngtd.com
"""

import requests
import pandas as pd
import time
from pathlib import Path
import json

def scrape_arizona_u11_teams():
    """Scrape Arizona U11 teams using the correct GotSport API."""
    
    # The actual API endpoint based on network analysis
    url = "https://it.lngtd.com/"
    
    headers = {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'en-US,en;q=0.9',
        'Content-Type': 'application/json;charset=UTF-8',
        'Origin': 'https://rankings.gotsport.com',
        'Referer': 'https://rankings.gotsport.com/',
        'Sec-Ch-Ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'cross-site',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36'
    }
    
    # Try different payload structures based on typical GotSport API patterns
    payloads_to_try = [
        {
            "search": {
                "team_country": "USA",
                "age": "11",
                "gender": "m",
                "state": "AZ"
            }
        },
        {
            "filters": {
                "country": "USA",
                "age_group": "11",
                "gender": "m",
                "state": "AZ"
            }
        },
        {
            "query": {
                "team_country": "USA",
                "age": "11",
                "gender": "m",
                "state": "AZ"
            }
        }
    ]
    
    all_teams = []
    
    for i, payload in enumerate(payloads_to_try):
        print(f"Trying payload structure {i+1}...")
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            print(f"Status: {response.status_code}")
            print(f"Response length: {len(response.text)}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"JSON response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                    
                    # Look for team data in various possible structures
                    teams = None
                    if isinstance(data, dict):
                        for key in ['teams', 'data', 'results', 'team_ranking_data']:
                            if key in data:
                                teams = data[key]
                                break
                    
                    if teams and isinstance(teams, list):
                        print(f"Found {len(teams)} teams!")
                        for team in teams:
                            if isinstance(team, dict):
                                team_id = team.get('id') or team.get('team_id')
                                team_name = team.get('name') or team.get('team_name')
                                club = team.get('club') or team.get('club_name')
                                
                                if team_id and team_name:
                                    all_teams.append({
                                        'gotsport_team_id': team_id,
                                        'display_name': team_name,
                                        'club': club or '',
                                        'team_id': f"az_u11_{team_id}"
                                    })
                        break
                    else:
                        print("No teams found in this payload structure")
                        
                except json.JSONDecodeError:
                    print("Response is not JSON")
                    print(f"First 200 chars: {response.text[:200]}")
            
        except Exception as e:
            print(f"Error with payload {i+1}: {e}")
        
        time.sleep(1)
    
    return all_teams


def run():
    """Scrape and save Arizona U11 master list."""
    
    print("Scraping Arizona U11 teams from GotSport...")
    teams = scrape_arizona_u11_teams()
    
    if not teams:
        print("No teams found! Trying alternative approach...")
        
        # Fallback to the system.gotsport.com API we used before
        print("Falling back to system.gotsport.com API...")
        
        all_teams = []
        page = 1
        
        while True:
            print(f"Scraping page {page}...")
            
            url = "https://system.gotsport.com/api/v1/team_ranking_data"
            params = {
                "search[team_country]": "USA",
                "search[age]": "11",
                "search[gender]": "m",
                "search[page]": page,
                "search[team_association]": "AZ"
            }
            
            try:
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                
                if not data.get('team_ranking_data'):
                    print(f"No more teams on page {page}")
                    break
                
                teams = data['team_ranking_data']
                print(f"Found {len(teams)} teams on page {page}")
                
                for team in teams:
                    team_name = team.get('team_name', '')
                    club_name = team.get('club_name', '')
                    team_id = team.get('id')
                    
                    if team_id and team_name:
                        all_teams.append({
                            'gotsport_team_id': team_id,
                            'display_name': team_name,
                            'club': club_name,
                            'team_id': f"az_u11_{team_id}"
                        })
                
                page += 1
                time.sleep(1)
                
            except Exception as e:
                print(f"Error on page {page}: {e}")
                break
        
        teams = all_teams
    
    if not teams:
        print("No teams found with either approach!")
        return
    
    # Create DataFrame
    df = pd.DataFrame(teams)
    
    # Save to master directory
    output_dir = Path("data/master/az_boys_u11_2025")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "master_teams.csv"
    
    df.to_csv(output_path, index=False)
    print(f"Saved {len(df)} Arizona U11 teams to {output_path}")
    
    # Show sample
    print("\nSample teams with GotSport IDs:")
    for _, row in df.head(10).iterrows():
        print(f"  {row['gotsport_team_id']}: {row['display_name']} ({row['club']})")
    
    # Check for specific teams
    next_level = df[df['display_name'].str.contains('Next Level', case=False)]
    if not next_level.empty:
        print(f"\nNext Level Soccer teams found: {len(next_level)}")
        for _, row in next_level.iterrows():
            print(f"  {row['gotsport_team_id']}: {row['display_name']}")
    
    # Check for AZ Arsenal
    arsenal = df[df['display_name'].str.contains('Arsenal', case=False)]
    if not arsenal.empty:
        print(f"\nAZ Arsenal teams found: {len(arsenal)}")
        for _, row in arsenal.iterrows():
            print(f"  {row['gotsport_team_id']}: {row['display_name']}")


if __name__ == "__main__":
    run()
