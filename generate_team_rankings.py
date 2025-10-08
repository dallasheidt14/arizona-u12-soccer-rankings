#!/usr/bin/env python3
"""
AZ U12 Team Ranking System - Backend
====================================

Complete backend script to calculate offensive, defensive, and SOS ratings
with weighted recent game emphasis and game count penalties.

Features:
- Weighted offensive/defensive stats (last 10 games weighted more heavily)
- Strength of Schedule (SOS) calculations
- Game count penalties for teams with fewer games
- Power Score rankings with metadata
- Comprehensive error handling and logging
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os

# =============================
# 📌 CONFIGURATION SECTION
# =============================
OFFENSE_WEIGHT = 0.375
DEFENSE_WEIGHT = 0.375
SOS_WEIGHT = 0.25
RECENT_WEIGHT = 0.7  # Weight for last 10 games
FULL_WEIGHT = 1.0

# Game count penalty thresholds
GAMES_PENALTY_THRESHOLDS = {
    "full": 20,        # >= 20 games: no penalty
    "moderate": 10,    # 10-19 games: moderate penalty
    "low_penalty": 0.9,  # multiplier for moderate penalty
    "high_penalty": 0.75  # multiplier for heavy penalty
}

# Input files
MATCHED_GAMES_FILE = "Matched_Games.csv"  # Now cleaned of duplicates
MASTER_TEAM_LIST_FILE = "AZ MALE U12 MASTER TEAM LIST.csv"

# Output files
RANKINGS_FILE = "Rankings_PowerScore_NEW.csv"
GAME_HISTORIES_FILE = "Team_Game_Histories_NEW.csv"
LOGS_FILE = "Ranking_Logs.txt"

def log_message(message, log_file):
    """Log message to file and console"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] {message}"
    print(log_msg)
    log_file.append(log_msg)

def validate_and_clean_data(games_df, log_file):
    """Validate and clean the game data"""
    log_message("Validating and cleaning game data...", log_file)
    
    original_count = len(games_df)
    
    # Filter to matched games only
    matched_games = games_df[
        (games_df["Team A Match Type"] != "NO_MATCH") & 
        (games_df["Team B Match Type"] != "NO_MATCH")
    ].copy()
    
    log_message(f"Filtered to matched games: {len(matched_games)}/{original_count}", log_file)
    
    # Validate dates
    matched_games["Date"] = pd.to_datetime(matched_games["Date"], errors="coerce")
    invalid_dates = matched_games["Date"].isna().sum()
    if invalid_dates > 0:
        log_message(f"Warning: {invalid_dates} games with invalid dates", log_file)
    
    # Sort by date (newest first for recent game weighting)
    matched_games = matched_games.sort_values(by="Date", ascending=False)
    
    # Validate scores
    matched_games["Score A"] = pd.to_numeric(matched_games["Score A"], errors="coerce")
    matched_games["Score B"] = pd.to_numeric(matched_games["Score B"], errors="coerce")
    
    invalid_scores = matched_games["Score A"].isna().sum() + matched_games["Score B"].isna().sum()
    if invalid_scores > 0:
        log_message(f"Warning: {invalid_scores} games with invalid scores", log_file)
    
    # Remove games with invalid scores
    valid_games = matched_games.dropna(subset=["Score A", "Score B"])
    removed_games = len(matched_games) - len(valid_games)
    if removed_games > 0:
        log_message(f"Removed {removed_games} games with invalid scores", log_file)
    
    log_message(f"Final valid games: {len(valid_games)}", log_file)
    
    return valid_games

