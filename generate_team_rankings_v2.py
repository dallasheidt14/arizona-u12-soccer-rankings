#!/usr/bin/env python3
"""
Arizona U12 Soccer Rankings System - Enhanced Backend
====================================================

Complete backend script with fixed mathematical logic, CLI support,
and production-ready features.

Key improvements:
- Fixed recent games weighting (rate-level, not sum-level)
- Proper component normalization to [0,1] scale
- Robust defense scoring (monotone decreasing)
- Recency-weighted SOS calculation
- CLI argument support with config overrides
- Enhanced error handling and logging
"""

import pandas as pd
import numpy as np
import argparse
import sys
import os
import json
from datetime import datetime
from pathlib import Path
from itertools import product

# Import configuration
import config

# Import enhanced ranking functions
from enhanced_rank_core import (
    apply_enhanced_window_filter,
    add_expectation_tracking_enhanced, 
    add_inactivity_flags,
    add_provisional_flags,
    calculate_club_rankings,
    get_what_changed_today
)

def log_message(message, log_file=None, level="INFO"):
    """Log message to file and console with timestamp."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] {level}: {message}"
    
    print(log_msg)
    
    if log_file:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_msg + '\n')

def setup_cli_args():
    """Set up command-line argument parsing."""
    parser = argparse.ArgumentParser(
        description="Arizona U12 Soccer Rankings System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_team_rankings.py
  python generate_team_rankings.py --state AZ --gender MALE --year 2025
  python generate_team_rankings.py --materialize --recent-weight 0.8
  python generate_team_rankings.py --off-w 0.4 --def-w 0.4 --sos-w 0.2
        """
    )
    
    # Filter arguments
    parser.add_argument('--state', type=str, default=config.DEFAULT_STATE,
                       help=f'Filter by state (default: {config.DEFAULT_STATE})')
    parser.add_argument('--gender', type=str, default=config.DEFAULT_GENDER,
                       help=f'Filter by gender (default: {config.DEFAULT_GENDER})')
    parser.add_argument('--year', type=int, default=config.DEFAULT_YEAR,
                       help=f'Filter by year (default: {config.DEFAULT_YEAR})')
    
    # Output arguments
    parser.add_argument('--materialize', action='store_true',
                       help='Create per-segment materialized output files')
    parser.add_argument('--materialize-grid', action='store_true',
                       help='Materialize ALL slice combinations discovered in the dataset (State×Gender×Year)')
    parser.add_argument('--parquet', action='store_true',
                       help='Also write .parquet files for faster dashboard loads')
    parser.add_argument('--index-json', default='rankings_index.json',
                       help='Where to write a JSON index of available slices')
    parser.add_argument('--output-dir', type=str, default='.',
                       help='Output directory for files (default: current directory)')
    
    # Algorithm arguments
    parser.add_argument('--recent-weight', type=float, default=config.RECENT_WEIGHT,
                       help=f'Weight for recent games (default: {config.RECENT_WEIGHT})')
    parser.add_argument('--recent-window', type=int, default=config.RECENT_WINDOW,
                       help=f'Number of recent games to weight (default: {config.RECENT_WINDOW})')
    
    parser.add_argument('--off-w', type=float, default=config.OFFENSE_WEIGHT,
                       help=f'Offense weight (default: {config.OFFENSE_WEIGHT})')
    parser.add_argument('--def-w', type=float, default=config.DEFENSE_WEIGHT,
                       help=f'Defense weight (default: {config.DEFENSE_WEIGHT})')
    parser.add_argument('--sos-w', type=float, default=config.SOS_WEIGHT,
                       help=f'SOS weight (default: {config.SOS_WEIGHT})')
    
    # Penalty arguments
    parser.add_argument('--penalty-full', type=int, default=config.GAMES_PENALTY_THRESHOLDS['full'],
                       help=f'Games for no penalty (default: {config.GAMES_PENALTY_THRESHOLDS["full"]})')
    parser.add_argument('--penalty-moderate', type=int, default=config.GAMES_PENALTY_THRESHOLDS['moderate'],
                       help=f'Games for moderate penalty (default: {config.GAMES_PENALTY_THRESHOLDS["moderate"]})')
    parser.add_argument('--penalty-low', type=float, default=config.GAMES_PENALTY_THRESHOLDS['low_penalty'],
                       help=f'Moderate penalty multiplier (default: {config.GAMES_PENALTY_THRESHOLDS["low_penalty"]})')
    parser.add_argument('--penalty-high', type=float, default=config.GAMES_PENALTY_THRESHOLDS['high_penalty'],
                       help=f'High penalty multiplier (default: {config.GAMES_PENALTY_THRESHOLDS["high_penalty"]})')
    
    # File arguments
    parser.add_argument('--games-file', type=str, default=config.MATCHED_GAMES_FILE,
                       help=f'Input games file (default: {config.MATCHED_GAMES_FILE})')
    parser.add_argument('--master-file', type=str, default=config.MASTER_TEAM_LIST_FILE,
                       help=f'Input master teams file (default: {config.MASTER_TEAM_LIST_FILE})')
    
    # Debug arguments
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show configuration and exit without processing')
    
    return parser.parse_args()

