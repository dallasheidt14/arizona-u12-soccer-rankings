#!/usr/bin/env python3
"""
Generate U11 master list with team IDs.

This script reads the existing U11 master list and adds stable team IDs
using the canonical team names and division key.
"""
import pandas as pd
from pathlib import Path
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.id_codec import make_team_id


def main():
    """Generate U11 master list with team IDs."""
    
    # Configuration
    division_key = "az_boys_u11_2025"
    input_file = "AZ MALE u11 MASTER TEAM LIST.csv"
    output_file = "data/master/az_boys_u11_2025/master_teams.csv"
    
    print(f"Generating U11 master list with team IDs...")
    print(f"Division key: {division_key}")
    print(f"Input file: {input_file}")
    print(f"Output file: {output_file}")
    
    # Read existing master list
    if not Path(input_file).exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    df = pd.read_csv(input_file)
    print(f"Loaded {len(df)} teams from master list")
    
    # Rename columns to standard format
    df = df.rename(columns={
        "Team": "display_name",
        "Club": "club"
    })
    
    # Generate team IDs
    print("Generating team IDs...")
    df["team_id"] = df["display_name"].apply(
        lambda x: make_team_id(x, division_key)
    )
    
    # Verify all IDs are unique
    if df["team_id"].duplicated().any():
        duplicates = df[df["team_id"].duplicated()]["display_name"].tolist()
        raise ValueError(f"Duplicate team IDs generated for: {duplicates}")
    
    print(f"Generated {len(df)} unique team IDs")
    
    # Reorder columns
    df = df[["team_id", "display_name", "club"]]
    
    # Create output directory
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save master list
    df.to_csv(output_file, index=False)
    print(f"Saved master list to: {output_file}")
    
    # Display sample
    print("\nSample entries:")
    print(df.head())
    
    print(f"\nSuccessfully generated U11 master list with {len(df)} teams")


if __name__ == "__main__":
    main()
