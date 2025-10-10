# rankings/generate_team_rankings_v52.py
"""
ARIZONA U12 RANKING LOGIC — V5.2 (Strength-Adjusted)

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
4. Compute SOS from comprehensive history (fallback to percentile)
5. Normalize metrics (min-max 0–1)
6. Combine into PowerScore = 0.35*SAO + 0.35*SAD + 0.30*SOS
7. Output Rankings_v52.csv sorted by PowerScore
"""
import pandas as pd
import numpy as np
import os
from pathlib import Path

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

# ---- V5.2 Tuning Parameters ----
OFF_WEIGHT = 0.35
DEF_WEIGHT = 0.35
SOS_WEIGHT = 0.30
SOS_FLOOR = 0.40
GOAL_DIFF_CAP = 6        # cap ±6 (apply symmetrically)
PERFORMANCE_K = 0.20     # ±20% adjustment sensitivity (xGD layer)

def segment_weights(n: int, recent_k: int = 10, recent_share: float = 0.70):
    """Base 70/30 two-segment weights (no taper), length=n, sum=1.0."""
    if n <= 0:
        return np.array([], dtype=float)
    
    # When n <= recent_k, all games are "recent", distribute uniformly
    if n <= recent_k:
        return np.ones(n, dtype=float) / n
    
    # When n > recent_k, use 70/30 split
    w = np.zeros(n, dtype=float)
    old = n - recent_k
    w[:old] = (1.0 - recent_share) / old
    w[-recent_k:] = recent_share / recent_k
    return w

def tapered_weights(n: int,
                    recent_k: int = 10,
                    recent_share: float = 0.70,
                    full_weight_games: int = 25,
                    dampen_start: int = 25,
                    dampen_end: int = 30,
                    dampen_factor: float = 0.8,
                    enabled: bool = True):
    """Apply linear taper for games beyond `full_weight_games` up to `dampen_end`."""
    if n <= 0:
        return np.array([], dtype=float)

    cap = min(n, dampen_end)
    base_len = min(cap, full_weight_games)
    base = segment_weights(base_len, recent_k, recent_share)

    if not enabled or cap <= full_weight_games:
        w = base
    else:
        extra = cap - full_weight_games  # up to 5
        # linear multipliers from dampen_factor -> dampen_factor/2 over `extra` steps
        multipliers = np.linspace(dampen_factor, dampen_factor/2, extra)
        # use the last base weight as the anchor
        anchor = base[-1] if base_len > 0 else 0.0
        tapered = anchor * multipliers
        w = np.concatenate([base, tapered])

    # If n > cap, ignore older games
    if n > cap:
        # Prepend zeros for older-than-cap (they don't count)
        zeros = np.zeros(n - cap, dtype=float)
        w = np.concatenate([zeros, w])

    # Normalize to 1.0 if any nonzero; else uniform
    s = w.sum()
    if s > 0:
        w = w / s
    else:
        w = np.ones(n, dtype=float) / n
    return w

def minmax_norm(s: pd.Series) -> pd.Series:
    """Min-max normalize to [0,1] range."""
    s_min, s_max = s.min(), s.max()
    if s_max == s_min:
        return pd.Series(0.5, index=s.index)
    return ((s - s_min) / (s_max - s_min)).round(3)

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

