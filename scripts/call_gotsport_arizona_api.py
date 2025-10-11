#!/usr/bin/env python3
"""
Call the GotSport API with the correct parameters for Arizona U11 Boys teams.
Using the exact API call from the GotSport rankings page.
"""

import requests
import pandas as pd
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.id_codec import make_team_id

def call_gotsport_arizona_api():
    """Call the GotSport API with correct Arizona parameters."""
    
    url = "https://system.gotsport.com/api/v1/team_ranking_data"
    params = {
        'search[team_country]': 'USA',
        'search[age]': '11',
        'search[gender]': 'm',
        'search[page]': '1',
        'search[team_association]': 'AZ'  # This is the key parameter!
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
    
    print(f"Calling GotSport Arizona API: {url}")
    print(f"Parameters: {params}")
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        
        print(f"Got response: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        
        data = response.json()
        print(f"Response type: {type(data)}")
        
        # Save raw response for debugging
        with open("debug_gotsport_arizona_response.json", "w", encoding="utf-8") as f:
            import json
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("Saved raw API response to debug_gotsport_arizona_response.json")
        
        return data
        
    except Exception as e:
        print(f"Error calling API: {e}")
        return None

def extract_teams_from_arizona_response(data):
    """Extract team names from Arizona API response."""
    
    if not data:
        print("No data to process")
        return []
    
    teams = []
    
    # Extract teams from team_ranking_data
    if isinstance(data, dict) and 'team_ranking_data' in data:
        teams_data = data['team_ranking_data']
        print(f"Found {len(teams_data)} teams in team_ranking_data")
        
        # Extract team names
        for i, team_record in enumerate(teams_data):
            if isinstance(team_record, dict) and 'team_name' in team_record:
                team_name = team_record['team_name']
                teams.append(team_name)
                if i < 20:  # Show first 20
                    print(f"  {i+1:2d}. {team_name}")
        
        # Check pagination
        if 'pagination' in data:
            pagination = data['pagination']
            current_page = pagination.get('current_page', 1)
            total_pages = pagination.get('total_pages', 1)
            total_count = pagination.get('total_count', len(teams))
            
            print(f"\nPagination: Page {current_page} of {total_pages}")
            print(f"Total teams available: {total_count}")
    
    # Remove duplicates and sort
    teams = list(set(teams))
    teams.sort()
    
    print(f"\nFound {len(teams)} unique teams")
    return teams

def create_master_list_from_arizona_teams(teams):
    """Create master list from Arizona team names."""
    
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
        # Call GotSport Arizona API
        data = call_gotsport_arizona_api()
        
        if data:
            # Extract teams from API response
            teams = extract_teams_from_arizona_response(data)
            
            if teams and len(teams) > 5:
                # Create master list from Arizona teams
                master_df = create_master_list_from_arizona_teams(teams)
                
                if master_df is not None:
                    print(f"\nSuccessfully created master list with {len(master_df)} Arizona teams")
                    
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
                    
                    # Show sample of all teams
                    print(f"\nSample of all teams:")
                    for i, row in master_df.head(10).iterrows():
                        print(f"  {i+1:2d}. {row['display_name']}")
                else:
                    print("Failed to create master list")
            else:
                print("API returned too few teams")
        else:
            print("Failed to call GotSport Arizona API")
            
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
