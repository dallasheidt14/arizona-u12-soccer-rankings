#!/usr/bin/env python3
"""
Scrape game histories for Arizona U11 teams using the GotSport API
API endpoint: https://system.gotsport.com/api/v1/teams/{team_id}/matches?past=true
"""
import pandas as pd
import requests
import time
from pathlib import Path
from datetime import datetime
import json

def scrape_team_matches_api(team_id, team_name):
    """Scrape matches for a single team using the GotSport API"""
    
    url = f"https://system.gotsport.com/api/v1/teams/{team_id}/matches"
    params = {"past": "true"}
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
        'Origin': 'https://rankings.gotsport.com',
        'Referer': 'https://rankings.gotsport.com/',
        'Accept-Encoding': 'gzip, deflate, br, zstd'
    }
    
    try:
        print(f"  Scraping {team_name} (ID: {team_id})...")
        
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        matches = []
        if isinstance(data, list):
            matches = data
        elif isinstance(data, dict) and 'matches' in data:
            matches = data['matches']
        elif isinstance(data, dict) and 'data' in data:
            matches = data['data']
        
        print(f"    Found {len(matches)} matches")
        
        # Process matches
        games = []
        for match in matches:
            try:
                # Extract game data from API response
                game = {
                    'date': match.get('date', match.get('match_date', '')),
                    'opponent': match.get('opponent', match.get('opponent_name', '')),
                    'score': match.get('score', match.get('result', '')),
                    'result': match.get('outcome', match.get('result', '')),
                    'competition': match.get('competition', match.get('event', '')),
                    'venue': match.get('venue', match.get('location', '')),
                    'home_away': match.get('home_away', ''),
                    'team_score': match.get('team_score', match.get('goals_for', '')),
                    'opponent_score': match.get('opponent_score', match.get('goals_against', ''))
                }
                
                # Clean up the data
                for key, value in game.items():
                    if value is None:
                        game[key] = ''
                    else:
                        game[key] = str(value).strip()
                
                games.append(game)
                
            except Exception as e:
                print(f"    Error processing match: {e}")
                continue
        
        # Show sample games
        if games:
            print(f"    Sample games:")
            for game in games[:3]:
                print(f"      {game['date']} - {game['opponent']} - {game['score']}")
        
        return games
        
    except Exception as e:
        print(f"    Error scraping {team_name}: {e}")
        return []

def main():
    print("Scraping game histories for Arizona U11 teams using GotSport API...")
    
    # Load Arizona teams
    az_file = Path("data/master/U11 2015 BOYS MASTER TEAM LIST/by_state/AZ_teams.csv")
    df = pd.read_csv(az_file)
    
    print(f"Loaded {len(df)} Arizona U11 teams")
    
    # Create output directory
    output_dir = Path("data/game_histories/az_u11_2025")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    all_games = []
    successful_teams = 0
    
    # Scrape each team's matches
    for idx, row in df.iterrows():
        team_id = row['gotsport_team_id']
        team_name = row['display_name']
        
        print(f"\n{idx + 1}/{len(df)}: {team_name}")
        
        games = scrape_team_matches_api(team_id, team_name)
        
        if games:
            successful_teams += 1
            # Add team info to each game
            for game in games:
                game['team_id'] = team_id
                game['team_name'] = team_name
                game['club'] = row.get('club', '')
                all_games.append(game)
        
        # Be respectful to the server
        time.sleep(1)
        
        # Save progress every 20 teams
        if (idx + 1) % 20 == 0:
            if all_games:
                progress_df = pd.DataFrame(all_games)
                progress_file = output_dir / f"az_u11_games_progress_{idx + 1}.csv"
                progress_df.to_csv(progress_file, index=False)
                print(f"  Progress saved: {progress_file}")
        
        # Test with first 10 teams
        if idx >= 9:
            print("  Stopping after 10 teams for testing...")
            break
    
    # Save final results
    if all_games:
        final_df = pd.DataFrame(all_games)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_file = output_dir / f"az_u11_game_histories_{timestamp}.csv"
        final_df.to_csv(final_file, index=False)
        
        print(f"\nSUCCESS!")
        print(f"Scraped game histories for {successful_teams}/{min(10, len(df))} Arizona teams")
        print(f"Total games found: {len(all_games)}")
        print(f"Saved to: {final_file}")
        
        # Show sample games
        print(f"\nSample games:")
        print(final_df[['team_name', 'date', 'opponent', 'score', 'result']].head(10).to_string(index=False))
        
        # Show games per team
        games_per_team = final_df.groupby('team_name').size().sort_values(ascending=False)
        print(f"\nGames per team:")
        print(games_per_team.head(10))
        
    else:
        print(f"\nNo games found for any teams")
        print("This might indicate:")
        print("1. U11 season hasn't started yet")
        print("2. Teams haven't played any games")
        print("3. API endpoint structure is different")
    
    print(f"\nGame history scraping complete!")

if __name__ == "__main__":
    main()


