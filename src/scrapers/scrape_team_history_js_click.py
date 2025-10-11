"""
scrapers/scrape_team_history_js_click.py
Purpose: JavaScript scraper that clicks on Game History to load match data
"""

from playwright.sync_api import sync_playwright

def test_click_game_history(team_url: str):
    print(f"Testing Game History click on: {team_url}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Show browser for debugging
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            page.goto(team_url, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(5000)
            
            # Look for Game History link/button
            game_history_elements = page.query_selector_all("text=Game History")
            print(f"Found {len(game_history_elements)} 'Game History' elements")
            
            # Also look for any clickable elements with "game" or "history"
            all_elements = page.query_selector_all("*")
            clickable_elements = []
            
            for element in all_elements:
                text = element.text_content()
                if text and ("game" in text.lower() or "history" in text.lower()):
                    tag = element.tag_name.lower()
                    if tag in ["a", "button", "div", "span"]:
                        clickable_elements.append((tag, text.strip()[:50]))
            
            print(f"Found {len(clickable_elements)} clickable elements with game/history text:")
            for tag, text in clickable_elements[:10]:  # Show first 10
                print(f"  {tag}: {text}")
            
            # Try to click on Game History if found
            if game_history_elements:
                print("Clicking on Game History...")
                game_history_elements[0].click()
                page.wait_for_timeout(3000)
                
                # Check for tables after clicking
                tables = page.query_selector_all("table")
                print(f"After clicking, found {len(tables)} tables")
                
                # Look for match data
                text_content = page.text_content("body")
                if "vs" in text_content.lower() or "score" in text_content.lower():
                    print("Found potential match data after clicking!")
                else:
                    print("No match data found after clicking")
            
            # Keep browser open for manual inspection
            input("Press Enter to close browser...")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    import sys
    team_url = sys.argv[1] if len(sys.argv) > 1 else "https://rankings.gotsport.com/teams/238248"
    test_click_game_history(team_url)
