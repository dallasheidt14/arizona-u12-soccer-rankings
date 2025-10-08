#!/usr/bin/env python3
"""
AZ U12 Team Stats & SOS Calculator
=================================

Comprehensive system to calculate offensive/defensive ratings and Strength of Schedule (SOS)
for Arizona U12 Male teams based on matched game history.

INPUT FILES:
- Matched_Games.csv (from team matching process)
- AZ MALE U12 MASTER TEAM LIST.csv (for team metadata)

OUTPUT FILES:
- Rankings.csv (final team rankings)
- Team_Stats.csv (detailed team statistics)
- SOS_Matrix.csv (strength of schedule matrix)
- error_log.txt (validation errors)
- skipped_games_log.csv (games with data issues)
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os
from collections import defaultdict

# ========== CONFIGURATION ========== #
# Power Score Weights
OFFENSE_WEIGHT = 0.375
DEFENSE_WEIGHT = 0.375
SOS_WEIGHT = 0.25

# Validation Thresholds
MIN_GAMES_REQUIRED = 3
INACTIVITY_PENALTY_THRESHOLD = 3  # games or weeks

# Input Files
MATCHED_GAMES_FILE = "Matched_Games.csv"
MASTER_TEAM_LIST_FILE = "AZ MALE U12 MASTER TEAM LIST.csv"

# Output Files
RANKINGS_FILE = "Rankings.csv"
TEAM_STATS_FILE = "Team_Stats.csv"
SOS_MATRIX_FILE = "SOS_Matrix.csv"
ERROR_LOG_FILE = "error_log.txt"
SKIPPED_GAMES_FILE = "skipped_games_log.csv"

def log_error(message, error_log):
    """Log error message to file and console"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    error_msg = f"[{timestamp}] {message}"
    print(f"ERROR: {message}")
    error_log.append(error_msg)

def validate_score(score):
    """Validate that score is a valid integer"""
    try:
        if pd.isna(score):
            return False, "Missing score"
        score_int = int(float(score))
        if score_int < 0:
            return False, "Negative score"
        return True, score_int
    except (ValueError, TypeError):
        return False, f"Invalid score format: {score}"

def load_and_validate_data():
    """Load and validate the matched games data"""
    print("Loading and validating data...")
    
    error_log = []
    
    # Load matched games
    try:
        games_df = pd.read_csv(MATCHED_GAMES_FILE)
        print(f"+ Loaded {len(games_df)} games from {MATCHED_GAMES_FILE}")
    except FileNotFoundError:
        log_error(f"File not found: {MATCHED_GAMES_FILE}", error_log)
        return None, None, error_log
    except Exception as e:
        log_error(f"Error loading {MATCHED_GAMES_FILE}: {e}", error_log)
        return None, None, error_log
    
    # Load master team list
    try:
        master_df = pd.read_csv(MASTER_TEAM_LIST_FILE)
        print(f"+ Loaded {len(master_df)} teams from {MASTER_TEAM_LIST_FILE}")
    except FileNotFoundError:
        log_error(f"File not found: {MASTER_TEAM_LIST_FILE}", error_log)
        return None, None, error_log
    except Exception as e:
        log_error(f"Error loading {MASTER_TEAM_LIST_FILE}: {e}", error_log)
        return None, None, error_log
    
    # Validate and clean data
    print("\nValidating game data...")
    skipped_games = []
    valid_games = []
    
    for idx, row in games_df.iterrows():
        game_id = row.get('Match ID', f'Game_{idx}')
        
        # Check if both teams are matched
        team_a_match = row.get('Team A Match')
        team_b_match = row.get('Team B Match')
        
        if pd.isna(team_a_match) or pd.isna(team_b_match):
            skipped_games.append({
                'Game_ID': game_id,
                'Team_A': row.get('Team A', ''),
                'Team_B': row.get('Team B', ''),
                'Team_A_Match': team_a_match,
                'Team_B_Match': team_b_match,
                'Reason': 'Unmatched team(s)',
                'Date': row.get('Date', ''),
                'Event': row.get('Event', '')
            })
            continue
        
        # Validate scores
        score_a_valid, score_a_value = validate_score(row.get('Score A'))
        score_b_valid, score_b_value = validate_score(row.get('Score B'))
        
        if not score_a_valid or not score_b_valid:
            skipped_games.append({
                'Game_ID': game_id,
                'Team_A': row.get('Team A', ''),
                'Team_B': row.get('Team B', ''),
                'Team_A_Match': team_a_match,
                'Team_B_Match': team_b_match,
                'Reason': f'Invalid scores: A={score_a_value}, B={score_b_value}',
                'Date': row.get('Date', ''),
                'Event': row.get('Event', '')
            })
            continue
        
        # Add to valid games
        valid_games.append({
            'Game_ID': game_id,
            'Date': row.get('Date', ''),
            'Event': row.get('Event', ''),
            'Team_A': team_a_match,
            'Team_B': team_b_match,
            'Team_A_Goals': score_a_value,
            'Team_B_Goals': score_b_value,
            'Original_Team_A': row.get('Team A', ''),
            'Original_Team_B': row.get('Team B', ''),
            'Match_Type_A': row.get('Team A Match Type', ''),
            'Match_Type_B': row.get('Team B Match Type', '')
        })
    
    # Convert to DataFrame
    valid_games_df = pd.DataFrame(valid_games)
    skipped_games_df = pd.DataFrame(skipped_games)
    
    print(f"+ Valid games: {len(valid_games_df)}")
    print(f"+ Skipped games: {len(skipped_games_df)}")
    
    if len(skipped_games_df) > 0:
        skipped_games_df.to_csv(SKIPPED_GAMES_FILE, index=False)
        print(f"+ Skipped games saved to {SKIPPED_GAMES_FILE}")
    
    return valid_games_df, master_df, error_log

