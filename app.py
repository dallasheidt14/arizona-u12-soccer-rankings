# app.py
import os
import time
import json
import urllib.parse
from pathlib import Path
from typing import Optional, List, Dict

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ---- Config ----
DATA_DIR = Path(".")  # root of your pipeline outputs
INDEX_JSON = DATA_DIR / "rankings_index.json"            # created in Phase 3
RANKINGS_FALLBACK = DATA_DIR / "Rankings.csv"            # global default
HISTORY_FALLBACK = DATA_DIR / "Team_Game_Histories.csv"  # global default

# Optional: look for slice-specific files when state/gender/year provided
def slice_suffix(state: Optional[str], gender: Optional[str], year: Optional[str]):
    parts = []
    if state: parts.append(state)
    if gender: parts.append(gender)  # expect "MALE"/"FEMALE"
    if year: parts.append(str(year))
    return "_" + "_".join(parts) if parts else ""

# Simple in-process cache keyed by filepath mtime
class _Cache:
    def __init__(self):
        self._data: Dict[str, dict] = {}
    def get_df(self, path: Path) -> Optional[pd.DataFrame]:
        if not path.exists():
            return None
        mtime = path.stat().st_mtime
        key = f"{path}:{mtime}"
        for k in list(self._data.keys()):
            if k.startswith(str(path)+":") and k != key:
                del self._data[k]
        if key not in self._data:
            if path.suffix.lower() == ".parquet":
                df = pd.read_parquet(path)
            else:
                # utf-8-sig strips BOM if present; low_memory avoids mixed dtypes
                df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
            self._data[key] = {"df": df}
        return self._data[key]["df"]

CACHE = _Cache()

app = FastAPI(title="Youth Rankings API", version="1.0.0")

# Allow your frontend origin(s)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "*"  # tighten in prod
    ],
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

# ---- Utilities ----
def load_index():
    if INDEX_JSON.exists():
        with INDEX_JSON.open("r", encoding="utf-8") as f:
            data = json.load(f)
        slices = data.get("slices", [])
        # sanitize gender variants to MALE/FEMALE for consistency
        for s in slices:
            if isinstance(s.get("gender"), str):
                g = s["gender"].upper()
                if g in ("M", "MALE", "BOYS"):
                    s["gender"] = "MALE"
                elif g in ("F", "FEMALE", "GIRLS"):
                    s["gender"] = "FEMALE"
        return {"slices": slices}
    # fallback: construct a minimal "All" listing
    return {"slices": [{
        "state": None, "gender": None, "year": None,
        "rankings": RANKINGS_FALLBACK.name,
        "histories": HISTORY_FALLBACK.name,
        "teams": None, "games": None
    }]}

def find_rankings_path(state: Optional[str], gender: Optional[str], year: Optional[str]) -> Path:
    sfx = slice_suffix(state, gender, year)
    # Prefer v3 rankings, then CSV, then Parquet for the slice
    candidates = [
        DATA_DIR / f"Rankings_v3{sfx}.csv",
        DATA_DIR / f"Rankings_v3.csv",
        DATA_DIR / f"Rankings{sfx}.csv",
        DATA_DIR / f"Rankings{sfx}.parquet",
    ]
    for p in candidates:
        if p.exists():
            return p
    # Fallback to global - try multiple possible names (v3 first)
    fallback_candidates = [
        DATA_DIR / "Rankings_v3.csv",
        DATA_DIR / "Rankings.csv",
        DATA_DIR / "Rankings_PowerScore.csv", 
        RANKINGS_FALLBACK,
        DATA_DIR / "Rankings.parquet"
    ]
    for p in fallback_candidates:
        if p.exists():
            return p
    return fallback_candidates[0]  # Return first candidate even if it doesn't exist

def find_history_path(state: Optional[str], gender: Optional[str], year: Optional[str]) -> Path:
    sfx = slice_suffix(state, gender, year)
    candidates = [
        DATA_DIR / f"Team_Game_Histories{sfx}.parquet",
        DATA_DIR / f"Team_Game_Histories{sfx}.csv",
    ]
    for p in candidates:
        if p.exists():
            return p
    return HISTORY_FALLBACK if HISTORY_FALLBACK.exists() else candidates[-1]

