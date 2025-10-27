import pandas as pd
import numpy as np
from sophisticated_team_matcher import SophisticatedTeamMatcher

def test_problematic_case():
    """Test the specific problematic case"""
    
    matcher = SophisticatedTeamMatcher()
    
    team1 = "DSA Dallas Rebels 15B Cisneros"
    team2 = "Academia De Futbol Dallas 15b"
    
    parsed1 = matcher.parse_team_name(team1)
    parsed2 = matcher.parse_team_name(team2)
    similarity = matcher.calculate_similarity(parsed1, parsed2)
    
    print(f"Team 1: '{team1}'")
    print(f"  Parsed: Club='{parsed1.get('club')}', Year='{parsed1.get('birth_year')}', Gender='{parsed1.get('gender')}', Designation='{parsed1.get('designation')}', Coach='{parsed1.get('coach')}'")
    
    print(f"Team 2: '{team2}'")
    print(f"  Parsed: Club='{parsed2.get('club')}', Year='{parsed2.get('birth_year')}', Gender='{parsed2.get('gender')}', Designation='{parsed2.get('designation')}', Coach='{parsed2.get('coach')}'")
    
    print(f"Similarity: {similarity:.3f}")
    print(f"Match: {'✓ YES' if similarity >= 0.8 else '✗ NO'}")

if __name__ == "__main__":
    test_problematic_case()
