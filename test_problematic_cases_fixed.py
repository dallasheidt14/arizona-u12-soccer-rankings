from sophisticated_team_matcher import SophisticatedTeamMatcher

def test_problematic_cases():
    """Test the problematic cases identified by the user"""
    matcher = SophisticatedTeamMatcher()
    
    # Test cases that should NOT match
    test_cases = [
        # Case 1: Different years (2016 vs 2015)
        ('Las Vegas Sports Academy U10 Boys Copper 2016', 'Las Vegas Sports Academy U10 Boys Copper 2015'),
        
        # Case 2: Different team numbers (II vs I)
        ('Revolution 15B Grey II', 'Revolution 15B Grey'),
        
        # Case 3: Different team designations (2 vs A)
        ('AHFC 15B Blue 2 CF', 'AHFC 15B Blue A CF'),
        
        # Case 4: Different team designations (1 vs A)
        ('AHFC 15B Blue 1 CF', 'AHFC 15B Blue A CF'),
        
        # Case 5: Different team numbers (1 vs 2)
        ('EMFC 15B Monaco Comp 1', 'EMFC 15B Monaco Comp 2'),
    ]
    
    print("=== TESTING PROBLEMATIC CASES ===")
    print("These should all return 0.0 (no match):")
    print()
    
    for i, (team1, team2) in enumerate(test_cases, 1):
        parsed1 = matcher.parse_team_name(team1)
        parsed2 = matcher.parse_team_name(team2)
        similarity = matcher.calculate_similarity(parsed1, parsed2)
        
        print(f"{i}. '{team1}' vs '{team2}'")
        print(f"   Team 1: Year='{parsed1.get('birth_year')}', Gender='{parsed1.get('gender')}', Designation='{parsed1.get('designation')}', Coach='{parsed1.get('coach')}'")
        print(f"   Team 2: Year='{parsed2.get('birth_year')}', Gender='{parsed2.get('gender')}', Designation='{parsed2.get('designation')}', Coach='{parsed2.get('coach')}'")
        print(f"   Similarity: {similarity}")
        
        if similarity > 0:
            print(f"   ❌ BAD MATCH - Should be 0.0")
        else:
            print(f"   ✅ CORRECT - No match")
        print()

if __name__ == "__main__":
    test_problematic_cases()
