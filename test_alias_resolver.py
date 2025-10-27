#!/usr/bin/env python3
"""
Test script for AliasResolver functionality
"""

import pandas as pd
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sophisticated_team_matcher import SophisticatedTeamMatcher
from src.identity.alias_resolver import AliasResolver

def test_alias_resolver():
    """Test the alias resolver with a small sample"""
    print("=== TESTING ALIAS RESOLVER ===")
    
    # Load U10 master team list
    u10_master_path = 'data/input/National_Male_U10_Master_Team_List.csv'
    if not os.path.exists(u10_master_path):
        print(f"❌ U10 master team list not found: {u10_master_path}")
        return
    
    master_df = pd.read_csv(u10_master_path)
    print(f"✅ Loaded U10 master team list: {len(master_df)} teams")
    
    # Initialize matcher and resolver
    matcher = SophisticatedTeamMatcher()
    resolver = AliasResolver(
        master_df=master_df,
        matcher=matcher,
        alias_csv_path='data/mappings/test_alias_table.csv',
        threshold=0.82,
        dry_run=False
    )
    
    # Test with some sample team names
    test_teams = [
        "AZ Arsenal 16 Boys Teal OC",
        "PRFC Scottsdale 16B Predator", 
        "Next Level Soccer Southeast 2015 boys black",
        "Southeast 2015 boys black",
        "Some Random Team Name"
    ]
    
    print("\n=== TESTING TEAM RESOLUTION ===")
    for team_name in test_teams:
        canonical_id, canonical_name = resolver.resolve(team_name)
        print(f"'{team_name}' -> '{canonical_name}' (ID: {canonical_id})")
    
    # Show stats
    stats = resolver.get_stats()
    print(f"\n=== RESOLVER STATS ===")
    print(f"Cached aliases: {stats['cached_aliases']}")
    print(f"New aliases: {stats['new_aliases']}")
    print(f"Total aliases: {stats['total_aliases']}")
    
    # Flush to save test aliases
    resolver.flush()
    print("✅ Test aliases saved")

if __name__ == "__main__":
    test_alias_resolver()
