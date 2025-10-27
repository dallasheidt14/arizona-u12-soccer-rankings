"""
Team Name Normalization Module

Aggressive pre-cleaning function to normalize team naming conventions before matching.
Handles common variations in club names, spacing, punctuation, and formatting.
"""

import re
from typing import Dict, List
import yaml
import os

# Common normalization mappings
COMMON_NORMALIZATIONS = {
    # Club suffixes
    "soccer club": "sc",
    "football club": "fc", 
    "futbol club": "fc",
    "futbol": "fc",
    "academy": "acad",
    "athletic club": "ac",
    "sports club": "sc",
    "youth soccer": "ys",
    "premier": "prem",
    "elite": "elite",
    "select": "sel",
    
    # State abbreviations
    "az ": "arizona ",
    "ca ": "california ",
    "tx ": "texas ",
    "fl ": "florida ",
    "ny ": "new york ",
    "pa ": "pennsylvania ",
    "il ": "illinois ",
    "oh ": "ohio ",
    "mi ": "michigan ",
    "ga ": "georgia ",
    "nc ": "north carolina ",
    "va ": "virginia ",
    "wa ": "washington ",
    "or ": "oregon ",
    "co ": "colorado ",
    "ut ": "utah ",
    "nv ": "nevada ",
    "az": "arizona",
    "ca": "california", 
    "tx": "texas",
    "fl": "florida",
    "ny": "new york",
    "pa": "pennsylvania",
    "il": "illinois",
    "oh": "ohio",
    "mi": "michigan",
    "ga": "georgia",
    "nc": "north carolina",
    "va": "virginia",
    "wa": "washington",
    "or": "oregon",
    "co": "colorado",
    "ut": "utah",
    "nv": "nevada",
    
    # Common club name variations
    "united": "united",
    "city": "city",
    "town": "town",
    "association": "assoc",
    "athletic": "ath",
    "sports": "sports",
    "soccer": "soccer",
    "football": "football",
    "youth": "youth",
    
    # Age group variations
    "under": "u",
    "u-": "u",
    "boys": "b",
    "girls": "g",
    "male": "b",
    "female": "g",
    "men": "b",
    "women": "g",
}

# Patterns to remove or normalize
REMOVE_PATTERNS = [
    r'\b(boys?|girls?|male|female|men|women)\b',  # Remove redundant gender terms
    r'\b(premier|elite|select|academy|club)\b',   # Remove redundant level terms when redundant
    r'[^\w\s]',  # Remove punctuation except spaces
    r'\s+',      # Normalize multiple spaces to single space
]

def load_club_prefixes(prefixes_file: str = 'data/mappings/club_prefixes.yml') -> Dict[str, List[str]]:
    """
    Load club prefix mappings from YAML file.
    
    Args:
        prefixes_file: Path to the club prefixes YAML file
        
    Returns:
        Dictionary mapping canonical club names to their variations
    """
    if not os.path.exists(prefixes_file):
        print(f"Warning: Club prefixes file not found: {prefixes_file}")
        return {}
    
    try:
        with open(prefixes_file, 'r', encoding='utf-8') as f:
            prefixes = yaml.safe_load(f)
        return prefixes or {}
    except Exception as e:
        print(f"Error loading club prefixes: {e}")
        return {}

def apply_club_prefix_normalization(name: str, club_prefixes: Dict[str, List[str]]) -> str:
    """
    Apply club prefix normalization to a team name.
    
    Args:
        name: Team name to normalize
        club_prefixes: Dictionary of canonical club names to variations
        
    Returns:
        Normalized team name with canonical club prefix
    """
    if not club_prefixes:
        return name
    
    name_lower = name.lower().strip()
    
    # Check each canonical club name and its variations
    for canonical_club, variations in club_prefixes.items():
        for variation in variations:
            variation_lower = variation.lower().strip()
            
            # Check if the variation appears at the start of the team name
            if name_lower.startswith(variation_lower):
                # Replace variation with canonical club name
                normalized_name = canonical_club + name_lower[len(variation_lower):]
                return normalized_name
    
    return name

