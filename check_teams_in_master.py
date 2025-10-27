#!/usr/bin/env python3
"""
Check if specific teams are in master lists
"""

import pandas as pd
import os

def check_teams_in_master():
    """Check if specific teams are in master lists"""
    print("=== CHECKING IF TEAMS ARE IN MASTER LISTS ===")
    
    # Load master lists
    u10_master_path = 'data/input/National_Male_U10_Master_Team_List.csv'
    u11_master_path = 'data/input/National_Male_U11_Master_Team_List.csv'
    
    u10_master_df = pd.read_csv(u10_master_path)
    u11_master_df = pd.read_csv(u11_master_path)
    
    # Combine master lists
    combined_master_df = pd.concat([u10_master_df, u11_master_df], ignore_index=True)
    master_teams = combined_master_df['Team_Name'].tolist()
    
    print(f"Combined master teams: {len(master_teams)}")
    
    # Test teams
    test_teams = [
        "AZ Arsenal 16 Boys Teal OC",
        "PRFC Scottsdale 16B Predator",
        "CJFA MetroStars 16B",
        "Riptide Black 2016B"
    ]
    
    for team_name in test_teams:
        print(f"\n=== CHECKING: '{team_name}' ===")
        
        # Check if exact match exists
        if team_name in master_teams:
            print(f"✅ Exact match found!")
        else:
            print(f"❌ No exact match found")
            
            # Search for partial matches
            partial_matches = []
            for master_team in master_teams:
                if pd.isna(master_team):
                    continue
                if team_name.lower() in master_team.lower() or master_team.lower() in team_name.lower():
                    partial_matches.append(master_team)
            
            if partial_matches:
                print(f"Found {len(partial_matches)} partial matches:")
                for i, match in enumerate(partial_matches[:5]):
                    print(f"  {i+1}. {match}")
            else:
                print("No partial matches found")
                
                # Search for teams with similar words
                team_words = set(team_name.lower().split())
                word_matches = []
                for master_team in master_teams:
                    if pd.isna(master_team):
                        continue
                    master_words = set(master_team.lower().split())
                    common_words = team_words.intersection(master_words)
                    if len(common_words) >= 2:  # At least 2 common words
                        word_matches.append((master_team, len(common_words)))
                
                if word_matches:
                    word_matches.sort(key=lambda x: x[1], reverse=True)
                    print(f"Found {len(word_matches)} word matches:")
                    for i, (match, count) in enumerate(word_matches[:5]):
                        print(f"  {i+1}. {match} ({count} common words)")

if __name__ == "__main__":
    check_teams_in_master()