def reshape_to_long_format(games_df, log_file):
    """Reshape game data to long format (one row per team per game)"""
    log_message("Reshaping data to long format...", log_file)
    
    # Team A perspective
    team_a_games = games_df[["Team A Match", "Score A", "Team B Match", "Score B", "Date"]].rename(
        columns={
            "Team A Match": "Team", 
            "Score A": "Goals For", 
            "Team B Match": "Opponent", 
            "Score B": "Goals Against"
        }
    )
    
    # Team B perspective
    team_b_games = games_df[["Team B Match", "Score B", "Team A Match", "Score A", "Date"]].rename(
        columns={
            "Team B Match": "Team", 
            "Score B": "Goals For", 
            "Team A Match": "Opponent", 
            "Score A": "Goals Against"
        }
    )
    
    # Combine both perspectives
    long_games = pd.concat([team_a_games, team_b_games], ignore_index=True)
    
    # Sort by team and date (newest first)
    long_games = long_games.sort_values(by=["Team", "Date"], ascending=[True, False])
    
    log_message(f"Created {len(long_games)} team-game records", log_file)
    
    return long_games

def calculate_weighted_stats(long_games_df, log_file):
    """Calculate weighted offensive/defensive stats with recent game emphasis"""
    log_message("Calculating weighted team statistics...", log_file)
    
    stats = {}
    teams_processed = 0
    
    for team, group in long_games_df.groupby("Team"):
        if len(group) == 0:
            log_message(f"Warning: Team '{team}' has no games", log_file)
            continue
        
        # Sort by date (newest first)
        group = group.sort_values(by="Date", ascending=False)
        
        # Split into recent (last 10) and older games
        recent_games = group.head(10)
        older_games = group.iloc[10:]
        
        # Calculate goals for recent and older games
        recent_gf = recent_games["Goals For"].sum()
        recent_ga = recent_games["Goals Against"].sum()
        old_gf = older_games["Goals For"].sum()
        old_ga = older_games["Goals Against"].sum()
        
        total_games = len(group)
        
        # Calculate weighted averages
        if total_games <= 10:
            # If <= 10 games, weight all at RECENT_WEIGHT
            gf_per_game = (RECENT_WEIGHT * (recent_gf + old_gf)) / total_games
            ga_per_game = (RECENT_WEIGHT * (recent_ga + old_ga)) / total_games
        else:
            # Weight recent games more heavily
            gf_per_game = (RECENT_WEIGHT * recent_gf + (1 - RECENT_WEIGHT) * old_gf) / total_games
            ga_per_game = (RECENT_WEIGHT * recent_ga + (1 - RECENT_WEIGHT) * old_ga) / total_games
        
        # Calculate win/loss/tie records
        wins = (group["Goals For"] > group["Goals Against"]).sum()
        losses = (group["Goals For"] < group["Goals Against"]).sum()
        ties = (group["Goals For"] == group["Goals Against"]).sum()
        
        stats[team] = {
            "Games Played": total_games,
            "Goals For/Game": gf_per_game,
            "Goals Against/Game": ga_per_game,
            "Wins": wins,
            "Losses": losses,
            "Ties": ties,
            "Goals For": group["Goals For"].sum(),
            "Goals Against": group["Goals Against"].sum(),
            "Goal Differential": group["Goals For"].sum() - group["Goals Against"].sum()
        }
        
        teams_processed += 1
    
    log_message(f"Calculated stats for {teams_processed} teams", log_file)
    
    return pd.DataFrame.from_dict(stats, orient="index").reset_index().rename(columns={"index": "Team"})

def calculate_sos(long_games_df, team_stats_df, log_file):
    """Calculate Strength of Schedule (SOS) for each team"""
    log_message("Calculating Strength of Schedule (SOS)...", log_file)
    
    # Create opponent stats lookup
    opponent_stats = team_stats_df.set_index("Team")
    
    sos_scores = []
    
    for _, row in team_stats_df.iterrows():
        team = row["Team"]
        team_games = long_games_df[long_games_df["Team"] == team]
        
        opponent_scores = []
        
        for _, game in team_games.iterrows():
            opponent = game["Opponent"]
            
            if opponent in opponent_stats.index:
                opp_stat = opponent_stats.loc[opponent]
                
                # SOS formula: opponent_GF_per_game + max(0, 1 - opponent_GA_per_game)
                sos_score = opp_stat["Goals For/Game"] + max(0, 1 - opp_stat["Goals Against/Game"])
                opponent_scores.append(sos_score)
        
        # Calculate average SOS
        avg_sos = sum(opponent_scores) / len(opponent_scores) if opponent_scores else 0
        
        sos_scores.append({
            "Team": team,
            "SOS": avg_sos,
            "Opponents_Count": len(opponent_scores)
        })
    
    sos_df = pd.DataFrame(sos_scores)
    log_message(f"Calculated SOS for {len(sos_df)} teams", log_file)
    
    return sos_df

