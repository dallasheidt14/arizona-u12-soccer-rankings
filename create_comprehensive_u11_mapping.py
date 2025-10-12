#!/usr/bin/env python3
"""
Create comprehensive name mapping for ALL teams in U11 games
"""
import pandas as pd
import hashlib

def create_comprehensive_u11_mapping():
    """Create name mapping for ALL teams found in U11 games"""
    print("Creating comprehensive U11 name mapping...")
    
    # Load our Arizona teams (master list)
    teams_df = pd.read_csv('data/master/u11_boys_2015/teams_by_state/arizona_teams.csv')
    print(f"Loaded {len(teams_df)} Arizona U11 teams from master list")
    
    # Load all teams from games
    games_df = pd.read_csv('data/gold/Matched_Games_U11_CLEAN.csv')
    all_teams_in_games = set(games_df['Team A'].unique()) | set(games_df['Team B'].unique())
    print(f"Found {len(all_teams_in_games)} unique teams in games")
    
    # Create comprehensive mapping
    name_mapping = []
    
    # Add teams from master list (these have real team_ids)
    for _, team in teams_df.iterrows():
        team_name = team['team_name']
        team_id = team['team_id']
        
        name_mapping.append({
            'raw_name': team_name,
            'team_id': team_id,
            'display_name': team_name,
            'source': 'master_list'
        })
    
    # Add teams from games that aren't in master list (generate external IDs)
    master_team_names = set(teams_df['team_name'])
    external_teams = all_teams_in_games - master_team_names
    
    print(f"Adding {len(external_teams)} external teams with generated IDs")
    
    for team_name in external_teams:
        # Generate external ID
        external_id = f"ext_{hashlib.sha1(f'u11_2025:{team_name}'.encode()).hexdigest()[:12]}"
        
        name_mapping.append({
            'raw_name': team_name,
            'team_id': external_id,
            'display_name': team_name,
            'source': 'external'
        })
    
    # Convert to DataFrame
    mapping_df = pd.DataFrame(name_mapping)
    
    # Save to expected location
    output_path = 'data/mappings/az_boys_u11_2025/name_map.csv'
    mapping_df.to_csv(output_path, index=False)
    
    print(f"Created comprehensive name mapping for {len(mapping_df)} teams")
    print(f"  - {len(teams_df)} from master list")
    print(f"  - {len(external_teams)} external teams")
    print(f"Saved to: {output_path}")
    
    # Show sample
    print(f"\nSample name mapping:")
    print(mapping_df.head(5).to_string(index=False))
    
    return output_path

if __name__ == "__main__":
    create_comprehensive_u11_mapping()

