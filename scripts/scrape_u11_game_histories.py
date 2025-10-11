#!/usr/bin/env python3
"""
Scrape U11 game histories for each Arizona team using their GotSport team IDs.

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

DIV = "az_boys_u11_2025"
MASTER = Path(f"data/master/{DIV}/master_teams.csv")
OUTPUT_DIR = Path(f"data/outputs/{DIV}")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# GotSport base URL pattern
BASE_URL = "https://rankings.gotsport.com/teams/{team_id}/game-history"


def extract_team_id_from_gotsport_url(url):
    """Extract team ID from GotSport URL."""
    match = re.search(r'/teams/(\d+)/', url)
    return match.group(1) if match else None


def scrape_team_game_history(team_id, team_name):
    """Scrape game history for a single team."""
    url = BASE_URL.format(team_id=team_id)
    
    try:
        print(f"Scraping {team_name} ({team_id})...")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for game history table
        games = []
        
        # Try to find game rows - GotSport typically uses specific classes
        game_rows = soup.find_all('tr', class_=re.compile(r'game|match|row'))
        
        if not game_rows:
            # Try alternative selectors
            game_rows = soup.find_all('tr')[1:]  # Skip header row
        
        for row in game_rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 4:  # Need at least date, opponent, score columns
                try:
                    # Extract game data - adjust selectors based on GotSport's structure
                    date_cell = cells[0].get_text(strip=True)
                    opponent_cell = cells[1].get_text(strip=True)
                    score_cell = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                    
                    # Parse score (format: "3-1" or "1-3")
                    if '-' in score_cell:
                        try:
                            scores = score_cell.split('-')
                            goals_for = int(scores[0].strip())
                            goals_against = int(scores[1].strip())
                        except (ValueError, IndexError):
                            continue
                    else:
                        continue
                    
                    # Parse date
                    try:
                        # Try common date formats
                        if '/' in date_cell:
                            game_date = datetime.strptime(date_cell, '%m/%d/%Y').strftime('%Y-%m-%d')
                        elif '-' in date_cell:
                            game_date = datetime.strptime(date_cell, '%Y-%m-%d').strftime('%Y-%m-%d')
                        else:
                            continue
                    except ValueError:
                        continue
                    
                    games.append({
                        'team_id': team_id,
                        'team_name': team_name,
                        'date': game_date,
                        'opponent': opponent_cell,
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
    
    # Load master list
    master = pd.read_csv(MASTER)
    print(f"Loaded {len(master)} Arizona U11 teams")
    
    all_games = []
    
    for _, row in master.iterrows():
        team_id = row['team_id']
        team_name = row['display_name']
        
        # For now, we need to get the actual GotSport team ID
        # The team_id we have is our internal ID, not the GotSport ID
        # We need to either:
        # 1. Add a gotsport_team_id column to the master list, or
        # 2. Extract it from the team's GotSport URL
        
        # For now, let's assume we need to add GotSport team IDs
        # This would require updating the master list scraping to capture the team IDs
        
        print(f"Skipping {team_name} - need GotSport team ID")
        time.sleep(1)  # Be respectful to the server
    
    if all_games:
        # Save all games
        games_df = pd.DataFrame(all_games)
        output_path = OUTPUT_DIR / "histories.csv"
        games_df.to_csv(output_path, index=False)
        print(f"Saved {len(games_df)} game records to {output_path}")
    else:
        print("No games scraped - need to add GotSport team IDs to master list")


if __name__ == "__main__":
    run()
