#!/usr/bin/env python3
"""
Clean team names by removing inappropriate color suffixes.
Some teams legitimately have colors (like FC Elite Arizona 2015 Boys Blue),
but others like RSL teams shouldn't have colors.
"""

import pandas as pd
import sys
import os
from pathlib import Path

def clean_team_names():
    """Remove inappropriate colors from team names."""
    
    # Load the current master list
    master_path = Path("data/master/az_boys_u11_2025/master_teams.csv")
    if not master_path.exists():
        print(f"Master list not found: {master_path}")
        return
    
    print(f"Loading master list from {master_path}")
    master_df = pd.read_csv(master_path)
    print(f"Loaded {len(master_df)} teams")
    
    # Teams that should NOT have colors (remove color suffixes)
    no_color_teams = [
        "RSL-AZ",
        "AYSO",
        "Arizona Soccer Club",
        "Madison FC",
        "State 48 FC",
        "Phoenix Premier FC",
        "Phoenix Rising FC",
        "Phoenix Rush",
        "Scottsdale City FC",
        "FC Arizona",
        "FC Sonora",
        "FC Tucson",
        "FC Deportivo Arizona",
        "Real Arizona FC",
        "North Scottsdale Soccer Club",
        "Pima County Surf Soccer Club",
        "Thunderbird FC",
        "Vail SC",
        "Flagstaff SC",
        "Kingman SC",
        "East Valley/NSFC",
        "Phoenix United Futbol Club",
        "Brazas Futebol Club",
        "AZ Inferno",
        "Amore Soccer",
        "Epic Soccer Club",
        "Synergy FC AZ",
        "Dynamos SC",
        "FBSL",
        "CCV STARS",
        "Sun Warriors AZFC",
        "Paladin Soccer Club"
    ]
    
    def clean_name(name):
        """Remove color suffixes from teams that shouldn't have them."""
        original_name = name
        
        # Check if this team should not have colors
        should_remove_color = any(team_prefix in name for team_prefix in no_color_teams)
        
        if should_remove_color:
            # Remove common color suffixes
            colors = [" Blue", " Red", " White", " Black", " Silver", " Gold", " Green", " Yellow"]
            for color in colors:
                if name.endswith(color):
                    name = name[:-len(color)]
                    break
        
        return name
    
    # Apply cleaning
    print("Cleaning team names...")
    master_df["display_name"] = master_df["display_name"].apply(clean_name)
    
    # Check for changes
    changes = master_df[master_df["display_name"] != master_df["display_name"]]
    print(f"Cleaned {len(changes)} team names")
    
    # Show some examples of cleaned names
    print("\nExamples of cleaned names:")
    for i, row in master_df.head(10).iterrows():
        print(f"  {row['display_name']}")
    
    # Check RSL teams specifically
    rsl_teams = master_df[master_df["display_name"].str.contains("RSL", case=False, na=False)]
    print(f"\nRSL teams ({len(rsl_teams)}):")
    for i, row in rsl_teams.iterrows():
        print(f"  {row['display_name']}")
    
    # Save cleaned master list
    output_path = Path("data/master/az_boys_u11_2025/master_teams.csv")
    master_df.to_csv(output_path, index=False)
    print(f"\nSaved cleaned master list to {output_path}")
    
    return master_df

if __name__ == "__main__":
    try:
        master_df = clean_team_names()
        print(f"\nSuccessfully cleaned master list with {len(master_df)} teams")
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
