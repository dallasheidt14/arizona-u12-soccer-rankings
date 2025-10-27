from sophisticated_team_matcher import SophisticatedTeamMatcher

def debug_state_abbreviations():
    """Debug state abbreviation handling"""
    matcher = SophisticatedTeamMatcher()
    
    test_names = [
        'AYSO United NM 15B White',
        'AYSO United GEO 15B White',
    ]
    
    print("=== DEBUGGING STATE ABBREVIATIONS ===")
    for name in test_names:
        parsed = matcher.parse_team_name(name)
        print(f"'{name}'")
        print(f"  Year: '{parsed.get('birth_year')}'")
        print(f"  Gender: '{parsed.get('gender')}'")
        print(f"  Designation: '{parsed.get('designation')}'")
        print(f"  Coach: '{parsed.get('coach')}'")
        print(f"  Club: '{parsed.get('club')}'")
        print()

if __name__ == "__main__":
    debug_state_abbreviations()
