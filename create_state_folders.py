#!/usr/bin/env python3
"""
Create folders and files for each state from the scraped U11 teams
"""
import pandas as pd
from pathlib import Path
from datetime import datetime

def main():
    print("Creating state folders and files...")
    
    # Load the scraped data
    df = pd.read_csv('all_u11_teams_20251011_180702.csv')
    print(f"Loaded {len(df)} teams")
    
    # Create main directory for state organization
    states_dir = Path("u11_teams_by_state")
    states_dir.mkdir(exist_ok=True)
    
    # Get unique states
    states = sorted(df['state'].unique())
    print(f"Found {len(states)} states/regions")
    
    # Create folder and file for each state
    for state in states:
        state_teams = df[df['state'] == state]
        
        # Clean state name for folder/file names
        clean_state = state.replace(':', '_').replace('/', '_').replace(' ', '_')
        
        # Create state folder
        state_folder = states_dir / clean_state
        state_folder.mkdir(exist_ok=True)
        
        # Save teams to CSV file
        state_file = state_folder / f"{clean_state}_teams.csv"
        state_teams.to_csv(state_file, index=False)
        
        print(f"  {state}: {len(state_teams)} teams -> {state_folder}")
    
    # Create summary file
    summary_data = []
    for state in states:
        state_teams = df[df['state'] == state]
        summary_data.append({
            'state': state,
            'team_count': len(state_teams),
            'folder_name': state.replace(':', '_').replace('/', '_').replace(' ', '_')
        })
    
    summary_df = pd.DataFrame(summary_data)
    summary_df = summary_df.sort_values('team_count', ascending=False)
    
    summary_file = states_dir / "state_summary.csv"
    summary_df.to_csv(summary_file, index=False)
    
    print(f"\nSUCCESS!")
    print(f"Created {len(states)} state folders in: {states_dir}")
    print(f"Summary saved to: {summary_file}")
    
    print(f"\nTOP 10 STATES BY TEAM COUNT:")
    print("=" * 50)
    for _, row in summary_df.head(10).iterrows():
        print(f"{row['state']:8} {row['team_count']:4} teams")
    
    print(f"\nAll state folders created successfully!")

if __name__ == "__main__":
    main()


