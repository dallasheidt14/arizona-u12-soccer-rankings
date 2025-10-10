#!/usr/bin/env python3
"""
Generate Comprehensive Game History
===================================

This script generates a comprehensive game history file that includes ALL games
from the last 18 months, while rankings continue to use only the last 30 games
for scoring purposes.

Key distinction:
- Rankings: Use last 30 games (with tapered weights) for scoring
- Game History: Show ALL games from last 18 months for complete team history
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import os

# Configuration
HISTORY_WINDOW_DAYS = 18 * 30  # 18 months
RANKINGS_WINDOW_DAYS = 365     # 12 months (for rankings)
MAX_GAMES_FOR_RANK = 30        # Max games used for ranking calculations

def wide_to_long(games_df: pd.DataFrame) -> pd.DataFrame:
    """Convert wide format games to long format."""
    a = games_df[["Team A","Team B","Score A","Score B","Date"]].rename(
        columns={"Team A":"Team","Team B":"Opponent","Score A":"GF","Score B":"GA"})
    b = games_df[["Team B","Team A","Score B","Score A","Date"]].rename(
        columns={"Team B":"Team","Team A":"Opponent","Score B":"GF","Score A":"GA"})
    long = pd.concat([a,b], ignore_index=True)
    long = long.dropna(subset=["Team","Opponent"])
    long["Date"] = pd.to_datetime(long["Date"], errors="coerce")
    return long

def clamp_window_for_history(df: pd.DataFrame, days: int, today=None) -> pd.DataFrame:
    """Filter games to last N days for comprehensive history."""
    today = today or pd.Timestamp.now().normalize()
    cutoff = today - pd.Timedelta(days=days)
    return df[df["Date"] >= cutoff].copy()

def generate_comprehensive_history(wide_matches_csv: Path, out_csv: Path):
    """Generate comprehensive game history with ALL games from last 18 months."""
    
    print(f"Loading games from {wide_matches_csv}...")
    raw = pd.read_csv(wide_matches_csv, encoding="utf-8-sig")
    
    print("Converting to long format...")
    long = wide_to_long(raw)
    
    print(f"Original games: {len(long)}")
    
    # Load master team list and create team name mapping (same as rankings)
    try:
        master_teams = pd.read_csv("AZ MALE U12 MASTER TEAM LIST.csv")
        master_team_names = set(master_teams["Team Name"].str.strip())
        print(f"Loaded {len(master_team_names)} authorized AZ U12 teams from master list")
        
        # Create team name mapping: Team Name -> "Team Name Club"
        team_name_mapping = {}
        for _, row in master_teams.iterrows():
            team_name = row["Team Name"].strip()
            club_name = str(row["Club"]).strip() if pd.notna(row["Club"]) else ""
            # Combine team name with club name (only if club name exists)
            if club_name and club_name != "nan":
                combined_name = f"{team_name} {club_name}"
            else:
                combined_name = team_name
            team_name_mapping[team_name] = combined_name
        print(f"Created team name mapping for {len(team_name_mapping)} teams")
        
        # Apply team name mapping to include club names for both Team and Opponent
        long["Team"] = long["Team"].map(lambda x: team_name_mapping.get(x, x))
        long["Opponent"] = long["Opponent"].map(lambda x: team_name_mapping.get(x, x))
        print("Applied team name mapping with club names to both Team and Opponent columns")
        
    except FileNotFoundError:
        print("Warning: AZ MALE U12 MASTER TEAM LIST.csv not found, skipping team name mapping")
    
    # Apply 18-month window for comprehensive history
    print(f"Applying {HISTORY_WINDOW_DAYS}-day window for comprehensive history...")
    long_history = clamp_window_for_history(long, HISTORY_WINDOW_DAYS)
    
    print(f"Games in comprehensive history: {len(long_history)}")
    
    # Remove duplicates (same team playing same opponent on same date)
    print(f"Removing duplicates...")
    before_dedup = len(long_history)
    long_history = long_history.drop_duplicates(subset=["Team", "Date", "Opponent"], keep="first")
    after_dedup = len(long_history)
    print(f"Removed {before_dedup - after_dedup} duplicate games")
    
    # Sort by team and date (most recent first)
    long_history = long_history.sort_values(["Team", "Date"], ascending=[True, False]).reset_index(drop=True)
    
    # Add basic game statistics
    long_history["GoalsFor"] = long_history["GF"]
    long_history["GoalsAgainst"] = long_history["GA"]
    long_history["GoalDiff"] = long_history["GF"] - long_history["GA"]
    
    # Calculate proper Expected GD based on team strength differences
    print("Calculating team strengths for Expected GD...")
    
    # Calculate team offensive and defensive strengths
    team_stats = long_history.groupby("Team").agg({
        "GF": ["sum", "count"],
        "GA": ["sum", "count"]
    }).round(3)
    
    team_stats.columns = ["GF_total", "Games", "GA_total", "Games2"]
    team_stats = team_stats.drop("Games2", axis=1)
    team_stats["Off_Strength"] = team_stats["GF_total"] / team_stats["Games"]
    team_stats["Def_Strength"] = team_stats["GA_total"] / team_stats["Games"]
    
    # Merge team strengths into game data
    long_history = long_history.merge(
        team_stats[["Off_Strength", "Def_Strength"]], 
        left_on="Team", 
        right_index=True, 
        how="left"
    )
    long_history = long_history.merge(
        team_stats[["Off_Strength", "Def_Strength"]].rename(columns={
            "Off_Strength": "Opp_Off_Strength", 
            "Def_Strength": "Opp_Def_Strength"
        }), 
        left_on="Opponent", 
        right_index=True, 
        how="left"
    )
    
    # Fill missing strengths with league averages
    long_history["Off_Strength"] = long_history["Off_Strength"].fillna(team_stats["Off_Strength"].mean())
    long_history["Def_Strength"] = long_history["Def_Strength"].fillna(team_stats["Def_Strength"].mean())
    long_history["Opp_Off_Strength"] = long_history["Opp_Off_Strength"].fillna(team_stats["Off_Strength"].mean())
    long_history["Opp_Def_Strength"] = long_history["Opp_Def_Strength"].fillna(team_stats["Def_Strength"].mean())
    
    # Expected GD = Team's offensive strength - Opponent's defensive strength
    long_history["expected_gd"] = long_history["Off_Strength"] - long_history["Opp_Def_Strength"]
    long_history["gd_delta"] = long_history["GoalDiff"] - long_history["expected_gd"]
    
    # Simple impact bucket based on goal difference
    def get_impact_bucket(gd_delta):
        if gd_delta > 1.0:
            return "good"
        elif gd_delta < -1.0:
            return "weak"
        else:
            return "neutral"
    
    long_history["impact_bucket"] = long_history["gd_delta"].apply(get_impact_bucket)
    
    # Calculate normalized opponent strengths for display
    print("Calculating normalized opponent strengths...")
    
    # Calculate normalized offensive and defensive scores
    def robust_minmax(series):
        """Robust min-max normalization."""
        min_val, max_val = series.min(), series.max()
        if max_val == min_val:
            return pd.Series([0.5] * len(series), index=series.index)
        return (series - min_val) / (max_val - min_val)
    
    off_norm = robust_minmax(team_stats["Off_Strength"])
    def_norm = robust_minmax(team_stats["Def_Strength"])
    
    # Calculate base strength (average of normalized offense and defense)
    team_stats["BaseStrength"] = 0.5 * (off_norm + def_norm)
    
    # Create opponent strength mapping
    opp_strength_map = team_stats["BaseStrength"].to_dict()
    
    # Map opponent strengths to games
    long_history["Opponent_BaseStrength"] = long_history["Opponent"].map(
        lambda opp: opp_strength_map.get(opp, 0.5)
    ).round(3)
    
    # Select columns for output
    output_cols = [
        "Team", "Date", "Opponent", "GoalsFor", "GoalsAgainst", "GoalDiff",
        "expected_gd", "gd_delta", "impact_bucket", "Opponent_BaseStrength"
    ]
    
    # Ensure all columns exist
    for col in output_cols:
        if col not in long_history.columns:
            long_history[col] = 0.0 if col in ["expected_gd", "gd_delta", "Opponent_BaseStrength"] else "neutral"
    
    # Save comprehensive history
    long_history[output_cols].to_csv(out_csv, index=False, encoding="utf-8")
    
    print(f"Saved comprehensive game history to {out_csv}")
    
    # Show sample statistics
    print("\nSample team statistics:")
    team_stats = long_history.groupby("Team").agg({
        "Date": ["count", "min", "max"],
        "GoalsFor": "sum",
        "GoalsAgainst": "sum"
    }).round(2)
    
    team_stats.columns = ["Games", "FirstGame", "LastGame", "TotalGF", "TotalGA"]
    team_stats["GoalDiff"] = team_stats["TotalGF"] - team_stats["TotalGA"]
    
    # Show top 5 teams by games played
    top_teams = team_stats.sort_values("Games", ascending=False).head(5)
    print("\nTop 5 teams by games played:")
    for team, stats in top_teams.iterrows():
        print(f"  {team}: {stats['Games']} games, {stats['TotalGF']}-{stats['TotalGA']} ({stats['GoalDiff']:+d})")
    
    return long_history

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Generate comprehensive game history")
    p.add_argument("--in", dest="in_path", required=True, help="Input wide format games CSV")
    p.add_argument("--out", dest="out_path", default="Team_Game_Histories_COMPREHENSIVE.csv", help="Output comprehensive history CSV")
    args = p.parse_args()
    
    generate_comprehensive_history(Path(args.in_path), Path(args.out_path))