def apply_game_count_penalty(games_played, raw_score):
    """Apply penalty based on number of games played"""
    if games_played >= GAMES_PENALTY_THRESHOLDS["full"]:
        return raw_score
    elif games_played >= GAMES_PENALTY_THRESHOLDS["moderate"]:
        return raw_score * GAMES_PENALTY_THRESHOLDS["low_penalty"]
    else:
        return raw_score * GAMES_PENALTY_THRESHOLDS["high_penalty"]

def calculate_power_scores(team_stats_df, sos_df, log_file):
    """Calculate final power scores with penalties"""
    log_message("Calculating power scores...", log_file)
    
    # Merge team stats with SOS
    combined_df = team_stats_df.merge(sos_df, on="Team", how="left")
    
    # Fill missing SOS with 0
    combined_df["SOS"] = combined_df["SOS"].fillna(0)
    
    # Calculate component scores
    combined_df["Offense Score"] = combined_df["Goals For/Game"]
    combined_df["Defense Score"] = combined_df["Goals Against/Game"]
    combined_df["Adj Defense Score"] = 1 - combined_df["Defense Score"]
    
    # Calculate raw power score
    combined_df["Raw Power"] = (
        OFFENSE_WEIGHT * combined_df["Offense Score"] +
        DEFENSE_WEIGHT * combined_df["Adj Defense Score"] +
        SOS_WEIGHT * combined_df["SOS"]
    )
    
    # Apply game count penalties
    combined_df["Power Score"] = combined_df.apply(
        lambda row: apply_game_count_penalty(row["Games Played"], row["Raw Power"]), 
        axis=1
    )
    
    log_message(f"Calculated power scores for {len(combined_df)} teams", log_file)
    
    return combined_df

def add_metadata_and_rank(team_stats_df, master_df, log_file):
    """Add team metadata and create final rankings"""
    log_message("Adding metadata and creating rankings...", log_file)
    
    # Prepare master team list for merge
    master_clean = master_df[["Team Name", "Club", "Team ID", "State", "Gender", "Age Group"]].copy()
    master_clean.columns = ["Team", "Club", "Team_ID", "State", "Gender", "Age_Group"]
    
    # Merge with master team list
    ranked_df = team_stats_df.merge(master_clean, on="Team", how="left")
    
    # Fill missing metadata
    ranked_df["Club"] = ranked_df["Club"].fillna("Unknown")
    ranked_df["State"] = ranked_df["State"].fillna("Unknown")
    ranked_df["Gender"] = ranked_df["Gender"].fillna("Unknown")
    ranked_df["Age_Group"] = ranked_df["Age_Group"].fillna("Unknown")
    
    # Sort by power score (descending)
    ranked_df = ranked_df.sort_values(by="Power Score", ascending=False).reset_index(drop=True)
    ranked_df["Rank"] = ranked_df.index + 1
    
    # Reorder columns for better readability
    column_order = [
        "Rank", "Team", "Club", "Team_ID", "State", "Gender", "Age_Group",
        "Games Played", "Wins", "Losses", "Ties", "Goals For", "Goals Against", "Goal Differential",
        "Goals For/Game", "Goals Against/Game", "Offense Score", "Adj Defense Score", 
        "SOS", "Raw Power", "Power Score", "Opponents_Count"
    ]
    
    ranked_df = ranked_df[column_order]
    
    log_message(f"Created rankings for {len(ranked_df)} teams", log_file)
    
    return ranked_df

