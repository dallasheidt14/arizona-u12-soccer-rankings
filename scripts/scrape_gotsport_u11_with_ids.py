#!/usr/bin/env python3
"""
Re-scrape GotSport U11 master list to capture actual GotSport team IDs.

This will allow us to scrape individual team game histories.
"""

import requests
import pandas as pd
import time
from pathlib import Path
import re

def scrape_gotsport_u11_master_with_ids():
    """Scrape U11 teams from GotSport with their actual team IDs."""
    
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
                team_id = team.get('id')  # This is the GotSport team ID!
                
                if team_id and team_name:
                    all_teams.append({
                        'gotsport_team_id': team_id,
                        'display_name': team_name,
                        'club': club_name,
                        'team_id': f"az_u11_{team_id}"  # Our internal ID
                    })
            
            page += 1
            time.sleep(1)  # Be respectful
            
        except Exception as e:
            print(f"Error on page {page}: {e}")
            break
    
    return all_teams


def run():
    """Scrape and save GotSport U11 master list with team IDs."""
    
    print("Scraping GotSport U11 master list with team IDs...")
    teams = scrape_gotsport_u11_master_with_ids()
    
    if not teams:
        print("No teams found!")
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


if __name__ == "__main__":
    run()
