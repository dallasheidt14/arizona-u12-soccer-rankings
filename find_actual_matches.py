#!/usr/bin/env python3
"""
Test to find actual matches in master lists
"""

import pandas as pd
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sophisticated_team_matcher import SophisticatedTeamMatcher

def find_actual_matches():
    """Find actual matches in master lists"""
    print("=== FINDING ACTUAL MATCHES IN MASTER LISTS ===")
    
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
        "PRFC Scottsdale 16B Predator"
    ]
    
    for team_name in test_teams:
        print(f"\n=== SEARCHING FOR: '{team_name}' ===")
        
        # Parse the team name
        parsed = matcher.parse_team_name(team_name)
        print(f"Parsed: {parsed}")
        
        # Search for teams with similar names in master list
        search_terms = []
        if parsed.get('club'):
            search_terms.extend(parsed['club'].split())
        if parsed.get('state'):
            search_terms.append(parsed['state'])
        
        print(f"Search terms: {search_terms}")
        
        # Find teams that contain any of the search terms
        potential_matches = []
        for master_team in master_teams:
            if pd.isna(master_team):
                continue
            master_lower = master_team.lower()
            for term in search_terms:
                if term.lower() in master_lower:
                    potential_matches.append(master_team)
                    break
        
        print(f"Found {len(potential_matches)} potential matches")
        
        # Show first 10 potential matches
        for i, match in enumerate(potential_matches[:10]):
            print(f"  {i+1}. {match}")
        
        # Test similarity with first few potential matches
        if potential_matches:
            print(f"\nTesting similarity with first 5 potential matches:")
            for i, master_team in enumerate(potential_matches[:5]):
                master_parsed = matcher.parse_team_name(master_team)
                similarity = matcher.calculate_similarity(parsed, master_parsed)
                print(f"  {i+1}. '{master_team}' -> similarity: {similarity:.3f}")

if __name__ == "__main__":
    find_actual_matches()