def validate_args(args):
    """Validate command-line arguments."""
    errors = []
    
    # Check weight sum
    weight_sum = args.off_w + args.def_w + args.sos_w
    if abs(weight_sum - 1.0) > 0.001:
        errors.append(f"Weights sum to {weight_sum:.3f}, should be 1.0")
    
    # Check individual weights
    for name, weight in [("off-w", args.off_w), ("def-w", args.def_w), ("sos-w", args.sos_w)]:
        if not (0 <= weight <= 1):
            errors.append(f"{name} ({weight}) must be between 0 and 1")
    
    # Check recent window
    if not (1 <= args.recent_window <= 50):
        errors.append(f"recent-window ({args.recent_window}) must be between 1 and 50")
    
    # Check recent weight
    if not (0 <= args.recent_weight <= 1):
        errors.append(f"recent-weight ({args.recent_weight}) must be between 0 and 1")
    
    # Check penalty multipliers
    for name, mult in [("penalty-low", args.penalty_low), ("penalty-high", args.penalty_high)]:
        if not (0 <= mult <= 1):
            errors.append(f"{name} ({mult}) must be between 0 and 1")
    
    if errors:
        raise ValueError("Argument validation failed:\n" + "\n".join(errors))

# Schema validation constants
REQUIRED_GAME_COLS = {
    "Date", "Team A", "Team B", "Score A", "Score B", "Team A Match", "Team B Match"
}
REQUIRED_MASTER_COLS = {"Team Name", "Club"}  # Core required columns

def validate_schema(games_df, master_df, log_file):
    """Validate input data schemas and fail fast on missing columns."""
    log_message("Validating input data schemas...", log_file)
    
    missing_g = REQUIRED_GAME_COLS - set(games_df.columns)
    missing_m = REQUIRED_MASTER_COLS - set(master_df.columns)
    
    if missing_g:
        raise ValueError(f"Games file missing required columns: {sorted(missing_g)}")
    if missing_m:
        raise ValueError(f"Master team list missing required columns: {sorted(missing_m)}")
    
    log_message("Schema validation passed", log_file)
    return True

