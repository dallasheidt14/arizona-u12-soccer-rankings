#!/usr/bin/env python3
"""
Test script to check the structure of a GotSport game history page
"""
import requests
from bs4 import BeautifulSoup
import pandas as pd

def test_game_history_page():
    """Test scraping one team's game history page"""
    
    # Use the team ID you provided as an example
    team_id = "163451"
    url = f"https://rankings.gotsport.com/teams/{team_id}/game-history"
    
    print(f"Testing game history page: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        print(f"Response status: {response.status_code}")
        print(f"Content length: {len(response.content)}")
        
        # Save raw HTML for inspection
        with open('test_game_history.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print("Saved raw HTML to test_game_history.html")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for various structures
        print("\nLooking for game data structures...")
        
        # Check for tables
        tables = soup.find_all('table')
        print(f"Found {len(tables)} tables")
        
        for i, table in enumerate(tables):
            rows = table.find_all('tr')
            print(f"  Table {i+1}: {len(rows)} rows")
            if rows:
                print(f"    First row: {rows[0].get_text()[:100]}...")
        
        # Check for divs with game-like content
        game_divs = soup.find_all('div', class_=lambda x: x and ('game' in x.lower() or 'match' in x.lower() or 'history' in x.lower()))
        print(f"Found {len(game_divs)} game-related divs")
        
        # Check for any elements containing 'vs' or game-like text
        vs_elements = soup.find_all(text=lambda text: text and ('vs' in text.lower() or 'v.' in text.lower()))
        print(f"Found {len(vs_elements)} elements with 'vs' text")
        
        # Show sample content
        print("\nSample page content:")
        body_text = soup.get_text()[:2000]
        print(body_text)
        
        # Look for specific patterns
        print("\nLooking for specific game patterns...")
        all_text = soup.get_text()
        lines = all_text.split('\n')
        
        game_lines = []
        for line in lines:
            line = line.strip()
            if ('vs' in line.lower() or 'v.' in line.lower()) and len(line) > 10 and len(line) < 200:
                game_lines.append(line)
        
        print(f"Found {len(game_lines)} potential game lines:")
        for line in game_lines[:10]:  # Show first 10
            print(f"  {line}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_game_history_page()


