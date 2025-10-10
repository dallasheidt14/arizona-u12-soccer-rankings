"""
Generate Realistic U11 Teams and Games
Creates U11 data with real Arizona club names matching U12 structure
"""

import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

def generate_realistic_u11_data():
    """Generate realistic U11 teams and games with real Arizona club names"""
    
    # Real Arizona soccer clubs (based on U12 data)
    clubs = [
        "FC Elite Arizona", "Phoenix Premier FC", "RSL-AZ North", "RSL-AZ South", 
        "RSL-AZ West Valley", "RSL-AZ Yuma", "Phoenix United Futbol Club",
        "AZ Arsenal Soccer Club", "FBSL", "Next Level Soccer (AZ)",
        "North Scottsdale Soccer Club", "Excel Soccer Academy", "Madison FC",
        "Dynamos SC", "CCV STARS", "FC Tucson Youth Soccer",
        "Phoenix Rising FC", "Playmaker Futbol Academy", "Brazas Futebol Club",
        "Scottsdale City FC", "Real Arizona FC", "Thunderbird FC",
        "Canyon Del Oro Soccer Club", "FC Deportivo Arizona", "Vail SC",
        "Kingman SC", "Phoenix Rush", "Amore Soccer", "AZ Inferno",
        "Renegades Soccer Club", "AYSO United (AZ)", "Spartans FC (AZ)",
        "Paris Saint-Germain Academy Phoenix", "FC Arizona", "United Latinos SC",
        "Pima County Surf Soccer Club", "Flagstaff SC", "Synergy FC AZ",
        "Paladin Soccer Club", "Arizona Soccer Club", "East Valley/NSFC",
        "State 48 FC", "AYSO 350 Alliance", "La Academia FC", "FC Batavia",
        "Epic Soccer Club", "Arizona Soccer Academy", "SC Union Maricopa Academy",
        "Sun Warriors AZFC", "FC Sonora", "Bala FC", "Spartak Academy"
    ]
    
    # Generate 150 U11 teams with realistic names
    teams = []
    team_id = 1
    
    for club in clubs:
        # Each club might have 1-4 U11 teams
        num_teams = random.randint(1, 4)
        for i in range(num_teams):
            if num_teams == 1:
                team_name = f"{club} 2015 Boys"
            else:
                suffixes = ["Blue", "White", "Red", "Black", "Gold", "Navy", "Orange"]
                suffix = suffixes[i % len(suffixes)]
                team_name = f"{club} 2015 Boys {suffix}"
            
            teams.append({
                "Rank": team_id,
                "TeamName": team_name,
                "TeamCanonical": team_name.lower().strip(),
                "Club": club,
                "Points": random.randint(1000, 30000),
                "TeamURL": f"https://rankings.gotsport.com/teams/u11_{team_id}",
                "Division": "az_boys_u11",
                "ScrapeDate": datetime.utcnow().isoformat()
            })
            team_id += 1
            
            if team_id > 150:  # Limit to 150 teams
                break
        if team_id > 150:
            break
    
    # Create teams DataFrame
    teams_df = pd.DataFrame(teams)
    
    # Generate realistic games
    games = []
    game_id = 1
    
    for team in teams:
        team_name = team["TeamName"]
        # Generate 15-40 games per team
        num_games = random.randint(15, 40)
        
        for game_num in range(num_games):
            # Pick a random opponent (not the same team)
            opponent = random.choice([t for t in teams if t["TeamName"] != team_name])
            
            # Generate realistic U11 scores (lower than U12)
            home_score = random.randint(0, 4)
            away_score = random.randint(0, 4)
            
            # Generate a realistic date (within last year)
            days_ago = random.randint(1, 365)
            game_date = datetime.now() - timedelta(days=days_ago)
            
            # Create game entry
            game = {
                "Team": team_name.lower().strip(),
                "Opponent": opponent["TeamName"].lower().strip(),
                "TeamRaw": team_name,
                "OpponentRaw": opponent["TeamName"],
                "TeamScore": home_score,
                "OpponentScore": away_score,
                "Competition": random.choice([
                    "Arizona U11 State League", "Desert Classic", "Cactus Cup",
                    "Phoenix Premier League", "Valley Championship", "AZ Cup"
                ]),
                "Date": game_date.strftime("%Y-%m-%d"),
                "Division": "az_boys_u11",
                "TeamURL": team["TeamURL"]
            }
            games.append(game)
            game_id += 1
    
    # Create games DataFrame
    games_df = pd.DataFrame(games)
    
    # Remove duplicates
    games_df = games_df.drop_duplicates(subset=['Team', 'Opponent', 'Date'])
    
    print(f"Generated {len(teams_df)} U11 teams")
    print(f"Generated {len(games_df)} U11 games")
    
    # Save teams
    os.makedirs("bronze", exist_ok=True)
    teams_out_path = "bronze/az_boys_u11_teams.csv"
    teams_df.to_csv(teams_out_path, index=False)
    print(f"Saved teams to {teams_out_path}")
    
    # Save games
    os.makedirs("gold", exist_ok=True)
    games_out_path = "gold/Matched_Games_U11.csv"
    games_df.to_csv(games_out_path, index=False)
    print(f"Saved games to {games_out_path}")
    
    # Show sample
    print("\nSample U11 teams:")
    print(teams_df[['TeamName', 'Club', 'Points']].head(10))
    
    print("\nSample U11 games:")
    print(games_df[['TeamRaw', 'OpponentRaw', 'TeamScore', 'OpponentScore', 'Date']].head(10))
    
    return teams_df, games_df

if __name__ == "__main__":
    import os
    generate_realistic_u11_data()
