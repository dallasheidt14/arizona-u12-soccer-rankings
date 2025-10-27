#!/usr/bin/env python3
"""
Debug find_best_match method
"""

import pandas as pd
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sophisticated_team_matcher import SophisticatedTeamMatcher

def debug_find_best_match():
    """Debug the find_best_match method"""
    print("=== DEBUGGING FIND_BEST_MATCH METHOD ===")
    
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
    
    # Test with a team that should have matches
    team_name = "AZ Arsenal 16 Boys Teal OC"
    print(f"\n=== TESTING: '{team_name}' ===")
    
    # Parse the team name
    team1_parsed = matcher.parse_team_name(team_name)
    print(f"Parsed: {team1_parsed}")
    
    if not team1_parsed.get('birth_year') or not team1_parsed.get('gender'):
        print("❌ Missing birth year or gender")
        return
    
    print(f"✅ Birth year: {team1_parsed['birth_year']}, Gender: {team1_parsed['gender']}")
    
    # Manually implement find_best_match logic
    best_match = None
    best_score = 0.0
    threshold = 0.8
    
    matches_found = 0
    for i, master_team in enumerate(master_teams):
        if pd.isna(master_team) or master_team == team_name:
            continue
        
        team2_parsed = matcher.parse_team_name(master_team)
        if not team2_parsed.get('birth_year') or not team2_parsed.get('gender'):
            continue
        
        similarity = matcher.calculate_similarity(team1_parsed, team2_parsed)
        
        if similarity > 0.5:  # Show any reasonable similarity
            matches_found += 1
            print(f"  Match {matches_found}: '{master_team}' -> similarity: {similarity:.3f}")
        
        if similarity > best_score and similarity >= threshold:
            best_score = similarity
            best_match = master_team
    
    print(f"\nTotal matches found: {matches_found}")
    print(f"Best match: '{best_match}' (score: {best_score:.3f})")
    
    # Test the actual find_best_match method
    actual_best = matcher.find_best_match(team_name, master_teams, threshold=0.8)
    print(f"Actual find_best_match result: '{actual_best}'")

if __name__ == "__main__":
    debug_find_best_match()