def save_outputs(ranked_df, long_games_df, log_file):
    """Save all output files"""
    log_message("Saving output files...", log_file)
    
    # Save rankings
    ranked_df.to_csv(RANKINGS_FILE, index=False)
    log_message(f"Saved rankings to {RANKINGS_FILE}", log_file)
    
    # Save game histories
    long_games_df.to_csv(GAME_HISTORIES_FILE, index=False)
    log_message(f"Saved game histories to {GAME_HISTORIES_FILE}", log_file)
    
    # Save logs
    with open(LOGS_FILE, 'w', encoding='utf-8') as f:
        for log_entry in log_file:
            f.write(log_entry + '\n')
    log_message(f"Saved logs to {LOGS_FILE}", log_file)

def print_summary(ranked_df, long_games_df, log_file):
    """Print summary statistics"""
    print("\n" + "="*60)
    print("RANKING SYSTEM SUMMARY")
    print("="*60)
    
    print(f"Total Teams Ranked: {len(ranked_df)}")
    print(f"Total Team-Game Records: {len(long_games_df)}")
    print(f"Average Games per Team: {ranked_df['Games Played'].mean():.1f}")
    
    print(f"\nConfiguration Used:")
    print(f"  Offense Weight: {OFFENSE_WEIGHT}")
    print(f"  Defense Weight: {DEFENSE_WEIGHT}")
    print(f"  SOS Weight: {SOS_WEIGHT}")
    print(f"  Recent Game Weight: {RECENT_WEIGHT}")
    print(f"  Game Penalty Thresholds: {GAMES_PENALTY_THRESHOLDS}")
    
    print(f"\nTop 10 Teams:")
    print("-" * 50)
    for i, (_, team) in enumerate(ranked_df.head(10).iterrows()):
        print(f"{i+1:2d}. {team['Team']:<35} Power: {team['Power Score']:.3f}")
    
    print(f"\nTeams by Game Count:")
    print("-" * 30)
    game_counts = ranked_df['Games Played'].value_counts().sort_index()
    for games, count in game_counts.items():
        print(f"  {games:2d} games: {count:3d} teams")

def main():
    """Main function to run the ranking system"""
    
    print("AZ U12 Team Ranking System - Backend")
    print("=" * 50)
    print(f"Configuration:")
    print(f"  Offense Weight: {OFFENSE_WEIGHT}")
    print(f"  Defense Weight: {DEFENSE_WEIGHT}")
    print(f"  SOS Weight: {SOS_WEIGHT}")
    print(f"  Recent Game Weight: {RECENT_WEIGHT}")
    print()
    
    log_file = []
    
    try:
        # Load data
        log_message("Loading input files...", log_file)
        games_df = pd.read_csv(MATCHED_GAMES_FILE)
        master_df = pd.read_csv(MASTER_TEAM_LIST_FILE)
        log_message(f"Loaded {len(games_df)} games and {len(master_df)} master teams", log_file)
        
        # Validate and clean data
        valid_games = validate_and_clean_data(games_df, log_file)
        
        # Reshape to long format
        long_games = reshape_to_long_format(valid_games, log_file)
        
        # Calculate weighted team statistics
        team_stats = calculate_weighted_stats(long_games, log_file)
        
        # Calculate SOS
        sos_df = calculate_sos(long_games, team_stats, log_file)
        
        # Calculate power scores
        team_stats_with_sos = calculate_power_scores(team_stats, sos_df, log_file)
        
        # Add metadata and create rankings
        final_rankings = add_metadata_and_rank(team_stats_with_sos, master_df, log_file)
        
        # Save outputs
        save_outputs(final_rankings, long_games, log_file)
        
        # Print summary
        print_summary(final_rankings, long_games, log_file)
        
        print(f"\nRanking system complete!")
        print(f"Check the following files:")
        print(f"  - {RANKINGS_FILE}")
        print(f"  - {GAME_HISTORIES_FILE}")
        print(f"  - {LOGS_FILE}")
        
    except Exception as e:
        log_message(f"Error in main execution: {e}", log_file)
        print(f"Error: {e}")
        return

if __name__ == "__main__":
    main()
