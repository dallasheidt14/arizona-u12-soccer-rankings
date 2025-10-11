#!/usr/bin/env python3
"""
Search through multiple pages of GotSport API to find Arizona U11 Boys teams.
"""

import requests
import pandas as pd
import sys
import os
from pathlib import Path
import time

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.id_codec import make_team_id

def search_arizona_teams():
    """Search through GotSport API pages to find Arizona teams."""
    
    base_url = "https://system.gotsport.com/api/v1/team_ranking_data"
    
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
    
    arizona_teams = []
    page = 1
    max_pages = 50  # Limit search to first 50 pages
    
    print(f"Searching for Arizona U11 Boys teams...")
    
    while page <= max_pages:
        params = {
            'search[team_country]': 'USA',
            'search[age]': '11',
            'search[gender]': 'm',
            'search[page]': str(page),
            'search[team_association]': 'AZ'
        }
        
        print(f"Searching page {page}...")
        
        try:
            response = requests.get(base_url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if 'team_ranking_data' not in data:
                print(f"No team data on page {page}")
                break
            
            teams_data = data['team_ranking_data']
            
            if not teams_data:
                print(f"No teams on page {page}")
                break
            
            # Look for Arizona teams
            page_arizona_teams = []
            for team_record in teams_data:
                if isinstance(team_record, dict) and 'team_name' in team_record:
                    team_name = team_record['team_name']
                    
                    # Check if this looks like an Arizona team
                    if any(indicator in team_name.upper() for indicator in ['AZ', 'ARIZONA', 'PHOENIX', 'SCOTTSDALE', 'TUCSON', 'MESA', 'CHANDLER', 'GLENDALE', 'TEMPE', 'PEORIA', 'SURPRISE', 'GOODYEAR', 'AVONDALE', 'BUCKEYE', 'CASA GRANDE', 'FLAGSTAFF', 'PRESCOTT', 'YUMA', 'KINGMAN', 'LAKE HAVASU', 'RSL-AZ', 'FC ARIZONA', 'ARIZONA SOCCER', 'PHOENIX RISING', 'PHOENIX PREMIER', 'SCOTTSDALE CITY', 'NORTH SCOTTSDALE', 'PIMA COUNTY', 'CANYON DEL ORO', 'THUNDERBIRD', 'VAIL', 'MADISON', 'STATE 48', 'BALA', 'LA ACADEMIA', 'AZ ARSENAL', 'NEXT LEVEL', 'ARIZONA SOCCER ACADEMY', 'EXCEL SOCCER', 'PLAYMAKER', 'PARIS SAINT-GERMAIN', 'SC UNION', 'SPARTAK', 'AYSO', 'SPARTANS', 'UNITED LATINOS']):
                        page_arizona_teams.append(team_name)
                        arizona_teams.append(team_name)
                        print(f"  Found AZ team: {team_name}")
            
            print(f"  Found {len(page_arizona_teams)} Arizona teams on page {page}")
            
            # Check pagination
            if 'pagination' in data:
                pagination = data['pagination']
                current_page = pagination.get('current_page', page)
                total_pages = pagination.get('total_pages', 1)
                
                print(f"  Page {current_page} of {total_pages}")
                
                if current_page >= total_pages:
                    print("Reached last page")
                    break
            
            page += 1
            
            # Small delay to be respectful
            time.sleep(1)
            
        except Exception as e:
            print(f"Error on page {page}: {e}")
            break
    
    # Remove duplicates and sort
    arizona_teams = list(set(arizona_teams))
    arizona_teams.sort()
    
    print(f"\nFound {len(arizona_teams)} unique Arizona teams")
    
    # Show all Arizona teams found
    print("\nAll Arizona teams found:")
    for i, team in enumerate(arizona_teams):
        print(f"  {i+1:3d}. {team}")
    
    return arizona_teams

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
        # Search for Arizona teams
        teams = search_arizona_teams()
        
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
            else:
                print("Failed to create master list")
        else:
            print("Found too few Arizona teams")
            
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
