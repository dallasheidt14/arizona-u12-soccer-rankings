from sophisticated_team_matcher import SophisticatedTeamMatcher

def debug_specific_cases():
    """Debug the specific problematic cases identified by the user"""
    matcher = SophisticatedTeamMatcher()
    
    test_cases = [
        # Case 1: Should be a match (same team, different naming)
        ('Manitou FC 15B Academy Orange', 'Manitou FC 2015 Boys Academy Orange'),
        
        # Case 2: Should NOT be a match (different team numbers)
        ('South 15B Gold I', 'South 15B Gold'),
        
        # Case 3: Should NOT be a match (different coaches)
        ('Hudson United 2015 Boys Blue GREY 1', 'Hudson United 2015 Boys Blue RENN 1'),
    ]
    
    print("=== DEBUGGING SPECIFIC PROBLEMATIC CASES ===")
    for i, (team1, team2) in enumerate(test_cases, 1):
        parsed1 = matcher.parse_team_name(team1)
        parsed2 = matcher.parse_team_name(team2)
        similarity = matcher.calculate_similarity(parsed1, parsed2)
        
        print(f"{i}. '{team1}' vs '{team2}'")
        print(f"   Team 1: Year='{parsed1.get('birth_year')}', Gender='{parsed1.get('gender')}', Designation='{parsed1.get('designation')}', Coach='{parsed1.get('coach')}'")
        print(f"   Team 2: Year='{parsed2.get('birth_year')}', Gender='{parsed2.get('gender')}', Designation='{parsed2.get('designation')}', Coach='{parsed2.get('coach')}'")
        print(f"   Similarity: {similarity}")
        
        if i == 1:
            print(f"   Expected: MATCH (same team, different naming)")
        else:
            print(f"   Expected: NO MATCH (different teams)")
        print()

if __name__ == "__main__":
    debug_specific_cases()
