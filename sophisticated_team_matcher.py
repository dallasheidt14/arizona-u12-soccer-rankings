import pandas as pd
import numpy as np
import re
from difflib import SequenceMatcher
from typing import Dict, List, Tuple, Optional

# Import normalization
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from src.identity.team_normalizer import normalize_team_name

class SophisticatedTeamMatcher:
    """
    Advanced fuzzy matching for soccer teams with strict validation criteria.
    
    Matching Requirements:
    1. Same birth year (U10=2016/16, U11=2015/15, U12=2014/14)
    2. Same club name (with fuzzy tolerance)
    3. Same team color/designation (Red, Blue, Premier, Elite, etc.)
    4. Same gender (Boys/Girls)
    """
    
    def __init__(self):
        # Age group to birth year mapping
        self.age_to_birth_year = {
            'U10': ['2016', '16', 'u10'],
            'U11': ['2015', '15', 'u11'], 
            'U12': ['2014', '14', 'u12'],
            'U13': ['2013', '13', 'u13'],
            'U14': ['2012', '12', 'u14'],
            'U15': ['2011', '11', 'u15'],
            'U16': ['2010', '10', 'u16'],
            'U17': ['2009', '09', 'u17'],
            'U18': ['2008', '08', 'u18'],
            'U19': ['2007', '07', 'u19']
        }
        
        # Common club suffixes to normalize
        self.club_suffixes = [
            'fc', 'sc', 'united', 'city', 'town', 'academy', 'club', 'association',
            'athletic', 'sports', 'soccer', 'football', 'youth', 'premier', 'elite'
        ]
        
        # Common team designations/colors
        self.team_designations = [
            'red', 'blue', 'green', 'white', 'black', 'gold', 'silver', 'orange',
            'purple', 'yellow', 'navy', 'maroon', 'gray', 'grey', 'pink',
            'premier', 'elite', 'select', 'academy', 'pre', 'development',
            'travel', 'recreation', 'rec', 'competitive', 'comp'
        ]
        
        # Common coach name patterns (last names that appear in team names)
        self.coach_patterns = [
            'chacon', 'perez', 'garcia', 'rodriguez', 'martinez', 'hernandez', 'lopez', 'gonzalez',
            'wilson', 'smith', 'johnson', 'brown', 'jones', 'garcia', 'miller', 'davis',
            'castro', 'mendoza', 'cisneros', 'delta', 'alpha', 'beta', 'gamma',
            'anderson', 'thomas', 'taylor', 'moore', 'jackson', 'martin', 'lee', 'perez',
            'thompson', 'white', 'harris', 'sanchez', 'clark', 'ramirez', 'lewis', 'robinson'
        ]
        
        # Gender variations
        self.gender_terms = {
            'boys': ['boys', 'b', 'male', 'm'],
            'girls': ['girls', 'g', 'female', 'f']
        }
        
        # Common state abbreviations that should cause team differentiation
        self.state_abbreviations = [
            'al', 'ak', 'az', 'ar', 'ca', 'co', 'ct', 'de', 'fl', 'ga', 'hi', 'id', 'il', 'in', 'ia', 'ks', 'ky', 'la', 'me', 'md', 'ma', 'mi', 'mn', 'ms', 'mo', 'mt', 'ne', 'nv', 'nh', 'nj', 'nm', 'ny', 'nc', 'nd', 'oh', 'ok', 'or', 'pa', 'ri', 'sc', 'sd', 'tn', 'tx', 'ut', 'vt', 'va', 'wa', 'wv', 'wi', 'wy',
            'ala', 'alaska', 'ariz', 'ark', 'calif', 'colo', 'conn', 'del', 'fla', 'geo', 'hawaii', 'idaho', 'ill', 'ind', 'iowa', 'kans', 'kent', 'la', 'maine', 'md', 'mass', 'mich', 'minn', 'miss', 'mo', 'mont', 'neb', 'nev', 'nh', 'nj', 'nm', 'ny', 'nc', 'nd', 'ohio', 'okla', 'ore', 'pa', 'ri', 'sc', 'sd', 'tenn', 'tex', 'utah', 'vt', 'va', 'wash', 'wv', 'wis', 'wy'
        ]

    def parse_team_name(self, team_name: str) -> Dict[str, str]:
        """
        Parse team name into components: club, birth_year, gender, designation
        """
        if not team_name or pd.isna(team_name):
            return {}
        
        # Apply normalization preprocessing
        normalized_name = normalize_team_name(team_name)
        
        # Extract birth year/age group
        birth_year = self._extract_birth_year(normalized_name)
        
        # Extract gender
        gender = self._extract_gender(normalized_name)
        
        # Extract team designation/color
        designation = self._extract_designation(normalized_name)
        
        # Extract coach name
        coach = self._extract_coach_name(normalized_name)
        
        # Extract state abbreviation
        state = self._extract_state(normalized_name)
        
        # Extract club name (everything else)
        club = self._extract_club_name(normalized_name, birth_year, gender, designation, coach)
        
        return {
            'club': club,
            'birth_year': birth_year,
            'gender': gender,
            'designation': designation,
            'coach': coach,
            'state': state,
            'original': team_name,
            'normalized': normalized_name
        }

    def _extract_birth_year(self, name: str) -> str:
        """Extract birth year from team name"""
        # Look for 4-digit years first (highest priority)
        # Updated pattern to handle cases like "2016B" where letter follows year
        year_match = re.search(r'\b(20\d{2})(?:[a-zA-Z]|\b)', name)
        if year_match:
            return year_match.group(1)
        
        # Look for U## patterns (like "U11", "U10")
        u_match = re.search(r'\bu(\d{1,2})\b', name)
        if u_match:
            age = int(u_match.group(1))
            if age in [10, 11, 12, 13, 14, 15, 16, 17, 18, 19]:
                # Convert U## to birth year
                # U11 = 2015 birth year, U10 = 2016 birth year, U12 = 2014 birth year
                # Formula: 2024 - age + 2 (to get correct birth years)
                birth_year = 2024 - age + 2
                return str(birth_year)
        
        # Look for 2-digit years
        year_match = re.search(r'\b(\d{2})\b', name)
        if year_match:
            year = year_match.group(1)
            # Convert 2-digit to 4-digit (assume 20xx)
            if int(year) >= 0 and int(year) <= 30:  # 2000-2030
                return f"20{year}"
            elif int(year) >= 80 and int(year) <= 99:  # 1980-1999
                return f"19{year}"
        
        # Look for B/G patterns with years (like "15B", "16G")
        bg_match = re.search(r'\b(\d{2})[bg]\b', name)
        if bg_match:
            year = bg_match.group(1)
            if int(year) >= 0 and int(year) <= 30:  # 2000-2030
                return f"20{year}"
            elif int(year) >= 80 and int(year) <= 99:  # 1980-1999
                return f"19{year}"
        
        return ""

    def _extract_gender(self, name: str) -> str:
        """Extract gender from team name"""
        # Look for explicit gender terms
        for gender, terms in self.gender_terms.items():
            for term in terms:
                if f' {term} ' in f' {name} ' or name.endswith(f' {term}'):
                    return gender
        
        # Look for B/G patterns (like "15B", "16G")
        b_pattern = re.search(r'\b\d{2,4}[bg]\b', name)
        if b_pattern:
            if 'b' in b_pattern.group(0).lower():
                return 'boys'
            elif 'g' in b_pattern.group(0).lower():
                return 'girls'
        
        return ""

    def _extract_designation(self, name: str) -> str:
        """Extract team designation/color from team name"""
        # Look for Roman numerals first (highest priority)
        roman_match = re.search(r'\b(i|ii|iii|iv|v|vi|vii|viii|ix|x)\b', name.lower())
        if roman_match:
            roman_to_num = {'i': '1', 'ii': '2', 'iii': '3', 'iv': '4', 'v': '5', 
                           'vi': '6', 'vii': '7', 'viii': '8', 'ix': '9', 'x': '10'}
            return roman_to_num[roman_match.group(1)]
        
        # Look for single letter designations (A, B, C, etc.) - but not gender indicators
        letter_match = re.search(r'\b([a-z])\b', name.lower())
        if letter_match:
            letter = letter_match.group(1)
            # Don't extract 'b' or 'g' as they're gender indicators
            if letter not in ['b', 'g']:
                return letter
        
        # Look for numeric designations (1, 2, 3, etc.) - but not birth years
        # Exclude 4-digit years and 2-digit years that could be birth years
        numeric_match = re.search(r'\b(\d+)\b', name)
        if numeric_match:
            num = numeric_match.group(1)
            # Don't extract 4-digit years or 2-digit years that could be birth years
            if len(num) == 4:  # Skip 4-digit years
                pass  # Continue to predefined designations
            elif len(num) == 2 and int(num) >= 0 and int(num) <= 30:  # Skip potential birth years
                pass  # Continue to predefined designations
            else:
                return num
        
        # Finally check predefined designations (colors, levels, etc.)
        for designation in self.team_designations:
            if f' {designation} ' in f' {name} ' or name.endswith(f' {designation}'):
                return designation
        
        return ""

    def _extract_coach_name(self, name: str) -> str:
        """Extract coach name from team name"""
        # Look for coach names at the end of team names
        for coach in self.coach_patterns:
            if name.endswith(f' {coach}'):
                return coach
        
        # Look for coach names that are followed by numbers or at the end
        # Pattern: word followed by optional number or at end of string
        coach_match = re.search(r'\b([A-Za-z]+(?:\.[A-Za-z])?)\s*(?:\d+\s*)?$', name)
        if coach_match:
            potential_coach = coach_match.group(1).lower()
            # Check if it looks like a coach name (not a generic term)
            # Don't include colors as generic terms since they can be coach names
            generic_terms = ['team', 'club', 'fc', 'sc', 'united', 'boys', 'girls', 'male', 'female', 'premier', 'elite', 'select', 'academy']
            if len(potential_coach) > 3 and potential_coach not in generic_terms:
                return potential_coach
        
        # Look for coach names that are followed by numbers in the middle
        # Find ALL matches and take the last one (most likely to be coach name)
        all_matches = re.findall(r'\b([A-Za-z]+(?:\.[A-Za-z])?)\s+\d+', name)
        if all_matches:
            # Take the last match (most likely to be the coach name)
            potential_coach = all_matches[-1].lower()
            # Don't include colors as generic terms since they can be coach names
            generic_terms = ['team', 'club', 'fc', 'sc', 'united', 'boys', 'girls', 'male', 'female', 'premier', 'elite', 'select', 'academy']
            if len(potential_coach) > 3 and potential_coach not in generic_terms:
                return potential_coach
        
        return ""

    def _extract_state(self, name: str) -> str:
        """Extract state abbreviation from team name"""
        name_lower = name.lower()
        for state in self.state_abbreviations:
            if f' {state} ' in f' {name_lower} ' or name_lower.endswith(f' {state}'):
                return state
        return ""

    def _extract_club_name(self, name: str, birth_year: str, gender: str, designation: str, coach: str) -> str:
        club = name
        
        # Remove birth year
        if birth_year:
            club = re.sub(rf'\b{re.escape(birth_year)}\b', '', club).strip()
            # Also remove 2-digit version
            if len(birth_year) == 4:
                two_digit = birth_year[2:]
                club = re.sub(rf'\b{re.escape(two_digit)}\b', '', club).strip()
        
        # Remove gender
        if gender:
            for term in self.gender_terms[gender]:
                club = re.sub(rf'\b{re.escape(term)}\b', '', club).strip()
        
        # Remove designation
        if designation:
            club = re.sub(rf'\b{re.escape(designation)}\b', '', club).strip()
        
        # Remove coach name
        if coach:
            club = re.sub(rf'\b{re.escape(coach)}\b', '', club).strip()
        
        # Remove U## patterns
        club = re.sub(r'\bu\d{1,2}\b', '', club).strip()
        
        # Clean up extra spaces
        club = re.sub(r'\s+', ' ', club).strip()
        
        return club

    def normalize_club_name(self, club_name: str) -> str:
        """Normalize club name for better matching"""
        if not club_name:
            return ""
        
        normalized = club_name.lower().strip()
        
        # Remove common suffixes
        for suffix in self.club_suffixes:
            if normalized.endswith(f' {suffix}'):
                normalized = normalized[:-len(f' {suffix}')].strip()
        
        # Remove common prefixes
        prefixes = ['the ', 'fc ', 'sc ']
        for prefix in prefixes:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):].strip()
        
        # Remove special characters and extra spaces
        normalized = re.sub(r'[^\w\s]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized

    def calculate_similarity(self, team1: Dict[str, str], team2: Dict[str, str]) -> float:
        """
        Calculate similarity score between two parsed teams.
        Returns 0.0 to 1.0, where 1.0 is perfect match.
        """
        # Must have same birth year (critical requirement)
        if team1.get('birth_year') != team2.get('birth_year'):
            return 0.0
        
        # Must have same gender (critical requirement)
        if team1.get('gender') != team2.get('gender'):
            return 0.0
        
        # Must have same designation (critical requirement)
        if team1.get('designation') != team2.get('designation'):
            return 0.0
        
        # Must have same coach name (critical requirement)
        # But allow matches when both teams have no coach name specified
        coach1 = team1.get('coach', '')
        coach2 = team2.get('coach', '')
        if coach1 and coach2 and coach1 != coach2:
            return 0.0
        
        # Must have same state (critical requirement)
        # But allow matches when both teams have no state specified
        state1 = team1.get('state', '')
        state2 = team2.get('state', '')
        if state1 and state2 and state1 != state2:
            return 0.0
        
        # Calculate club name similarity
        club1_norm = self.normalize_club_name(team1.get('club', ''))
        club2_norm = self.normalize_club_name(team2.get('club', ''))
        
        if not club1_norm or not club2_norm:
            return 0.0
        
        # Use sequence matcher for club name similarity
        club_similarity = SequenceMatcher(None, club1_norm, club2_norm).ratio()
        
        # Check for substring matches (boost score)
        # Check if one club name contains the other as a significant substring
        if club1_norm in club2_norm or club2_norm in club1_norm:
            club_similarity = max(club_similarity, 0.9)
        else:
            # Check for partial word matches (like "next level se" vs "next level soccer southeast")
            words1 = set(club1_norm.split())
            words2 = set(club2_norm.split())
            common_words = words1.intersection(words2)
            
            # Only boost if they share meaningful club words (not generic terms)
            meaningful_common = [w for w in common_words if len(w) > 2 and w not in ['fc', 'sc', 'united', 'city', 'town', 'academy', 'club', 'association', 'athletic', 'sports', 'soccer', 'football', 'youth', 'premier', 'elite']]
            
            if len(meaningful_common) >= 2:  # At least 2 meaningful common words
                club_similarity = max(club_similarity, 0.8)
        
        # Additional validation: club names must be reasonably similar
        # If clubs are too different, reject the match
        if club_similarity < 0.8:  # Increased threshold for stricter matching
            return 0.0
        
        # Additional check: reject matches where club names are completely different
        # (like "Team A" vs "Team B")
        if club1_norm != club2_norm and not (club1_norm in club2_norm or club2_norm in club1_norm):
            # If they're not substrings of each other, require very high similarity
            if club_similarity < 0.9:  # Increased threshold for stricter matching
                return 0.0
        
        # Special case: reject "Team A" vs "Team B" type matches
        if ('team a' in club1_norm and 'team b' in club2_norm) or ('team b' in club1_norm and 'team a' in club2_norm):
            return 0.0
        
        # Special case: reject matches where one club is just a generic word from another
        # (like "team a" containing "team")
        if club1_norm != club2_norm:
            # If one is much shorter and contained in the other, be more strict
            shorter = min(club1_norm, club2_norm, key=len)
            longer = max(club1_norm, club2_norm, key=len)
            if len(shorter) < len(longer) * 0.7:  # If shorter is less than 70% of longer
                if shorter in longer and club_similarity < 0.95:
                    return 0.0
        
        # Additional validation: reject matches where club names share only generic words
        # (like "South Valley Chivas" vs "Alabama FC South" - both have "South" but different clubs)
        words1 = set(club1_norm.split())
        words2 = set(club2_norm.split())
        common_words = words1.intersection(words2)
        
        # Exclude generic terms like age/gender identifiers and common suffixes
        generic_terms = ['fc', 'sc', 'united', 'city', 'town', 'academy', 'club', 'association', 'athletic', 'sports', 'soccer', 'football', 'youth', 'premier', 'elite', '15b', '16b', '17b', '18b', '15g', '16g', '17g', '18g', 'south', 'north', 'east', 'west', 'central', 'metro', 'valley', 'ridge', 'hills', 'park', 'field', 'stadium', 'center', 'centre']
        meaningful_words = [w for w in common_words if len(w) > 1 and w not in generic_terms]
        
        # Require at least 2 meaningful words for a match (increased from 1)
        if len(meaningful_words) < 2:
            return 0.0
        
        # Additional validation: require minimum 3 matching criteria
        # Count matching criteria: birth_year, gender, designation, coach, club_words
        matching_criteria = 0
        
        # Birth year match
        if team1.get('birth_year') == team2.get('birth_year') and team1.get('birth_year'):
            matching_criteria += 1
        
        # Gender match
        if team1.get('gender') == team2.get('gender') and team1.get('gender'):
            matching_criteria += 1
        
        # Designation match
        if team1.get('designation') == team2.get('designation') and team1.get('designation'):
            matching_criteria += 1
        
        # Coach match (only if both have coach names)
        coach1 = team1.get('coach', '')
        coach2 = team2.get('coach', '')
        if coach1 and coach2 and coach1 == coach2:
            matching_criteria += 1
        
        # Club word match (meaningful words)
        if len(meaningful_words) >= 2:
            matching_criteria += 1
        
        # Require minimum 3 matching criteria
        if matching_criteria < 3:
            return 0.0
        
        return club_similarity

    def find_best_match(self, team_name: str, master_teams: List[str], threshold: float = 0.8) -> Optional[str]:
        """
        Find the best matching team from master list.
        
        Args:
            team_name: Team name to match
            master_teams: List of master team names
            threshold: Minimum similarity score (0.0 to 1.0)
        
        Returns:
            Best matching team name or None if no match above threshold
        """
        if not team_name or pd.isna(team_name):
            return None
        
        team1_parsed = self.parse_team_name(team_name)
        if not team1_parsed.get('birth_year') or not team1_parsed.get('gender'):
            return None
        
        best_match = None
        best_score = 0.0
        
        for master_team in master_teams:
            if pd.isna(master_team) or master_team == team_name:
                continue
            
            team2_parsed = self.parse_team_name(master_team)
            if not team2_parsed.get('birth_year') or not team2_parsed.get('gender'):
                continue
            
            similarity = self.calculate_similarity(team1_parsed, team2_parsed)
            
            if similarity > best_score and similarity >= threshold:
                best_score = similarity
                best_match = master_team
        
        return best_match

    def create_team_mapping(self, game_teams: List[str], master_teams: List[str], threshold: float = 0.8) -> Dict[str, str]:
        """
        Create mapping from game team names to master team names.
        
        Args:
            game_teams: List of team names from game data
            master_teams: List of master team names
            threshold: Minimum similarity score for matching
        
        Returns:
            Dictionary mapping game team names to master team names
        """
        mapping = {}
        unmatched = []
        matches_found = []
        
        print(f"Creating sophisticated team mapping for {len(game_teams)} game teams against {len(master_teams)} master teams...")
        print(f"Using threshold: {threshold}")
        
        for game_team in game_teams:
            if pd.isna(game_team):
                continue
            
            # First try exact match
            if game_team in master_teams:
                mapping[game_team] = game_team
                continue
            
            # Try sophisticated fuzzy matching
            best_match = self.find_best_match(game_team, master_teams, threshold)
            
            if best_match:
                mapping[game_team] = best_match
                matches_found.append((game_team, best_match))
                print(f"  ✓ MATCHED: '{game_team}' → '{best_match}'")
            else:
                unmatched.append(game_team)
        
        print(f"\n=== MAPPING RESULTS ===")
        print(f"Exact matches: {len(mapping) - len(matches_found)}")
        print(f"Fuzzy matches: {len(matches_found)}")
        print(f"Total mapped: {len(mapping)}")
        print(f"Unmatched: {len(unmatched)}")
        
        if unmatched:
            print(f"\nSample unmatched teams:")
            for team in sorted(unmatched)[:10]:
                parsed = self.parse_team_name(team)
                print(f"  - '{team}' → Club: '{parsed.get('club')}', Year: '{parsed.get('birth_year')}', Gender: '{parsed.get('gender')}', Designation: '{parsed.get('designation')}'")
        
        return mapping

def test_sophisticated_matching():
    """Test the sophisticated matching system with sample data"""
    
    # Sample test cases
    test_cases = [
        # Good matches (should work)
        ("Next Level Soccer Southeast 2015 Boys Red", "Next Level SE U11 Boys Red"),
        ("Real Madrid FC 2016 Boys Blue", "Real Madrid 16 Boys Blue"),
        ("Arsenal FC 2015 Boys Premier", "Arsenal 15 Boys Premier"),
        ("RSL North Boys 15 Chacon", "RSL North Boys 15 Chacon"),  # Same coach
        ("RSL North Boys 15 Chacon", "RSL North Boys 15 Perez"),   # Different coaches - should NOT match
        
        # Bad matches (should NOT work)
        ("Revolution 15B Blue", "Revolution 16B Blue"),  # Different birth years
        ("Erie FC 2017 Boys", "Rise FC 2016 Boys"),     # Different clubs, different years
        ("Team A 2015 Boys Red", "Team B 2015 Boys Red"), # Different clubs
        
        # Edge cases
        ("NLSA Surf/HVSA PDP 2016 Boys", "NLSA Surf PDP 2016 Boys"),  # Should work
        ("16B FPFC HERNANDO ELITE", "2016B"),  # Should NOT work (too generic)
        ("DSA Dallas Rebels 15B Cisneros", "Academia De Futbol Dallas 15b"),  # Different clubs, different coaches
        ("Solar SW 15B Garcia.S", "Solar 15B Castro"),  # Same club, different coaches
    ]
    
    matcher = SophisticatedTeamMatcher()
    
    print("=== TESTING SOPHISTICATED TEAM MATCHING ===\n")
    
    for team1, team2 in test_cases:
        parsed1 = matcher.parse_team_name(team1)
        parsed2 = matcher.parse_team_name(team2)
        similarity = matcher.calculate_similarity(parsed1, parsed2)
        
        print(f"Team 1: '{team1}'")
        print(f"  Parsed: Club='{parsed1.get('club')}', Year='{parsed1.get('birth_year')}', Gender='{parsed1.get('gender')}', Designation='{parsed1.get('designation')}', Coach='{parsed1.get('coach')}'")
        
        print(f"Team 2: '{team2}'")
        print(f"  Parsed: Club='{parsed2.get('club')}', Year='{parsed2.get('birth_year')}', Gender='{parsed2.get('gender')}', Designation='{parsed2.get('designation')}', Coach='{parsed2.get('coach')}'")
        
        print(f"Similarity: {similarity:.3f}")
        print(f"Match: {'✓ YES' if similarity >= 0.8 else '✗ NO'}")
        print("-" * 80)

if __name__ == "__main__":
    test_sophisticated_matching()
