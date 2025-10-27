import pandas as pd
import numpy as np
from sophisticated_team_matcher import SophisticatedTeamMatcher
from datetime import datetime

def run_comprehensive_audit():
    """Run sophisticated matching on real U11 data and create detailed audit report"""
    
    print("=== COMPREHENSIVE U11 DATA AUDIT ===")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Load U11 master team list
    try:
        master_df = pd.read_csv('data/input/National_Male_U11_Master_Team_List.csv')
        master_teams = master_df['Team_Name'].tolist()
        print(f"✅ Loaded U11 master team list: {len(master_teams)} teams")
    except Exception as e:
        print(f"❌ Error loading master team list: {e}")
        return
    
    # Load U11 game history
    try:
        games_df = pd.read_csv('data/Game History u10 and u11.csv')
        games_df.columns = games_df.columns.str.strip()
        
        # Get unique teams from game history
        team_a_teams = games_df['Team A'].dropna().unique().tolist()
        team_b_teams = games_df['Team B'].dropna().unique().tolist()
        all_game_teams = list(set(team_a_teams + team_b_teams))
        print(f"✅ Loaded game history: {len(games_df)} games")
        print(f"✅ Found {len(all_game_teams)} unique teams in game history")
        
    except Exception as e:
        print(f"❌ Error loading game history: {e}")
        return
    
    # Initialize sophisticated matcher
    matcher = SophisticatedTeamMatcher()
    
    # Test with threshold 0.8
    threshold = 0.8
    print(f"\n--- RUNNING SOPHISTICATED MATCHING (threshold: {threshold}) ---")
    
    mapping = matcher.create_team_mapping(all_game_teams, master_teams, threshold)
    
    # Analyze results
    exact_matches = sum(1 for game_team, master_team in mapping.items() if game_team == master_team)
    fuzzy_matches = len(mapping) - exact_matches
    unmatched = len(all_game_teams) - len(mapping)
    
    print(f"\n=== AUDIT RESULTS ===")
    print(f"Exact matches: {exact_matches}")
    print(f"Fuzzy matches: {fuzzy_matches}")
    print(f"Total mapped: {len(mapping)}")
    print(f"Unmatched: {unmatched}")
    print(f"Match rate: {len(mapping)/len(all_game_teams)*100:.1f}%")
    
    # Create detailed audit report
    create_audit_report(mapping, matcher, all_game_teams, master_teams)
    
    return mapping

