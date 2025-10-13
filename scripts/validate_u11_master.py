#!/usr/bin/env python3
"""
U11 Master Teams Validation Script
=================================

Validates the U11 master teams file schema and data quality.
Checks for required columns, nulls, duplicates, and reports stats.
"""

import pandas as pd
import sys
from pathlib import Path

def validate_u11_master():
    """Validate U11 master teams file."""
    master_path = Path("data/master/az_boys_u11_2025/master_teams.csv")
    
    print("U11 Master Teams Validation")
    print("=" * 40)
    print(f"Checking: {master_path}")
    
    if not master_path.exists():
        print(f"[ERROR] Master file not found at {master_path}")
        return False
    
    try:
        master = pd.read_csv(master_path)
        print(f"[OK] Loaded {len(master):,} rows")
        
        # Check required columns
        required_cols = {"gotsport_team_id", "display_name"}
        missing_cols = required_cols - set(master.columns)
        
        if missing_cols:
            print(f"[ERROR] Missing required columns: {missing_cols}")
            print(f"Available columns: {list(master.columns)}")
            return False
        
        print(f"[OK] Required columns present: {required_cols}")
        
        # Check for nulls in key columns
        null_team_ids = master["gotsport_team_id"].isnull().sum()
        null_display_names = master["display_name"].isnull().sum()
        
        if null_team_ids > 0:
            print(f"[ERROR] {null_team_ids} null team_id values")
            return False
        
        if null_display_names > 0:
            print(f"[ERROR] {null_display_names} null display_name values")
            return False
        
        print("[OK] No null values in key columns")
        
        # Check for duplicate team IDs
        duplicate_ids = master[master["gotsport_team_id"].duplicated(keep=False)]
        if not duplicate_ids.empty:
            print(f"[ERROR] {len(duplicate_ids)} duplicate team_id values:")
            print(duplicate_ids[["gotsport_team_id", "display_name"]].to_string())
            return False
        
        print("[OK] No duplicate team IDs")
        
        # Report stats
        print("\nMaster Stats:")
        print(f"  Total teams: {len(master):,}")
        
        if "club" in master.columns:
            unique_clubs = master["club"].nunique()
            print(f"  Unique clubs: {unique_clubs}")
        
        if "state" in master.columns:
            state_counts = master["state"].value_counts()
            print(f"  States: {dict(state_counts)}")
        
        if "age_group" in master.columns:
            age_counts = master["age_group"].value_counts()
            print(f"  Age groups: {dict(age_counts)}")
        
        if "gender" in master.columns:
            gender_counts = master["gender"].value_counts()
            print(f"  Gender: {dict(gender_counts)}")
        
        print("\n[OK] Master validation passed!")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to process master file: {e}")
        return False

if __name__ == "__main__":
    success = validate_u11_master()
    sys.exit(0 if success else 1)
