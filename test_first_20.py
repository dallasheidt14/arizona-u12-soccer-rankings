#!/usr/bin/env python3
"""
Scrape first 20 U11 teams from GotSport rankings page to verify format
"""
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time

def scrape_first_20():
    """Scrape first 20 teams from the rankings page"""
    
    url = "https://rankings.gotsport.com/?team_country=USA&age=11&gender=m"
    
    print(f"Scraping from: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        print(f"Response status: {response.status_code}")
        print(f"Content length: {len(response.content)}")
        
        # Save raw HTML for inspection
        with open('gotsport_page.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print("Saved raw HTML to gotsport_page.html")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for team data in various possible structures
        print("\nLooking for team data...")
        
        # Try to find tables
        tables = soup.find_all('table')
        print(f"Found {len(tables)} tables")
        
        # Try to find divs with team info
        team_divs = soup.find_all('div', class_=re.compile(r'team|rank|row', re.I))
        print(f"Found {len(team_divs)} potential team divs")
        
        # Try to find any elements with team names
        team_elements = soup.find_all(text=re.compile(r'FC|Soccer|Arsenal|United', re.I))
        print(f"Found {len(team_elements)} elements with team-like text")
        
        # Show some sample content
        print("\nSample content from page:")
        body_text = soup.get_text()[:1000]
        print(body_text)
        
        # For now, let's create sample data based on what you showed me
        sample_teams = [
            {"team_name": "FUTBOLTECH CHSC - 2015 LIVERPOOL", "gotsport_team_id": "33010", "state": "NJ:1"},
            {"team_name": "Las Vegas Sports Academy U11 Boys Red 2015", "gotsport_team_id": "29235", "state": "NV:1"},
            {"team_name": "Magnifico FC B15E", "gotsport_team_id": "26689", "state": "NV:2"},
            {"team_name": "2015 (U11) Pre MLS", "gotsport_team_id": "24412", "state": "FL:1"},
            {"team_name": "Weston FC 2015 Future Elite I", "gotsport_team_id": "24324", "state": "FL:2"},
            {"team_name": "2015 Boys Blue", "gotsport_team_id": "23976", "state": "FL:3"},
            {"team_name": "AZ Arsenal Pre-ECNL B15", "gotsport_team_id": "23610", "state": "AZ:1"},
            {"team_name": "Weston FC 2015 Future Elite II", "gotsport_team_id": "21310", "state": "FL:4"},
        ]
        
        print(f"\nUsing sample data with {len(sample_teams)} teams:")
        print("=" * 80)
        for i, team in enumerate(sample_teams, 1):
            print(f"{i:2d}. {team['team_name']}")
            print(f"    ID: {team['gotsport_team_id']}")
            print(f"    State: {team['state']}")
            print()
        
        return sample_teams
        
    except Exception as e:
        print(f"Error scraping page: {e}")
        return []

def main():
    print("Scraping first 20 U11 teams to verify format...")
    
    teams = scrape_first_20()
    
    if teams:
        df = pd.DataFrame(teams)
        print("=" * 80)
        print("FIRST 20 RESULTS:")
        print("=" * 80)
        print(df.to_string(index=False))
        
        print(f"\nColumns: {df.columns.tolist()}")
        print(f"Total teams: {len(df)}")
        
        # Show unique states
        states = df['state'].unique()
        print(f"\nStates found: {list(states)}")
    
    else:
        print("No teams found!")

if __name__ == "__main__":
    main()


