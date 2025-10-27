from sophisticated_team_matcher import SophisticatedTeamMatcher

def test_problematic_club_matches():
    """Test the problematic club matches identified by the user"""
    matcher = SophisticatedTeamMatcher()
    
    # Test cases that should NOT match (different clubs)
    test_cases = [
        # Case 1: Different clubs with shared generic word
        ('South Valley Chivas 15B Navy', 'Alabama FC South 15B Navy'),
        
        # Case 2: Different clubs with shared word
        ('Oregon Surf 15B Blue', 'Lincoln Surf 15B Blue'),
        
        # Case 3: Different clubs with shared location
        ('Dallas Hornets 16B Rockwall - WHITE', 'Dallas Cosmos 16B White'),
        
        # Case 4: Different clubs with shared word
        ('Legends FC AZ 14B FC', 'Inter Legends FC 14B Capetillo'),
        
        # Case 5: Different coaches
        ('BVB 16B Black East (Brown)', 'BVB 16B Black West (Orona)'),
        
        # Case 6: Different clubs with shared location
        ('Atletico Dallas Youth FTW 15B Blue', 'FC Dallas Youth 15B Central Blue'),
        
        # Case 7: Different clubs with shared suffix
        ('Colorado Rapids YSC 15B Pre-Elite I', 'Fremont YSC 15B ID I'),
    ]
    
    print("=== TESTING PROBLEMATIC CLUB MATCHES ===")
    print("These should all return 0.0 (no match):")
    print()
    
    for i, (team1, team2) in enumerate(test_cases, 1):
        parsed1 = matcher.parse_team_name(team1)
        parsed2 = matcher.parse_team_name(team2)
        similarity = matcher.calculate_similarity(parsed1, parsed2)
        
        print(f"{i}. '{team1}' vs '{team2}'")
        print(f"   Team 1: Club='{parsed1.get('club')}', Year='{parsed1.get('birth_year')}', Gender='{parsed1.get('gender')}', Designation='{parsed1.get('designation')}', Coach='{parsed1.get('coach')}', State='{parsed1.get('state')}'")
        print(f"   Team 2: Club='{parsed2.get('club')}', Year='{parsed2.get('birth_year')}', Gender='{parsed2.get('gender')}', Designation='{parsed2.get('designation')}', Coach='{parsed2.get('coach')}', State='{parsed2.get('state')}'")
        print(f"   Similarity: {similarity}")
        
        if similarity > 0:
            print(f"   ❌ BAD MATCH - Should be 0.0")
        else:
            print(f"   ✅ CORRECT - No match")
        print()

if __name__ == "__main__":
    test_problematic_club_matches()
