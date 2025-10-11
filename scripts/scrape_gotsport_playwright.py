#!/usr/bin/env python3
"""
Scrape GotSport U11 master team list using Playwright to handle JavaScript rendering.
This will get the actual authoritative team names from the GotSport rankings page.
"""

import asyncio
import pandas as pd
import sys
import os
from pathlib import Path
from playwright.async_api import async_playwright

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.id_codec import make_team_id

async def scrape_gotsport_with_playwright():
    """Scrape GotSport rankings page using Playwright."""
    
    url = "https://rankings.gotsport.com/?team_country=USA&age=11&gender=m&state=AZ"
    
    print(f"Scraping GotSport with Playwright from: {url}")
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Set user agent
        await page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        try:
            print("Loading page...")
            await page.goto(url, wait_until='networkidle', timeout=30000)
            
            # Wait for content to load
            print("Waiting for rankings table to load...")
            await page.wait_for_timeout(5000)  # Wait 5 seconds for JS to render
            
            # Try to find the rankings table
            teams = []
            
            # Method 1: Look for table rows
            try:
                # Wait for table to appear
                await page.wait_for_selector('table, .rankings-table, [data-testid="rankings-table"]', timeout=10000)
                
                # Get all table rows
                rows = await page.query_selector_all('tr')
                print(f"Found {len(rows)} table rows")
                
                for i, row in enumerate(rows):
                    cells = await row.query_selector_all('td, th')
                    if len(cells) >= 2:
                        # Usually team name is in second column
                        team_cell = cells[1]
                        team_text = await team_cell.inner_text()
                        team_text = team_text.strip()
                        
                        if team_text and len(team_text) > 5 and not team_text.isdigit():
                            teams.append(team_text)
                            if i < 10:  # Show first 10
                                print(f"  Row {i}: {team_text}")
                
            except Exception as e:
                print(f"Table method failed: {e}")
            
            # Method 2: Look for any text that looks like team names
            if len(teams) < 10:
                print("Trying alternative method - searching page text...")
                
                # Get all text content
                page_text = await page.inner_text('body')
                lines = [line.strip() for line in page_text.split('\n') if line.strip()]
                
                for line in lines:
                    # Look for lines that contain team indicators
                    if (('Boys' in line or 'FC' in line or 'SC' in line or 'AZ' in line) and 
                        len(line) > 10 and len(line) < 100 and
                        not line.isdigit() and
                        'Rank' not in line and 'Team' not in line and
                        'GotSport' not in line and 'Copyright' not in line and
                        'Loading' not in line and 'Error' not in line):
                        teams.append(line)
            
            # Method 3: Look for specific selectors
            if len(teams) < 10:
                print("Trying selector-based approach...")
                
                selectors = [
                    '.team-name',
                    '.team',
                    '[data-field="team"]',
                    '.rankings-team',
                    '.team-row',
                    'td:nth-child(2)',
                    'div[class*="team"]',
                    'span[class*="team"]'
                ]
                
                for selector in selectors:
                    try:
                        elements = await page.query_selector_all(selector)
                        if elements:
                            print(f"Found {len(elements)} elements with selector: {selector}")
                            for elem in elements[:20]:  # Check first 20
                                text = await elem.inner_text()
                                text = text.strip()
                                if text and len(text) > 5 and 'Boys' in text:
                                    teams.append(text)
                            break
                    except:
                        continue
            
            # Remove duplicates and sort
            teams = list(set(teams))
            teams.sort()
            
            print(f"\nFound {len(teams)} unique teams")
            
            # Show all teams found
            print("\nAll teams found:")
            for i, team in enumerate(teams):
                print(f"  {i+1:3d}. {team}")
            
            # Save page screenshot for debugging
            await page.screenshot(path="debug_gotsport_playwright.png")
            print("Saved screenshot to debug_gotsport_playwright.png")
            
            await browser.close()
            return teams
            
        except Exception as e:
            print(f"Error during scraping: {e}")
            await browser.close()
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

async def main():
    try:
        # Scrape teams from GotSport using Playwright
        teams = await scrape_gotsport_with_playwright()
        
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
            print("Check debug_gotsport_playwright.png to see what was rendered")
            
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