def normalize_team_name(name: str) -> str:
    """
    Aggressively normalize team name for better matching.
    
    Args:
        name: Raw team name string
        
    Returns:
        Normalized team name string
    """
    if not isinstance(name, str) or not name.strip():
        return ""
    
    # Start with lowercase and strip
    s = name.lower().strip()
    
    # Phase 3 Enhancement #3: Apply club prefix normalization first
    club_prefixes = load_club_prefixes()
    s = apply_club_prefix_normalization(s, club_prefixes)
    
    # Apply common normalizations (but be more selective about state expansions)
    for old, new in COMMON_NORMALIZATIONS.items():
        # Skip state abbreviations for now - they cause more problems than they solve
        if old in ['az ', 'ca ', 'tx ', 'fl ', 'ny ', 'pa ', 'il ', 'oh ', 'mi ', 'ga ', 'nc ', 'va ', 'wa ', 'or ', 'co ', 'ut ', 'nv ', 'az', 'ca', 'tx', 'fl', 'ny', 'pa', 'il', 'oh', 'mi', 'ga', 'nc', 'va', 'wa', 'or', 'co', 'ut', 'nv']:
            continue
        else:
            s = s.replace(old, new)
    
    # Handle year patterns
    # Convert 4-digit years to 2-digit (2016 -> 16)
    s = re.sub(r'\b20(\d{2})\b', r'\1', s)
    
    # Convert U## patterns to 2-digit years (U10 -> 16, U11 -> 15)
    def u_to_year(match):
        age = int(match.group(1))
        if age in [10, 11, 12, 13, 14, 15, 16, 17, 18, 19]:
            birth_year = 2024 - age + 2
            return str(birth_year)[2:]  # Return 2-digit year
        return match.group(0)
    
    s = re.sub(r'\bu(\d{1,2})\b', u_to_year, s)
    
    # Handle B/G patterns with years (16B -> 16, 2016B -> 16)
    s = re.sub(r'\b(\d{2})[bg]\b', r'\1', s)
    s = re.sub(r'\b20(\d{2})[bg]\b', r'\1', s)
    
    # Don't convert 2-digit years back to 4-digit - keep them as 2-digit
    
    # Remove redundant gender/age terms
    s = re.sub(r'\b(boys?|girls?|male|female|men|women|b|g)\b', '', s)
    
    # Remove punctuation and normalize spacing
    s = re.sub(r'[^\w\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s)
    
    return s.strip()

def normalize_club_name(club_name: str) -> str:
    """
    Normalize club name specifically for matching.
    
    Args:
        club_name: Raw club name
        
    Returns:
        Normalized club name
    """
    if not isinstance(club_name, str):
        return ""
    
    s = club_name.lower().strip()
    
    # Apply club-specific normalizations
    club_normalizations = {
        "soccer club": "sc",
        "football club": "fc",
        "futbol club": "fc", 
        "academy": "acad",
        "athletic club": "ac",
        "sports club": "sc",
        "youth soccer": "ys",
        "premier": "prem",
        "elite": "elite",
        "select": "sel",
        "united": "united",
        "city": "city",
        "association": "assoc",
        "athletic": "ath",
    }
    
    for old, new in club_normalizations.items():
        s = s.replace(old, new)
    
    # Remove common suffixes that don't add meaning
    s = re.sub(r'\b(fc|sc|ac|acad|prem|elite|sel|united|city|assoc|ath)\b', '', s)
    
    # Clean up spacing
    s = re.sub(r'\s+', ' ', s)
    
    return s.strip()

def extract_meaningful_tokens(name: str) -> List[str]:
    """
    Extract meaningful tokens from a normalized team name.
    
    Args:
        name: Normalized team name
        
    Returns:
        List of meaningful tokens
    """
    if not isinstance(name, str):
        return []
    
    tokens = name.split()
    
    # Filter out generic terms
    generic_terms = {
        'fc', 'sc', 'ac', 'acad', 'prem', 'elite', 'sel', 'united', 'city', 'town',
        'assoc', 'ath', 'sports', 'soccer', 'football', 'youth', 'club', 'team',
        'b', 'g', 'boys', 'girls', 'male', 'female', 'men', 'women'
    }
    
    meaningful_tokens = []
    for token in tokens:
        if len(token) > 1 and token not in generic_terms:
            meaningful_tokens.append(token)
    
    return meaningful_tokens

def calculate_token_overlap(name1: str, name2: str) -> float:
    """
    Calculate token overlap ratio between two normalized names.
    
    Args:
        name1: First normalized name
        name2: Second normalized name
        
    Returns:
        Token overlap ratio (0.0 to 1.0)
    """
    tokens1 = set(extract_meaningful_tokens(name1))
    tokens2 = set(extract_meaningful_tokens(name2))
    
    if not tokens1 and not tokens2:
        return 1.0
    if not tokens1 or not tokens2:
        return 0.0
    
    intersection = len(tokens1 & tokens2)
    union = len(tokens1 | tokens2)
    
    return intersection / union if union > 0 else 0.0

# Test cases for validation
if __name__ == "__main__":
    test_cases = [
        ("AZ Arsenal 16 Boys Teal OC", "az arsenal 16 teal oc"),
        ("Phoenix Rising FC 2016", "phoenix rising fc 16"),
        ("RSL North 16B", "rsl arizona north 16"),
        ("Barcelona AZ 2016", "arizona barca academy 16"),
        ("Rebels SC Boys 2016", "rebels sc 16 white"),
        ("U10 Boys Arsenal", "16 arsenal"),
        ("2016B Premier Elite", "16 premier elite"),
    ]
    
    print("=== TEAM NAME NORMALIZATION TEST ===")
    for original, expected in test_cases:
        normalized = normalize_team_name(original)
        print(f"'{original}' -> '{normalized}' (expected: '{expected}')")
        print(f"  Match: {normalized == expected}")
        print()
