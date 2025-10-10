"""
Bootstrap team aliases from historical data
Creates team_aliases.json from existing Matched_Games.csv
"""

import pandas as pd
import json
from collections import defaultdict
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def bootstrap_aliases():
    """Create team aliases from historical match data."""
    
    # Load master team list
    master_path = Path("AZ MALE U12 MASTER TEAM LIST.csv")
    if not master_path.exists():
        logger.error("Master team list not found")
        return
    
    master_df = pd.read_csv(master_path)
    master_teams = set(master_df["Team Name"].str.strip().str.lower())
    
    # Load historical games
    games_path = Path("Matched_Games.csv")
    if not games_path.exists():
        logger.warning("No historical games found, creating empty aliases")
        aliases = {}
    else:
        games_df = pd.read_csv(games_path)
        
        # Collect all team names from games
        all_teams = set()
        for col in ["Team A", "Team B"]:
            all_teams.update(games_df[col].dropna().str.strip().str.lower())
        
        # Find potential aliases
        aliases = defaultdict(list)
        
        for game_team in all_teams:
            if not game_team:
                continue
                
            # Look for exact matches in master list
            if game_team in master_teams:
                continue
            
            # Look for partial matches
            potential_matches = []
            for master_team in master_teams:
                # Check if game_team is contained in master_team or vice versa
                if (game_team in master_team or master_team in game_team) and len(game_team) > 3:
                    potential_matches.append(master_team)
            
            if potential_matches:
                # Use the longest match (most specific)
                best_match = max(potential_matches, key=len)
                aliases[best_match].append(game_team)
    
    # Convert to regular dict and clean up
    aliases_dict = {}
    for master_team, variants in aliases.items():
        # Remove duplicates and sort
        unique_variants = sorted(list(set(variants)))
        if unique_variants:
            aliases_dict[master_team] = unique_variants
    
    # Save aliases
    aliases_path = Path("team_aliases.json")
    with aliases_path.open("w", encoding="utf-8") as f:
        json.dump(aliases_dict, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Created {len(aliases_dict)} team aliases in {aliases_path}")
    
    # Print summary
    total_variants = sum(len(variants) for variants in aliases_dict.values())
    logger.info(f"Total variants: {total_variants}")
    
    # Show some examples
    if aliases_dict:
        logger.info("Sample aliases:")
        for master_team, variants in list(aliases_dict.items())[:5]:
            logger.info(f"  {master_team}: {variants}")

if __name__ == "__main__":
    bootstrap_aliases()
