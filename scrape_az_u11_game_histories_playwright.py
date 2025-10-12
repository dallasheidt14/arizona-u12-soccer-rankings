#!/usr/bin/env python3
"""
Scrape game histories for Arizona U11 teams using Playwright for JavaScript-rendered pages
"""
import pandas as pd
import asyncio
from playwright.async_api import async_playwright
import time
from pathlib import Path
from datetime import datetime
import json

async def scrape_team_game_history(page, team_id, team_name):
    """Scrape game history for a single team using Playwright"""
    
    url = f"https://rankings.gotsport.com/teams/{team_id}/game-history"
    
    try:
        print(f"  Scraping {team_name} (ID: {team_id})...")
        
        await page.goto(url, wait_until='networkidle', timeout=30000)
        
        # Wait for the page to load
        await page.wait_for_timeout(3000)
        
        # Look for game data in various possible selectors
        games = []
        
        # Try different selectors for game data
        selectors_to_try = [
            'table tr',
            '.game-row',
            '.match-row', 
            '[data-testid*="game"]',
            '.history-row',
            'tbody tr',
            '.team-game'
        ]
        
        for selector in selectors_to_try:
            try:
                elements = await page.query_selector_all(selector)
                if elements and len(elements) > 1:  # More than just header
                    print(f"    Found {len(elements)} elements with selector: {selector}")
                    
                    for element in elements[1:]:  # Skip first element (likely header)
                        try:
                            text = await element.inner_text()
                            if text and len(text.strip()) > 10:  # Reasonable content
                                # Try to extract structured data
                                cells = await element.query_selector_all('td, th, div')
                                if len(cells) >= 3:
                                    date = await cells[0].inner_text() if len(cells) > 0 else ""
                                    opponent = await cells[1].inner_text() if len(cells) > 1 else ""
                                    score = await cells[2].inner_text() if len(cells) > 2 else ""
                                    result = await cells[3].inner_text() if len(cells) > 3 else ""
                                    
                                    if date.strip() and opponent.strip():
                                        games.append({
                                            'date': date.strip(),
                                            'opponent': opponent.strip(),
                                            'score': score.strip(),
                                            'result': result.strip()
                                        })
                                else:
                                    # If no structured cells, try to parse the text
                                    if 'vs' in text.lower() or 'v.' in text.lower():
                                        games.append({
                                            'date': 'Unknown',
                                            'opponent': text.strip(),
                                            'score': '',
                                            'result': ''
                                        })
                        except Exception as e:
                            continue
                    
                    if games:
                        break  # Found games with this selector
                        
            except Exception as e:
                continue
        
        # If still no games, try to get all text and look for game patterns
        if not games:
            try:
                page_text = await page.inner_text('body')
                lines = page_text.split('\n')
                
                for line in lines:
                    line = line.strip()
                    if ('vs' in line.lower() or 'v.' in line.lower()) and len(line) > 10:
                        games.append({
                            'date': 'Unknown',
                            'opponent': line,
                            'score': '',
                            'result': ''
                        })
                        
                # Limit to avoid too many false positives
                games = games[:20]
                
            except Exception as e:
                pass
        
        print(f"    Found {len(games)} games")
        return games
        
    except Exception as e:
        print(f"    Error scraping {team_name}: {e}")
        return []

async def main():
    print("Scraping game histories for Arizona U11 teams using Playwright...")
    
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
        # Launch browser
        browser = await p.chromium.launch(headless=True)  # Set to True for headless
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        
        try:
            # Scrape each team's game history
            for idx, row in df.iterrows():
                team_id = row['gotsport_team_id']
                team_name = row['display_name']
                
                print(f"\n{idx + 1}/{len(df)}: {team_name}")
                
                # Create a new page for each team
                page = await context.new_page()
                
                try:
                    games = await scrape_team_game_history(page, team_id, team_name)
                    
                    if games:
                        successful_teams += 1
                        # Add team info to each game
                        for game in games:
                            game['team_id'] = team_id
                            game['team_name'] = team_name
                            game['club'] = row.get('club', '')
                            all_games.append(game)
                    
                    # Be respectful to the server
                    await asyncio.sleep(2)
                    
                    # Save progress every 10 teams
                    if (idx + 1) % 10 == 0:
                        if all_games:
                            progress_df = pd.DataFrame(all_games)
                            progress_file = output_dir / f"az_u11_games_progress_{idx + 1}.csv"
                            progress_df.to_csv(progress_file, index=False)
                            print(f"  Progress saved: {progress_file}")
                    
                    # Limit to first 5 teams for testing
                    if idx >= 4:
                        print("  Stopping after 5 teams for testing...")
                        break
                        
                finally:
                    await page.close()
        
        finally:
            await browser.close()
    
    # Save final results
    if all_games:
        final_df = pd.DataFrame(all_games)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_file = output_dir / f"az_u11_game_histories_{timestamp}.csv"
        final_df.to_csv(final_file, index=False)
        
        print(f"\nSUCCESS!")
        print(f"Scraped game histories for {successful_teams} Arizona teams")
        print(f"Total games found: {len(all_games)}")
        print(f"Saved to: {final_file}")
        
        # Show sample games
        print(f"\nSample games:")
        print(final_df.head(10).to_string(index=False))
        
    else:
        print(f"\nNo games found for any teams")
    
    print(f"\nGame history scraping complete!")

if __name__ == "__main__":
    asyncio.run(main())
