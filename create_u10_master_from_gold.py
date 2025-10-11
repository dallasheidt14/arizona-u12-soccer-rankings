"""
Create U10 Master Team List from Gold Data
Generates master team list from all teams found in match data
"""
import pandas as pd
import numpy as np

def create_u10_master_from_gold():
    """Create U10 master team list from gold match data"""
    
    # Read games data to get all teams
    games_path = "gold/Matched_Games_AZ_BOYS_U10.csv"
    df_games = pd.read_csv(games_path)
    print(f"Loaded {len(df_games)} games from gold data")

    # Get all unique teams from the games data
    all_teams = set(df_games['Team A'].unique()) | set(df_games['Team B'].unique())
    print(f"Found {len(all_teams)} unique teams in games data")

    team_stats = {}
    for idx, team_name in enumerate(sorted(all_teams)):
        team_canonical = team_name.lower() 

        team_games = df_games[
            (df_games['Team A'].str.lower() == team_canonical) | 
            (df_games['Team B'].str.lower() == team_canonical)
        ]

        wins = 0
        losses = 0
        ties = 0
        goals_for = 0
        goals_against = 0

        for _, game in team_games.iterrows():
            team_a_lower = game['Team A'].lower()
            team_b_lower = game['Team B'].lower()

            if team_a_lower == team_canonical:
                team_score = game['Score A']
                opp_score = game['Score B']
            elif team_b_lower == team_canonical:
                team_score = game['Score B']
                opp_score = game['Score A']
            else:
                continue # Should not happen if filtered correctly

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
            'Team ID': f"u10_{idx+1:03d}", # Use idx+1 for 1-based indexing
            'Wins': wins,
            'Losses': losses,
            'Ties': ties,
            'Games Played': games_played,
            'Goals For': goals_for,
            'Goals Against': goals_against,
            'Win Percentage': win_percentage,
            'Goal Ratio': goal_ratio
        }

    master_teams = []
    for idx, team_name in enumerate(sorted(all_teams)):
        stats = team_stats.get(team_name, {})
        
        # Extract club name from team name
        club_name = team_name.split()[0] if team_name.split() else team_name
        
        master_team = {
            'Team Name': team_name.lower(),  # Store canonicalized name
            'Club': club_name,
            'Team ID': stats.get('Team ID', f"u10_{idx+1:03d}"),
            'Wins': stats.get('Wins', 0),
            'Losses': stats.get('Losses', 0),
            'Ties': stats.get('Ties', 0),
            'Games Played': stats.get('Games Played', 0),
            'State': 'AZ',
            'Win Percentage': stats.get('Win Percentage', 0.0),
            'State Rank': idx+1, # Rank by alphabetical order for now
            'Goal Ratio': stats.get('Goal Ratio', 0.0),
            'Team URL': '',  # No URLs available
            'Gender': 'M',
            'Age Group': 'U10'
        }
        master_teams.append(master_team)

    df_master = pd.DataFrame(master_teams)
    output_path = "bronze/AZ MALE u10 MASTER TEAM LIST.csv"
    df_master.to_csv(output_path, index=False)
    print(f"Saved master team list to {output_path}")
    
    print(f"\nSample U10 master team list:")
    print(df_master[['Team Name', 'Club', 'Games Played', 'Wins', 'Losses', 'Win Percentage']].head(10))
    
    # Show top teams by win percentage
    print(f"\nTop 10 teams by win percentage:")
    top_teams = df_master[df_master['Games Played'] > 0].nlargest(10, 'Win Percentage')
    print(top_teams[['Team Name', 'Club', 'Games Played', 'Wins', 'Losses', 'Win Percentage']])
    
    return df_master

if __name__ == "__main__":
    create_u10_master_from_gold()
