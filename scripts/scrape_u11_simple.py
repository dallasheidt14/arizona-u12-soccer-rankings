#!/usr/bin/env python3
"""
Simple U11 master list scraper - just get teams with proper state info
"""
import requests
import pandas as pd
from pathlib import Path
import time
from datetime import datetime

def extract_state(team_association):
    """Extract state from team_association field like 'FL:1' -> 'FL'"""
    if not team_association:
        return None
    
    if ':' in team_association:
        return team_association.split(':')[0]
    
    return team_association

def main():
    print("Scraping U11 teams with proper state info...")
    
    all_teams = []
    page = 1
    max_pages = 50  # Limit to avoid long runs
    
    while page <= max_pages:
        print(f"Page {page}/{max_pages}...")
        
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
            print(f"  Found {len(teams)} teams")
            
            for team in teams:
                team_name = team.get('team_name', '')
                club_name = team.get('club_name', '')
                gotsport_team_id = team.get('id')
                team_association = team.get('team_association', '')
                
                # Extract clean state
                state = extract_state(team_association)
                
                if gotsport_team_id and team_name and state:
                    all_teams.append({
                        'gotsport_team_id': gotsport_team_id,
                        'display_name': team_name,
                        'club': club_name,
                        'state': state,
                        'team_association_raw': team_association
                    })
            
            page += 1
            time.sleep(0.5)  # Be nice to the server
            
        except Exception as e:
            print(f"Error on page {page}: {e}")
            break
    
    if not all_teams:
        print("No teams found!")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(all_teams)
    
    # Create output directory
    output_dir = Path("data/master/az_boys_u11_2025")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save master list
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"master_teams_{timestamp}.csv"
    df.to_csv(output_path, index=False)
    
    print(f"\n✅ Scraped {len(df)} U11 teams")
    print(f"📁 Saved to: {output_path}")
    
    # Show states
    states = sorted(df['state'].unique())
    print(f"\n🗺️  States found: {states}")
    print(f"📊 Total states: {len(states)}")
    
    # State distribution
    print(f"\n📈 Teams per state:")
    state_counts = df['state'].value_counts().sort_index()
    for state, count in state_counts.items():
        print(f"  {state}: {count} teams")
    
    # Create state-specific files
    states_dir = output_dir / "by_state"
    states_dir.mkdir(exist_ok=True)
    
    print(f"\n📂 Creating state files in: {states_dir}")
    for state in states:
        state_teams = df[df['state'] == state]
        clean_state = state.replace(' ', '_').replace('/', '_')
        state_file = states_dir / f"{clean_state}_teams.csv"
        state_teams.to_csv(state_file, index=False)
        print(f"  {state}: {len(state_teams)} teams -> {state_file}")
    
    # Arizona teams
    az_teams = df[df['state'] == 'AZ']
    if not az_teams.empty:
        print(f"\n🏜️  Arizona teams: {len(az_teams)}")
        print("Sample Arizona teams:")
        for _, row in az_teams.head(5).iterrows():
            print(f"  {row['gotsport_team_id']}: {row['display_name']}")
    
    print(f"\n✅ Ready! Master list with proper states created.")

if __name__ == "__main__":
    main()


