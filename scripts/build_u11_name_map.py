#!/usr/bin/env python3
"""
Build name mapping for U11 teams.

This script creates a mapping from raw team names in game data to stable team IDs
from the master list, with validation and error logging.
"""
import pandas as pd
from pathlib import Path
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.name_map_builder import build_name_map, save_name_map, validate_name_map


def main():
    """Build U11 name mapping."""
    
    # Configuration
    division_key = "az_boys_u11_2025"
    master_file = "data/master/az_boys_u11_2025/master_teams.csv"
    games_file = "data/gold/Matched_Games_U11_CLEAN.csv"
    output_file = "data/mappings/az_boys_u11_2025/name_map.csv"
    
    print(f"Building U11 name mapping...")
    print(f"Division key: {division_key}")
    print(f"Master file: {master_file}")
    print(f"Games file: {games_file}")
    print(f"Output file: {output_file}")
    
    # Load master list
    if not Path(master_file).exists():
        raise FileNotFoundError(f"Master file not found: {master_file}")
    
    master_df = pd.read_csv(master_file)
    print(f"Loaded {len(master_df)} teams from master list")
    
    # Load games data
    if not Path(games_file).exists():
        raise FileNotFoundError(f"Games file not found: {games_file}")
    
    games_df = pd.read_csv(games_file)
    print(f"Loaded {len(games_df)} games from games data")
    
    # Get all unique team names from games data
    team_a_names = games_df["Team A"].dropna().unique()
    team_b_names = games_df["Team B"].dropna().unique()
    all_team_names = pd.Series(list(team_a_names) + list(team_b_names)).unique()
    
    print(f"Found {len(all_team_names)} unique team names in games data")
    
    # Build name mapping
    print("Building name mapping...")
    try:
        name_map_df = build_name_map(master_df, pd.Series(all_team_names), division_key)
        print(f"Successfully mapped {len(name_map_df)} team names")
        
        # Validate mapping
        stats = validate_name_map(name_map_df)
        print(f"Mapping validation:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # Save mapping
        save_name_map(name_map_df, division_key)
        print(f"Saved name mapping to: {output_file}")
        
        # Display sample
        print("\nSample mappings:")
        print(name_map_df.head(10))
        
        print(f"\nSuccessfully built U11 name mapping with {len(name_map_df)} entries")
        
    except RuntimeError as e:
        print(f"Error building name mapping: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
