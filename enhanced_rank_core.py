"""
Enhanced ranking core functions with expectation tracking and advanced features
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import config

# Import advanced expectation tracking
from advanced_expectation_tracking import add_expectation_tracking, validate_expectation_model

def calculate_expected_goal_differential(team_a: str, team_b: str, team_stats: pd.DataFrame) -> float:
    """
    Calculate expected goal differential for Team A vs Team B using simple opponent-adjusted model.
    
    Args:
        team_a: Name of team A
        team_b: Name of team B  
        team_stats: DataFrame with team statistics including Off_norm, Def_norm
        
    Returns:
        Expected goal differential (Team A - Team B)
    """
    try:
        # Get team statistics
        stats_a = team_stats[team_stats["Team"] == team_a]
        stats_b = team_stats[team_stats["Team"] == team_b]
        
        if stats_a.empty or stats_b.empty:
            return 0.0
        
        # Extract normalized offensive and defensive ratings
        off_a = stats_a.iloc[0].get("Off_norm", 0.5)
        def_a = stats_a.iloc[0].get("Def_norm", 0.5)
        off_b = stats_b.iloc[0].get("Off_norm", 0.5)
        def_b = stats_b.iloc[0].get("Def_norm", 0.5)
        
        # Simple model: expected goals = offensive rating * (1 - opponent defensive rating)
        # Scale to realistic goal expectations (youth soccer typically 0-5 goals)
        scale_factor = 2.0  # Adjust based on typical goal ranges
        
        exp_goals_a = off_a * (1 - def_b) * scale_factor
        exp_goals_b = off_b * (1 - def_a) * scale_factor
        
        return exp_goals_a - exp_goals_b
        
    except Exception:
        return 0.0

def calculate_impact_bucket(gd_delta: float) -> str:
    """
    Categorize goal differential delta into impact bucket.
    
    Args:
        gd_delta: Actual GD - Expected GD
        
    Returns:
        Impact bucket: 'good', 'neutral', or 'weak'
    """
    buckets = config.IMPACT_BUCKETS
    
    if gd_delta <= buckets[0][1]:  # <= -0.5
        return "weak"
    elif gd_delta >= buckets[2][0]:  # >= 0.5
        return "good"
    else:  # -0.5 < gd_delta < 0.5
        return "neutral"

def apply_enhanced_window_filter(games_df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply 12-month window and 20-match soft cap to games data.
    
    Args:
        games_df: DataFrame with game data including Date column
        
    Returns:
        Filtered DataFrame with enhanced windowing applied
    """
    if not config.ENABLE_EXPECTATION_TRACKING:
        return games_df
    
    # Convert Date to datetime if needed
    if not pd.api.types.is_datetime64_any_dtype(games_df["Date"]):
        games_df["Date"] = pd.to_datetime(games_df["Date"])
    
    # Apply 12-month window
    cutoff_date = pd.Timestamp.now() - pd.Timedelta(days=config.RANK_WINDOW_DAYS)
    windowed_games = games_df[games_df["Date"] >= cutoff_date].copy()
    
    # Apply 20-match soft cap per team
    enhanced_games = []
    
    for team in windowed_games["Team"].unique():
        team_games = windowed_games[windowed_games["Team"] == team].copy()
        
        # Sort by date (most recent first) and take up to RANK_MAX_MATCHES
        team_games = team_games.sort_values("Date", ascending=False)
        if len(team_games) > config.RANK_MAX_MATCHES:
            team_games = team_games.head(config.RANK_MAX_MATCHES)
        
        enhanced_games.append(team_games)
    
    if enhanced_games:
        return pd.concat(enhanced_games, ignore_index=True)
    else:
        return pd.DataFrame()

def add_expectation_tracking_enhanced(games_df: pd.DataFrame, team_stats: pd.DataFrame) -> pd.DataFrame:
    """
    Add expectation tracking using the configured model (advanced or simple).
    
    Args:
        games_df: DataFrame with game data
        team_stats: DataFrame with team statistics
        
    Returns:
        Enhanced DataFrame with expectation columns
    """
    if not config.ENABLE_EXPECTATION_TRACKING:
        return games_df
    
    # Use the advanced expectation tracking
    enhanced_df = add_expectation_tracking(games_df, team_stats)
    
    # Validate the model
    validation_metrics = validate_expectation_model(enhanced_df)
    
    # Log validation results
    if validation_metrics.get("calibration_centered", False):
        print(f"SUCCESS: Expectation model calibrated and centered (mean: {validation_metrics.get('mean_expected_gd', 0):.3f})")
    else:
        print(f"WARNING: Expectation model not properly calibrated (mean: {validation_metrics.get('mean_expected_gd', 0):.3f})")
    
    correlation = validation_metrics.get("expected_actual_correlation", 0)
    if correlation > 0:
        print(f"SUCCESS: Positive correlation between expected and actual GD: {correlation:.3f}")
    else:
        print(f"WARNING: No positive correlation between expected and actual GD: {correlation:.3f}")
    
    return enhanced_df

