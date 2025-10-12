#!/usr/bin/env python3
"""
Generate U11 Arizona rankings from game histories
"""
import pandas as pd
import numpy as np
from datetime import datetime
import json

def load_data():
    """Load the organized U11 data"""
    print("Loading U11 data...")
    
    # Load teams
    teams_df = pd.read_csv('data/master/u11_boys_2015/teams_by_state/arizona_teams.csv')
    print(f"  Loaded {len(teams_df)} Arizona U11 teams")
    
    # Load game histories
    games_df = pd.read_csv('data/game_histories/u11_boys_2015/arizona/game_histories.csv')
    print(f"  Loaded {len(games_df)} games")
    
    return teams_df, games_df

def calculate_team_stats(games_df, teams_df):
    """Calculate team statistics from game histories"""
    print("Calculating team statistics...")
    
    team_stats = []
    
    for _, team in teams_df.iterrows():
        team_id = team['team_id']
        team_name = team['team_name']
        
        # Get all games for this team
        team_games = games_df[games_df['team_id'] == team_id]
        
        if len(team_games) == 0:
            continue
        
        # Calculate basic stats
        wins = 0
        losses = 0
        draws = 0
        goals_for = 0
        goals_against = 0
        
        for _, game in team_games.iterrows():
            home_score = game['home_score'] if pd.notna(game['home_score']) else 0
            away_score = game['away_score'] if pd.notna(game['away_score']) else 0
            
            # Determine if this team was home or away
            is_home = game['home_team_id'] == team_id
            
            if is_home:
                team_score = home_score
                opp_score = away_score
            else:
                team_score = away_score
                opp_score = home_score
            
            goals_for += team_score
            goals_against += opp_score
            
            if team_score > opp_score:
                wins += 1
            elif team_score < opp_score:
                losses += 1
            else:
                draws += 1
        
        total_games = wins + losses + draws
        
        if total_games == 0:
            continue
        
        # Calculate metrics
        win_percentage = wins / total_games
        goal_difference = goals_for - goals_against
        goals_per_game = goals_for / total_games
        goals_against_per_game = goals_against / total_games
        
        # Simple PowerScore calculation
        power_score = (win_percentage * 0.4) + (goal_difference / total_games * 0.3) + (goals_per_game * 0.2) + ((1 - goals_against_per_game) * 0.1)
        
        team_stats.append({
            'team_id': team_id,
            'team_name': team_name,
            'total_games': total_games,
            'wins': wins,
            'losses': losses,
            'draws': draws,
            'goals_for': goals_for,
            'goals_against': goals_against,
            'goal_difference': goal_difference,
            'win_percentage': win_percentage,
            'goals_per_game': goals_per_game,
            'goals_against_per_game': goals_against_per_game,
            'power_score': power_score
        })
    
    return pd.DataFrame(team_stats)

def generate_rankings(team_stats_df):
    """Generate final rankings"""
    print("Generating rankings...")
    
    # Sort by PowerScore (descending)
    rankings_df = team_stats_df.sort_values('power_score', ascending=False).reset_index(drop=True)
    
    # Add rank
    rankings_df['rank'] = range(1, len(rankings_df) + 1)
    
    # Round values for display
    rankings_df['power_score'] = rankings_df['power_score'].round(4)
    rankings_df['win_percentage'] = rankings_df['win_percentage'].round(3)
    rankings_df['goals_per_game'] = rankings_df['goals_per_game'].round(2)
    rankings_df['goals_against_per_game'] = rankings_df['goals_against_per_game'].round(2)
    
    return rankings_df

def save_rankings(rankings_df):
    """Save rankings to organized location"""
    print("Saving rankings...")
    
    # Save to organized location
    output_path = 'data/rankings/u11_boys_2015/rankings.csv'
    rankings_df.to_csv(output_path, index=False)
    
    # Also save a timestamped version
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamped_path = f'data/rankings/u11_boys_2015/rankings_{timestamp}.csv'
    rankings_df.to_csv(timestamped_path, index=False)
    
    print(f"  Saved to: {output_path}")
    print(f"  Backup saved to: {timestamped_path}")
    
    return output_path

def display_top_rankings(rankings_df, top_n=10):
    """Display top rankings"""
    print(f"\nTOP {top_n} ARIZONA U11 TEAMS:")
    print("=" * 80)
    
    top_teams = rankings_df.head(top_n)
    
    for _, team in top_teams.iterrows():
        print(f"#{team['rank']:2d} {team['team_name']:<40} "
              f"PowerScore: {team['power_score']:.4f} "
              f"Record: {team['wins']}-{team['losses']}-{team['draws']} "
              f"({team['total_games']} games)")

def main():
    """Main ranking generation process"""
    print("GENERATING ARIZONA U11 RANKINGS")
    print("=" * 50)
    
    try:
        # Load data
        teams_df, games_df = load_data()
        
        # Calculate team statistics
        team_stats_df = calculate_team_stats(games_df, teams_df)
        print(f"  Calculated stats for {len(team_stats_df)} teams")
        
        # Generate rankings
        rankings_df = generate_rankings(team_stats_df)
        
        # Save rankings
        output_path = save_rankings(rankings_df)
        
        # Display results
        display_top_rankings(rankings_df)
        
        print(f"\nSUCCESS!")
        print(f"Generated rankings for {len(rankings_df)} Arizona U11 teams")
        print(f"Based on {len(games_df)} games")
        print(f"Rankings saved to: {output_path}")
        
        return rankings_df
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return None

if __name__ == "__main__":
    rankings_df = main()
