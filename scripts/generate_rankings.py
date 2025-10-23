#!/usr/bin/env python3
"""
Scalable Youth Soccer Rankings Generator
=======================================

This is a template script for generating rankings for any age group with cross-age support.
Simply modify the configuration section to generate rankings for U11, U12, U13, etc.

Key Features:
- Cross-age game support (e.g., U10 vs U11, U11 vs U12)
- Automatic master team list loading
- V5.3E Enhanced ranking algorithm
- State-level breakdowns
- Comprehensive reporting

Usage:
    python scripts/generate_rankings.py --age U11 --gender M
    python scripts/generate_rankings.py --age U12 --gender M
    python scripts/generate_rankings.py --age U10 --gender F
"""

import pandas as pd
import numpy as np
import os
import sys
import argparse
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

class YouthSoccerRankingsGenerator:
    """Generate youth soccer rankings for any age group with cross-age support."""
    
    def __init__(self, age_group, gender='M'):
        self.age_group = age_group.upper()
        self.gender = gender.upper()
        self.project_root = os.path.dirname(os.path.dirname(__file__))
        
        # Input files - will be determined based on age group
        self.combined_games_file = os.path.join(self.project_root, "data", "Game History u10 and u11.csv")
        self.master_file = self._get_master_file_path()
        self.cross_age_master_file = self._get_cross_age_master_file_path()
        
        # Output files
        self.output_dir = os.path.join(self.project_root, "data", "output")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Configuration
        self.ranking_window_days = 365
        self.max_games = 30
        self.recent_games = 15  # Most recent games (50% weight)
        self.middle_games = 10  # Middle games 16-25 (35% weight)
        self.oldest_games = 5   # Oldest games 26-30 (15% weight)
        self.recent_weight = 0.50    # Weight for games 1-15 (reduced from 0.60)
        self.middle_weight = 0.35    # Weight for games 16-25 (increased from 0.30)
        self.oldest_weight = 0.15    # Weight for games 26-30 (increased from 0.10)
        self.default_opponent_strength = 0.35  # Default strength for unknown opponents
        
        print(f"Initialized rankings generator for {self.age_group} {self.gender}")
        
    def _get_master_file_path(self):
        """Get the master team list file path for the current age group."""
        gender_full = "Male" if self.gender == "M" else "Female"
        return os.path.join(
            self.project_root, 
            "data", 
            "input", 
            f"National_{gender_full}_U{self.age_group}_Master_Team_List.csv"
        )
    
    def _get_cross_age_master_file_path(self):
        """Get the cross-age master team list file path."""
        gender_full = "Male" if self.gender == "M" else "Female"
        
        if self.age_group == '10':
            cross_age = '11'
        elif self.age_group == '11':
            cross_age = '12'
        elif self.age_group == '12':
            cross_age = '13'
        else:
            # For other age groups, we'll handle cross-age differently
            return None
            
        return os.path.join(
            self.project_root, 
            "data", 
            "input", 
            f"National_{gender_full}_U{cross_age}_Master_Team_List.csv"
        )
    
    def load_data(self):
        """Load the game history and master team lists."""
        print(f"=== LOADING DATA FOR {self.age_group} {self.gender} ===")
        
        # Load combined game history
        self.combined_games_df = pd.read_csv(self.combined_games_file)
        print(f"Loaded {len(self.combined_games_df)} combined games from: {self.combined_games_file}")
        
        # Load primary master team list
        self.master_df = pd.read_csv(self.master_file)
        print(f"Loaded {len(self.master_df)} {self.age_group} master teams from: {self.master_file}")
        
        # Load cross-age master team list if available
        self.cross_age_master_df = None
        if self.cross_age_master_file and os.path.exists(self.cross_age_master_file):
            self.cross_age_master_df = pd.read_csv(self.cross_age_master_file)
            print(f"Loaded {len(self.cross_age_master_df)} cross-age master teams from: {self.cross_age_master_file}")
        
        # Convert date column
        self.combined_games_df['Date '] = pd.to_datetime(self.combined_games_df['Date '])
        
        # Filter to last 18 months
        cutoff_date = datetime.now() - timedelta(days=18*30)
        self.combined_games_df = self.combined_games_df[self.combined_games_df['Date '] >= cutoff_date]
        print(f"Games in last 18 months: {len(self.combined_games_df)}")
        
        # Create combined team-to-state mapping
        self.team_to_state = {}
        
        # Add primary teams
        if 'State_Code' in self.master_df.columns:
            primary_mapping = self.master_df.set_index('Team_Name')['State_Code'].to_dict()
        elif 'State' in self.master_df.columns:
            primary_mapping = self.master_df.set_index('Team_Name')['State'].to_dict()
        else:
            primary_mapping = {}
        
        # Add cross-age teams
        if self.cross_age_master_df is not None:
            if 'State_Code' in self.cross_age_master_df.columns:
                cross_age_mapping = self.cross_age_master_df.set_index('Team_Name')['State_Code'].to_dict()
            elif 'State' in self.cross_age_master_df.columns:
                cross_age_mapping = self.cross_age_master_df.set_index('Team_Name')['State'].to_dict()
            else:
                cross_age_mapping = {}
        else:
            cross_age_mapping = {}
        
        # Combine mappings
        self.team_to_state.update(primary_mapping)
        self.team_to_state.update(cross_age_mapping)
        
        print(f"Created combined team-to-state mapping for {len(self.team_to_state)} teams")
        
        return self.combined_games_df, self.master_df, self.cross_age_master_df
    
    def filter_for_age_group_games(self):
        """Filter for games involving the target age group."""
        print(f"\n=== FILTERING FOR {self.age_group} GAMES WITH CROSS-AGE SUPPORT ===")
        
        # Get teams from master lists
        primary_teams = set(self.master_df['Team_Name'].unique())
        cross_age_teams = set(self.cross_age_master_df['Team_Name'].unique()) if self.cross_age_master_df is not None else set()
        all_master_teams = primary_teams | cross_age_teams
        
        print(f"{self.age_group} teams in master list: {len(primary_teams)}")
        if self.cross_age_master_df is not None:
            print(f"Cross-age teams in master list: {len(cross_age_teams)}")
        print(f"Total teams in master lists: {len(all_master_teams)}")
        
        # Filter for games where Team A is the target age group
        age_group_games = self.combined_games_df[
            (self.combined_games_df['Team A Age Group '] == f'U{self.age_group}') &
            (self.combined_games_df['Team A '].isin(primary_teams))
        ].copy()
        
        # Also include games where Team B is the target age group (regardless of Team A age)
        team_b_games = self.combined_games_df[
            (self.combined_games_df['Team B '].isin(primary_teams)) &
            (self.combined_games_df['Team A '].isin(all_master_teams))
        ].copy()
        
        # Combine games
        self.age_group_games_df = pd.concat([age_group_games, team_b_games]).drop_duplicates()
        
        print(f"Total combined games: {len(self.combined_games_df)}")
        print(f"{self.age_group} games (including cross-age): {len(self.age_group_games_df)}")
        
        # Analyze cross-age games
        if self.cross_age_master_df is not None:
            cross_age_games = self.age_group_games_df[
                (self.age_group_games_df['Team A Age Group '] == f'U{self.age_group}') & 
                (self.age_group_games_df['Team B '].isin(cross_age_teams))
            ]
            print(f"Cross-age games ({self.age_group} vs {self.age_group[:-1] if self.age_group != '10' else '11'}): {len(cross_age_games)}")
        
        # Get unique teams from games
        teams_in_games = set(self.age_group_games_df['Team A '].unique()) | set(self.age_group_games_df['Team B '].unique())
        print(f"Unique teams in {self.age_group} games: {len(teams_in_games)}")
        
        return self.age_group_games_df
    
    def build_team_game_histories(self):
        """Build comprehensive game histories including cross-age games."""
        print(f"\n=== BUILDING TEAM GAME HISTORIES FOR {self.age_group} ===")
        
        # Get teams from master list that have games
        primary_teams = set(self.master_df['Team_Name'].unique())
        teams_with_games = set(self.age_group_games_df['Team A '].unique()) | set(self.age_group_games_df['Team B '].unique())
        teams_to_rank = primary_teams & teams_with_games
        
        print(f"{self.age_group} teams in master list: {len(primary_teams)}")
        print(f"Teams with {self.age_group} games: {len(teams_with_games)}")
        print(f"{self.age_group} teams to rank: {len(teams_to_rank)}")
        
        # Build histories
        histories = []
        
        for team in teams_to_rank:
            # Get games where team is Team A
            team_a_games = self.age_group_games_df[self.age_group_games_df['Team A '] == team].copy()
            team_a_games['Team'] = team
            team_a_games['Opponent'] = team_a_games['Team B ']
            team_a_games['Score_For'] = team_a_games['Score A ']
            team_a_games['Score_Against'] = team_a_games['Score B ']
            team_a_games['Result'] = team_a_games['Team A Result']
            team_a_games['Is_Home'] = True
            
            # Determine opponent age group
            if self.cross_age_master_df is not None:
                cross_age_teams = set(self.cross_age_master_df['Team_Name'].unique())
                team_a_games['Opponent_Age_Group'] = team_a_games['Team B '].apply(
                    lambda x: f'U{self.age_group[:-1] if self.age_group != "10" else "11"}' if x in cross_age_teams else f'U{self.age_group}'
                )
            else:
                team_a_games['Opponent_Age_Group'] = f'U{self.age_group}'
            
            # Get games where team is Team B
            team_b_games = self.age_group_games_df[self.age_group_games_df['Team B '] == team].copy()
            team_b_games['Team'] = team
            team_b_games['Opponent'] = team_b_games['Team A ']
            team_b_games['Score_For'] = team_b_games['Score B ']
            team_b_games['Score_Against'] = team_b_games['Score A ']
            # For Team B, we need to reverse the result
            team_b_games['Result'] = team_b_games['Team A Result'].map({'W': 'L', 'L': 'W', 'T': 'T'})
            team_b_games['Is_Home'] = False
            
            # Determine opponent age group
            if self.cross_age_master_df is not None:
                cross_age_teams = set(self.cross_age_master_df['Team_Name'].unique())
                team_b_games['Opponent_Age_Group'] = team_b_games['Team A '].apply(
                    lambda x: f'U{self.age_group[:-1] if self.age_group != "10" else "11"}' if x in cross_age_teams else f'U{self.age_group}'
                )
            else:
                team_b_games['Opponent_Age_Group'] = f'U{self.age_group}'
            
            # Combine and sort by date
            team_games = pd.concat([team_a_games, team_b_games])
            team_games = team_games.sort_values('Date ')
            
            # Add to histories
            for _, game in team_games.iterrows():
                histories.append({
                    'Team': team,
                    'Opponent': game['Opponent'],
                    'Date': game['Date '],
                    'Score_For': game['Score_For'],
                    'Score_Against': game['Score_Against'],
                    'Result': game['Result'],
                    'Event': game['Event'],
                    'Is_Home': game['Is_Home'],
                    'Opponent_Age_Group': game['Opponent_Age_Group'],
                    'Cross_State': game['Team A State '] != self.team_to_state.get(game['Opponent'], 'Unknown') if 'Team A State ' in game else False
                })
        
        self.histories_df = pd.DataFrame(histories)
        print(f"Built {len(self.histories_df)} game history records")
        
        # Analyze cross-age games in histories
        if self.cross_age_master_df is not None:
            cross_age_histories = self.histories_df[self.histories_df['Opponent_Age_Group'] != f'U{self.age_group}']
            print(f"Cross-age game histories: {len(cross_age_histories)}")
        
        return self.histories_df
    
    def calculate_team_stats(self):
        """Calculate comprehensive team statistics."""
        print(f"\n=== CALCULATING TEAM STATISTICS FOR {self.age_group} ===")
        
        team_stats = []
        
        for team in self.histories_df['Team'].unique():
            team_games = self.histories_df[self.histories_df['Team'] == team].copy()
            team_games = team_games.sort_values('Date')
            
            # Filter to ranking window
            cutoff_date = datetime.now() - timedelta(days=self.ranking_window_days)
            recent_games = team_games[team_games['Date'] >= cutoff_date]
            
            if len(recent_games) == 0:
                continue
            
            # Limit to max games
            if len(recent_games) > self.max_games:
                recent_games = recent_games.tail(self.max_games)
            
            # Basic stats
            total_games = len(recent_games)  # Games used for ranking (max 30)
            total_games_history = len(team_games)  # Total games in team history
            wins = len(recent_games[recent_games['Result'] == 'W'])
            losses = len(recent_games[recent_games['Result'] == 'L'])
            ties = len(recent_games[recent_games['Result'] == 'T'])
            
            # Goal stats
            # Calculate goal differential with cap at ±6 goals per game
            goal_diff_cap = 6
            capped_goal_diffs = []
            
            for _, game in recent_games.iterrows():
                game_diff = game['Score_For'] - game['Score_Against']
                # Cap individual game differential at ±6
                capped_diff = max(-goal_diff_cap, min(goal_diff_cap, game_diff))
                capped_goal_diffs.append(capped_diff)
            
            goal_differential = sum(capped_goal_diffs)
            goals_for = recent_games['Score_For'].sum()
            goals_against = recent_games['Score_Against'].sum()
            
            # Win percentage
            win_pct = wins / total_games if total_games > 0 else 0
            
            # Tiered performance weighting (last 30 games)
            # Games 1-15 (most recent): 50% weight
            # Games 16-25 (middle): 35% weight  
            # Games 26-30 (oldest): 15% weight
            
            recent_15 = recent_games.tail(min(15, len(recent_games)))
            middle_10 = recent_games.tail(min(25, len(recent_games))).head(min(10, len(recent_games) - 15)) if len(recent_games) > 15 else pd.DataFrame()
            oldest_5 = recent_games.tail(min(30, len(recent_games))).head(min(5, len(recent_games) - 25)) if len(recent_games) > 25 else pd.DataFrame()
            
            # Calculate weighted win percentage
            recent_wins = len(recent_15[recent_15['Result'] == 'W']) if len(recent_15) > 0 else 0
            middle_wins = len(middle_10[middle_10['Result'] == 'W']) if len(middle_10) > 0 else 0
            oldest_wins = len(oldest_5[oldest_5['Result'] == 'W']) if len(oldest_5) > 0 else 0
            
            recent_win_pct = recent_wins / len(recent_15) if len(recent_15) > 0 else 0
            middle_win_pct = middle_wins / len(middle_10) if len(middle_10) > 0 else 0
            oldest_win_pct = oldest_wins / len(oldest_5) if len(oldest_5) > 0 else 0
            
            # Calculate weighted average
            weighted_win_pct = (
                self.recent_weight * recent_win_pct +
                self.middle_weight * middle_win_pct +
                self.oldest_weight * oldest_win_pct
            )
            
            # Cross-age games
            cross_age_games = len(recent_games[recent_games['Opponent_Age_Group'] != f'U{self.age_group}'])
            cross_age_pct = cross_age_games / total_games if total_games > 0 else 0
            
            # Cross-state games
            cross_state_games = len(recent_games[recent_games['Cross_State'] == True])
            cross_state_pct = cross_state_games / total_games if total_games > 0 else 0
            
            # State assignment from master team list
            team_state = self.team_to_state.get(team, 'Unknown')
            
            team_stats.append({
                'Team': team,
                'State': team_state,
                'Games_Played': total_games,  # Games used for ranking (max 30)
                'Total_Games_History': total_games_history,  # Total games in team history
                'Wins': wins,
                'Losses': losses,
                'Ties': ties,
                'Win_Percentage': win_pct,
                'Goals_For': goals_for,
                'Goals_Against': goals_against,
                'Goal_Differential': goal_differential,
                'Recent_Win_Pct': weighted_win_pct,
                'Cross_Age_Games': cross_age_games,
                'Cross_Age_Pct': cross_age_pct,
                'Cross_State_Games': cross_state_games,
                'Cross_State_Pct': cross_state_pct,
                'Last_Game_Date': recent_games['Date'].max()
            })
        
        self.team_stats_df = pd.DataFrame(team_stats)
        print(f"Calculated stats for {len(self.team_stats_df)} teams")
        
        # Show state distribution
        print(f"\nState distribution:")
        state_counts = self.team_stats_df['State'].value_counts().head(10)
        for state, count in state_counts.items():
            print(f"  {state}: {count} teams")
        
        # Show cross-age game statistics
        if self.cross_age_master_df is not None:
            avg_cross_age = self.team_stats_df['Cross_Age_Pct'].mean()
            print(f"\nCross-age game statistics:")
            print(f"  Average cross-age game percentage: {avg_cross_age:.1%}")
            print(f"  Teams with cross-age games: {len(self.team_stats_df[self.team_stats_df['Cross_Age_Games'] > 0])}")
        
        return self.team_stats_df
    
    def calculate_strength_of_schedule(self):
        """Calculate strength of schedule including cross-age opponents using iterative method."""
        print(f"\n=== CALCULATING STRENGTH OF SCHEDULE FOR {self.age_group} ===")
        
        # Calculate SOS using iterative method
        print("Calculating iterative SOS...")
        sos_scores = self.calculate_iterative_sos()
        
        self.sos_df = pd.DataFrame(sos_scores)
        
        # Merge with team stats
        self.team_stats_df = self.team_stats_df.merge(self.sos_df, on='Team', how='left')
        
        print(f"Calculated SOS for {len(self.sos_df)} teams")
        if self.cross_age_master_df is not None:
            print(f"Teams with cross-age opponents: {len(self.sos_df[self.sos_df['Cross_Age_Opponents'] > 0])}")
        
        return self.team_stats_df
    
    def apply_performance_adjustment(self):
        """
        Apply expected vs actual performance adjustment.
        Rewards teams that outperform expectations based on Power Score strength.
        """
        print(f"\n=== APPLYING PERFORMANCE ADJUSTMENT FOR {self.age_group} ===")
        
        # Calculate initial power scores for expected performance
        self.calculate_power_scores()
        
        # Get team power scores for expected margin calculation
        team_power_scores = {}
        for _, row in self.team_stats_df.iterrows():
            team_power_scores[row['Team']] = row['Power_Score']
        
        # Calculate performance adjustments
        performance_adjustments = {team: 0.0 for team in team_power_scores.keys()}
        
        for team in team_power_scores.keys():
            team_games = self.histories_df[self.histories_df['Team'] == team]
            
            # Filter to ranking window
            cutoff_date = datetime.now() - timedelta(days=self.ranking_window_days)
            recent_games = team_games[team_games['Date'] >= cutoff_date]
            
            if len(recent_games) > self.max_games:
                recent_games = recent_games.tail(self.max_games)
            
            total_perf_delta = 0
            game_count = 0
            
            for _, game in recent_games.iterrows():
                opponent = game['Opponent']
                
                # Only calculate for known opponents
                if opponent in team_power_scores:
                    # Expected margin based on Power Score difference (more comprehensive)
                    expected_margin = 6 * (team_power_scores[team] - team_power_scores[opponent])
                    
                    # Actual margin (capped at ±6)
                    actual_margin = np.clip(game['Score_For'] - game['Score_Against'], -6, 6)
                    
                    # Performance delta
                    perf_delta = actual_margin - expected_margin
                    total_perf_delta += perf_delta
                    game_count += 1
            
            if game_count > 0:
                avg_perf_delta = total_perf_delta / game_count
                performance_adjustments[team] = 0.02 * avg_perf_delta  # Small learning rate
        
        # Apply adjustments to SOS scores (final adjustment)
        for team, adjustment in performance_adjustments.items():
            mask = self.team_stats_df['Team'] == team
            self.team_stats_df.loc[mask, 'SOS_Score'] = self.team_stats_df.loc[mask, 'SOS_Score'] + adjustment
        
        # Log statistics
        adjustments = list(performance_adjustments.values())
        print(f"Performance adjustments applied (Power Score-based):")
        print(f"  Mean adjustment: {np.mean(adjustments):.4f}")
        print(f"  Std adjustment: {np.std(adjustments):.4f}")
        print(f"  Max positive: {np.max(adjustments):.4f}")
        print(f"  Max negative: {np.min(adjustments):.4f}")
        
        return self.team_stats_df
    
    def calculate_iterative_sos(self):
        """Calculate SOS using simplified iterative method with goal differential cap."""
        print("Using simplified iterative SOS calculation...")
        
        # Initialize team strengths (start with win percentages)
        team_strengths = {}
        for _, team_stat in self.team_stats_df.iterrows():
            team = team_stat['Team']
            team_strengths[team] = team_stat['Win_Percentage']
        
        # Add cross-age team strengths if available
        if self.cross_age_master_df is not None:
            cross_age_teams = set(self.cross_age_master_df['Team_Name'].unique())
            cross_age_games = self.combined_games_df[
                (self.combined_games_df['Team A Age Group '] == f'U{self.age_group[:-1] if self.age_group != "10" else "11"}') &
                (self.combined_games_df['Team A '].isin(cross_age_teams))
            ]
            
            for team in cross_age_teams:
                team_games = cross_age_games[cross_age_games['Team A '] == team]
                if len(team_games) > 0:
                    wins = len(team_games[team_games['Team A Result'] == 'W'])
                    total_games = len(team_games)
                    win_pct = wins / total_games if total_games > 0 else 0.5
                    team_strengths[team] = win_pct
        
        # Calculate average team strength for conditional cross-age multiplier
        avg_team_strength = np.mean([team_strengths[team] for team in team_strengths.keys()]) if team_strengths else 0.5
        print(f"Average {self.age_group} team strength: {avg_team_strength:.3f}")
        
        # Iterative SOS calculation (simplified version)
        max_iterations = 10
        convergence_threshold = 0.01
        
        for iteration in range(max_iterations):
            old_strengths = team_strengths.copy()
            
            # Calculate new strengths based on opponent performance
            for team in team_strengths.keys():
                team_games = self.histories_df[self.histories_df['Team'] == team]
                
                # Filter to ranking window
                cutoff_date = datetime.now() - timedelta(days=self.ranking_window_days)
                recent_games = team_games[team_games['Date'] >= cutoff_date]
                
                if len(recent_games) > self.max_games:
                    recent_games = recent_games.tail(self.max_games)
                
                if len(recent_games) == 0:
                    continue
                
                # Calculate weighted opponent strength
                weighted_opponent_strength = 0
                total_weight = 0
                
                for _, game in recent_games.iterrows():
                    opponent = game['Opponent']
                    opponent_strength = team_strengths.get(opponent, self.default_opponent_strength)
                    
                    # IMPROVED: Proportional cross-age multiplier (scales with strength difference, capped at +10%)
                    if game['Opponent_Age_Group'] != f'U{self.age_group}':
                        if opponent_strength > avg_team_strength:
                            # Calculate proportional boost based on strength difference
                            strength_ratio = (opponent_strength - avg_team_strength) / avg_team_strength
                            boost_factor = 1 + 0.05 * strength_ratio  # scales 0-10%
                            opponent_strength *= min(boost_factor, 1.10)  # cap at +10%
                            # Optional: Log when boost is applied for debugging
                            # print(f"Proportional boost for {game['Opponent_Age_Group']} opponent {opponent}: {strength_ratio:.3f} ratio -> {boost_factor:.3f} factor")
                        # This prevents weak cross-age teams from inflating SOS
                    
                    # Apply goal differential cap for weighting
                    score_for = game['Score_For']
                    score_against = game['Score_Against']
                    goal_diff = score_for - score_against
                    capped_diff = max(-6, min(6, goal_diff))
                    
                    # Weight based on game result and margin (with caps)
                    if game['Result'] == 'W':
                        weight = min(1.6, 1.0 + 0.1 * capped_diff)
                    elif game['Result'] == 'L':
                        weight = max(0.4, 1.0 - 0.1 * abs(capped_diff))
                    else:  # Tie
                        weight = 1.0
                    
                    weighted_opponent_strength += opponent_strength * weight
                    total_weight += weight
                
                if total_weight > 0:
                    # Update team strength (blend with previous strength)
                    new_strength = weighted_opponent_strength / total_weight
                    team_strengths[team] = 0.7 * team_strengths[team] + 0.3 * new_strength
            
            # Check convergence
            max_change = max(abs(team_strengths[team] - old_strengths[team]) for team in team_strengths.keys())
            if max_change < convergence_threshold:
                print(f"Converged after {iteration + 1} iterations (max change: {max_change:.4f})")
                break
        
        # NEW: Normalize SOS across both age groups
        sos_values = np.array(list(team_strengths.values()))
        mean_sos, std_sos = sos_values.mean(), sos_values.std()
        team_strengths = {t: (s - mean_sos) / std_sos for t, s in team_strengths.items()}
        print(f"SOS normalized: mean={mean_sos:.3f}, std={std_sos:.3f}")
        
        # Convert to list format
        sos_scores = []
        for team in self.team_stats_df['Team']:
            team_games = self.histories_df[self.histories_df['Team'] == team]
            
            # Filter to ranking window
            cutoff_date = datetime.now() - timedelta(days=self.ranking_window_days)
            recent_games = team_games[team_games['Date'] >= cutoff_date]
            
            if len(recent_games) > self.max_games:
                recent_games = recent_games.tail(self.max_games)
            
            # Get iterative SOS score
            iterative_sos = team_strengths.get(team, self.default_opponent_strength)
            
            sos_scores.append({
                'Team': team,
                'SOS_Score': iterative_sos,
                'Opponents_Count': len(recent_games),
                'Cross_Age_Opponents': len([g for _, g in recent_games.iterrows() if g['Opponent_Age_Group'] != f'U{self.age_group}'])
            })
        
        return sos_scores
    
    def calculate_power_scores(self):
        """Calculate V5.3E Enhanced power scores."""
        print(f"\n=== CALCULATING POWER SCORES FOR {self.age_group} ===")
        
        # Calculate offense and defense metrics (goals per game)
        self.team_stats_df['Offense'] = self.team_stats_df['Goals_For'] / self.team_stats_df['Games_Played']
        self.team_stats_df['Defense'] = self.team_stats_df['Goals_Against'] / self.team_stats_df['Games_Played']
        
        # NEW: Bayesian Shrinkage 2.0 - Stabilize low-sample teams
        tau = 8  # Regularization constant
        mu_off = self.team_stats_df['Offense'].mean()
        mu_def = self.team_stats_df['Defense'].mean()
        
        self.team_stats_df['Offense_Adj'] = (
            (self.team_stats_df['Games_Played'] * self.team_stats_df['Offense'] + tau * mu_off)
            / (self.team_stats_df['Games_Played'] + tau)
        )
        self.team_stats_df['Defense_Adj'] = (
            (self.team_stats_df['Games_Played'] * self.team_stats_df['Defense'] + tau * mu_def)
            / (self.team_stats_df['Games_Played'] + tau)
        )
        
        print(f"Bayesian shrinkage applied: τ={tau}, mean_off={mu_off:.2f}, mean_def={mu_def:.2f}")
        
        # Normalize metrics using logistic normalization (use adjusted values)
        μ_off, σ_off = self.team_stats_df['Offense_Adj'].mean(), self.team_stats_df['Offense_Adj'].std()
        self.team_stats_df['Offense_Norm'] = 1 / (1 + np.exp(-(self.team_stats_df['Offense_Adj'] - μ_off) / (σ_off * 1.5)))
        
        μ_def, σ_def = self.team_stats_df['Defense_Adj'].mean(), self.team_stats_df['Defense_Adj'].std()
        self.team_stats_df['Defense_Norm'] = 1 / (1 + np.exp(-(self.team_stats_df['Defense_Adj'] - μ_def) / (σ_def * 1.5)))
        
        μ_sos, σ_sos = self.team_stats_df['SOS_Score'].mean(), self.team_stats_df['SOS_Score'].std()
        self.team_stats_df['SOS_Norm'] = 1 / (1 + np.exp(-(self.team_stats_df['SOS_Score'] - μ_sos) / (σ_sos * 1.5)))
        
        # Note: Defense should be inverted AFTER normalization since lower is better
        self.team_stats_df['Defense_Norm'] = 1 - self.team_stats_df['Defense_Norm']
        
        # Calculate power score (V5.3E Enhanced formula with offense/defense)
        self.team_stats_df['Power_Score'] = (
            0.20 * self.team_stats_df['Offense_Norm'] +
            0.20 * self.team_stats_df['Defense_Norm'] +
            0.60 * self.team_stats_df['SOS_Norm']
        )
        
        # Apply game count penalty (provisional teams) - cap at 1.0 for 30+ games
        self.team_stats_df['Games_Penalty'] = np.minimum(
            np.power(self.team_stats_df['Games_Played'] / 20, 0.5), 
            1.0
        )
        self.team_stats_df['Power_Score_Adj'] = self.team_stats_df['Power_Score'] * self.team_stats_df['Games_Penalty']
        
        print(f"Power scores calculated using V5.3E Enhanced algorithm")
        
        return self.team_stats_df
    
    def generate_rankings(self):
        """Generate final rankings."""
        print(f"\n=== GENERATING {self.age_group} RANKINGS ===")
        
        # Sort by adjusted power score
        rankings_df = self.team_stats_df.copy()
        rankings_df = rankings_df.sort_values('Power_Score_Adj', ascending=False)
        rankings_df['National_Rank'] = range(1, len(rankings_df) + 1)
        
        # Add status
        rankings_df['Status'] = 'Active'
        rankings_df.loc[rankings_df['Games_Played'] < 5, 'Status'] = 'Provisional'
        rankings_df.loc[rankings_df['Last_Game_Date'] < datetime.now() - timedelta(days=180), 'Status'] = 'Inactive'
        
        self.rankings_df = rankings_df
        
        print(f"Generated rankings for {len(rankings_df)} teams")
        
        return self.rankings_df
    
    def generate_state_rankings(self):
        """Generate state-specific rankings."""
        print(f"\n=== GENERATING STATE RANKINGS FOR {self.age_group} ===")
        
        state_rankings = {}
        
        for state in self.rankings_df['State'].unique():
            if state == 'Unknown':
                continue
                
            state_teams = self.rankings_df[self.rankings_df['State'] == state].copy()
            state_teams = state_teams.sort_values('Power_Score_Adj', ascending=False)
            state_teams['State_Rank'] = range(1, len(state_teams) + 1)
            
            state_rankings[state] = state_teams
            
            print(f"{state}: {len(state_teams)} teams")
        
        self.state_rankings = state_rankings
        
        return state_rankings
    
    def save_results(self):
        """Save all results to files."""
        print(f"\n=== SAVING {self.age_group} RESULTS ===")
        
        # National rankings
        national_file = os.path.join(self.output_dir, f"National_U{self.age_group}_{self.gender}_Rankings.csv")
        self.rankings_df.to_csv(national_file, index=False)
        print(f"Saved {self.age_group} {self.gender} national rankings: {national_file}")
        
        # State rankings
        for state, state_df in self.state_rankings.items():
            state_file = os.path.join(self.output_dir, f"U{self.age_group}_{self.gender}_Rankings_{state}.csv")
            state_df.to_csv(state_file, index=False)
            print(f"Saved {self.age_group} {self.gender} {state} rankings: {state_file}")
        
        # Summary report
        self.generate_summary_report()
        
        return national_file
    
    def generate_summary_report(self):
        """Generate comprehensive summary report."""
        print(f"\n=== GENERATING {self.age_group} SUMMARY REPORT ===")
        
        report = []
        report.append(f"U{self.age_group} {self.gender} SOCCER RANKINGS SUMMARY")
        report.append("=" * 50)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Combined Game History: {self.combined_games_file}")
        report.append(f"{self.age_group} Master Team List: {self.master_file}")
        if self.cross_age_master_file:
            report.append(f"Cross-Age Master Team List: {self.cross_age_master_file}")
        report.append(f"Total Teams Ranked: {len(self.rankings_df)}")
        report.append(f"Total {self.age_group} Games: {len(self.age_group_games_df):,}")
        report.append(f"Ranking Window: {self.ranking_window_days} days")
        report.append("")
        
        # Cross-age statistics
        if self.cross_age_master_df is not None:
            cross_age_teams = len(self.rankings_df[self.rankings_df['Cross_Age_Games'] > 0])
            avg_cross_age = self.rankings_df['Cross_Age_Pct'].mean()
            report.append("CROSS-AGE GAME STATISTICS:")
            report.append("-" * 30)
            report.append(f"Teams with cross-age games: {cross_age_teams}")
            report.append(f"Average cross-age game percentage: {avg_cross_age:.1%}")
            report.append("")
        
        # Top 10 nationally
        report.append(f"TOP 10 NATIONAL U{self.age_group} RANKINGS:")
        report.append("-" * 35)
        top_10 = self.rankings_df.head(10)
        for _, team in top_10.iterrows():
            cross_age_info = f" ({team['Cross_Age_Games']} cross-age)" if team['Cross_Age_Games'] > 0 else ""
            report.append(f"{team['National_Rank']:2d}. {team['Team']} ({team['State']}) - {team['Power_Score_Adj']:.3f}{cross_age_info}")
        report.append("")
        
        # State breakdown
        report.append("STATE BREAKDOWN:")
        report.append("-" * 20)
        for state in sorted([s for s in self.state_rankings.keys() if s != 'Unknown']):
            state_df = self.state_rankings[state]
            top_team = state_df.iloc[0]
            cross_age_info = f" ({top_team['Cross_Age_Games']} cross-age)" if top_team['Cross_Age_Games'] > 0 else ""
            report.append(f"{state}: {len(state_df)} teams - Top: {top_team['Team']} (#{top_team['National_Rank']} nationally){cross_age_info}")
        report.append("")
        
        # Arizona specific
        if 'AZ' in self.state_rankings:
            az_df = self.state_rankings['AZ']
            report.append(f"ARIZONA U{self.age_group} RANKINGS:")
            report.append("-" * 25)
            report.append(f"Total Arizona teams: {len(az_df)}")
            report.append("Top 5 Arizona teams:")
            for _, team in az_df.head(5).iterrows():
                cross_age_info = f" ({team['Cross_Age_Games']} cross-age)" if team['Cross_Age_Games'] > 0 else ""
                report.append(f"  {team['State_Rank']:2d}. {team['Team']} (#{team['National_Rank']} nationally){cross_age_info}")
        
        # Save report
        report_file = os.path.join(self.output_dir, f"U{self.age_group}_{self.gender}_Rankings_Summary.txt")
        with open(report_file, 'w') as f:
            f.write('\n'.join(report))
        
        print(f"Saved {self.age_group} {self.gender} summary report: {report_file}")
        
        # Print to console
        print('\n'.join(report))
        
        return report_file
    
    def run(self):
        """Run the complete rankings generation."""
        print("=" * 60)
        print(f"U{self.age_group} {self.gender} SOCCER RANKINGS GENERATOR")
        print("=" * 60)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # Load data
            self.load_data()
            
            # Filter for age group games
            self.filter_for_age_group_games()
            
            # Build game histories
            self.build_team_game_histories()
            
            # Calculate statistics
            self.calculate_team_stats()
            
            # Calculate strength of schedule
            self.calculate_strength_of_schedule()
            
            # NEW: Apply performance adjustment (includes power score calculation)
            self.apply_performance_adjustment()
            
            # Generate rankings
            self.generate_rankings()
            
            # Generate state rankings
            self.generate_state_rankings()
            
            # Save results
            self.save_results()
            
            print(f"\n{'='*60}")
            print(f"U{self.age_group} {self.gender} RANKINGS GENERATION COMPLETE")
            print(f"{'='*60}")
            print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            return self.rankings_df, self.state_rankings
            
        except Exception as e:
            print(f"❌ Error during processing: {e}")
            raise

def main():
    """Main function with command line argument support."""
    parser = argparse.ArgumentParser(description='Generate youth soccer rankings for any age group')
    parser.add_argument('--age', required=True, help='Age group (e.g., 10, 11, 12)')
    parser.add_argument('--gender', default='M', help='Gender (M or F)')
    
    args = parser.parse_args()
    
    generator = YouthSoccerRankingsGenerator(args.age, args.gender)
    rankings, state_rankings = generator.run()
    return rankings, state_rankings

if __name__ == "__main__":
    main()
