#!/usr/bin/env python3
"""
Scrape ALL U11 teams with club names included
Format: team_name, club_name, gotsport_team_id, state
"""
import requests
import pandas as pd
from pathlib import Path
import time
from datetime import datetime

def main():
    print("Scraping ALL U11 teams with club names...")
    print("Format: team_name, club_name, gotsport_team_id, state")
    
    all_teams = []
    page = 1
    
    while True:
        print(f"Page {page}...")
        
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
                gotsport_team_id = team.get('team_id')  # Use team_id for matches API
                team_association = team.get('team_association', '')
                
                if gotsport_team_id and team_name:
                    all_teams.append({
                        'team_name': team_name,
                        'club_name': club_name,
                        'gotsport_team_id': gotsport_team_id,
                        'state': team_association
                    })
            
            page += 1
            time.sleep(0.5)
            
        except Exception as e:
            print(f"Error on page {page}: {e}")
            break
    
    if not all_teams:
        print("No teams found!")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(all_teams)
    
    # Save ALL teams to correct location
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("data/Master/U11 BOYS/ALL STATES")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"all_u11_teams_with_clubs_{timestamp}.csv"
    df.to_csv(output_file, index=False)
    
    print(f"\nSUCCESS!")
    print(f"Scraped {len(df)} U11 teams with club names")
    print(f"Saved to: {output_file}")
    
    # Show first 20 results
    print(f"\nFIRST 20 RESULTS:")
    print("=" * 100)
    print(df.head(20).to_string(index=False))
    
    # Show states found
    states = sorted(df['state'].unique())
    print(f"\nStates found: {len(states)}")
    for state in states[:15]:  # Show first 15
        count = len(df[df['state'] == state])
        print(f"  {state}: {count} teams")
    
    if len(states) > 15:
        print(f"  ... and {len(states) - 15} more states")
    
    print(f"\nReady to create state folders with club names!")

if __name__ == "__main__":
    main()
