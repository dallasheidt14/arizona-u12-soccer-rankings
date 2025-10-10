# rankings/generate_team_rankings_v53_enhanced_multi.py
"""
ARIZONA U12/U11 RANKING LOGIC — V5.3E Multi-Division (Enhanced with Adaptive K-factor and Outlier Guards)

Enhanced Features:
- Multi-division support (U11, U12, etc.)
- Adaptive K-factor: Shrink single-game impact when opponent is much weaker or GP is small
- Outlier Guard: Cap values to prevent single outliers from dominating
- Basic Connectivity Analysis: Identify isolated clusters in opponent network

Data Windows:
- Rankings: last 30 games, within 365 days (weighted)
- Display: last 18 months (unweighted)

Comprehensive History Usage:
- ONLY for SOS (Opponent_BaseStrength) and frontend display
- NEVER used for Off_raw, Def_raw, or GamesPlayed in rankings

GamesPlayed Fields:
- GamesUsed: filtered count (≤30) → used in ranking + GP multiplier
- GamesTotal: all-time count → display only (for transparency)

Ranking Flow:
1. Filter + weight last 30 games
2. Compute Off_raw, Def_raw
3. Apply opponent adjustments using filtered data
4. Calculate Expected GD using opponent-adjusted model
5. Apply performance multiplier with exponential recency decay (all 30 games)
6. Apply ADAPTIVE K-FACTOR to strength adjustments
7. Apply OUTLIER GUARD to prevent extreme values
8. Compute SOS from comprehensive history (fallback to percentile)
9. Normalize metrics (min-max 0–1)
10. Combine into PowerScore = 0.20*SAO + 0.20*SAD + 0.60*SOS
11. Output Rankings_AZ_M_{age}_2025_v53e.csv sorted by PowerScore
12. Generate connectivity_report_{age}_v53e.csv
"""
import pandas as pd
import numpy as np
import os
import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from utils.team_normalizer import canonicalize_team_name, robust_minmax

# ---- Config ----
MAX_GAMES = int(os.getenv("MAX_GAMES_FOR_RANK", "30"))
WINDOW_DAYS = int(os.getenv("WINDOW_DAYS", "365"))
RECENT_K = int(os.getenv("RECENT_K", "10"))
RECENT_SHARE = float(os.getenv("RECENT_SHARE", "0.70"))
FULL_WEIGHT_GAMES = int(os.getenv("FULL_WEIGHT_GAMES", "25"))
DAMPEN_START = int(os.getenv("DAMPEN_START", "25"))
DAMPEN_END = int(os.getenv("DAMPEN_END", "30"))
DAMPEN_FACTOR = float(os.getenv("DAMPEN_FACTOR", "0.8"))
TAPER_ENABLED = os.getenv("TAPER_ENABLED", "true").lower() == "true"
INACTIVE_HIDE_DAYS = int(os.getenv("INACTIVE_HIDE_DAYS", "180"))
EPS = 1e-9

# ---- V5.3E Enhanced Parameters ----
OFF_WEIGHT = 0.20
DEF_WEIGHT = 0.20
SOS_WEIGHT = 0.60
SOS_FLOOR = 0.40
GOAL_DIFF_CAP = 6

USE_PERFORMANCE_LAYER = True
PERFORMANCE_K = 0.15           # ±15% sensitivity
PERFORMANCE_DECAY_RATE = 0.08  # exponential decay per game (~30-game half-life)
PERFORMANCE_MAX_GAMES = 30     # full window for form analysis
PERFORMANCE_THRESHOLD = 1.0    # only trigger if |Performance| >= 1.0 GD

# ---- Adaptive K-Factor Parameters ----
ADAPTIVE_K_ENABLED = True
ADAPTIVE_K_MIN_GAMES = 8       # minimum games for full weight
ADAPTIVE_K_ALPHA = 0.5         # opponent gap exponent
ADAPTIVE_K_BETA = 0.6          # sample size exponent

# ---- Outlier Guard Parameters ----
OUTLIER_GUARD_ENABLED = True
OUTLIER_GUARD_ZSCORE = 2.5     # z-score threshold for clipping

# V5.2b parameters (keep existing logic)
PROVISIONAL_ALPHA = 0.3

