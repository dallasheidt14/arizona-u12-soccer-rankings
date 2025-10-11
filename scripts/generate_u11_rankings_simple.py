#!/usr/bin/env python3
"""
Generate U11 rankings from ID-based histories.

Simple implementation that reads the histories.csv and generates rankings
using basic PowerScore calculation.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

DIV_SLICE = "az_boys_u11_2025"
HISTORIES = Path(f"data/outputs/{DIV_SLICE}/histories.csv")
MASTER = Path(f"data/master/{DIV_SLICE}/master_teams.csv")
RANKINGS_OUT = Path(f"data/outputs/{DIV_SLICE}/rankings.csv")


def calculate_powerscore(histories_df):
    """Calculate PowerScore for each team."""
    
    # Filter to last 30 games within 365 days
    cutoff_date = datetime.now() - timedelta(days=365)
    histories_df['date'] = pd.to_datetime(histories_df['date'])
    recent_games = histories_df[histories_df['date'] >= cutoff_date]
    
    # Calculate basic metrics for each team
    team_stats = []
    
    for team_id in histories_df['team_id'].unique():
        team_games = recent_games[recent_games['team_id'] == team_id]
        
        if len(team_games) == 0:
            continue
            
        # Take last 30 games
        team_games = team_games.sort_values('date').tail(30)
        
        # Basic stats
        games_played = len(team_games)
        wins = len(team_games[team_games['result'] == 'W'])
        draws = len(team_games[team_games['result'] == 'D'])
        losses = len(team_games[team_games['result'] == 'L'])
        
        # Goals
        goals_for = team_games['goals_for'].sum()
        goals_against = team_games['goals_against'].sum()
        goal_difference = goals_for - goals_against
        
        # Win percentage
        win_pct = wins / games_played if games_played > 0 else 0
        
        # Goals per game
        goals_per_game = goals_for / games_played if games_played > 0 else 0
        goals_against_per_game = goals_against / games_played if games_played > 0 else 0
        
        # Simple PowerScore calculation
        # Weight: 40% win percentage, 30% goal difference per game, 30% goals per game
        power_score = (
            0.4 * win_pct +
            0.3 * (goal_difference / games_played if games_played > 0 else 0) +
            0.3 * (goals_per_game / 5.0)  # Normalize goals per game
        )
        
        # Ensure PowerScore is between 0 and 1
        power_score = max(0, min(1, power_score))
        
        team_stats.append({
            'team_id': team_id,
            'games_played': games_played,
            'wins': wins,
            'draws': draws,
            'losses': losses,
            'goals_for': goals_for,
            'goals_against': goals_against,
            'goal_difference': goal_difference,
            'win_pct': win_pct,
            'goals_per_game': goals_per_game,
            'goals_against_per_game': goals_against_per_game,
            'power_score': power_score
        })
    
    return pd.DataFrame(team_stats)


def run():
    """Generate U11 rankings from histories."""
    
    # Load histories
    histories = pd.read_csv(HISTORIES)
    print(f"Loaded histories: {len(histories)} records")
    
    # Load master list
    master = pd.read_csv(MASTER)
    print(f"Loaded master list: {len(master)} teams")
    
    # Calculate PowerScores
    team_stats = calculate_powerscore(histories)
    print(f"Calculated stats for {len(team_stats)} teams")
    
    # Join with master list for display names
    rankings = team_stats.merge(
        master[['team_id', 'display_name']], 
        on='team_id', 
        how='left'
    )
    
    # Fill missing display names with team_id
    rankings['display_name'] = rankings['display_name'].fillna(rankings['team_id'])
    
    # Sort by PowerScore
    rankings = rankings.sort_values('power_score', ascending=False).reset_index(drop=True)
    rankings['rank'] = range(1, len(rankings) + 1)
    
    # Reorder columns
    rankings = rankings[[
        'rank', 'team_id', 'display_name', 'power_score', 
        'games_played', 'wins', 'draws', 'losses',
        'goals_for', 'goals_against', 'goal_difference',
        'win_pct', 'goals_per_game', 'goals_against_per_game'
    ]]
    
    # Create output directory
    RANKINGS_OUT.parent.mkdir(parents=True, exist_ok=True)
    
    # Save rankings
    rankings.to_csv(RANKINGS_OUT, index=False)
    print(f"Saved rankings: {RANKINGS_OUT}")
    
    # Show top teams
    print(f"\nTop 10 U11 teams:")
    for _, row in rankings.head(10).iterrows():
        print(f"  {row['rank']}. {row['display_name']} - {row['power_score']:.3f} ({row['games_played']} games)")
    
    # Statistics
    az_teams = rankings[~rankings['team_id'].str.startswith('ext_')]
    external_teams = rankings[rankings['team_id'].str.startswith('ext_')]
    
    print(f"\nStatistics:")
    print(f"  Total teams ranked: {len(rankings)}")
    print(f"  Arizona teams: {len(az_teams)}")
    print(f"  External teams: {len(external_teams)}")
    print(f"  Average games per team: {rankings['games_played'].mean():.1f}")


if __name__ == "__main__":
    run()