def load_and_validate_data(games_file, master_file, log_file):
    """Load and validate input data files with Gold layer fallback."""
    log_message("Loading input files...", log_file)
    
    # Import the enhanced data loader
    from data_loader import load_games_data_with_fallback, get_data_source_info
    
    # Get data source info
    data_info = get_data_source_info()
    log_message(f"Data source: {data_info['data_source']}", log_file)
    
    # Load games data with automatic fallback
    try:
        games_df = load_games_data_with_fallback(games_file, log_file)
        log_message(f"Loaded {len(games_df)} games from {data_info['data_source']}", log_file)
    except Exception as e:
        log_message(f"Failed to load games data: {e}", log_file)
        raise
    
    # Load master teams data
    if not os.path.exists(master_file):
        raise FileNotFoundError(f"Master teams file not found: {master_file}")
    
    master_df = pd.read_csv(master_file)
    log_message(f"Loaded {len(master_df)} master teams from {master_file}", log_file)
    
    # Validate required columns
    required_game_cols = ['Date', 'Team A', 'Team B', 'Score A', 'Score B', 'Team A Match', 'Team B Match']
    missing_cols = [col for col in required_game_cols if col not in games_df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns in games file: {missing_cols}")
    
    required_master_cols = ['Team Name', 'Club']
    missing_master_cols = [col for col in required_master_cols if col not in master_df.columns]
    if missing_master_cols:
        raise ValueError(f"Missing required columns in master file: {missing_master_cols}")
    
    return games_df, master_df

def apply_filters(games_df, master_df, args, log_file):
    """Apply state/gender/year filters to the data."""
    original_games = len(games_df)
    original_teams = len(master_df)
    
    # Apply year filter
    if args.year:
        log_message(f"Applying year filter: {args.year}", log_file)
        games_df['Date'] = pd.to_datetime(games_df['Date'], errors='coerce')
        games_df['Year'] = games_df['Date'].dt.year
        games_df = games_df[games_df['Year'] == args.year]
        log_message(f"After year filter: {len(games_df)} games", log_file)
    
    # Note: State and gender filters will be applied after team matching
    # since we need to merge with master data first
    
    log_message(f"Filtering complete: {len(games_df)}/{original_games} games, {len(master_df)}/{original_teams} teams", log_file)
    return games_df, master_df

def filter_matched_games(games_df, log_file):
    """Filter to only matched games and validate data."""
    log_message("Validating and cleaning game data...", log_file)
    
    # Filter to matched games only
    matched_games = games_df[
        (games_df['Team A Match Type'] != 'NO_MATCH') & 
        (games_df['Team B Match Type'] != 'NO_MATCH')
    ].copy()
    
    log_message(f"Filtered to matched games: {len(matched_games)}/{len(games_df)}", log_file)
    
    # Convert dates and scores
    matched_games['Date'] = pd.to_datetime(matched_games['Date'], errors='coerce')
    matched_games['Score A'] = pd.to_numeric(matched_games['Score A'], errors='coerce')
    matched_games['Score B'] = pd.to_numeric(matched_games['Score B'], errors='coerce')
    
    # Remove invalid games
    valid_games = matched_games.dropna(subset=['Date', 'Score A', 'Score B'])
    log_message(f"Final valid games: {len(valid_games)}", log_file)
    
    return valid_games

def reshape_to_long_format(games_df, log_file):
    """Reshape games data to long format (one row per team per game)."""
    log_message("Reshaping data to long format...", log_file)
    
    # Create Team A records
    team_a_records = games_df[['Date', 'Team A Match', 'Team B Match', 'Score A', 'Score B']].copy()
    team_a_records.columns = ['Date', 'Team', 'Opponent', 'Goals For', 'Goals Against']
    
    # Create Team B records
    team_b_records = games_df[['Date', 'Team B Match', 'Team A Match', 'Score B', 'Score A']].copy()
    team_b_records.columns = ['Date', 'Team', 'Opponent', 'Goals For', 'Goals Against']
    
    # Combine and sort
    long_games = pd.concat([team_a_records, team_b_records], ignore_index=True)
    long_games = long_games.sort_values(['Team', 'Date'])
    
    log_message(f"Created {len(long_games)} team-game records", log_file)
    return long_games

# ===== NORMALIZATION HELPERS =====
def _robust_minmax(series, low_q=config.ROBUST_MIN_Q, high_q=config.ROBUST_MAX_Q):
    """Robust min-max normalization with outlier clipping."""
    s = series.astype(float).copy()
    lo = s.quantile(low_q)
    hi = s.quantile(high_q)
    s = s.clip(lower=lo, upper=hi)
    rng = (hi - lo) if (hi - lo) > 0 else 1.0
    return (s - lo) / rng

def _safe_ratio(numer, denom):
    """Safe division that returns 0 for zero denominator."""
    return numer / denom if denom > 0 else 0.0

def calculate_weighted_stats(long_games_df, recent_window, recent_weight, log_file):
    """Calculate per-team stats with proper recent games weighting."""
    log_message("Calculating weighted team statistics (fixed weighting)...", log_file)
    rows = []

    for team, g in long_games_df.groupby("Team"):
        g = g.sort_values("Date", ascending=False)
        total = len(g)
        recent = g.head(recent_window)
        older = g.iloc[recent_window:]

        # Raw sums
        r_gf = recent["Goals For"].sum()
        r_ga = recent["Goals Against"].sum()
        o_gf = older["Goals For"].sum()
        o_ga = older["Goals Against"].sum()

        if total == 0:
            continue

        if total <= recent_window:
            # No weighting when all games are "recent" by definition
            gfpg = _safe_ratio(r_gf, total)
            gapg = _safe_ratio(r_ga, total)
        else:
            # Weight segment AVERAGES, not sums
            gf_recent = _safe_ratio(r_gf, len(recent))
            gf_older = _safe_ratio(o_gf, len(older))
            ga_recent = _safe_ratio(r_ga, len(recent))
            ga_older = _safe_ratio(o_ga, len(older))

            gfpg = recent_weight * gf_recent + (1 - recent_weight) * gf_older
            gapg = recent_weight * ga_recent + (1 - recent_weight) * ga_older

        wins = (g["Goals For"] > g["Goals Against"]).sum()
        losses = (g["Goals For"] < g["Goals Against"]).sum()
        ties = (g["Goals For"] == g["Goals Against"]).sum()

        rows.append({
            "Team": team,
            "Games Played": total,
            "Wins": wins, "Losses": losses, "Ties": ties,
            "Goals For": g["Goals For"].sum(),
            "Goals Against": g["Goals Against"].sum(),
            "Goal Differential": g["Goals For"].sum() - g["Goals Against"].sum(),
            "GFPG": gfpg,
            "GAPG": gapg
        })

    df = pd.DataFrame(rows)
    log_message(f"Calculated weighted rates for {len(df)} teams", log_file)
    return df

def calculate_sos(long_games_df, team_stats_df, recent_window, recent_weight, log_file):
    """Calculate recency-weighted Strength of Schedule."""
    log_message("Calculating Strength of Schedule (normalized + recency-weighted)...", log_file)

    # Build opponent base strength from normalized GFPG and GAPG
    tmp = team_stats_df.copy()
    tmp["Off_norm"] = _robust_minmax(tmp["GFPG"])
    tmp["Def_raw"] = 1.0 / (1.0 + tmp["GAPG"])
    tmp["Def_norm"] = _robust_minmax(tmp["Def_raw"])
    tmp["OppBase"] = 0.5 * (tmp["Off_norm"] + tmp["Def_norm"])

    opp_lookup = tmp.set_index("Team")["OppBase"].to_dict()

    sos_rows = []
    for team, g in long_games_df.groupby("Team"):
        g = g.sort_values("Date", ascending=False).reset_index(drop=True)
        if g.empty:
            sos_rows.append({"Team": team, "SOS": 0.0})
            continue

        # Per-match recency weights
        n = len(g)
        if n <= recent_window:
            weights = np.ones(n, dtype=float)
        else:
            w_recent = np.ones(min(recent_window, n), dtype=float) * recent_weight
            w_older = np.ones(max(n - recent_window, 0), dtype=float) * (1 - recent_weight)
            weights = np.concatenate([w_recent, w_older])
        weights = weights / weights.sum()

        per_match = []
        for idx, row in g.iterrows():
            opp = row["Opponent"]
            per_match.append(opp_lookup.get(opp, 0.0))

        sos = float(np.dot(weights, np.array(per_match))) if per_match else 0.0
        sos_rows.append({"Team": team, "SOS": sos})

    sos_df = pd.DataFrame(sos_rows)
    log_message("SOS computed for all teams", log_file)
    return sos_df

def apply_game_count_penalty(games_played, raw_score, penalty_thresholds):
    """Apply game count penalty to raw power score."""
    if games_played >= penalty_thresholds["full"]:
        return raw_score
    elif games_played >= penalty_thresholds["moderate"]:
        return raw_score * penalty_thresholds["low_penalty"]
    else:
        return raw_score * penalty_thresholds["high_penalty"]

def calculate_power_scores(team_stats_df, sos_df, offense_weight, defense_weight, sos_weight, penalty_thresholds, log_file):
    """Calculate normalized Power Scores with proper component weighting."""
    log_message("Normalizing components and computing Power Score...", log_file)

    df = team_stats_df.merge(sos_df, on="Team", how="left")
    df["SOS"] = df["SOS"].fillna(0.0)

    # Normalized offense
    df["Off_norm"] = _robust_minmax(df["GFPG"])
    # Normalized defense (lower GA/G is better → 1/(1+GA/G), then minmax)
    df["Def_raw"] = 1.0 / (1.0 + df["GAPG"])
    df["Def_norm"] = _robust_minmax(df["Def_raw"])

    # SOS normalization
    df["SOS_norm"] = _robust_minmax(df["SOS"])

    df["Raw Power"] = (
        offense_weight * df["Off_norm"] +
        defense_weight * df["Def_norm"] +
        sos_weight * df["SOS_norm"]
    )

    df["Power Score"] = df.apply(
        lambda r: apply_game_count_penalty(r["Games Played"], r["Raw Power"], penalty_thresholds), axis=1
    )

    log_message(f"Calculated power scores for {len(df)} teams", log_file)
    return df

def add_metadata_and_rank(rankings_df, master_df, args, log_file):
    """Add metadata and create final rankings."""
    log_message("Adding metadata and creating rankings...", log_file)
    
    # Merge with master data
    merged_df = rankings_df.merge(
        master_df[['Team Name', 'Club', 'Team ID', 'State', 'Gender', 'Age Group']], 
        left_on='Team', 
        right_on='Team Name', 
        how='left'
    )
    
    # Apply state/gender filters
    if args.state:
        merged_df = merged_df[merged_df['State'] == args.state]
        log_message(f"Applied state filter '{args.state}': {len(merged_df)} teams", log_file)
    
    if args.gender:
        merged_df = merged_df[merged_df['Gender'] == args.gender]
        log_message(f"Applied gender filter '{args.gender}': {len(merged_df)} teams", log_file)
    
    # Sort by Power Score with tie-breakers
    merged_df = merged_df.sort_values(
        by=["Power Score", "SOS_norm", "Goal Differential", "Wins"],
        ascending=[False, False, False, False]
    ).reset_index(drop=True)
    
    merged_df["Rank"] = merged_df.index + 1
    
    # Add W-L-T string
    merged_df["W-L-T"] = merged_df["Wins"].astype(str) + "-" + merged_df["Losses"].astype(str) + "-" + merged_df["Ties"].astype(str)
    
    # Add Year column for slice discovery (extract from Age Group or use current year)
    if "Age Group" in merged_df.columns:
        # Extract year from Age Group (e.g., "U12" -> 2025)
        merged_df["Year"] = 2025  # Default to current year for U12
    else:
        merged_df["Year"] = 2025
    
    # Reorder columns for output
    output_cols = [
        'Rank', 'Team', 'Club', 'Team ID', 'State', 'Gender', 'Age Group', 'Year',
        'Games Played', 'Wins', 'Losses', 'Ties', 'W-L-T',
        'Goals For', 'Goals Against', 'Goal Differential',
        'GFPG', 'GAPG', 'Off_norm', 'Def_norm', 'SOS_norm', 'SOS',
        'Raw Power', 'Power Score'
    ]
    
    # Only include columns that exist
    final_cols = [col for col in output_cols if col in merged_df.columns]
    final_df = merged_df[final_cols]
    
    log_message(f"Created rankings for {len(final_df)} teams", log_file)
    return final_df

# ---- Phase 2: Game history enrichment ----
def enrich_game_histories_with_opponent_strength(
    long_games_df: pd.DataFrame,
    team_stats_df: pd.DataFrame,
    final_rank_df: pd.DataFrame,
    recent_window: int,
    recent_weight: float,
) -> pd.DataFrame:
    """
    Returns per-team per-match histories enriched with opponent base strength and recency weights.
    - Opponent_BaseStrength is built ONLY from normalized Off/Def (no SOS), to avoid recursion.
    - Recency_Weight matches the SOS computation (recent_window, recent_weight).
    - Optionally includes opponent final Power for display.
    """
    log_message("Enriching game histories with opponent strength and recency weights...", None)
    
    # Build base strength map from Off/Def normals (already computed in Phase 1)
    base = team_stats_df[["Team", "GFPG", "GAPG"]].copy()
    # Recompute normalized components exactly like Phase 1 to avoid drift
    off_norm = _robust_minmax(base["GFPG"])
    def_raw = 1.0 / (1.0 + base["GAPG"])
    def_norm = _robust_minmax(def_raw)
    base["Opp_Off_norm"] = off_norm
    base["Opp_Def_norm"] = def_norm
    base["Opponent_BaseStrength"] = 0.5 * (base["Opp_Off_norm"] + base["Opp_Def_norm"])
    opp_base_map = base.set_index("Team")[["Opponent_BaseStrength", "Opp_Off_norm", "Opp_Def_norm"]].to_dict(orient="index")

    # Optional cosmetic: opponent final Power (post-penalty) for UI
    opp_power_map = {}
    if "Power Score" in final_rank_df.columns:
        opp_power_map = final_rank_df.set_index("Team")["Power Score"].to_dict()

    # Team snapshots for own GFPG/GAPG (handy in UI rows)
    team_snapshot_map = team_stats_df.set_index("Team")[["GFPG", "GAPG"]].to_dict(orient="index")

    # Prepare histories
    out = long_games_df.copy()
    out = out.sort_values(["Team", "Date"], ascending=[True, False]).reset_index(drop=True)

    # Attach simple lookups
    out["Opponent_BaseStrength"] = out["Opponent"].map(lambda t: opp_base_map.get(t, {}).get("Opponent_BaseStrength", 0.0))
    out["Opp_Off_norm"] = out["Opponent"].map(lambda t: opp_base_map.get(t, {}).get("Opp_Off_norm", 0.0))
    out["Opp_Def_norm"] = out["Opponent"].map(lambda t: opp_base_map.get(t, {}).get("Opp_Def_norm", 0.0))
    out["Opp_Power (final)"] = out["Opponent"].map(lambda t: opp_power_map.get(t, None))
    out["GFPG_Snapshot"] = out["Team"].map(lambda t: team_snapshot_map.get(t, {}).get("GFPG", None))
    out["GAPG_Snapshot"] = out["Team"].map(lambda t: team_snapshot_map.get(t, {}).get("GAPG", None))

    # Per-team recency weights (exactly mirroring SOS logic)
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

    # Nice-to-have derived columns for UI
    out["Result"] = np.where(out["Goals For"] > out["Goals Against"], "W",
                      np.where(out["Goals For"] < out["Goals Against"], "L", "T"))
    out["GD"] = out["Goals For"] - out["Goals Against"]

    log_message(f"Enriched {len(out)} game history records with opponent strength data", None)
    return out

def save_outputs(rankings_df, enriched_histories_df, args, log_file):
    """Save output files."""
    log_message("Saving output files...", log_file)
    
    # Ensure output directory exists
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Main rankings file
    rankings_path = output_dir / config.RANKINGS_FILE
    rankings_df.to_csv(rankings_path, index=False)
    log_message(f"Saved rankings to {rankings_path}", log_file)
    
    # Enhanced game histories file
    histories_path = output_dir / config.GAME_HISTORIES_FILE
    enriched_histories_df.to_csv(histories_path, index=False)
    log_message(f"Saved enhanced game histories to {histories_path}", log_file)
    
    # Materialized outputs if requested
    if args.materialize:
        create_materialized_outputs(rankings_df, enriched_histories_df, args, log_file)

def create_materialized_outputs(rankings_df, enriched_histories_df, args, log_file):
    """Create materialized output files for different segments."""
    log_message("Creating materialized outputs...", log_file)
    
    output_dir = Path(args.output_dir)
    
    # Create filename pattern for rankings
    parts = []
    if args.state:
        parts.append(args.state)
    if args.gender:
        parts.append(args.gender)
    if args.year:
        parts.append(str(args.year))
    
    if parts:
        # Rankings materialized output
        rankings_filename = f"Rankings_{'_'.join(parts)}.csv"
        rankings_materialized_path = output_dir / rankings_filename
        rankings_df.to_csv(rankings_materialized_path, index=False)
        log_message(f"Saved materialized rankings to {rankings_materialized_path}", log_file)
        
        # Game histories materialized output
        histories_filename = f"Team_Game_Histories_{'_'.join(parts)}.csv"
        histories_materialized_path = output_dir / histories_filename
        enriched_histories_df.to_csv(histories_materialized_path, index=False)
        log_message(f"Saved materialized game histories to {histories_materialized_path}", log_file)
        
        # Write Parquet files if requested
        if args.parquet:
            try:
                rankings_parquet_path = output_dir / f"Rankings_{'_'.join(parts)}.parquet"
                rankings_df.to_parquet(rankings_parquet_path, index=False)
                log_message(f"Saved materialized rankings Parquet to {rankings_parquet_path}", log_file)
                
                histories_parquet_path = output_dir / f"Team_Game_Histories_{'_'.join(parts)}.parquet"
                enriched_histories_df.to_parquet(histories_parquet_path, index=False)
                log_message(f"Saved materialized game histories Parquet to {histories_parquet_path}", log_file)
            except Exception as e:
                error_msg = f"Parquet write failed for materialized outputs: {e}"
                print(f"[WARN] {error_msg}")
                log_message(error_msg, log_file, "WARNING")

# ---- Phase 3: Smart materialization and fast I/O ----
SLICE_NONE = {"state": None, "gender": None, "year": None}

def _unique_nonempty(series):
    """Get unique non-empty values from a pandas Series."""
    vals = sorted({v for v in series.dropna().unique().tolist() if str(v).strip() != ""})
    return vals

def discover_slices(ranked_df, histories_df):
    """Discover all valid slice combinations in the data."""
    # Expect these columns exist after Phase 1 wiring; if not, treat as empty
    states = _unique_nonempty(ranked_df.get("State", pd.Series(dtype=object)))
    genders = _unique_nonempty(ranked_df.get("Gender", pd.Series(dtype=object)))
    years = _unique_nonempty(ranked_df.get("Year", pd.Series(dtype=object)))

    # Always include the global all-slice
    slices = [SLICE_NONE]
    # Build cartesian product of present values
    for s, g, y in product(states or [None], genders or [None], years or [None]):
        slices.append({"state": s, "gender": g, "year": y})
    
    # De-duplicate (in case any list is empty)
    seen, uniq = set(), []
    for sl in slices:
        key = (sl["state"], sl["gender"], sl["year"])
        if key not in seen:
            uniq.append(sl)
            seen.add(key)
    
    return uniq

def apply_slice(df, sl):
    """Apply a slice filter to a dataframe."""
    out = df
    if sl["state"] is not None and "State" in out.columns:
        out = out[out["State"] == sl["state"]]
    if sl["gender"] is not None and "Gender" in out.columns:
        out = out[out["Gender"] == sl["gender"]]
    if sl["year"] is not None and "Year" in out.columns:
        out = out[out["Year"] == sl["year"]]
    return out

def suffix_from_slice(sl):
    """Generate filename suffix from slice parameters."""
    parts = []
    if sl["state"]:
        parts.append(sl["state"])
    if sl["gender"]:
        parts.append(str(sl["gender"]))
    if sl["year"]:
        parts.append(str(sl["year"]))
    return ("_" + "_".join(parts)) if parts else ""

def write_dual_format(df, base_name, write_parquet=False, log_file=None):
    """Write dataframe in both CSV and optionally Parquet formats."""
    csv_path = f"{base_name}.csv"
    df.to_csv(csv_path, index=False)
    
    if write_parquet:
        try:
            df.to_parquet(f"{base_name}.parquet", index=False)
            if log_file:
                log_message(f"Wrote Parquet: {base_name}.parquet", log_file)
        except Exception as e:
            # Don't fail the run; log and continue with CSV only
            error_msg = f"Parquet write failed for {base_name}: {e}"
            print(f"[WARN] {error_msg}")
            if log_file:
                log_message(error_msg, log_file, "WARNING")
    
    return csv_path

def materialize_grid(ranked_df, hist_df, write_parquet, index_json_path, log_file):
    """Materialize all discovered slice combinations."""
    log_message("Discovering slice combinations...", log_file)
    slices = discover_slices(ranked_df, hist_df)
    log_message(f"Found {len(slices)} slice combinations", log_file)
    
    out_index = []

    for sl in slices:
        sfx = suffix_from_slice(sl)
        r_df = apply_slice(ranked_df, sl)
        h_df = apply_slice(hist_df, sl)

        # Skip empty slices except the global all-slice
        if sfx and (r_df.empty or h_df.empty):
            log_message(f"Skipping empty slice: {sfx}", log_file)
            continue

        r_name = f"Rankings{sfx}"
        h_name = f"Team_Game_Histories{sfx}"

        r_csv = write_dual_format(r_df, r_name, write_parquet, log_file)
        h_csv = write_dual_format(h_df, h_name, write_parquet, log_file)

        out_index.append({
            "state": sl["state"], 
            "gender": sl["gender"], 
            "year": sl["year"],
            "rankings": Path(r_csv).name,
            "histories": Path(h_csv).name,
            "teams": int(r_df["Team"].nunique()) if "Team" in r_df.columns else 0,
            "games": int(len(h_df))
        })
        
        log_message(f"Materialized slice {sfx or 'All'}: {len(r_df)} teams, {len(h_df)} games", log_file)

    # Write a small discovery index for the UI
    with open(index_json_path, "w", encoding="utf-8") as f:
        json.dump({"slices": out_index}, f, indent=2)
    
    log_message(f"Wrote index JSON with {len(out_index)} slices to {index_json_path}", log_file)
    return out_index

def print_summary(rankings_df, args, log_file):
    """Print summary statistics."""
    log_message("=" * 60, log_file)
    log_message("RANKING SYSTEM SUMMARY", log_file)
    log_message("=" * 60, log_file)
    
    log_message(f"Total Teams Ranked: {len(rankings_df)}", log_file)
    log_message(f"Average Games per Team: {rankings_df['Games Played'].mean():.1f}", log_file)
    
    log_message("\nConfiguration Used:", log_file)
    log_message(f"  Recent Weight: {args.recent_weight}", log_file)
    log_message(f"  Recent Window: {args.recent_window}", log_file)
    log_message(f"  Offense Weight: {args.off_w}", log_file)
    log_message(f"  Defense Weight: {args.def_w}", log_file)
    log_message(f"  SOS Weight: {args.sos_w}", log_file)
    
    log_message("\nTop 10 Teams:", log_file)
    log_message("-" * 50, log_file)
    for i, row in rankings_df.head(10).iterrows():
        log_message(f"  {row['Rank']:2d}. {row['Team'][:40]:<40} Power: {row['Power Score']:.3f}", log_file)

def main():
    """Main execution function."""
    try:
        # Parse command-line arguments
        args = setup_cli_args()
        
        # Validate arguments
        validate_args(args)
        
        # Set up logging
        log_file = Path(args.output_dir) / config.LOGS_FILE
        log_file.parent.mkdir(exist_ok=True)
        
        # Clear previous log
        if log_file.exists():
            log_file.unlink()
        
        log_message("Arizona U12 Soccer Rankings System - Enhanced Backend", log_file)
        log_message("=" * 60, log_file)
        
        # Print configuration
        log_message("Configuration:", log_file)
        log_message(f"  Recent Weight: {args.recent_weight}", log_file)
        log_message(f"  Recent Window: {args.recent_window}", log_file)
        log_message(f"  Offense Weight: {args.off_w}", log_file)
        log_message(f"  Defense Weight: {args.def_w}", log_file)
        log_message(f"  SOS Weight: {args.sos_w}", log_file)
        log_message(f"  Filters: State={args.state}, Gender={args.gender}, Year={args.year}", log_file)
        log_message(f"  Materialize: {args.materialize}", log_file)
        
        if args.dry_run:
            log_message("Dry run complete - no processing performed", log_file)
            return
        
        # Load and validate data
        games_df, master_df = load_and_validate_data(args.games_file, args.master_file, log_file)
        
        # Validate schemas
        validate_schema(games_df, master_df, log_file)
        
        # Apply filters
        games_df, master_df = apply_filters(games_df, master_df, args, log_file)
        
        # Filter to matched games
        matched_games = filter_matched_games(games_df, log_file)
        
        # Reshape to long format
        long_games = reshape_to_long_format(matched_games, log_file)
        
        # Phase A/B: Apply enhanced features
        log_message("Applying enhanced ranking features...", log_file)
        
        # Apply 12-month/20-match window filter
        if config.ENABLE_EXPECTATION_TRACKING:
            original_count = len(long_games)
            long_games = apply_enhanced_window_filter(long_games)
            filtered_count = len(long_games)
            log_message(f"Applied window filter: {original_count} -> {filtered_count} games", log_file)
        
        # Calculate team statistics
        team_stats = calculate_weighted_stats(long_games, args.recent_window, args.recent_weight, log_file)
        
        # Calculate SOS
        sos_df = calculate_sos(long_games, team_stats, args.recent_window, args.recent_weight, log_file)
        
        # Calculate power scores
        penalty_thresholds = {
            "full": args.penalty_full,
            "moderate": args.penalty_moderate,
            "low_penalty": args.penalty_low,
            "high_penalty": args.penalty_high
        }
        
        rankings_df = calculate_power_scores(
            team_stats, sos_df, args.off_w, args.def_w, args.sos_w, penalty_thresholds, log_file
        )
        
        # Add metadata and create final rankings
        final_rankings = add_metadata_and_rank(rankings_df, master_df, args, log_file)
        
        # Phase 2: Enrich game histories with opponent strength and recency weights
        enriched_histories = enrich_game_histories_with_opponent_strength(
            long_games_df=long_games,
            team_stats_df=team_stats,
            final_rank_df=final_rankings,
            recent_window=args.recent_window,
            recent_weight=args.recent_weight
        )
        
        
        # Phase B: Add enhanced tracking features
        log_message("Adding enhanced tracking features...", log_file)
        
        # Add expectation tracking to game histories
        if config.ENABLE_EXPECTATION_TRACKING:
            enriched_histories = add_expectation_tracking_enhanced(enriched_histories, team_stats)
            log_message("Added advanced expectation tracking to game histories", log_file)
        
        # Save outputs
        save_outputs(final_rankings, enriched_histories, args, log_file)
        
        # Phase 3: Grid materialization if requested
        if args.materialize_grid:
            log_message("Starting grid materialization...", log_file)
            index_path = Path(args.output_dir) / args.index_json
            materialize_grid(
                ranked_df=final_rankings,
                hist_df=enriched_histories,
                write_parquet=args.parquet,
                index_json_path=str(index_path),
                log_file=log_file
            )
        
        # Print summary
        print_summary(final_rankings, args, log_file)
        
        log_message("\nRanking system complete!", log_file)
        log_message(f"Check the following files:", log_file)
        log_message(f"  - {Path(args.output_dir) / config.RANKINGS_FILE}", log_file)
        log_message(f"  - {Path(args.output_dir) / config.GAME_HISTORIES_FILE}", log_file)
        log_message(f"  - {log_file}", log_file)
        
    except Exception as e:
        error_msg = f"Error in main execution: {e}"
        print(error_msg)
        if 'log_file' in locals():
            log_message(error_msg, log_file, "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    main()
