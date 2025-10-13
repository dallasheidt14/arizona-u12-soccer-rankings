#!/usr/bin/env python3
"""
Organize U11 Teams by State
===========================

Takes the master U11 teams file and splits it by state into separate folders.
CAN and CAS are both California - keep them together.
"""

import pandas as pd
from pathlib import Path
import sys

def organize_u11_teams_by_state():
    """Split U11 master teams by state into organized folders."""
    
    print("Organizing U11 Teams by State")
    print("=" * 40)
    
    # Find the latest U11 teams file
    master_dir = Path("data/Master/U11 BOYS/ALL STATES")
    if not master_dir.exists():
        print(f"[ERROR] Master directory not found: {master_dir}")
        return False
    
    # Find the latest file
    csv_files = list(master_dir.glob("all_u11_teams_*.csv"))
    if not csv_files:
        print(f"[ERROR] No U11 teams files found in {master_dir}")
        return False
    
    # Get the most recent file
    latest_file = max(csv_files, key=lambda f: f.stat().st_mtime)
    print(f"[INFO] Using file: {latest_file}")
    
    try:
        # Load the master file
        df = pd.read_csv(latest_file)
        print(f"[INFO] Loaded {len(df):,} teams")
        
        # Create base output directory
        base_dir = Path("data/master/U11 BOYS")
        base_dir.mkdir(parents=True, exist_ok=True)
        
        # Group by state
        state_groups = df.groupby('state')
        
        print(f"[INFO] Found {len(state_groups)} states/regions")
        
        # Process each state
        for state, state_df in state_groups:
            # Clean state name for folder
            clean_state = state.replace(':', '_').replace('/', '_')
            
            # Create state folder
            state_dir = base_dir / clean_state
            state_dir.mkdir(parents=True, exist_ok=True)
            
            # Save state file
            state_file = state_dir / f"{clean_state}_teams.csv"
            state_df.to_csv(state_file, index=False)
            
            print(f"[OK] {state}: {len(state_df):,} teams -> {state_file}")
        
        # Create summary
        print(f"\n[SUMMARY]")
        print(f"Total teams: {len(df):,}")
        print(f"States processed: {len(state_groups)}")
        print(f"Output directory: {base_dir}")
        
        # Show top 10 states by team count
        state_counts = df['state'].value_counts().head(10)
        print(f"\nTop 10 states by team count:")
        for state, count in state_counts.items():
            print(f"  {state}: {count:,} teams")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to organize teams: {e}")
        return False

if __name__ == "__main__":
    success = organize_u11_teams_by_state()
    sys.exit(0 if success else 1)
