#!/usr/bin/env python3
"""
Fix Duplicate Games in Team Game Histories
==========================================

This script removes duplicate game entries from the Team_Game_Histories.csv file.
Each game appears twice (once for each team), but we only need it once per team.
"""

import pandas as pd
import os
from datetime import datetime

def fix_duplicate_games():
    """Remove duplicate games from the team game histories"""
    
    print("Fixing duplicate games in Team_Game_Histories.csv...")
    
    # Load the data
    game_histories_df = pd.read_csv("Team_Game_Histories.csv")
    
    print(f"Original data: {len(game_histories_df)} rows")
    
    # Show duplicates before removal
    duplicates = game_histories_df.duplicated(subset=['Date', 'Team', 'Opponent'], keep=False)
    duplicate_count = duplicates.sum()
    print(f"Found {duplicate_count} duplicate rows")
    
    # Remove duplicates (keep first occurrence)
    game_histories_df_clean = game_histories_df.drop_duplicates(
        subset=['Date', 'Team', 'Opponent'], 
        keep='first'
    )
    
    print(f"After deduplication: {len(game_histories_df_clean)} rows")
    print(f"Removed {len(game_histories_df) - len(game_histories_df_clean)} duplicate rows")
    
    # Create backup of original file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"Team_Game_Histories_BACKUP_{timestamp}.csv"
    game_histories_df.to_csv(backup_filename, index=False)
    print(f"Created backup: {backup_filename}")
    
    # Save cleaned data
    game_histories_df_clean.to_csv("Team_Game_Histories.csv", index=False)
    print("Saved cleaned data to Team_Game_Histories.csv")
    
    # Show sample of cleaned data for FC Arizona
    fc_arizona_games = game_histories_df_clean[
        game_histories_df_clean['Team'] == 'FC Arizona 14B Black GFC Suenaga U12'
    ].sort_values('Date', ascending=False)
    
    print(f"\nFC Arizona 14B Black GFC Suenaga U12 - Sample Games:")
    print(f"Total games: {len(fc_arizona_games)}")
    if len(fc_arizona_games) > 0:
        print("\nRecent games:")
        for _, game in fc_arizona_games.head(5).iterrows():
            result = 'W' if game['Goals For'] > game['Goals Against'] else 'L' if game['Goals For'] < game['Goals Against'] else 'T'
            print(f"  {game['Date']} vs {game['Opponent']} - {game['Goals For']}-{game['Goals Against']} ({result})")
    
    print("\nNext step: Re-run the ranking calculation with cleaned data")
    print("   Run: python generate_team_rankings.py")

if __name__ == "__main__":
    fix_duplicate_games()
