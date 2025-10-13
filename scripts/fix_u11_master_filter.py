#!/usr/bin/env python3
"""
Fix U11 Master Teams - Filter to Only U11 Teams
===============================================

The current master file includes teams from all age groups (8,293 teams).
We need to filter it to only include actual U11 teams (~78 teams).
"""

import pandas as pd
from pathlib import Path

def fix_u11_master():
    """Filter master teams to only include U11 teams."""
    
    print("Fixing U11 Master Teams")
    print("=" * 40)
    
    # Load current master (has all age groups)
    master_path = Path("data/master/az_boys_u11_2025/master_teams.csv")
    master = pd.read_csv(master_path)
    print(f"Current master: {len(master)} teams (all age groups)")
    
    # Load bronze U11 teams (correct U11 teams)
    bronze_path = Path("data/bronze/AZ MALE u11 MASTER TEAM LIST.csv")
    bronze = pd.read_csv(bronze_path)
    print(f"Bronze U11 teams: {len(bronze)} teams")
    
    # Get the correct U11 team IDs
    u11_team_ids = set(bronze["team_id"].astype(str))
    print(f"U11 team IDs to keep: {len(u11_team_ids)}")
    
    # Filter master to only include U11 teams
    master["gotsport_team_id_str"] = master["gotsport_team_id"].astype(str)
    u11_master = master[master["gotsport_team_id_str"].isin(u11_team_ids)].copy()
    
    print(f"Filtered master: {len(u11_master)} U11 teams")
    
    # Remove the temporary column
    u11_master = u11_master.drop("gotsport_team_id_str", axis=1)
    
    # Create backup
    backup_path = Path("data/master/az_boys_u11_2025/master_teams_all_ages_backup.csv")
    master.to_csv(backup_path, index=False)
    print(f"Created backup: {backup_path}")
    
    # Save filtered master
    u11_master.to_csv(master_path, index=False)
    print(f"Saved filtered U11 master: {master_path}")
    
    # Show sample teams
    print("\nSample U11 teams:")
    for _, row in u11_master.head(10).iterrows():
        print(f"  {row['gotsport_team_id']}: {row['display_name']}")
    
    return len(u11_master)

if __name__ == "__main__":
    team_count = fix_u11_master()
    print(f"\n✅ Fixed! U11 master now has {team_count} teams")
