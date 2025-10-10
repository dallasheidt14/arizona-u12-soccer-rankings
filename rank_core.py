"""
Core ranking functions for testing and modular use.
Extracted from generate_team_rankings_v2.py for clean imports.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import config

def _robust_minmax(series, min_q=0.05, max_q=0.95):
    """Robust min-max normalization using quantiles."""
    if len(series) == 0:
        return pd.Series(dtype=float)
    
    min_val = series.quantile(min_q)
    max_val = series.quantile(max_q)
    
    if max_val == min_val:
        return pd.Series(0.5, index=series.index)
    
    normalized = (series - min_val) / (max_val - min_val)
    return np.clip(normalized, 0, 1)

def _safe_ratio(numerator, denominator, default=0.0):
    """Safely compute ratio with default for zero denominator."""
    if denominator == 0:
        return default
    return numerator / denominator

def calculate_weighted_stats(long_games_df, log_file=None):
    """Calculate weighted team statistics with recency weighting."""
    stats = {}
    
    for team, group in long_games_df.groupby("Team"):
        group = group.sort_values(by="Date", ascending=False)
        n_games = len(group)
        
        if n_games == 0:
            stats[team] = {
                "Games Played": 0,
                "Goals For": 0,
                "Goals Against": 0,
                "GFPG": 0.0,
                "GAPG": 0.0,
                "Wins": 0,
                "Losses": 0,
                "Ties": 0
            }
            continue
        
        # Calculate recent vs older segments
        recent_window = config.RECENT_WINDOW
        recent_weight = config.RECENT_WEIGHT
        
        if n_games <= recent_window:
            # All games are "recent"
            recent_games = group
            older_games = pd.DataFrame()
        else:
            recent_games = group.head(recent_window)
            older_games = group.iloc[recent_window:]
        
        # Calculate segment averages
        recent_gf_avg = recent_games["Goals For"].mean() if len(recent_games) > 0 else 0
        recent_ga_avg = recent_games["Goals Against"].mean() if len(recent_games) > 0 else 0
        older_gf_avg = older_games["Goals For"].mean() if len(older_games) > 0 else 0
        older_ga_avg = older_games["Goals Against"].mean() if len(older_games) > 0 else 0
        
        # Weight segment averages (not sums!)
        weighted_gf = recent_weight * recent_gf_avg + (1 - recent_weight) * older_gf_avg
        weighted_ga = recent_weight * recent_ga_avg + (1 - recent_weight) * older_ga_avg
        
        # Calculate win/loss/tie
        wins = (group["Goals For"] > group["Goals Against"]).sum()
        losses = (group["Goals For"] < group["Goals Against"]).sum()
        ties = (group["Goals For"] == group["Goals Against"]).sum()
        
        stats[team] = {
            "Games Played": n_games,
            "Goals For": group["Goals For"].sum(),
            "Goals Against": group["Goals Against"].sum(),
            "GFPG": weighted_gf,
            "GAPG": weighted_ga,
            "Wins": wins,
            "Losses": losses,
            "Ties": ties
        }
    
    return pd.DataFrame.from_dict(stats, orient="index").reset_index().rename(columns={"index": "Team"})

def calculate_sos(long_games_df, team_stats_df, log_file=None):
    """Calculate Strength of Schedule with recency weighting."""
    # Build opponent base strength map (from normalized Off/Def only)
    team_stats_df = team_stats_df.copy()
    off_norm = _robust_minmax(team_stats_df["GFPG"])
    def_raw = 1.0 / (1.0 + team_stats_df["GAPG"])
    def_norm = _robust_minmax(def_raw)
    
    team_stats_df["Off_norm"] = off_norm
    team_stats_df["Def_norm"] = def_norm
    team_stats_df["BaseStrength"] = 0.5 * (off_norm + def_norm)
    
    base_strength_map = team_stats_df.set_index("Team")["BaseStrength"].to_dict()
    
    # Calculate SOS for each team
    sos_scores = {}
    
    for team, group in long_games_df.groupby("Team"):
        group = group.sort_values(by="Date", ascending=False)
        n_games = len(group)
        
        if n_games == 0:
            sos_scores[team] = 0.0
            continue
        
        # Calculate recency weights
        recent_window = config.RECENT_WINDOW
        recent_weight = config.RECENT_WEIGHT
        
        if n_games <= recent_window:
            weights = np.ones(n_games) / n_games
        else:
            recent_weights = np.full(min(recent_window, n_games), recent_weight)
            older_weights = np.full(max(n_games - recent_window, 0), 1 - recent_weight)
            weights = np.concatenate([recent_weights, older_weights])
            weights = weights / weights.sum()
        
        # Calculate weighted opponent strength
        opponent_strengths = []
        for _, game in group.iterrows():
            opponent = game["Opponent"]
            strength = base_strength_map.get(opponent, 0.0)
            opponent_strengths.append(strength)
        
        sos_score = np.average(opponent_strengths, weights=weights)
        sos_scores[team] = sos_score
    
    sos_df = pd.DataFrame.from_dict(sos_scores, orient="index", columns=["SOS"]).reset_index().rename(columns={"index": "Team"})
    return sos_df

def calculate_power_scores(team_stats_df, sos_df, off_w=0.375, def_w=0.375, sos_w=0.25, penalty_thresholds=None, log_file=None):
    """Calculate normalized power scores with game count penalties."""
    if penalty_thresholds is None:
        penalty_thresholds = config.GAMES_PENALTY_THRESHOLDS
    
    # Merge stats and SOS
    merged_df = team_stats_df.merge(sos_df, on="Team", how="left")
    merged_df["SOS"] = merged_df["SOS"].fillna(0.0)
    
    # Normalize components to [0,1]
    merged_df["Off_norm"] = _robust_minmax(merged_df["GFPG"])
    def_raw = 1.0 / (1.0 + merged_df["GAPG"])
    merged_df["Def_norm"] = _robust_minmax(def_raw)
    merged_df["SOS_norm"] = _robust_minmax(merged_df["SOS"])
    
    # Calculate raw power score
    merged_df["Raw Power"] = (
        off_w * merged_df["Off_norm"] +
        def_w * merged_df["Def_norm"] +
        sos_w * merged_df["SOS_norm"]
    )
    
    # Apply game count penalties
    def apply_penalty(games_played):
        if games_played >= penalty_thresholds["full"]:
            return 1.0
        elif games_played >= penalty_thresholds["moderate"]:
            return penalty_thresholds["low_penalty"]
        else:
            return penalty_thresholds["high_penalty"]
    
    merged_df["Penalty"] = merged_df["Games Played"].apply(apply_penalty)
    merged_df["Power Score"] = merged_df["Raw Power"] * merged_df["Penalty"]
    
    # Add raw defense for testing
    merged_df["Def_raw"] = def_raw
    
    return merged_df

def enrich_game_histories_with_opponent_strength(
    long_games_df, team_stats_df, final_rank_df, recent_window, recent_weight
):
    """Enrich game histories with opponent strength and recency weights."""
    # Build base strength map from Off/Def normals
    base = team_stats_df[["Team", "GFPG", "GAPG"]].copy()
    off_norm = _robust_minmax(base["GFPG"])
    def_raw = 1.0 / (1.0 + base["GAPG"])
    def_norm = _robust_minmax(def_raw)
    base["Opp_Off_norm"] = off_norm
    base["Opp_Def_norm"] = def_norm
    base["Opponent_BaseStrength"] = 0.5 * (base["Opp_Off_norm"] + base["Opp_Def_norm"])
    opp_base_map = base.set_index("Team")[["Opponent_BaseStrength", "Opp_Off_norm", "Opp_Def_norm"]].to_dict(orient="index")

    # Team snapshots for own GFPG/GAPG
    team_snapshot_map = team_stats_df.set_index("Team")[["GFPG", "GAPG"]].to_dict(orient="index")

    # Prepare histories
    out = long_games_df.copy()
    out = out.sort_values(["Team", "Date"], ascending=[True, False]).reset_index(drop=True)

    # Attach simple lookups
    out["Opponent_BaseStrength"] = out["Opponent"].map(lambda t: opp_base_map.get(t, {}).get("Opponent_BaseStrength", 0.0))
    out["Opp_Off_norm"] = out["Opponent"].map(lambda t: opp_base_map.get(t, {}).get("Opp_Off_norm", 0.0))
    out["Opp_Def_norm"] = out["Opponent"].map(lambda t: opp_base_map.get(t, {}).get("Opp_Def_norm", 0.0))
    out["GFPG_Snapshot"] = out["Team"].map(lambda t: team_snapshot_map.get(t, {}).get("GFPG", None))
    out["GAPG_Snapshot"] = out["Team"].map(lambda t: team_snapshot_map.get(t, {}).get("GAPG", None))

    # Per-team recency weights
    out["Recency_Weight"] = 0.0
    for team, g in out.groupby("Team", sort=False):
        idx = g.index.to_list()
        n = len(g)
        if n <= recent_window:
            w = np.ones(n, dtype=float)
        else:
            w_recent = np.ones(min(recent_window, n), dtype=float) * recent_weight
            w_older = np.ones(max(n - recent_window, 0), dtype=float) * (1 - recent_weight)
            w = np.concatenate([w_recent, w_older])
        w = w / w.sum() if w.sum() > 0 else w
        out.loc[idx, "Recency_Weight"] = w

    # Nice-to-have derived columns
    out["Result"] = np.where(out["Goals For"] > out["Goals Against"], "W",
                      np.where(out["Goals For"] < out["Goals Against"], "L", "T"))
    out["GD"] = out["Goals For"] - out["Goals Against"]

    return out