def add_inactivity_flags(team_stats: pd.DataFrame, games_df: pd.DataFrame) -> pd.DataFrame:
    """
    Add inactivity flags to team statistics.
    
    Args:
        team_stats: DataFrame with team statistics
        games_df: DataFrame with game data
        
    Returns:
        Enhanced DataFrame with inactivity flags
    """
    if not config.ENABLE_INACTIVITY_FLAGGING:
        return team_stats
    
    enhanced_stats = team_stats.copy()
    
    # Calculate days since last game for each team
    inactivity_flags = []
    last_game_dates = []
    
    for _, team_row in enhanced_stats.iterrows():
        team_name = team_row["Team"]
        
        # Get team's games
        team_games = games_df[games_df["Team"] == team_name]
        
        if team_games.empty:
            # No games found
            inactivity_flags.append("no_games")
            last_game_dates.append(None)
        else:
            # Find most recent game date
            if not pd.api.types.is_datetime64_any_dtype(team_games["Date"]):
                team_games["Date"] = pd.to_datetime(team_games["Date"])
            
            last_game = team_games["Date"].max()
            last_game_dates.append(last_game)
            
            # Calculate days since last game
            days_since = (pd.Timestamp.now() - last_game).days
            
            if days_since >= config.INACTIVE_HIDE_DAYS:
                inactivity_flags.append("inactive_hide")
            elif days_since >= config.INACTIVE_WARN_DAYS:
                inactivity_flags.append("inactive_warn")
            else:
                inactivity_flags.append("active")
    
    # Add new columns
    enhanced_stats["inactivity_flag"] = inactivity_flags
    enhanced_stats["last_game_date"] = last_game_dates
    
    return enhanced_stats

def add_provisional_flags(team_stats: pd.DataFrame, games_df: pd.DataFrame) -> pd.DataFrame:
    """
    Add provisional flags to team statistics with closed-loop detection.
    
    Rule v1: provisional if < 6 games OR < 3 unique cross-cluster opponents.
    """
    if not config.ENABLE_PROVISIONAL_GATING:
        return team_stats
    
    enhanced_stats = team_stats.copy()
    
    provisional_flags = []
    cross_cluster_counts = []
    provisional_reasons = []
    
    for _, team_row in enhanced_stats.iterrows():
        team_name = team_row["Team"]
        games_played = team_row.get("Games Played", 0)
        
        # Get team's games
        team_games = games_df[games_df["Team"] == team_name]
        
        # Count unique opponents (simplified cross-cluster detection)
        unique_opponents = team_games["Opponent"].nunique()
        cross_cluster_counts.append(unique_opponents)
        
        # Determine provisional status with detailed reasons
        reasons = []
        is_provisional = False
        
        if games_played < config.PROVISIONAL_MIN_GAMES:
            reasons.append(f"< {config.PROVISIONAL_MIN_GAMES} games")
            is_provisional = True
        
        if unique_opponents < config.PROVISIONAL_MIN_CROSS_CLUSTER:
            reasons.append(f"< {config.PROVISIONAL_MIN_CROSS_CLUSTER} unique opponents")
            is_provisional = True
        
        if is_provisional:
            provisional_flags.append("provisional")
            provisional_reasons.append("; ".join(reasons))
        else:
            provisional_flags.append("full")
            provisional_reasons.append("")
    
    # Add new columns
    enhanced_stats["provisional_flag"] = provisional_flags
    enhanced_stats["cross_cluster_opponents"] = cross_cluster_counts
    enhanced_stats["provisional_reason"] = provisional_reasons
    
    return enhanced_stats

def calculate_club_rankings(team_stats: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate club-level rankings by aggregating top team performances.
    
    Args:
        team_stats: DataFrame with team statistics
        
    Returns:
        DataFrame with club rankings
    """
    if not config.ENABLE_CLUB_RANKINGS:
        return pd.DataFrame()
    
    # Group by club and calculate club power score
    club_stats = []
    
    for club, club_teams in team_stats.groupby("Club"):
        if pd.isna(club) or club == "":
            continue
        
        # Get top 3 teams by power score (or all if fewer than 3)
        top_teams = club_teams.nlargest(3, "Power Score")
        club_power = top_teams["Power Score"].mean()
        
        club_stats.append({
            "Club": club,
            "Club_Power": club_power,
            "Teams_Count": len(club_teams),
            "Top_Teams": len(top_teams),
            "Avg_Power": club_teams["Power Score"].mean(),
            "Max_Power": club_teams["Power Score"].max()
        })
    
    if club_stats:
        club_df = pd.DataFrame(club_stats)
        club_df = club_df.sort_values("Club_Power", ascending=False)
        club_df["Club_Rank"] = range(1, len(club_df) + 1)
        return club_df
    
    return pd.DataFrame()

def get_what_changed_today(games_df: pd.DataFrame, team_stats: pd.DataFrame) -> Dict:
    """
    Calculate what changed today for the "What changed today?" panel.
    
    Args:
        games_df: DataFrame with game data
        team_stats: DataFrame with team statistics
        
    Returns:
        Dictionary with change metrics
    """
    if not config.ENABLE_WHAT_CHANGED:
        return {}
    
    today = pd.Timestamp.now().date()
    
    # Find games from today
    if not pd.api.types.is_datetime64_any_dtype(games_df["Date"]):
        games_df["Date"] = pd.to_datetime(games_df["Date"])
    
    today_games = games_df[games_df["Date"].dt.date == today]
    
    # Calculate metrics
    changes = {
        "new_games": len(today_games),
        "newly_ranked": 0,  # Would need historical comparison
        "rank_movers": [],  # Would need historical comparison
        "last_update": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
        "total_teams": len(team_stats),
        "active_teams": len(team_stats[team_stats.get("inactivity_flag", "active") == "active"])
    }
    
    return changes
