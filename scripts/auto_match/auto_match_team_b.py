#!/usr/bin/env python3
"""
Auto-Match Team B Data Script
============================

This script automatically adds Team B State, Club, and GotSport ID
by matching against master team lists.

USAGE:
    python scripts/auto_match/auto_match_team_b.py

INPUT FILES:
    - data/Game History u10 and u11.csv (your original data)
    - data/input/National_Male_U10_Master_Team_List.csv
    - data/input/National_Male_U11_Master_Team_List.csv

OUTPUT FILES:
    - data/processed/u10/U10_Enhanced.csv
    - data/processed/u11/U11_Enhanced.csv
    - data/processed/national/National_Male_U10_Game_History_18_Months.csv
    - data/processed/national/National_Male_U11_Game_History_18_Months.csv
"""

import pandas as pd
import numpy as np
import os
import sys
from fuzzywuzzy import fuzz, process
import re
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

class TeamBMatcher:
    """Auto-match Team B data against master team lists."""
    
    def __init__(self):
        self.project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.input_file = os.path.join(self.project_root, "data", "Game History u10 and u11.csv")
        self.u10_master = os.path.join(self.project_root, "data", "input", "National_Male_U10_Master_Team_List.csv")
        self.u11_master = os.path.join(self.project_root, "data", "input", "National_Male_U11_Master_Team_List.csv")
        
        # Output directories
        self.u10_enhanced_dir = os.path.join(self.project_root, "data", "processed", "u10")
        self.u11_enhanced_dir = os.path.join(self.project_root, "data", "processed", "u11")
        self.national_dir = os.path.join(self.project_root, "data", "processed", "national")
        
        # Ensure output directories exist
        os.makedirs(self.u10_enhanced_dir, exist_ok=True)
        os.makedirs(self.u11_enhanced_dir, exist_ok=True)
        os.makedirs(self.national_dir, exist_ok=True)
    
    def normalize_team_name(self, name):
        """Normalize team names for better matching."""
        if pd.isnull(name) or not isinstance(name, str):
            return ""
        
        name = name.lower()
        name = re.sub(r"[^a-z0-9 ]", "", name)
        name = re.sub(r"\s+", " ", name).strip()
        return name
    
    def load_data(self):
        """Load input data and master team lists."""
        print("=== LOADING DATA ===")
        
        # Load game history data
        if not os.path.exists(self.input_file):
            raise FileNotFoundError(f"Input file not found: {self.input_file}")
        
        df = pd.read_csv(self.input_file)
        df.columns = df.columns.str.strip()  # Clean column names
        print(f"Loaded {len(df)} total games")
        print(f"Columns: {list(df.columns)}")
        
        # Load master team lists
        u10_master_df = pd.read_csv(self.u10_master)
        u11_master_df = pd.read_csv(self.u11_master)
        
        print(f"U10 Master: {len(u10_master_df)} teams")
        print(f"U11 Master: {len(u11_master_df)} teams")
        
        return df, u10_master_df, u11_master_df
    
    def identify_age_groups(self, df):
        """Identify U10 vs U11 games."""
        print("\n=== IDENTIFYING AGE GROUPS ===")
        
        u10_games = []
        u11_games = []
        
        for idx, row in df.iterrows():
            team_a = str(row['Team A']).lower()
            team_b = str(row['Team B']).lower()
            
            # Check for U10 indicators (2015 birth year)
            if '2015' in team_a or '2015' in team_b or 'u10' in team_a or 'u10' in team_b:
                u10_games.append(idx)
            # Check for U11 indicators (2014 birth year)
            elif '2014' in team_a or '2014' in team_b or 'u11' in team_a or 'u11' in team_b:
                u11_games.append(idx)
            # Default to U11 if no clear indicator
            else:
                u11_games.append(idx)
        
        print(f"Detected U10 games: {len(u10_games)}")
        print(f"Detected U11 games: {len(u11_games)}")
        
        return u10_games, u11_games
    
    def match_team_b_data(self, df, master_df, age_group):
        """Match Team B data against master team list."""
        print(f"\n=== MATCHING U{age_group} TEAM B DATA ===")
        
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
        
        return df, match_results
    
    def save_enhanced_data(self, df, age_group):
        """Save enhanced data with Team B information."""
        output_file = os.path.join(
            self.project_root, "data", "processed", f"u{age_group}", f"U{age_group}_Enhanced.csv"
        )
        df.to_csv(output_file, index=False)
        print(f"Saved enhanced data to {output_file}")
        return output_file
    
    def convert_to_national_format(self, df, age_group):
        """Convert to national format ready for rankings."""
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
            'Match ID': range(1000000 + (age_group - 10) * 1000000, 
                             1000000 + (age_group - 10) * 1000000 + len(df)),
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
        output_file = os.path.join(
            self.national_dir, f"National_Male_U{age_group}_Game_History_18_Months.csv"
        )
        national_df.to_csv(output_file, index=False)
        print(f"✅ Saved national format to {output_file}")
        
        return national_df, output_file
    
    def show_sample_results(self, df, age_group):
        """Show sample of matched results."""
        print(f"\n=== SAMPLE U{age_group} MATCHED DATA ===")
        sample_cols = ['Team A', 'Team B', 'Team A State', 'Team B State', 
                      'Team A Club', 'Team B Club', 'Gotsport Team id # Team A', 
                      'Team B GotSport ID', 'Match Type']
        available_cols = [col for col in sample_cols if col in df.columns]
        if available_cols:
            print(df[available_cols].head(10).to_string())
    
    def process_age_group(self, df, master_df, age_group):
        """Process a specific age group."""
        print(f"\n{'='*50}")
        print(f"PROCESSING U{age_group} DATA")
        print(f"{'='*50}")
        
        # Match Team B data
        df_matched, match_results = self.match_team_b_data(df, master_df, age_group)
        
        # Save enhanced data
        enhanced_file = self.save_enhanced_data(df_matched, age_group)
        
        # Show sample results
        self.show_sample_results(df_matched, age_group)
        
        # Convert to national format
        national_df, national_file = self.convert_to_national_format(df_matched, age_group)
        
        return {
            'enhanced_file': enhanced_file,
            'national_file': national_file,
            'match_results': match_results,
            'total_games': len(df_matched)
        }
    
    def run(self):
        """Run the complete auto-matching process."""
        print("=" * 60)
        print("AUTO-MATCH TEAM B DATA PROCESSING")
        print("=" * 60)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # Load data
            df, u10_master_df, u11_master_df = self.load_data()
            
            # Identify age groups
            u10_games, u11_games = self.identify_age_groups(df)
            
            results = {}
            
            # Process U10 data
            if u10_games:
                u10_df = df.iloc[u10_games].copy()
                results['U10'] = self.process_age_group(u10_df, u10_master_df, 10)
            
            # Process U11 data
            if u11_games:
                u11_df = df.iloc[u11_games].copy()
                results['U11'] = self.process_age_group(u11_df, u11_master_df, 11)
            
            # Summary
            print(f"\n{'='*60}")
            print("PROCESSING COMPLETE")
            print(f"{'='*60}")
            print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            for age_group, result in results.items():
                print(f"\n{age_group} Results:")
                print(f"  Total Games: {result['total_games']:,}")
                print(f"  Enhanced File: {result['enhanced_file']}")
                print(f"  National File: {result['national_file']}")
                print(f"  Match Results: {result['match_results']}")
            
            print(f"\n✅ All files saved to organized directory structure")
            print(f"✅ Ready for V5.3E Enhanced rankings")
            
            return results
            
        except Exception as e:
            print(f"❌ Error during processing: {e}")
            raise

def main():
    """Main function."""
    matcher = TeamBMatcher()
    results = matcher.run()
    return results

if __name__ == "__main__":
    main()
