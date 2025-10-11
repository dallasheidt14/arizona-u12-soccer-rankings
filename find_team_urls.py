"""
Search for Arizona teams on GotSport to find their profile URLs
"""
import asyncio
import pandas as pd
from playwright.async_api import async_playwright

async def search_team_url(team_name, page):
    """Search for a team on GotSport and return its profile URL"""
    try:
        # Search for the team
        search_url = f"https://rankings.gotsport.com/team_search?search={team_name}"
        await page.goto(search_url, wait_until="domcontentloaded", timeout=10000)
        
        # Wait for results to load
        await page.wait_for_timeout(3000)
        
        # Look for team links in search results
        team_links = await page.query_selector_all('a[href*="/teams/"]')
        
        for link in team_links:
            link_text = await link.inner_text()
            if team_name.lower() in link_text.lower():
                href = await link.get_attribute('href')
                if href and '/teams/' in href:
                    return f"https://rankings.gotsport.com{href}"
        
        return None
    except Exception as e:
        print(f"Error searching for {team_name}: {e}")
        return None

async def find_all_team_urls():
    """Find GotSport URLs for all Arizona teams"""
    # Load the comprehensive team list
    df = pd.read_csv("bronze/az_boys_u10_comprehensive_teams.csv")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        team_urls = {}
        
        for i, row in df.iterrows():
            team_name = row["Team Name"]
            print(f"Searching for {team_name} ({i+1}/{len(df)})...")
            
            url = await search_team_url(team_name, page)
            if url:
                team_urls[team_name] = url
                print(f"  Found: {url}")
            else:
                print(f"  Not found")
            
            # Small delay between searches
            await page.wait_for_timeout(1000)
        
        await browser.close()
    
    # Update the comprehensive team list with found URLs
    for i, row in df.iterrows():
        team_name = row["Team Name"]
        if team_name in team_urls:
            df.at[i, "TeamURL"] = team_urls[team_name]
    
    # Save updated list
    df.to_csv("bronze/az_boys_u10_comprehensive_teams.csv", index=False)
    print(f"\nUpdated team list with {len(team_urls)} URLs found")
    
    return team_urls

if __name__ == "__main__":
    asyncio.run(find_all_team_urls())