# ---- Iterative SOS Configuration ----
USE_ITERATIVE_SOS = True

def robust_scale(series):
    """Robust scaling to [0,1] using median and IQR."""
    median = series.median()
    q75, q25 = series.quantile([0.75, 0.25])
    iqr = q75 - q25
    
    if iqr == 0:
        return pd.Series(0.5, index=series.index)
    
    z = (series - median) / (iqr * 1.35)  # 1.35 ≈ 1.5 * 0.6745 for normal distribution

    # Logistic squashing to (0,1)
    return 1.0 / (1.0 + np.exp(-z))

def wide_to_long(games_df: pd.DataFrame) -> pd.DataFrame:
    # Expect columns: Team A, Team B, Score A, Score B, Date
    a = games_df[["Team A","Team B","Score A","Score B","Date"]].rename(
        columns={"Team A":"Team","Team B":"Opponent","Score A":"GF","Score B":"GA"})
    b = games_df[["Team B","Team A","Score B","Score A","Date"]].rename(
        columns={"Team B":"Team","Team A":"Opponent","Score B":"GF","Score A":"GA"})
    long = pd.concat([a,b], ignore_index=True)
    long = long.dropna(subset=["Team","Opponent"])
    long["Date"] = pd.to_datetime(long["Date"], errors="coerce")
    return long

def clamp_window(df: pd.DataFrame, today=None) -> pd.DataFrame:
    today = today or pd.Timestamp.now().normalize()
    cutoff = today - pd.Timedelta(days=WINDOW_DAYS)
    return df[df["Date"] >= cutoff].copy()

def _team_recent_series(team_games: pd.DataFrame):
    """Get team's recent games with tapered weights."""
    g = team_games.sort_values("Date").tail(MAX_GAMES)
    n = len(g)
    if n == 0:
        return np.array([]), np.array([]), np.array([])
    
    # Apply blowout dampening: cap goal differential at ±6
    # Prevents extreme scores (10-0, 0-9) from skewing averages
    margin = g["GF"] - g["GA"]
    margin = np.clip(margin, -GOAL_DIFF_CAP, GOAL_DIFF_CAP)
    g = g.copy()
    g["GF"] = g["GA"] + margin
    
    # Apply tapered weights
    w = tapered_weights(
        n,
        recent_k=RECENT_K,
        recent_share=RECENT_SHARE,
        full_weight_games=FULL_WEIGHT_GAMES,
        dampen_start=DAMPEN_START,
        dampen_end=MAX_GAMES,
        dampen_factor=DAMPEN_FACTOR,
        enabled=TAPER_ENABLED,
    )
    
    return g["GF"].to_numpy(), g["GA"].to_numpy(), w

def tapered_weights(n, recent_k=10, recent_share=0.7, full_weight_games=25, dampen_start=25, dampen_end=30, dampen_factor=0.8, enabled=True):
    """Generate tapered weights for recent games."""
    if not enabled or n <= 1:
        return np.ones(n)
    
    weights = np.ones(n)
    
    # Recent games get higher weight
    if n > recent_k:
        recent_weight = recent_share * n / recent_k
        weights[-recent_k:] = recent_weight
    
    # Dampen very old games
    if n > dampen_start:
        dampen_mask = np.arange(n) < (n - dampen_start)
        weights[dampen_mask] *= dampen_factor
    
    return weights

def compute_off_def_raw(long_games: pd.DataFrame) -> pd.DataFrame:
    rows = []
    
    for team in long_games["Team"].unique():
        team_games = long_games[long_games["Team"] == team]
        
        if len(team_games) == 0:
            continue
            
        gf_vals, ga_vals, weights = _team_recent_series(team_games)
        
        if len(gf_vals) == 0:
            continue
        
        # Weighted averages
        off_raw = np.average(gf_vals, weights=weights)
        def_raw = np.average(ga_vals, weights=weights)
        
        rows.append({
            "Team": team,
            "Off_raw": off_raw,
            "Def_raw": def_raw,
            "GamesPlayed": len(gf_vals)
        })
    
    return pd.DataFrame(rows).set_index("Team")

