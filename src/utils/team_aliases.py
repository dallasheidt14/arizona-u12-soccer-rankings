"""
Team alias mapping system for resolving canonical team names.

This module provides functions to load, save, and resolve team name aliases
to ensure consistent team matching across different data sources.
"""
import json
from pathlib import Path
from typing import Dict, Optional


ALIASES_FILE = Path("data/aliases/team_aliases.json")


def load_aliases() -> Dict[str, str]:
    """
    Load team aliases from JSON file.
    
    Returns:
        Dictionary mapping canonical names to preferred display names
    """
    if not ALIASES_FILE.exists():
        return {}
    with open(ALIASES_FILE, 'r') as f:
        return json.load(f)


def save_aliases(aliases: Dict[str, str]):
    """
    Save team aliases to JSON file.
    
    Args:
        aliases: Dictionary mapping canonical names to preferred display names
    """
    ALIASES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ALIASES_FILE, 'w') as f:
        json.dump(aliases, f, indent=2)


def resolve_team_name(name: str, aliases: Optional[Dict[str, str]] = None) -> str:
    """
    Resolve team name using canonicalization and alias mapping.
    
    Args:
        name: Original team name
        aliases: Optional alias dictionary (loads from file if not provided)
        
    Returns:
        Resolved team name (canonical or aliased)
    """
    from .team_normalizer import canonicalize_team_name
    
    canonical = canonicalize_team_name(name)
    
    if aliases is None:
        aliases = load_aliases()
    
    return aliases.get(canonical, canonical)

