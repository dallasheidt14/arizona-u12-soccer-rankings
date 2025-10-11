#!/usr/bin/env python3
"""
Create U11 master list from games data (the actual source of truth).

The GotSport master list and games data are from different sources/time periods.
Use the games data as the authoritative source.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
from pathlib import Path
from src.utils.id_codec import make_team_id

def run():
    """Create master list from games data."""
    
    # Load games data
    games = pd.read_csv('data/raw/az_boys_u11_2025/games_raw.csv')
    print(f"Loaded {len(games)} games")
    
    # Extract unique teams
    all_teams = pd.concat([games['team_name_a'], games['team_name_b']]).dropna().unique()
    print(f"Found {len(all_teams)} unique teams")
    
    # Create master list
    master_data = []
    for team_name in all_teams:
        # Extract club name (simple heuristic)
        club_name = team_name.split(' 2015')[0].strip()
        if 'FC' in club_name:
            club_name = club_name.split('FC')[0] + 'FC'
        
        team_id = make_team_id(team_name, "az_boys_u11_2025")
        master_data.append({
            "team_id": team_id,
            "display_name": team_name,
            "club": club_name
        })
    
    master_df = pd.DataFrame(master_data)
    
    # Save master list
    output_dir = Path("data/master/az_boys_u11_2025")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "master_teams.csv"
    
    master_df.to_csv(output_path, index=False)
    print(f"Saved master list to {output_path}")
    
    # Show sample teams
    print(f"\nSample teams:")
    for _, row in master_df.head(10).iterrows():
        print(f"  {row['team_id']}: {row['display_name']}")
    
    print(f"\nCreated master list with {len(master_df)} teams")
    return master_df

if __name__ == "__main__":
    run()
