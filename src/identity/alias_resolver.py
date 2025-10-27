"""
Canonical Team Alias System v1

A persistent CSV-based alias table that caches sophisticated matching results.
First run performs full matching (~30-60 min), subsequent runs use cached aliases (~5 min).

Architecture:
- AliasResolver: O(1) lookups for known teams, delegates to SophisticatedTeamMatcher for unknowns
- Two-tier matching: Fast alias cache → precise 5-field sophisticated matching fallback
- Persistent storage: data/mappings/team_alias_table.csv with confidence scores
- Audit trail: Delta logs in data/mappings/logs/alias_additions_YYYYMMDD_HHMMSS.csv
"""

import pandas as pd
import os
from datetime import datetime
from typing import Tuple, Optional, Dict, Any, List
import logging

# Import the sophisticated matcher and new modules
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from sophisticated_team_matcher import SophisticatedTeamMatcher
from src.identity.team_normalizer import normalize_team_name
from src.identity.hybrid_matcher import HybridMatcher

class AliasResolver:
    """
    Resolves team name aliases using a persistent CSV cache with fallback to sophisticated matching.
    
    Features:
    - O(1) lookups for known teams via normalized dict
    - Fallback to SophisticatedTeamMatcher for unknown teams
    - Staging of new aliases during run, flush at end with delta logging
    - Dry-run mode for auditing before committing
    """
    
    def __init__(self, 
                 master_df: pd.DataFrame,
                 matcher: SophisticatedTeamMatcher,
                 alias_csv_path: str = 'data/mappings/team_alias_table.csv',
                 threshold: float = 0.82,
                 dry_run: bool = False):
        """
        Initialize the AliasResolver.
        
        Args:
            master_df: Master team list DataFrame with team_id and Team_Name columns
            matcher: SophisticatedTeamMatcher instance for fallback matching
            alias_csv_path: Path to the persistent alias CSV file
            threshold: Minimum confidence threshold for alias matching
            dry_run: If True, don't persist changes (for auditing)
        """
        self.master_df = master_df
        self.matcher = matcher
        self.alias_csv_path = alias_csv_path
        self.threshold = threshold
        self.dry_run = dry_run
        
        # Initialize hybrid matcher for fallback
        self.hybrid_matcher = HybridMatcher(threshold=0.7)
        
        # Initialize alias cache
        self.alias_cache: Dict[str, Tuple[str, str, float]] = {}  # normalized_name -> (team_id, team_name, confidence)
        self.new_aliases: Dict[str, Tuple[str, str, float]] = {}  # staged new aliases
        self.unmatched_teams: List[Dict[str, str]] = []  # for review logging
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Load existing aliases
        self._load_aliases()
        
    def _load_aliases(self):
        """Load existing aliases from CSV file."""
        if os.path.exists(self.alias_csv_path):
            try:
                alias_df = pd.read_csv(self.alias_csv_path)
                for _, row in alias_df.iterrows():
                    normalized_name = row['alias_name'].lower().strip()
                    self.alias_cache[normalized_name] = (
                        row['canonical_team_id'],
                        row['canonical_team_name'],
                        row['confidence']
                    )
                self.logger.info(f"Loaded {len(self.alias_cache)} existing aliases from {self.alias_csv_path}")
            except Exception as e:
                self.logger.warning(f"Failed to load existing aliases: {e}")
                self.alias_cache = {}
        else:
            self.logger.info(f"No existing alias file found at {self.alias_csv_path}, starting fresh")
            
    def resolve(self, raw_team_name: str) -> Tuple[str, str]:
        """
        Resolve a raw team name to canonical team ID and name.
        
        Args:
            raw_team_name: The raw team name from game history
            
        Returns:
            Tuple of (canonical_team_id, canonical_team_name)
        """
        if not raw_team_name or pd.isna(raw_team_name):
            return raw_team_name, raw_team_name
        
        # Normalize the team name for consistent lookup
        normalized_name = normalize_team_name(raw_team_name)
        
        # Check cache first
        if normalized_name in self.alias_cache:
            team_id, team_name, confidence = self.alias_cache[normalized_name]
            return team_id, team_name
            
        # Check staged new aliases
        if normalized_name in self.new_aliases:
            team_id, team_name, confidence = self.new_aliases[normalized_name]
            return team_id, team_name
            
        # Fallback to sophisticated matching
        self.logger.debug(f"No alias found for '{raw_team_name}', using sophisticated matcher")
        
        # Use sophisticated matcher to find best match
        best_match = self.matcher.find_best_match(raw_team_name, self.master_df['Team_Name'].tolist())
        
        if best_match:
            # Found a good match
            canonical_team_name = best_match
            
            # Find the team_id for this canonical name
            team_row = self.master_df[self.master_df['Team_Name'] == canonical_team_name]
            if not team_row.empty:
                team_id = team_row.iloc[0]['Team_ID']
                confidence = 0.9  # Default confidence for sophisticated matches
                
                # Stage this new alias
                self.new_aliases[normalized_name] = (team_id, canonical_team_name, confidence)
                
                self.logger.debug(f"Matched '{raw_team_name}' -> '{canonical_team_name}' (confidence: {confidence:.3f})")
                return team_id, canonical_team_name
        
        # Fallback to hybrid matching
        self.logger.debug(f"No sophisticated match found for '{raw_team_name}', trying hybrid matcher")
        
        hybrid_match = self.hybrid_matcher.find_best_match(raw_team_name, self.master_df['Team_Name'].tolist())
        
        if hybrid_match:
            canonical_team_name, hybrid_score = hybrid_match
            
            # Find the team_id for this canonical name
            team_row = self.master_df[self.master_df['Team_Name'] == canonical_team_name]
            if not team_row.empty:
                team_id = team_row.iloc[0]['Team_ID']
                confidence = hybrid_score  # Use hybrid score as confidence
                
                # Calculate token overlap for confidence-weighted auto-approval
                token_overlap = self.hybrid_matcher.calculate_token_overlap(raw_team_name, canonical_team_name)
                
                # Phase 3 Enhancement #1: Confidence-weighted auto-approval
                if confidence >= 0.9 and token_overlap >= 0.6:
                    # Auto-approve high-confidence matches
                    self.new_aliases[normalized_name] = (team_id, canonical_team_name, confidence)
                    self.logger.info(f"Auto-approved '{raw_team_name}' -> '{canonical_team_name}' (confidence: {confidence:.3f}, overlap: {token_overlap:.3f})")
                    return team_id, canonical_team_name
                else:
                    # Log for manual review (lower confidence)
                    self.logger.debug(f"Hybrid matched '{raw_team_name}' -> '{canonical_team_name}' (confidence: {confidence:.3f}, overlap: {token_overlap:.3f}) - needs review")
                    # Still stage the alias but mark for review
                    self.new_aliases[normalized_name] = (team_id, canonical_team_name, confidence)
                    return team_id, canonical_team_name
        
        # No match found, log for review
        self.logger.warning(f"No match found for '{raw_team_name}', logging for review")
        
        # Create unmatched log entry
        unmatched_entry = self.hybrid_matcher.create_unmatched_log_entry(raw_team_name, self.master_df['Team_Name'].tolist())
        self.unmatched_teams.append(unmatched_entry)
        
        return raw_team_name, raw_team_name
        
    def flush(self):
        """Persist new aliases to CSV and create delta log."""
        if self.dry_run:
            self.logger.info(f"Dry run mode: {len(self.new_aliases)} new aliases would be added")
            return
            
        if not self.new_aliases:
            self.logger.info("No new aliases to persist")
            return
            
        # Create delta log
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        delta_log_path = f"data/mappings/logs/alias_additions_{timestamp}.csv"
        
        delta_data = []
        for alias_name, (team_id, team_name, confidence) in self.new_aliases.items():
            delta_data.append({
                'alias_name': alias_name,
                'canonical_team_id': team_id,
                'canonical_team_name': team_name,
                'confidence': confidence,
                'last_seen': datetime.now().isoformat()
            })
            
        delta_df = pd.DataFrame(delta_data)
        delta_df.to_csv(delta_log_path, index=False)
        self.logger.info(f"Created delta log: {delta_log_path} with {len(delta_data)} new aliases")
        
        # Update main alias table
        if os.path.exists(self.alias_csv_path):
            # Append to existing file
            existing_df = pd.read_csv(self.alias_csv_path)
            combined_df = pd.concat([existing_df, delta_df], ignore_index=True)
        else:
            # Create new file
            combined_df = delta_df
            
        combined_df.to_csv(self.alias_csv_path, index=False)
        
        # Update cache
        for alias_name, (team_id, team_name, confidence) in self.new_aliases.items():
            self.alias_cache[alias_name] = (team_id, team_name, confidence)
            
        self.logger.info(f"Persisted {len(self.new_aliases)} new aliases to {self.alias_csv_path}")
        
        # Clear staged aliases
        self.new_aliases.clear()
        
        # Save unmatched teams log
        if self.unmatched_teams:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unmatched_log_path = f"data/mappings/review/unmatched_teams_{timestamp}.csv"
            
            unmatched_df = pd.DataFrame(self.unmatched_teams)
            unmatched_df.to_csv(unmatched_log_path, index=False)
            self.logger.info(f"Saved {len(self.unmatched_teams)} unmatched teams to: {unmatched_log_path}")
            
            # Clear unmatched teams
            self.unmatched_teams.clear()
        
    def get_alias_dict(self) -> Dict[str, str]:
        """
        Get a dictionary mapping alias names to canonical names for vectorized operations.
        
        Returns:
            Dictionary mapping normalized alias names to canonical team names
        """
        alias_dict = {}
        
        # Add cached aliases
        for normalized_name, (team_id, canonical_name, confidence) in self.alias_cache.items():
            alias_dict[normalized_name] = canonical_name
        
        # Add staged new aliases
        for normalized_name, (team_id, canonical_name, confidence) in self.new_aliases.items():
            alias_dict[normalized_name] = canonical_name
        
        return alias_dict
    
    def batch_resolve(self, team_names: List[str]) -> Dict[str, str]:
        """
        Batch resolve multiple team names efficiently.
        
        Args:
            team_names: List of team names to resolve
            
        Returns:
            Dictionary mapping team names to canonical names
        """
        results = {}
        
        for team_name in team_names:
            if team_name and not pd.isna(team_name):
                canonical_id, canonical_name = self.resolve(team_name)
                results[team_name] = canonical_name
        
        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the alias resolver."""
        return {
            'cached_aliases': len(self.alias_cache),
            'new_aliases': len(self.new_aliases),
            'total_aliases': len(self.alias_cache) + len(self.new_aliases),
            'alias_file_exists': os.path.exists(self.alias_csv_path)
        }
