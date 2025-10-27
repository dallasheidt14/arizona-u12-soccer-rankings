#!/usr/bin/env python3
"""
Debug similarity for similar teams
"""

import pandas as pd
import os
import sys
from difflib import SequenceMatcher

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sophisticated_team_matcher import SophisticatedTeamMatcher

def debug_similar_teams():
    """Debug similarity for similar teams"""
    print("=== DEBUGGING SIMILARITY FOR SIMILAR TEAMS ===")
    
    # Initialize matcher
    matcher = SophisticatedTeamMatcher()
    
    # Test similar teams
    team1_name = "AZ Arsenal 16 Boys Teal OC"
    team2_name = "AZ Arsenal 16 Boys Teal DB"
    
    parsed1 = matcher.parse_team_name(team1_name)
    parsed2 = matcher.parse_team_name(team2_name)
    
    print(f"Team 1: '{team1_name}'")
    print(f"Team 2: '{team2_name}'")
    print(f"Parsed 1: {parsed1}")
    print(f"Parsed 2: {parsed2}")
    
    # Step through similarity calculation
    team1 = parsed1
    team2 = parsed2
    
    # Extract club names
    club1 = team1.get('club', '')
    club2 = team2.get('club', '')
    print(f"\nClub 1: '{club1}'")
    print(f"Club 2: '{club2}'")
    
    # Normalize club names
    club1_norm = matcher.normalize_club_name(club1)
    club2_norm = matcher.normalize_club_name(club2)
    print(f"Normalized Club 1: '{club1_norm}'")
    print(f"Normalized Club 2: '{club2_norm}'")
    
    # Calculate base similarity
    club_similarity = SequenceMatcher(None, club1_norm, club2_norm).ratio()
    print(f"Base club similarity: {club_similarity}")
    
    # Check substring boost
    if club1_norm in club2_norm or club2_norm in club1_norm:
        club_similarity = max(club_similarity, 0.9)
        print(f"Substring boost applied: {club_similarity}")
    
    # Check word match boost
    words1 = set(club1_norm.split())
    words2 = set(club2_norm.split())
    common_words = words1.intersection(words2)
    print(f"Common words: {common_words}")
    
    # Check meaningful words
    generic_terms = ['fc', 'sc', 'united', 'city', 'town', 'academy', 'club', 'association', 'athletic', 'sports', 'soccer', 'football', 'youth', 'premier', 'elite', '15b', '16b', '17b', '18b', '15g', '16g', '17g', '18g', 'south', 'north', 'east', 'west', 'central', 'metro', 'valley', 'ridge', 'hills', 'park', 'field', 'stadium', 'center', 'centre']
    meaningful_words = [w for w in common_words if len(w) > 1 and w not in generic_terms]
    print(f"Meaningful words: {meaningful_words}")
    
    if len(meaningful_words) >= 2:
        club_similarity = max(club_similarity, 0.8)
        print(f"Word match boost applied: {club_similarity}")
    
    # Check thresholds
    print(f"\nChecking thresholds:")
    print(f"Club similarity >= 0.8: {club_similarity >= 0.8}")
    print(f"Meaningful words >= 2: {len(meaningful_words) >= 2}")
    
    # Check matching criteria
    matching_criteria = 0
    
    # Birth year match
    if team1.get('birth_year') == team2.get('birth_year') and team1.get('birth_year'):
        matching_criteria += 1
        print(f"Birth year match: {team1.get('birth_year')} == {team2.get('birth_year')}")
    
    # Gender match
    if team1.get('gender') == team2.get('gender') and team1.get('gender'):
        matching_criteria += 1
        print(f"Gender match: {team1.get('gender')} == {team2.get('gender')}")
    
    # Designation match
    if team1.get('designation') == team2.get('designation') and team1.get('designation'):
        matching_criteria += 1
        print(f"Designation match: {team1.get('designation')} == {team2.get('designation')}")
    
    # Coach match
    coach1 = team1.get('coach', '')
    coach2 = team2.get('coach', '')
    if coach1 and coach2 and coach1 == coach2:
        matching_criteria += 1
        print(f"Coach match: {coach1} == {coach2}")
    else:
        print(f"No coach match: {coach1} != {coach2}")
    
    # Club word match
    if len(meaningful_words) >= 2:
        matching_criteria += 1
        print(f"Club word match: {len(meaningful_words)} meaningful words")
    
    print(f"Total matching criteria: {matching_criteria}")
    print(f"Matching criteria >= 3: {matching_criteria >= 3}")
    
    # Final similarity
    if club_similarity >= 0.8 and len(meaningful_words) >= 2 and matching_criteria >= 3:
        print(f"Final similarity: {club_similarity}")
    else:
        print(f"Final similarity: 0.0 (failed validation)")

if __name__ == "__main__":
    debug_similar_teams()
