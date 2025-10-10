"""
Create U11 Master Team List from Bronze Data
Generates master team list matching U12 format
"""

import pandas as pd
import numpy as np

def create_u11_master_from_bronze():
    """Create U11 master team list from bronze scraped data"""
    
    # Read bronze teams data
    bronze_path = "bronze/az_boys_u11_teams.csv"
    df_bronze = pd.read_csv(bronze_path)
    
    print(f"Loaded {len(df_bronze)} teams from bronze data")
    
    # Read games data to calculate stats
    games_path = "gold/Matched_Games_U11.csv"
    df_games = pd.read_csv(games_path)
    
    print(f"Loaded {len(df_games)} games from gold data")
    
    # Calculate team statistics
    team_stats = {}
    
    for _, team in df_bronze.iterrows():
        team_name = team['TeamName']
        team_canonical = team['TeamCanonical']
        
        # Find games for this team
        team_games = df_games[
            (df_games['Team'] == team_canonical) | 
            (df_games['Opponent'] == team_canonical)
        ]
        
        wins = 0
        losses = 0
        ties = 0
        goals_for = 0
        goals_against = 0
        
        for _, game in team_games.iterrows():
            if game['Team'] == team_canonical:
                # Team is playing
                team_score = game['TeamScore']
                opp_score = game['OpponentScore']
                goals_for += team_score if pd.notna(team_score) else 0
                goals_against += opp_score if pd.notna(opp_score) else 0
                
                if pd.notna(team_score) and pd.notna(opp_score):
                    if team_score > opp_score:
                        wins += 1
                    elif team_score < opp_score:
                        losses += 1
                    else:
                        ties += 1
            else:
                # Team is opponent
                opp_score = game['TeamScore']
                team_score = game['OpponentScore']
                goals_for += team_score if pd.notna(team_score) else 0
                goals_against += opp_score if pd.notna(opp_score) else 0
                
                if pd.notna(team_score) and pd.notna(opp_score):
                    if team_score > opp_score:
                        wins += 1
                    elif team_score < opp_score:
                        losses += 1
                    else:
                        ties += 1
        
        games_played = wins + losses + ties
        win_percentage = wins / games_played if games_played > 0 else 0.0
        goal_ratio = goals_for / goals_against if goals_against > 0 else float('inf')
        
        team_stats[team_name] = {
            'Team ID': f"u11_{team['Rank']}",
            'Wins': wins,
            'Losses': losses,
            'Ties': ties,
            'Games Played': games_played,
            'Goals For': goals_for,
            'Goals Against': goals_against,
            'Win Percentage': win_percentage,
            'Goal Ratio': goal_ratio
        }
    
    # Create master team list
    master_teams = []
    
    for _, team in df_bronze.iterrows():
        team_name = team['TeamName']
        stats = team_stats.get(team_name, {})
        
        master_team = {
            'Team Name': team_name,
            'Club': team['Club'],
            'Team ID': stats.get('Team ID', f"u11_{team['Rank']}"),
            'Wins': stats.get('Wins', 0),
            'Losses': stats.get('Losses', 0),
            'Ties': stats.get('Ties', 0),
            'Games Played': stats.get('Games Played', 0),
            'State': 'AZ',
            'Win Percentage': stats.get('Win Percentage', 0.0),
            'State Rank': team['Rank'],
            'Goal Ratio': stats.get('Goal Ratio', 0.0),
            'Team URL': team['TeamURL'],
            'Gender': 'M',
            'Age Group': 'U11'  # Match U12 structure exactly
        }
        master_teams.append(master_team)
    
    # Create DataFrame
    df_master = pd.DataFrame(master_teams)
    
    # Sort by state rank
    df_master = df_master.sort_values('State Rank')
    
    print(f"Created master team list with {len(df_master)} teams")
    
    # Save master team list
    output_path = "AZ MALE U11 MASTER TEAM LIST.csv"
    df_master.to_csv(output_path, index=False)
    print(f"Saved master team list to {output_path}")
    
    # Show sample
    print("\nSample U11 master team list:")
    print(df_master[['Team Name', 'Club', 'Games Played', 'Wins', 'Losses', 'Win Percentage']].head(10))
    
    return df_master

if __name__ == "__main__":
    create_u11_master_from_bronze()
