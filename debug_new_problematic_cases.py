from sophisticated_team_matcher import SophisticatedTeamMatcher

def debug_new_problematic_cases():
    """Debug the new problematic cases identified by the user"""
    matcher = SophisticatedTeamMatcher()
    
    test_cases = [
        # Case 1: Different coaches (JZ vs BD)
        ('AZ Arsenal 15 Boys Teal 1 JZ', 'AZ Arsenal 15 Boys Teal BD'),
        
        # Case 2: Different years (2014 vs 2015)
        ('Las Vegas Sports Academy U11 Boys Onyx 2014', 'Las Vegas Sports Academy U11 Boys Onix 2015'),
        
        # Case 3: Different states (NM vs GEO)
        ('AYSO United NM 15B White', 'AYSO United GEO 15B White'),
    ]
    
    print("=== DEBUGGING NEW PROBLEMATIC CASES ===")
    for i, (team1, team2) in enumerate(test_cases, 1):
        parsed1 = matcher.parse_team_name(team1)
        parsed2 = matcher.parse_team_name(team2)
        similarity = matcher.calculate_similarity(parsed1, parsed2)
        
        print(f"{i}. '{team1}' vs '{team2}'")
        print(f"   Team 1: Year='{parsed1.get('birth_year')}', Gender='{parsed1.get('gender')}', Designation='{parsed1.get('designation')}', Coach='{parsed1.get('coach')}'")
        print(f"   Team 2: Year='{parsed2.get('birth_year')}', Gender='{parsed2.get('gender')}', Designation='{parsed2.get('designation')}', Coach='{parsed2.get('coach')}'")
        print(f"   Similarity: {similarity}")
        print(f"   Expected: NO MATCH (different teams)")
        print()

if __name__ == "__main__":
    debug_new_problematic_cases()
