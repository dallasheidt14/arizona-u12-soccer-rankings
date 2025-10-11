from __future__ import annotations
from dataclasses import dataclass

_CANON_PREFIX = ("AZ", "Boys")  # keep consistent with U12

def parse_age_from_division(div: str) -> str:
    """
    Accepts e.g. 'az_boys_u11' OR 'AZ_Boys_U11' OR 'AZ-BOYS-U11'
    Returns: 'U11'
    """
    parts = div.replace("-", "_").split("_")
    for p in parts:
        u = p.upper()
        if u.startswith("U") and u[1:].isdigit():
            return u  # U11, U12, etc.
    raise ValueError(f"Could not parse age from division: {div}")

def to_canonical_division(div: str) -> str:
    """
    'az_boys_u11' -> 'AZ_Boys_U11'
    """
    age = parse_age_from_division(div)
    return f"{_CANON_PREFIX[0]}_{_CANON_PREFIX[1]}_{age}"
