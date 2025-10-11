"""
Name mapping utilities for matching raw team names to master list entries.

This module provides functions to build and validate name mappings between
raw game data team names and master list team IDs.
"""
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.utils.team_normalizer import canonicalize_team_name


def normalize_u11_name(name: str) -> str:
    """
    Normalize U11 team name for matching.
    
    Strips common prefixes/suffixes and normalizes spacing while preserving colors.
    """
    if not isinstance(name, str):
        return name
    
    # Convert to lowercase and strip
    s = name.lower().strip()
    
    # Strip common prefixes
    prefixes = ["fc ", "sc ", "soccer club ", "football club "]
    for prefix in prefixes:
        if s.startswith(prefix):
            s = s[len(prefix):]
    
    # Strip "boys" and "girls" from anywhere in the name
    s = s.replace(" boys", "").replace(" girls", "")
    
    # Strip "fc" and "sc" from anywhere in the name
    s = s.replace(" fc", "").replace(" sc", "")
    
    # Strip "academy" from anywhere in the name
    s = s.replace(" academy", "")
    
    # Normalize spacing
    s = " ".join(s.split())
    
    return s


def build_name_map(master_df: pd.DataFrame, observed_names: pd.Series, division_key: str) -> pd.DataFrame:
    """
    Build name mapping from master list to observed team names.
    
    Args:
        master_df: Master list DataFrame with 'team_id' and 'display_name' columns
        observed_names: Series of team names observed in game data
        division_key: Division key for logging purposes
        
    Returns:
        DataFrame with columns: raw_name, team_id, display_name
        
    Raises:
        RuntimeError: If any observed teams cannot be matched to master list
    """
    # Prepare master list with canonical names
    m = master_df.copy()
    # For U11, use U11-specific normalization
    if "u11" in division_key.lower():
        m["norm"] = m["display_name"].apply(normalize_u11_name)
    else:
        m["norm"] = m["display_name"].map(canonicalize_team_name)
    
    # Prepare observed names with canonical names
    obs = pd.DataFrame({"raw_name": observed_names.dropna().unique()})
    # For U11, use U11-specific normalization
    if "u11" in division_key.lower():
        obs["norm"] = obs["raw_name"].apply(normalize_u11_name)
    else:
        obs["norm"] = obs["raw_name"].map(canonicalize_team_name)
    
    # Merge on canonical names
    mapped = obs.merge(m[["team_id", "display_name", "norm"]], on="norm", how="left")
    
    # Check for unmatched teams
    misses = mapped[mapped["team_id"].isna()]
    if not misses.empty:
        # Create logs directory if it doesn't exist
        logs_dir = Path("data/logs")
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Save unmatched teams for debugging
        misses_file = logs_dir / f"UNMATCHED_{division_key.upper()}.csv"
        misses[["raw_name", "norm"]].to_csv(misses_file, index=False)
        
        raise RuntimeError(
            f"Unmatched teams in {division_key}: {len(misses)} "
            f"(see {misses_file})"
        )
    
    # Return clean mapping
    out = mapped[["raw_name", "team_id", "display_name"]].drop_duplicates()
    return out


def load_name_map(division_key: str) -> pd.DataFrame:
    """
    Load existing name map for a division.
    
    Args:
        division_key: Division key (e.g., "az_boys_u11_2025")
        
    Returns:
        DataFrame with name mapping
        
    Raises:
        FileNotFoundError: If name map doesn't exist
    """
    map_path = Path(f"data/mappings/{division_key}/name_map.csv")
    if not map_path.exists():
        raise FileNotFoundError(f"Name map not found: {map_path}")
    
    return pd.read_csv(map_path)


def save_name_map(name_map_df: pd.DataFrame, division_key: str) -> None:
    """
    Save name map to file.
    
    Args:
        name_map_df: Name mapping DataFrame
        division_key: Division key for path construction
    """
    map_dir = Path(f"data/mappings/{division_key}")
    map_dir.mkdir(parents=True, exist_ok=True)
    
    map_path = map_dir / "name_map.csv"
    name_map_df.to_csv(map_path, index=False)


def validate_name_map(name_map_df: pd.DataFrame) -> Dict[str, int]:
    """
    Validate name map for completeness and consistency.
    
    Args:
        name_map_df: Name mapping DataFrame to validate
        
    Returns:
        Dictionary with validation statistics
    """
    stats = {
        "total_mappings": len(name_map_df),
        "unique_raw_names": name_map_df["raw_name"].nunique(),
        "unique_team_ids": name_map_df["team_id"].nunique(),
        "unique_display_names": name_map_df["display_name"].nunique(),
    }
    
    # Check for duplicates
    raw_dupes = name_map_df["raw_name"].duplicated().sum()
    id_dupes = name_map_df["team_id"].duplicated().sum()
    
    stats["duplicate_raw_names"] = raw_dupes
    stats["duplicate_team_ids"] = id_dupes
    
    return stats
