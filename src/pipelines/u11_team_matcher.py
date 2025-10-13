# src/pipelines/u11_team_matcher.py
from pathlib import Path
import hashlib, re
import pandas as pd
from typing import Optional
from fuzzywuzzy import process, fuzz

from src.utils.paths_u11 import (
    master_state_path, canonical_raw_path, mappings_dir, logs_dir, outputs_dir, compat_path
)

FUZZY = 90
_PUNCT = re.compile(r"[^a-z0-9 ]")
_WS = re.compile(r"\s+")

def normalize_name(s: str) -> str:
    if not isinstance(s, str): return ""
    s = s.lower()
    s = _PUNCT.sub("", s)
    s = _WS.sub(" ", s).strip()
    return s

def ext_id(name: str, season: int) -> str:
    return hashlib.sha1(f"ext_u11_{season}:{(name or '').strip()}".encode()).hexdigest()[:12]

def build_name_map(state: str, season: int):
    master = pd.read_csv(master_state_path(state))
    
    # Normalize column names (handle gotsport_team_id -> team_id, team_name -> display_name)
    if "gotsport_team_id" in master.columns:
        master = master.rename(columns={"gotsport_team_id": "team_id"})
    if "team_name" in master.columns:
        master = master.rename(columns={"team_name": "display_name"})
    
    assert {"team_id","display_name"}.issubset(master.columns), f"Master missing team_id/display_name. Has: {list(master.columns)}"
    master["norm"] = master["display_name"].map(normalize_name)

    raw = pd.read_csv(canonical_raw_path(state, season))
    observed = pd.Series(pd.concat([raw["Team A"], raw["Team B"]], ignore_index=True)).dropna().unique()
    obs = pd.DataFrame({"raw_name": observed})
    obs["norm"] = obs["raw_name"].map(normalize_name)

    # exact by norm
    m1 = obs.merge(master[["team_id","display_name","norm"]], on="norm", how="left")

    # fuzzy for unresolved
    pend = m1[m1["team_id"].isna()].copy()
    if not pend.empty:
        cands = master["norm"].tolist()
        guesses = []
        for q in pend["norm"]:
            g, sc = process.extractOne(q, cands, scorer=fuzz.WRatio) or (None, 0)
            guesses.append(g if g and sc >= FUZZY else None)
        pend["guess_norm"] = guesses
        m2 = pend.merge(master[["team_id","display_name","norm"]], left_on="guess_norm", right_on="norm", how="left", suffixes=('', '_match'))
        # Only update rows that have matches
        mask = m1["team_id"].isna() & m2["team_id"].notna()
        m1.loc[mask, "team_id"] = m2.loc[mask, "team_id"]
        m1.loc[mask, "display_name"] = m2.loc[mask, "display_name"]

    maps = mappings_dir(state, season)
    logs = logs_dir(state, season)
    
    # Handle unmatched teams - categorize them as external rather than failing
    unmatched = m1[m1["team_id"].isna()][["raw_name","norm"]].drop_duplicates()
    external_teams = []
    
    for _, row in unmatched.iterrows():
        raw_name = row["raw_name"]
        # Generate external ID for non-AZ teams
        ext_id_val = ext_id(raw_name, season)
        external_teams.append({
            "raw_name": raw_name,
            "team_id": ext_id_val,
            "display_name": raw_name,
            "match_type": "EXTERNAL"
        })
    
    # Combine matched and external teams
    matched_teams = m1[m1["team_id"].notna()][["raw_name","team_id","display_name"]].copy()
    matched_teams["match_type"] = "MATCHED"
    
    all_teams = pd.concat([matched_teams, pd.DataFrame(external_teams)], ignore_index=True)
    
    # Save logs for review
    if not unmatched.empty:
        (logs / "unmatched.csv").parent.mkdir(parents=True, exist_ok=True)
        unmatched.to_csv(logs / "unmatched.csv", index=False)
        print(f"[INFO] {len(unmatched)} unmatched teams categorized as external")
    
    # Save external candidates for review
    if external_teams:
        pd.DataFrame(external_teams).to_csv(logs / "external_candidates.csv", index=False)
        print(f"[INFO] {len(external_teams)} external teams logged")

    name_map = all_teams[["raw_name","team_id","display_name"]].drop_duplicates()
    name_map.to_csv(maps / "name_map.csv", index=False)
    print(f"name_map -> {maps/'name_map.csv'} ({len(name_map)} rows)")

