#!/usr/bin/env python3
"""
Scrape game histories for Arizona U11 teams using correct team_ids
"""
import requests
import pandas as pd
import time
from datetime import datetime
import json

def scrape_team_game_history(team_id, team_name):
    """Scrape game history for a single team"""
    url = f"https://system.gotsport.com/api/v1/teams/{team_id}/matches?past=true"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Origin': 'https://rankings.gotsport.com',
        'Referer': 'https://rankings.gotsport.com/'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if isinstance(data, list):
            return data
        else:
            print(f"  Warning: Unexpected data format for {team_name}")
            return []
    except Exception as e:
        print(f"  Error scraping {team_name}: {e}")
        return []

def scrape_az_u11_game_histories():
    """Scrape game histories for all Arizona U11 teams"""
    print("Scraping Arizona U11 game histories...")
    
    # Load Arizona teams with correct team_ids
    df = pd.read_csv('AZ_teams_CORRECTED_20251011_233516.csv')
    print(f"Loaded {len(df)} Arizona U11 teams")
    
    all_games = []
    successful_teams = 0
    failed_teams = 0
    
    for i, row in df.iterrows():
        team_id = row['team_id']
        team_name = row['team_name']
        ranking_id = row['ranking_id']
        
        print(f"Scraping {i+1}/{len(df)}: {team_name} (ID: {team_id})")
        
        # Scrape game history
        games = scrape_team_game_history(team_id, team_name)
        
        if games:
            print(f"  Found {len(games)} games")
            successful_teams += 1
            
            # Process each game
            for game in games:
                # Extract essential game details
                game_data = {
                    # Team info
                    'team_id': team_id,
                    'team_name': team_name,
                    'ranking_id': ranking_id,
                    
                    # Match info
                    'match_id': game.get('id'),
                    'title': game.get('title', ''),
                    'match_date': game.get('matchTime', ''),
                    'match_date_formatted': game.get('match_date_formatted', {}).get('long', ''),
                    
                    # Event/Tournament info
                    'event_name': game.get('event_name', ''),
                    'competition_name': game.get('competition_name', ''),
                    
                    # Scores
                    'home_score': game.get('home_score'),
                    'away_score': game.get('away_score'),
                    'winner_team_id': game.get('winner_team_id'),
                    
                    # Teams
                    'home_team_name': game.get('homeTeam', {}).get('full_name', ''),
                    'away_team_name': game.get('awayTeam', {}).get('full_name', ''),
                    'home_team_id': game.get('homeTeam', {}).get('team_id'),
                    'away_team_id': game.get('awayTeam', {}).get('team_id'),
                    
                    # Venue info
                    'venue_name': game.get('venue', {}).get('name', '') if game.get('venue') else '',
                    'venue_address': game.get('venue', {}).get('full_address', '') if game.get('venue') else '',
                    
                    # Raw data for reference
                    'raw_game_data': json.dumps(game)
                }
                all_games.append(game_data)
        else:
            print(f"  No games found")
            failed_teams += 1
        
        # Be respectful to the server
        time.sleep(0.5)
    
    # Convert to DataFrame
    games_df = pd.DataFrame(all_games)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"AZ_U11_game_histories_{timestamp}.csv"
    games_df.to_csv(output_file, index=False)
    
    print(f"\n" + "="*60)
    print(f"SCRAPING COMPLETE!")
    print(f"Successful teams: {successful_teams}")
    print(f"Failed teams: {failed_teams}")
    print(f"Total games scraped: {len(games_df)}")
    print(f"Saved to: {output_file}")
    
    # Show sample of scraped data
    if len(games_df) > 0:
        print(f"\nSample of scraped games:")
        print(games_df[['team_name', 'title', 'match_date']].head(10).to_string(index=False))
    
    return games_df

def create_standardized_games_format(games_df):
    """Convert scraped games to standardized format for rankings"""
    print("\nCreating standardized games format...")
    
    standardized_games = []
    
    for _, game in games_df.iterrows():
        title = game['title']
        match_date = game['match_date']
        
        # Parse team names from title (format: "Team A vs Team B")
        if ' vs ' in title:
            teams = title.split(' vs ')
            if len(teams) == 2:
                team_a = teams[0].strip()
                team_b = teams[1].strip()
                
                # Create standardized game record
                game_record = {
                    'date': match_date,
                    'team_a': team_a,
                    'team_b': team_b,
                    'team_a_id': game['team_id'] if team_a == game['team_name'] else None,
                    'team_b_id': game['team_id'] if team_b == game['team_name'] else None,
                    'match_id': game['match_id'],
                    'bracket_id': game['bracket_id'],
                    'source': 'gotsport_api'
                }
                standardized_games.append(game_record)
    
    # Convert to DataFrame
    std_df = pd.DataFrame(standardized_games)
    
    # Save standardized format
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    std_file = f"AZ_U11_games_standardized_{timestamp}.csv"
    std_df.to_csv(std_file, index=False)
    
    print(f"Standardized games saved to: {std_file}")
    print(f"Total standardized games: {len(std_df)}")
    
    return std_df

if __name__ == "__main__":
    # Scrape game histories
    games_df = scrape_az_u11_game_histories()
    
    if len(games_df) > 0:
        # Create standardized format
        std_df = create_standardized_games_format(games_df)
        
        print(f"\n🎉 SUCCESS! Ready to generate U11 rankings with {len(std_df)} games!")