def calculate_team_stats(games_df):
    """Calculate offensive and defensive ratings for each team"""
    print("\nCalculating team statistics...")
    
    # Create individual team performance records
    team_performances = []
    
    for _, game in games_df.iterrows():
        # Team A performance
        team_performances.append({
            'Team': game['Team_A'],
            'Goals_For': game['Team_A_Goals'],
            'Goals_Against': game['Team_B_Goals'],
            'Opponent': game['Team_B'],
            'Game_ID': game['Game_ID'],
            'Date': game['Date'],
            'Event': game['Event']
        })
        
        # Team B performance
        team_performances.append({
            'Team': game['Team_B'],
            'Goals_For': game['Team_B_Goals'],
            'Goals_Against': game['Team_A_Goals'],
            'Opponent': game['Team_A'],
            'Game_ID': game['Game_ID'],
            'Date': game['Date'],
            'Event': game['Event']
        })
    
    # Convert to DataFrame and aggregate
    team_df = pd.DataFrame(team_performances)
    
    # Calculate aggregate statistics
    team_stats = team_df.groupby('Team').agg({
        'Goals_For': ['sum', 'count'],
        'Goals_Against': 'sum',
        'Date': ['min', 'max']
    }).reset_index()
    
    # Flatten column names
    team_stats.columns = ['Team', 'Goals_For', 'Games_Played', 'Goals_Against', 'First_Game', 'Last_Game']
    
    # Calculate win/loss/tie records
    win_loss_tie = []
    for team in team_stats['Team']:
        team_games = team_df[team_df['Team'] == team]
        wins = 0
        losses = 0
        ties = 0
        
        for _, game in team_games.iterrows():
            gf = game['Goals_For']
            ga = game['Goals_Against']
            if gf > ga:
                wins += 1
            elif gf < ga:
                losses += 1
            else:
                ties += 1
        
        win_loss_tie.append({
            'Team': team,
            'Wins': wins,
            'Losses': losses,
            'Ties': ties
        })
    
    wlt_df = pd.DataFrame(win_loss_tie)
    team_stats = team_stats.merge(wlt_df, on='Team')
    
    # Calculate ratings
    team_stats['Offensive_Rating'] = team_stats['Goals_For'] / team_stats['Games_Played']
    team_stats['Defensive_Rating'] = team_stats['Goals_Against'] / team_stats['Games_Played']
    team_stats['Goal_Differential'] = team_stats['Goals_For'] - team_stats['Goals_Against']
    team_stats['Goal_Diff_Per_Game'] = team_stats['Goal_Differential'] / team_stats['Games_Played']
    
    # Filter teams with minimum games
    team_stats = team_stats[team_stats['Games_Played'] >= MIN_GAMES_REQUIRED]
    
    print(f"+ Calculated stats for {len(team_stats)} teams (min {MIN_GAMES_REQUIRED} games)")
    
    return team_stats

