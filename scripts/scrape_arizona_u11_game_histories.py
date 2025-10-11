#!/usr/bin/env python3
"""
Scrape game histories for Arizona U11 teams using their GotSport team IDs.

This mirrors the U12 approach - go to each team's individual game history page
and scrape their actual games directly.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
from pathlib import Path
import re
from datetime import datetime
import json

DIV = "az_boys_u11_2025"
MASTER = Path(f"data/master/{DIV}/arizona_teams.csv")
OUTPUT_DIR = Path(f"data/outputs/{DIV}")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# GotSport base URL pattern
BASE_URL = "https://rankings.gotsport.com/teams/{team_id}/game-history"


def scrape_team_game_history(team_id, team_name):
    """Scrape game history for a single team."""
    url = BASE_URL.format(team_id=team_id)
    
    try:
        print(f"Scraping {team_name} ({team_id})...")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for game history table
        games = []
        
        # Try multiple selectors for game rows
        selectors = [
            'tr.game-row',
            'tr.match-row', 
            'tr[data-game-id]',
            'tbody tr',
            'table tr'
        ]
        
        game_rows = []
        for selector in selectors:
            rows = soup.select(selector)
            if rows and len(rows) > 1:  # More than just header
                game_rows = rows[1:]  # Skip header
                break
        
        if not game_rows:
            print(f"  No game rows found for {team_name}")
            return []
        
        for row in game_rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 3:  # Need at least date, opponent, score
                try:
                    # Extract game data - adjust based on GotSport's structure
                    date_text = cells[0].get_text(strip=True)
                    opponent_text = cells[1].get_text(strip=True)
                    score_text = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                    
                    # Skip header rows
                    if any(header in date_text.lower() for header in ['date', 'opponent', 'score', 'result']):
                        continue
                    
                    # Parse score (format: "3-1" or "1-3")
                    if '-' in score_text:
                        try:
                            scores = score_text.split('-')
                            goals_for = int(scores[0].strip())
                            goals_against = int(scores[1].strip())
                        except (ValueError, IndexError):
                            continue
                    else:
                        continue
                    
                    # Parse date
                    try:
                        # Try common date formats
                        if '/' in date_text:
                            if len(date_text.split('/')[0]) <= 2:  # MM/DD/YYYY
                                game_date = datetime.strptime(date_text, '%m/%d/%Y').strftime('%Y-%m-%d')
                            else:  # YYYY/MM/DD
                                game_date = datetime.strptime(date_text, '%Y/%m/%d').strftime('%Y-%m-%d')
                        elif '-' in date_text:
                            game_date = datetime.strptime(date_text, '%Y-%m-%d').strftime('%Y-%m-%d')
                        else:
                            continue
                    except ValueError:
                        continue
                    
                    games.append({
                        'team_id': f"az_u11_{team_id}",
                        'team_name': team_name,
                        'date': game_date,
                        'opponent': opponent_text,
                        'goals_for': goals_for,
                        'goals_against': goals_against,
                        'result': 'W' if goals_for > goals_against else ('L' if goals_for < goals_against else 'D')
                    })
                    
                except Exception as e:
                    continue
        
        print(f"  Found {len(games)} games")
        return games
        
    except Exception as e:
        print(f"  Error scraping {team_name}: {e}")
        return []


def run():
    """Scrape game histories for all Arizona U11 teams."""
    
    # Load Arizona teams
    master = pd.read_csv(MASTER)
    print(f"Loaded {len(master)} Arizona U11 teams")
    
    all_games = []
    successful_scrapes = 0
    
    for idx, row in master.iterrows():
        team_id = row['gotsport_team_id']
        team_name = row['display_name']
        
        games = scrape_team_game_history(team_id, team_name)
        if games:
            all_games.extend(games)
            successful_scrapes += 1
        
        # Be respectful to the server
        time.sleep(2)
        
        # Progress update every 10 teams
        if (idx + 1) % 10 == 0:
            print(f"Progress: {idx + 1}/{len(master)} teams, {len(all_games)} total games")
    
    if all_games:
        # Save all games
        games_df = pd.DataFrame(all_games)
        output_path = OUTPUT_DIR / "histories.csv"
        games_df.to_csv(output_path, index=False)
        print(f"\nScraping complete!")
        print(f"Successfully scraped {successful_scrapes}/{len(master)} teams")
        print(f"Total games: {len(games_df)}")
        print(f"Saved to: {output_path}")
        
        # Show sample games
        print("\nSample games:")
        for _, game in games_df.head(5).iterrows():
            print(f"  {game['team_name']} vs {game['opponent']} ({game['goals_for']}-{game['goals_against']}) on {game['date']}")
    else:
        print("No games scraped!")


if __name__ == "__main__":
    run()
