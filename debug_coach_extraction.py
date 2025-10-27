from sophisticated_team_matcher import SophisticatedTeamMatcher
import re

def debug_coach_extraction():
    """Debug coach name extraction specifically"""
    matcher = SophisticatedTeamMatcher()
    
    test_names = [
        'Hudson United 2015 Boys Blue GREY 1',
        'Hudson United 2015 Boys Blue RENN 1',
        'Manitou FC 15B Academy Orange',
        'Manitou FC 2015 Boys Academy Orange',
    ]
    
    print("=== DEBUGGING COACH NAME EXTRACTION ===")
    for name in test_names:
        parsed = matcher.parse_team_name(name)
        print(f"'{name}'")
        print(f"  Year: '{parsed.get('birth_year')}'")
        print(f"  Gender: '{parsed.get('gender')}'")
        print(f"  Designation: '{parsed.get('designation')}'")
        print(f"  Coach: '{parsed.get('coach')}'")
        
        # Test the regex pattern manually
        coach_match = re.search(r'\b([A-Za-z]+(?:\.[A-Za-z])?)\s*$', name)
        if coach_match:
            potential_coach = coach_match.group(1).lower()
            print(f"  Regex match: '{potential_coach}'")
            
            generic_terms = ['team', 'club', 'fc', 'sc', 'united', 'boys', 'girls', 'male', 'female', 'premier', 'elite', 'select', 'academy', 'orange', 'blue', 'red', 'white', 'black', 'green', 'yellow', 'gold', 'silver', 'grey', 'gray', 'navy', 'maroon', 'burgundy', 'teal', 'cyan', 'lime', 'brown', 'tan', 'beige']
            if len(potential_coach) > 3 and potential_coach not in generic_terms:
                print(f"  Would extract as coach: '{potential_coach}'")
            else:
                print(f"  Rejected: length={len(potential_coach)}, in_generic={potential_coach in generic_terms}")
        else:
            print(f"  No regex match")
        print()

if __name__ == "__main__":
    debug_coach_extraction()
