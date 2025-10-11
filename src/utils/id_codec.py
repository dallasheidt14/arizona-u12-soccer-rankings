"""
Team ID generation utilities for stable, division-scoped team identifiers.

This module provides functions to generate consistent team IDs that are stable
across data processing runs and unique within each division.
"""
import hashlib
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.utils.team_normalizer import canonicalize_team_name


def make_team_id(display_name: str, division_key: str) -> str:
    """
    Generate stable team ID from display name + division key.
    
    Args:
        display_name: Original team name (e.g., "Arizona Soccer Club 2015 Boys Red")
        division_key: Division identifier (e.g., "az_boys_u11_2025")
        
    Returns:
        12-character hexadecimal ID that is stable and unique within division
        
    Example:
        >>> make_team_id("Arizona Soccer Club 2015 Boys Red", "az_boys_u11_2025")
        'a1b2c3d4e5f6'
    """
    # For U11, use simple normalization to preserve colors
    if "u11" in division_key.lower():
        canonical_name = display_name.lower().strip()
    else:
        canonical_name = canonicalize_team_name(display_name)
    
    base = f"{division_key}:{canonical_name}"
    return hashlib.sha1(base.encode()).hexdigest()[:12]


def validate_team_id(team_id: str) -> bool:
    """
    Validate that a team ID has the correct format.
    
    Args:
        team_id: Team ID to validate
        
    Returns:
        True if valid format, False otherwise
    """
    if not isinstance(team_id, str):
        return False
    if len(team_id) != 12:
        return False
    try:
        int(team_id, 16)  # Check if it's valid hex
        return True
    except ValueError:
        return False
