#!/usr/bin/env python3
"""
Debug script to see what's actually on a GotSport game history page
"""
import asyncio
from playwright.async_api import async_playwright
import pandas as pd

async def debug_game_history_page():
    """Debug what's actually on the game history page"""
    
    # Use the team ID you provided as an example
    team_id = "163451"
    url = f"https://rankings.gotsport.com/teams/{team_id}/game-history"
    
    print(f"Debugging game history page: {url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Show browser for debugging
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        page = await context.new_page()
        
        try:
            print("Loading page...")
            await page.goto(url, wait_until='networkidle', timeout=30000)
            
            # Wait for content to load
            await page.wait_for_timeout(5000)
            
            # Get page title
            title = await page.title()
            print(f"Page title: {title}")
            
            # Get all text content
            page_text = await page.inner_text('body')
            print(f"\nPage content length: {len(page_text)}")
            print(f"First 1000 characters:")
            print(page_text[:1000])
            
            # Look for specific elements
            print(f"\nLooking for specific elements...")
            
            # Check for tables
            tables = await page.query_selector_all('table')
            print(f"Found {len(tables)} tables")
            
            # Check for any elements with game-like content
            game_elements = await page.query_selector_all('*')
            print(f"Found {len(game_elements)} total elements")
            
            # Look for elements containing 'vs' or similar
            vs_elements = []
            for element in game_elements[:100]:  # Check first 100 elements
                try:
                    text = await element.inner_text()
                    if text and ('vs' in text.lower() or 'v.' in text.lower() or 'game' in text.lower()):
                        vs_elements.append(text.strip())
                except:
                    continue
            
            print(f"Found {len(vs_elements)} elements with game-like text:")
            for elem in vs_elements[:10]:
                print(f"  {elem}")
            
            # Check for any data attributes
            data_elements = await page.query_selector_all('[data-*]')
            print(f"Found {len(data_elements)} elements with data attributes")
            
            # Wait for user to see the page
            print("\nBrowser will stay open for 30 seconds for manual inspection...")
            await page.wait_for_timeout(30000)
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_game_history_page())


