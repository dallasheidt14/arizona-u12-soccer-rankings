"""
Hybrid Team Matcher

Fallback scorer using token overlap + fuzzy matching for teams that fail
sophisticated matching. Handles reordering, missing tokens, and partial matches.
"""

import pandas as pd
from typing import List, Optional, Tuple, Dict
from difflib import SequenceMatcher

try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    print("Warning: rapidfuzz not available, falling back to difflib")

# Import normalization with absolute path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.identity.team_normalizer import normalize_team_name, calculate_token_overlap

class HybridMatcher:
    """
    Hybrid matcher that combines fuzzy string matching with token overlap analysis.
    
    Uses:
    - Token sort ratio (handles reordering)
    - Token overlap ratio (handles missing tokens)  
    - Combined score: 0.6 * fuzzy + 0.4 * overlap
    """
    
    def __init__(self, threshold: float = 0.7):
        """
        Initialize hybrid matcher.
        
        Args:
            threshold: Minimum similarity score for matches (0.0 to 1.0)
        """
        self.threshold = threshold
        
    def calculate_fuzzy_score(self, name1: str, name2: str) -> float:
        """
        Calculate fuzzy string similarity score.
        
        Args:
            name1: First team name
            name2: Second team name
            
        Returns:
            Fuzzy similarity score (0.0 to 1.0)
        """
        if RAPIDFUZZ_AVAILABLE:
            # Use rapidfuzz for better performance
            return fuzz.token_sort_ratio(name1, name2) / 100.0
        else:
            # Fallback to difflib
            return SequenceMatcher(None, name1, name2).ratio()
    
    def calculate_hybrid_similarity(self, name1: str, name2: str) -> float:
        """
        Calculate hybrid similarity score combining fuzzy and token overlap.
        
        Args:
            name1: First team name
            name2: Second team name
            
        Returns:
            Hybrid similarity score (0.0 to 1.0)
        """
        # Normalize both names
        norm1 = normalize_team_name(name1)
        norm2 = normalize_team_name(name2)
        
        # Calculate fuzzy score
        fuzzy_score = self.calculate_fuzzy_score(norm1, norm2)
        
        # Calculate token overlap score
        overlap_score = calculate_token_overlap(norm1, norm2)
        
        # Combine scores: 60% fuzzy, 40% overlap
        hybrid_score = 0.6 * fuzzy_score + 0.4 * overlap_score
        
    def calculate_token_overlap(self, name1: str, name2: str) -> float:
        """
        Calculate token overlap ratio between two team names.
        
        Args:
            name1: First team name
            name2: Second team name
            
        Returns:
            Token overlap ratio (0.0 to 1.0)
        """
        return calculate_token_overlap(name1, name2)
    
    def find_best_match(self, team_name: str, master_teams: List[str]) -> Optional[Tuple[str, float]]:
        """
        Find the best matching team from master list using hybrid scoring.
        
        Args:
            team_name: Team name to match
            master_teams: List of master team names
            
        Returns:
            Tuple of (best_match_name, similarity_score) or None if no match above threshold
        """
        if not team_name or pd.isna(team_name):
            return None
        
        best_match = None
        best_score = 0.0
        
        for master_team in master_teams:
            if pd.isna(master_team) or master_team == team_name:
                continue
            
            similarity = self.calculate_hybrid_similarity(team_name, master_team)
            
            if similarity is not None and similarity > best_score and similarity >= self.threshold:
                best_score = similarity
                best_match = master_team
        
        if best_match:
            return (best_match, best_score)
        else:
            return None
    
    def find_top_candidates(self, team_name: str, master_teams: List[str], top_k: int = 3) -> List[Tuple[str, float]]:
        """
        Find top K candidate matches for a team name.
        
        Args:
            team_name: Team name to match
            master_teams: List of master team names
            top_k: Number of top candidates to return
            
        Returns:
            List of tuples (candidate_name, similarity_score) sorted by score descending
        """
        if not team_name or pd.isna(team_name):
            return []
        
        candidates = []
        
        for master_team in master_teams:
            if pd.isna(master_team) or master_team == team_name:
                continue
            
            similarity = self.calculate_hybrid_similarity(team_name, master_team)
            
            if similarity is not None and similarity > 0.3:  # Lower threshold for candidates
                candidates.append((master_team, similarity))
        
        # Sort by similarity score descending
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        return candidates[:top_k]
    
    def create_unmatched_log_entry(self, team_name: str, master_teams: List[str]) -> Dict[str, str]:
        """
        Create a log entry for an unmatched team with top candidates.
        
        Args:
            team_name: Unmatched team name
            master_teams: List of master team names
            
        Returns:
            Dictionary with log entry data
        """
        normalized_name = normalize_team_name(team_name)
        candidates = self.find_top_candidates(team_name, master_teams, top_k=3)
        
        # Format candidates as string
        candidate_strs = []
        for candidate, score in candidates:
            candidate_strs.append(f"{candidate} ({score:.3f})")
        
        candidates_str = " | ".join(candidate_strs) if candidate_strs else "None"
        best_score = candidates[0][1] if candidates else 0.0
        
        return {
            'raw_name': team_name,
            'normalized_name': normalized_name,
            'top_3_candidates': candidates_str,
            'best_score': f"{best_score:.3f}"
        }

# Test cases for validation
if __name__ == "__main__":
    matcher = HybridMatcher(threshold=0.7)
    
    test_cases = [
        ("AZ Arsenal 16 Boys Teal OC", "AZ Arsenal SC 16 Boys Teal (OC)"),
        ("Phoenix Rising FC 2016", "Phoenix Rising 16 Boys Red"),
        ("RSL North 16B", "RSL AZ North 2016 Boys"),
        ("Barcelona AZ 2016", "AZ Barca Academy 2016 Boys"),
        ("Rebels SC Boys 2016", "Rebels SC 16 Boys White"),
    ]
    
    print("=== HYBRID MATCHER TEST ===")
    for team1, team2 in test_cases:
        similarity = matcher.calculate_hybrid_similarity(team1, team2)
        print(f"'{team1}' vs '{team2}'")
        print(f"  Hybrid similarity: {similarity:.3f}")
        print(f"  Above threshold (0.7): {similarity >= 0.7}")
        print()
