"""
Verify that gold and master team lists are aligned.
Catches mismatches in <1 second.
"""
import sys
import pandas as pd
from utils.team_normalizer import canonicalize_team_name

def verify_alignment(gold_path: str, master_path: str):
    """Check that all teams in gold exist in master and vice versa."""
    g = pd.read_csv(gold_path)
    m = pd.read_csv(master_path)
    
    # Get canonical keys from gold
    g_team_a = g["Team A"].astype(str).str.strip().map(canonicalize_team_name)
    g_team_b = g["Team B"].astype(str).str.strip().map(canonicalize_team_name)
    gkeys = set(g_team_a).union(set(g_team_b))
    
    # Get canonical keys from master
    mkeys = set(m["Team Name"].astype(str).str.strip().map(canonicalize_team_name))
    
    missing_in_master = sorted(gkeys - mkeys)[:25]
    missing_in_gold = sorted(mkeys - gkeys)[:25]
    
    print(f"Gold teams: {len(gkeys)} | Master teams: {len(mkeys)}")
    
    if missing_in_master:
        print(f"ERROR: {len(missing_in_master)} teams in gold but not in master (sample):")
        print(missing_in_master)
    
    if missing_in_gold:
        print(f"WARNING: {len(missing_in_gold)} teams in master but not in gold (sample):")
        print(missing_in_gold)
    
    if missing_in_master or missing_in_gold:
        sys.exit(2)
    
    print("SUCCESS: Alignment verified: all teams match")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python -m utils.verify_alignment <gold_csv> <master_csv>")
        sys.exit(1)
    
    verify_alignment(sys.argv[1], sys.argv[2])
