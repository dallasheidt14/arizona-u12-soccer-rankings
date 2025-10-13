#!/usr/bin/env python3
"""
U11 Master Teams Deduplication Script
====================================

Removes duplicate rows from the U11 master teams file.
Keeps the first occurrence of each team_id.
"""

import pandas as pd
import sys
from pathlib import Path

def deduplicate_u11_master():
    """Remove duplicates from U11 master teams file."""
    master_path = Path("data/master/az_boys_u11_2025/master_teams.csv")
    backup_path = Path("data/master/az_boys_u11_2025/master_teams_backup.csv")
    
    print("U11 Master Teams Deduplication")
    print("=" * 40)
    print(f"Processing: {master_path}")
    
    if not master_path.exists():
        print(f"[ERROR] Master file not found at {master_path}")
        return False
    
    try:
        # Load master file
        master = pd.read_csv(master_path)
        original_count = len(master)
        print(f"[INFO] Loaded {original_count:,} rows")
        
        # Check for duplicates
        duplicate_mask = master["gotsport_team_id"].duplicated(keep=False)
        duplicate_count = duplicate_mask.sum()
        
        if duplicate_count == 0:
            print("[OK] No duplicates found")
            return True
        
        print(f"[INFO] Found {duplicate_count:,} duplicate rows")
        
        # Show some examples
        duplicates = master[duplicate_mask].sort_values("gotsport_team_id")
        print("\nDuplicate examples:")
        for team_id in duplicates["gotsport_team_id"].unique()[:5]:
            team_rows = duplicates[duplicates["gotsport_team_id"] == team_id]
            print(f"  Team ID {team_id}: {len(team_rows)} copies")
            for _, row in team_rows.iterrows():
                print(f"    - {row['display_name']}")
        
        # Create backup
        master.to_csv(backup_path, index=False)
        print(f"[INFO] Created backup: {backup_path}")
        
        # Remove duplicates (keep first occurrence)
        master_deduped = master.drop_duplicates(subset=["gotsport_team_id"], keep="first")
        final_count = len(master_deduped)
        removed_count = original_count - final_count
        
        print(f"[INFO] Removed {removed_count:,} duplicate rows")
        print(f"[INFO] Final count: {final_count:,} unique teams")
        
        # Save deduplicated file
        master_deduped.to_csv(master_path, index=False)
        print(f"[OK] Saved deduplicated master to {master_path}")
        
        # Verify no duplicates remain
        verify_master = pd.read_csv(master_path)
        verify_duplicates = verify_master["gotsport_team_id"].duplicated().sum()
        
        if verify_duplicates == 0:
            print("[OK] Verification passed - no duplicates remain")
            return True
        else:
            print(f"[ERROR] Verification failed - {verify_duplicates} duplicates still exist")
            return False
        
    except Exception as e:
        print(f"[ERROR] Failed to process master file: {e}")
        return False

if __name__ == "__main__":
    success = deduplicate_u11_master()
    sys.exit(0 if success else 1)
