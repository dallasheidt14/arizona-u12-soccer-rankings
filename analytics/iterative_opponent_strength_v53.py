#!/usr/bin/env python3
"""
Iterative Opponent-Strength / Better SOS Engine (V5.3+)
========================================================

This module implements an Elo-based iterative engine to compute opponent strength
through multiple passes over game results, providing a more sophisticated SOS
calculation than the traditional approach.

Key Features:
- Elo-style rating updates with goal-differential awareness
- Master team filtering for consistency
- Convergence detection and iteration limits
- Normalized output for integration with existing rankings

Usage:
    from analytics.iterative_opponent_strength_v53 import compute_iterative_sos
    sos_dict = compute_iterative_sos("Matched_Games.csv")
"""

import pandas as pd
import numpy as np
from collections import defaultdict
from statistics import mean
from pathlib import Path
import warnings

# ---- Iterative SOS Configuration ----
INITIAL_RATING = 1500
K_FACTOR = 24                    # Update sensitivity
GOAL_DIFF_MULT = 0.20           # Goal-margin weight
GOAL_DIFF_CAP = 6               # Cap blowouts at 6 goals
MAX_ITERS = 30                  # Maximum iterations
CONV_TOL = 1.0                  # Convergence tolerance (mean Δrating)
RATING_SCALE = 400              # Logistic curve spread
USE_GOAL_DIFF_AWARE = True      # Enable goal-diff multiplier


def load_and_filter_games(matched_games_path: str) -> pd.DataFrame:
    """
    Load Matched_Games.csv and filter to master team vs master team games.
    Also applies team name mapping to include club names.
    
    Args:
        matched_games_path: Path to Matched_Games.csv
        
    Returns:
        Filtered DataFrame with only master team games and mapped team names
    """
    print(f"Loading games from {matched_games_path}...")
    df = pd.read_csv(matched_games_path)
    
    # Load master team list
    master_teams = pd.read_csv("AZ MALE U12 MASTER TEAM LIST.csv")
    master_team_names = set(master_teams["Team Name"].str.strip())
    
    print(f"Loaded {len(master_team_names)} master teams")
    
    # Create team name mapping: Team Name -> "Team Name Club"
    team_name_mapping = {}
    for _, row in master_teams.iterrows():
        team_name = row["Team Name"].strip()
        club_name = str(row["Club"]).strip() if pd.notna(row["Club"]) else ""
        # Combine team name with club name
        if club_name and club_name != "nan":
            combined_name = f"{team_name} {club_name}"
        else:
            combined_name = team_name
        team_name_mapping[team_name] = combined_name
    
    # Apply team name mapping to include club names
    df["Team A"] = df["Team A"].map(lambda x: team_name_mapping.get(x, x))
    df["Team B"] = df["Team B"].map(lambda x: team_name_mapping.get(x, x))
    
    # Filter to master team vs master team games (using mapped names)
    master_games = df[
        (df["Team A"].isin(team_name_mapping.values())) & 
        (df["Team B"].isin(team_name_mapping.values()))
    ].copy()
    
    print(f"Filtered to {len(master_games)} master team vs master team games")
    
    return master_games


def initialize_ratings(teams: list) -> dict:
    """
    Initialize all teams with the same starting rating.
    
    Args:
        teams: List of unique team names
        
    Returns:
        Dictionary mapping team names to initial ratings
    """
    return {team: INITIAL_RATING for team in teams}


def run_elo_iterations(games_df: pd.DataFrame, ratings: dict) -> tuple:
    """
    Run iterative Elo updates until convergence or max iterations.
    
    Args:
        games_df: DataFrame with Team A, Team B, Score A, Score B columns
        ratings: Dictionary of current team ratings
        
    Returns:
        Tuple of (final_ratings, convergence_info)
    """
    print("Running Elo iterations...")
    
    convergence_info = {
        'iterations': [],
        'mean_deltas': [],
        'converged': False,
        'final_iteration': 0
    }
    
    for iteration in range(MAX_ITERS):
        deltas = []
        
        for _, game in games_df.iterrows():
            team_a = game["Team A"]
            team_b = game["Team B"]
            score_a = game["Score A"]
            score_b = game["Score B"]
            
            # Calculate goal differential
            gd = score_a - score_b
            
            # Determine actual outcome (1 = A wins, 0 = B wins, 0.5 = tie)
            if gd > 0:
                actual = 1
            elif gd < 0:
                actual = 0
            else:
                actual = 0.5
            
            # Calculate expected outcome using logistic function
            rating_diff = ratings[team_b] - ratings[team_a]
            exp_a = 1 / (1 + 10 ** (rating_diff / RATING_SCALE))
            
            # Apply goal-differential multiplier (capped)
            if USE_GOAL_DIFF_AWARE:
                mult = 1 + GOAL_DIFF_MULT * min(abs(gd), GOAL_DIFF_CAP)
            else:
                mult = 1
            
            # Calculate rating change
            change = K_FACTOR * mult * (actual - exp_a)
            
            # Update ratings
            ratings[team_a] += change
            ratings[team_b] -= change
            
            deltas.append(abs(change))
        
        # Track convergence
        mean_delta = sum(deltas) / len(deltas)
        convergence_info['iterations'].append(iteration + 1)
        convergence_info['mean_deltas'].append(mean_delta)
        
        print(f"  Iteration {iteration + 1}: Mean Delta rating = {mean_delta:.2f}")
        
        # Check convergence
        if mean_delta < CONV_TOL:
            convergence_info['converged'] = True
            convergence_info['final_iteration'] = iteration + 1
            print(f"Converged after {iteration + 1} iterations")
            break
    
    if not convergence_info['converged']:
        convergence_info['final_iteration'] = MAX_ITERS
        print(f"Reached maximum iterations ({MAX_ITERS}) without convergence")
    
    return ratings, convergence_info