# Canonical column mapping - maps canonical names to all known synonyms
CANON = {
    # Canonical -> known synonyms in your CSVs
    "Team": ["Team", "team_name", "Name"],
    "PowerScore": ["PowerScore", "Power Score", "Power_Score", "Power"],
    "Off_norm": ["Off_norm", "Offense_norm", "Offense Score", "Offense_Score", "Off Rating", "Offensive Rating"],
    "Def_norm": ["Def_norm", "Defense_norm", "Adj Defense Score", "Defense Score", "Def Rating", "Defensive Rating"],
    "SOS_norm": ["SOS_norm", "Schedule Strength", "Schedule Rating", "SOS"],
    "GamesPlayed": ["GamesPlayed", "Games Played", "GP"],
    "WL": ["WL", "W-L-T", "Record"],
    "State": ["State"],
    "Gender": ["Gender", "Sex"],
    "Year": ["Year", "BirthYear", "Birth Year"],
    # History endpoint:
    "GoalsFor": ["GoalsFor", "Goals For", "GF"],
    "GoalsAgainst": ["GoalsAgainst", "Goals Against", "GA"],
    "Date": ["Date", "MatchDate"],
    "Opponent": ["Opponent", "Opp", "Opponent Name"],
    "Opponent_BaseStrength": ["Opponent_BaseStrength", "Opp_BaseStrength", "Opp Strength", "Opponent Strength"],
    "expected_gd": ["expected_gd", "Expected_GD", "ExpGD"],
    "gd_delta": ["gd_delta", "Delta_vs_Expected", "DeltaExp"],
    "impact_bucket": ["impact_bucket", "Impact", "ImpactBucket"],
}

import re
import logging

logging.basicConfig(level=logging.INFO)

def _norm_header(s: str) -> str:
    s = str(s).replace("\ufeff", "")      # strip BOM
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)     # spaces/dashes → underscores
    s = re.sub(r"_+", "_", s).strip("_")  # collapse repeats
    return s

# Build a reverse lookup map once (normalized form → canonical name)
_CANON_REVERSE = {}
for canon, variants in CANON.items():
    # Include the canonical key itself as a match target too
    for v in set([canon] + variants):
        _CANON_REVERSE[_norm_header(v)] = canon

