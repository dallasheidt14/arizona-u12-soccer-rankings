#!/usr/bin/env python3
"""
Build U11 name map (raw → master), with strict 92% fuzzy and alias overlay.

This mirrors U12 intent but fixes all the drop/merge errors.
"""

from pathlib import Path
from typing import Optional
import pandas as pd

try:
    from rapidfuzz import process, fuzz
    HAVE_RF = True
except Exception:
    import difflib
    HAVE_RF = False

from src.utils.normalize_light import normalize_light

DIV = "az_boys_u11_2025"
MASTER = Path(f"data/master/{DIV}/master_teams.csv")          # 122 AZ teams
RAW_GAMES = Path(f"data/raw/{DIV}/games_raw.csv")
ALIAS_CSV = Path(f"data/mappings/{DIV}/aliases.csv")          # optional manual overrides
MAPPING_OUT = Path(f"data/mappings/{DIV}/name_map.csv")
UNMATCHED_OUT = Path(f"data/logs/{DIV}/unmatched.csv")


def _best_fuzzy(query: str, candidates: list[str]) -> Optional[str]:
    if not candidates: 
        return None
    if HAVE_RF:
        match, score, _ = process.extractOne(query, candidates, scorer=fuzz.WRatio)
        return match if score >= 92 else None
    # difflib fallback ~0.92
    m = difflib.get_close_matches(query, candidates, n=1, cutoff=0.92)
    return m[0] if m else None


def run():
    master = pd.read_csv(MASTER)
    assert {"team_id","display_name"}.issubset(master.columns), f"Master missing cols in {MASTER}"
    master["lower"] = master["display_name"].str.lower()
    master["norm"] = master["display_name"].map(normalize_light)

    games = pd.read_csv(RAW_GAMES)
    colA = "team_name_a" if "team_name_a" in games.columns else "Team A"
    colB = "team_name_b" if "team_name_b" in games.columns else "Team B"

    observed = pd.Series(pd.concat([games[colA], games[colB]], ignore_index=True)).dropna().unique()
    obs = pd.DataFrame({"raw_name": observed})
    obs["lower"] = obs["raw_name"].str.lower()
    obs["norm"]  = obs["raw_name"].map(normalize_light)

    # 1) exact lower match
    exact = obs.merge(master[["team_id","display_name","lower"]], on="lower", how="left")

    # 2) normalized match for unresolved
    pending_mask = exact["team_id"].isna()
    if pending_mask.any():
        pend = exact.loc[pending_mask, ["raw_name","norm"]]
        step2 = pend.merge(master[["team_id","display_name","norm"]], on="norm", how="left")
        exact.loc[pending_mask, ["team_id","display_name"]] = step2[["team_id","display_name"]].values

    # 3) fuzzy for remaining (strict)
    pending_mask = exact["team_id"].isna()
    if pending_mask.any():
        candidates = master["lower"].tolist()
        pend = exact.loc[pending_mask].copy()
        
        # Apply fuzzy matching to each pending row
        for idx, row in pend.iterrows():
            guess = _best_fuzzy(row["lower"], candidates)
            if guess:
                # Find the matching team in master
                match_row = master[master["lower"] == guess]
                if not match_row.empty:
                    exact.loc[idx, "team_id"] = match_row.iloc[0]["team_id"]
                    exact.loc[idx, "display_name"] = match_row.iloc[0]["display_name"]

    # 4) manual alias overlay (if provided)
    if ALIAS_CSV.exists():
        alias = pd.read_csv(ALIAS_CSV)
        # expected: raw_name, team_id  (display_name optional)
        alias["lower"] = alias["raw_name"].str.lower()
        overlay = alias.merge(master[["team_id","display_name","lower"]],
                              left_on=["team_id"], right_on=["team_id"], how="left")
        # Override rows whose lower matches alias
        idx = exact["lower"].isin(overlay["lower_x"] if "lower_x" in overlay.columns else overlay["lower"])
        # Map to alias-provided team_id where available, else by master
        exact.loc[idx, "team_id"] = overlay.set_index("lower_x")["team_id"].reindex(exact.loc[idx,"lower"]).values
        exact.loc[idx, "display_name"] = overlay.set_index("lower_x")["display_name_y"].reindex(exact.loc[idx,"lower"]).values

    # Save unmatched and handle external opponents
    unmatched = exact[exact["team_id"].isna()][["raw_name","lower","norm"]].drop_duplicates()
    UNMATCHED_OUT.parent.mkdir(parents=True, exist_ok=True)
    MAPPING_OUT.parent.mkdir(parents=True, exist_ok=True)

    if not unmatched.empty:
        # Generate external IDs for non-Arizona teams
        import hashlib
        for idx, row in unmatched.iterrows():
            raw_name = row["raw_name"]
            external_id = f"ext_{hashlib.sha1(raw_name.encode()).hexdigest()[:12]}"
            exact.loc[exact["raw_name"] == raw_name, "team_id"] = external_id
            exact.loc[exact["raw_name"] == raw_name, "display_name"] = raw_name
        
        print(f"Generated external IDs for {len(unmatched)} non-Arizona opponents")
        
        # Save unmatched for reference (but don't fail)
        unmatched.to_csv(UNMATCHED_OUT, index=False)
        print(f"Saved unmatched teams to {UNMATCHED_OUT}")

    mapping = exact[["raw_name","team_id","display_name"]].drop_duplicates()
    mapping.to_csv(MAPPING_OUT, index=False)
    print(f"Wrote name_map: {MAPPING_OUT} ({len(mapping)} rows)")


if __name__ == "__main__":
    run()