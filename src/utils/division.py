from __future__ import annotations
from dataclasses import dataclass

_CANON_PREFIX = ("AZ", "Boys")  # keep consistent with U12

def parse_age_from_division(div: str) -> str:
    """
    Parse age from division string with registry integration.
    
    First tries to use the division registry for validation.
    Falls back to string parsing for backward compatibility.
    
    Args:
        div: Division string (e.g., 'az_boys_u11', 'AZ_Boys_U12')
        
    Returns:
        Age string (e.g., 'U11', 'U12')
        
    Raises:
        ValueError: If age cannot be parsed from division string
    """
    try:
        # Try registry first for validation
        from src.utils.division_registry import get_division
        div_config = get_division(div)
        return f"U{div_config['age']}"
    except (ImportError, KeyError, FileNotFoundError):
        # Fallback to string parsing for backward compatibility
        parts = div.replace("-", "_").split("_")
        for p in parts:
            u = p.upper()
            if u.startswith("U") and u[1:].isdigit():
                return u  # U11, U12, etc.
        raise ValueError(f"Could not parse age from division: {div}")

def to_canonical_division(div: str) -> str:
    """
    Convert division string to canonical format with registry integration.
    
    Args:
        div: Division string (e.g., 'az_boys_u11')
        
    Returns:
        Canonical division string (e.g., 'AZ_Boys_U11')
    """
    try:
        # Try registry first for enhanced formatting
        from src.utils.division_registry import get_canonical_division_name
        return get_canonical_division_name(div)
    except (ImportError, KeyError, FileNotFoundError):
        # Fallback to string parsing
        age = parse_age_from_division(div)
        return f"{_CANON_PREFIX[0]}_{_CANON_PREFIX[1]}_{age}"
