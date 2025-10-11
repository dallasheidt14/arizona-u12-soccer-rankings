#!/usr/bin/env python3
"""
Scrape the actual master team list from GotSport rankings page.
This gets the authoritative team names as they appear officially on GotSport.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import sys
import os
import json
from pathlib import Path

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.id_codec import make_team_id

def scrape_gotsport_rankings():
    """Scrape team rankings from GotSport."""
    
    url = "https://rankings.gotsport.com/?team_country=USA&age=11&gender=m&state=AZ"
    
    print(f"Scraping GotSport rankings from: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    try:
        print("Making request to GotSport...")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        print(f"Got response: {response.status_code}")
        print(f"Content length: {len(response.text)}")
        
        # Save raw HTML for debugging
        with open("debug_gotsport_page.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        print("Saved raw HTML to debug_gotsport_page.html")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for different possible table structures
        teams = []
        
        # Method 1: Look for table rows with team data
        table_rows = soup.find_all('tr')
        print(f"Found {len(table_rows)} table rows")
        
        for i, row in enumerate(table_rows[:10]):  # Check first 10 rows
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                # Usually team name is in second column
                team_cell = cells[1]
                team_text = team_cell.get_text(strip=True)
                print(f"Row {i}: {team_text}")
                
                if team_text and len(team_text) > 5 and not team_text.isdigit():
                    teams.append(team_text)
        
        # Method 2: Look for any text that looks like team names
        if len(teams) < 10:
            print("Trying alternative method - searching for team-like text...")
            all_text = soup.get_text()
            lines = [line.strip() for line in all_text.split('\n') if line.strip()]
            
            for line in lines:
                # Look for lines that contain team indicators
                if (('Boys' in line or 'FC' in line or 'SC' in line or 'AZ' in line) and 
                    len(line) > 10 and len(line) < 100 and
                    not line.isdigit() and
                    'Rank' not in line and 'Team' not in line and
                    'GotSport' not in line and 'Copyright' not in line):
                    teams.append(line)
        
        # Remove duplicates and sort
        teams = list(set(teams))
        teams.sort()
        
        print(f"\nFound {len(teams)} unique teams")
        
        # Show all teams found
        print("\nAll teams found:")
        for i, team in enumerate(teams):
            print(f"  {i+1:3d}. {team}")
        
        return teams
        
    except Exception as e:
        print(f"Error scraping GotSport: {e}")
        return None

def create_master_list_from_scraped_teams(teams):
    """Create master list from scraped team names."""
    
    if not teams:
        print("No teams to process")
        return None
    
    master_data = []
    for team_name in teams:
        team_id = make_team_id(team_name, "az_boys_u11_2025")
        
        # Extract club name (everything before the year)
        parts = team_name.split()
        club_parts = []
        for part in parts:
            if part.isdigit() and len(part) == 4:  # Found year like "2015"
                break
            club_parts.append(part)
        club = " ".join(club_parts) if club_parts else ""
        
        master_data.append({
            "team_id": team_id,
            "display_name": team_name,
            "club": club
        })
    
    master_df = pd.DataFrame(master_data)
    
    # Verify no duplicate team IDs
    if master_df["team_id"].duplicated().any():
        duplicates = master_df[master_df["team_id"].duplicated()]
        print(f"WARNING: Duplicate team IDs found:")
        for _, row in duplicates.iterrows():
            print(f"  {row['display_name']} -> {row['team_id']}")
    
    # Save master list
    output_path = Path("data/master/az_boys_u11_2025/master_teams.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    master_df.to_csv(output_path, index=False)
    print(f"\nSaved master list to {output_path}")
    print(f"Total teams: {len(master_df)}")
    
    return master_df

if __name__ == "__main__":
    try:
        # Scrape teams from GotSport
        teams = scrape_gotsport_rankings()
        
        if teams and len(teams) > 10:
            # Create master list from scraped teams
            master_df = create_master_list_from_scraped_teams(teams)
            
            if master_df is not None:
                print(f"\nSuccessfully scraped and created master list with {len(master_df)} teams")
                
                # Show RSL teams specifically
                rsl_teams = master_df[master_df["display_name"].str.contains("RSL", case=False, na=False)]
                if not rsl_teams.empty:
                    print(f"\nRSL teams found ({len(rsl_teams)}):")
                    for _, row in rsl_teams.iterrows():
                        print(f"  {row['display_name']}")
                
                # Show Next Level Soccer
                next_level = master_df[master_df["display_name"].str.contains("Next Level", case=False, na=False)]
                if not next_level.empty:
                    print(f"\nNext Level Soccer teams:")
                    for _, row in next_level.iterrows():
                        print(f"  {row['display_name']}")
            else:
                print("Failed to create master list")
        else:
            print("Scraping failed or returned too few teams")
            print("Check debug_gotsport_page.html to see what was scraped")
            
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
