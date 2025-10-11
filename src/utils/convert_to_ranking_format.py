"""
Convert to Ranking Format Utility
Normalizes data format for ranking algorithm input with flexible column mapping
"""

import pandas as pd
from pathlib import Path
from dateutil import parser
import sys

def validate_division_schema(df, division):
    """Validate that DataFrame has required columns for ranking algorithm."""
    required = ['Team A', 'Team B', 'Score A', 'Score B', 'Date']
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Schema validation failed for {division}: missing {missing}")
    
    # Check data types
    if not pd.api.types.is_numeric_dtype(df['Score A']):
        raise ValueError(f"Score A must be numeric, got {df['Score A'].dtype}")
    if not pd.api.types.is_numeric_dtype(df['Score B']):
        raise ValueError(f"Score B must be numeric, got {df['Score B'].dtype}")
    
    return True

def convert_to_ranking_format(input_path, output_path):
    """Convert any division data to standard ranking format with flexible column mapping"""
    # Support both CSV and Parquet
    if input_path.endswith(".parquet"):
        df = pd.read_parquet(input_path)
    else:
        df = pd.read_csv(input_path)
    
    print(f"Input file: {input_path}")
    print(f"Input shape: {df.shape}")
    print(f"Input columns: {df.columns.tolist()}")
    
    # Flexible column mapping
    aliases = {
        "Team A": ["Home", "Home Team", "TeamA", "TeamName", "Team_Canonical", "TeamCanonical", "Team"],
        "Team B": ["Away", "Away Team", "TeamB", "OpponentName", "Opponent_Canonical", "Opponent"],
        "Score A": ["Home Score", "ScoreA", "GF_A", "TeamScore"],
        "Score B": ["Away Score", "ScoreB", "GA_A", "OpponentScore"],
        "Date": ["Date/Time", "Match Date", "Game Date"],
        "Competition": ["Event", "League", "Tournament"],
    }
    
    # Apply column mapping
    for dst, srcs in aliases.items():
        if dst not in df.columns:
            for s in srcs:
                if s in df.columns:
                    df[dst] = df[s]
                    print(f"Mapped {s} -> {dst}")
                    break
    
    # Validate schema
    required_cols = ['Team A', 'Team B', 'Score A', 'Score B', 'Date']
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        print(f"Missing required columns: {missing_cols}")
        print("Available columns:", df.columns.tolist())
        return False
    
    # Ensure correct types
    df['Team A'] = df['Team A'].astype(str).str.strip()
    df['Team B'] = df['Team B'].astype(str).str.strip()
    
    # Handle numeric scores
    df['Score A'] = pd.to_numeric(df['Score A'], errors='coerce').fillna(0)
    df['Score B'] = pd.to_numeric(df['Score B'], errors='coerce').fillna(0)
    
    # ISO normalize Date
    try:
        df["Date"] = df["Date"].apply(lambda x: parser.parse(str(x)).date().isoformat())
    except Exception as e:
        print(f"Warning: Could not parse dates: {e}")
        # Keep original dates if parsing fails
    
    # Reset index if necessary
    if df.index.name or "Unnamed: 0" in df.columns:
        df.reset_index(drop=True, inplace=True)
        print("Reset DataFrame index")
    
    # Drop duplicate rows
    initial_count = len(df)
    df.drop_duplicates(subset=['Team A', 'Team B', 'Date'], inplace=True)
    final_count = len(df)
    
    if initial_count != final_count:
        print(f"Removed {initial_count - final_count} duplicate rows")
    
    # Select columns for ranking (include Competition if available)
    output_cols = required_cols
    if 'Competition' in df.columns:
        output_cols = required_cols + ['Competition']
    
    df_clean = df[output_cols].copy()
    
    # Save cleaned file
    df_clean.to_csv(output_path, index=False)
    print(f"Converted {len(df_clean)} rows to {output_path}")
    
    # Show sample
    print("\nSample cleaned data:")
    print(df_clean.head(3))
    
    return True

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python convert_to_ranking_format.py <input_path> <output_path>")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    convert_to_ranking_format(input_path, output_path)