def create_audit_report(mapping, matcher, all_game_teams, master_teams):
    """Create detailed audit report for review"""
    
    print(f"\n--- CREATING DETAILED AUDIT REPORT ---")
    
    # Analyze fuzzy matches
    fuzzy_matches = []
    for game_team, master_team in mapping.items():
        if game_team != master_team:
            fuzzy_matches.append((game_team, master_team))
    
    # Sort by similarity for review
    fuzzy_matches_with_similarity = []
    for game_team, master_team in fuzzy_matches:
        game_parsed = matcher.parse_team_name(game_team)
        master_parsed = matcher.parse_team_name(master_team)
        similarity = matcher.calculate_similarity(game_parsed, master_parsed)
        fuzzy_matches_with_similarity.append((game_team, master_team, similarity))
    
    # Sort by similarity (highest first)
    fuzzy_matches_with_similarity.sort(key=lambda x: x[2], reverse=True)
    
    # Create audit files
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 1. All fuzzy matches (for detailed review)
    with open(f'audit_fuzzy_matches_{timestamp}.txt', 'w') as f:
        f.write("=== SOPHISTICATED TEAM MATCHING AUDIT REPORT ===\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total fuzzy matches: {len(fuzzy_matches_with_similarity)}\n")
        f.write(f"Threshold used: 0.8\n\n")
        
        f.write("=== FUZZY MATCHES (sorted by similarity) ===\n")
        f.write("Format: Game Team → Master Team (similarity)\n")
        f.write("Parsed components: Club, Year, Gender, Designation, Coach\n\n")
        
        for i, (game_team, master_team, similarity) in enumerate(fuzzy_matches_with_similarity, 1):
            game_parsed = matcher.parse_team_name(game_team)
            master_parsed = matcher.parse_team_name(master_team)
            
            f.write(f"{i:3d}. '{game_team}' → '{master_team}' ({similarity:.3f})\n")
            f.write(f"     Game:   Club='{game_parsed.get('club')}', Year='{game_parsed.get('birth_year')}', Gender='{game_parsed.get('gender')}', Designation='{game_parsed.get('designation')}', Coach='{game_parsed.get('coach')}'\n")
            f.write(f"     Master: Club='{master_parsed.get('club')}', Year='{master_parsed.get('birth_year')}', Gender='{master_parsed.get('gender')}', Designation='{master_parsed.get('designation')}', Coach='{master_parsed.get('coach')}'\n\n")
    
    # 2. High-confidence matches (similarity > 0.9)
    high_conf_matches = [m for m in fuzzy_matches_with_similarity if m[2] > 0.9]
    
    with open(f'audit_high_confidence_{timestamp}.txt', 'w') as f:
        f.write("=== HIGH-CONFIDENCE MATCHES (similarity > 0.9) ===\n")
        f.write(f"Count: {len(high_conf_matches)}\n\n")
        
        for i, (game_team, master_team, similarity) in enumerate(high_conf_matches, 1):
            f.write(f"{i:3d}. '{game_team}' → '{master_team}' ({similarity:.3f})\n")
    
    # 3. Medium-confidence matches (0.8 < similarity <= 0.9)
    medium_conf_matches = [m for m in fuzzy_matches_with_similarity if 0.8 < m[2] <= 0.9]
    
    with open(f'audit_medium_confidence_{timestamp}.txt', 'w') as f:
        f.write("=== MEDIUM-CONFIDENCE MATCHES (0.8 < similarity <= 0.9) ===\n")
        f.write(f"Count: {len(medium_conf_matches)}\n\n")
        
        for i, (game_team, master_team, similarity) in enumerate(medium_conf_matches, 1):
            f.write(f"{i:3d}. '{game_team}' → '{master_team}' ({similarity:.3f})\n")
    
    # 4. Unmatched teams (first 100)
    unmatched_teams = [team for team in all_game_teams if team not in mapping]
    
    with open(f'audit_unmatched_{timestamp}.txt', 'w') as f:
        f.write("=== UNMATCHED TEAMS (first 100) ===\n")
        f.write(f"Total unmatched: {len(unmatched_teams)}\n\n")
        
        for i, team in enumerate(sorted(unmatched_teams)[:100], 1):
            parsed = matcher.parse_team_name(team)
            f.write(f"{i:3d}. '{team}'\n")
            f.write(f"     Parsed: Club='{parsed.get('club')}', Year='{parsed.get('birth_year')}', Gender='{parsed.get('gender')}', Designation='{parsed.get('designation')}', Coach='{parsed.get('coach')}'\n\n")
    
    # 5. Summary report
    with open(f'audit_summary_{timestamp}.txt', 'w') as f:
        f.write("=== AUDIT SUMMARY ===\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("MATCHING STATISTICS:\n")
        f.write(f"- Total game teams: {len(all_game_teams)}\n")
        f.write(f"- Total master teams: {len(master_teams)}\n")
        f.write(f"- Exact matches: {len(mapping) - len(fuzzy_matches)}\n")
        f.write(f"- Fuzzy matches: {len(fuzzy_matches)}\n")
        f.write(f"- Unmatched: {len(unmatched_teams)}\n")
        f.write(f"- Match rate: {len(mapping)/len(all_game_teams)*100:.1f}%\n\n")
        
        f.write("CONFIDENCE BREAKDOWN:\n")
        f.write(f"- High confidence (>0.9): {len(high_conf_matches)}\n")
        f.write(f"- Medium confidence (0.8-0.9): {len(medium_conf_matches)}\n")
        f.write(f"- Low confidence (<0.8): {len(fuzzy_matches) - len(high_conf_matches) - len(medium_conf_matches)}\n\n")
        
        f.write("FILES GENERATED:\n")
        f.write(f"- audit_fuzzy_matches_{timestamp}.txt (all fuzzy matches with details)\n")
        f.write(f"- audit_high_confidence_{timestamp}.txt (similarity > 0.9)\n")
        f.write(f"- audit_medium_confidence_{timestamp}.txt (similarity 0.8-0.9)\n")
        f.write(f"- audit_unmatched_{timestamp}.txt (unmatched teams)\n")
        f.write(f"- audit_summary_{timestamp}.txt (this summary)\n\n")
        
        f.write("REVIEW INSTRUCTIONS:\n")
        f.write("1. Start with audit_summary_{timestamp}.txt for overview\n")
        f.write("2. Review audit_high_confidence_{timestamp}.txt first (most likely correct)\n")
        f.write("3. Check audit_medium_confidence_{timestamp}.txt for questionable matches\n")
        f.write("4. Look at audit_fuzzy_matches_{timestamp}.txt for detailed analysis\n")
        f.write("5. Check audit_unmatched_{timestamp}.txt for teams that should have matches\n")
    
    print(f"✅ Audit files created:")
    print(f"   - audit_fuzzy_matches_{timestamp}.txt")
    print(f"   - audit_high_confidence_{timestamp}.txt") 
    print(f"   - audit_medium_confidence_{timestamp}.txt")
    print(f"   - audit_unmatched_{timestamp}.txt")
    print(f"   - audit_summary_{timestamp}.txt")
    
    return timestamp

if __name__ == "__main__":
    mapping = run_comprehensive_audit()
    print(f"\n=== AUDIT COMPLETE ===")
    print(f"Check the generated audit files for detailed review.")
