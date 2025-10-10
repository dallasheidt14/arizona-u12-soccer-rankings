"""
Enhanced data loading for ranking system with Gold layer fallback
"""

import pandas as pd
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def load_games_data_with_fallback(games_file: str = None, log_file=None) -> pd.DataFrame:
    """
    Load games data with automatic fallback to Gold layer or legacy CSV.
    
    Priority:
    1. Explicit games_file parameter
    2. Gold layer (data_ingest/gold/All_Games.parquet)
    3. Legacy Matched_Games.csv
    """
    
    # Try explicit file first
    if games_file and Path(games_file).exists():
        logger.info(f"Loading games from explicit file: {games_file}")
        return pd.read_csv(games_file)
    
    # Try Gold layer (Parquet preferred, CSV fallback)
    gold_dir = Path("data_ingest/gold")
    if gold_dir.exists():
        parquet_path = gold_dir / "All_Games.parquet"
        csv_path = gold_dir / "All_Games.csv"
        
        if parquet_path.exists():
            logger.info(f"Loading games from Gold Parquet: {parquet_path}")
            df = pd.read_parquet(parquet_path)
            
            # Convert Gold schema to legacy schema if needed
            df = convert_gold_to_legacy_schema(df)
            return df
            
        elif csv_path.exists():
            logger.info(f"Loading games from Gold CSV: {csv_path}")
            df = pd.read_csv(csv_path)
            df = convert_gold_to_legacy_schema(df)
            return df
    
    # Fallback to legacy CSV
    legacy_path = Path("Matched_Games.csv")
    if legacy_path.exists():
        logger.info(f"Loading games from legacy CSV: {legacy_path}")
        return pd.read_csv(legacy_path)
    
    raise FileNotFoundError("No games data found in Gold layer or legacy files")

def convert_gold_to_legacy_schema(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert Gold layer schema to legacy Matched_Games.csv schema.
    
    Gold schema: match_id, date_utc, season, competition, venue,
                home_team_raw, away_team_raw, home_team_match, away_team_match,
                home_score, away_score, status, source_url, fetched_at, record_checksum
    
    Legacy schema: Date, Team A, Team B, Score A, Score B, Team A Match, Team B Match, etc.
    """
    
    if df.empty:
        return df
    
    # Create legacy schema DataFrame
    legacy_df = pd.DataFrame()
    
    # Map Gold columns to legacy columns
    legacy_df["Date"] = pd.to_datetime(df["date_utc"], errors="coerce")
    legacy_df["Team A"] = df["home_team_raw"]
    legacy_df["Team B"] = df["away_team_raw"]
    legacy_df["Score A"] = df["home_score"]
    legacy_df["Score B"] = df["away_score"]
    
    # Use matched names if available, otherwise raw names
    legacy_df["Team A Match"] = df["home_team_match"].fillna(df["home_team_raw"])
    legacy_df["Team B Match"] = df["away_team_match"].fillna(df["away_team_raw"])
    
    # Add match type based on resolution method
    legacy_df["Team A Match Type"] = df.get("home_team_match_method", "UNMATCHED")
    legacy_df["Team B Match Type"] = df.get("away_team_match_method", "UNMATCHED")
    
    # Add metadata columns
    legacy_df["Competition"] = df["competition"]
    legacy_df["Venue"] = df["venue"]
    legacy_df["Status"] = df["status"]
    legacy_df["Source"] = df["source_url"]
    
    # Filter to completed games only (for ranking purposes)
    legacy_df = legacy_df[
        (legacy_df["Status"] == "FINAL") | 
        (legacy_df["Status"] == "COMPLETED") |
        (legacy_df["Status"].isna())
    ]
    
    # Remove games with missing scores
    legacy_df = legacy_df.dropna(subset=["Score A", "Score B"])
    
    logger.info(f"Converted {len(df)} Gold records to {len(legacy_df)} legacy format records")
    
    return legacy_df

def validate_gold_schema(df: pd.DataFrame) -> bool:
    """Validate that Gold layer data has required columns."""
    required_cols = [
        "date_utc", "home_team_raw", "away_team_raw", 
        "home_score", "away_score", "status"
    ]
    
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        logger.error(f"Gold layer missing required columns: {missing_cols}")
        return False
    
    return True

def get_data_source_info() -> dict:
    """Get information about current data source."""
    gold_dir = Path("data_ingest/gold")
    legacy_path = Path("Matched_Games.csv")
    
    info = {
        "gold_parquet_exists": (gold_dir / "All_Games.parquet").exists(),
        "gold_csv_exists": (gold_dir / "All_Games.csv").exists(),
        "legacy_csv_exists": legacy_path.exists(),
        "data_source": None
    }
    
    if info["gold_parquet_exists"]:
        info["data_source"] = "Gold Parquet"
    elif info["gold_csv_exists"]:
        info["data_source"] = "Gold CSV"
    elif info["legacy_csv_exists"]:
        info["data_source"] = "Legacy CSV"
    else:
        info["data_source"] = "None"
    
    return info
