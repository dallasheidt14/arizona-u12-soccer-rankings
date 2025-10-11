"""
Division Registry Helper Module

Provides centralized access to division configurations stored in data/divisions.json.
Enables dynamic division management without code changes.
"""
import json
from pathlib import Path
from typing import Dict, Any, List

# Path to the division registry JSON file
DIVISION_REGISTRY_PATH = Path(__file__).resolve().parents[2] / "data" / "divisions.json"

def load_divisions() -> Dict[str, Any]:
    """
    Load all registered divisions from the JSON file.
    
    Returns:
        Dict containing all division configurations
        
    Raises:
        FileNotFoundError: If registry file doesn't exist
        json.JSONDecodeError: If registry file is malformed
    """
    if not DIVISION_REGISTRY_PATH.exists():
        raise FileNotFoundError(f"Division registry not found: {DIVISION_REGISTRY_PATH}")
    
    with open(DIVISION_REGISTRY_PATH, "r", encoding="utf-8") as f:
        divisions = json.load(f)
    
    # Validate schema
    for div_key, div_config in divisions.items():
        required_fields = ["age", "gender", "state", "url", "active"]
        missing_fields = [field for field in required_fields if field not in div_config]
        if missing_fields:
            raise ValueError(f"Division '{div_key}' missing required fields: {missing_fields}")
    
    return divisions

def get_division(div_key: str) -> Dict[str, Any]:
    """
    Get a single division's configuration by key.
    
    Args:
        div_key: Division key (e.g., 'az_boys_u11')
        
    Returns:
        Division configuration dictionary
        
    Raises:
        KeyError: If division not found in registry
    """
    divisions = load_divisions()
    if div_key not in divisions:
        raise KeyError(f"Division '{div_key}' not found in registry.")
    return divisions[div_key]

def list_divisions(active_only: bool = False) -> List[str]:
    """
    List all available division keys.
    
    Args:
        active_only: If True, only return active divisions
        
    Returns:
        List of division keys
    """
    divisions = load_divisions()
    
    if active_only:
        return [key for key, config in divisions.items() if config.get("active", False)]
    else:
        return list(divisions.keys())

def list_active_divisions() -> List[str]:
    """
    List only active divisions.
    
    Returns:
        List of active division keys
    """
    return list_divisions(active_only=True)

def get_gotsport_url(div_key: str) -> str:
    """
    Return the GotSport URL for a given division.
    
    Args:
        div_key: Division key (e.g., 'az_boys_u11')
        
    Returns:
        GotSport URL string
    """
    return get_division(div_key)["url"]

def get_master_list_path(div_key: str) -> Path:
    """
    Auto-generate master list path from division key.
    
    Args:
        div_key: Division key (e.g., 'az_boys_u11')
        
    Returns:
        Path to master team list file
    """
    div = get_division(div_key)
    age = div["age"]
    gender_label = "MALE" if div["gender"] == "m" else "FEMALE"
    return Path(f"data/bronze/AZ {gender_label} u{age} MASTER TEAM LIST.csv")

def get_canonical_division_name(div_key: str) -> str:
    """
    Convert division key to canonical display format.
    
    Args:
        div_key: Division key (e.g., 'az_boys_u11')
        
    Returns:
        Canonical name (e.g., 'AZ_Boys_U11')
    """
    div = get_division(div_key)
    state = div["state"]
    gender_label = "Boys" if div["gender"] == "m" else "Girls"
    age = div["age"]
    return f"{state}_{gender_label}_U{age}"

def get_rankings_output_path(div_key: str) -> Path:
    """
    Auto-generate rankings output path from division key.
    
    Args:
        div_key: Division key (e.g., 'az_boys_u11')
        
    Returns:
        Path to rankings output file
    """
    div = get_division(div_key)
    state = div["state"]
    gender_code = "M" if div["gender"] == "m" else "F"
    age = div["age"]
    return Path(f"data/outputs/Rankings_{state}_{gender_code}_U{age}_2025_v53e.csv")

def is_division_active(div_key: str) -> bool:
    """
    Check if a division is active.
    
    Args:
        div_key: Division key (e.g., 'az_boys_u11')
        
    Returns:
        True if division is active, False otherwise
    """
    return get_division(div_key).get("active", False)

def get_division_metadata(div_key: str) -> Dict[str, Any]:
    """
    Get all metadata for a division.
    
    Args:
        div_key: Division key (e.g., 'az_boys_u11')
        
    Returns:
        Dictionary with age, gender, state, url, active status
    """
    return get_division(div_key).copy()

# Convenience functions for common operations
def get_all_active_metadata() -> Dict[str, Dict[str, Any]]:
    """
    Get metadata for all active divisions.
    
    Returns:
        Dictionary mapping division keys to their metadata
    """
    active_keys = list_active_divisions()
    return {key: get_division_metadata(key) for key in active_keys}

def validate_division_key(div_key: str) -> bool:
    """
    Validate that a division key exists in the registry.
    
    Args:
        div_key: Division key to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        get_division(div_key)
        return True
    except (KeyError, FileNotFoundError):
        return False
