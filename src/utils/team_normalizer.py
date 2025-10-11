"""
Team name canonicalization and robust normalization utilities.

This module provides functions to normalize team names for consistent joins
and robust statistical normalization that handles edge cases.
"""
import re
import numpy as np
import pandas as pd


# Teams where color is part of identity (from U12 analysis)
KNOWN_COLOR_TEAMS = {
    "southeast 2014 boys black",
    "sffa 2014 boys white", 
    "sffa 2014 boys blue",
    "doral sc white 2014",
    "miami skies fc 2014 black",
    "2014 cyclones boys black"
}

def canonicalize_team_name(s: str, preserve_known_colors: bool = True) -> str:
    """
    Normalize team names to canonical form for consistent joins.
    Strips venue markers, normalizes variants, standardizes spacing.
    Preserves colors for known teams where color is part of identity.
    
    Args:
        s: Team name string to canonicalize
        preserve_known_colors: Whether to preserve colors for known teams
        
    Returns:
        Canonicalized team name string
    """
    if not isinstance(s, str):
        return s
    
    original = s.lower().strip()
    s = re.sub(r"\s+\((h|a)\)$", "", original)            # strip (H)/(A)
    s = re.sub(r"\bsc\b|\bfc\b|\bacademy\b", "", s)
    s = s.replace("boys", "").replace("girls", "")
    s = s.replace("b14", "2014").replace("b15", "2015")
    s = re.sub(r"\s+", " ", s).strip()
    
    # Check if this is a known color team
    if preserve_known_colors and original in KNOWN_COLOR_TEAMS:
        return original
    
    # Strip trailing color suffixes
    s = re.sub(r"\s+(blue|red|white|black|gold|maroon|green|navy|silver|grey|gray)$", "", s).strip()
    
    return s


def robust_minmax(x: pd.Series, lo=0.05, hi=0.95) -> pd.Series:
    """
    Min-max normalize using percentiles to handle outliers and degenerate cases.
    Returns 0.5 for flat distributions instead of NaN or zeros.
    
    Args:
        x: pandas Series to normalize
        lo: Lower percentile for clipping (default 0.05)
        hi: Upper percentile for clipping (default 0.95)
        
    Returns:
        Normalized pandas Series
    """
    x = x.astype(float)
    if x.notna().sum() == 0:
        return pd.Series(np.nan, index=x.index)
    lo_v, hi_v = x.quantile(lo), x.quantile(hi)
    if np.isclose(hi_v, lo_v):
        # Flat series: return 0.5 for all non-NaNs
        return pd.Series(0.5, index=x.index).where(x.notna(), np.nan)
    y = (x.clip(lo_v, hi_v) - lo_v) / (hi_v - lo_v)
    return y

