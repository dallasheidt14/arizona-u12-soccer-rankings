#!/usr/bin/env python3
"""
Extract unique teams from U11 games data to create canonical master list.
Preserves exact display names from games data (e.g., "FC Elite Arizona 2015 Boys Blue").
"""

import pandas as pd
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.id_codec import make_team_id

def extract_unique_teams():
    """Extract unique teams from games data and create master list."""
    
    # Load games data
    games_path = Path("data/gold/Matched_Games_U11_CLEAN.csv")
    if not games_path.exists():
        raise FileNotFoundError(f"Games data not found: {games_path}")
    
    print(f"Loading games data from {games_path}")
    games_df = pd.read_csv(games_path)
    
    # Extract unique team names from both Team A and Team B
    team_a_names = games_df["Team A"].dropna().unique()
    team_b_names = games_df["Team B"].dropna().unique()
    
    # Combine and get unique teams
    all_teams = pd.concat([
        pd.Series(team_a_names),
        pd.Series(team_b_names)
    ]).drop_duplicates().sort_values().reset_index(drop=True)
    
    print(f"Found {len(all_teams)} unique teams")
    
    # Create master list DataFrame
    master_data = []
    
    for team_name in all_teams:
        # Generate stable team ID using normalization
        team_id = make_team_id(team_name, "az_boys_u11_2025")
        
        # Extract club name from team name (everything before the year)
        # e.g., "FC Elite Arizona 2015 Boys Blue" -> "FC Elite Arizona"
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
        raise ValueError(f"Duplicate team IDs found: {duplicates}")
    
    # Verify no duplicate display names
    if master_df["display_name"].duplicated().any():
        duplicates = master_df[master_df["display_name"].duplicated()]
        raise ValueError(f"Duplicate display names found: {duplicates}")
    
    print(f"Generated {len(master_df)} unique team IDs")
    
    # Save master list
    output_path = Path("data/master/az_boys_u11_2025/master_teams.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    master_df.to_csv(output_path, index=False)
    print(f"Saved master list to {output_path}")
    
    # Show sample of teams
    print("\nSample teams:")
    for i, row in master_df.head(10).iterrows():
        print(f"  {row['team_id']}: {row['display_name']}")
    
    # Check for specific teams
    next_level = master_df[master_df["display_name"].str.contains("next level", case=False, na=False)]
    if not next_level.empty:
        print(f"\nNext Level Soccer found:")
        print(f"  {next_level.iloc[0]['team_id']}: {next_level.iloc[0]['display_name']}")
    else:
        print("\nWARNING: Next Level Soccer not found in master list")
    
    return master_df

if __name__ == "__main__":
    try:
        master_df = extract_unique_teams()
        print(f"\nSuccessfully created master list with {len(master_df)} teams")
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
