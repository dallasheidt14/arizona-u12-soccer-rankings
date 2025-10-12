#!/usr/bin/env python3
"""
Scrape U11 master team list from GotSport with team IDs.

Focus: Just get the master list with GotSport team IDs for Arizona U11 teams.
We'll use these IDs later to scrape individual team game histories.
"""

import requests
import pandas as pd
import time
from pathlib import Path

def scrape_u11_master_list():
    """Scrape U11 teams from GotSport API with their team IDs."""
    
    all_teams = []
    page = 1
    
    print("Scraping U11 teams from GotSport...")
    
    while True:
        print(f"Scraping page {page}...")
        
        url = "https://system.gotsport.com/api/v1/team_ranking_data"
        params = {
            "search[team_country]": "USA",
            "search[age]": "11",
            "search[gender]": "m",
            "search[page]": page
            # Removed Arizona filter - we'll filter afterward
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
            
            # Debug: Show available fields from first team
            if page == 1 and teams:
                print(f"Available fields: {list(teams[0].keys())}")
            
            for team in teams:
                team_name = team.get('team_name', '')
                club_name = team.get('club_name', '')
                gotsport_team_id = team.get('id')  # This is the GotSport team ID!
                team_association = team.get('team_association', '')  # Get actual state/association from API
                team_region = team.get('team_region', '')  # Get region info
                team_country = team.get('team_country', '')  # Get country info
                
                if gotsport_team_id and team_name:
                    all_teams.append({
                        'gotsport_team_id': gotsport_team_id,
                        'display_name': team_name,
                        'club': club_name,
                        'state': team_association,  # Use actual API state/association
                        'region': team_region,
                        'country': team_country,
                        'age_group': 'U11',
                        'gender': 'M'
                    })
            
            page += 1
            time.sleep(1)  # Be respectful to the server
            
        except Exception as e:
            print(f"Error on page {page}: {e}")
            break
    
    return all_teams


def run():
    """Scrape and save U11 master list with GotSport team IDs."""
    
    print("Starting U11 master list scrape...")
    teams = scrape_u11_master_list()
    
    if not teams:
        print("No teams found!")
        return
    
    # Create DataFrame
    df = pd.DataFrame(teams)
    
    # Create output directory
    output_dir = Path("data/master/az_boys_u11_2025")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save master list with timestamp to avoid permission issues
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"master_teams_{timestamp}.csv"
    df.to_csv(output_path, index=False)
    
    print(f"\nSuccessfully scraped {len(df)} U11 teams")
    print(f"Saved to: {output_path}")
    
    # Show states found
    states = sorted(df['state'].unique())
    print(f"\nStates found: {states}")
    print(f"Total unique states: {len(states)}")
    
    # Create folder structure and save teams by state
    states_dir = output_dir / "by_state"
    states_dir.mkdir(exist_ok=True)
    
    print(f"\nCreating state-specific files in: {states_dir}")
    
    # Save each state's teams to separate files
    for state in states:
        state_teams = df[df['state'] == state]
        if not state_teams.empty:
            # Clean state name for filename
            clean_state = state.replace(' ', '_').replace('/', '_')
            state_file = states_dir / f"{clean_state}_teams.csv"
            state_teams.to_csv(state_file, index=False)
            print(f"  {state}: {len(state_teams)} teams -> {state_file}")
    
    # Show sample teams from different states
    print("\nSample teams by state:")
    for state in states[:5]:  # Show first 5 states
        state_teams = df[df['state'] == state]
        print(f"\n{state} ({len(state_teams)} teams):")
        for _, row in state_teams.head(3).iterrows():
            print(f"  {row['gotsport_team_id']}: {row['display_name']} ({row['club']})")
    
    # Check for specific Arizona teams
    az_teams = df[df['state'] == 'AZ']
    if not az_teams.empty:
        print(f"\nArizona teams: {len(az_teams)}")
        next_level = az_teams[az_teams['display_name'].str.contains('Next Level', case=False)]
        if not next_level.empty:
            print(f"Arizona Next Level Soccer teams: {len(next_level)}")
            for _, row in next_level.iterrows():
                print(f"  {row['gotsport_team_id']}: {row['display_name']}")
        
        arsenal = az_teams[az_teams['display_name'].str.contains('Arsenal', case=False)]
        if not arsenal.empty:
            print(f"Arizona Arsenal teams: {len(arsenal)}")
            for _, row in arsenal.iterrows():
                print(f"  {row['gotsport_team_id']}: {row['display_name']}")
    
    print(f"\nReady for next step: Use Arizona GotSport team IDs to scrape individual game histories")


if __name__ == "__main__":
    run()
