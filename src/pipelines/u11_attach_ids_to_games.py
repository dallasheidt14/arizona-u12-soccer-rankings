#!/usr/bin/env python3
"""
Attach IDs and produce ID histories + a compat games file (so v53 can run).
"""

from pathlib import Path
import hashlib
import pandas as pd

DIV = "az_boys_u11_2025"
MASTER     = Path(f"data/master/{DIV}/master_teams.csv")
RAW_GAMES  = Path(f"data/raw/{DIV}/games_raw.csv")
NAME_MAP   = Path(f"data/mappings/{DIV}/name_map.csv")
HIST_OUT   = Path(f"data/outputs/{DIV}/histories.csv")
COMPAT_OUT = Path("data/gold/Matched_Games_U11_COMPAT.csv")  # for legacy generator


def ext_id(name: str) -> str:
    base = f"ext_u11_2025:{(name or '').strip()}"
    return hashlib.sha1(base.encode()).hexdigest()[:12]


def run():
    master = pd.read_csv(MASTER)[["team_id","display_name"]].copy()
    mapping = pd.read_csv(NAME_MAP)  # raw_name -> team_id, display_name
    games = pd.read_csv(RAW_GAMES)

    # Column normalization
    colA = "team_name_a" if "team_name_a" in games.columns else "Team A"
    colB = "team_name_b" if "team_name_b" in games.columns else "Team B"
    date_col = "date" if "date" in games.columns else "Date"
    sa = "score_a" if "score_a" in games.columns else "Score A"
    sb = "score_b" if "score_b" in games.columns else "Score B"

    g = games.rename(columns={
        colA: "raw_a", colB: "raw_b", date_col: "date", sa: "score_a", sb: "score_b"
    }).copy()

    # Attach AZ team ids when present; keep opponents that are off-master as 'ext_*'
    g = g.merge(mapping.rename(columns={"raw_name":"raw_a","team_id":"team_id_a","display_name":"display_name_a"}),
                on="raw_a", how="left")
    g = g.merge(mapping.rename(columns={"raw_name":"raw_b","team_id":"team_id_b","display_name":"display_name_b"}),
                on="raw_b", how="left")

    # external ids if missing
    g["team_id_a"] = g["team_id_a"].fillna(g["raw_a"].map(ext_id))
    g["team_id_b"] = g["team_id_b"].fillna(g["raw_b"].map(ext_id))
    g["display_name_a"] = g["display_name_a"].fillna(g["raw_a"])
    g["display_name_b"] = g["display_name_b"].fillna(g["raw_b"])

    # Two directional per-team rows
    rows_a = g[["team_id_a","display_name_a","team_id_b","display_name_b","date","score_a","score_b"]].copy()
    rows_a.columns = ["team_id","display_name","opponent_team_id","opponent_display_name","date","goals_for","goals_against"]

    rows_b = g[["team_id_b","display_name_b","team_id_a","display_name_a","date","score_b","score_a"]].copy()
    rows_b.columns = ["team_id","display_name","opponent_team_id","opponent_display_name","date","goals_for","goals_against"]

    hist = pd.concat([rows_a, rows_b], ignore_index=True)
    hist["result"] = hist.apply(lambda r: "W" if r.goals_for > r.goals_against else ("L" if r.goals_for < r.goals_against else "D"), axis=1)

    # Final schema check
    req = {"team_id","display_name","opponent_team_id","opponent_display_name","date","goals_for","goals_against","result"}
    if not req.issubset(hist.columns):
        raise ValueError(f"Histories missing {req - set(hist.columns)}")

    HIST_OUT.parent.mkdir(parents=True, exist_ok=True)
    hist.to_csv(HIST_OUT, index=False)
    print(f"Wrote histories: {HIST_OUT} ({len(hist)} rows)")

    # ===== Compat file for legacy generator (expects TeamKey/OppKey/Team/Opp/etc.)
    compat = hist.rename(columns={
        "team_id": "TeamKey",
        "opponent_team_id": "OppKey",
        "display_name": "Team",
        "opponent_display_name": "Opp",
        "goals_for": "Score A",
        "goals_against": "Score B",
        "date": "Date"
    })[["TeamKey","OppKey","Team","Opp","Score A","Score B","Date"]].copy()

    compat.to_csv(COMPAT_OUT, index=False)
    print(f"Wrote legacy-compat games for generator: {COMPAT_OUT} ({len(compat)} rows)")


if __name__ == "__main__":
    run()