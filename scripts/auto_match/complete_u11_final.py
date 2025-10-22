#!/usr/bin/env python3
"""
Complete U11 Processing
======================

Process the remaining games as U11 data.
"""

import pandas as pd
import numpy as np
from fuzzywuzzy import fuzz, process
import re

def normalize_team_name(name):
    """Normalize team names for better matching."""
    if pd.isnull(name) or not isinstance(name, str):
        return ""
    
    name = name.lower()
    name = re.sub(r"[^a-z0-9 ]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name

def complete_u11_processing():
    """Complete U11 processing."""
    
    print("=== COMPLETING U11 PROCESSING ===")
    
    # Load your game history data
    input_file = r"data\Game History u10 and u11.csv"
    
    try:
        df = pd.read_csv(input_file)
        print(f"Loaded {len(df)} total games")
        
        # Clean column names
        df.columns = df.columns.str.strip()
        print(f"Columns: {list(df.columns)}")
        
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return
    
    # Load U10 national data to see what was already processed
    try:
        u10_df = pd.read_csv('data/input/National_Male_U10_Game_History_18_Months.csv')
        print(f"U10 National: {len(u10_df)} games already processed")
        
        # Get U10 game indices to exclude them
        # We'll use a different approach - process remaining games as U11
        remaining_count = len(df) - len(u10_df)
        print(f"Remaining games for U11: {remaining_count}")
        
    except FileNotFoundError:
        print("No U10 national data found")
        remaining_count = len(df)
    
    # Process remaining games as U11
    if remaining_count > 0:
        print(f"\n=== PROCESSING REMAINING GAMES AS U11 ===")
        # Take the last remaining_count games as U11
        u11_df = df.tail(remaining_count).copy()
        print(f"Processing {len(u11_df)} games as U11...")
        
        process_age_group_data(u11_df, 11)
    else:
        print("No remaining games to process")

def process_age_group_data(df, age_group):
    """Process data for a specific age group."""
    
    print(f"Processing {len(df)} games for U{age_group}...")
    
    # Load master team list
    master_file = f'data/input/National_Male_U{age_group}_Master_Team_List.csv'
    try:
        master_df = pd.read_csv(master_file)
        print(f"Loaded master team list: {len(master_df)} teams")
    except FileNotFoundError:
        print(f"❌ Master team list not found: {master_file}")
        return
    
    # Create matching dictionaries
    name_to_state = master_df.set_index('Team_Name')['State_Code'].to_dict()
    name_to_club = master_df.set_index('Team_Name')['Club'].to_dict()
    name_to_id = master_df.set_index('Team_Name')['GotSport_Team_ID'].to_dict()
    
    # Initialize new columns
    df['Team B State'] = ''
    df['Team B Club'] = ''
    df['Team B GotSport ID'] = ''
    df['Match Type'] = ''
    
    # Match each Team B
    print("Matching Team B data...")
    match_results = {'EXACT': 0, 'FUZZY': 0, 'NO_MATCH': 0, 'EMPTY': 0}
    
    for idx, row in df.iterrows():
        team_b_name = row['Team B']
        
        if pd.isnull(team_b_name) or not isinstance(team_b_name, str):
            df.at[idx, 'Match Type'] = 'EMPTY'
            match_results['EMPTY'] += 1
            continue
        
        # Try exact match first
        if team_b_name in name_to_state:
            df.at[idx, 'Team B State'] = name_to_state[team_b_name]
            df.at[idx, 'Team B Club'] = name_to_club[team_b_name]
            df.at[idx, 'Team B GotSport ID'] = name_to_id[team_b_name]
            df.at[idx, 'Match Type'] = 'EXACT'
            match_results['EXACT'] += 1
        else:
            # Try fuzzy matching
            match, score = process.extractOne(team_b_name, master_df['Team_Name'].tolist())
            if score >= 85:  # 85% similarity threshold
                df.at[idx, 'Team B State'] = name_to_state[match]
                df.at[idx, 'Team B Club'] = name_to_club[match]
                df.at[idx, 'Team B GotSport ID'] = name_to_id[match]
                df.at[idx, 'Match Type'] = f'FUZZY_{score}'
                match_results['FUZZY'] += 1
            else:
                df.at[idx, 'Match Type'] = 'NO_MATCH'
                match_results['NO_MATCH'] += 1
        
        if idx % 10000 == 0:
            print(f"Processed {idx}/{len(df)} games...")
    
    # Print results
    print(f"\n=== MATCHING RESULTS FOR U{age_group} ===")
    for match_type, count in match_results.items():
        percentage = (count / len(df)) * 100
        print(f"{match_type}: {count} games ({percentage:.1f}%)")
    
    # Save enhanced data
    output_file = f'U{age_group}_Enhanced.csv'
    df.to_csv(output_file, index=False)
    print(f"Saved enhanced data to {output_file}")
    
    # Show sample
    print(f"\n=== SAMPLE MATCHED DATA ===")
    sample_cols = ['Team A', 'Team B', 'Team A State', 'Team B State', 'Team A Club', 'Team B Club', 'Gotsport Team id # Team A', 'Team B GotSport ID', 'Match Type']
    available_cols = [col for col in sample_cols if col in df.columns]
    if available_cols:
        print(df[available_cols].head(10).to_string())
    
    # Convert to national format
    convert_to_national_format(df, age_group)

def convert_to_national_format(df, age_group):
    """Convert to national format."""
    
    print(f"Converting U{age_group} data to national format...")
    
    # Create national format
    national_df = pd.DataFrame({
        'Date': df['Date'],
        'Team A': df['Team A'],
        'Team B': df['Team B'],
        'Team A State': df['Team A State'],
        'Team B State': df['Team B State'],
        'Team A Division': f'U{age_group}B',
        'Team B Division': f'U{age_group}B',
        'Team A Club': df['Team A Club'],
        'Team B Club': df['Team B Club'],
        'Score A': df['Score A'],
        'Score B': df['Score B'],
        'Result A': df['Team A Result'],
        'Result B': '',
        'Event': df['Event'],
        'Competition': df['Event'],
        'Division': f'U{age_group}B U{age_group} Boys Elite',
        'Venue': df['Event'],
        'Location': '',
        'Match ID': range(2000000, 2000000 + len(df)),  # Different range for U11
        'Original Team A ID': df['Gotsport Team id # Team A'],
        'Original Team B ID': df['Team B GotSport ID'],
        'Cross_State': False,
        'Event_Type': 'League',
        'Venue_State': df['Team A State']
    })
    
    # Calculate Result B
    def calculate_result_b(result_a):
        if result_a == 'W':
            return 'L'
        elif result_a == 'L':
            return 'W'
        elif result_a == 'T':
            return 'T'
        else:
            return ''
    
    national_df['Result B'] = national_df['Result A'].apply(calculate_result_b)
    national_df['Cross_State'] = national_df['Team A State'] != national_df['Team B State']
    
    # Save national format
    output_file = f'data/input/National_Male_U{age_group}_Game_History_18_Months.csv'
    national_df.to_csv(output_file, index=False)
    print(f"✅ Saved national format to {output_file}")
    
    return national_df

if __name__ == "__main__":
    complete_u11_processing()
