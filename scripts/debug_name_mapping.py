#!/usr/bin/env python3
"""Debug script to test name mapping."""

import pandas as pd
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.name_map_builder import build_name_map

def debug_name_mapping():
    """Debug the name mapping issue."""
    
    # Load data
    master = pd.read_csv("data/master/az_boys_u11_2025/master_teams.csv")
    games = pd.read_csv("data/gold/Matched_Games_U11_CLEAN.csv")
    observed = pd.concat([games["Team A"], games["Team B"]]).drop_duplicates()
    
    print(f"Master teams: {len(master)}")
    print(f"Observed teams: {len(observed)}")
    
    # Check Academy teams specifically
    academy_master = master[master["display_name"].str.contains("Academy", case=False, na=False)]
    academy_observed = observed[observed.str.contains("Academy", case=False, na=False)]
    
    print(f"Academy in master: {len(academy_master)}")
    print(f"Academy in observed: {len(academy_observed)}")
    
    # Show first few Academy teams
    print("\nAcademy teams in master:")
    for name in academy_master["display_name"].head(3):
        print(f"  {name}")
    
    print("\nAcademy teams in observed:")
    for name in academy_observed.head(3):
        print(f"  {name}")
    
    # Try the mapping
    try:
        result = build_name_map(master, observed, "az_boys_u11_2025")
        print(f"\nSuccess! Mapped {len(result)} teams")
    except Exception as e:
        print(f"\nError: {e}")
        
        # Check the unmatched file
        unmatched_path = Path("data/logs/UNMATCHED_AZ_BOYS_U11_2025.csv")
        if unmatched_path.exists():
            unmatched = pd.read_csv(unmatched_path)
            print(f"\nUnmatched teams ({len(unmatched)}):")
            for name in unmatched["raw_name"].head(5):
                print(f"  {name}")

if __name__ == "__main__":
    debug_name_mapping()
