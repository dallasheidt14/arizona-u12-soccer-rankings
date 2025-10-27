#!/usr/bin/env python3
"""
Test U10 Rankings Generator with Alias System (Small Sample)
============================================================

This script tests the alias system with a small sample of teams to verify
it works correctly before running on the full dataset.
"""

import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Import sophisticated team matcher and alias resolver
from sophisticated_team_matcher import SophisticatedTeamMatcher
from src.identity.alias_resolver import AliasResolver

class TestU10RankingsGenerator:
    """Test U10 rankings with alias-based sophisticated team matching (small sample)"""
    
    def __init__(self):
        self.u10_master_df = None
        self.u11_master_df = None
        self.u10_games_df = None
        self.matcher = SophisticatedTeamMatcher()
        self.resolver = None
        
    def load_data(self):
        """Load all required data files"""
        print("=== LOADING DATA ===")
        
        # Load U10 master team list
        u10_master_path = 'data/input/National_Male_U10_Master_Team_List.csv'
        if os.path.exists(u10_master_path):
            self.u10_master_df = pd.read_csv(u10_master_path)
            print(f"✅ Loaded U10 master team list: {len(self.u10_master_df)} teams")
        else:
            print(f"❌ U10 master team list not found: {u10_master_path}")
            return False
        
        # Load U11 master team list (for cross-age games)
        u11_master_path = 'data/input/National_Male_U11_Master_Team_List.csv'
        if os.path.exists(u11_master_path):
            self.u11_master_df = pd.read_csv(u11_master_path)
            print(f"✅ Loaded U11 master team list: {len(self.u11_master_df)} teams")
        else:
            print(f"❌ U11 master team list not found: {u11_master_path}")
            return False
        
        # Load U10 game history
        games_path = 'data/Game History u10 and u11.csv'
        if os.path.exists(games_path):
            self.u10_games_df = pd.read_csv(games_path)
            # Clean column names
            self.u10_games_df.columns = self.u10_games_df.columns.str.strip()
            print(f"✅ Loaded game history: {len(self.u10_games_df)} games")
        else:
            print(f"❌ Game history not found: {games_path}")
            return False
        
        # Initialize alias resolver after loading master lists
        print("🔄 Initializing alias resolver...")
        
        # Combine U10 and U11 master lists for comprehensive matching
        combined_master_df = pd.concat([
            self.u10_master_df,
            self.u11_master_df
        ], ignore_index=True)
        
        self.resolver = AliasResolver(
            master_df=combined_master_df,
            matcher=self.matcher,
            alias_csv_path='data/mappings/test_alias_table.csv',
            threshold=0.82,
            dry_run=False
        )
        
        stats = self.resolver.get_stats()
        print(f"✅ Alias resolver initialized: {stats['cached_aliases']} cached aliases")
        
        return True
    
    def test_alias_matching(self):
        """Test alias matching with a small sample"""
        print("\n=== TESTING ALIAS MATCHING ===")
        
        # Get a small sample of teams from game history
        sample_teams = self.u10_games_df['Team A'].dropna().unique()[:50]  # First 50 teams
        print(f"Testing with {len(sample_teams)} sample teams")
        
        matches_found = 0
        for team_name in sample_teams:
            canonical_id, canonical_name = self.resolver.resolve(team_name)
            if canonical_name != team_name:
                print(f"✅ MATCH: '{team_name}' -> '{canonical_name}'")
                matches_found += 1
            else:
                print(f"❌ NO MATCH: '{team_name}'")
        
        print(f"\nMatches found: {matches_found}/{len(sample_teams)} ({matches_found/len(sample_teams)*100:.1f}%)")
        
        # Show resolver stats
        stats = self.resolver.get_stats()
        print(f"\n=== RESOLVER STATS ===")
        print(f"Cached aliases: {stats['cached_aliases']}")
        print(f"New aliases: {stats['new_aliases']}")
        print(f"Total aliases: {stats['total_aliases']}")
        
        # Flush new aliases
        print("\n🔄 Saving new aliases...")
        self.resolver.flush()
        
        return matches_found > 0

def main():
    """Main function"""
    print("=== TEST U10 RANKINGS GENERATOR WITH ALIAS SYSTEM ===")
    
    generator = TestU10RankingsGenerator()
    
    # Load data
    if not generator.load_data():
        print("❌ Failed to load data")
        return None
    
    # Test alias matching
    if generator.test_alias_matching():
        print("✅ Alias matching test passed!")
    else:
        print("❌ Alias matching test failed!")
        return None
    
    print("✅ Test completed successfully!")

if __name__ == "__main__":
    main()
