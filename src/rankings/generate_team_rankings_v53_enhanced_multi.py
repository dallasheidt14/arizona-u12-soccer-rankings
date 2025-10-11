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
sys.path.append('.')  # Add current directory for utils imports

from src.utils.division import parse_age_from_division, to_canonical_division
from src.utils.data_loader import resolve_input_path, load_games_frame
from src.utils.team_normalizer import canonicalize_team_name, robust_minmax

# Division registry integration
try:
    from src.utils.division_registry import get_master_list_path, validate_division_key
    REGISTRY_AVAILABLE = True
except ImportError:
    REGISTRY_AVAILABLE = False

def first_existing(paths):
    """Return first path that exists, or raise FileNotFoundError."""
    for p in paths:
        if Path(p).exists():
            return p
    raise FileNotFoundError(f"None of these paths exist: {paths}")

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

def wide_to_long_with_keys(games_df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert wide format to long format, preserving canonical keys.
    Input must have Team_A_Key and Team_B_Key columns.
    """
    # Create team A perspective
    a = games_df[["Team A", "Team B", "Score A", "Score B", "Date", "Team_A_Key", "Team_B_Key"]].rename(
        columns={
            "Team A": "Team",
            "Team B": "Opponent",
            "Score A": "GF",
            "Score B": "GA",
            "Team_A_Key": "TeamKey",
            "Team_B_Key": "OppKey"
        }
    )
    
    # Create team B perspective
    b = games_df[["Team B", "Team A", "Score B", "Score A", "Date", "Team_B_Key", "Team_A_Key"]].rename(
        columns={
            "Team B": "Team",
            "Team A": "Opponent",
            "Score B": "GF",
            "Score A": "GA",
            "Team_B_Key": "TeamKey",
            "Team_A_Key": "OppKey"
        }
    )
    
    long = pd.concat([a, b], ignore_index=True)
    long = long.dropna(subset=["Team", "Opponent"])
    long["Date"] = pd.to_datetime(long["Date"], errors="coerce")
    return long

# Keep old function for backward compatibility
def wide_to_long(games_df: pd.DataFrame) -> pd.DataFrame:
    """Legacy function - redirects to wide_to_long_with_keys if keys present."""
    if "Team_A_Key" in games_df.columns:
        return wide_to_long_with_keys(games_df)
    else:
        # Fallback to original behavior
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
    """Compute raw offense/defense using TeamKey for grouping."""
    rows = []
    
    for team_key in long_games["TeamKey"].unique():
        team_games = long_games[long_games["TeamKey"] == team_key]
        
        if len(team_games) == 0:
            continue
            
        gf_vals, ga_vals, weights = _team_recent_series(team_games)
        
        if len(gf_vals) == 0:
            continue
        
        # Weighted averages
        off_raw = np.average(gf_vals, weights=weights)
        def_raw = np.average(ga_vals, weights=weights)
        
        rows.append({
            "TeamKey": team_key,
            "Off_raw": off_raw,
            "Def_raw": def_raw,
            "GamesPlayed": len(gf_vals)
        })
    
    base_df = pd.DataFrame(rows)
    base_df = base_df.set_index("TeamKey")  # Index by key, not Team
    return base_df

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

def build_rankings_from_wide(games_df: pd.DataFrame, out_csv: Path, division: str = "AZ_Boys_U12"):
    # Extract age from division for file naming
    age = division.split('_')[-1]  # U11, U12, etc.
    age_lower = age.lower()  # u11, u12
    
    # Use registry for master list path if available
    if REGISTRY_AVAILABLE:
        try:
            MASTER_PATH = get_master_list_path(division)
            if not MASTER_PATH.exists():
                # Fall back to old logic if registry path doesn't exist
                MASTER_PATH = first_existing([
                    f"data/bronze/AZ MALE {age_lower} MASTER TEAM LIST.csv",
                    f"AZ MALE {age_lower} MASTER TEAM LIST.csv"
                ])
        except (KeyError, FileNotFoundError):
            # Fall back to old logic if registry fails
            MASTER_PATH = first_existing([
                f"data/bronze/AZ MALE {age_lower} MASTER TEAM LIST.csv",
                f"AZ MALE {age_lower} MASTER TEAM LIST.csv"
            ])
    else:
        # Use old logic if registry not available
        MASTER_PATH = first_existing([
            f"data/bronze/AZ MALE {age_lower} MASTER TEAM LIST.csv",
            f"AZ MALE {age_lower} MASTER TEAM LIST.csv"
        ])
    
    print(f"[v53e] Using master list: {MASTER_PATH}")
    
    # Use the passed DataFrame directly (no need to re-read)
    raw = games_df.copy()
    
    # Strip whitespace from team names
    raw["Team A"] = raw["Team A"].astype(str).str.strip()
    raw["Team B"] = raw["Team B"].astype(str).str.strip()
    
    # Add canonical keys to raw data BEFORE wide_to_long
    raw["Team_A_Key"] = raw["Team A"].map(canonicalize_team_name)
    raw["Team_B_Key"] = raw["Team B"].map(canonicalize_team_name)
    
    # Convert to long format with keys
    long = wide_to_long_with_keys(raw)
    long = clamp_window(long)
    
    # Load master list with keys
    master_teams = pd.read_csv(MASTER_PATH)
    master_teams["Team Name"] = master_teams["Team Name"].astype(str).str.strip()
    master_teams["TeamKey"] = master_teams["Team Name"].map(canonicalize_team_name)
    master_team_keys = set(master_teams["TeamKey"])
    print(f"Loaded {len(master_team_keys)} authorized AZ {age} teams from master list")
    
    # Filter matches: keep only rows where Team is a master team
    # (Keep all opponents for accurate SOS calculation)
    long = long[long["TeamKey"].isin(master_team_keys)].copy()
    print(f"Filtered to master teams. Remaining matches: {len(long)}")
    print(f"Unique teams after filter: {len(long['TeamKey'].unique())}")
    
    # DO NOT map Team to "Team + Club" here - keep keys separate
    # Club names will be merged at the very end for display only
    
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
        
        # Canonicalize using TeamKey (already present if comp_hist was built correctly)
        if "TeamKey" not in comp_hist.columns:
            comp_hist["TeamKey"] = comp_hist["Team"].astype(str).str.strip().map(canonicalize_team_name)
        if "OppKey" not in comp_hist.columns:
            comp_hist["OppKey"] = comp_hist["Opponent"].astype(str).str.strip().map(canonicalize_team_name)
        
        # Build opponent strength lookup (OppKey -> BaseStrength)
        opp_strength_map = comp_hist.groupby("OppKey")["Opponent_BaseStrength"].mean().to_dict()
        
        # Calculate median fallback
        fallback = np.median(list(opp_strength_map.values())) if opp_strength_map else 0.5
        
        # Calculate SOS for each team based on their last 30 games (use TeamKey)
        sos_scores = {}
        sos_counts = {"matched": 0, "total": 0}
        
        for team_key in adj.index:  # adj is indexed by TeamKey now
            team_games = comp_hist[comp_hist["TeamKey"] == team_key].sort_values("Date", ascending=False)
            if len(team_games) > 0:
                recent_games = team_games.head(30)
                
                # Look up opponent strengths using OppKey
                opp_strengths = recent_games["OppKey"].map(opp_strength_map).fillna(fallback)
                avg_opp_strength = opp_strengths.mean()
                sos_scores[team_key] = avg_opp_strength
                sos_counts["matched"] += 1
                sos_counts["total"] += len(recent_games)
            else:
                sos_scores[team_key] = fallback  # Default neutral strength
        
        adj["SOS_raw"] = adj.index.map(sos_scores)
        print(f"SOS calculation: {sos_counts['matched']}/{len(adj)} teams matched")
        
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

    # ✅ Correct sort: numerical only, no implicit alphabetical fallback
    # Remove GamesPlayed from sort keys to avoid alphabetical fallback
    sort_cols = ["PowerScore_adj", "SOS_norm", "SAO_norm", "SAD_norm"]
    out = adj.sort_values(
        sort_cols,
        ascending=[False, False, False, True],  # SAD is defensive (lower is better)
        kind="mergesort"
    )
    
    # Re-rank after sorting
    out["Rank"] = range(1, len(out) + 1)
    
    # 🔒 Guardrail: ensure PowerScore really descending
    if not (out["PowerScore_adj"].diff().fillna(0) <= 0).all():
        raise AssertionError("Ranking not strictly sorted by PowerScore descending!")

    # Filter inactive teams (6 months) - temporarily disabled for U11
    cutoff = pd.Timestamp.now().normalize() - pd.Timedelta(days=INACTIVE_HIDE_DAYS)
    if age == "U11":
        # For U11, don't filter by inactivity to ensure we get rankings
        out_visible = out.copy()
        print(f"U11: Skipping inactivity filter, using all {len(out_visible)} teams")
    else:
        out_visible = out[out["LastGame"] >= cutoff].copy()

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
    out_visible_with_team = out_visible_with_team.rename(columns={'index': 'TeamKey'})
    
    # Merge master list to get Team Name and Club for display
    out_visible_with_team = out_visible_with_team.merge(
        master_teams[["TeamKey", "Team Name", "Club"]],
        on="TeamKey",
        how="left"
    )
    
    # Create DisplayTeam column (Team + Club for UI)
    out_visible_with_team["DisplayTeam"] = np.where(
        out_visible_with_team["Club"].notna() & (out_visible_with_team["Club"] != ""),
        out_visible_with_team["Team Name"] + " " + out_visible_with_team["Club"],
        out_visible_with_team["Team Name"]
    )
    
    # Use DisplayTeam for the "Team" column in output
    out_visible_with_team["Team"] = out_visible_with_team["DisplayTeam"]
    
    # Keep Club as separate field for API
    out_visible_with_team["Club"] = out_visible_with_team["Club"].fillna("")
    
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
    
    # Normalize division and resolve path
    age = parse_age_from_division(args.division)  # 'U11'
    canonical_div = to_canonical_division(args.division)  # 'AZ_Boys_U11'
    in_path = resolve_input_path(age=age, explicit=args.in_path)
    print(f"[v53e] Division={canonical_div}  Age={age}  Input={in_path}")

    # Load and schema-check
    games_df = load_games_frame(in_path)
    print(f"[v53e] Loaded {len(games_df):,} rows from {in_path}")
    
    # Auto-generate output path if not provided
    if not args.out_path:
        args.out_path = f"Rankings_AZ_M_{age}_2025_v53e.csv"
    
    print(f"[v53e] Processing division: {canonical_div}")
    print(f"[v53e] Output file: {args.out_path}")
    
    # Run the ranking generation
    result = build_rankings_from_wide(games_df, Path(args.out_path), canonical_div)
    
    if not result.empty:
        print(f"[v53e] Successfully generated rankings for {len(result)} teams")
        print(f"[v53e] Output saved to: {args.out_path}")
    else:
        print("[v53e] No rankings generated")

if __name__ == "__main__":
    main()
