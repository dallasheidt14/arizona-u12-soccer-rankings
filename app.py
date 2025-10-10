# app.py
import os
import time
import json
import urllib.parse
from pathlib import Path
from typing import Optional, List, Dict

import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import prediction module
from analytics.projected_outcomes_v52b import interactive_predict

# ---- Config ----
DATA_DIR = Path(os.getenv("DATA_DIR", "."))  # root of your pipeline outputs
INDEX_JSON = DATA_DIR / "rankings_index.json"            # created in Phase 3
RANKINGS_FALLBACK = DATA_DIR / "Rankings.csv"            # global default
HISTORY_FALLBACK = DATA_DIR / "Team_Game_Histories.csv"  # global default

# Environment configuration
INACTIVE_HIDE_DAYS = int(os.getenv("INACTIVE_HIDE_DAYS", "180"))
RECENT_K = int(os.getenv("RECENT_K", "10"))
RECENT_SHARE = float(os.getenv("RECENT_SHARE", "0.70"))
DEFAULT_INCLUDE_INACTIVE = os.getenv("DEFAULT_INCLUDE_INACTIVE", "false").lower() == "true"
RANKINGS_FILE_PREFERENCE = os.getenv("RANKINGS_FILE_PREFERENCE", "v53,v52b,v52a,v52,v51,v5,v4,v3,legacy").split(",")

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

# Cache rankings for prediction endpoint
def load_rankings():
    """Load Rankings_v52b.csv for predictions."""
    rankings_path = DATA_DIR / "Rankings_v52b.csv"
    if rankings_path.exists():
        return pd.read_csv(rankings_path)
    else:
        # Fallback to other ranking files
        for fallback in ["Rankings_v52a.csv", "Rankings_v52.csv", "Rankings_v51.csv", "Rankings_v5.csv", "Rankings_v4.csv", "Rankings_v3.csv"]:
            fallback_path = DATA_DIR / fallback
            if fallback_path.exists():
                return pd.read_csv(fallback_path)
        raise HTTPException(status_code=404, detail="No ranking files found")

# Cache rankings on startup
try:
    rankings_df = load_rankings()
except Exception as e:
    rankings_df = None
    print(f"Warning: Could not load rankings for predictions: {e}")

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

