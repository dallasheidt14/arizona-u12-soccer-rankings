#!/usr/bin/env python3
"""
Call the GotSport API directly to get the authoritative team list.
This uses the actual API endpoint that the rankings page calls.
"""

import requests
import pandas as pd
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.id_codec import make_team_id

def call_gotsport_api():
    """Call the GotSport team ranking API directly."""
    
    url = "https://system.gotsport.com/api/v1/team_ranking_data"
    params = {
        'search[team_country]': 'USA',
        'search[age]': '11',
        'search[gender]': 'm',
        'search[page]': '1',
        'search[team_association]': 'AZ'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Origin': 'https://rankings.gotsport.com',
        'Referer': 'https://rankings.gotsport.com/',
        'Sec-Ch-Ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
    }
    
    print(f"Calling GotSport API: {url}")
    print(f"Parameters: {params}")
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        
        print(f"Got response: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        
        data = response.json()
        print(f"Response type: {type(data)}")
        
        # Save raw response for debugging
        with open("debug_gotsport_api_response.json", "w", encoding="utf-8") as f:
            import json
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("Saved raw API response to debug_gotsport_api_response.json")
        
        return data
        
    except Exception as e:
        print(f"Error calling API: {e}")
        return None

def extract_teams_from_api_response(data):
    """Extract team names from API response."""
    
    if not data:
        print("No data to process")
        return []
    
    teams = []
    
    # Try different possible structures
    if isinstance(data, dict):
        # Look for teams in various possible keys
        possible_keys = ['team_ranking_data', 'teams', 'data', 'results', 'rankings', 'items']
        
        for key in possible_keys:
            if key in data and isinstance(data[key], list):
                print(f"Found teams in '{key}' key: {len(data[key])} items")
                teams_data = data[key]
                break
        else:
            # If no list found, maybe the data itself is a list
            if isinstance(data, list):
                teams_data = data
            else:
                print(f"Unknown data structure. Keys: {list(data.keys())}")
                return []
    
    elif isinstance(data, list):
        teams_data = data
    else:
        print(f"Unknown data type: {type(data)}")
        return []
    
    print(f"Processing {len(teams_data)} team records")
    
    # Extract team names
    for i, team_record in enumerate(teams_data):
        if isinstance(team_record, dict):
            # Try different possible field names for team name
            team_name = None
            for field in ['team_name', 'name', 'teamName', 'display_name', 'title', 'team_title']:
                if field in team_record:
                    team_name = team_record[field]
                    break
            
            if team_name:
                teams.append(team_name)
                if i < 10:  # Show first 10
                    print(f"  {i+1:2d}. {team_name}")
        elif isinstance(team_record, str):
            teams.append(team_record)
            if i < 10:
                print(f"  {i+1:2d}. {team_record}")
    
    # Remove duplicates and sort
    teams = list(set(teams))
    teams.sort()
    
    print(f"\nFound {len(teams)} unique teams")
    return teams

def create_master_list_from_api_teams(teams):
    """Create master list from API team names."""
    
    if not teams:
        print("No teams to process")
        return None
    
    master_data = []
    for team_name in teams:
        team_id = make_team_id(team_name, "az_boys_u11_2025")
        
        # Extract club name (everything before the year)
        parts = team_name.split()
        club_parts = []
        for part in parts:
            if part.isdigit() and len(part) == 4:  # Found year like "2015"
                break
            club_parts.append(part)
        club = " ".join(club_parts) if club_parts else ""
        
        master_data.append({
            "team_id": team_id,
            "display_name": team_name,
            "club": club
        })
    
    master_df = pd.DataFrame(master_data)
    
    # Verify no duplicate team IDs
    if master_df["team_id"].duplicated().any():
        duplicates = master_df[master_df["team_id"].duplicated()]
        print(f"WARNING: Duplicate team IDs found:")
        for _, row in duplicates.iterrows():
            print(f"  {row['display_name']} -> {row['team_id']}")
    
    # Save master list
    output_path = Path("data/master/az_boys_u11_2025/master_teams.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    master_df.to_csv(output_path, index=False)
    print(f"\nSaved master list to {output_path}")
    print(f"Total teams: {len(master_df)}")
    
    return master_df

if __name__ == "__main__":
    try:
        # Call GotSport API
        data = call_gotsport_api()
        
        if data:
            # Extract teams from API response
            teams = extract_teams_from_api_response(data)
            
            if teams and len(teams) > 10:
                # Create master list from API teams
                master_df = create_master_list_from_api_teams(teams)
                
                if master_df is not None:
                    print(f"\nSuccessfully created master list with {len(master_df)} teams")
                    
                    # Show RSL teams specifically
                    rsl_teams = master_df[master_df["display_name"].str.contains("RSL", case=False, na=False)]
                    if not rsl_teams.empty:
                        print(f"\nRSL teams found ({len(rsl_teams)}):")
                        for _, row in rsl_teams.iterrows():
                            print(f"  {row['display_name']}")
                    
                    # Show Next Level Soccer
                    next_level = master_df[master_df["display_name"].str.contains("Next Level", case=False, na=False)]
                    if not next_level.empty:
                        print(f"\nNext Level Soccer teams:")
                        for _, row in next_level.iterrows():
                            print(f"  {row['display_name']}")
                else:
                    print("Failed to create master list")
            else:
                print("API returned too few teams")
        else:
            print("Failed to call GotSport API")
            
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
