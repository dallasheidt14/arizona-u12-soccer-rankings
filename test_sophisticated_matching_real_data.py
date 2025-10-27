import pandas as pd
import numpy as np
from sophisticated_team_matcher import SophisticatedTeamMatcher

def test_real_u11_data():
    """Test sophisticated matching on real U11 data"""
    
    print("=== TESTING SOPHISTICATED MATCHING ON REAL U11 DATA ===\n")
    
    # Load U11 master team list
    try:
        master_df = pd.read_csv('data/input/National_Male_U11_Master_Team_List.csv')
        print(f"✅ Loaded U11 master team list: {len(master_df)} teams")
        master_teams = master_df['Team_Name'].tolist()
    except Exception as e:
        print(f"❌ Error loading master team list: {e}")
        return
    
    # Load U11 game history
    try:
        games_df = pd.read_csv('data/Game History u10 and u11.csv')
        print(f"✅ Loaded game history: {len(games_df)} games")
        
        # Strip whitespace from column names
        games_df.columns = games_df.columns.str.strip()
        
        # Get unique teams from game history
        team_a_teams = games_df['Team A'].dropna().unique().tolist()
        team_b_teams = games_df['Team B'].dropna().unique().tolist()
        all_game_teams = list(set(team_a_teams + team_b_teams))
        print(f"✅ Found {len(all_game_teams)} unique teams in game history")
        
    except Exception as e:
        print(f"❌ Error loading game history: {e}")
        return
    
    # Initialize sophisticated matcher
    matcher = SophisticatedTeamMatcher()
    
    # Test matching with different thresholds
    thresholds = [0.7, 0.8, 0.9]
    
    for threshold in thresholds:
        print(f"\n--- TESTING WITH THRESHOLD {threshold} ---")
        
        mapping = matcher.create_team_mapping(all_game_teams, master_teams, threshold)
        
        # Analyze results
        exact_matches = sum(1 for game_team, master_team in mapping.items() if game_team == master_team)
        fuzzy_matches = len(mapping) - exact_matches
        unmatched = len(all_game_teams) - len(mapping)
        
        print(f"Exact matches: {exact_matches}")
        print(f"Fuzzy matches: {fuzzy_matches}")
        print(f"Total mapped: {len(mapping)}")
        print(f"Unmatched: {unmatched}")
        print(f"Match rate: {len(mapping)/len(all_game_teams)*100:.1f}%")
        
        # Show sample fuzzy matches
        if fuzzy_matches > 0:
            print(f"\nSample fuzzy matches (threshold {threshold}):")
            fuzzy_count = 0
            for game_team, master_team in mapping.items():
                if game_team != master_team and fuzzy_count < 10:
                    # Parse both teams to show the matching logic
                    game_parsed = matcher.parse_team_name(game_team)
                    master_parsed = matcher.parse_team_name(master_team)
                    similarity = matcher.calculate_similarity(game_parsed, master_parsed)
                    
                    print(f"  '{game_team}' → '{master_team}' (similarity: {similarity:.3f})")
                    print(f"    Game: Club='{game_parsed.get('club')}', Year='{game_parsed.get('birth_year')}', Gender='{game_parsed.get('gender')}', Designation='{game_parsed.get('designation')}'")
                    print(f"    Master: Club='{master_parsed.get('club')}', Year='{master_parsed.get('birth_year')}', Gender='{master_parsed.get('gender')}', Designation='{master_parsed.get('designation')}'")
                    print()
                    fuzzy_count += 1
        
        # Show sample unmatched teams
        if unmatched > 0:
            print(f"\nSample unmatched teams (threshold {threshold}):")
            unmatched_teams = [team for team in all_game_teams if team not in mapping]
            for i, team in enumerate(sorted(unmatched_teams)[:10]):
                parsed = matcher.parse_team_name(team)
                print(f"  {i+1}. '{team}'")
                print(f"     Parsed: Club='{parsed.get('club')}', Year='{parsed.get('birth_year')}', Gender='{parsed.get('gender')}', Designation='{parsed.get('designation')}'")
            if len(unmatched_teams) > 10:
                print(f"     ... and {len(unmatched_teams) - 10} more")

def analyze_specific_teams():
    """Analyze specific teams that might be problematic"""
    
    print("\n=== ANALYZING SPECIFIC PROBLEMATIC TEAMS ===\n")
    
    # Load data
    try:
        master_df = pd.read_csv('data/input/National_Male_U11_Master_Team_List.csv')
        master_teams = master_df['Team_Name'].tolist()
        
        games_df = pd.read_csv('data/Game History u10 and u11.csv')
        # Strip whitespace from column names
        games_df.columns = games_df.columns.str.strip()
        
        all_game_teams = list(set(games_df['Team A'].dropna().unique().tolist() + 
                                 games_df['Team B'].dropna().unique().tolist()))
        
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return
    
    matcher = SophisticatedTeamMatcher()
    
    # Look for teams with "Southeast" in the name
    southeast_teams = [team for team in all_game_teams if 'southeast' in team.lower()]
    print(f"Found {len(southeast_teams)} teams with 'Southeast' in name:")
    
    for team in southeast_teams:
        print(f"  - '{team}'")
        
        # Parse the team
        parsed = matcher.parse_team_name(team)
        print(f"    Parsed: Club='{parsed.get('club')}', Year='{parsed.get('birth_year')}', Gender='{parsed.get('gender')}', Designation='{parsed.get('designation')}'")
        
        # Find potential matches in master list
        potential_matches = []
        for master_team in master_teams:
            if 'southeast' in master_team.lower():
                master_parsed = matcher.parse_team_name(master_team)
                similarity = matcher.calculate_similarity(parsed, master_parsed)
                if similarity > 0.5:  # Show any reasonable similarity
                    potential_matches.append((master_team, similarity))
        
        if potential_matches:
            print(f"    Potential matches:")
            for master_team, similarity in sorted(potential_matches, key=lambda x: x[1], reverse=True):
                print(f"      - '{master_team}' (similarity: {similarity:.3f})")
        else:
            print(f"    No potential matches found")
        print()

if __name__ == "__main__":
    test_real_u11_data()
    analyze_specific_teams()