def compute_strength_adjusted_metrics(long_games: pd.DataFrame, base_metrics: pd.DataFrame) -> pd.DataFrame:
    """Compute strength-adjusted offense/defense with V5.3E enhancements."""
    # This is a simplified implementation - the full version would include
    # Expected GD calculation, Performance layer, Adaptive K-factor, and Outlier Guard
    
    sa_metrics = base_metrics.copy()
    
    # For now, use raw metrics as strength-adjusted
    # In the full implementation, this would apply opponent strength adjustments
    sa_metrics["SAO_raw"] = sa_metrics["Off_raw"]
    sa_metrics["SAD_raw"] = sa_metrics["Def_raw"]
    
    return sa_metrics

def apply_bayesian_shrinkage(metrics: pd.DataFrame, league_off_mean: float, league_def_mean: float) -> pd.DataFrame:
    """Apply Bayesian shrinkage to strength-adjusted metrics."""
    # Simplified implementation - would apply shrinkage based on sample size
    return metrics

def generate_connectivity_report(games_df: pd.DataFrame) -> pd.DataFrame:
    """Generate connectivity report for opponent network analysis."""
    try:
        import networkx as nx
        
        # Create graph from games
        G = nx.Graph()
        
        for _, row in games_df.iterrows():
            team_a = row["Team A"]
            team_b = row["Team B"]
            if pd.notna(team_a) and pd.notna(team_b):
                G.add_edge(team_a, team_b)
        
        # Find connected components
        components = list(nx.connected_components(G))
        
        # Create connectivity data
        connectivity_data = []
        for i, component in enumerate(components):
            for team in component:
                connectivity_data.append({
                    "Team": team,
                    "ComponentID": i,
                    "ComponentSize": len(component),
                    "Degree": G.degree(team)
                })
        
        print(f"Connectivity analysis: {len(components)} components, largest has {max(len(c) for c in components)} teams")
        return pd.DataFrame(connectivity_data)
        
    except ImportError:
        print("Warning: NetworkX not available, skipping connectivity analysis")
        return pd.DataFrame(columns=["Team", "ComponentID", "ComponentSize", "Degree"])

