"""
scrapers/scrape_team_history_js_v2.py
Purpose: Improved JavaScript-enabled scraper with better error handling
"""

import argparse
import os
import re
import json
import time
import random
from typing import List, Dict
import pandas as pd
from playwright.sync_api import sync_playwright

# ---- Integration: reuse your normalizer/aliases
try:
    from utils.team_normalizer import canonicalize_team_name
except Exception:
    def canonicalize_team_name(s: str) -> str:
        return re.sub(r"\s+", " ", str(s or "").strip().lower())

BASE_URL = "https://rankings.gotsport.com"
TIMEOUT = 60000  # 60 seconds
SLEEP_JITTER = (1.5, 3.5)

def log(msg: str): print(f"[scrape_team_history_js_v2] {msg}")

def save_log(line: str, division: str):
    os.makedirs("logs", exist_ok=True)
    with open(f"logs/scrape_errors_{division}.log", "a", encoding="utf-8") as f:
        f.write(line.rstrip() + "\n")

def scrape_rankings_page_js_v2(division: str) -> List[Dict]:
    """Scrape team rankings using JavaScript rendering with better error handling"""
    age = division.split('_')[-1][1:]  # Extract age from az_boys_u12 -> 12
    url = f"{BASE_URL}/?team_country=USA&age={age}&gender=m&state=AZ"
    log(f"Scraping {division} from {url}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            # Navigate to page
            log("Navigating to page...")
            page.goto(url, timeout=TIMEOUT, wait_until="domcontentloaded")
            
            # Wait a bit for JavaScript to load
            log("Waiting for JavaScript to load...")
            page.wait_for_timeout(5000)
            
            # Try to find any content
            content = page.content()
            log(f"Page content length: {len(content)}")
            
            # Look for any tables or data
            tables = page.query_selector_all("table")
            log(f"Found {len(tables)} tables")
            
            if len(tables) == 0:
                # Try to find any data in the page
                log("No tables found, checking for other content...")
                
                # Look for any text that might indicate rankings
                text_content = page.text_content("body")
                log(f"Body text length: {len(text_content)}")
                log(f"First 500 chars: {text_content[:500]}")
                
                # Check if there's any indication of data loading
                if "loading" in text_content.lower() or "no data" in text_content.lower():
                    log("Page appears to be loading or has no data")
                    return []
                
                # Try to wait longer for content
                log("Waiting longer for content to load...")
                page.wait_for_timeout(10000)
                
                # Check again
                tables = page.query_selector_all("table")
                log(f"After longer wait, found {len(tables)} tables")
            
            if len(tables) == 0:
                log("Still no tables found. Page may not have data for this division.")
                return []
            
            # Extract team data from first table
            teams = page.evaluate("""
                () => {
                    const tables = document.querySelectorAll('table');
                    if (tables.length === 0) return [];
                    
                    const table = tables[0];
                    const rows = Array.from(table.querySelectorAll('tr'));
                    const teams = [];
                    
                    for (let i = 1; i < rows.length; i++) { // Skip header
                        const cells = rows[i].querySelectorAll('td');
                        if (cells.length >= 3) {
                            const rank = cells[0]?.textContent?.trim() || '';
                            const teamName = cells[1]?.textContent?.trim() || '';
                            const club = cells[2]?.textContent?.trim() || '';
                            const points = cells[3]?.textContent?.trim() || '';
                            
                            // Try to find team profile link
                            const link = cells[1]?.querySelector('a');
                            const teamUrl = link ? link.href : '';
                            
                            if (teamName) {
                                teams.push({
                                    rank: rank,
                                    teamName: teamName,
                                    club: club,
                                    points: points,
                                    teamUrl: teamUrl
                                });
                            }
                        }
                    }
                    
                    return teams;
                }
            """)
            
            browser.close()
            log(f"Extracted {len(teams)} teams")
            return teams
            
        except Exception as e:
            log(f"Error scraping {division}: {e}")
            browser.close()
            return []

def run_division_js_v2(division: str) -> int:
    """Run JavaScript-enabled scraping for a division"""
    log(f"Starting JavaScript scraping for {division}")
    
    # Try to scrape team list from rankings page
    teams_data = scrape_rankings_page_js_v2(division)
    
    if not teams_data:
        log(f"No teams found for {division}")
        save_log(f"No teams found for {division} - page may be empty or JavaScript not loading", division)
        return 1
    
    # Save team list to bronze
    teams_df = pd.DataFrame(teams_data)
    teams_df.columns = ["Rank", "Team Name", "Club", "Points", "TeamURL"]
    teams_df["Division"] = division
    teams_df["ScrapeDate"] = pd.Timestamp.now().isoformat()
    
    os.makedirs("bronze", exist_ok=True)
    bronze_file = f"bronze/{division}_teams.csv"
    teams_df.to_csv(bronze_file, index=False)
    log(f"SUCCESS: Saved {len(teams_df)} teams to {bronze_file}")
    
    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--division", required=True, help="az_boys_u10 | az_boys_u11 | az_boys_u12 | az_boys_u13 | az_boys_u14")
    args = parser.parse_args()
    
    code = run_division_js_v2(args.division)
    raise SystemExit(code)
