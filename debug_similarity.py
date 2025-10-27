#!/usr/bin/env python3
"""
Debug similarity calculation
"""

import pandas as pd
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sophisticated_team_matcher import SophisticatedTeamMatcher

def debug_similarity():
    """Debug the similarity calculation"""
    print("=== DEBUGGING SIMILARITY CALCULATION ===")
    
    # Initialize matcher
    matcher = SophisticatedTeamMatcher()
    
    # Test exact match
    team1_name = "AZ Arsenal 16 Boys Teal OC"
    team2_name = "AZ Arsenal 16 Boys Teal OC"
    
    print(f"Team 1: '{team1_name}'")
    print(f"Team 2: '{team2_name}'")
    
    parsed1 = matcher.parse_team_name(team1_name)
    parsed2 = matcher.parse_team_name(team2_name)
    
    print(f"\nParsed 1: {parsed1}")
    print(f"Parsed 2: {parsed2}")
    
    # Test similarity calculation step by step
    similarity = matcher.calculate_similarity(parsed1, parsed2)
    print(f"\nSimilarity: {similarity}")
    
    # Test with slight variation
    team3_name = "AZ Arsenal 16 Boys Teal DB"
    parsed3 = matcher.parse_team_name(team3_name)
    print(f"\nTeam 3: '{team3_name}'")
    print(f"Parsed 3: {parsed3}")
    
    similarity2 = matcher.calculate_similarity(parsed1, parsed3)
    print(f"Similarity (1 vs 3): {similarity2}")

if __name__ == "__main__":
    debug_similarity()
