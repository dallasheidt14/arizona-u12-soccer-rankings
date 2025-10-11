# rankings/generate_team_rankings_v3.py
import pandas as pd
import numpy as np
from math import log
from pathlib import Path

# ---- Config ----
MAX_GAMES = 20
WINDOW_DAYS = 365
RECENT_K = 10
RECENT_SHARE = 0.70
INACTIVE_HIDE_DAYS = 180
EPS = 1e-9

def segment_weights(n: int, recent_k: int = RECENT_K, recent_share: float = RECENT_SHARE) -> np.ndarray:
    """Deterministic 70/30 split: last recent_k games get recent_share weight."""
    w = np.zeros(n, dtype=float)
    k = min(n, recent_k)
    old = n - k
    if k:   w[-k:] = recent_share / k
    if old: w[:old] = (1.0 - recent_share) / old
    return w

def minmax_norm(s: pd.Series) -> pd.Series:
    """Min-max normalize to [0,1] range."""
    s_min, s_max = s.min(), s.max()
    if s_max == s_min:
        return pd.Series(0.5, index=s.index)
    return ((s - s_min) / (s_max - s_min)).round(3)

def wide_to_long(games_df: pd.DataFrame) -> pd.DataFrame:
    # Expect columns: Team A Match, Team B Match, Score A, Score B, Date
    a = games_df[["Team A Match","Team B Match","Score A","Score B","Date"]].rename(
        columns={"Team A Match":"Team","Team B Match":"Opponent","Score A":"GF","Score B":"GA"})
    b = games_df[["Team B Match","Team A Match","Score B","Score A","Date"]].rename(
        columns={"Team B Match":"Team","Team A Match":"Opponent","Score B":"GF","Score A":"GA"})
    long = pd.concat([a,b], ignore_index=True)
    long = long.dropna(subset=["Team","Opponent"])
    long["Date"] = pd.to_datetime(long["Date"], errors="coerce")
    return long

def clamp_window(df: pd.DataFrame, today=None) -> pd.DataFrame:
    today = today or pd.Timestamp.now().normalize()
    cutoff = today - pd.Timedelta(days=WINDOW_DAYS)
    return df[df["Date"] >= cutoff].copy()

def _team_recent_series(team_games: pd.DataFrame):
    g = team_games.sort_values("Date").tail(MAX_GAMES)
    n = len(g)
    if n == 0:
        return np.array([]), np.array([]), np.array([])
    w = segment_weights(n)
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

def gp_multiplier(gp: int) -> float:
    """Multiplicative penalty based on games played."""
    if gp >= 20: return 1.00
    if gp >= 10: return 0.90
    return 0.75

def build_rankings_from_wide(wide_matches_csv: Path, out_csv: Path):
    raw = pd.read_csv(wide_matches_csv, encoding="utf-8-sig")
    long = wide_to_long(raw)
    long = clamp_window(long)

    base = compute_off_def_raw(long)
    adj  = opponent_adjust(long, base)

    # Min-max normalize to [0,1] range
    Off_norm = minmax_norm(adj["Off_raw_adj"])
    Def_norm = minmax_norm(adj["Def_raw_adj"])
    # SOS proxy (replace with your own raw SOS if you compute it upstream)
    SOS_norm = minmax_norm(adj["Off_raw_adj"].rank(pct=True))  # neutral but monotonic

    out = adj.copy()
    out["Off_norm"] = Off_norm
    out["Def_norm"] = Def_norm
    out["SOS_norm"] = SOS_norm

    out["PowerScore"] = (0.375*out["Off_norm"] + 0.375*out["Def_norm"] + 0.25*out["SOS_norm"]).round(3)

    out["GamesPlayed"] = base["GamesPlayed"]
    out["GP_Mult"] = out["GamesPlayed"].apply(gp_multiplier)
    out["PowerScore_adj"] = (out["PowerScore"] * out["GP_Mult"]).round(3)
    out["Status"] = np.where(out["GamesPlayed"] >= 6, "Active", "Provisional")

    # Add LastGame for inactivity filtering
    last_date = long.groupby("Team")["Date"].max()
    out = out.merge(last_date.rename("LastGame"), left_on="Team", right_index=True, how="left")

    out = out.reset_index()  # Team as a column

    # Sort with offense-first tie-breakers and no ties
    sort_cols = ["PowerScore_adj","Off_norm","Def_norm","SOS_norm","GamesPlayed","Team"]
    out = out.sort_values(sort_cols, ascending=[False,False,False,False,False,True], kind="mergesort")
    # DON'T reset_index(drop=True) - keep TeamKey as index for proper mapping
    out["Rank"] = range(1, len(out) + 1)

    # Filter inactive teams (6 months)
    cutoff = pd.Timestamp.now().normalize() - pd.Timedelta(days=INACTIVE_HIDE_DAYS)
    out_visible = out[out["LastGame"] >= cutoff].copy()

    cols = ["Rank","Team","PowerScore_adj","PowerScore","GP_Mult","Off_norm","Def_norm","SOS_norm","GamesPlayed","Status","LastGame"]
    out_visible[cols].to_csv(out_csv, index=False, encoding="utf-8")
    return out_visible

if __name__ == "__main__":
    # Example CLI usage:
    # python -m rankings.generate_team_rankings_v3 --in Matched_Games.csv --out Rankings_v4.csv
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="in_path", required=True)
    p.add_argument("--out", dest="out_path", default="Rankings_v4.csv")
    args = p.parse_args()
    build_rankings_from_wide(Path(args.in_path), Path(args.out_path))
