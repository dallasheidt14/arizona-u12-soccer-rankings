#!/usr/bin/env python3
"""
Rebuild U11 name mapping using Arizona-specific master list and game history.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
from pathlib import Path
from src.utils.name_map_builder import build_name_map

def rebuild_arizona_name_mapping():
    """Rebuild name mapping for Arizona U11 teams."""
    
    # Paths
    master_path = Path("data/master/az_boys_u11_2025/master_teams.csv")
    games_path = Path("data/gold/Matched_Games_AZ_BOYS_U11.csv")
    name_map_output_dir = Path("data/mappings/az_boys_u11_2025")
    name_map_output_dir.mkdir(parents=True, exist_ok=True)
    name_map_output_path = name_map_output_dir / "name_map.csv"
    
    # Check files exist
    if not master_path.exists():
        raise FileNotFoundError(f"Master teams list not found at {master_path}")
    if not games_path.exists():
        raise FileNotFoundError(f"Games data not found at {games_path}")
    
    # Load master list
    master_df = pd.read_csv(master_path)
    print(f"Loaded Arizona master list from {master_path}")
    print(f"Master list has {len(master_df)} teams")
    
    # Load games data
    games_df = pd.read_csv(games_path)
    observed_names = pd.concat([games_df["Team A"], games_df["Team B"]]).dropna().drop_duplicates()
    print(f"Found {len(observed_names)} unique observed team names in Arizona games")
    
    # Show sample teams from each source
    print("\nSample master teams:")
    for _, row in master_df.head(5).iterrows():
        print(f"  {row['team_id']}: {row['display_name']}")
    
    print("\nSample observed teams:")
    for name in observed_names.head(5):
        print(f"  {name}")
    
    # Build name mapping
    print("\nBuilding name mapping...")
    name_map_df = build_name_map(master_df, observed_names, "az_boys_u11_2025")
    
    # Save mapping
    name_map_df.to_csv(name_map_output_path, index=False)
    print(f"Saved name mapping to {name_map_output_path}")
    
    # Show results
    print(f"\nMapping results:")
    print(f"  Total mappings: {len(name_map_df)}")
    print(f"  Unique team_ids: {name_map_df['team_id'].nunique()}")
    
    print("\nSample mappings:")
    for _, row in name_map_df.head(10).iterrows():
        print(f"  {row['raw_name']} -> {row['team_id']} ({row['display_name']})")
    
    # Check for specific teams
    next_level_soccer = name_map_df[name_map_df["display_name"].str.contains("Next Level Soccer", case=False)]
    if not next_level_soccer.empty:
        print("\nNext Level Soccer mapping:")
        for _, row in next_level_soccer.iterrows():
            print(f"  {row['raw_name']} -> {row['team_id']} ({row['display_name']})")
    
    return name_map_df

if __name__ == "__main__":
    try:
        mapping_df = rebuild_arizona_name_mapping()
        print(f"\n✅ Successfully created Arizona U11 name mapping with {len(mapping_df)} entries")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
