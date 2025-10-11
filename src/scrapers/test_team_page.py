"""
scrapers/test_team_page.py
Purpose: Test what's on a team profile page
"""

from playwright.sync_api import sync_playwright

def test_team_page(team_url: str):
    print(f"Testing team page: {team_url}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            page.goto(team_url, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(5000)
            
            # Get page content
            content = page.content()
            print(f"Page content length: {len(content)}")
            
            # Look for tables
            tables = page.query_selector_all("table")
            print(f"Found {len(tables)} tables")
            
            # Look for any text that might indicate matches/games/results
            text_content = page.text_content("body")
            print(f"Body text length: {len(text_content)}")
            
            # Check for match-related keywords
            keywords = ["match", "game", "result", "score", "opponent", "date", "competition"]
            found_keywords = [kw for kw in keywords if kw.lower() in text_content.lower()]
            print(f"Found keywords: {found_keywords}")
            
            # Print first 1000 characters of body text
            print(f"First 1000 chars of body text:")
            print(text_content[:1000])
            
            browser.close()
            
        except Exception as e:
            print(f"Error: {e}")
            browser.close()

if __name__ == "__main__":
    import sys
    team_url = sys.argv[1] if len(sys.argv) > 1 else "https://rankings.gotsport.com/teams/238248"
    test_team_page(team_url)