def normalize_headers(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df with columns renamed to canonical names where possible."""
    renamed = {}
    unmapped = []
    for c in df.columns:
        key = _norm_header(c)
        if key in _CANON_REVERSE:
            canonical_name = _CANON_REVERSE[key]
            # Handle duplicates by keeping the first occurrence
            if canonical_name not in renamed:
                renamed[c] = canonical_name
            else:
                # Skip duplicate mappings to avoid DataFrame issues
                renamed[c] = c
                unmapped.append(f"{c} (duplicate of {canonical_name})")
        else:
            renamed[c] = c
            unmapped.append(c)
    if unmapped:
        logging.info("Unmapped headers (left as-is): %s", unmapped)
    return df.rename(columns=renamed)

def to_num(df, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        if c in out.columns:
            s = out[c].astype(str)
            # Handle percent and commas
            s = s.str.replace("%", "", regex=False).str.replace(",", "", regex=False)
            # Handle negatives in parentheses: "(1234)" -> "-1234"
            s = s.str.replace(r"^\((.*)\)$", r"-\1", regex=True)
            out[c] = pd.to_numeric(s, errors="coerce")
    return out

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Canonicalize headers and coerce numeric metrics safely."""
    df2 = normalize_headers(df)

    # Back-compat for a few legacy names that carry data under non-canonical labels.
    # (If any slipped through header normalization above, catch them here.)
    if "Power Score" in df2.columns and "PowerScore" not in df2.columns:
        df2["PowerScore"] = df2["Power Score"]

    # Numeric casts where relevant
    df2 = to_num(df2, ["PowerScore", "Off_norm", "Def_norm", "SOS_norm", "GamesPlayed", "GoalsFor", "GoalsAgainst"])

    # Ensure Team is str
    if "Team" in df2.columns:
        df2["Team"] = df2["Team"].astype(str)

    return df2

def safe_sort(df: pd.DataFrame, by: str, order: str) -> pd.DataFrame:
    # Fall back to a safe column if requested one missing or non-numeric where needed
    ascending = (order == "asc")
    if by not in df.columns:
        fallback = "PowerScore" if "PowerScore" in df.columns else None
        return df if fallback is None else df.sort_values(by=fallback, ascending=False, na_position="last")
    try:
        return df.sort_values(by=by, ascending=ascending, na_position="last")
    except Exception:
        # e.g., mixed types; try numeric coercion then retry
        tmp = df.copy()
        tmp[by] = pd.to_numeric(tmp[by], errors="coerce")
        return tmp.sort_values(by=by, ascending=ascending, na_position="last")

# ---- GP Penalty & Status helpers ----
STRONG_K = 1.0   # penalty points per missing game under 10
MILD_K   = 0.30  # penalty points per missing game from 10..19
CASCADE_TIERS = True  # under-10 receives both tiers if True

def _games_penalty_points(gp: int) -> float:
    gp = int(gp) if pd.notna(gp) else 0
    penalty = 0.0
    if gp < 10:
        penalty += (10 - gp) * STRONG_K
        if CASCADE_TIERS:
            penalty += (20 - 10) * MILD_K
    elif gp < 20:
        penalty += (20 - gp) * MILD_K
    return penalty

def _status_from_gp(gp: int) -> str:
    gp = int(gp) if pd.notna(gp) else 0
    if gp < 10:
        return "Provisional (<10 GP)"
    if gp < 20:
        return "Limited Sample (10–19 GP)"
    return "Full Sample"

def _ensure_numeric(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

# ---- Endpoints ----

@app.get("/api/slices")
def api_slices():
    return load_index()

@app.get("/api/rankings")
def api_rankings(
    state: Optional[str] = Query(None),
    gender: Optional[str] = Query(None),   # MALE/FEMALE
    year: Optional[str] = Query(None),
    q: Optional[str] = Query(None),        # search team name
    sort: Optional[str] = Query("PowerScore"),  # PowerScore|Off_norm|Def_norm|SOS_norm|GamesPlayed
    order: Optional[str] = Query("desc"),  # asc|desc
    limit: int = Query(500, ge=1, le=5000),
):
    path = find_rankings_path(state, gender, year)
    df = CACHE.get_df(path)
    if df is None:
        raise HTTPException(status_code=404, detail="Rankings file not found")

    df = normalize_columns(df)

    # Optional in-file filtering if global file
    if state and "State" in df.columns:
        df = df[df["State"] == state]
    if gender and "Gender" in df.columns:
        # Map input gender to data gender values (data uses M/F, not MALE/FEMALE)
        if gender.upper() in ("M","MALE","BOYS"):
            df = df[df["Gender"].astype(str).str.upper() == "M"]
        else:
            df = df[df["Gender"].astype(str).str.upper() == "F"]
    if year and "Year" in df.columns:
        df = df[df["Year"].astype(str) == str(year)]

    if q and "Team" in df.columns:
        df = df[df["Team"].str.contains(q, case=False, na=False)]

    # Ensure numeric types
    df = _ensure_numeric(df, ["PowerScore","Off_norm","Def_norm","SOS_norm","GamesPlayed"])

    # Compute GP penalties and adjusted score even if materializer didn't write it
    if "GamesPlayed" not in df.columns:
        df["GamesPlayed"] = pd.NA

    df["PenaltyGP"] = df["GamesPlayed"].fillna(0).astype("Int64").apply(lambda x: _games_penalty_points(int(x) if pd.notna(x) else 0))

    if "PowerScore" in df.columns and "PowerScore_adj" not in df.columns:
        df["PowerScore_adj"] = (df["PowerScore"] - df["PenaltyGP"]).clip(lower=0).round(2)

    # Status badge
    df["Status"] = df["GamesPlayed"].fillna(0).astype("Int64").apply(lambda x: _status_from_gp(int(x) if pd.notna(x) else 0))

    # Deterministic, offense-first tie breaking (no ties)
    sort_cols  = []
    ascending  = []

    if "PowerScore_adj" in df.columns:
        sort_cols.append("PowerScore_adj"); ascending.append(False)
    elif "PowerScore" in df.columns:
        sort_cols.append("PowerScore"); ascending.append(False)

    for key in ["Off_norm","Def_norm","SOS_norm","GamesPlayed"]:
        if key in df.columns:
            sort_cols.append(key)
            ascending.append(False)

    # Final deterministic fallback
    if "Team" in df.columns:
        sort_cols.append("Team"); ascending.append(True)

    if sort_cols:
        df = df.sort_values(by=sort_cols, ascending=ascending, kind="mergesort").reset_index(drop=True)
        df["Rank"] = df.index + 1

    # Keep the response schema stable
    preferred_cols = [
        "Rank", "Team",
        "PowerScore_adj", "PowerScore", "PenaltyGP",
        "Off_norm", "Def_norm", "SOS_norm",
        "GamesPlayed", "Status", "WL"
    ]
    cols = [c for c in preferred_cols if c in df.columns]
    return JSONResponse(df[cols].head(limit).to_dict(orient="records"))

@app.get("/api/team/{team}")
def api_team_history(
    team: str,
    state: Optional[str] = Query(None),
    gender: Optional[str] = Query(None),
    year: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=5000),
):
    path = find_history_path(state, gender, year)
    df = CACHE.get_df(path)
    if df is None:
        raise HTTPException(status_code=404, detail="History file not found")
    df = normalize_columns(df)

    if state and "State" in df.columns:
        df = df[df["State"] == state]
    if gender and "Gender" in df.columns:
        # Map input gender to data gender values (data uses M/F, not MALE/FEMALE)
        if gender.upper() in ("M","MALE","BOYS"):
            df = df[df["Gender"].astype(str).str.upper() == "M"]
        else:
            df = df[df["Gender"].astype(str).str.upper() == "F"]
    if year and "Year" in df.columns:
        df = df[df["Year"].astype(str) == str(year)]

    team_name = urllib.parse.unquote(team)
    if "Team" in df.columns:
        df = df[df["Team"] == team_name]
    if df.empty:
        return []

    wanted = ["Date","Opponent","GoalsFor","GoalsAgainst","expected_gd","gd_delta","impact_bucket","Opponent_BaseStrength"]
    cols = [c for c in wanted if c in df.columns]

    if "Date" in df.columns:
        try:
            df["Date"] = pd.to_datetime(df["Date"])
        except Exception:
            pass
        df = df.sort_values("Date", ascending=False)
        # pretty ISO date string
        try:
            df["Date"] = pd.to_datetime(df["Date"]).dt.date.astype(str)
        except Exception:
            pass

    return JSONResponse(df[cols].head(limit).to_dict(orient="records"))

@app.get("/api/health")
def api_health(state: Optional[str] = None, gender: Optional[str] = None, year: Optional[str] = None):
    rp = str(find_rankings_path(state, gender, year))
    hp = str(find_history_path(state, gender, year))
    info = {}
    for name, p in (("rankings", rp), ("history", hp)):
        try:
            df = CACHE.get_df(Path(p))
            cols = list(df.columns)[:50] if df is not None else []
        except Exception:
            cols = ["<error reading>"]
        info[name] = {"path": p, "columns_head": cols}
    return info

@app.get("/api/debug_paths")
def debug_paths(state: str = "AZ", gender: str = "MALE", year: int = 2014, limit: int = 30):
    """
    Shows which file is being used for Rankings + the first N raw & normalized headers.
    Helps diagnose BOM/spacing/case mismatches quickly.
    """
    # Reuse your existing path resolution (update if your helper names differ)
    rankings_path = find_rankings_path(state, gender, year)  # your existing helper
    if not rankings_path or not Path(rankings_path).exists():
        return JSONResponse(
            {
                "rankings_path": rankings_path,
                "exists": False,
                "note": "Rankings file not found for given slice."
            },
            status_code=404
        )

    import pandas as pd

    # Read raw (without header normalization) but with BOM-safe encoding:
    try:
        if str(rankings_path).lower().endswith(".parquet"):
            raw_df = pd.read_parquet(rankings_path)
        else:
            raw_df = pd.read_csv(rankings_path, nrows=limit, encoding="utf-8-sig", low_memory=False)
        raw_cols = list(raw_df.columns)
    except Exception as e:
        return JSONResponse(
            {"rankings_path": rankings_path, "exists": True, "error": f"Failed to read: {e}"},
            status_code=500
        )

    # Apply your normalization
    normalized_df = normalize_columns(raw_df.copy())
    norm_cols = list(normalized_df.columns)

    return {
        "rankings_path": rankings_path,
        "exists": True,
        "raw_columns": raw_cols[:limit],
        "normalized_columns": norm_cols[:limit],
        "sample_normalized_head": normalized_df.head(min(5, limit)).to_dict(orient="records"),
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
