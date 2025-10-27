#!/usr/bin/env python3
"""
Investigate team name differences between master list and game history
"""

import pandas as pd
import os

def investigate_team_names():
    """Investigate differences between master list and game history team names"""
    print("=== INVESTIGATING TEAM NAME DIFFERENCES ===")
    
    # Load U10 master team list
    u10_master_path = 'data/input/National_Male_U10_Master_Team_List.csv'
    master_df = pd.read_csv(u10_master_path)
    print(f"✅ Loaded U10 master team list: {len(master_df)} teams")
    
    # Load game history
    games_path = 'data/Game History u10 and u11.csv'
    games_df = pd.read_csv(games_path)
    games_df.columns = games_df.columns.str.strip()
    print(f"✅ Loaded game history: {len(games_df)} games")
    
    # Get unique teams from game history
    game_teams_a = set(games_df['Team A'].dropna().unique())
    game_teams_b = set(games_df['Team B'].dropna().unique())
    all_game_teams = game_teams_a | game_teams_b
    print(f"Unique teams in game history: {len(all_game_teams)}")
    
    # Get teams from master list
    master_teams = set(master_df['Team_Name'].unique())
    print(f"Teams in master list: {len(master_teams)}")
    
    # Find intersection
    intersection = all_game_teams & master_teams
    print(f"Teams in both: {len(intersection)}")
    print(f"Match rate: {len(intersection)/len(all_game_teams)*100:.1f}%")
    
    # Show some examples of teams in game history but not in master list
    game_only = all_game_teams - master_teams
    print(f"\nTeams in game history but not in master list: {len(game_only)}")
    print("Sample teams:")
    for i, team in enumerate(sorted(list(game_only))[:10]):
        print(f"  {i+1}. {team}")
    
    # Show some examples of teams in master list but not in game history
    master_only = master_teams - all_game_teams
    print(f"\nTeams in master list but not in game history: {len(master_only)}")
    print("Sample teams:")
    for i, team in enumerate(sorted(list(master_only))[:10]):
        print(f"  {i+1}. {team}")
    
    # Show some examples of teams in both
    print(f"\nSample teams in both:")
    for i, team in enumerate(sorted(list(intersection))[:10]):
        print(f"  {i+1}. {team}")

if __name__ == "__main__":
    investigate_team_names()
