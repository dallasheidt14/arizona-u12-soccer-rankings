"""
scrapers/debug_gotsport_page.py
Purpose: Debug what's actually on the GotSport page
"""

from playwright.sync_api import sync_playwright

def debug_page(division: str):
    age = division.split('_')[-1][1:]  # Extract age from az_boys_u12 -> 12
    url = f"https://rankings.gotsport.com/?team_country=USA&age={age}&gender=m&state=AZ"
    print(f"Debugging {division} from {url}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Show browser for debugging
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(10000)  # Wait longer
            
            # Get page content
            content = page.content()
            print(f"Page content length: {len(content)}")
            
            # Look for tables
            tables = page.query_selector_all("table")
            print(f"Found {len(tables)} tables")
            
            if len(tables) > 0:
                # Get first table HTML
                first_table = tables[0]
                table_html = first_table.inner_html()
                print(f"First table HTML (first 1000 chars):")
                print(table_html[:1000])
                
                # Try to extract data manually
                rows = first_table.query_selector_all("tr")
                print(f"Found {len(rows)} rows in first table")
                
                for i, row in enumerate(rows[:5]):  # First 5 rows
                    cells = row.query_selector_all("td")
                    print(f"Row {i}: {len(cells)} cells")
                    for j, cell in enumerate(cells):
                        text = cell.text_content().strip()
                        links = cell.query_selector_all("a")
                        print(f"  Cell {j}: '{text}' ({len(links)} links)")
                        for k, link in enumerate(links):
                            href = link.get_attribute("href")
                            link_text = link.text_content().strip()
                            print(f"    Link {k}: '{link_text}' -> '{href}'")
            
            # Keep browser open for manual inspection
            input("Press Enter to close browser...")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    import sys
    division = sys.argv[1] if len(sys.argv) > 1 else "az_boys_u12"
    debug_page(division)
