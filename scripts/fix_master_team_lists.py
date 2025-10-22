#!/usr/bin/env python3
"""
Fix Master Team Lists with Correct Age Groups
============================================

This script fixes the master team lists to have the correct age groups:
- U10: Birth year 2016, Age_U = 10
- U11: Birth year 2015, Age_U = 11  
- U12: Birth year 2014, Age_U = 12

Current issue: Age groups are shifted by one year.
"""

import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

class MasterTeamListFixer:
    """Fix master team lists with correct age groups."""
    
    def __init__(self):
        self.project_root = os.path.dirname(os.path.dirname(__file__))
        self.input_dir = os.path.join(self.project_root, "data", "input")
        self.output_dir = os.path.join(self.project_root, "data", "input", "corrected")
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
    def load_current_lists(self):
        """Load current master team lists."""
        print("=== LOADING CURRENT MASTER TEAM LISTS ===")
        
        # Load current lists
        self.u10_current = pd.read_csv(os.path.join(self.input_dir, "National_Male_U10_Master_Team_List.csv"))
        self.u11_current = pd.read_csv(os.path.join(self.input_dir, "National_Male_U11_Master_Team_List.csv"))
        
        print(f"Current 'U10' list: {len(self.u10_current)} teams (Age_Group: {self.u10_current['Age_Group'].iloc[0]})")
        print(f"Current 'U11' list: {len(self.u11_current)} teams (Age_Group: {self.u11_current['Age_Group'].iloc[0]})")
        
        return self.u10_current, self.u11_current
    
    def analyze_age_groups(self):
        """Analyze current age group assignments."""
        print("\n=== ANALYZING CURRENT AGE GROUPS ===")
        
        print("Current 'U10' list:")
        print(f"  Age_Group: {self.u10_current['Age_Group'].unique()}")
        print(f"  Age_U: {self.u10_current['Age_U'].unique()}")
        print(f"  Total teams: {len(self.u10_current)}")
        
        print("\nCurrent 'U11' list:")
        print(f"  Age_Group: {self.u11_current['Age_Group'].unique()}")
        print(f"  Age_U: {self.u11_current['Age_U'].unique()}")
        print(f"  Total teams: {len(self.u11_current)}")
        
        print("\n=== CORRECT AGE GROUPS SHOULD BE ===")
        print("U10: Birth year 2016, Age_U = 10")
        print("U11: Birth year 2015, Age_U = 11")
        print("U12: Birth year 2014, Age_U = 12")
        
    def create_corrected_lists(self):
        """Create corrected master team lists."""
        print("\n=== CREATING CORRECTED MASTER TEAM LISTS ===")
        
        # Current 'U10' list (Age_Group=2015) should become U11 list (Age_Group=2015)
        u11_corrected = self.u10_current.copy()
        u11_corrected['Age_U'] = 11  # Fix Age_U from 10 to 11
        print(f"Created U11 corrected list: {len(u11_corrected)} teams (Age_Group: 2015, Age_U: 11)")
        
        # Current 'U11' list (Age_Group=2014) should become U12 list (Age_Group=2014)
        u12_corrected = self.u11_current.copy()
        u12_corrected['Age_U'] = 12  # Fix Age_U from 11 to 12
        print(f"Created U12 corrected list: {len(u12_corrected)} teams (Age_Group: 2014, Age_U: 12)")
        
        # For U10, we need to find teams with birth year 2016
        # This is trickier since we don't have a direct source
        # We'll need to create a proper U10 list from the game data
        
        print("\n=== CREATING PROPER U10 LIST ===")
        u10_corrected = self.create_u10_from_game_data()
        
        return u10_corrected, u11_corrected, u12_corrected
    
    def create_u10_from_game_data(self):
        """Create proper U10 master list from game data."""
        print("Creating U10 master list from game data...")
        
        # Load game data
        games_file = os.path.join(self.project_root, "data", "processed", "national", "National_Male_U10_Game_History_18_Months.csv")
        games_df = pd.read_csv(games_file)
        
        # Get all unique teams from games
        all_teams = set(games_df['Team A'].unique()) | set(games_df['Team B'].unique())
        print(f"Found {len(all_teams)} unique teams in game data")
        
        # Filter for teams that appear to be U10 (2016 birth year)
        # Look for teams with "2016" in their name
        u10_teams = []
        for team in all_teams:
            if '2016' in str(team).lower():
                u10_teams.append(team)
        
        print(f"Found {len(u10_teams)} teams with '2016' in name")
        
        # Create U10 master list
        u10_master = []
        for team in u10_teams:
            # Try to get state from existing master lists
            state_code = 'Unknown'
            club = 'Unknown'
            gotsport_id = None
            
            # Check in current lists
            for _, row in self.u10_current.iterrows():
                if row['Team_Name'] == team:
                    state_code = row['State_Code']
                    club = row['Club']
                    gotsport_id = row['GotSport_Team_ID']
                    break
            
            u10_master.append({
                'Team_Name': team,
                'Club': club,
                'State': 'Unknown',
                'State_Code': state_code,
                'Region': 'Unknown',
                'Division': 'U10B',
                'Age_Group': 2016,  # Correct birth year for U10
                'Age_U': 10,        # Correct age
                'Gender': 'M',
                'Gender_Full': 'Male',
                'League': 'USYS',
                'Active_Status': 'Active',
                'GotSport_Team_ID': gotsport_id,
                'Team_ID': f"u10_{hash(team) % 1000000:06d}",
                'Source_URL': 'Generated from game data'
            })
        
        u10_df = pd.DataFrame(u10_master)
        print(f"Created U10 master list: {len(u10_df)} teams (Age_Group: 2016, Age_U: 10)")
        
        return u10_df
    
    def save_corrected_lists(self, u10_df, u11_df, u12_df):
        """Save corrected master team lists."""
        print("\n=== SAVING CORRECTED MASTER TEAM LISTS ===")
        
        # Save U10 corrected
        u10_file = os.path.join(self.output_dir, "National_Male_U10_Master_Team_List_CORRECTED.csv")
        u10_df.to_csv(u10_file, index=False)
        print(f"Saved U10 corrected: {u10_file}")
        
        # Save U11 corrected
        u11_file = os.path.join(self.output_dir, "National_Male_U11_Master_Team_List_CORRECTED.csv")
        u11_df.to_csv(u11_file, index=False)
        print(f"Saved U11 corrected: {u11_file}")
        
        # Save U12 corrected
        u12_file = os.path.join(self.output_dir, "National_Male_U12_Master_Team_List_CORRECTED.csv")
        u12_df.to_csv(u12_file, index=False)
        print(f"Saved U12 corrected: {u12_file}")
        
        return u10_file, u11_file, u12_file
    
    def generate_summary_report(self, u10_df, u11_df, u12_df):
        """Generate summary report of corrected lists."""
        print("\n=== GENERATING SUMMARY REPORT ===")
        
        report = []
        report.append("CORRECTED MASTER TEAM LISTS SUMMARY")
        report.append("=" * 50)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # U10 summary
        report.append("U10 MASTER TEAM LIST (Birth Year 2016):")
        report.append(f"  Total teams: {len(u10_df)}")
        report.append(f"  Age_Group: {u10_df['Age_Group'].unique()}")
        report.append(f"  Age_U: {u10_df['Age_U'].unique()}")
        
        # State breakdown for U10
        state_counts = u10_df['State_Code'].value_counts().head(10)
        report.append("  Top 10 states:")
        for state, count in state_counts.items():
            report.append(f"    {state}: {count} teams")
        report.append("")
        
        # U11 summary
        report.append("U11 MASTER TEAM LIST (Birth Year 2015):")
        report.append(f"  Total teams: {len(u11_df)}")
        report.append(f"  Age_Group: {u11_df['Age_Group'].unique()}")
        report.append(f"  Age_U: {u11_df['Age_U'].unique()}")
        
        # State breakdown for U11
        state_counts = u11_df['State_Code'].value_counts().head(10)
        report.append("  Top 10 states:")
        for state, count in state_counts.items():
            report.append(f"    {state}: {count} teams")
        report.append("")
        
        # U12 summary
        report.append("U12 MASTER TEAM LIST (Birth Year 2014):")
        report.append(f"  Total teams: {len(u12_df)}")
        report.append(f"  Age_Group: {u12_df['Age_Group'].unique()}")
        report.append(f"  Age_U: {u12_df['Age_U'].unique()}")
        
        # State breakdown for U12
        state_counts = u12_df['State_Code'].value_counts().head(10)
        report.append("  Top 10 states:")
        for state, count in state_counts.items():
            report.append(f"    {state}: {count} teams")
        report.append("")
        
        # Arizona specific
        az_u10 = u10_df[u10_df['State_Code'] == 'AZ']
        az_u11 = u11_df[u11_df['State_Code'] == 'AZ']
        az_u12 = u12_df[u12_df['State_Code'] == 'AZ']
        
        report.append("ARIZONA TEAMS:")
        report.append(f"  U10: {len(az_u10)} teams")
        report.append(f"  U11: {len(az_u11)} teams")
        report.append(f"  U12: {len(az_u12)} teams")
        
        # Save report
        report_file = os.path.join(self.output_dir, "Master_Team_Lists_Correction_Summary.txt")
        with open(report_file, 'w') as f:
            f.write('\n'.join(report))
        
        print(f"Saved summary report: {report_file}")
        
        # Print to console
        print('\n'.join(report))
        
        return report_file
    
    def run(self):
        """Run the complete master team list correction."""
        print("=" * 60)
        print("MASTER TEAM LISTS CORRECTION")
        print("=" * 60)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # Load current lists
            self.load_current_lists()
            
            # Analyze age groups
            self.analyze_age_groups()
            
            # Create corrected lists
            u10_corrected, u11_corrected, u12_corrected = self.create_corrected_lists()
            
            # Save corrected lists
            self.save_corrected_lists(u10_corrected, u11_corrected, u12_corrected)
            
            # Generate summary report
            self.generate_summary_report(u10_corrected, u11_corrected, u12_corrected)
            
            print(f"\n{'='*60}")
            print("MASTER TEAM LISTS CORRECTION COMPLETE")
            print(f"{'='*60}")
            print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            return u10_corrected, u11_corrected, u12_corrected
            
        except Exception as e:
            print(f"❌ Error during correction: {e}")
            raise

def main():
    """Main function."""
    fixer = MasterTeamListFixer()
    u10, u11, u12 = fixer.run()
    return u10, u11, u12

if __name__ == "__main__":
    main()
