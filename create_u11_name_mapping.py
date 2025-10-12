#!/usr/bin/env python3
"""
Create name mapping file for U11 ranking generator
"""
import pandas as pd

def create_u11_name_mapping():
    """Create name mapping file from our organized U11 data"""
    print("Creating U11 name mapping...")
    
    # Load our Arizona teams
    teams_df = pd.read_csv('data/master/u11_boys_2015/teams_by_state/arizona_teams.csv')
    print(f"Loaded {len(teams_df)} Arizona U11 teams")
    
    # Create name mapping (raw_name -> team_id, display_name)
    name_mapping = []
    
    for _, team in teams_df.iterrows():
        team_name = team['team_name']
        team_id = team['team_id']
        
        # Create mapping entry
        name_mapping.append({
            'raw_name': team_name,
            'team_id': team_id,
            'display_name': team_name
        })
    
    # Convert to DataFrame
    mapping_df = pd.DataFrame(name_mapping)
    
    # Save to expected location
    output_path = 'data/mappings/az_boys_u11_2025/name_map.csv'
    mapping_df.to_csv(output_path, index=False)
    
    print(f"Created name mapping for {len(mapping_df)} teams")
    print(f"Saved to: {output_path}")
    
    # Show sample
    print(f"\nSample name mapping:")
    print(mapping_df.head(3).to_string(index=False))
    
    return output_path

if __name__ == "__main__":
    create_u11_name_mapping()