def calculate_sos(games_df, team_stats):
    """Calculate Strength of Schedule for each team"""
    print("\nCalculating Strength of Schedule...")
    
    # Create opponent strength lookup
    opponent_strength = dict(zip(team_stats['Team'], 
                                team_stats['Offensive_Rating'] + team_stats['Defensive_Rating']))
    
    # Calculate SOS for each team
    sos_data = []
    
    for team in team_stats['Team']:
        # Get all games for this team
        team_games = games_df[(games_df['Team_A'] == team) | (games_df['Team_B'] == team)]
        
        opponent_offensive_ratings = []
        opponent_defensive_ratings = []
        
        for _, game in team_games.iterrows():
            if game['Team_A'] == team:
                opponent = game['Team_B']
            else:
                opponent = game['Team_A']
            
            if opponent in opponent_strength:
                opponent_stats = team_stats[team_stats['Team'] == opponent].iloc[0]
                opponent_offensive_ratings.append(opponent_stats['Offensive_Rating'])
                opponent_defensive_ratings.append(opponent_stats['Defensive_Rating'])
        
        if opponent_offensive_ratings:
            sos_offense = np.mean(opponent_offensive_ratings)
            sos_defense = np.mean(opponent_defensive_ratings)
            sos_overall = (sos_offense + sos_defense) / 2
        else:
            sos_offense = sos_defense = sos_overall = 0
        
        sos_data.append({
            'Team': team,
            'SOS_Offensive': sos_offense,
            'SOS_Defensive': sos_defense,
            'SOS_Overall': sos_overall,
            'Opponents_Count': len(opponent_offensive_ratings)
        })
    
    sos_df = pd.DataFrame(sos_data)
    print(f"+ Calculated SOS for {len(sos_df)} teams")
    
    return sos_df

def create_sos_matrix(games_df, team_stats):
    """Create SOS matrix showing who played who"""
    print("\nCreating SOS matrix...")
    
    sos_matrix = []
    
    for _, game in games_df.iterrows():
        team_a = game['Team_A']
        team_b = game['Team_B']
        
        # Get team stats
        team_a_stats = team_stats[team_stats['Team'] == team_a]
        team_b_stats = team_stats[team_stats['Team'] == team_b]
        
        if not team_a_stats.empty and not team_b_stats.empty:
            team_a_stats = team_a_stats.iloc[0]
            team_b_stats = team_b_stats.iloc[0]
            
            sos_matrix.append({
                'Team_A': team_a,
                'Team_B': team_b,
                'Team_A_Offensive': team_a_stats['Offensive_Rating'],
                'Team_A_Defensive': team_a_stats['Defensive_Rating'],
                'Team_B_Offensive': team_b_stats['Offensive_Rating'],
                'Team_B_Defensive': team_b_stats['Defensive_Rating'],
                'Team_A_Goals': game['Team_A_Goals'],
                'Team_B_Goals': game['Team_B_Goals'],
                'Date': game['Date'],
                'Event': game['Event']
            })
    
    sos_matrix_df = pd.DataFrame(sos_matrix)
    print(f"+ Created SOS matrix with {len(sos_matrix_df)} matchups")
    
    return sos_matrix_df

def calculate_power_scores(team_stats, sos_df):
    """Calculate final power scores and rankings"""
    print("\nCalculating power scores and rankings...")
    
    # Merge team stats with SOS
    final_df = team_stats.merge(sos_df, on='Team')
    
    # Calculate power score
    final_df['Power_Score'] = (
        OFFENSE_WEIGHT * final_df['Offensive_Rating'] +
        DEFENSE_WEIGHT * (1 - final_df['Defensive_Rating']) +
        SOS_WEIGHT * final_df['SOS_Overall']
    )
    
    # Sort by power score
    final_df = final_df.sort_values('Power_Score', ascending=False)
    final_df['Rank'] = range(1, len(final_df) + 1)
    
    print(f"+ Calculated power scores for {len(final_df)} teams")
    
    return final_df

