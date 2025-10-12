#!/usr/bin/env python3
"""
Convert U11 game histories to format expected by existing ranking generator
"""
import pandas as pd
from datetime import datetime

def convert_u11_to_ranking_format():
    """Convert U11 game histories to the format expected by the ranking generator"""
    print("Converting U11 game histories to ranking format...")
    
    # Load our U11 game histories
    games_df = pd.read_csv('data/game_histories/u11_boys_2015/arizona/game_histories.csv')
    print(f"Loaded {len(games_df)} U11 games")
    
    # Convert to the format expected by the ranking generator
    converted_games = []
    
    for _, game in games_df.iterrows():
        # Create two rows (Team A vs Team B, Team B vs Team A)
        
        # Row 1: Team A perspective
        row_a = {
            'Team A': game['home_team_name'],
            'Team B': game['away_team_name'],
            'Score A': int(game['home_score']) if pd.notna(game['home_score']) else 0,
            'Score B': int(game['away_score']) if pd.notna(game['away_score']) else 0,
            'Date': game['match_date'],
            'Competition': game['event_name'],
            'Venue': game['venue_name']
        }
        converted_games.append(row_a)
        
        # Row 2: Team B perspective (swap teams and scores)
        row_b = {
            'Team A': game['away_team_name'],
            'Team B': game['home_team_name'],
            'Score A': int(game['away_score']) if pd.notna(game['away_score']) else 0,
            'Score B': int(game['home_score']) if pd.notna(game['home_score']) else 0,
            'Date': game['match_date'],
            'Competition': game['event_name'],
            'Venue': game['venue_name']
        }
        converted_games.append(row_b)
    
    # Convert to DataFrame
    converted_df = pd.DataFrame(converted_games)
    
    # Save to the location expected by the ranking generator
    output_path = 'data/gold/Matched_Games_U11_CLEAN.csv'
    converted_df.to_csv(output_path, index=False)
    
    print(f"Converted {len(converted_games)} game records")
    print(f"Saved to: {output_path}")
    
    # Show sample
    print(f"\nSample converted games:")
    print(converted_df.head(6).to_string(index=False))
    
    return output_path

if __name__ == "__main__":
    convert_u11_to_ranking_format()

