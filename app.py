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
                df = pd.read_csv(path)
            self._data[key] = {"df": df}
        return self._data[key]["df"]

CACHE = _Cache()

app = FastAPI(title="Youth Rankings API", version="1.0.0")

# Allow your frontend origin(s)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in prod
    allow_credentials=False,
    allow_methods=["GET"],
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
    # Prefer CSV then Parquet for the slice
    candidates = [
        DATA_DIR / f"Rankings{sfx}.csv",
        DATA_DIR / f"Rankings{sfx}.parquet",
    ]
    for p in candidates:
        if p.exists():
            return p
    # Fallback to global - try multiple possible names (CSV first)
    fallback_candidates = [
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

def coalesce_columns(df, canon: dict[str, list[str]]) -> pd.DataFrame:
    """Create canonical columns by copying from the first synonym that exists."""
    out = df.copy()
    existing = set(out.columns)
    for target, candidates in canon.items():
        if target in existing:
            continue
        for c in candidates:
            if c in existing:
                out[target] = out[c]
                break
    return out

def to_num(df, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    return out

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Broader normalization + light typing. Never throw."""
    df2 = coalesce_columns(df, CANON)

    # Light renames for a few legacy names that collide with different meaning
    if "Power Score" in df2.columns and "PowerScore" not in df2.columns:
        df2["PowerScore"] = df2["Power Score"]

    # Numeric casts where relevant
    df2 = to_num(df2, ["PowerScore", "Off_norm", "Def_norm", "SOS_norm", "GamesPlayed", "GoalsFor", "GoalsAgainst"])

    # Make sure Team is string
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

    # Add Rank and build payload from whatever exists
    df = df.reset_index(drop=True)
    if "Rank" not in df.columns:
        df.insert(0, "Rank", df.index + 1)

    preferred_cols = ["Team","PowerScore","Off_norm","Def_norm","SOS_norm","GamesPlayed","WL"]
    cols = ["Rank"] + [c for c in preferred_cols if c in df.columns]

    # Safe sort
    df = safe_sort(df, sort, order)

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