def add_team_metadata(final_df, master_df):
    """Add team metadata from master list"""
    print("\nAdding team metadata...")
    
    # Merge with master team list
    master_clean = master_df[['Team Name', 'Club', 'Team ID', 'Goal Ratio', 'State Rank']].copy()
    master_clean.columns = ['Team', 'Club', 'Team_ID', 'GotSport_Goal_Ratio', 'GotSport_Rank']
    
    final_with_metadata = final_df.merge(master_clean, on='Team', how='left')
    
    # Reorder columns for better readability
    column_order = [
        'Rank', 'Team', 'Club', 'Team_ID', 'Games_Played', 'Wins', 'Losses', 'Ties',
        'Goals_For', 'Goals_Against', 'Goal_Differential', 'Goal_Diff_Per_Game',
        'Offensive_Rating', 'Defensive_Rating', 'SOS_Offensive', 'SOS_Defensive', 'SOS_Overall',
        'Power_Score', 'GotSport_Goal_Ratio', 'GotSport_Rank', 'First_Game', 'Last_Game'
    ]
    
    final_with_metadata = final_with_metadata[column_order]
    
    print(f"+ Added metadata for {len(final_with_metadata)} teams")
    
    return final_with_metadata

def save_outputs(final_df, team_stats, sos_df, sos_matrix_df, error_log):
    """Save all output files"""
    print("\nSaving output files...")
    
    # Save rankings
    final_df.to_csv(RANKINGS_FILE, index=False)
    print(f"+ Rankings saved to {RANKINGS_FILE}")
    
    # Save team stats
    team_stats.to_csv(TEAM_STATS_FILE, index=False)
    print(f"+ Team stats saved to {TEAM_STATS_FILE}")
    
    # Save SOS matrix
    sos_matrix_df.to_csv(SOS_MATRIX_FILE, index=False)
    print(f"+ SOS matrix saved to {SOS_MATRIX_FILE}")
    
    # Save error log
    if error_log:
        with open(ERROR_LOG_FILE, 'w', encoding='utf-8') as f:
            for error in error_log:
                f.write(error + '\n')
        print(f"+ Error log saved to {ERROR_LOG_FILE}")
    
    print("\nAll output files saved successfully!")

def print_summary(final_df, team_stats, sos_df):
    """Print summary statistics"""
    print("\n" + "="*60)
    print("SUMMARY STATISTICS")
    print("="*60)
    
    print(f"Total Teams Ranked: {len(final_df)}")
    print(f"Total Games Analyzed: {team_stats['Games_Played'].sum()}")
    print(f"Average Games per Team: {team_stats['Games_Played'].mean():.1f}")
    
    print(f"\nTop 10 Teams:")
    print("-" * 40)
    for i, (_, team) in enumerate(final_df.head(10).iterrows()):
        print(f"{i+1:2d}. {team['Team']:<30} Power: {team['Power_Score']:.3f}")
    
    print(f"\nConfiguration Used:")
    print(f"  Offense Weight: {OFFENSE_WEIGHT}")
    print(f"  Defense Weight: {DEFENSE_WEIGHT}")
    print(f"  SOS Weight: {SOS_WEIGHT}")
    print(f"  Min Games Required: {MIN_GAMES_REQUIRED}")

def main():
    """Main function to run the stats and SOS calculation"""
    
    print("AZ U12 Team Stats & SOS Calculator")
    print("=" * 50)
    print(f"Configuration:")
    print(f"  Offense Weight: {OFFENSE_WEIGHT}")
    print(f"  Defense Weight: {DEFENSE_WEIGHT}")
    print(f"  SOS Weight: {SOS_WEIGHT}")
    print(f"  Min Games Required: {MIN_GAMES_REQUIRED}")
    print()
    
    # Load and validate data
    games_df, master_df, error_log = load_and_validate_data()
    if games_df is None:
        print("Failed to load data. Check error log.")
        return
    
    # Calculate team statistics
    team_stats = calculate_team_stats(games_df)
    
    # Calculate SOS
    sos_df = calculate_sos(games_df, team_stats)
    
    # Create SOS matrix
    sos_matrix_df = create_sos_matrix(games_df, team_stats)
    
    # Calculate power scores and rankings
    final_df = calculate_power_scores(team_stats, sos_df)
    
    # Add team metadata
    final_df = add_team_metadata(final_df, master_df)
    
    # Save outputs
    save_outputs(final_df, team_stats, sos_df, sos_matrix_df, error_log)
    
    # Print summary
    print_summary(final_df, team_stats, sos_df)
    
    print(f"\nProcessing complete!")
    print(f"Check the following files:")
    print(f"  - {RANKINGS_FILE}")
    print(f"  - {TEAM_STATS_FILE}")
    print(f"  - {SOS_MATRIX_FILE}")
    if error_log:
        print(f"  - {ERROR_LOG_FILE}")
    if os.path.exists(SKIPPED_GAMES_FILE):
        print(f"  - {SKIPPED_GAMES_FILE}")

if __name__ == "__main__":
    main()