def compute_off_def_raw(long_games: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for team, tg in long_games.groupby("Team", sort=False):
        gf, ga, w = _team_recent_series(tg)
        if len(w) == 0:
            off_raw, def_raw, gp = 0.0, 0.0, 0
        else:
            # Weighted goals per game
            gf_w = float((gf * w).sum())
            ga_w = float((ga * w).sum())
            off_raw = gf_w
            def_raw = 1.0 / (1.0 + ga_w)  # Lower GA → higher defense score
            gp = int(len(w))
        rows.append((team, off_raw, def_raw, gp))
    return pd.DataFrame(rows, columns=["Team","Off_raw","Def_raw","GamesPlayed"]).set_index("Team")

def opponent_adjust(long_games: pd.DataFrame, base: pd.DataFrame) -> pd.DataFrame:
    # Use Off_raw as an environment proxy
    opp_off = base["Off_raw"].replace(0, base["Off_raw"].mean())
    tmp = long_games.merge(opp_off.rename("Opp_Off_base"), left_on="Opponent", right_index=True, how="left")
    opp_avg = tmp.groupby("Team")["Opp_Off_base"].mean().rename("Opp_Off_avg")
    league_avg = opp_off.mean()

    # If you faced stronger offenses, scoring is harder ⇒ boost Off; vice versa
    def_factor = (opp_avg / league_avg).replace([np.inf,-np.inf],1.0).fillna(1.0)
    off_adj = base["Off_raw"] * def_factor.reindex(base.index).fillna(1.0)

    # If you faced weaker offenses, GA should be discounted ⇒ multiply by league_avg/opp_avg
    off_factor = (league_avg / opp_avg).replace([np.inf,-np.inf],1.0).fillna(1.0)
    def_adj = base["Def_raw"] * off_factor.reindex(base.index).fillna(1.0)

    adj = base.copy()
    adj["Off_raw_adj"] = off_adj
    adj["Def_raw_adj"] = def_adj
    return adj

def compute_strength_adjusted_metrics(long_games: pd.DataFrame, base: pd.DataFrame) -> pd.DataFrame:
    """
    Compute strength-adjusted offense and defense metrics (V5.2).
    
    For each game:
    - Adj_GF = GF * (1.0 / Opponent_Def_norm) - harder to score on strong defense
    - Adj_GA = GA * (1.0 / Opponent_Off_norm) - less penalty for allowing goals to strong offense
    
    Then apply performance multiplier based on xGD if available.
    """
    # Normalize base metrics for opponent strength calculations
    off_norm_temp = minmax_norm(base["Off_raw"])
    def_norm_temp = minmax_norm(base["Def_raw"])
    
    # Create opponent strength lookup (inverse of normalized metrics)
    # Higher normalized values = stronger opponents = higher multipliers
    opp_def_strength = (1.0 / (def_norm_temp + EPS)).replace([np.inf], 1.0)
    opp_off_strength = (1.0 / (off_norm_temp + EPS)).replace([np.inf], 1.0)
    
    # Merge opponent strengths into game data
    games_enriched = long_games.copy()
    games_enriched = games_enriched.merge(
        opp_def_strength.rename("Opp_Def_Strength"), 
        left_on="Opponent", 
        right_index=True, 
        how="left"
    )
    games_enriched = games_enriched.merge(
        opp_off_strength.rename("Opp_Off_Strength"), 
        left_on="Opponent", 
        right_index=True, 
        how="left"
    )
    
    # Fill missing opponent strengths with league means (fallback guardrail)
    games_enriched["Opp_Def_Strength"] = games_enriched["Opp_Def_Strength"].fillna(opp_def_strength.mean())
    games_enriched["Opp_Off_Strength"] = games_enriched["Opp_Off_Strength"].fillna(opp_off_strength.mean())
    
    # Calculate strength-adjusted goals
    games_enriched["Adj_GF"] = games_enriched["GF"] * games_enriched["Opp_Def_Strength"]
    games_enriched["Adj_GA"] = games_enriched["GA"] * games_enriched["Opp_Off_Strength"]
    
    # Apply performance multiplier if xGD data exists
    if "Performance" in games_enriched.columns:
        games_enriched["Performance"] = games_enriched["Performance"].fillna(0.5)
        games_enriched["Adj_GF"] *= (1.0 + PERFORMANCE_K * (games_enriched["Performance"] - 0.5))
        games_enriched["Adj_GA"] *= (1.0 - PERFORMANCE_K * (games_enriched["Performance"] - 0.5))
    
    # Aggregate at team level (using existing weights from _team_recent_series)
    rows = []
    for team, tg in games_enriched.groupby("Team", sort=False):
        gf, ga, w = _team_recent_series(tg)
        if len(w) == 0:
            sao_raw, sad_raw, gp = 0.0, 0.0, 0
        else:
            # Get adjusted goals for this team's games
            team_games_sorted = tg.sort_values("Date").tail(MAX_GAMES)
            adj_gf = team_games_sorted["Adj_GF"].to_numpy()
            adj_ga = team_games_sorted["Adj_GA"].to_numpy()
            
            # Apply weights
            sao_raw = float((adj_gf * w).sum())
            sad_raw = 1.0 / (1.0 + (adj_ga * w).sum())
            gp = int(len(w))
        
        rows.append((team, sao_raw, sad_raw, gp))
    
    return pd.DataFrame(rows, columns=["Team", "SAO_raw", "SAD_raw", "GamesPlayed"]).set_index("Team")

def gp_multiplier(gp: int) -> float:
    """Multiplicative penalty based on games played."""
    if gp >= 20: return 1.00
    if gp >= 10: return 0.90
    return 0.75

def build_rankings_from_wide(wide_matches_csv: Path, out_csv: Path):
    raw = pd.read_csv(wide_matches_csv, encoding="utf-8-sig")
    long = wide_to_long(raw)
    long = clamp_window(long)

    # Load authoritative AZ U12 master team list
    master_teams = pd.read_csv("AZ MALE U12 MASTER TEAM LIST.csv")
    master_team_names = set(master_teams["Team Name"].str.strip())
    print(f"Loaded {len(master_team_names)} authorized AZ U12 teams from master list")

    # Filter to include only master teams as ranked entities
    # Keep all opponents for accurate SOS calculation
    long = long[long["Team"].isin(master_team_names)].copy()
    print(f"Filtered to master teams. Remaining matches: {len(long)}")
    print(f"Unique teams after filter: {len(long['Team'].unique())}")

    # Use filtered dataset for Off_raw/Def_raw calculations (per V5 spec)
    print("Calculating Off_raw/Def_raw from filtered 30-game window...")
    base = compute_off_def_raw(long)
    
    # V5.2: Compute strength-adjusted metrics (includes performance layer)
    print("Computing strength-adjusted offense/defense metrics...")
    sa_metrics = compute_strength_adjusted_metrics(long, base)
    
    # Merge strength-adjusted metrics
    adj = base.copy()
    adj["SAO_raw"] = sa_metrics["SAO_raw"]
    adj["SAD_raw"] = sa_metrics["SAD_raw"]

    # Calculate actual SOS based on opponent strength
    print("Calculating actual SOS based on opponent strength...")
    
    # Load comprehensive history to get opponent strengths
    try:
        comp_hist = pd.read_csv("Team_Game_Histories_COMPREHENSIVE.csv")
        comp_hist["Date"] = pd.to_datetime(comp_hist["Date"])
        
        # Calculate SOS for each team based on their last 30 games
        sos_scores = {}
        for team in adj.index:
            team_games = comp_hist[comp_hist["Team"] == team].sort_values("Date", ascending=False)
            if len(team_games) > 0:
                # Use last 30 games for SOS calculation
                recent_games = team_games.head(30)
                avg_opp_strength = recent_games["Opponent_BaseStrength"].mean()
                sos_scores[team] = avg_opp_strength
            else:
                sos_scores[team] = 0.5  # Default neutral strength
        
        # Add SOS to the dataframe
        adj["SOS_raw"] = adj.index.map(sos_scores)
        print(f"Calculated SOS for {len(sos_scores)} teams")
        
    except FileNotFoundError:
        print("Warning: Comprehensive history not found, using offensive ranking as SOS proxy")
        adj["SOS_raw"] = adj["Off_raw_adj"].rank(pct=True)
    
    # Min-max normalize to [0,1] range
    SAO_norm = minmax_norm(adj["SAO_raw"])
    SAD_norm = minmax_norm(adj["SAD_raw"])
    SOS_norm = minmax_norm(adj["SOS_raw"])  # Now using actual opponent strength
    # Apply opponent-strength floor (prevents weak-schedule inflation)
    SOS_norm = SOS_norm.clip(lower=SOS_FLOOR)

    out = adj.copy()
    out["SAO_norm"] = SAO_norm
    out["SAD_norm"] = SAD_norm
    out["SOS_norm"] = SOS_norm

    out["PowerScore"] = (
        OFF_WEIGHT * out["SAO_norm"] +
        DEF_WEIGHT * out["SAD_norm"] +
        SOS_WEIGHT * out["SOS_norm"]
    ).round(3)

    # Add LastGame for inactivity filtering
    last_date = long.groupby("Team")["Date"].max()
    out = out.merge(last_date.rename("LastGame"), left_on="Team", right_index=True, how="left")

    out = out.reset_index()  # Team as a column
    
    # GamesPlayed = filtered count (≤30) used in rankings (per V5 spec)
    print("Setting GamesPlayed to filtered count for ranking calculations...")
    out["GamesPlayed"] = out["Team"].map(base["GamesPlayed"].to_dict())
    
    # Add GamesTotal for display transparency (all-time count)
    print("Adding GamesTotal for display transparency...")
    try:
        comp_hist = pd.read_csv("Team_Game_Histories_COMPREHENSIVE.csv")
        total_games = comp_hist.groupby("Team").size()
        out["GamesTotal"] = out["Team"].map(lambda team: total_games.get(team, 0))
        print(f"Added GamesTotal for {len(out)} teams from comprehensive history")
    except FileNotFoundError:
        print("Warning: Comprehensive history not found, GamesTotal = GamesPlayed")
        out["GamesTotal"] = out["GamesPlayed"]
    
    out["GP_Mult"] = out["GamesPlayed"].apply(gp_multiplier)
    out["PowerScore_adj"] = (out["PowerScore"] * out["GP_Mult"]).round(3)
    out["Status"] = np.where(out["GamesPlayed"] >= 6, "Active", "Provisional")
    
    # Add is_active flag for frontend (LastGame >= today - 180 days)
    cutoff = pd.Timestamp.now().normalize() - pd.Timedelta(days=INACTIVE_HIDE_DAYS)
    out["is_active"] = out["LastGame"] >= cutoff

    # Sort with offense-first tie-breakers and no ties
    sort_cols = ["PowerScore_adj","SAO_norm","SAD_norm","SOS_norm","GamesPlayed","Team"]
    out = out.sort_values(sort_cols, ascending=[False,False,False,False,False,True], kind="mergesort").reset_index(drop=True)
    out["Rank"] = out.index + 1

    # Filter inactive teams (6 months)
    cutoff = pd.Timestamp.now().normalize() - pd.Timedelta(days=INACTIVE_HIDE_DAYS)
    out_visible = out[out["LastGame"] >= cutoff].copy()

    # Sanity check: ensure only master teams in final rankings
    invalid_teams = set(out_visible["Team"]) - master_team_names
    if invalid_teams:
        print(f"WARNING: {len(invalid_teams)} non-master teams found: {list(invalid_teams)[:5]}")
    else:
        print(f"PASS: All {len(out_visible)} ranked teams are from master list")

    # Sanity check: verify expected team count (150-180 AZ U12 teams)
    unique_teams = len(out_visible["Team"].unique())
    print(f"Sanity check: {unique_teams} master teams ranked")
    if not (150 <= unique_teams <= 180):
        print(f"WARNING: Expected 150-180 AZ U12 teams, got {unique_teams}")
    
    cols = ["Rank","Team","PowerScore_adj","PowerScore","GP_Mult","SAO_norm","SAD_norm","SOS_norm","GamesPlayed","GamesTotal","Status","is_active","LastGame"]
    out_visible[cols].to_csv(out_csv, index=False, encoding="utf-8")
    return out_visible

if __name__ == "__main__":
    # Example CLI usage:
    # python -m rankings.generate_team_rankings_v52 --in Matched_Games.csv --out Rankings_v52.csv
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="in_path", required=True)
    p.add_argument("--out", dest="out_path", default="Rankings_v52.csv")
    args = p.parse_args()
    build_rankings_from_wide(Path(args.in_path), Path(args.out_path))
