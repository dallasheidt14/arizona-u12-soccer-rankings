#!/usr/bin/env python3
"""
Create U11 master list directly from games data to ensure perfect matching.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
from pathlib import Path
from src.utils.id_codec import make_team_id

def create_u11_master_from_games():
    """Create master list from games data for perfect matching."""
    
    # Paths
    games_path = Path("data/gold/Matched_Games_U11_CLEAN.csv")
    master_output_dir = Path("data/master/az_boys_u11_2025")
    master_output_dir.mkdir(parents=True, exist_ok=True)
    master_output_path = master_output_dir / "master_teams.csv"
    
    # Check games file exists
    if not games_path.exists():
        raise FileNotFoundError(f"Games data not found at {games_path}")
    
    # Load games data
    games_df = pd.read_csv(games_path)
    print(f"Loaded games data from {games_path}")
    print(f"Total games: {len(games_df)}")
    
    # Extract unique team names
    unique_teams = pd.concat([games_df["Team A"], games_df["Team B"]]).dropna().unique()
    print(f"Found {len(unique_teams)} unique teams")
    
    # Create master list
    master_data = []
    for team_name in unique_teams:
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
    master_df.to_csv(master_output_path, index=False)
    print(f"Saved master list to {master_output_path}")
    
    # Show sample teams
    print("\nSample teams:")
    for _, row in master_df.head(10).iterrows():
        print(f"  {row['team_id']}: {row['display_name']}")
    
    # Check for specific teams
    next_level_soccer = master_df[master_df["display_name"].str.contains("Next Level Soccer", case=False)]
    if not next_level_soccer.empty:
        print("\nNext Level Soccer found:")
        for _, row in next_level_soccer.iterrows():
            print(f"  {row['team_id']}: {row['display_name']}")
    
    print(f"\nCreated master list with {len(master_df)} teams")
    return master_df

if __name__ == "__main__":
    try:
        master_df = create_u11_master_from_games()
        print("Successfully created U11 master list from games data")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
