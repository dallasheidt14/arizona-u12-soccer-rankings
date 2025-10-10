# rankings/generate_team_rankings_v53_enhanced.py
"""
ARIZONA U12 RANKING LOGIC — V5.3E (Enhanced with Adaptive K-factor and Outlier Guards)

Enhanced Features:
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
11. Output Rankings_v53_enhanced.csv sorted by PowerScore
12. Generate connectivity_report_v53e.csv
"""
import pandas as pd
import numpy as np
import os
from pathlib import Path
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

# ---- Iterative SOS Configuration ----
USE_ITERATIVE_SOS = True
PERFORMANCE_K_V52B = 0.10          # reduced from 0.20
RIDGE_GA = 0.25               # stabilize defensive inverse
SHRINK_TAU = 8                # Bayesian shrinkage strength

# Robust scaling uses p5/p95 percentiles
SOS_FLOOR_DYNAMIC_PERCENTILE = 20
SOS_FLOOR_MIN = 0.30

# Opponent strength clipping (prevents extremes)
OPP_STRENGTH_CLIP_NORM_LOW  = 0.15
OPP_STRENGTH_CLIP_NORM_HIGH = 0.95
OPP_STRENGTH_FINAL_MIN = 0.67
OPP_STRENGTH_FINAL_MAX = 1.50

# Provisional handling
PROVISIONAL_ALPHA = 1.5
PROVISIONAL_MIN_GAMES = 10

# SOS distribution stretching (emphasize top schedules)
SOS_STRETCH_EXPONENT = 1.5

def adaptive_multiplier(team_strength, opp_strength, games_used, 
                        k_base=1.0, min_games=8, alpha=0.5, beta=0.6):
    """
    Shrink single-game impact when opponent is much weaker or GP is small.
    
    Args:
        team_strength: Team's current normalized strength (0-1)
        opp_strength: Opponent's normalized strength (0-1)
        games_used: Number of games in team's sample
        k_base: Base K-factor
        min_games: Minimum games for full weight
        alpha: Opponent gap exponent
        beta: Sample size exponent
    
    Returns:
        Adjusted K-factor multiplier (0-1)
    """
    # Opponent gap: if much stronger, shrink impact
    gap = max(0.0, team_strength - opp_strength)
    opp_factor = 1.0 / (1.0 + gap**alpha)
    
    # Sample penalty: if < min_games, shrink impact
    sample_factor = min(1.0, (games_used / min_games)**beta)
    
    return k_base * opp_factor * sample_factor

def clip_to_zscore(series, z=2.5):
    """
    Cap values to prevent single outliers from dominating.
    
    Args:
        series: pandas Series of per-game contributions
        z: Z-score threshold for clipping
    
    Returns:
        Clipped series
    """
    mu = series.mean()
    sd = series.std(ddof=1) or 1.0
    lo, hi = mu - z*sd, mu + z*sd
    return series.clip(lower=lo, upper=hi)

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

