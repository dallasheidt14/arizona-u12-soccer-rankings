#!/usr/bin/env python3
"""
Incremental Alias Sync

Detects new team names and runs matcher only on unknowns.
Enables fast incremental updates with versioned tracking.

Usage:
    python scripts/incremental_alias_sync.py
"""

import pandas as pd
import os
import sys
from datetime import datetime
from typing import Set, List, Dict, Tuple

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Import our modules
from src.identity.alias_resolver import AliasResolver
from sophisticated_team_matcher import SophisticatedTeamMatcher

def load_existing_aliases(alias_csv_path: str) -> Set[str]:
    """
    Load existing alias names from the alias table.
    
    Args:
        alias_csv_path: Path to the alias table CSV
        
    Returns:
        Set of existing alias names (normalized)
    """
    if not os.path.exists(alias_csv_path):
        print(f"ℹ️  No existing alias table found at {alias_csv_path}")
        return set()
    
    try:
        df = pd.read_csv(alias_csv_path)
        if 'alias_name' in df.columns:
            aliases = set(df['alias_name'].tolist())
            print(f"✅ Loaded {len(aliases)} existing aliases")
            return aliases
        else:
            print("❌ No 'alias_name' column found in alias table")
            return set()
    except Exception as e:
        print(f"❌ Error loading existing aliases: {e}")
        return set()

def extract_team_names_from_games(games_csv_path: str) -> Set[str]:
    """
    Extract unique team names from game history.
    
    Args:
        games_csv_path: Path to the game history CSV
        
    Returns:
        Set of unique team names
    """
    if not os.path.exists(games_csv_path):
        print(f"❌ Game history not found: {games_csv_path}")
        return set()
    
    try:
        df = pd.read_csv(games_csv_path)
        
        # Clean column names
        df.columns = df.columns.str.strip()
        
        # Extract team names from Team A and Team B columns
        team_names = set()
        
        if 'Team A' in df.columns:
            team_names.update(df['Team A'].dropna().unique())
        if 'Team B' in df.columns:
            team_names.update(df['Team B'].dropna().unique())
        
        print(f"✅ Extracted {len(team_names)} unique team names from game history")
        return team_names
        
    except Exception as e:
        print(f"❌ Error extracting team names: {e}")
        return set()

def find_new_team_names(existing_aliases: Set[str], game_team_names: Set[str]) -> List[str]:
    """
    Find team names that are not in the existing alias cache.
    
    Args:
        existing_aliases: Set of existing alias names
        game_team_names: Set of team names from game history
        
    Returns:
        List of new team names to process
    """
    # Normalize existing aliases for comparison
    from src.identity.team_normalizer import normalize_team_name
    normalized_existing = {normalize_team_name(alias) for alias in existing_aliases}
    
    new_team_names = []
    for team_name in game_team_names:
        normalized_name = normalize_team_name(team_name)
        if normalized_name not in normalized_existing:
            new_team_names.append(team_name)
    
    print(f"🔍 Found {len(new_team_names)} new team names to process")
    return new_team_names

def process_new_team_names(new_team_names: List[str], master_df: pd.DataFrame) -> List[Dict[str, str]]:
    """
    Process new team names through the alias resolver.
    
    Args:
        new_team_names: List of new team names to process
        master_df: Master team list DataFrame
        
    Returns:
        List of new alias entries
    """
    if not new_team_names:
        return []
    
    print(f"🔄 Processing {len(new_team_names)} new team names...")
    
    # Initialize matcher and resolver
    matcher = SophisticatedTeamMatcher()
    resolver = AliasResolver(
        master_df=master_df,
        matcher=matcher,
        alias_csv_path='data/mappings/team_alias_table.csv',
        threshold=0.82,
        dry_run=False
    )
    
    new_aliases = []
    processed_count = 0
    
    for team_name in new_team_names:
        try:
            canonical_id, canonical_name = resolver.resolve(team_name)
            
            # Check if this was a new match
            if canonical_name != team_name:  # Match was found
                new_aliases.append({
                    'alias_name': team_name,
                    'canonical_team_id': canonical_id,
                    'canonical_team_name': canonical_name,
                    'confidence': 0.9,  # Default confidence for new matches
                    'processed_at': datetime.now().isoformat()
                })
            
            processed_count += 1
            if processed_count % 100 == 0:
                print(f"   Processed {processed_count}/{len(new_team_names)} team names...")
                
        except Exception as e:
            print(f"⚠️  Error processing '{team_name}': {e}")
            continue
    
    print(f"✅ Processed {processed_count} team names, found {len(new_aliases)} new matches")
    return new_aliases

