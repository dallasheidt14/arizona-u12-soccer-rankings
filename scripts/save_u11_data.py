#!/usr/bin/env python3
"""
Save the U11 data that was already scraped (8,020 teams)
"""
import pandas as pd
from pathlib import Path
from datetime import datetime

def main():
    # The data was already scraped and is in the all_teams list
    # Let's recreate it from the existing file if possible, or create a minimal version
    
    # Check if we have any existing data
    existing_file = Path("data/master/az_boys_u11_2025/master_teams.csv")
    if existing_file.exists():
        print(f"Found existing file: {existing_file}")
        df = pd.read_csv(existing_file)
        print(f"Loaded {len(df)} teams from existing file")
    else:
        print("No existing file found. The scraped data was lost due to the error.")
        print("We need to re-run the scraper.")
        return
    
    # Create output directory
    output_dir = Path("data/master/az_boys_u11_2025")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"master_teams_{timestamp}.csv"
    df.to_csv(output_path, index=False)
    
    print(f"\nSuccessfully saved {len(df)} U11 teams")
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
    main()


