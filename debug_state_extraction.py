from sophisticated_team_matcher import SophisticatedTeamMatcher

def debug_state_extraction():
    """Debug state extraction specifically"""
    matcher = SophisticatedTeamMatcher()
    
    test_names = [
        'AYSO United NM 15B White',
        'AYSO United GEO 15B White',
    ]
    
    print("=== DEBUGGING STATE EXTRACTION ===")
    for name in test_names:
        parsed = matcher.parse_team_name(name)
        print(f"'{name}'")
        print(f"  State: '{parsed.get('state')}'")
        
        # Test the state extraction method directly
        state = matcher._extract_state(name.lower())
        print(f"  Direct state extraction: '{state}'")
        print()

if __name__ == "__main__":
    debug_state_extraction()
