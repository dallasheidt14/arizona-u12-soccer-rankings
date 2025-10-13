#!/usr/bin/env python3
"""
Clean U11 master file to remove U9/U10 teams
"""
import pandas as pd
import re

def clean_u11_master():
    print("Cleaning U11 master file to remove U9/U10 teams...")
    
    # Load the current master file
    master_path = "data/master/U11 BOYS/AZ/AZ_teams.csv"
    df = pd.read_csv(master_path)
    
    print(f"Original teams: {len(df)}")
    
    # Filter out U9 and U10 teams
    # Keep teams that:
    # 1. Don't contain "U9" or "U10" in the name
    # 2. Are explicitly U11 teams
    # 3. Are 2015 birth year teams (which should be U11)
    
    def is_u11_team(team_name):
        if pd.isna(team_name):
            return False
        
        team_name_lower = team_name.lower()
        
        # Exclude U9 and U10 teams
        if 'u9' in team_name_lower or 'u10' in team_name_lower:
            return False
        
        # Include explicit U11 teams
        if 'u11' in team_name_lower:
            return True
        
        # Include 2015 birth year teams (U11 age group)
        if '2015' in team_name_lower:
            return True
        
        # Include teams that don't specify age (likely U11 based on context)
        # But exclude if they have other age indicators
        if any(age in team_name_lower for age in ['u8', 'u9', 'u10', 'u12', 'u13', 'u14', 'u15', 'u16', 'u17', 'u18']):
            return False
        
        # Default to include if no age indicators
        return True
    
    # Apply filter
    df_cleaned = df[df['team_name'].apply(is_u11_team)]
    
    print(f"Cleaned teams: {len(df_cleaned)}")
    print(f"Removed: {len(df) - len(df_cleaned)} teams")
    
    # Show what was removed
    removed = df[~df['team_name'].apply(is_u11_team)]
    if not removed.empty:
        print("\nRemoved teams:")
        for _, team in removed.iterrows():
            print(f"  - {team['team_name']}")
    
    # Save cleaned file
    df_cleaned.to_csv(master_path, index=False)
    print(f"\nCleaned master file saved to: {master_path}")
    
    # Verify age groups in cleaned file
    print("\nAge group analysis in cleaned file:")
    age_groups = df_cleaned['team_name'].str.extract(r'(U\d+)', expand=False).value_counts()
    print(age_groups)
    
    return True

if __name__ == "__main__":
    clean_u11_master()
