from __future__ import annotations
from pathlib import Path
import pandas as pd
from typing import Optional, List

DEFAULT_GOLD_NAMES = [
    "data/silver/Matched_Games_{AGE}.parquet",
    "data/silver/Matched_Games_{AGE}.csv",
    "data/gold/Matched_Games_{AGE}.parquet",
    "data/gold/Matched_Games_{AGE}.csv",
    "data/gold/Matched_Games.parquet",
    "data/gold/Matched_Games.csv",
]

def _first_existing(paths: List[str]) -> Optional[Path]:
    for p in paths:
        if Path(p).exists():
            return Path(p)
    return None

def resolve_input_path(age: str, explicit: Optional[str] = None) -> Path:
    """
    If explicit is provided, use it. Otherwise search known gold locations.
    """
    if explicit:
        p = Path(explicit)
        if not p.exists():
            raise FileNotFoundError(f"--input provided but not found: {explicit}")
        return p
    candidates = [p.format(AGE=age) for p in DEFAULT_GOLD_NAMES]
    found = _first_existing(candidates)
    if not found:
        raise FileNotFoundError(f"No input file found. Tried: {candidates}")
    return found

def load_games_frame(path: Path) -> pd.DataFrame:
    """
    Read CSV or Parquet into a DataFrame, with light schema normalization.
    """
    if path.suffix.lower() == ".parquet":
        df = pd.read_parquet(path)
    else:
        df = pd.read_csv(path)
    # light normalization: strip cols, standardize names if present
    df.columns = [c.strip() for c in df.columns]
    # optional: alias common variants → target schema
    colmap = {
        "Home": "Team A", "Away": "Team B",
        "Home Team": "Team A", "Away Team": "Team B",
        "ScoreA": "Score A", "ScoreB": "Score B",
        "Date/Time": "Date",
    }
    for src, dst in colmap.items():
        if src in df.columns and dst not in df.columns:
            df[dst] = df[src]
    required = ["Team A", "Team B", "Score A", "Score B", "Date"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Input schema missing {missing}. Columns: {list(df.columns)}")
    return df
