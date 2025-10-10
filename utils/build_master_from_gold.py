"""
Build Master Team List from Gold Data
Rebuilds master team lists from gold layer data when bronze data is corrupted.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_teams_from_gold(gold_path: str) -> pd.DataFrame:
    """Extract unique teams from gold games data."""
    logger.info(f"Reading gold data from {gold_path}")
    
    try:
        gold = pd.read_csv(gold_path)
        logger.info(f"Loaded {len(gold)} games from gold data")
        
        # Extract teams from both Team A and Team B columns
        teams_a = gold["Team A"].dropna().astype(str).str.strip()
        teams_b = gold["Team B"].dropna().astype(str).str.strip()
        
        # Combine and get unique teams
        all_teams = pd.concat([teams_a, teams_b]).unique()
        logger.info(f"Found {len(all_teams)} unique teams")
        
        # Create master DataFrame
        master = pd.DataFrame({
            "Team": sorted(all_teams),
            "Club": ""  # Empty club column for now
        })
        
        return master
        
    except Exception as e:
        logger.error(f"Failed to extract teams from {gold_path}: {e}")
        raise

def build_u11_master_from_gold():
    """Build U11 master team list from gold data."""
    logger.info("🏆 Building U11 master team list from gold data")
    
    # Try different gold file paths
    gold_paths = [
        "gold/Matched_Games_AZ_BOYS_U11.csv",
        "gold/Matched_Games_U11.csv"
    ]
    
    gold_path = None
    for path in gold_paths:
        if Path(path).exists():
            gold_path = path
            break
    
    if not gold_path:
        raise FileNotFoundError(f"No U11 gold data found. Checked: {gold_paths}")
    
    # Extract teams
    master = extract_teams_from_gold(gold_path)
    
    # Save master team list
    output_path = "AZ MALE u11 MASTER TEAM LIST.csv"
    master.to_csv(output_path, index=False)
    logger.info(f"✅ Saved U11 master team list to {output_path}")
    
    # Show sample
    logger.info(f"Sample U11 teams ({len(master)} total):")
    for i, team in enumerate(master["Team"].head(10)):
        logger.info(f"  {i+1}. {team}")
    
    return master

def build_u12_master_from_gold():
    """Build U12 master team list from gold data (for comparison)."""
    logger.info("🏆 Building U12 master team list from gold data")
    
    gold_paths = [
        "gold/Matched_Games_AZ_BOYS_U12.csv",
        "gold/Matched_Games_U12.csv"
    ]
    
    gold_path = None
    for path in gold_paths:
        if Path(path).exists():
            gold_path = path
            break
    
    if not gold_path:
        raise FileNotFoundError(f"No U12 gold data found. Checked: {gold_paths}")
    
    # Extract teams
    master = extract_teams_from_gold(gold_path)
    
    # Save master team list
    output_path = "AZ MALE U12 MASTER TEAM LIST.csv"
    master.to_csv(output_path, index=False)
    logger.info(f"✅ Saved U12 master team list to {output_path}")
    
    return master

def main():
    """Main function to rebuild master lists."""
    try:
        # Build U11 master
        u11_master = build_u11_master_from_gold()
        
        # Build U12 master for comparison
        try:
            u12_master = build_u12_master_from_gold()
            logger.info(f"U12 master has {len(u12_master)} teams")
        except FileNotFoundError:
            logger.warning("U12 gold data not found, skipping U12 master rebuild")
        
        logger.info("🎉 Master team list rebuild complete!")
        
    except Exception as e:
        logger.error(f"❌ Failed to rebuild master lists: {e}")
        raise

if __name__ == "__main__":
    main()