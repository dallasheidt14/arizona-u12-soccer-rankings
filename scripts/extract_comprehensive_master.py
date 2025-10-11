#!/usr/bin/env python3
"""
Extract ALL unique teams from U11 games data to create comprehensive master list.
This ensures we capture all team variations (colors, etc.) that exist in the games.
"""

import pandas as pd
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.id_codec import make_team_id

def extract_comprehensive_master_list():
    """Extract all unique teams from games data."""
    
    games_path = Path("data/gold/Matched_Games_U11_CLEAN.csv")
    if not games_path.exists():
        raise FileNotFoundError(f"Games data not found at {games_path}")
    
    print(f"Loading games data from {games_path}")
    games_df = pd.read_csv(games_path)
    
    # Extract all unique team names from games data
    team_a_names = games_df["Team A"].dropna().unique()
    team_b_names = games_df["Team B"].dropna().unique()
    all_team_names = pd.concat([pd.Series(team_a_names), pd.Series(team_b_names)]).drop_duplicates().sort_values()
    
    print(f"Found {len(all_team_names)} unique teams in games data")
    
    # Show sample teams
    print("\nSample teams from games:")
    for i, name in enumerate(all_team_names.head(15)):
        print(f"  {i+1}. {name}")
    
    # Create master list with team IDs
    master_data = []
    for team_name in all_team_names:
        team_id = make_team_id(team_name, "az_boys_u11_2025")
        
        # Extract club name (everything before the last color/year)
        parts = team_name.split()
        club_parts = []
        for part in parts:
            if part.lower() in ['blue', 'red', 'white', 'black', 'gold', 'silver']:
                break
            if part.isdigit() and len(part) == 4:  # Year like "2015"
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
        print(f"WARNING: Duplicate team IDs found:")
        for _, row in duplicates.iterrows():
            print(f"  {row['display_name']} -> {row['team_id']}")
    
    # Save comprehensive master list
    output_path = Path("data/master/az_boys_u11_2025/master_teams.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    master_df.to_csv(output_path, index=False)
    print(f"\nSaved comprehensive master list to {output_path}")
    print(f"Total teams: {len(master_df)}")
    
    # Show RSL teams
    rsl_teams = master_df[master_df["display_name"].str.contains("RSL", case=False, na=False)]
    if not rsl_teams.empty:
        print(f"\nRSL teams ({len(rsl_teams)}):")
        for _, row in rsl_teams.iterrows():
            print(f"  {row['display_name']}")
    
    # Show Next Level Soccer
    next_level = master_df[master_df["display_name"].str.contains("Next Level", case=False, na=False)]
    if not next_level.empty:
        print(f"\nNext Level Soccer teams:")
        for _, row in next_level.iterrows():
            print(f"  {row['display_name']}")
    
    return master_df

if __name__ == "__main__":
    try:
        master_df = extract_comprehensive_master_list()
        print(f"\n✅ Successfully created comprehensive master list with {len(master_df)} teams")
        
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
