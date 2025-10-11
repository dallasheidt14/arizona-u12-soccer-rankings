"""
Team name canonicalization and robust normalization utilities.

This module provides functions to normalize team names for consistent joins
and robust statistical normalization that handles edge cases.
"""
import re
import numpy as np
import pandas as pd


def canonicalize_team_name(s: str) -> str:
    """
    Normalize team names to canonical form for consistent joins.
    Strips venue markers, normalizes variants, standardizes spacing.
    
    Args:
        s: Team name string to canonicalize
        
    Returns:
        Canonicalized team name string
    """
    if not isinstance(s, str):
        return s
    s = s.lower()
    s = re.sub(r"\s+\((h|a)\)$", "", s)            # strip (H)/(A)
    s = re.sub(r"\bsc\b|\bfc\b|\bacademy\b", "", s)
    s = s.replace("boys", "").replace("b14", "2014")
    s = re.sub(r"\s+", " ", s).strip()
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

