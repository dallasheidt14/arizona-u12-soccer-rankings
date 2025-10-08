#!/usr/bin/env python3
"""
Fix Duplicate Games in Matched Games
====================================

This script removes duplicate game entries from the Matched_Games.csv file.
"""

import pandas as pd
import os
from datetime import datetime

def fix_duplicate_matched_games():
    """Remove duplicate games from the matched games file"""
    
    print("Fixing duplicate games in Matched_Games.csv...")
    
    # Load the data
    matched_games_df = pd.read_csv("Matched_Games.csv")
    
    print(f"Original data: {len(matched_games_df)} rows")
    
    # Show duplicates before removal
    duplicates = matched_games_df.duplicated(subset=['Date', 'Team A', 'Team B'], keep=False)
    duplicate_count = duplicates.sum()
    print(f"Found {duplicate_count} duplicate rows")
    
    # Remove duplicates (keep first occurrence)
    matched_games_df_clean = matched_games_df.drop_duplicates(
        subset=['Date', 'Team A', 'Team B'], 
        keep='first'
    )
    
    print(f"After deduplication: {len(matched_games_df_clean)} rows")
    print(f"Removed {len(matched_games_df) - len(matched_games_df_clean)} duplicate rows")
    
    # Create backup of original file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"Matched_Games_BACKUP_{timestamp}.csv"
    matched_games_df.to_csv(backup_filename, index=False)
    print(f"Created backup: {backup_filename}")
    
    # Save cleaned data
    matched_games_df_clean.to_csv("Matched_Games.csv", index=False)
    print("Saved cleaned data to Matched_Games.csv")
    
    # Show sample of cleaned data for FC Arizona
    fc_arizona_games = matched_games_df_clean[
        (matched_games_df_clean['Team A'] == 'FC Arizona 14B Black GFC Suenaga U12') |
        (matched_games_df_clean['Team B'] == 'FC Arizona 14B Black GFC Suenaga U12')
    ].sort_values('Date', ascending=False)
    
    print(f"\nFC Arizona 14B Black GFC Suenaga U12 - Sample Games:")
    print(f"Total games: {len(fc_arizona_games)}")
    if len(fc_arizona_games) > 0:
        print("\nRecent games:")
        for _, game in fc_arizona_games.head(5).iterrows():
            if game['Team A'] == 'FC Arizona 14B Black GFC Suenaga U12':
                opponent = game['Team B']
                score = f"{game['Score A']}-{game['Score B']}"
                result = game['Result A']
            else:
                opponent = game['Team A']
                score = f"{game['Score B']}-{game['Score A']}"
                result = game['Result B']
            print(f"  {game['Date']} vs {opponent} - {score} ({result})")
    
    print("\nNext step: Re-run the ranking calculation with cleaned data")
    print("   Run: python generate_team_rankings.py")

if __name__ == "__main__":
    fix_duplicate_matched_games()
