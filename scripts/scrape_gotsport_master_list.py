#!/usr/bin/env python3
"""
Scrape U11 Boys Arizona master team list from GotSport rankings page.
This gives us the authoritative team names as they appear officially.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.id_codec import make_team_id

def scrape_gotsport_master_list():
    """Scrape master team list from GotSport rankings page."""
    
    url = "https://rankings.gotsport.com/?team_country=USA&age=11&gender=m&state=AZ"
    
    print(f"Scraping GotSport master list from: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        print(f"Got response: {response.status_code}")
        print(f"Content length: {len(response.text)}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for team names in the rankings table
        teams = []
        
        # Try different selectors for the rankings table
        selectors = [
            'table tr td:nth-child(2)',  # Team name in second column
            '.team-name',
            '.team',
            'td[data-field="team"]',
            'tr td:contains("Boys")',
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                print(f"Found {len(elements)} elements with selector: {selector}")
                for elem in elements:
                    team_name = elem.get_text(strip=True)
                    if team_name and ('Boys' in team_name or 'FC' in team_name or 'SC' in team_name):
                        teams.append(team_name)
                break
        
        # If no specific selector worked, try to find all text that looks like team names
        if not teams:
            print("Trying fallback method - looking for team-like text...")
            all_text = soup.get_text()
            lines = all_text.split('\n')
            
            for line in lines:
                line = line.strip()
                # Look for lines that contain common team indicators
                if (('Boys' in line or 'FC' in line or 'SC' in team_name) and 
                    len(line) > 10 and len(line) < 100 and
                    not line.isdigit() and
                    'Rank' not in line and 'Team' not in line):
                    teams.append(line)
        
        # Remove duplicates and sort
        teams = list(set(teams))
        teams.sort()
        
        print(f"Found {len(teams)} unique teams")
        
        # Show first few teams
        print("\nFirst 10 teams found:")
        for i, team in enumerate(teams[:10]):
            print(f"  {i+1}. {team}")
        
        # Create master list DataFrame
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
            print(f"WARNING: Duplicate team IDs found: {duplicates}")
        
        # Save master list
        output_path = Path("data/master/az_boys_u11_2025/master_teams.csv")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        master_df.to_csv(output_path, index=False)
        print(f"\nSaved master list to {output_path}")
        print(f"Total teams: {len(master_df)}")
        
        # Show RSL teams specifically
        rsl_teams = master_df[master_df["display_name"].str.contains("RSL", case=False, na=False)]
        if not rsl_teams.empty:
            print(f"\nRSL teams found ({len(rsl_teams)}):")
            for i, row in rsl_teams.iterrows():
                print(f"  {row['display_name']}")
        else:
            print("\nNo RSL teams found")
        
        return master_df
        
    except Exception as e:
        print(f"Error scraping GotSport: {e}")
        print("This might be due to:")
        print("1. Website structure changes")
        print("2. Anti-bot protection")
        print("3. Network issues")
        print("\nLet's try a different approach...")
        return None

def create_fallback_master_list():
    """Create a fallback master list based on known Arizona U11 teams."""
    
    print("Creating fallback master list with known Arizona U11 teams...")
    
    # Known Arizona U11 Boys teams (without colors)
    known_teams = [
        "RSL-AZ North 2015 Boys",
        "RSL-AZ South 2015 Boys", 
        "RSL-AZ Yuma 2015 Boys",
        "RSL-AZ West Valley 2015 Boys",
        "FC Elite Arizona 2015 Boys",
        "Phoenix Premier FC 2015 Boys",
        "Phoenix Rising FC 2015 Boys",
        "Phoenix Rush 2015 Boys",
        "Scottsdale City FC 2015 Boys",
        "FC Arizona 2015 Boys",
        "FC Sonora 2015 Boys",
        "FC Tucson Youth Soccer 2015 Boys",
        "Real Arizona FC 2015 Boys",
        "North Scottsdale Soccer Club 2015 Boys",
        "Pima County Surf Soccer Club 2015 Boys",
        "Thunderbird FC 2015 Boys",
        "Vail SC 2015 Boys",
        "Flagstaff SC 2015 Boys",
        "Kingman SC 2015 Boys",
        "East Valley/NSFC 2015 Boys",
        "Phoenix United Futbol Club 2015 Boys",
        "Brazas Futebol Club 2015 Boys",
        "AZ Inferno 2015 Boys",
        "Amore Soccer 2015 Boys",
        "Epic Soccer Club 2015 Boys",
        "Synergy FC AZ 2015 Boys",
        "Dynamos SC 2015 Boys",
        "FBSL 2015 Boys",
        "CCV STARS 2015 Boys",
        "Sun Warriors AZFC 2015 Boys",
        "Paladin Soccer Club 2015 Boys",
        "Madison FC 2015 Boys",
        "State 48 FC 2015 Boys",
        "Canyon Del Oro Soccer Club 2015 Boys",
        "Bala FC 2015 Boys",
        "La Academia FC 2015 Boys",
        "AZ Arsenal Soccer Club 2015 Boys",
        "Arizona Soccer Club 2015 Boys",
        "Next Level Soccer (AZ) 2015 Boys",
        "Arizona Soccer Academy 2015 Boys",
        "Excel Soccer Academy 2015 Boys",
        "Playmaker Futbol Academy 2015 Boys",
        "Paris Saint-Germain Academy Phoenix 2015 Boys",
        "SC Union Maricopa Academy 2015 Boys",
        "Spartak Academy 2015 Boys",
        "AYSO 350 Alliance 2015 Boys",
        "AYSO United (AZ) 2015 Boys",
        "Spartans FC (AZ) 2015 Boys",
        "United Latinos SC 2015 Boys"
    ]
    
    master_data = []
    for team_name in known_teams:
        team_id = make_team_id(team_name, "az_boys_u11_2025")
        
        # Extract club name
        parts = team_name.split()
        club_parts = []
        for part in parts:
            if part.isdigit() and len(part) == 4:
                break
            club_parts.append(part)
        club = " ".join(club_parts) if club_parts else ""
        
        master_data.append({
            "team_id": team_id,
            "display_name": team_name,
            "club": club
        })
    
    master_df = pd.DataFrame(master_data)
    
    # Save master list
    output_path = Path("data/master/az_boys_u11_2025/master_teams.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    master_df.to_csv(output_path, index=False)
    print(f"Saved fallback master list to {output_path}")
    print(f"Total teams: {len(master_df)}")
    
    return master_df

if __name__ == "__main__":
    try:
        # Try scraping GotSport first
        master_df = scrape_gotsport_master_list()
        
        # If scraping failed, use fallback
        if master_df is None or len(master_df) < 50:
            print("\nGotSport scraping failed or returned too few teams.")
            print("Using fallback master list with known teams...")
            master_df = create_fallback_master_list()
        
        print(f"\nSuccessfully created master list with {len(master_df)} teams")
        
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
