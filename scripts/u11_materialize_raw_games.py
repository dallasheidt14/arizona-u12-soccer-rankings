# scripts/u11_materialize_raw_games.py
from pathlib import Path
import pandas as pd
from src.utils.paths_u11 import scraped_histories_path, canonical_raw_path

REQUIRED = {"Team A","Team B","Score A","Score B","Date"}

def run(state: str = "AZ", season: int = 2025) -> None:
    src = scraped_histories_path(state)
    df = pd.read_csv(src)

    # Transform team-centric data to game-centric format
    # Each row represents a game from one team's perspective
    # We need to create Team A vs Team B format
    
    games_data = []
    
    for _, row in df.iterrows():
        team_name = row['team_name']
        opponent_name = row['opponent_name']
        home_score = row['home_score']
        away_score = row['away_score']
        match_date = row['match_date']
        
        # Skip if no opponent name
        if pd.isna(opponent_name) or not opponent_name.strip():
            continue
            
        # Determine which team is Team A and which is Team B
        # Use alphabetical order for consistency
        teams = sorted([team_name, opponent_name])
        
        # Determine scores based on team order
        if teams[0] == team_name:
            # Our team is Team A
            score_a = home_score if not pd.isna(home_score) else 0
            score_b = away_score if not pd.isna(away_score) else 0
        else:
            # Our team is Team B
            score_a = away_score if not pd.isna(away_score) else 0
            score_b = home_score if not pd.isna(home_score) else 0
        
        games_data.append({
            'Team A': teams[0],
            'Team B': teams[1],
            'Score A': score_a,
            'Score B': score_b,
            'Date': match_date,
            'Competition': row.get('competition_name', ''),
            'Event': row.get('event_name', ''),
            'Venue': row.get('venue_name', '')
        })
    
    # Create DataFrame from games data
    df_games = pd.DataFrame(games_data)
    
    # Remove duplicates (same game might appear twice from both teams' perspectives)
    df_games = df_games.drop_duplicates(subset=['Team A', 'Team B', 'Date'])
    
    missing = REQUIRED - set(df_games.columns)
    if missing:
        raise ValueError(f"Missing columns after transformation: {missing}. Available: {list(df_games.columns)}")

    dst = canonical_raw_path(state, season)
    dst.parent.mkdir(parents=True, exist_ok=True)
    df_games.to_csv(dst, index=False)
    print(f"Canonical raw -> {dst} ({len(df_games)} rows)")

if __name__ == "__main__":
    run("AZ", 2025)
