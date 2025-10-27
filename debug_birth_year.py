#!/usr/bin/env python3
"""
Debug birth year extraction
"""

import re

def debug_birth_year_extraction():
    """Debug the birth year extraction logic"""
    print("=== DEBUGGING BIRTH YEAR EXTRACTION ===")
    
    test_names = [
        "Riptide Black 2016B",
        "AZ Arsenal 16 Boys Teal OC",
        "PRFC Scottsdale 16B Predator",
        "CJFA MetroStars 16B"
    ]
    
    for name in test_names:
        print(f"\nTesting: '{name}'")
        
        # Test 4-digit year pattern
        year_match = re.search(r'\b(20\d{2})(?:[a-zA-Z]|\b)', name)
        if year_match:
            print(f"  4-digit year: {year_match.group(1)}")
        else:
            print("  4-digit year: No match")
        
        # Test U## pattern
        u_match = re.search(r'\bu(\d{1,2})\b', name)
        if u_match:
            age = int(u_match.group(1))
            birth_year = 2024 - age + 2
            print(f"  U## pattern: U{u_match.group(1)} -> {birth_year}")
        else:
            print("  U## pattern: No match")
        
        # Test 2-digit year pattern
        year_match = re.search(r'\b(\d{2})\b', name)
        if year_match:
            year = year_match.group(1)
            if int(year) >= 0 and int(year) <= 30:
                print(f"  2-digit year: {year} -> 20{year}")
            elif int(year) >= 80 and int(year) <= 99:
                print(f"  2-digit year: {year} -> 19{year}")
        else:
            print("  2-digit year: No match")
        
        # Test B/G pattern
        bg_match = re.search(r'\b(\d{2})[bg]\b', name)
        if bg_match:
            year = bg_match.group(1)
            if int(year) >= 0 and int(year) <= 30:
                print(f"  B/G pattern: {year}B/G -> 20{year}")
            elif int(year) >= 80 and int(year) <= 99:
                print(f"  B/G pattern: {year}B/G -> 19{year}")
        else:
            print("  B/G pattern: No match")

if __name__ == "__main__":
    debug_birth_year_extraction()