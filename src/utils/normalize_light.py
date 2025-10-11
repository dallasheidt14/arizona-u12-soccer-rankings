"""
Light normalization for team name matching.

Conservative normalizer that only handles lowercase, diacritics, and punctuation/whitespace.
Does NOT remove meaningful tokens like "FC", "Boys", "Blue", colors, etc.
"""

import re
import unicodedata

_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[^a-z0-9 ]")


def normalize_light(s: str) -> str:
    """
    Light normalization for team name matching.
    
    Only handles:
    - Unicode normalization (NFKD)
    - ASCII conversion (removes diacritics)
    - Lowercase conversion
    - Punctuation removal
    - Whitespace normalization
    
    Does NOT remove meaningful tokens like "FC", "Boys", "Blue", colors, etc.
    """
    if not s:
        return ""
    
    # Unicode normalization and ASCII conversion
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    
    # Convert to lowercase
    s = s.lower()
    
    # Remove punctuation
    s = _PUNCT.sub(" ", s)
    
    # Normalize whitespace
    s = _WS.sub(" ", s).strip()
    
    return s