def robust_scale(series):
    """
    Robust scaling using percentile winsorization + z-score + logistic.
    Prevents binary 0/1 cliffs by creating smooth distributions.
    """
    from scipy.stats import zscore
    # Winsorize to [5th, 95th] percentile to kill outliers
    p5, p95 = np.nanpercentile(series, [5, 95])
    s = series.clip(lower=p5, upper=p95)
    
    # Z-score on clipped values
    z = zscore(s.fillna(s.mean()))
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
    Compute strength-adjusted offense and defense metrics (V5.3E).
    
    Enhanced with:
    - Adaptive K-factor: Shrink impact for weak opponents and low-GP teams
    - Outlier Guard: Cap extreme values to prevent single-game dominance
    
    For each game:
    - Adj_GF = GF * (1.0 / Opponent_Def_norm) * adaptive_k - harder to score on strong defense
    - Adj_GA = GA * (1.0 / Opponent_Off_norm) * adaptive_k - less penalty for allowing goals to strong offense
    
    Then apply V5.3 performance multiplier based on Expected GD with exponential recency decay.
    """
    # Normalize base metrics for opponent strength calculations
    off_norm_temp = minmax_norm(base["Off_raw"])
    def_norm_temp = minmax_norm(base["Def_raw"])
    
    # Create opponent strength lookup (inverse of normalized metrics)
    # Higher normalized values = stronger opponents = higher multipliers
    # Clip normalized values before inversion to prevent extremes
    def_norm_clipped = def_norm_temp.clip(lower=OPP_STRENGTH_CLIP_NORM_LOW, 
                                           upper=OPP_STRENGTH_CLIP_NORM_HIGH)
    off_norm_clipped = off_norm_temp.clip(lower=OPP_STRENGTH_CLIP_NORM_LOW, 
                                           upper=OPP_STRENGTH_CLIP_NORM_HIGH)
    
    # Invert and apply final caps
    opp_def_strength = (1.0 / def_norm_clipped).clip(lower=OPP_STRENGTH_FINAL_MIN, 
                                                       upper=OPP_STRENGTH_FINAL_MAX)
    opp_off_strength = (1.0 / off_norm_clipped).clip(lower=OPP_STRENGTH_FINAL_MIN, 
                                                       upper=OPP_STRENGTH_FINAL_MAX)
    
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
    
    # V5.3E: Apply Adaptive K-factor if enabled
    if ADAPTIVE_K_ENABLED:
        # Get team current strengths for adaptive K
        team_strengths = long_games.groupby("Team")["Off_raw"].mean() if "Off_raw" in long_games.columns else off_norm_temp
        opp_strengths = games_enriched["Opponent"].map(team_strengths).fillna(0.5)
        
        # Calculate games used per team
        games_count = long_games.groupby("Team").size()
        games_enriched["games_used"] = games_enriched["Team"].map(games_count)
        
        # Apply adaptive multiplier
        games_enriched["adaptive_k"] = games_enriched.apply(
            lambda row: adaptive_multiplier(
                team_strength=team_strengths.get(row["Team"], 0.5),
                opp_strength=opp_strengths[row.name],
                games_used=row["games_used"],
                k_base=1.0,
                min_games=ADAPTIVE_K_MIN_GAMES,
                alpha=ADAPTIVE_K_ALPHA,
                beta=ADAPTIVE_K_BETA
            ),
            axis=1
        )
        
        print(f"Applied adaptive K-factor. Mean multiplier: {games_enriched['adaptive_k'].mean():.3f}")
    else:
        games_enriched["adaptive_k"] = 1.0
    
    # Calculate strength-adjusted goals with adaptive K
    games_enriched["Adj_GF"] = games_enriched["GF"] * games_enriched["Opp_Def_Strength"] * games_enriched["adaptive_k"]
    games_enriched["Adj_GA"] = games_enriched["GA"] * games_enriched["Opp_Off_Strength"] * games_enriched["adaptive_k"]
    
    # V5.3: Apply Expected GD and Performance layer with threshold + recency decay
    if USE_PERFORMANCE_LAYER:
        # Step 3: Expected GD and Performance
        # Expected GD = Team's offensive strength vs Opponent's defensive strength
        # Merge team's own strength for Expected GD calculation
        team_off_strength = off_norm_temp.rename("Team_Off_Strength")
        team_def_strength = def_norm_temp.rename("Team_Def_Strength")
        
        games_enriched = games_enriched.merge(
            team_off_strength, 
            left_on="Team", 
            right_index=True, 
            how="left"
        )
        games_enriched = games_enriched.merge(
            team_def_strength, 
            left_on="Team", 
            right_index=True, 
            how="left"
        )
        
        # Expected GD = Team's offensive advantage - Opponent's defensive advantage
        games_enriched["ExpectedGD"] = (
            games_enriched["Team_Off_Strength"] - games_enriched["Opp_Def_Strength"]
        )
        
        games_enriched["GoalDiff"] = games_enriched["GF"] - games_enriched["GA"]
        games_enriched["Performance_raw"] = games_enriched["GoalDiff"] - games_enriched["ExpectedGD"]
        
        # Scaled performance (for diagnostics)
        games_enriched["Performance_scaled"] = np.clip((games_enriched["Performance_raw"] + 3) / 6, 0, 1)
        games_enriched["Performance_scaled"] = games_enriched["Performance_scaled"].fillna(0.5)
        
        # Step 4: Compute Exponential Recency Decay
        games_enriched = games_enriched.sort_values(["Team", "Date"], ascending=[True, False])
        games_enriched["GamesAgo"] = games_enriched.groupby("Team").cumcount()
        games_enriched["RecencyDecay"] = np.exp(
            -PERFORMANCE_DECAY_RATE * games_enriched["GamesAgo"].clip(0, PERFORMANCE_MAX_GAMES)
        )
        
        # Step 5: Apply THRESHOLD + Decay Form Adjustment
        perf_delta = games_enriched["Performance_raw"]
        
        # Only trigger adjustment if |delta| >= threshold
        significant = np.abs(perf_delta) >= PERFORMANCE_THRESHOLD
        sign = np.sign(perf_delta)
        
        # Compute adjustment factor (recency-weighted, threshold-gated)
        adj_factor = 1 + (
            PERFORMANCE_K * sign * games_enriched["RecencyDecay"] * significant.astype(float)
        )
        
        # Apply proportional boost/penalty
        games_enriched["Adj_GF"] *= adj_factor
        games_enriched["Adj_GA"] *= (2 - adj_factor)
        
        # Keep for diagnostics
        games_enriched["Perf_Delta"] = perf_delta
        games_enriched["Perf_Adj_Factor"] = adj_factor
    
    # V5.3E: Apply Outlier Guard if enabled
    if OUTLIER_GUARD_ENABLED:
        print(f"Applying outlier guard with z-score threshold {OUTLIER_GUARD_ZSCORE}")
        for team in games_enriched["Team"].unique():
            mask = games_enriched["Team"] == team
            if mask.sum() > 1:  # Need at least 2 games for z-score calculation
                games_enriched.loc[mask, "Adj_GF"] = clip_to_zscore(
                    games_enriched.loc[mask, "Adj_GF"], 
                    z=OUTLIER_GUARD_ZSCORE
                )
                games_enriched.loc[mask, "Adj_GA"] = clip_to_zscore(
                    games_enriched.loc[mask, "Adj_GA"], 
                    z=OUTLIER_GUARD_ZSCORE
                )
    
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
            sad_raw = 1.0 / ((adj_ga * w).sum() + RIDGE_GA)
            gp = int(len(w))
        
        rows.append((team, sao_raw, sad_raw, gp))
    
    return pd.DataFrame(rows, columns=["Team", "SAO_raw", "SAD_raw", "GamesPlayed"]).set_index("Team")

def apply_bayesian_shrinkage(sa_metrics, league_off_mean, league_def_mean):
    """Apply Bayesian shrinkage toward league means based on games played."""
    shrunk = sa_metrics.copy()
    gp = sa_metrics["GamesPlayed"]
    
    shrunk["SAO_raw"] = (gp * sa_metrics["SAO_raw"] + SHRINK_TAU * league_off_mean) / (gp + SHRINK_TAU)
    shrunk["SAD_raw"] = (gp * sa_metrics["SAD_raw"] + SHRINK_TAU * league_def_mean) / (gp + SHRINK_TAU)
    
    return shrunk

def gp_multiplier(gp: int) -> float:
    """Multiplicative penalty based on games played."""
    if gp >= 20: return 1.00
    if gp >= 10: return 0.90
    return 0.75

def generate_connectivity_report(games_df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate basic connectivity analysis of opponent network.
    
    Returns:
        DataFrame with Team, ComponentID, ComponentSize, Degree columns
    """
    try:
        import networkx as nx
        
        # Build graph
        G = nx.Graph()
        for _, row in games_df.iterrows():
            G.add_edge(row["Team A"], row["Team B"])
        
        # Find connected components
        components = list(nx.connected_components(G))
        
        # Build report
        connectivity_data = []
        for comp_id, component in enumerate(components):
            comp_size = len(component)
            for team in component:
                degree = G.degree(team) if team in G else 0
                connectivity_data.append({
                    "Team": team,
                    "ComponentID": comp_id,
                    "ComponentSize": comp_size,
                    "Degree": degree
                })
        
        print(f"Connectivity analysis: {len(components)} components, largest has {max(len(c) for c in components)} teams")
        return pd.DataFrame(connectivity_data)
        
    except ImportError:
        print("Warning: NetworkX not available, skipping connectivity analysis")
        return pd.DataFrame(columns=["Team", "ComponentID", "ComponentSize", "Degree"])

