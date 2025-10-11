"""
scrapers/scrape_team_history_js_complete.py
Purpose: Complete JavaScript-enabled scraper for GotSport's SPA architecture
Handles both team list extraction and match history scraping
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

def log(msg: str): print(f"[scrape_js_complete] {msg}")

def save_log(line: str, division: str):
    os.makedirs("logs", exist_ok=True)
    with open(f"logs/scrape_errors_{division}.log", "a", encoding="utf-8") as f:
        f.write(line.rstrip() + "\n")

def load_profile_cache(division: str) -> Dict[str, str]:
    path = f"bronze/team_profiles_{division}.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_profile_cache(cache: Dict[str, str], division: str):
    os.makedirs("bronze", exist_ok=True)
    path = f"bronze/team_profiles_{division}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def scrape_rankings_page_js(division: str) -> List[Dict]:
    """Scrape team rankings using JavaScript rendering"""
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
            page.goto(url, timeout=TIMEOUT, wait_until="domcontentloaded")
            
            # Wait for JavaScript to load
            page.wait_for_timeout(5000)
            
            # Extract team data
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

def scrape_team_matches_js(team_name: str, team_url: str, division: str) -> List[Dict]:
    """Scrape individual team matches using JavaScript rendering"""
    if not team_url:
        return []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            page.goto(team_url, timeout=TIMEOUT, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            
            # Extract match data
            matches = page.evaluate("""
                () => {
                    const tables = document.querySelectorAll('table');
                    const matches = [];
                    
                    for (const table of tables) {
                        const rows = Array.from(table.querySelectorAll('tr'));
                        
                        for (let i = 1; i < rows.length; i++) { // Skip header
                            const cells = rows[i].querySelectorAll('td');
                            if (cells.length >= 4) {
                                const date = cells[0]?.textContent?.trim() || '';
                                const opponent = cells[1]?.textContent?.trim() || '';
                                const score = cells[2]?.textContent?.trim() || '';
                                const competition = cells[3]?.textContent?.trim() || '';
                                
                                // Parse score - handle various formats
                                const scoreMatch = score.match(/(\\d+)\\s*[-:]\\s*(\\d+)/);
                                if (scoreMatch) {
                                    matches.push({
                                        date: date,
                                        opponent: opponent,
                                        scoreA: parseInt(scoreMatch[1]),
                                        scoreB: parseInt(scoreMatch[2]),
                                        competition: competition
                                    });
                                }
                            }
                        }
                    }
                    
                    return matches;
                }
            """)
            
            browser.close()
            
            # Convert to our format
            formatted_matches = []
            for match in matches:
                formatted_matches.append({
                    "Team A": team_name,
                    "Team B": canonicalize_team_name(match["opponent"]),
                    "Score A": match["scoreA"],
                    "Score B": match["scoreB"],
                    "Date": match["date"],
                    "Competition": match["competition"],
                    "SourceURL": team_url,
                })
            
            return formatted_matches
            
        except Exception as e:
            log(f"Error scraping matches for {team_name}: {e}")
            save_log(f"Error scraping matches for {team_name}: {e}", division)
            browser.close()
            return []

def run_division_js_complete(division: str) -> int:
    """Run complete JavaScript-enabled scraping for a division"""
    log(f"Starting complete JavaScript scraping for {division}")
    
    # Step 1: Scrape team list from rankings page
    teams_data = scrape_rankings_page_js(division)
    
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
    
    # Step 2: Scrape match histories
    cache = load_profile_cache(division)
    all_matches = []
    
    log(f"Starting match history scraping for {len(teams_data)} teams...")
    
    for i, team_data in enumerate(teams_data, 1):
        team_name = team_data["teamName"]
        team_url = team_data["teamUrl"]
        
        log(f"Scraping matches for {team_name} ({i}/{len(teams_data)})")
        
        if team_url:
            matches = scrape_team_matches_js(team_name, team_url, division)
            all_matches.extend(matches)
            log(f"Found {len(matches)} matches for {team_name}")
        else:
            log(f"No URL found for {team_name}, skipping")
        
        # Polite delay
        time.sleep(random.uniform(*SLEEP_JITTER))
    
    # Save profile cache
    cache.update({team["teamName"]: team["teamUrl"] for team in teams_data})
    save_profile_cache(cache, division)
    
    # Write gold output
    os.makedirs("gold", exist_ok=True)
    div_up = division.upper()
    out_path = f"gold/Matched_Games_{div_up}.csv"
    pd.DataFrame(all_matches).to_csv(out_path, index=False)
    log(f"SUCCESS: Saved {len(all_matches)} total matches to {out_path}")
    
    # Summary
    teams_with_games = {match["Team A"] for match in all_matches}
    log(f"Summary: {len(teams_with_games)}/{len(teams_data)} teams have match data")
    
    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--division", required=True, help="az_boys_u10 | az_boys_u11 | az_boys_u12 | az_boys_u13 | az_boys_u14")
    args = parser.parse_args()
    
    code = run_division_js_complete(args.division)
    raise SystemExit(code)
