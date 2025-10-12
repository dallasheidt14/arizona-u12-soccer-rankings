#!/usr/bin/env python3
"""
Create proper master list for U11 ranking generator
"""
import pandas as pd

def create_proper_u11_master():
    """Create master list with correct column names for ranking generator"""
    print("Creating proper U11 master list...")
    
    # Load our Arizona teams with correct team_ids
    teams_df = pd.read_csv('data/master/u11_boys_2015/teams_by_state/arizona_teams.csv')
    print(f"Loaded {len(teams_df)} Arizona U11 teams")
    
    # Create master list with correct format
    master_list = []
    
    for _, team in teams_df.iterrows():
        master_list.append({
            'team_id': team['team_id'],
            'display_name': team['team_name'],
            'club': team.get('club_name', ''),
            'state': 'AZ',
            'gender': 'M',
            'age_group': 'U11'
        })
    
    # Convert to DataFrame
    master_df = pd.DataFrame(master_list)
    
    # Save to expected location
    output_path = 'data/bronze/AZ MALE u11 MASTER TEAM LIST.csv'
    master_df.to_csv(output_path, index=False)
    
    print(f"Created master list for {len(master_df)} teams")
    print(f"Saved to: {output_path}")
    
    # Show sample
    print(f"\nSample master list:")
    print(master_df.head(3).to_string(index=False))
    
    return output_path

if __name__ == "__main__":
    create_proper_u11_master()