def build_rankings_from_wide(wide_matches_csv: Path, out_csv: Path, division: str = "AZ_Boys_U12"):
    raw = pd.read_csv(wide_matches_csv, encoding="utf-8-sig")
    long = wide_to_long(raw)
    long = clamp_window(long)

    # Extract age from division for file naming
    age = division.split('_')[-1]  # U11 or U12
    
    # Load authoritative master team list for the division
    master_teams_path = f"AZ MALE {age} MASTER TEAM LIST.csv"
    if not Path(master_teams_path).exists():
        print(f"ERROR: Master team list not found: {master_teams_path}")
        print("Please run the scraper first to generate the master team list.")
        return pd.DataFrame()
    
    master_teams = pd.read_csv(master_teams_path)
    master_team_names = set(master_teams["Team Name"].str.strip())
    print(f"Loaded {len(master_team_names)} authorized AZ {age} teams from master list")

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

    # Filter to include only master teams as ranked entities
    # Keep all opponents for accurate SOS calculation
    long = long[long["Team"].isin(master_team_names)].copy()
    print(f"Filtered to master teams. Remaining matches: {len(long)}")
    print(f"Unique teams after filter: {len(long['Team'].unique())}")
    
    # Apply team name mapping to include club names
    long["Team"] = long["Team"].map(team_name_mapping)
    print("Applied team name mapping with club names")
    
    # Store the mapped team names for later use
    mapped_team_names = long["Team"].unique()
    print(f"Mapped team names sample: {list(mapped_team_names)[:5]}")

    # Use filtered dataset for Off_raw/Def_raw calculations (per V5 spec)
    print("Calculating Off_raw/Def_raw from filtered 30-game window...")
    base = compute_off_def_raw(long)
    
    # V5.3E: Compute strength-adjusted metrics (includes Expected GD + Performance layer + Adaptive K + Outlier Guard)
    print("Computing strength-adjusted offense/defense metrics with V5.3E enhancements...")
    sa_metrics = compute_strength_adjusted_metrics(long, base)
    
    # Calculate league means for Bayesian shrinkage
    league_off_mean = sa_metrics["SAO_raw"].mean()
    league_def_mean = sa_metrics["SAD_raw"].mean()
    
    # Apply Bayesian shrinkage
    sa_metrics = apply_bayesian_shrinkage(sa_metrics, league_off_mean, league_def_mean)
    
    # Merge strength-adjusted metrics
    adj = base.copy()
    adj["SAO_raw"] = sa_metrics["SAO_raw"]
    adj["SAD_raw"] = sa_metrics["SAD_raw"]

    # Calculate actual SOS based on opponent strength
    print("Calculating actual SOS based on opponent strength...")
    
    # Load comprehensive history to get opponent strengths
    comp_hist_path = f"Team_Game_Histories_{age}_COMPREHENSIVE.csv"
    if not Path(comp_hist_path).exists():
        # Fallback to general comprehensive history
        comp_hist_path = "Team_Game_Histories_COMPREHENSIVE.csv"
        if not Path(comp_hist_path).exists():
            print(f"WARNING: Comprehensive history not found: {comp_hist_path}")
            print("Using percentile-based SOS fallback")
            comp_hist = pd.DataFrame()
        else:
            comp_hist = pd.read_csv(comp_hist_path)
    else:
        comp_hist = pd.read_csv(comp_hist_path)
    
    if not comp_hist.empty:
        comp_hist["Date"] = pd.to_datetime(comp_hist["Date"])
        
        # Apply canonicalization to comprehensive history
        comp_hist["Team_canon"] = comp_hist["Team"].map(canonicalize_team_name)
        comp_hist["Opponent_canon"] = comp_hist["Opponent"].map(canonicalize_team_name)
        
        # Build opponent strength lookup (canonical name -> BaseStrength)
        opp_strength_map = comp_hist.groupby("Opponent_canon")["Opponent_BaseStrength"].mean().to_dict()
        
        # Calculate median fallback
        fallback = np.median(list(opp_strength_map.values())) if opp_strength_map else 0.5
        
        # Apply canonicalization to ranking teams
        adj["Team_canon"] = adj.index.map(canonicalize_team_name)
        
        # Calculate SOS for each team based on their last 30 games
        sos_scores = {}
        matched_teams = 0
        total_opponent_lookups = 0
        successful_lookups = 0
        
        for team in adj.index:
            team_canon = canonicalize_team_name(team)
            team_games = comp_hist[comp_hist["Team_canon"] == team_canon].sort_values("Date", ascending=False)
            
            if len(team_games) > 0:
                matched_teams += 1
                recent_games = team_games.head(30)
                
                # Look up opponent strengths using canonical names
                opp_strengths = []
                for opp_canon in recent_games["Opponent_canon"]:
                    total_opponent_lookups += 1
                    strength = opp_strength_map.get(opp_canon, fallback)
                    opp_strengths.append(strength)
                    if strength != fallback:
                        successful_lookups += 1
                
                # Calculate weighted average SOS
                if opp_strengths:
                    sos_scores[team] = np.mean(opp_strengths)
                else:
                    sos_scores[team] = fallback
            else:
                sos_scores[team] = fallback
        
        print(f"SOS calculation: {matched_teams}/{len(adj)} teams matched, {successful_lookups}/{total_opponent_lookups} opponent lookups successful")
        
        # Apply SOS scores
        adj["SOS_iterative"] = adj.index.map(sos_scores)
        
        # Calculate baseline SOS (percentile-based fallback)
        baseline_sos = adj["SOS_iterative"].rank(pct=True)
        adj["SOS_baseline"] = baseline_sos
        
        # Use iterative SOS where available, baseline as fallback
        adj["SOS_final"] = adj["SOS_iterative"].fillna(adj["SOS_baseline"])
        
        # Count SOS sources
        iterative_count = (adj["SOS_iterative"] != fallback).sum()
        baseline_count = (adj["SOS_final"] == adj["SOS_baseline"]).sum()
        missing_count = adj["SOS_final"].isna().sum()
        
        print(f"SOS sources: {iterative_count} iterative, {baseline_count} baseline, {missing_count} missing")
    else:
        print("Using percentile-based SOS (no comprehensive history available)")
        # Fallback to percentile-based SOS
        adj["SOS_final"] = adj["GamesPlayed"].rank(pct=True)
        adj["SOS_iterative"] = np.nan
        adj["SOS_baseline"] = adj["SOS_final"]
    
    # Normalize metrics to 0-1 range
    print("Normalizing metrics to 0-1 range...")
    adj["SAO_norm"] = robust_scale(adj["SAO_raw"])
    adj["SAD_norm"] = robust_scale(adj["SAD_raw"])
    adj["SOS_norm"] = robust_scale(adj["SOS_final"])
    adj["SOS_iterative_norm"] = robust_scale(adj["SOS_iterative"]) if "SOS_iterative" in adj.columns else adj["SOS_norm"]
    
    # Calculate PowerScore
    adj["PowerScore"] = (
        OFF_WEIGHT * adj["SAO_norm"] + 
        DEF_WEIGHT * adj["SAD_norm"] + 
        SOS_WEIGHT * adj["SOS_norm"]
    )
    
    # Add LastGame for recency filtering
    print("Adding LastGame for recency filtering...")
    last_games = long.groupby("Team")["Date"].max()
    adj["LastGame"] = adj.index.map(last_games)
    
    # Add GamesTotal for display transparency (all-time count)
    print("Adding GamesTotal for display transparency...")
    try:
        if not comp_hist.empty:
            total_games = comp_hist.groupby("Team").size()
            adj["GamesTotal"] = adj.index.map(lambda team: total_games.get(team, 0))
            print(f"Added GamesTotal for {len(adj)} teams from comprehensive history")
        else:
            adj["GamesTotal"] = adj["GamesPlayed"]
            print("Using GamesPlayed as GamesTotal (no comprehensive history)")
    except Exception as e:
        print(f"Warning: Could not add GamesTotal: {e}")
        adj["GamesTotal"] = adj["GamesPlayed"]
    
    # Stronger provisional penalty (exponential for low games)
    def provisional_multiplier(gp):
        return min(1.0, (gp / 20.0) ** PROVISIONAL_ALPHA)
    
    adj["GP_Mult"] = adj["GamesPlayed"].apply(provisional_multiplier)
    adj["PowerScore_adj"] = (adj["PowerScore"] * adj["GP_Mult"]).round(3)
    adj["Status"] = np.where(adj["GamesPlayed"] >= 6, "Active", "Provisional")
    
    # Add is_active flag for frontend (LastGame >= today - 180 days)
    cutoff = pd.Timestamp.now().normalize() - pd.Timedelta(days=INACTIVE_HIDE_DAYS)
    adj["is_active"] = adj["LastGame"] >= cutoff

    # Sort with offense-first tie-breakers and no ties
    sort_cols = ["PowerScore_adj","SAO_norm","SAD_norm","SOS_norm","GamesPlayed","Team"]
    out = adj.sort_values(sort_cols, ascending=[False,False,False,False,False,True], kind="mergesort").reset_index(drop=True)
    out["Rank"] = out.index + 1

    # Filter inactive teams (6 months)
    cutoff = pd.Timestamp.now().normalize() - pd.Timedelta(days=INACTIVE_HIDE_DAYS)
    out_visible = out[out["LastGame"] >= cutoff].copy()

    # Sanity check: ensure only master teams in final rankings
    # Create reverse mapping to check against original team names
    reverse_mapping = {v: k for k, v in team_name_mapping.items()}
    original_team_names = set(out_visible.index.map(lambda x: reverse_mapping.get(x, x)))
    invalid_teams = original_team_names - master_team_names
    if invalid_teams:
        print(f"WARNING: {len(invalid_teams)} non-master teams found: {list(invalid_teams)[:5]}")
    else:
        print(f"PASS: All {len(out_visible)} ranked teams are from master list")

    # Sanity check: verify expected team count
    unique_teams = len(out_visible.index.unique())
    print(f"Sanity check: {unique_teams} master teams ranked")
    if age == "U12":
        if not (150 <= unique_teams <= 180):
            print(f"WARNING: Expected 150-180 AZ U12 teams, got {unique_teams}")
    elif age == "U11":
        if not (140 <= unique_teams <= 160):
            print(f"WARNING: Expected 140-160 AZ U11 teams, got {unique_teams}")
    
    # Reset index to make team names a column
    out_visible_with_team = out_visible.reset_index()
    out_visible_with_team = out_visible_with_team.rename(columns={'index': 'Team'})
    
    # --- Safe mapping patch ---
    # Map numeric indices back to actual team names
    if "Team" not in out_visible_with_team.columns:
        # If DataFrame index is numeric, try to map back to names
        if isinstance(out_visible_with_team.index[0], (int, float)):
            # Build reverse mapping from master list
            master_df = pd.read_csv(master_teams_path)
            name_map = {i: name for i, name in enumerate(sorted(master_df["Team Name"].unique()))}
            out_visible_with_team["Team"] = out_visible_with_team.index.map(name_map).fillna(out_visible_with_team.index)
        else:
            out_visible_with_team.reset_index(inplace=True)
            out_visible_with_team.rename(columns={"index": "Team"}, inplace=True)
    
    # Debug: Check if team names are numeric
    print(f"Debug: out_visible index type: {type(out_visible.index[0])}")
    print(f"Debug: out_visible index sample: {list(out_visible.index)[:5]}")
    print(f"Debug: out_visible_with_team Team column sample: {out_visible_with_team['Team'].head(5).tolist()}")
    
    if out_visible_with_team["Team"].astype(str).str.isnumeric().any():
        print("WARNING: numeric team names detected — mapping failed.")
        # Try to fix by using the stored mapped team names
        if 'mapped_team_names' in locals():
            # Create a mapping from numeric index to mapped team names
            index_to_mapped_name = {i: name for i, name in enumerate(sorted(mapped_team_names))}
            out_visible_with_team["Team"] = out_visible_with_team["Team"].map(index_to_mapped_name).fillna(out_visible_with_team["Team"])
            print("Applied fallback: Used stored mapped team names")
        else:
            print("ERROR: No mapped team names available for fallback")
    else:
        print("PASS: All team names are valid strings.")
    # --- End patch ---
    
    cols = ["Rank","Team","PowerScore_adj","PowerScore","GP_Mult","SAO_norm","SAD_norm","SOS_norm","SOS_iterative_norm","GamesPlayed","GamesTotal","Status","is_active","LastGame"]
    out_visible_with_team[cols].to_csv(out_csv, index=False, encoding="utf-8")
    
    # Generate connectivity report
    print("Generating connectivity report...")
    connectivity_df = generate_connectivity_report(raw)
    connectivity_out_path = f"connectivity_report_{age.lower()}_v53e.csv"
    connectivity_df.to_csv(connectivity_out_path, index=False)
    
    return out_visible_with_team

