#!/usr/bin/env python3
"""
Human Feedback Integration Script

Merges manually approved aliases from review CSV into the main alias table.
This enables human-in-the-loop oversight for borderline matches (0.7-0.9 confidence).

Usage:
1. Review unmatched_teams_*.csv files in data/mappings/review/
2. Create approved_aliases.csv with approved matches
3. Run: python scripts/merge_reviewed_aliases.py
"""

import pandas as pd
import os
import sys
from datetime import datetime
from typing import List, Dict

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

def load_approved_aliases(approved_csv_path: str) -> pd.DataFrame:
    """
    Load approved aliases from CSV file.
    
    Expected CSV format:
    alias_name,canonical_team_id,canonical_team_name,confidence,notes
    """
    if not os.path.exists(approved_csv_path):
        print(f"❌ Approved aliases file not found: {approved_csv_path}")
        print("Please create this file with approved matches.")
        return pd.DataFrame()
    
    try:
        df = pd.read_csv(approved_csv_path)
        required_columns = ['alias_name', 'canonical_team_id', 'canonical_team_name', 'confidence']
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            print(f"❌ Missing required columns: {missing_columns}")
            print(f"Required columns: {required_columns}")
            return pd.DataFrame()
        
        print(f"✅ Loaded {len(df)} approved aliases from {approved_csv_path}")
        return df
        
    except Exception as e:
        print(f"❌ Error loading approved aliases: {e}")
        return pd.DataFrame()

def load_existing_aliases(alias_csv_path: str) -> pd.DataFrame:
    """Load existing alias table."""
    if not os.path.exists(alias_csv_path):
        print(f"ℹ️  No existing alias table found at {alias_csv_path}")
        return pd.DataFrame()
    
    try:
        df = pd.read_csv(alias_csv_path)
        print(f"✅ Loaded {len(df)} existing aliases from {alias_csv_path}")
        return df
    except Exception as e:
        print(f"❌ Error loading existing aliases: {e}")
        return pd.DataFrame()

def merge_aliases(existing_df: pd.DataFrame, approved_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge approved aliases with existing aliases, avoiding duplicates.
    """
    if existing_df.empty:
        # No existing aliases, use approved as-is
        merged_df = approved_df.copy()
    else:
        # Merge and remove duplicates
        merged_df = pd.concat([existing_df, approved_df], ignore_index=True)
        
        # Remove duplicates based on alias_name (keep first occurrence)
        merged_df = merged_df.drop_duplicates(subset=['alias_name'], keep='first')
    
    return merged_df

def create_backup(alias_csv_path: str) -> str:
    """Create backup of existing alias table."""
    if not os.path.exists(alias_csv_path):
        return ""
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"{alias_csv_path}.backup_{timestamp}"
    
    try:
        import shutil
        shutil.copy2(alias_csv_path, backup_path)
        print(f"✅ Created backup: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"⚠️  Could not create backup: {e}")
        return ""

def save_merged_aliases(merged_df: pd.DataFrame, alias_csv_path: str):
    """Save merged aliases to CSV."""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(alias_csv_path), exist_ok=True)
        
        # Add timestamp column
        merged_df['last_updated'] = datetime.now().isoformat()
        
        # Save to CSV
        merged_df.to_csv(alias_csv_path, index=False)
        print(f"✅ Saved {len(merged_df)} aliases to {alias_csv_path}")
        
    except Exception as e:
        print(f"❌ Error saving merged aliases: {e}")
        raise

def create_merge_log(approved_df: pd.DataFrame, backup_path: str):
    """Create a log of the merge operation."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_path = f"data/mappings/logs/merge_operation_{timestamp}.csv"
    
    try:
        # Ensure log directory exists
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        
        # Create log entry
        log_df = approved_df.copy()
        log_df['merge_timestamp'] = datetime.now().isoformat()
        log_df['backup_file'] = backup_path
        
        log_df.to_csv(log_path, index=False)
        print(f"✅ Created merge log: {log_path}")
        
    except Exception as e:
        print(f"⚠️  Could not create merge log: {e}")

def main():
    """Main function for merging reviewed aliases."""
    print("=== HUMAN FEEDBACK INTEGRATION: MERGE REVIEWED ALIASES ===")
    
    # File paths
    approved_csv_path = "data/mappings/review/approved_aliases.csv"
    alias_csv_path = "data/mappings/team_alias_table.csv"
    
    # Load approved aliases
    approved_df = load_approved_aliases(approved_csv_path)
    if approved_df.empty:
        print("\n📋 To use this script:")
        print("1. Review unmatched_teams_*.csv files in data/mappings/review/")
        print("2. Create approved_aliases.csv with approved matches")
        print("3. Run this script again")
        return
    
    # Load existing aliases
    existing_df = load_existing_aliases(alias_csv_path)
    
    # Create backup
    backup_path = create_backup(alias_csv_path)
    
    # Merge aliases
    print("\n🔄 Merging aliases...")
    merged_df = merge_aliases(existing_df, approved_df)
    
    # Show merge statistics
    print(f"\n📊 Merge Statistics:")
    print(f"   Existing aliases: {len(existing_df)}")
    print(f"   Approved aliases: {len(approved_df)}")
    print(f"   Total after merge: {len(merged_df)}")
    print(f"   New aliases added: {len(merged_df) - len(existing_df)}")
    
    # Save merged aliases
    save_merged_aliases(merged_df, alias_csv_path)
    
    # Create merge log
    create_merge_log(approved_df, backup_path)
    
    print(f"\n✅ Successfully merged {len(approved_df)} approved aliases!")
    print(f"📁 Main alias table: {alias_csv_path}")
    if backup_path:
        print(f"💾 Backup created: {backup_path}")

if __name__ == "__main__":
    main()