def build_rankings_from_wide(wide_matches_csv: Path, out_csv: Path):
    raw = pd.read_csv(wide_matches_csv, encoding="utf-8-sig")
    long = wide_to_long(raw)
    long = clamp_window(long)

    # Load authoritative AZ U12 master team list
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

    # Filter to include only master teams as ranked entities
    # Keep all opponents for accurate SOS calculation
    long = long[long["Team"].isin(master_team_names)].copy()
    print(f"Filtered to master teams. Remaining matches: {len(long)}")
    print(f"Unique teams after filter: {len(long['Team'].unique())}")
    
    # Apply team name mapping to include club names
    long["Team"] = long["Team"].map(team_name_mapping)
    print("Applied team name mapping with club names")

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
    try:
        comp_hist = pd.read_csv("Team_Game_Histories_COMPREHENSIVE.csv")
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
                    if opp_canon in opp_strength_map:
                        successful_lookups += 1
                    opp_strengths.append(strength)
                
                sos_scores[team] = np.mean(opp_strengths) if opp_strengths else fallback
            else:
                sos_scores[team] = fallback
        
        # Calculate and assert match rates
        team_match_rate = matched_teams / len(adj) if len(adj) > 0 else 0
        opp_match_rate = successful_lookups / total_opponent_lookups if total_opponent_lookups > 0 else 0
        
        print(f"Team match rate: {team_match_rate:.1%} ({matched_teams}/{len(adj)})")
        print(f"Opponent strength match rate: {opp_match_rate:.1%} ({successful_lookups}/{total_opponent_lookups})")
        
        assert team_match_rate > 0.9, (
            f"Low team match rate: {team_match_rate:.1%}. "
            f"Check comprehensive history and team name canonicalization."
        )
        assert opp_match_rate > 0.9, (
            f"Low opponent match rate: {opp_match_rate:.1%}. "
            f"Check team_aliases.json for missing mappings."
        )
        
        # Add SOS to the dataframe
        adj["SOS_raw"] = adj.index.map(sos_scores)
        print(f"Calculated baseline SOS for {len(sos_scores)} teams (median: {np.median(list(sos_scores.values())):.3f})")
        
    except FileNotFoundError:
        print("Warning: Comprehensive history not found, using offensive ranking as SOS proxy")
        adj["SOS_raw"] = adj["Off_raw"].rank(pct=True)
    
    # Robust normalize to [0,1] range (prevents binary 0/1 cliffs)
    SAO_norm = robust_scale(adj["SAO_raw"])
    SAD_norm = robust_scale(adj["SAD_raw"])
    
    # Normalize baseline SOS using robust method
    SOS_norm_baseline = robust_minmax(adj["SOS_raw"])
    
    # Log baseline SOS health
    print(f"Baseline SOS zero rate: {(SOS_norm_baseline == 0).mean():.1%}")
    print(f"Baseline SOS unique values: {SOS_norm_baseline.nunique()}")

    out = adj.copy()
    out["SAO_norm"] = SAO_norm
    out["SAD_norm"] = SAD_norm
    out["SOS_norm"] = SOS_norm_baseline

    # Step 7: Compute Final PowerScore (will be updated after iterative SOS)
    out["PowerScore"] = (
        OFF_WEIGHT * out["SAO_norm"] +
        DEF_WEIGHT * out["SAD_norm"] +
        SOS_WEIGHT * out["SOS_norm"]
    ).round(4)  # Store 4 decimals, display 3 in frontend

    # Add LastGame for inactivity filtering
    last_date = long.groupby("Team")["Date"].max()
    out = out.merge(last_date.rename("LastGame"), left_on="Team", right_index=True, how="left")

    out = out.reset_index()  # Team as a column
    
    # Step 6.5: Compute Iterative SOS (if enabled)
    if USE_ITERATIVE_SOS:
        try:
            import sys
            from pathlib import Path
            sys.path.append(str(Path(__file__).parent.parent))
            from analytics.iterative_opponent_strength_v53_enhanced import compute_iterative_sos_adaptive
            print("Computing iterative SOS with adaptive K-factor...")
            sos_iterative_dict = compute_iterative_sos_adaptive("Matched_Games.csv", use_adaptive_k=True)
            out["SOS_iterative_norm"] = out["Team"].map(sos_iterative_dict)
            print(f"Added iterative SOS for {out['SOS_iterative_norm'].notna().sum()} teams")
        except Exception as e:
            print(f"Warning: Failed to compute iterative SOS: {e}")
            out["SOS_iterative_norm"] = np.nan
    else:
        out["SOS_iterative_norm"] = np.nan
    
    # Create SOS_component: iterative primary, baseline fallback
    out["SOS_component"] = out["SOS_iterative_norm"].combine_first(out["SOS_norm"])
    out["SOS_source"] = np.where(
        out["SOS_iterative_norm"].notna(), 
        "iterative", 
        "baseline"
    )

    # Log SOS source distribution
    print(f"SOS sources: {out['SOS_source'].value_counts().to_dict()}")

    # Update PowerScore to use SOS_component instead of baseline SOS
    out["PowerScore"] = (
        OFF_WEIGHT * out["SAO_norm"] +
        DEF_WEIGHT * out["SAD_norm"] +
        SOS_WEIGHT * out["SOS_component"]
    ).round(4)
    
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
    
    # Stronger provisional penalty (exponential for low games)
    def provisional_multiplier(gp):
        return min(1.0, (gp / 20.0) ** PROVISIONAL_ALPHA)
    
    out["GP_Mult"] = out["GamesPlayed"].apply(provisional_multiplier)
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
    # Create reverse mapping to check against original team names
    reverse_mapping = {v: k for k, v in team_name_mapping.items()}
    original_team_names = set(out_visible["Team"].map(lambda x: reverse_mapping.get(x, x)))
    invalid_teams = original_team_names - master_team_names
    if invalid_teams:
        print(f"WARNING: {len(invalid_teams)} non-master teams found: {list(invalid_teams)[:5]}")
    else:
        print(f"PASS: All {len(out_visible)} ranked teams are from master list")

    # Sanity check: verify expected team count (150-180 AZ U12 teams)
    unique_teams = len(out_visible["Team"].unique())
    print(f"Sanity check: {unique_teams} master teams ranked")
    if not (150 <= unique_teams <= 180):
        print(f"WARNING: Expected 150-180 AZ U12 teams, got {unique_teams}")
    
    cols = ["Rank","Team","PowerScore_adj","PowerScore","GP_Mult","SAO_norm","SAD_norm","SOS_norm","SOS_iterative_norm","GamesPlayed","GamesTotal","Status","is_active","LastGame"]
    out_visible[cols].to_csv(out_csv, index=False, encoding="utf-8")
    
    # Generate connectivity report
    print("Generating connectivity report...")
    connectivity_df = generate_connectivity_report(pd.read_csv("Matched_Games.csv"))
    connectivity_df.to_csv("connectivity_report_v53e.csv", index=False)
    
    return out_visible

if __name__ == "__main__":
    # Example CLI usage:
    # python -m rankings.generate_team_rankings_v53_enhanced --in Matched_Games.csv --out Rankings_v53_enhanced.csv
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="in_path", required=True)
    p.add_argument("--out", dest="out_path", default="Rankings_v53_enhanced.csv")
    args = p.parse_args()
    build_rankings_from_wide(Path(args.in_path), Path(args.out_path))
