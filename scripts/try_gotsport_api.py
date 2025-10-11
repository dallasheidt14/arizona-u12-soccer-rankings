#!/usr/bin/env python3
"""
Try to find and call the GotSport API endpoint directly.
The rankings page loads data via JavaScript, so we need to find the actual API.
"""

import requests
import pandas as pd
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.id_codec import make_team_id

def try_gotsport_api_endpoints():
    """Try different possible API endpoints for GotSport rankings."""
    
    base_url = "https://rankings.gotsport.com"
    
    # Possible API endpoints to try
    api_endpoints = [
        "/api/rankings",
        "/api/teams",
        "/api/rankings/teams",
        "/api/v1/rankings",
        "/api/v1/teams",
        "/api/rankings?country=USA&age=11&gender=m&state=AZ",
        "/api/teams?country=USA&age=11&gender=m&state=AZ",
        "/api/rankings/teams?country=USA&age=11&gender=m&state=AZ",
        "/api/v1/rankings?country=USA&age=11&gender=m&state=AZ",
        "/api/v1/teams?country=USA&age=11&gender=m&state=AZ",
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://rankings.gotsport.com/',
    }
    
    for endpoint in api_endpoints:
        url = base_url + endpoint
        print(f"Trying: {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            print(f"  Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"  JSON response: {type(data)} with {len(data) if isinstance(data, (list, dict)) else 'unknown'} items")
                    
                    # If we get data, try to extract teams
                    if isinstance(data, list) and len(data) > 0:
                        print(f"  First item: {data[0]}")
                        return data
                    elif isinstance(data, dict):
                        print(f"  Keys: {list(data.keys())}")
                        if 'teams' in data:
                            return data['teams']
                        elif 'data' in data:
                            return data['data']
                        else:
                            return data
                            
                except ValueError:
                    print(f"  Not JSON: {response.text[:200]}...")
            else:
                print(f"  Error: {response.text[:100]}...")
                
        except Exception as e:
            print(f"  Exception: {e}")
        
        print()
    
    return None

def create_master_list_from_api_data(data):
    """Create master list from API data."""
    
    if not data:
        print("No data to process")
        return None
    
    print(f"Processing API data: {type(data)}")
    
    teams = []
    
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                # Try different possible field names for team name
                team_name = None
                for field in ['name', 'team_name', 'teamName', 'display_name', 'title']:
                    if field in item:
                        team_name = item[field]
                        break
                
                if team_name:
                    teams.append(team_name)
            elif isinstance(item, str):
                teams.append(item)
    
    elif isinstance(data, dict):
        # Look for teams in the data structure
        for key, value in data.items():
            if 'team' in key.lower() and isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and 'name' in item:
                        teams.append(item['name'])
                    elif isinstance(item, str):
                        teams.append(item)
    
    if not teams:
        print("No teams found in API data")
        return None
    
    # Remove duplicates and sort
    teams = list(set(teams))
    teams.sort()
    
    print(f"Found {len(teams)} unique teams")
    
    # Show first few teams
    print("\nFirst 10 teams:")
    for i, team in enumerate(teams[:10]):
        print(f"  {i+1}. {team}")
    
    # Create master list
    master_data = []
    for team_name in teams:
        team_id = make_team_id(team_name, "az_boys_u11_2025")
        
        # Extract club name
        parts = team_name.split()
        club_parts = []
        for part in parts:
            if part.isdigit() and len(part) == 4:
                break
            club_parts.append(part)
        club = " ".join(club_parts) if club_parts else ""
        
        master_data.append({
            "team_id": team_id,
            "display_name": team_name,
            "club": club
        })
    
    master_df = pd.DataFrame(master_data)
    
    # Save master list
    output_path = Path("data/master/az_boys_u11_2025/master_teams.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    master_df.to_csv(output_path, index=False)
    print(f"\nSaved master list to {output_path}")
    print(f"Total teams: {len(master_df)}")
    
    return master_df

if __name__ == "__main__":
    try:
        # Try to find API endpoint
        data = try_gotsport_api_endpoints()
        
        if data:
            # Create master list from API data
            master_df = create_master_list_from_api_data(data)
            
            if master_df is not None:
                print(f"\nSuccessfully created master list with {len(master_df)} teams")
            else:
                print("Failed to create master list from API data")
        else:
            print("No API endpoint found")
            print("The GotSport site likely uses JavaScript to load data dynamically")
            print("We may need to use Selenium or find the actual API endpoint")
            
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
