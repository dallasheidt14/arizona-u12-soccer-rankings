#!/usr/bin/env python3
"""
Scrape AZ U11 Game Histories
============================

Scrapes game histories for Arizona U11 teams using the correct team_id from matches API.
Uses the organized AZ teams file from the state organization process.
"""

import requests
import pandas as pd
from pathlib import Path
import time
from datetime import datetime
import json

def scrape_az_u11_game_histories():
    """Scrape game histories for all Arizona U11 teams."""
    
    print("Scraping AZ U11 Game Histories")
    print("=" * 40)
    
    # Load AZ teams from the new folder structure
    az_teams_file = Path("data/master/U11 BOYS/AZ/AZ_teams.csv")
    if not az_teams_file.exists():
        print(f"[ERROR] AZ teams file not found: {az_teams_file}")
        return False
    
    az_teams = pd.read_csv(az_teams_file)
    print(f"[INFO] Loaded {len(az_teams)} AZ U11 teams")
    
    # Create output directory using the specified structure
    output_dir = Path("data/game_histories/U11 BOYS/AZ")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    all_games = []
    successful_teams = 0
    failed_teams = 0
    
    print(f"[INFO] Starting to scrape game histories...")
    
    for idx, team in az_teams.iterrows():
        team_id = team['gotsport_team_id']
        team_name = team['team_name']
        
        print(f"[{idx+1}/{len(az_teams)}] Scraping {team_name} (ID: {team_id})")
        
        try:
            # Use the CORRECT API endpoint with team_id
            url = f"https://system.gotsport.com/api/v1/teams/{team_id}/matches?past=true"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
                'Origin': 'https://rankings.gotsport.com',
                'Referer': 'https://rankings.gotsport.com/'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # API returns a list directly, not a dict with 'matches' key
            if isinstance(data, list) and data:
                matches = data
                print(f"  Found {len(matches)} matches")
                
                for match in matches:
                    # Extract ALL available data including opponent names
                    home_team = match.get('homeTeam', {})
                    away_team = match.get('awayTeam', {})
                    
                    # Parse opponent from title if available
                    title = match.get('title', '')
                    opponent_name = ''
                    if ' vs. ' in title:
                        parts = title.split(' vs. ')
                        if len(parts) == 2:
                            # Determine which team is the opponent
                            if team_name in parts[0]:
                                opponent_name = parts[1]
                            elif team_name in parts[1]:
                                opponent_name = parts[0]
                    
                    game_data = {
                        # Team info
                        'team_id': team_id,
                        'team_name': team_name,
                        'match_id': match.get('id'),
                        'title': title,
                        
                        # Event/Tournament info
                        'event_name': match.get('event_name', ''),
                        'competition_name': match.get('competition_name', ''),
                        'competition': match.get('competition', ''),
                        
                        # Teams (extract from nested objects and title)
                        'home_team_name': home_team.get('name', '') if isinstance(home_team, dict) else '',
                        'away_team_name': away_team.get('name', '') if isinstance(away_team, dict) else '',
                        'home_team_id': home_team.get('team_id', '') if isinstance(home_team, dict) else '',
                        'away_team_id': away_team.get('team_id', '') if isinstance(away_team, dict) else '',
                        'opponent_name': opponent_name,
                        
                        # Scores
                        'home_score': match.get('home_score'),
                        'away_score': match.get('away_score'),
                        
                        # Venue info
                        'venue_name': match.get('venue', {}).get('name', '') if isinstance(match.get('venue'), dict) else '',
                        'venue_address': match.get('venue', {}).get('full_address', '') if isinstance(match.get('venue'), dict) else '',
                        
                        # Date info
                        'match_date': match.get('match_date', ''),
                        'match_date_formatted': match.get('match_date_formatted', {}).get('long', '') if isinstance(match.get('match_date_formatted'), dict) else match.get('match_date_formatted', ''),
                        
                        # Additional fields
                        'home_away': match.get('home_away', ''),
                        'result': match.get('result', ''),
                        'winner_team_id': match.get('winner_team_id', ''),
                        
                        # Raw data for debugging
                        'raw_match_data': str(match)
                    }
                    all_games.append(game_data)
                
                successful_teams += 1
            else:
                print(f"  No matches found")
                successful_teams += 1
            
            # Rate limiting
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  ERROR: {e}")
            failed_teams += 1
            continue
    
    # Save results
    if all_games:
        df = pd.DataFrame(all_games)
        
        # Save to the specified location
        output_file = output_dir / "game_histories.csv"
        df.to_csv(output_file, index=False)
        
        print(f"\n[SUCCESS]")
        print(f"Total games scraped: {len(all_games)}")
        print(f"Successful teams: {successful_teams}")
        print(f"Failed teams: {failed_teams}")
        print(f"Saved to: {output_file}")
        
        # Show sample data
        print(f"\nSample games:")
        print(df.head(10)[['team_name', 'home_team_name', 'away_team_name', 'home_score', 'away_score', 'event_name', 'competition_name']].to_string(index=False))
        
        # Show unique events and competitions
        unique_events = df['event_name'].nunique()
        unique_competitions = df['competition_name'].nunique()
        print(f"\nUnique events: {unique_events}")
        print(f"Unique competitions: {unique_competitions}")
        
        # Show top events
        if unique_events > 0:
            print(f"\nTop 5 events by game count:")
            event_counts = df['event_name'].value_counts().head(5)
            for event, count in event_counts.items():
                print(f"  {event}: {count} games")
        
        return True
    else:
        print(f"\n[ERROR] No games scraped!")
        return False

if __name__ == "__main__":
    success = scrape_az_u11_game_histories()
    if success:
        print("\n[SUCCESS] AZ U11 game histories scraped successfully!")
    else:
        print("\n[ERROR] Failed to scrape game histories")
