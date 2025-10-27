#!/usr/bin/env python3
"""
Detailed test of sophisticated matcher to understand why it's not finding matches
"""

import pandas as pd
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sophisticated_team_matcher import SophisticatedTeamMatcher

def test_sophisticated_matcher():
    """Test the sophisticated matcher in detail"""
    print("=== TESTING SOPHISTICATED MATCHER IN DETAIL ===")
    
    # Load master lists
    u10_master_path = 'data/input/National_Male_U10_Master_Team_List.csv'
    u11_master_path = 'data/input/National_Male_U11_Master_Team_List.csv'
    
    u10_master_df = pd.read_csv(u10_master_path)
    u11_master_df = pd.read_csv(u11_master_path)
    
    # Combine master lists
    combined_master_df = pd.concat([u10_master_df, u11_master_df], ignore_index=True)
    master_teams = combined_master_df['Team_Name'].tolist()
    
    print(f"Combined master teams: {len(master_teams)}")
    
    # Initialize matcher
    matcher = SophisticatedTeamMatcher()
    
    # Test with some specific team names
    test_teams = [
        "AZ Arsenal 16 Boys Teal OC",
        "PRFC Scottsdale 16B Predator",
        "CJFA MetroStars 16B",
        "Riptide Black 2016B"
    ]
    
    for team_name in test_teams:
        print(f"\n=== TESTING: '{team_name}' ===")
        
        # Parse the team name
        parsed = matcher.parse_team_name(team_name)
        print(f"Parsed: {parsed}")
        
        # Check if it has required fields
        if not parsed.get('birth_year'):
            print("❌ No birth year found")
            continue
        if not parsed.get('gender'):
            print("❌ No gender found")
            continue
            
        print(f"✅ Birth year: {parsed['birth_year']}, Gender: {parsed['gender']}")
        
        # Try to find matches
        matches_found = 0
        for master_team in master_teams[:1000]:  # Test first 1000 master teams
            if pd.isna(master_team) or master_team == team_name:
                continue
                
            master_parsed = matcher.parse_team_name(master_team)
            if not master_parsed.get('birth_year') or not master_parsed.get('gender'):
                continue
                
            similarity = matcher.calculate_similarity(parsed, master_parsed)
            if similarity > 0.5:  # Show any reasonable similarity
                print(f"  Similarity {similarity:.3f}: '{master_team}'")
                matches_found += 1
                
        print(f"Found {matches_found} potential matches")
        
        # Try the actual find_best_match method
        best_match = matcher.find_best_match(team_name, master_teams, threshold=0.8)
        if best_match:
            print(f"✅ Best match: '{best_match}'")
        else:
            print("❌ No match found above threshold")
            
            # Try with lower threshold
            best_match_low = matcher.find_best_match(team_name, master_teams, threshold=0.5)
            if best_match_low:
                print(f"✅ Best match (low threshold): '{best_match_low}'")
            else:
                print("❌ No match found even with low threshold")

if __name__ == "__main__":
    test_sophisticated_matcher()