def build_histories(state: str, season: int):
    master = pd.read_csv(master_state_path(state))
    
    # Normalize column names (handle gotsport_team_id -> team_id, team_name -> display_name)
    if "gotsport_team_id" in master.columns:
        master = master.rename(columns={"gotsport_team_id": "team_id"})
    if "team_name" in master.columns:
        master = master.rename(columns={"team_name": "display_name"})
    
    master = master[["team_id","display_name"]]
    # Convert team_id to string for consistent merging
    master["team_id"] = master["team_id"].astype(str)
    
    raw = pd.read_csv(canonical_raw_path(state, season))
    mapping = pd.read_csv(mappings_dir(state, season) / "name_map.csv")
    # Convert mapping team_id to string as well
    mapping["team_id"] = mapping["team_id"].astype(str)

    g = raw.copy()
    g = g.merge(mapping.rename(columns={"raw_name":"Team A","team_id":"Team A Id","display_name":"Team A Display"}), on="Team A", how="left")
    g = g.merge(mapping.rename(columns={"raw_name":"Team B","team_id":"Team B Id","display_name":"Team B Display"}), on="Team B", how="left")

    # external IDs for true non-AZ opponents; log them for review
    logs = logs_dir(state, season)
    ext_names = []
    for side in ("A","B"):
        miss = g[f"Team {side} Id"].isna()
        if miss.any():
            ext_names.append(g.loc[miss, [f"Team {side}"]].rename(columns={f"Team {side}":"raw_opponent"}))
            g.loc[miss, f"Team {side} Id"] = g.loc[miss, f"Team {side}"].map(lambda x: ext_id(x, season))
            g.loc[miss, f"Team {side} Display"] = g.loc[miss, f"Team {side}"]

    if ext_names:
        pd.concat(ext_names).drop_duplicates().to_csv(logs / "external_candidates.csv", index=False)

    # two directional histories
    a = g[["Team A Id","Team B Id","Date","Score A","Score B"]].copy()
    a.columns = ["team_id","opponent_team_id","date","goals_for","goals_against"]
    b = g[["Team B Id","Team A Id","Date","Score B","Score A"]].copy()
    b.columns = ["team_id","opponent_team_id","date","goals_for","goals_against"]
    hist = pd.concat([a,b], ignore_index=True)
    hist["result"] = hist.apply(lambda r: "W" if r.goals_for > r.goals_against else ("L" if r.goals_for < r.goals_against else "D"), axis=1)

    # display strictly from master for AZ teams
    hist = hist.merge(master, on="team_id", how="left")
    hist = hist.merge(master.rename(columns={"team_id":"opponent_team_id","display_name":"opponent_display_name"}),
                      on="opponent_team_id", how="left")

    outdir = outputs_dir(state, season)
    hist_path = outdir / "histories.csv"
    hist.to_csv(hist_path, index=False)
    print(f"histories -> {hist_path} ({len(hist)} rows)")

    # legacy-compat for v53 generator
    compat = hist.rename(columns={
        "team_id":"TeamKey","opponent_team_id":"OppKey",
        "display_name":"Team","opponent_display_name":"Opp",
        "goals_for":"Score A","goals_against":"Score B","date":"Date"
    })[["TeamKey","OppKey","Team","Opp","Score A","Score B","Date"]]
    
    # Create Team A/Team B format for compatibility using raw games
    # Map team IDs back to team names using the mapping
    raw = pd.read_csv(canonical_raw_path(state, season))
    mapping = pd.read_csv(mappings_dir(state, season) / "name_map.csv")
    
    # Merge Team A with mapping
    raw_a = raw.merge(mapping[["raw_name","display_name"]], left_on="Team A", right_on="raw_name", how="left")
    raw_a = raw_a.rename(columns={"display_name": "Team A Name"})
    
    # Merge Team B with mapping  
    raw_b = raw_a.merge(mapping[["raw_name","display_name"]], left_on="Team B", right_on="raw_name", how="left")
    raw_b = raw_b.rename(columns={"display_name": "Team B Name"})
    
    # Create final COMPAT format
    compat_ab = raw_b[["Team A Name","Team B Name","Score A","Score B","Date"]].copy()
    compat_ab = compat_ab.rename(columns={"Team A Name": "Team A", "Team B Name": "Team B"})
    
    compat_file = compat_path(state)
    compat_ab.to_csv(compat_file, index=False)
    print(f"compat -> {compat_file} ({len(compat_ab)} rows)")

def run(state="AZ", season=2025):
    build_name_map(state, season)
    build_histories(state, season)

if __name__ == "__main__":
    run("AZ", 2025)
