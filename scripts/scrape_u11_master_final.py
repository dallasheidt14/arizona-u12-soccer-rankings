#!/usr/bin/env python3
"""
Scrape U11 teams from GotSport API and properly extract state information
This will get the real state data and organize teams by state
"""
import requests
import pandas as pd
from pathlib import Path
import time
from datetime import datetime
import re

def extract_state_from_association(team_association):
    """Extract state from team_association field"""
    if not team_association:
        return None
    
    # Handle formats like "FL:1", "NJ:1", "AZ:1"
    if ':' in team_association:
        state = team_association.split(':')[0]
        return state
    
    # Handle direct state codes
    if len(team_association) == 2 and team_association.isalpha():
        return team_association
    
    return team_association

def scrape_u11_teams():
    """Scrape U11 teams from GotSport API"""
    
    print("Starting U11 teams scrape from GotSport API...")
    
    all_teams = []
    page = 1
    
    while True:
        print(f"Scraping page {page}...")
        
        url = "https://system.gotsport.com/api/v1/team_ranking_data"
        params = {
            "search[team_country]": "USA",
            "search[age]": "11",
            "search[gender]": "m",
            "search[page]": page
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
            
            # Debug: Show first team's fields
            if page == 1 and teams:
                print(f"Available fields: {list(teams[0].keys())}")
                print(f"Sample team_association: {teams[0].get('team_association', 'N/A')}")
            
            for team in teams:
                team_name = team.get('team_name', '')
                club_name = team.get('club_name', '')
                gotsport_team_id = team.get('id')
                team_association = team.get('team_association', '')
                team_region = team.get('team_region', '')
                team_country = team.get('team_country', '')
                
                # Extract clean state from team_association
                state = extract_state_from_association(team_association)
                
                if gotsport_team_id and team_name:
                    all_teams.append({
                        'gotsport_team_id': gotsport_team_id,
                        'display_name': team_name,
                        'club': club_name,
                        'state': state,
                        'team_association_raw': team_association,  # Keep original for debugging
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

def main():
    print("Starting comprehensive U11 master list scrape...")
    
    # Scrape teams
    teams = scrape_u11_teams()
    
    if not teams:
        print("No teams found!")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(teams)
    
    # Remove teams with no state
    df_with_state = df[df['state'].notna() & (df['state'] != '')]
    print(f"Teams with state info: {len(df_with_state)} out of {len(df)}")
    
    # Create output directory
    output_dir = Path("data/master/az_boys_u11_2025")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"master_teams_{timestamp}.csv"
    df_with_state.to_csv(output_path, index=False)
    
    print(f"\nSuccessfully scraped {len(df_with_state)} U11 teams with state info")
    print(f"Saved to: {output_path}")
    
    # Show states found
    states = sorted(df_with_state['state'].unique())
    print(f"\nStates found: {states}")
    print(f"Total unique states: {len(states)}")
    
    # Show state distribution
    print("\nTeams per state:")
    state_counts = df_with_state['state'].value_counts().sort_index()
    for state, count in state_counts.items():
        print(f"  {state}: {count} teams")
    
    # Create folder structure and save teams by state
    states_dir = output_dir / "by_state"
    states_dir.mkdir(exist_ok=True)
    
    print(f"\nCreating state-specific files in: {states_dir}")
    
    # Save each state's teams to separate files
    for state in states:
        state_teams = df_with_state[df_with_state['state'] == state]
        if not state_teams.empty:
            # Clean state name for filename
            clean_state = state.replace(' ', '_').replace('/', '_')
            state_file = states_dir / f"{clean_state}_teams.csv"
            state_teams.to_csv(state_file, index=False)
            print(f"  {state}: {len(state_teams)} teams -> {state_file}")
    
    # Show sample teams from different states
    print("\nSample teams by state:")
    for state in states[:5]:  # Show first 5 states
        state_teams = df_with_state[df_with_state['state'] == state]
        print(f"\n{state} ({len(state_teams)} teams):")
        for _, row in state_teams.head(3).iterrows():
            print(f"  {row['gotsport_team_id']}: {row['display_name']} ({row['club']})")
    
    # Check for Arizona teams specifically
    az_teams = df_with_state[df_with_state['state'] == 'AZ']
    if not az_teams.empty:
        print(f"\nArizona teams found: {len(az_teams)}")
        print("Sample Arizona teams:")
        for _, row in az_teams.head(10).iterrows():
            print(f"  {row['gotsport_team_id']}: {row['display_name']}")
        
        # Check for specific clubs
        next_level = az_teams[az_teams['display_name'].str.contains('Next Level', case=False)]
        if not next_level.empty:
            print(f"\nNext Level Soccer teams: {len(next_level)}")
            for _, row in next_level.iterrows():
                print(f"  {row['gotsport_team_id']}: {row['display_name']}")
        
        arsenal = az_teams[az_teams['display_name'].str.contains('Arsenal', case=False)]
        if not arsenal.empty:
            print(f"\nArsenal teams: {len(arsenal)}")
            for _, row in arsenal.iterrows():
                print(f"  {row['gotsport_team_id']}: {row['display_name']}")
    
    print(f"\nReady for next step: Use Arizona GotSport team IDs to scrape individual game histories")

if __name__ == "__main__":
    main()


