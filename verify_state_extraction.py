from sophisticated_team_matcher import SophisticatedTeamMatcher

def verify_state_extraction():
    """Verify state extraction is working correctly"""
    matcher = SophisticatedTeamMatcher()
    
    test_cases = [
        ('AYSO United NM 15B White', 'AYSO United GEO 15B White'),
    ]
    
    print("=== VERIFYING STATE EXTRACTION ===")
    for team1, team2 in test_cases:
        parsed1 = matcher.parse_team_name(team1)
        parsed2 = matcher.parse_team_name(team2)
        
        print(f"'{team1}'")
        print(f"  State: '{parsed1.get('state')}'")
        print(f"'{team2}'")
        print(f"  State: '{parsed2.get('state')}'")
        print(f"States match: {parsed1.get('state') == parsed2.get('state')}")
        print()

if __name__ == "__main__":
    verify_state_extraction()