def find_rankings_path(state: Optional[str], gender: Optional[str], year: Optional[str], division: Optional[str] = None) -> Path:
    # Handle division-specific paths first
    if division:
        age_map = {"az_boys_u11": "U11", "az_boys_u12": "U12"}
        age = age_map.get(division, "U12")
        
        # Division-specific candidates (prefer v53e enhanced)
        division_candidates = [
            DATA_DIR / f"Rankings_AZ_M_{age}_2025_v53e.csv",
            DATA_DIR / f"Rankings_AZ_M_{age}_2025_v53.csv",
            DATA_DIR / f"Rankings_AZ_M_{age}_2025.csv",
            DATA_DIR / f"Rankings_{age}_v53e.csv",
            DATA_DIR / f"Rankings_{age}_v53.csv",
            DATA_DIR / f"Rankings_{age}.csv",
        ]
        
        for p in division_candidates:
            if p.exists():
                return p
        
        # If no division-specific file found, fall through to general logic
    
    sfx = slice_suffix(state, gender, year)
    # Prefer v5.3E enhanced rankings (latest), then v5.3, then v5.2b, v5.2a, v5.2, v5.1, v5, then v4, then v3, then CSV, then Parquet for the slice
    candidates = [
        DATA_DIR / f"Rankings_v53_enhanced{sfx}.csv",
        DATA_DIR / f"Rankings_v53_enhanced.csv",
        DATA_DIR / f"Rankings_v53{sfx}.csv",
        DATA_DIR / f"Rankings_v53.csv",
        DATA_DIR / f"Rankings_v52b{sfx}.csv",
        DATA_DIR / f"Rankings_v52b.csv",
        DATA_DIR / f"Rankings_v52a{sfx}.csv",
        DATA_DIR / f"Rankings_v52a.csv",
        DATA_DIR / f"Rankings_v52{sfx}.csv",
        DATA_DIR / f"Rankings_v52.csv",
        DATA_DIR / f"Rankings_v51{sfx}.csv",
        DATA_DIR / f"Rankings_v51.csv",
        DATA_DIR / f"Rankings_v5{sfx}.csv",
        DATA_DIR / f"Rankings_v5.csv",
        DATA_DIR / f"Rankings_v4{sfx}.csv",
        DATA_DIR / f"Rankings_v4.csv",
        DATA_DIR / f"Rankings_v3{sfx}.csv",
        DATA_DIR / f"Rankings_v3.csv",
        DATA_DIR / f"Rankings{sfx}.csv",
        DATA_DIR / f"Rankings{sfx}.parquet",
    ]
    for p in candidates:
        if p.exists():
            return p
    # Fallback to global - try multiple possible names (v5.3E enhanced first)
    fallback_candidates = [
        DATA_DIR / "Rankings_v53_enhanced.csv",
        DATA_DIR / "Rankings_v53.csv",
        DATA_DIR / "Rankings_v52b.csv",
        DATA_DIR / "Rankings_v52a.csv",
        DATA_DIR / "Rankings_v52.csv",
        DATA_DIR / "Rankings_v51.csv",
        DATA_DIR / "Rankings_v5.csv",
        DATA_DIR / "Rankings_v4.csv",
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
    # For team history details, prefer comprehensive history (shows ALL games from last 18 months)
    # The comprehensive file has all games, but basic data only
    
    # Try comprehensive history first (shows ALL games from last 18 months)
    comprehensive_path = Path("Team_Game_Histories_COMPREHENSIVE.csv")
    if comprehensive_path.exists():
        return comprehensive_path
    
    # Fallback to enriched history files (has calculations but fewer games)
    sfx = slice_suffix(state, gender, year)
    enriched_candidates = [
        DATA_DIR / f"Team_Game_Histories{sfx}.parquet",
        DATA_DIR / f"Team_Game_Histories{sfx}.csv",
        Path("Team_Game_Histories.csv"),  # Global enriched file
    ]
    
    for p in enriched_candidates:
        if p.exists():
            return p
    
    return HISTORY_FALLBACK if HISTORY_FALLBACK.exists() else enriched_candidates[-1]

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
INACTIVE_HIDE_DAYS = 180

def gp_multiplier(gp: int) -> float:
    """Multiplicative penalty based on games played."""
    if gp >= 20: return 1.00
    if gp >= 10: return 0.90
    return 0.75

def _status_from_gp(gp: int) -> str:
    gp = int(gp) if pd.notna(gp) else 0
    if gp >= 6:
        return "Active"
    return "Provisional"

def _ensure_numeric(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def schema_check(df: pd.DataFrame, required=("Team", "PowerScore")):
    """Validate that required columns exist after normalization."""
    missing = [c for c in required if c not in df.columns]
    if missing:
        # Enhanced error with file path and column info for support tickets
        error_detail = {
            "error": "Missing required columns", 
            "missing": missing, 
            "have": list(df.columns)[:20],  # First 20 columns
            "total_columns": len(df.columns),
            "file_path": str(path) if 'path' in locals() else "unknown"
        }
        raise HTTPException(status_code=422, detail=error_detail)

# ---- Endpoints ----

@app.get("/api/slices")
def api_slices():
    return load_index()

@app.get("/api/rankings")
def api_rankings(
    state: Optional[str] = Query(None),
    gender: Optional[str] = Query(None),   # MALE/FEMALE
    year: Optional[str] = Query(None),
    division: Optional[str] = Query(None), # az_boys_u11, az_boys_u12
    q: Optional[str] = Query(None),        # search team name
    sort: Optional[str] = Query("PowerScore"),  # PowerScore|Off_norm|Def_norm|SOS_norm|GamesPlayed
    order: Optional[str] = Query("desc"),  # asc|desc
    limit: int = Query(500, ge=1, le=5000),
    include_inactive: bool = Query(DEFAULT_INCLUDE_INACTIVE),
):
    path = find_rankings_path(state, gender, year, division)
    df = CACHE.get_df(path)
    if df is None:
        raise HTTPException(status_code=404, detail="Rankings file not found")

    df = normalize_columns(df)
    
    # Schema validation after normalization
    schema_check(df, ("Team", "PowerScore"))

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

    # Apply multiplicative GP penalty if not already computed
    if "GamesPlayed" not in df.columns:
        df["GamesPlayed"] = pd.NA

    if "PowerScore" in df.columns and "PowerScore_adj" not in df.columns:
        df["GP_Mult"] = df["GamesPlayed"].fillna(0).astype("Int64").apply(
            lambda x: gp_multiplier(int(x) if pd.notna(x) else 0)
        )
        df["PowerScore_adj"] = (df["PowerScore"] * df["GP_Mult"]).round(3)

    # Status badge
    df["Status"] = df["GamesPlayed"].fillna(0).astype("Int64").apply(
        lambda x: _status_from_gp(int(x) if pd.notna(x) else 0)
    )

    # Inactivity filtering
    hidden_inactive = 0
    if not include_inactive and "LastGame" in df.columns:
        cutoff = pd.Timestamp.now().normalize() - pd.Timedelta(days=INACTIVE_HIDE_DAYS)
        try:
            df["__lg"] = pd.to_datetime(df["LastGame"], errors="coerce")
            mask = df["__lg"] >= cutoff
            hidden_inactive = int((~mask).sum())
            df = df[mask]
        finally:
            if "__lg" in df.columns:
                df.drop(columns="__lg", inplace=True)

    # Separate Active (8+ games) and Provisional (<8 games) teams
    active_teams = df[df["GamesPlayed"] >= 8].copy()
    provisional_teams = df[df["GamesPlayed"] < 8].copy()
    
    # Update Status based on 8-game rule
    if not active_teams.empty:
        active_teams["Status"] = "Active"
    if not provisional_teams.empty:
        provisional_teams["Status"] = "Provisional"
    
    # Sort active teams by PowerScore_adj (for ranking)
    if not active_teams.empty:
        sort_cols = []
        ascending = []
        
        if "PowerScore_adj" in active_teams.columns:
            sort_cols.append("PowerScore_adj"); ascending.append(False)
        elif "PowerScore" in active_teams.columns:
            sort_cols.append("PowerScore"); ascending.append(False)
        
        for key in ["Off_norm","Def_norm","SOS_norm","GamesPlayed"]:
            if key in active_teams.columns:
                sort_cols.append(key)
                ascending.append(False)
        
        if "Team" in active_teams.columns:
            sort_cols.append("Team"); ascending.append(True)
        
        if sort_cols:
            active_teams = active_teams.sort_values(by=sort_cols, ascending=ascending, kind="mergesort").reset_index(drop=True)
            active_teams["Rank"] = active_teams.index + 1
    
    # Sort provisional teams by PowerScore_adj (no rank numbers)
    if not provisional_teams.empty:
        sort_cols = []
        ascending = []
        
        if "PowerScore_adj" in provisional_teams.columns:
            sort_cols.append("PowerScore_adj"); ascending.append(False)
        elif "PowerScore" in provisional_teams.columns:
            sort_cols.append("PowerScore"); ascending.append(False)
        
        for key in ["Off_norm","Def_norm","SOS_norm","GamesPlayed"]:
            if key in provisional_teams.columns:
                sort_cols.append(key)
                ascending.append(False)
        
        if "Team" in provisional_teams.columns:
            sort_cols.append("Team"); ascending.append(True)
        
        if sort_cols:
            provisional_teams = provisional_teams.sort_values(by=sort_cols, ascending=ascending, kind="mergesort").reset_index(drop=True)
            # No rank numbers for provisional teams
    
    # Combine for backward compatibility
    all_teams = pd.concat([active_teams, provisional_teams], ignore_index=True)
    
    # Add SOS_display field (iterative primary, baseline fallback)
    if "SOS_iterative_norm" in all_teams.columns and "SOS_norm" in all_teams.columns:
        all_teams["SOS_display"] = all_teams["SOS_iterative_norm"].combine_first(all_teams["SOS_norm"])
        active_teams["SOS_display"] = active_teams["SOS_iterative_norm"].combine_first(active_teams["SOS_norm"])
        provisional_teams["SOS_display"] = provisional_teams["SOS_iterative_norm"].combine_first(provisional_teams["SOS_norm"])
    elif "SOS_iterative_norm" in all_teams.columns:
        all_teams["SOS_display"] = all_teams["SOS_iterative_norm"]
        active_teams["SOS_display"] = active_teams["SOS_iterative_norm"]
        provisional_teams["SOS_display"] = provisional_teams["SOS_iterative_norm"]
    elif "SOS_norm" in all_teams.columns:
        all_teams["SOS_display"] = all_teams["SOS_norm"]
        active_teams["SOS_display"] = active_teams["SOS_norm"]
        provisional_teams["SOS_display"] = provisional_teams["SOS_norm"]
    else:
        all_teams["SOS_display"] = np.nan
        active_teams["SOS_display"] = np.nan
        provisional_teams["SOS_display"] = np.nan

    # Keep the response schema stable
    preferred_cols = [
        "Rank", "Team",
        "PowerScore_adj", "PowerScore", "GP_Mult",
        "SAO_norm", "SAD_norm", "SOS_norm", "SOS_iterative_norm", "SOS_display",  # Add SOS_display
        "GamesPlayed", "Status", "WL", "LastGame"
    ]
    cols = [c for c in preferred_cols if c in all_teams.columns]
    
    # Prepare data arrays
    active_data = active_teams[cols].head(limit).to_dict(orient="records") if not active_teams.empty else []
    provisional_data = provisional_teams[cols].to_dict(orient="records") if not provisional_teams.empty else []
    all_data = all_teams[cols].to_dict(orient="records")
    
    # Convert numpy types to JSON-serializable types
    def convert_numpy_types(obj):
        if isinstance(obj, dict):
            return {k: convert_numpy_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy_types(item) for item in obj]
        elif hasattr(obj, 'item'):  # numpy scalar
            return obj.item()
        elif hasattr(obj, 'tolist'):  # numpy array
            return obj.tolist()
        elif pd.isna(obj):  # Handle NaN values
            return None
        elif isinstance(obj, (pd.Timestamp, np.datetime64)):  # Handle timestamps
            return str(obj)
        else:
            return obj
    
    active_data = convert_numpy_types(active_data)
    provisional_data = convert_numpy_types(provisional_data)
    all_data = convert_numpy_types(all_data)
    
    # Enhanced meta block with Active/Provisional counts
    meta = {
        "hidden_inactive": hidden_inactive,
        "total_teams": len(all_teams),
        "active_teams": len(active_teams),
        "provisional_teams": len(provisional_teams),
        "slice": {
            "state": state,
            "gender": gender, 
            "year": year
        },
        "records": len(active_data),
        "total_available": len(all_teams),
        "method": "Up to 30 most-recent matches (last 12 months). Games 26–30 count with reduced influence. Active teams: 8+ games. Provisional teams: <8 games."
    }
    
    # Add metadata about SOS sources
    if "SOS_iterative_norm" in all_teams.columns and "SOS_norm" in all_teams.columns:
        meta["sos_sources"] = {
            "iterative_count": int(all_teams["SOS_iterative_norm"].notna().sum()),
            "baseline_count": int((all_teams["SOS_iterative_norm"].isna() & all_teams["SOS_norm"].notna()).sum()),
            "missing_count": int((all_teams["SOS_iterative_norm"].isna() & all_teams["SOS_norm"].isna()).sum())
        }
    
    # Convert meta to JSON-serializable types
    meta = convert_numpy_types(meta)
    
    return JSONResponse({
        "meta": meta, 
        "data": all_data,  # Backward compatibility
        "active": active_data,
        "provisional": provisional_data
    })

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
    
    # Add performance indicator for score highlighting (UI uses 1.0 threshold to match V5.3)
    if "gd_delta" in df.columns:
        df["performance"] = df["gd_delta"].apply(lambda x: 
            "overperformed" if x >= 1.0 else 
            "underperformed" if x <= -1.0 else 
            "neutral"
        )
        cols.append("performance")

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

@app.get("/api/predict")
def predict_outcome(
    team_a: str = Query(..., description="Team A name"),
    team_b: str = Query(..., description="Team B name"),
    mode: str = Query("simple", description="Prediction mode: 'simple' or 'advanced'")
):
    """
    Predict the outcome probabilities for a match between two teams.
    Uses PowerScore-based logistic model from V5.2b.
    """
    if rankings_df is None:
        return JSONResponse({
            "status": "error",
            "error": "Rankings data not available"
        }, status_code=503)
    
    try:
        result = interactive_predict(team_a, team_b, rankings_df, mode=mode)
        
        # Check if there was an error in the prediction
        if "error" in result:
            return JSONResponse({
                "status": "error",
                "error": result["error"]
            }, status_code=400)
        
        return JSONResponse({
            "status": "success",
            "teams": {"team_a": team_a, "team_b": team_b},
            "prediction_mode": mode,
            "probabilities": result
        })
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