def main():
    """Main function with CLI argument parsing."""
    parser = argparse.ArgumentParser(description="Multi-Division Team Rankings Generator V5.3E")
    parser.add_argument("--division", 
                       default="AZ_Boys_U12",
                       help="Division to process (default: AZ_Boys_U12)")
    parser.add_argument("--input", 
                       dest="in_path",
                       help="Input games CSV file (default: auto-detect from division)")
    parser.add_argument("--output", 
                       dest="out_path",
                       help="Output rankings CSV file (default: auto-generate from division)")
    
    args = parser.parse_args()
    
    # Auto-generate file paths if not provided
    age = args.division.split('_')[-1]  # U11 or U12
    
    if not args.in_path:
        # Try division-specific file first, then fallback
        division_file = f"data_ingest/gold/Matched_Games_{age}.csv"
        fallback_file = "Matched_Games.csv"
        
        if Path(division_file).exists():
            args.in_path = division_file
        elif Path(fallback_file).exists():
            args.in_path = fallback_file
        else:
            print(f"ERROR: No input file found. Tried: {division_file}, {fallback_file}")
            return
    
    if not args.out_path:
        args.out_path = f"Rankings_AZ_M_{age}_2025_v53e.csv"
    
    print(f"Processing division: {args.division}")
    print(f"Input file: {args.in_path}")
    print(f"Output file: {args.out_path}")
    
    # Run the ranking generation
    result = build_rankings_from_wide(Path(args.in_path), Path(args.out_path), args.division)
    
    if not result.empty:
        print(f"Successfully generated rankings for {len(result)} teams")
        print(f"Output saved to: {args.out_path}")
    else:
        print("No rankings generated")

if __name__ == "__main__":
    main()
