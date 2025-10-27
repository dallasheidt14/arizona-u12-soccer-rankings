import re

def debug_grey_extraction_detailed():
    """Debug why GREY isn't being extracted"""
    name = 'Hudson United 2015 Boys Blue GREY 1'
    
    print(f"Testing: '{name}'")
    
    # Test the second regex pattern with findall
    all_matches = re.findall(r'\b([A-Za-z]+(?:\.[A-Za-z])?)\s+\d+', name)
    print(f"All matches: {all_matches}")
    
    if all_matches:
        # Take the last match (most likely to be coach name)
        potential_coach = all_matches[-1].lower()
        print(f"Last match: '{potential_coach}'")
        
        generic_terms = ['team', 'club', 'fc', 'sc', 'united', 'boys', 'girls', 'male', 'female', 'premier', 'elite', 'select', 'academy', 'orange', 'blue', 'red', 'white', 'black', 'green', 'yellow', 'gold', 'silver', 'grey', 'gray', 'navy', 'maroon', 'burgundy', 'teal', 'cyan', 'lime', 'brown', 'tan', 'beige']
        print(f"Length: {len(potential_coach)}")
        print(f"In generic: {potential_coach in generic_terms}")
        print(f"Generic terms: {generic_terms}")
        
        if len(potential_coach) > 3 and potential_coach not in generic_terms:
            print(f"Would extract as coach: '{potential_coach}'")
        else:
            print(f"Rejected: length={len(potential_coach)}, in_generic={potential_coach in generic_terms}")

if __name__ == "__main__":
    debug_grey_extraction_detailed()
