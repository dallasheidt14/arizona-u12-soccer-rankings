#!/usr/bin/env python3
"""
Simple test of similarity calculation
"""

import pandas as pd
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sophisticated_team_matcher import SophisticatedTeamMatcher

def simple_similarity_test():
    """Simple test of similarity calculation"""
    print("=== SIMPLE SIMILARITY TEST ===")
    
    # Initialize matcher
    matcher = SophisticatedTeamMatcher()
    
    # Test exact match
    team1_name = "AZ Arsenal 16 Boys Teal OC"
    team2_name = "AZ Arsenal 16 Boys Teal OC"
    
    parsed1 = matcher.parse_team_name(team1_name)
    parsed2 = matcher.parse_team_name(team2_name)
    
    print(f"Team 1: '{team1_name}'")
    print(f"Team 2: '{team2_name}'")
    print(f"Parsed 1: {parsed1}")
    print(f"Parsed 2: {parsed2}")
    
    # Test similarity calculation
    similarity = matcher.calculate_similarity(parsed1, parsed2)
    print(f"Similarity: {similarity}")
    
    # Test with slight variation
    team3_name = "AZ Arsenal 16 Boys Teal DB"
    parsed3 = matcher.parse_team_name(team3_name)
    print(f"\nTeam 3: '{team3_name}'")
    print(f"Parsed 3: {parsed3}")
    
    similarity2 = matcher.calculate_similarity(parsed1, parsed3)
    print(f"Similarity (1 vs 3): {similarity2}")

if __name__ == "__main__":
    simple_similarity_test()
