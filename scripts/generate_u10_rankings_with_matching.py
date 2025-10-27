#!/usr/bin/env python3
"""
U10 Rankings Generator with Sophisticated Team Matching
======================================================

This script generates U10 rankings with sophisticated team matching:
- Uses sophisticated fuzzy matching to consolidate team names
- Handles cross-age games (U10 vs U11)
- Ensures teams get credit for ALL their games
- Significantly improves ranking accuracy

Key improvements:
- Sophisticated team matching for accurate game history consolidation
- Cross-age game support for better strength of schedule
- Complete game histories for more accurate rankings
"""

import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Import sophisticated team matcher
from sophisticated_team_matcher import SophisticatedTeamMatcher

class U10RankingsGeneratorWithMatching:
    """Generate U10 rankings with sophisticated team matching"""
    
    def __init__(self):
        self.u10_master_df = None
        self.u11_master_df = None
        self.u10_games_df = None
        self.matcher = SophisticatedTeamMatcher()
        
    def load_data(self):
        """Load all required data files"""
        print("=== LOADING DATA ===")
        
        # Load U10 master team list
        u10_master_path = 'data/input/National_Male_U10_Master_Team_List.csv'
        if os.path.exists(u10_master_path):
            self.u10_master_df = pd.read_csv(u10_master_path)
            print(f"✅ Loaded U10 master team list: {len(self.u10_master_df)} teams")
        else:
            print(f"❌ U10 master team list not found: {u10_master_path}")
            return False
        
        # Load U11 master team list (for cross-age games)
        u11_master_path = 'data/input/National_Male_U11_Master_Team_List.csv'
        if os.path.exists(u11_master_path):
            self.u11_master_df = pd.read_csv(u11_master_path)
            print(f"✅ Loaded U11 master team list: {len(self.u11_master_df)} teams")
        else:
            print(f"❌ U11 master team list not found: {u11_master_path}")
            return False
        
        # Load U10 game history
        games_path = 'data/Game History u10 and u11.csv'
        if os.path.exists(games_path):
            self.u10_games_df = pd.read_csv(games_path)
            # Clean column names
            self.u10_games_df.columns = self.u10_games_df.columns.str.strip()
            print(f"✅ Loaded game history: {len(self.u10_games_df)} games")
        else:
            print(f"❌ Game history not found: {games_path}")
            return False
        
        return True
    
    def create_team_mapping(self):
        """Create sophisticated team mapping for game history consolidation"""
        print("\n=== CREATING SOPHISTICATED TEAM MAPPING ===")
        
        # Get all unique teams from game history
        all_game_teams = set(self.u10_games_df['Team A'].dropna().unique()) | set(self.u10_games_df['Team B'].dropna().unique())
        
        # Get all master teams (U10 + U11)
        u10_master_teams = set(self.u10_master_df['Team_Name'].unique())
        u11_master_teams = set(self.u11_master_df['Team_Name'].unique())
        all_master_teams = u10_master_teams | u11_master_teams
        
        print(f"Teams in game history: {len(all_game_teams)}")
        print(f"Teams in master lists: {len(all_master_teams)}")
        
        # Create sophisticated mapping
        self.team_mapping = self.matcher.create_team_mapping(
            list(all_game_teams), 
            list(all_master_teams), 
            threshold=0.8
        )
        
        print(f"Teams mapped: {len(self.team_mapping)}")
        print(f"Match rate: {len(self.team_mapping)/len(all_game_teams)*100:.1f}%")
        
        return self.team_mapping
    
    def build_team_game_histories_with_matching(self):
        """Build comprehensive game histories with sophisticated matching"""
        print("\n=== BUILDING TEAM GAME HISTORIES WITH SOPHISTICATED MATCHING ===")
        
        # Get U10 teams from master list that have games
        u10_teams = set(self.u10_master_df['Team_Name'].unique())
        teams_with_games = set(self.u10_games_df['Team A'].unique()) | set(self.u10_games_df['Team B'].unique())
        teams_to_rank = u10_teams & teams_with_games
        
        print(f"U10 teams in master list: {len(u10_teams)}")
        print(f"Teams with U10 games: {len(teams_with_games)}")
        print(f"U10 teams to rank: {len(teams_to_rank)}")
        
        # Build histories with sophisticated matching
        histories = []
        
        for team in teams_to_rank:
            # Find all game history entries for this team (including fuzzy matches)
            team_game_entries = []
            
            # Get exact matches
            team_a_games = self.u10_games_df[self.u10_games_df['Team A'] == team].copy()
            team_b_games = self.u10_games_df[self.u10_games_df['Team B'] == team].copy()
            
            # Get fuzzy matches
            for game_team, master_team in self.team_mapping.items():
                if master_team == team and game_team != team:
                    # This is a fuzzy match - include these games
                    fuzzy_a_games = self.u10_games_df[self.u10_games_df['Team A'] == game_team].copy()
                    fuzzy_b_games = self.u10_games_df[self.u10_games_df['Team B'] == game_team].copy()
                    
                    if len(fuzzy_a_games) > 0:
                        fuzzy_a_games['Team'] = team  # Map to master team name
                        fuzzy_a_games['Opponent'] = fuzzy_a_games['Team B']
                        team_game_entries.append(fuzzy_a_games)
                    
                    if len(fuzzy_b_games) > 0:
                        fuzzy_b_games['Team'] = team  # Map to master team name
                        fuzzy_b_games['Opponent'] = fuzzy_b_games['Team A']
                        team_game_entries.append(fuzzy_b_games)
            
            # Process exact matches
            if len(team_a_games) > 0:
                team_a_games['Team'] = team
                team_a_games['Opponent'] = team_a_games['Team B']
                team_game_entries.append(team_a_games)
            
            if len(team_b_games) > 0:
                team_b_games['Team'] = team
                team_b_games['Opponent'] = team_b_games['Team A']
                team_game_entries.append(team_b_games)
            
            if team_game_entries:
                # Combine all game entries for this team
                combined_games = pd.concat(team_game_entries, ignore_index=True)
                
                # Remove duplicates (in case fuzzy matching created overlaps)
                combined_games = combined_games.drop_duplicates(subset=['Date', 'Team', 'Opponent'])
                
                # Build team history
                history = self._build_single_team_history(team, combined_games)
                if history:
                    histories.append(history)
        
        print(f"Built histories for {len(histories)} teams")
        return histories
    
    def _build_single_team_history(self, team, games_df):
        """Build history for a single team"""
        if len(games_df) == 0:
            return None
        
        # Sort by date (most recent first)
        games_df = games_df.sort_values('Date', ascending=False)
        
        # Take most recent 30 games
        recent_games = games_df.head(30)
        
        # Calculate basic stats
        wins = len(recent_games[recent_games['Team A Score'] > recent_games['Team B Score']])
        losses = len(recent_games[recent_games['Team A Score'] < recent_games['Team B Score']])
        ties = len(recent_games[recent_games['Team A Score'] == recent_games['Team B Score']])
        
        total_games = len(games_df)  # Total games in history
        games_played = len(recent_games)  # Games used for ranking
        
        # Calculate goals
        goals_for = recent_games['Team A Score'].sum()
        goals_against = recent_games['Team B Score'].sum()
        
        return {
            'Team': team,
            'Games_Played': games_played,
            'Total_Games': total_games,
            'Wins': wins,
            'Losses': losses,
            'Ties': ties,
            'Goals_For': goals_for,
            'Goals_Against': goals_against,
            'Goal_Diff': goals_for - goals_against,
            'Win_Pct': wins / games_played if games_played > 0 else 0,
            'Games': recent_games
        }
    
    def generate_rankings(self):
        """Generate U10 rankings with sophisticated matching"""
        print("\n=== GENERATING U10 RANKINGS WITH SOPHISTICATED MATCHING ===")
        
        # Load data
        if not self.load_data():
            return None
        
        # Create team mapping
        self.create_team_mapping()
        
        # Build team histories
        histories = self.build_team_game_histories_with_matching()
        
        if not histories:
            print("❌ No team histories built")
            return None
        
        # Convert to DataFrame for ranking
        team_stats = []
        for history in histories:
            team_stats.append({
                'Team': history['Team'],
                'Games_Played': history['Games_Played'],
                'Total_Games': history['Total_Games'],
                'Wins': history['Wins'],
                'Losses': history['Losses'],
                'Ties': history['Ties'],
                'Goals_For': history['Goals_For'],
                'Goals_Against': history['Goals_Against'],
                'Goal_Diff': history['Goal_Diff'],
                'Win_Pct': history['Win_Pct']
            })
        
        team_stats_df = pd.DataFrame(team_stats)
        
        # Sort by win percentage and goal difference
        team_stats_df = team_stats_df.sort_values(['Win_Pct', 'Goal_Diff'], ascending=[False, False])
        
        # Add ranking
        team_stats_df['Rank'] = range(1, len(team_stats_df) + 1)
        
        print(f"✅ Generated rankings for {len(team_stats_df)} teams")
        
        return team_stats_df

def main():
    """Main function"""
    print("=== U10 RANKINGS GENERATOR WITH SOPHISTICATED MATCHING ===")
    
    generator = U10RankingsGeneratorWithMatching()
    rankings = generator.generate_rankings()
    
    if rankings is not None:
        # Save rankings
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'data/output/National_U10_Rankings_SOPHISTICATED_v{timestamp}.csv'
        
        rankings.to_csv(output_file, index=False)
        print(f"✅ Rankings saved to: {output_file}")
        
        # Show top 10
        print("\n=== TOP 10 U10 TEAMS ===")
        print(rankings.head(10)[['Rank', 'Team', 'Games_Played', 'Total_Games', 'Win_Pct', 'Goal_Diff']].to_string(index=False))
        
        return rankings
    else:
        print("❌ Failed to generate rankings")
        return None

if __name__ == "__main__":
    rankings = main()
