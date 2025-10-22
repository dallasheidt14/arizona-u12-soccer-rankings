#!/usr/bin/env python3
"""
Ready-to-Use Auto-Match Script
==============================

Run this script to automatically add Team B State, Club, and GotSport ID
by matching against your master team lists.

USAGE:
1. Put your U10 data in 'u10_data.csv'
2. Put your U11 data in 'u11_data.csv'  
3. Run: python ready_auto_match.py
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

def auto_match_team_b(input_file, age_group):
    """Automatically match Team B data."""
    
    print(f"Processing {input_file} for U{age_group}...")
    
    # Load your game history data
    df = pd.read_csv(input_file)
    print(f"Loaded {len(df)} games")
    print(f"Columns: {list(df.columns)}")
    
    # Load master team list
    master_file = f'data/input/National_Male_U{age_group}_Master_Team_List.csv'
    try:
        master_df = pd.read_csv(master_file)
        print(f"Loaded master team list: {len(master_df)} teams")
    except FileNotFoundError:
        print(f"Master team list not found: {master_file}")
        return None
    
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
        team_b_name = row['team b']
        
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
        
        if idx % 1000 == 0:
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
    sample_cols = ['team a', 'team b', 'Team A State', 'Team B State', 'Team A Club', 'Team B Club', 'gotsport id team a', 'Team B GotSport ID', 'Match Type']
    available_cols = [col for col in sample_cols if col in df.columns]
    print(df[available_cols].head(10).to_string())
    
    return df

def convert_to_national_format(enhanced_file, age_group):
    """Convert to national format."""
    
    print(f"Converting {enhanced_file} to national format...")
    
    df = pd.read_csv(enhanced_file)
    
    # Create national format
    national_df = pd.DataFrame({
        'Date': df.iloc[:, 0],  # Column A (Date)
        'Team A': df['team a'],
        'Team B': df['team b'],
        'Team A State': df['Team A State'],
        'Team B State': df['Team B State'],
        'Team A Division': f'U{age_group}B',
        'Team B Division': f'U{age_group}B',
        'Team A Club': df['team a club'],
        'Team B Club': df['Team B Club'],
        'Score A': df['score A'],
        'Score B': df['Score B'],
        'Result A': df['Team A Result'],
        'Result B': '',
        'Event': df['event'],
        'Competition': df['event'],
        'Division': f'U{age_group}B U{age_group} Boys Elite',
        'Venue': df['event'],
        'Location': '',
        'Match ID': range(1000000, 1000000 + len(df)),
        'Original Team A ID': df['gotsport id team a'],
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
    print(f"Saved national format to {output_file}")
    
    return national_df

def main():
    """Main function to process U10 and U11 data."""
    
    print("=== AUTO-MATCH TEAM B DATA ===")
    print("This script will automatically add Team B State, Club, and GotSport ID")
    print("by matching against your master team lists.")
    
    # Process U10 data
    print("\n=== PROCESSING U10 DATA ===")
    try:
        u10_enhanced = auto_match_team_b('u10_data.csv', 10)
        if u10_enhanced is not None:
            u10_national = convert_to_national_format('U10_Enhanced.csv', 10)
            print("✅ U10 data processed successfully!")
    except FileNotFoundError:
        print("❌ u10_data.csv not found - skipping U10")
    except Exception as e:
        print(f"❌ Error processing U10 data: {e}")
    
    # Process U11 data
    print("\n=== PROCESSING U11 DATA ===")
    try:
        u11_enhanced = auto_match_team_b('u11_data.csv', 11)
        if u11_enhanced is not None:
            u11_national = convert_to_national_format('U11_Enhanced.csv', 11)
            print("✅ U11 data processed successfully!")
    except FileNotFoundError:
        print("❌ u11_data.csv not found - skipping U11")
    except Exception as e:
        print(f"❌ Error processing U11 data: {e}")
    
    print("\n=== COMPLETE ===")
    print("Team B data has been automatically matched and converted to national format!")
    print("\nOutput files created:")
    print("- U10_Enhanced.csv (enhanced U10 data)")
    print("- U11_Enhanced.csv (enhanced U11 data)")
    print("- data/input/National_Male_U10_Game_History_18_Months.csv")
    print("- data/input/National_Male_U11_Game_History_18_Months.csv")

if __name__ == "__main__":
    main()
