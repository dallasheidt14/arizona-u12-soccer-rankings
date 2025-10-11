#!/usr/bin/env python3
"""
Rebuild U11 name mapping for Arizona teams only, allowing non-Arizona teams to pass through.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
from pathlib import Path
from src.utils.name_map_builder import normalize_u11_name

def rebuild_arizona_name_mapping_permissive():
    """Rebuild name mapping for Arizona U11 teams, allowing non-Arizona teams."""
    
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
    
    # Prepare master list with normalized names
    master_df["norm"] = master_df["display_name"].apply(normalize_u11_name)
    
    # Prepare observed names with normalized names
    obs_df = pd.DataFrame({"raw_name": observed_names})
    obs_df["norm"] = obs_df["raw_name"].apply(normalize_u11_name)
    
    # Try to match Arizona teams
    print("\nAttempting to match Arizona teams...")
    matched = obs_df.merge(
        master_df[["team_id", "display_name", "norm"]], 
        on="norm", 
        how="left"
    )
    
    # For unmatched teams, create a placeholder mapping (they're likely non-Arizona teams)
    unmatched_mask = matched["team_id"].isna()
    unmatched_count = unmatched_mask.sum()
    
    print(f"Matched Arizona teams: {len(matched) - unmatched_count}")
    print(f"Unmatched teams (likely non-Arizona): {unmatched_count}")
    
    if unmatched_count > 0:
        # Create placeholder team_ids for non-Arizona teams
        import hashlib
        for idx, row in matched[unmatched_mask].iterrows():
            # Generate a stable ID for non-Arizona teams
            raw_name = row["raw_name"]
            placeholder_id = f"non_az_{hashlib.sha1(raw_name.encode()).hexdigest()[:8]}"
            matched.loc[idx, "team_id"] = placeholder_id
            matched.loc[idx, "display_name"] = raw_name  # Keep original name
    
    # Create final mapping
    name_map_df = matched[["raw_name", "team_id", "display_name"]].drop_duplicates()
    
    # Save mapping
    name_map_df.to_csv(name_map_output_path, index=False)
    print(f"Saved name mapping to {name_map_output_path}")
    
    # Show results
    print(f"\nMapping results:")
    print(f"  Total mappings: {len(name_map_df)}")
    print(f"  Arizona teams: {len(name_map_df[name_map_df['team_id'].str.startswith('non_az_') == False])}")
    print(f"  Non-Arizona teams: {len(name_map_df[name_map_df['team_id'].str.startswith('non_az_')])}")
    
    print("\nSample Arizona team mappings:")
    az_teams = name_map_df[name_map_df['team_id'].str.startswith('non_az_') == False]
    for _, row in az_teams.head(5).iterrows():
        print(f"  {row['raw_name']} -> {row['team_id']} ({row['display_name']})")
    
    print("\nSample non-Arizona team mappings:")
    non_az_teams = name_map_df[name_map_df['team_id'].str.startswith('non_az_')]
    for _, row in non_az_teams.head(5).iterrows():
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
        mapping_df = rebuild_arizona_name_mapping_permissive()
        print(f"\nSuccessfully created Arizona U11 name mapping with {len(mapping_df)} entries")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
