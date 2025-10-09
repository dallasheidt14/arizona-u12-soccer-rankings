# rankings/generate_team_rankings_v3.py
import pandas as pd
import numpy as np
from math import log
from pathlib import Path

# ---- Config ----
MAX_GAMES = 20
WINDOW_DAYS = 365
HALF_LIFE_GAMES = 12.0
STRONG_K = 1.0
MILD_K   = 0.30
CASCADE_TIERS = True
EPS = 1e-9

def recency_weights(n: int, half_life_games: float = HALF_LIFE_GAMES) -> np.ndarray:
    lam = log(2.0) / max(half_life_games, 1e-6)
    w = np.exp(-lam * (np.arange(n)[::-1]))  # newest largest
    return w / w.sum()

def percentile_norm(s: pd.Series) -> pd.Series:
    ranks = s.rank(method="first", pct=True)
    return (ranks * 99 + 1).round(2)

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
    w = recency_weights(n)
    return g["GF"].to_numpy(), g["GA"].to_numpy(), w

def compute_off_def_raw(long_games: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for team, tg in long_games.groupby("Team", sort=False):
        gf, ga, w = _team_recent_series(tg)
        if len(w) == 0:
            off_raw, def_raw, gp = 0.0, 0.0, 0
        else:
            off_raw = float((gf * w).sum())
            def_raw = float((ga * w).sum())
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

def games_penalty(gp: int) -> float:
    gp = int(gp) if pd.notna(gp) else 0
    pen = 0.0
    if gp < 10:
        pen += (10 - gp) * STRONG_K
        if CASCADE_TIERS:
            pen += (20 - 10) * MILD_K
    elif gp < 20:
        pen += (20 - gp) * MILD_K
    return pen

def status_from_gp(gp: int) -> str:
    gp = int(gp) if pd.notna(gp) else 0
    if gp < 10:  return "Provisional (<10 GP)"
    if gp < 20:  return "Limited Sample (10–19 GP)"
    return "Full Sample"

def build_rankings_from_wide(wide_matches_csv: Path, out_csv: Path):
    raw = pd.read_csv(wide_matches_csv, encoding="utf-8-sig")
    long = wide_to_long(raw)
    long = clamp_window(long)

    base = compute_off_def_raw(long)
    adj  = opponent_adjust(long, base)

    # Normalize to 1..100 via percentiles (prevents "tons of 1s")
    Off_norm = percentile_norm(adj["Off_raw_adj"] + EPS)
    # Make defense "higher is better" by inverting GA sensibly:
    # center around median offense so scales are comparable
    def_center = Off_norm.median() if Off_norm.notna().any() else 50.0
    Def_norm = percentile_norm((def_center := (adj["Off_raw_adj"].median() if adj["Off_raw_adj"].notna().any() else 1.0)) - adj["Def_raw_adj"] + EPS)
    # SOS proxy (replace with your own raw SOS if you compute it upstream)
    SOS_norm = percentile_norm(adj["Off_raw_adj"].rank(pct=True))  # neutral but monotonic; swap in your SOS when ready

    out = adj.copy()
    out["Off_norm"] = Off_norm
    out["Def_norm"] = Def_norm
    out["SOS_norm"] = SOS_norm

    out["PowerScore"] = (0.375*out["Off_norm"] + 0.375*out["Def_norm"] + 0.25*out["SOS_norm"]).round(2)

    out["GamesPlayed"] = base["GamesPlayed"]
    out["PenaltyGP"]   = out["GamesPlayed"].apply(games_penalty)
    out["PowerScore_adj"] = (out["PowerScore"] - out["PenaltyGP"]).clip(lower=0).round(2)
    out["Status"] = out["GamesPlayed"].apply(status_from_gp)

    out = out.reset_index()  # Team as a column

    # Sort with offense-first tie-breakers and no ties
    sort_cols = ["PowerScore_adj","Off_norm","Def_norm","SOS_norm","GamesPlayed","Team"]
    out = out.sort_values(sort_cols, ascending=[False,False,False,False,False,True], kind="mergesort").reset_index(drop=True)
    out["Rank"] = out.index + 1

    cols = ["Rank","Team","PowerScore_adj","PowerScore","PenaltyGP","Off_norm","Def_norm","SOS_norm","GamesPlayed","Status"]
    out[cols].to_csv(out_csv, index=False, encoding="utf-8")
    return out

if __name__ == "__main__":
    # Example CLI usage:
    # python -m rankings.generate_team_rankings_v3 --in Matched_Games.csv --out Rankings_v3.csv
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="in_path", required=True)
    p.add_argument("--out", dest="out_path", default="Rankings_v3.csv")
    args = p.parse_args()
    build_rankings_from_wide(Path(args.in_path), Path(args.out_path))
