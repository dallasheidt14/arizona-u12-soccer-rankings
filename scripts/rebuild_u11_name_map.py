#!/usr/bin/env python3
"""
Rebuild U11 name mapping using the new master list.
Maps raw game names to team_id and display_name.
"""

import pandas as pd
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.name_map_builder import build_name_map

def rebuild_name_mapping():
    """Rebuild name mapping with new master list."""
    
    # Load new master list
    master_path = Path("data/master/az_boys_u11_2025/master_teams.csv")
    if not master_path.exists():
        raise FileNotFoundError(f"Master list not found: {master_path}")
    
    print(f"Loading master list from {master_path}")
    master_df = pd.read_csv(master_path)
    print(f"Master list has {len(master_df)} teams")
    
    # Load games data to get observed names
    games_path = Path("data/gold/Matched_Games_U11_CLEAN.csv")
    if not games_path.exists():
        raise FileNotFoundError(f"Games data not found: {games_path}")
    
    print(f"Loading games data from {games_path}")
    games_df = pd.read_csv(games_path)
    
    # Extract observed team names
    team_a_names = games_df["Team A"].dropna()
    team_b_names = games_df["Team B"].dropna()
    observed_names = pd.concat([team_a_names, team_b_names]).drop_duplicates()
    
    print(f"Found {len(observed_names)} unique observed team names")
    
    # Build name mapping
    print("Building name mapping...")
    try:
        name_map_df = build_name_map(master_df, observed_names, "az_boys_u11_2025")
        
        # Save name mapping
        output_path = Path("data/mappings/az_boys_u11_2025/name_map.csv")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        name_map_df.to_csv(output_path, index=False)
        print(f"Saved name mapping to {output_path}")
        
        # Show sample mappings
        print("\nSample mappings:")
        for i, row in name_map_df.head(10).iterrows():
            print(f"  {row['raw_name']} -> {row['team_id']} ({row['display_name']})")
        
        # Check for Next Level Soccer mapping
        next_level = name_map_df[name_map_df["raw_name"].str.contains("next level", case=False, na=False)]
        if not next_level.empty:
            print(f"\nNext Level Soccer mapping:")
            print(f"  {next_level.iloc[0]['raw_name']} -> {next_level.iloc[0]['team_id']} ({next_level.iloc[0]['display_name']})")
        else:
            print("\nWARNING: Next Level Soccer not found in name mapping")
        
        # Check for any unmatched teams
        unmatched_path = Path("data/logs/UNMATCHED_AZ_BOYS_U11_2025.csv")
        if unmatched_path.exists():
            unmatched_df = pd.read_csv(unmatched_path)
            if len(unmatched_df) > 0:
                print(f"\nWARNING: {len(unmatched_df)} unmatched teams found in {unmatched_path}")
                print("First few unmatched teams:")
                for i, row in unmatched_df.head(5).iterrows():
                    print(f"  {row['raw_name']}")
            else:
                print(f"\nAll teams matched successfully!")
        else:
            print(f"\nNo unmatched teams log found - all teams matched!")
        
        return name_map_df
        
    except Exception as e:
        print(f"Error building name mapping: {e}")
        raise

if __name__ == "__main__":
    try:
        name_map_df = rebuild_name_mapping()
        print(f"\nSuccessfully created name mapping with {len(name_map_df)} entries")
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
