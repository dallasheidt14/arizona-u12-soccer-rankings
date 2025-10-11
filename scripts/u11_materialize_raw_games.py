#!/usr/bin/env python3
"""
Materialize canonical raw games file for U11 pipeline.

Converts data/gold/Matched_Games_AZ_BOYS_U11.csv to canonical format at
data/raw/az_boys_u11_2025/games_raw.csv with standardized column names.
"""

from pathlib import Path
import pandas as pd

DIV = "az_boys_u11_2025"
SRC = Path("data/gold/Matched_Games_AZ_BOYS_U11.csv")   # full coverage
DST = Path(f"data/raw/{DIV}/games_raw.csv")


def run():
    """Convert source games file to canonical raw format."""
    
    # Load source data
    df = pd.read_csv(SRC)
    print(f"Loaded {len(df)} games from {SRC}")
    
    # Standardize column names
    cols = {c.lower().strip(): c for c in df.columns}
    rename_map = {}
    
    for c in df.columns:
        lc = c.lower().strip()
        if lc in ("team a", "team_a", "home", "home team", "home_team"):
            rename_map[c] = "team_name_a"
        elif lc in ("team b", "team_b", "away", "away team", "away_team"):
            rename_map[c] = "team_name_b"
        elif lc in ("score a", "score_a", "goals a", "goals_a", "home score", "home_score"):
            rename_map[c] = "score_a"
        elif lc in ("score b", "score_b", "goals b", "goals_b", "away score", "away_score"):
            rename_map[c] = "score_b"
        elif lc in ("date", "game date", "match date"):
            rename_map[c] = "date"
        elif lc in ("competition", "league", "event"):
            rename_map[c] = "competition"
        elif lc in ("team a url", "team_a_url", "home_url"):
            rename_map[c] = "team_url_a"
        elif lc in ("team b url", "team_b_url", "away_url"):
            rename_map[c] = "team_url_b"
    
    # Apply column renaming
    df = df.rename(columns=rename_map)
    
    # Validate required columns
    required = {"team_name_a", "team_name_b", "score_a", "score_b", "date"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in {SRC}: {missing}")
    
    # Create output directory
    DST.parent.mkdir(parents=True, exist_ok=True)
    
    # Save canonical raw file
    df.to_csv(DST, index=False)
    print(f"Wrote canonical raw: {DST} ({len(df)} rows)")
    
    # Show sample data
    print(f"\nSample columns: {list(df.columns)}")
    print(f"Sample games:")
    for _, row in df.head(3).iterrows():
        print(f"  {row['team_name_a']} vs {row['team_name_b']} ({row['score_a']}-{row['score_b']}) on {row['date']}")


if __name__ == "__main__":
    run()
