#!/usr/bin/env python3
"""
Rebuild U11 name mapping using the clean U11 games data with proper Arizona team names.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
from pathlib import Path
from src.utils.name_map_builder import normalize_u11_name

def rebuild_u11_name_mapping_clean():
    """Rebuild name mapping using clean U11 games data."""
    
    # Paths
    master_path = Path("data/master/az_boys_u11_2025/master_teams.csv")
    games_path = Path("data/gold/Matched_Games_U11_CLEAN.csv")
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
    print(f"Found {len(observed_names)} unique observed team names in clean games")
    
    # Show sample teams from each source
    print("\nSample master teams:")
    for _, row in master_df.head(5).iterrows():
        print(f"  {row['team_id']}: {row['display_name']}")
    
    print("\nSample observed teams:")
    for name in observed_names.head(10):
        print(f"  {name}")
    
    # Prepare master list with normalized names
    master_df["norm"] = master_df["display_name"].apply(normalize_u11_name)
    
    # Prepare observed names with normalized names
    obs_df = pd.DataFrame({"raw_name": observed_names})
    obs_df["norm"] = obs_df["raw_name"].apply(normalize_u11_name)
    
    # Try to match teams
    print("\nAttempting to match teams...")
    matched = obs_df.merge(
        master_df[["team_id", "display_name", "norm"]], 
        on="norm", 
        how="left"
    )
    
    # Count matches
    matched_count = matched["team_id"].notna().sum()
    unmatched_count = matched["team_id"].isna().sum()
    
    print(f"Matched teams: {matched_count}")
    print(f"Unmatched teams: {unmatched_count}")
    
    if unmatched_count > 0:
        print(f"\nUnmatched teams (first 10):")
        unmatched = matched[matched["team_id"].isna()]
        for _, row in unmatched.head(10).iterrows():
            print(f"  {row['raw_name']} -> {row['norm']}")
    
    # For unmatched teams, create placeholder mappings
    if unmatched_count > 0:
        import hashlib
        for idx, row in matched[matched["team_id"].isna()].iterrows():
            raw_name = row["raw_name"]
            placeholder_id = f"placeholder_{hashlib.sha1(raw_name.encode()).hexdigest()[:8]}"
            matched.loc[idx, "team_id"] = placeholder_id
            matched.loc[idx, "display_name"] = raw_name
    
    # Create final mapping
    name_map_df = matched[["raw_name", "team_id", "display_name"]].drop_duplicates()
    
    # Save mapping
    name_map_df.to_csv(name_map_output_path, index=False)
    print(f"Saved name mapping to {name_map_output_path}")
    
    # Show results
    print(f"\nMapping results:")
    print(f"  Total mappings: {len(name_map_df)}")
    print(f"  Arizona teams matched: {len(name_map_df[~name_map_df['team_id'].str.startswith('placeholder_')])}")
    print(f"  Placeholder teams: {len(name_map_df[name_map_df['team_id'].str.startswith('placeholder_')])}")
    
    print("\nSample Arizona team mappings:")
    az_teams = name_map_df[~name_map_df['team_id'].str.startswith('placeholder_')]
    for _, row in az_teams.head(10).iterrows():
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
        mapping_df = rebuild_u11_name_mapping_clean()
        print(f"\nSuccessfully created U11 name mapping with {len(mapping_df)} entries")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)