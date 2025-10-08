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
RANKINGS_FALLBACK = DATA_DIR / "Rankings_PowerScore.csv"            # global default
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
        DATA_DIR / "Rankings_PowerScore.csv",
        DATA_DIR / "Rankings.csv", 
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

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    # ensure common names used by the UI
    colmap = {
        "Power Score": "PowerScore",
        "Games Played": "GamesPlayed",
        "W-L-T": "WL",
        "Goals For": "GoalsFor",
        "Goals Against": "GoalsAgainst",
        "Offense Score": "Off_norm",
        "Adj Defense Score": "Def_norm",
        "SOS": "SOS_norm",
    }
    for a,b in colmap.items():
        if a in df.columns and b not in df.columns:
            df[b] = df[a]
    
    # Create W-L-T column if it doesn't exist
    if "WL" not in df.columns and "Wins" in df.columns and "Losses" in df.columns and "Ties" in df.columns:
        df["WL"] = df["Wins"].astype(str) + "-" + df["Losses"].astype(str) + "-" + df["Ties"].astype(str)
    
    # Create missing normalized columns if they don't exist
    if "Off_norm" not in df.columns and "Goals For/Game" in df.columns:
        # Normalize goals for per game to 0-1 scale
        max_gf = df["Goals For/Game"].max()
        min_gf = df["Goals For/Game"].min()
        if max_gf > min_gf:
            df["Off_norm"] = (df["Goals For/Game"] - min_gf) / (max_gf - min_gf)
        else:
            df["Off_norm"] = 0.5
    
    if "Def_norm" not in df.columns and "Goals Against/Game" in df.columns:
        # Normalize goals against per game to 0-1 scale (inverted - lower is better)
        max_ga = df["Goals Against/Game"].max()
        min_ga = df["Goals Against/Game"].min()
        if max_ga > min_ga:
            df["Def_norm"] = 1.0 - (df["Goals Against/Game"] - min_ga) / (max_ga - min_ga)
        else:
            df["Def_norm"] = 0.5
    
    if "SOS_norm" not in df.columns and "SOS" in df.columns:
        # Normalize SOS to 0-1 scale
        max_sos = df["SOS"].max()
        min_sos = df["SOS"].min()
        if max_sos > min_sos:
            df["SOS_norm"] = (df["SOS"] - min_sos) / (max_sos - min_sos)
        else:
            df["SOS_norm"] = 0.5
    
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

    # Optional filtering (if global file)
    if state and "State" in df.columns:
        df = df[df["State"] == state]
    if gender and "Gender" in df.columns:
        gnorm = "MALE" if gender and gender.upper() in ("M","MALE","BOYS") else "FEMALE"
        df = df[df["Gender"].str.upper() == gnorm]
    if year and "Year" in df.columns:
        df = df[df["Year"].astype(str) == str(year)]

    if q:
        df = df[df["Team"].str.contains(q, case=False, na=False)]

    # Sorting
    if sort not in df.columns:
        sort = "PowerScore" if "PowerScore" in df.columns else "Power Score"
    ascending = (order == "asc")
    try:
        df = df.sort_values(by=sort, ascending=ascending, na_position="last")
    except Exception:
        pass

    # Build minimal payload
    cols = ["Team","PowerScore","Off_norm","Def_norm","SOS_norm","GamesPlayed","WL"]
    cols = [c for c in cols if c in df.columns]
    # Add Rank
    df = df.reset_index(drop=True)
    df.insert(0, "Rank", df.index + 1)

    return JSONResponse(df[["Rank"] + cols].head(limit).to_dict(orient="records"))

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

    # Optional filtering if global
    if state and "State" in df.columns:
        df = df[df["State"] == state]
    if gender and "Gender" in df.columns:
        gnorm = "MALE" if gender and gender.upper() in ("M","MALE","BOYS") else "FEMALE"
        df = df[df["Gender"].str.upper() == gnorm]
    if year and "Year" in df.columns:
        df = df[df["Year"].astype(str) == str(year)]

    # Filter to the team as 'Team'
    df = df[df["Team"] == urllib.parse.unquote(team)]
    if df.empty:
        return []

    # Minimal columns for UI (with expectation fields if present)
    wanted = [
        "Date","Opponent","GoalsFor","GoalsAgainst",
        "expected_gd","gd_delta","impact_bucket","Opponent_BaseStrength",
    ]
    # Some files may use spaces; patch them
    if "Goals For" in df.columns and "GoalsFor" not in df.columns:
        df["GoalsFor"] = df["Goals For"]
    if "Goals Against" in df.columns and "GoalsAgainst" not in df.columns:
        df["GoalsAgainst"] = df["Goals Against"]

    cols = [c for c in wanted if c in df.columns]
    # Ensure date desc
    if "Date" in df.columns:
        df = df.sort_values("Date", ascending=False)
        # cast to ISO string
        try:
            df["Date"] = pd.to_datetime(df["Date"]).dt.date.astype(str)
        except Exception:
            pass

    return JSONResponse(df[cols].head(limit).to_dict(orient="records"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
