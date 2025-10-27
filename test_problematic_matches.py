import pandas as pd
import numpy as np
from sophisticated_team_matcher import SophisticatedTeamMatcher

def test_problematic_matches():
    """Test the sophisticated matching on the specific problematic matches identified"""
    
    print("=== TESTING SOPHISTICATED MATCHING ON PROBLEMATIC CASES ===\n")
    
    # Load U11 master team list
    try:
        master_df = pd.read_csv('data/input/National_Male_U11_Master_Team_List.csv')
        master_teams = master_df['Team_Name'].tolist()
        print(f"✅ Loaded U11 master team list: {len(master_teams)} teams")
    except Exception as e:
        print(f"❌ Error loading master team list: {e}")
        return
    
    matcher = SophisticatedTeamMatcher()
    
    # Test the specific problematic matches you identified
    problematic_cases = [
        ("DSA Dallas Rebels 15B Cisneros", "Academia De Futbol Dallas 15b"),
        ("AZSC 15B White", "JSC 15B White"),
        ("Kitsap Alliance FC 15B White", "Phoenix Premier FC 15B White"),
        ("Solar SW 15B Garcia.S", "Solar 15B Castro"),
        ("Mankato United 15B", "Dublin United 15B Pre-EA"),
        ("Dallas Hornets 15B Delta", "Diablo Valley FC 15B Delta"),
        ("WSM 15B TS Samba", "15B TS Samba"),
    ]
    
    print("Testing problematic matches (should be REJECTED):")
    print("-" * 80)
    
    for game_team, master_team in problematic_cases:
        # Parse both teams
        game_parsed = matcher.parse_team_name(game_team)
        master_parsed = matcher.parse_team_name(master_team)
        similarity = matcher.calculate_similarity(game_parsed, master_parsed)
        
        print(f"Game Team: '{game_team}'")
        print(f"  Parsed: Club='{game_parsed.get('club')}', Year='{game_parsed.get('birth_year')}', Gender='{game_parsed.get('gender')}', Designation='{game_parsed.get('designation')}'")
        
        print(f"Master Team: '{master_team}'")
        print(f"  Parsed: Club='{master_parsed.get('club')}', Year='{master_parsed.get('birth_year')}', Gender='{master_parsed.get('gender')}', Designation='{master_parsed.get('designation')}'")
        
        print(f"Similarity: {similarity:.3f}")
        print(f"Match: {'✓ YES' if similarity >= 0.8 else '✗ NO'}")
        
        if similarity >= 0.8:
            print("  ⚠️  WARNING: This should be REJECTED!")
        else:
            print("  ✅ CORRECTLY REJECTED")
        
        print("-" * 80)
    
    # Test some good matches that should work
    good_cases = [
        ("Next Level Soccer Southeast 2015 Boys Red", "Next Level SE U11 Boys Red"),
        ("Real Madrid FC 2016 Boys Blue", "Real Madrid 16 Boys Blue"),
        ("Arsenal FC 2015 Boys Premier", "Arsenal 15 Boys Premier"),
    ]
    
    print("\nTesting good matches (should be ACCEPTED):")
    print("-" * 80)
    
    for game_team, master_team in good_cases:
        # Parse both teams
        game_parsed = matcher.parse_team_name(game_team)
        master_parsed = matcher.parse_team_name(master_team)
        similarity = matcher.calculate_similarity(game_parsed, master_parsed)
        
        print(f"Game Team: '{game_team}'")
        print(f"Master Team: '{master_team}'")
        print(f"Similarity: {similarity:.3f}")
        print(f"Match: {'✓ YES' if similarity >= 0.8 else '✗ NO'}")
        
        if similarity >= 0.8:
            print("  ✅ CORRECTLY ACCEPTED")
        else:
            print("  ⚠️  WARNING: This should be ACCEPTED!")
        
        print("-" * 80)

if __name__ == "__main__":
    test_problematic_matches()
