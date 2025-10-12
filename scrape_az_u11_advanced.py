#!/usr/bin/env python3
"""
Advanced scraper for GotSport game histories with anti-detection measures
"""
import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import time
from pathlib import Path
from datetime import datetime
import random

async def scrape_team_game_history_advanced(page, team_id, team_name):
    """Advanced scraping with anti-detection measures"""
    
    url = f"https://rankings.gotsport.com/teams/{team_id}/game-history"
    
    try:
        print(f"  Scraping {team_name} (ID: {team_id})...")
        
        # Add random delay to appear more human-like
        await asyncio.sleep(random.uniform(1, 3))
        
        # Navigate with realistic browser behavior
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        
        # Simulate human behavior - scroll and wait
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(random.uniform(2, 4))
        
        # Wait for any dynamic content to load
        try:
            await page.wait_for_selector('table', timeout=10000)
        except:
            pass
        
        try:
            await page.wait_for_selector('[data-testid*="game"]', timeout=5000)
        except:
            pass
        
        # Get page content
        page_text = await page.inner_text('body')
        
        # Look for game data in various ways
        games = []
        
        # Method 1: Look for tables
        tables = await page.query_selector_all('table')
        for table in tables:
            rows = await table.query_selector_all('tr')
            if len(rows) > 1:  # Has data rows
                for row in rows[1:]:  # Skip header
                    cells = await row.query_selector_all('td, th')
                    if len(cells) >= 3:
                        try:
                            date = await cells[0].inner_text()
                            opponent = await cells[1].inner_text()
                            score = await cells[2].inner_text() if len(cells) > 2 else ""
                            result = await cells[3].inner_text() if len(cells) > 3 else ""
                            
                            if date.strip() and opponent.strip():
                                games.append({
                                    'date': date.strip(),
                                    'opponent': opponent.strip(),
                                    'score': score.strip(),
                                    'result': result.strip()
                                })
                        except:
                            continue
        
        # Method 2: Look for game-like text patterns
        if not games:
            lines = page_text.split('\n')
            for line in lines:
                line = line.strip()
                # Look for patterns like "Team A vs Team B" or "Team A v Team B"
                if (' vs ' in line or ' v ' in line) and len(line) > 10 and len(line) < 200:
                    games.append({
                        'date': 'Unknown',
                        'opponent': line,
                        'score': '',
                        'result': ''
                    })
        
        # Method 3: Look for any structured data
        if not games:
            # Try to find any elements that might contain game data
            all_elements = await page.query_selector_all('*')
            for element in all_elements[:200]:  # Limit to avoid too much processing
                try:
                    text = await element.inner_text()
                    if text and ('vs' in text.lower() or 'game' in text.lower()) and len(text) > 10:
                        games.append({
                            'date': 'Unknown',
                            'opponent': text.strip(),
                            'score': '',
                            'result': ''
                        })
                except:
                    continue
        
        # Remove duplicates and limit
        unique_games = []
        seen = set()
        for game in games:
            key = f"{game['opponent']}_{game['date']}"
            if key not in seen:
                seen.add(key)
                unique_games.append(game)
        
        games = unique_games[:20]  # Limit to 20 games per team
        
        print(f"    Found {len(games)} games")
        
        # Debug: Show what we found
        if games:
            print(f"    Sample games:")
            for game in games[:3]:
                print(f"      {game['date']} - {game['opponent']} - {game['score']}")
        
        return games
        
    except Exception as e:
        print(f"    Error scraping {team_name}: {e}")
        return []

async def main():
    print("Advanced scraping of Arizona U11 game histories...")
    
    # Load Arizona teams
    az_file = Path("data/master/U11 2015 BOYS MASTER TEAM LIST/by_state/AZ_teams.csv")
    df = pd.read_csv(az_file)
    
    print(f"Loaded {len(df)} Arizona U11 teams")
    
    # Create output directory
    output_dir = Path("data/game_histories/az_u11_2025")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    all_games = []
    successful_teams = 0
    
    async with async_playwright() as p:
        # Launch browser with stealth settings
        browser = await p.chromium.launch(
            headless=False,  # Set to True for headless
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
        )
        
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        )
        
        # Add stealth script
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
        """)
        
        try:
            # Test with just a few teams first
            test_teams = df.head(3)  # Test with first 3 teams
            
            for idx, row in test_teams.iterrows():
                team_id = row['gotsport_team_id']
                team_name = row['display_name']
                
                print(f"\n{idx + 1}/{len(test_teams)}: {team_name}")
                
                # Create a new page for each team
                page = await context.new_page()
                
                try:
                    games = await scrape_team_game_history_advanced(page, team_id, team_name)
                    
                    if games:
                        successful_teams += 1
                        # Add team info to each game
                        for game in games:
                            game['team_id'] = team_id
                            game['team_name'] = team_name
                            game['club'] = row.get('club', '')
                            all_games.append(game)
                    
                    # Longer delay between teams
                    await asyncio.sleep(random.uniform(3, 6))
                    
                finally:
                    await page.close()
        
        finally:
            await browser.close()
    
    # Save results
    if all_games:
        final_df = pd.DataFrame(all_games)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_file = output_dir / f"az_u11_game_histories_test_{timestamp}.csv"
        final_df.to_csv(final_file, index=False)
        
        print(f"\nSUCCESS!")
        print(f"Scraped game histories for {successful_teams}/{len(test_teams)} Arizona teams")
        print(f"Total games found: {len(all_games)}")
        print(f"Saved to: {final_file}")
        
        # Show sample games
        print(f"\nSample games:")
        print(final_df.head(10).to_string(index=False))
        
    else:
        print(f"\nNo games found for any teams")
        print("This might indicate:")
        print("1. U11 season hasn't started yet")
        print("2. Teams haven't played any games")
        print("3. Site has stronger anti-bot protection")
    
    print(f"\nTest scraping complete!")

if __name__ == "__main__":
    asyncio.run(main())


