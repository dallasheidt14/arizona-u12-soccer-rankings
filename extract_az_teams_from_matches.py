"""
Extract all Arizona teams from existing match data and create a comprehensive list
"""
import pandas as pd
import re

def extract_az_teams_from_matches():
    # Read the existing match data
    df = pd.read_csv("gold/Matched_Games_AZ_BOYS_U10.csv")
    
    # Get all unique team names
    all_teams = set()
    all_teams.update(df["Team A"].unique())
    all_teams.update(df["Team B"].unique())
    
    # Filter to Arizona teams
    az_teams = []
    for team in all_teams:
        team_lower = team.lower()
        # Check if team name contains Arizona indicators
        if any(indicator in team_lower for indicator in [
            'az ', 'arizona', 'phoenix', 'scottsdale', 'mesa', 'tucson', 
            'chandler', 'glendale', 'tempe', 'peoria', 'surprise', 'gilbert', 
            'avondale', 'goodyear', 'buckeye', 'maricopa', 'pinal',
            'rsl az', 'az arsenal', 'az fc', 'az united', 'az sc',
            'state 48', 'desert', 'cactus', 'valley', 'phoenix rising'
        ]):
            az_teams.append(team)
        # Also check for common Arizona club patterns
        elif any(pattern in team_lower for pattern in [
            'next level soccer', 'tuzos', 'del sol', 'real salt lake',
            'southeast', 'northwest', 'northeast', 'southwest',
            '16b', '15b', '17b', '18b',  # Common Arizona team naming patterns
            'prfc', 'fc tucson', 'legends fc az', 'phoenix premier'
        ]):
            az_teams.append(team)
    
    # Remove duplicates and sort
    az_teams = sorted(list(set(az_teams)))
    
    print(f"Found {len(az_teams)} Arizona teams from match data:")
    for i, team in enumerate(az_teams, 1):
        print(f"{i:2d}. {team}")
    
    # Create a CSV with these teams
    az_teams_df = pd.DataFrame({
        'Team Name': az_teams,
        'TeamID': [f"az_u10_{i+1:03d}" for i in range(len(az_teams))],
        'Points': ['USA:0'] * len(az_teams),
        'TeamURL': [''] * len(az_teams),  # Will need to be filled in
        'Division': ['az_boys_u10'] * len(az_teams),
        'ScrapeDate': ['2025-10-10T15:30:00.000000'] * len(az_teams)
    })
    
    az_teams_df.to_csv("bronze/az_boys_u10_comprehensive_teams.csv", index=False)
    print(f"\nSaved comprehensive Arizona team list to bronze/az_boys_u10_comprehensive_teams.csv")
    
    return az_teams

if __name__ == "__main__":
    extract_az_teams_from_matches()