def create_diff_log(new_aliases: List[Dict[str, str]], output_path: str):
    """
    Create a diff log of new aliases.
    
    Args:
        new_aliases: List of new alias entries
        output_path: Path to save the diff log
    """
    if not new_aliases:
        print("ℹ️  No new aliases to log")
        return
    
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Create diff log DataFrame
        diff_df = pd.DataFrame(new_aliases)
        diff_df['action'] = 'added'
        diff_df['timestamp'] = datetime.now().isoformat()
        
        # Save to CSV
        diff_df.to_csv(output_path, index=False)
        print(f"📝 Created diff log: {output_path}")
        
    except Exception as e:
        print(f"❌ Error creating diff log: {e}")

def update_alias_table(new_aliases: List[Dict[str, str]], alias_csv_path: str):
    """
    Update the main alias table with new aliases.
    
    Args:
        new_aliases: List of new alias entries
        alias_csv_path: Path to the main alias table
    """
    if not new_aliases:
        print("ℹ️  No new aliases to add")
        return
    
    try:
        # Load existing aliases
        existing_df = pd.DataFrame()
        if os.path.exists(alias_csv_path):
            existing_df = pd.read_csv(alias_csv_path)
        
        # Create new aliases DataFrame
        new_df = pd.DataFrame(new_aliases)
        
        # Combine and remove duplicates
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        combined_df = combined_df.drop_duplicates(subset=['alias_name'], keep='first')
        
        # Save updated alias table
        combined_df.to_csv(alias_csv_path, index=False)
        print(f"✅ Updated alias table with {len(new_aliases)} new aliases")
        
    except Exception as e:
        print(f"❌ Error updating alias table: {e}")

def main():
    """Main function for incremental alias sync."""
    print("=== INCREMENTAL ALIAS SYNC ===")
    
    # File paths
    alias_csv_path = "data/mappings/team_alias_table.csv"
    games_csv_path = "data/Game History u10 and u11.csv"
    master_u10_path = "data/input/National_Male_U10_Master_Team_List.csv"
    master_u11_path = "data/input/National_Male_U11_Master_Team_List.csv"
    
    # Load master team lists
    print("📂 Loading master team lists...")
    master_dfs = []
    
    for master_path in [master_u10_path, master_u11_path]:
        if os.path.exists(master_path):
            df = pd.read_csv(master_path)
            master_dfs.append(df)
            print(f"✅ Loaded {len(df)} teams from {os.path.basename(master_path)}")
        else:
            print(f"⚠️  Master list not found: {master_path}")
    
    if not master_dfs:
        print("❌ No master team lists found")
        return
    
    # Combine master lists
    combined_master_df = pd.concat(master_dfs, ignore_index=True)
    print(f"✅ Combined master list: {len(combined_master_df)} teams")
    
    # Load existing aliases
    existing_aliases = load_existing_aliases(alias_csv_path)
    
    # Extract team names from games
    game_team_names = extract_team_names_from_games(games_csv_path)
    
    # Find new team names
    new_team_names = find_new_team_names(existing_aliases, game_team_names)
    
    if not new_team_names:
        print("✅ No new team names found - alias table is up to date!")
        return
    
    # Process new team names
    new_aliases = process_new_team_names(new_team_names, combined_master_df)
    
    # Create diff log
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    diff_log_path = f"data/mappings/logs/alias_diff_{timestamp}.csv"
    create_diff_log(new_aliases, diff_log_path)
    
    # Update alias table
    update_alias_table(new_aliases, alias_csv_path)
    
    # Summary
    print(f"\n📊 Sync Summary:")
    print(f"   Existing aliases: {len(existing_aliases)}")
    print(f"   New team names processed: {len(new_team_names)}")
    print(f"   New aliases added: {len(new_aliases)}")
    print(f"   Diff log: {diff_log_path}")

if __name__ == "__main__":
    main()