def compute_opponent_strengths(games_df: pd.DataFrame, ratings: dict) -> dict:
    """
    Calculate mean opponent strength for each team.
    
    Args:
        games_df: DataFrame with game results
        ratings: Dictionary of team ratings
        
    Returns:
        Dictionary mapping team names to mean opponent strength
    """
    print("Computing opponent strengths...")
    
    # Group games by team to find opponents
    team_opponents = defaultdict(list)
    
    for _, game in games_df.iterrows():
        team_a = game["Team A"]
        team_b = game["Team B"]
        
        # Add each team's opponents
        team_opponents[team_a].append(ratings[team_b])
        team_opponents[team_b].append(ratings[team_a])
    
    # Calculate mean opponent strength for each team
    opp_strength = {}
    for team, opponent_ratings in team_opponents.items():
        if opponent_ratings:
            opp_strength[team] = mean(opponent_ratings)
        else:
            # Fallback for teams with no games (shouldn't happen with filtering)
            opp_strength[team] = INITIAL_RATING
            warnings.warn(f"No opponents found for team: {team}")
    
    return opp_strength


def normalize_sos(opp_strength: dict) -> dict:
    """
    Normalize opponent strengths to 0-1 range.
    
    Args:
        opp_strength: Dictionary of raw opponent strengths
        
    Returns:
        Dictionary of normalized SOS values
    """
    print("Normalizing SOS to 0-1 range...")
    
    values = list(opp_strength.values())
    min_val = min(values)
    max_val = max(values)
    
    # Handle edge case where all teams have same strength
    if max_val == min_val:
        print("Warning: All teams have identical strength, setting SOS to 0.5")
        return {team: 0.5 for team in opp_strength.keys()}
    
    # Normalize to 0-1 range
    normalized = {}
    for team, strength in opp_strength.items():
        normalized[team] = (strength - min_val) / (max_val - min_val)
    
    print(f"SOS range: {min_val:.1f} - {max_val:.1f} -> 0.0 - 1.0")
    
    return normalized


def compute_iterative_sos(matched_games_path: str) -> dict:
    """
    Main entry point: Compute iterative SOS for all teams.
    
    Args:
        matched_games_path: Path to Matched_Games.csv
        
    Returns:
        Dictionary mapping team names to normalized SOS values
    """
    print("=" * 60)
    print("ITERATIVE SOS ENGINE (V5.3+)")
    print("=" * 60)
    
    # Step 1: Load and filter games
    games_df = load_and_filter_games(matched_games_path)
    
    if len(games_df) == 0:
        raise ValueError("No master team games found in dataset")
    
    # Step 2: Get unique teams and initialize ratings
    teams = pd.unique(games_df[["Team A", "Team B"]].values.ravel("K"))
    teams = [t for t in teams if pd.notna(t)]  # Remove any NaN values
    
    print(f"Found {len(teams)} unique teams")
    
    ratings = initialize_ratings(teams)
    
    # Step 3: Run iterative Elo updates
    final_ratings, convergence_info = run_elo_iterations(games_df, ratings)
    
    # Step 4: Compute opponent strengths
    opp_strength = compute_opponent_strengths(games_df, final_ratings)
    
    # Step 5: Normalize to 0-1 range
    sos_normalized = normalize_sos(opp_strength)
    
    # Print summary
    print("\n" + "=" * 60)
    print("ITERATIVE SOS SUMMARY")
    print("=" * 60)
    print(f"Teams processed: {len(teams)}")
    print(f"Games processed: {len(games_df)}")
    print(f"Converged: {convergence_info['converged']}")
    print(f"Iterations: {convergence_info['final_iteration']}")
    print(f"Final mean Delta rating: {convergence_info['mean_deltas'][-1]:.2f}")
    print(f"SOS range: {min(sos_normalized.values()):.3f} - {max(sos_normalized.values()):.3f}")
    
    return sos_normalized


if __name__ == "__main__":
    # Test the implementation
    try:
        sos_dict = compute_iterative_sos("Matched_Games.csv")
        
        print("\nTop 10 teams by iterative SOS:")
        sorted_sos = sorted(sos_dict.items(), key=lambda x: x[1], reverse=True)
        for i, (team, sos) in enumerate(sorted_sos[:10], 1):
            print(f"{i:2d}. {team}: {sos:.3f}")
            
    except Exception as e:
        print(f"Error: {e}")
        raise
