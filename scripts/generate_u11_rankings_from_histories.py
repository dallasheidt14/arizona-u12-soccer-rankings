#!/usr/bin/env python3
"""
Generate U11 rankings from scraped game histories.

This will use the same V5.3E algorithm as U12 but with the new ID-based data structure.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
from pathlib import Path
import numpy as np

DIV = "az_boys_u11_2025"
HISTORIES = Path(f"data/outputs/{DIV}/histories.csv")
MASTER = Path(f"data/master/{DIV}/arizona_teams.csv")
OUTPUT_DIR = Path(f"data/outputs/{DIV}")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def calculate_team_stats(histories_df):
    """Calculate team statistics from game histories."""
    
    # Group by team
    team_stats = []
    
    for team_id, team_games in histories_df.groupby('team_id'):
        team_name = team_games.iloc[0]['display_name']
        
        # Basic stats
        total_games = len(team_games)
        wins = len(team_games[team_games['result'] == 'W'])
        losses = len(team_games[team_games['result'] == 'L'])
        draws = len(team_games[team_games['result'] == 'D'])
        
        goals_for = team_games['goals_for'].sum()
        goals_against = team_games['goals_against'].sum()
        
        # Win percentage
        win_pct = wins / total_games if total_games > 0 else 0
        
        # Goals per game
        gpg = goals_for / total_games if total_games > 0 else 0
        gpa = goals_against / total_games if total_games > 0 else 0
        
        # Simple PowerScore calculation (can be enhanced with V5.3E algorithm)
        power_score = win_pct * 0.6 + (gpg / (gpg + gpa + 1)) * 0.4
        
        team_stats.append({
            'team_id': team_id,
            'Team': team_name,
            'GamesPlayed': total_games,
            'Wins': wins,
            'Losses': losses,
            'Draws': draws,
            'GoalsFor': goals_for,
            'GoalsAgainst': goals_against,
            'WinPct': win_pct,
            'GPG': gpg,
            'GPA': gpa,
            'PowerScore': power_score
        })
    
    return pd.DataFrame(team_stats)


def run():
    """Generate U11 rankings from scraped histories."""
    
    # Check if histories file exists
    if not HISTORIES.exists():
        print(f"Histories file not found: {HISTORIES}")
        print("Please run the game history scraper first.")
        return
    
    # Load data
    print("Loading game histories...")
    histories_df = pd.read_csv(HISTORIES)
    print(f"Loaded {len(histories_df)} game records")
    
    # Load master list for additional team info
    master_df = pd.read_csv(MASTER)
    print(f"Loaded {len(master_df)} Arizona teams")
    
    # Calculate team statistics
    print("Calculating team statistics...")
    team_stats = calculate_team_stats(histories_df)
    
    # Sort by PowerScore
    team_stats = team_stats.sort_values('PowerScore', ascending=False).reset_index(drop=True)
    team_stats['Rank'] = range(1, len(team_stats) + 1)
    
    # Reorder columns
    cols = ['Rank', 'Team', 'team_id', 'PowerScore', 'GamesPlayed', 'Wins', 'Losses', 'Draws', 'GoalsFor', 'GoalsAgainst', 'WinPct', 'GPG', 'GPA']
    team_stats = team_stats[cols]
    
    # Save rankings
    rankings_path = OUTPUT_DIR / "rankings.csv"
    team_stats.to_csv(rankings_path, index=False)
    
    print(f"\nGenerated U11 rankings for {len(team_stats)} teams")
    print(f"Saved to: {rankings_path}")
    
    # Show top 10 teams
    print("\nTop 10 U11 teams:")
    for _, row in team_stats.head(10).iterrows():
        print(f"  {row['Rank']:2d}. {row['Team']:<30} PowerScore: {row['PowerScore']:.3f} ({row['GamesPlayed']} games)")
    
    # Check for specific teams
    next_level = team_stats[team_stats['Team'].str.contains('Next Level', case=False)]
    if not next_level.empty:
        print(f"\nNext Level Soccer teams:")
        for _, row in next_level.iterrows():
            print(f"  {row['Rank']:2d}. {row['Team']:<30} PowerScore: {row['PowerScore']:.3f}")
    
    arsenal = team_stats[team_stats['Team'].str.contains('Arsenal', case=False)]
    if not arsenal.empty:
        print(f"\nAZ Arsenal teams:")
        for _, row in arsenal.head(5).iterrows():
            print(f"  {row['Rank']:2d}. {row['Team']:<30} PowerScore: {row['PowerScore']:.3f}")


if __name__ == "__main__":
    run()
