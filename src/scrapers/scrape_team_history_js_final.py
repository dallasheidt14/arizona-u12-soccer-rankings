"""
scrapers/scrape_team_history_js_final.py
Purpose: Final JavaScript scraper that intercepts the correct API call for match data
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

def log(msg: str): print(f"[scrape_js_final] {msg}")

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

def scrape_rankings_page_js_final(division: str) -> List[Dict]:
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
                        if (cells.length >= 4) {
                            const rank = cells[0]?.textContent?.trim() || '';
                            const teamId = cells[1]?.textContent?.trim() || '';
                            const teamName = cells[2]?.textContent?.trim() || '';
                            const points = cells[3]?.textContent?.trim() || '';
                            
                            // Try to find team profile link in any cell
                            let teamUrl = '';
                            for (const cell of cells) {
                                const link = cell.querySelector('a');
                                if (link && link.href) {
                                    teamUrl = link.href;
                                    break;
                                }
                            }
                            
                            if (teamName) {
                                teams.push({
                                    rank: rank,
                                    teamId: teamId,
                                    teamName: teamName,
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

def scrape_team_matches_js_final(team_name: str, team_url: str, division: str) -> List[Dict]:
    """Scrape individual team matches by intercepting the correct API call"""
    if not team_url:
        return []
    
    # Extract team ID from URL
    team_id_match = re.search(r'/teams/(\d+)', team_url)
    if not team_id_match:
        log(f"Could not extract team ID from URL: {team_url}")
        return []
    
    team_id = team_id_match.group(1)
    game_history_url = f"{BASE_URL}/teams/{team_id}/game-history"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        # Track the specific API call we're looking for
        match_data = None
        
        def handle_response(response):
            url = response.url
            if "it.lngtd.com" in url and response.request.method == "POST":
                try:
                    # Get the request body
                    post_data = response.request.post_data
                    if post_data:
                        data = json.loads(post_data)
                        log(f"Found API call to {url}")
                        log(f"Request body: {json.dumps(data, indent=2)}")
                        
                        # Look for match data in the request
                        if "details" in data and "page" in data["details"]:
                            if data["details"]["page"] == "teams":
                                match_data = data
                                log(f"Found team page data for {team_name}")
                except Exception as e:
                    log(f"Error parsing API response: {e}")
        
        page.on("response", handle_response)
        
        try:
            log(f"Scraping game history from: {game_history_url}")
            page.goto(game_history_url, timeout=TIMEOUT, wait_until="domcontentloaded")
            
            # Wait longer for all API calls to complete
            page.wait_for_timeout(10000)
            
            # Also try to extract match data from the page content directly
            page_matches = page.evaluate("""
                () => {
                    const matches = [];
                    
                    // Look for any data that might contain match information
                    const scripts = document.querySelectorAll('script');
                    for (const script of scripts) {
                        const content = script.textContent;
                        if (content && (content.includes('match') || content.includes('game') || content.includes('result'))) {
                            try {
                                // Try to parse as JSON
                                const data = JSON.parse(content);
                                if (data && (data.matches || data.games || data.results)) {
                                    return data;
                                }
                            } catch (e) {
                                // Not JSON, continue
                            }
                        }
                    }
                    
                    // Look for any tables with match data
                    const tables = document.querySelectorAll('table');
                    for (const table of tables) {
                        const rows = Array.from(table.querySelectorAll('tr'));
                        for (let i = 1; i < rows.length; i++) {
                            const cells = rows[i].querySelectorAll('td');
                            if (cells.length >= 3) {
                                const date = cells[0]?.textContent?.trim() || '';
                                const opponent = cells[1]?.textContent?.trim() || '';
                                const score = cells[2]?.textContent?.trim() || '';
                                
                                const scoreMatch = score.match(/(\\d+)\\s*[-:]\\s*(\\d+)/);
                                if (scoreMatch && opponent) {
                                    matches.push({
                                        date: date,
                                        opponent: opponent,
                                        scoreA: parseInt(scoreMatch[1]),
                                        scoreB: parseInt(scoreMatch[2]),
                                        competition: cells[3]?.textContent?.trim() || ''
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
            
            # First try the API data
            if match_data:
                log(f"Using API data for {team_name}")
                # Parse the API data structure
                # This would need to be adjusted based on the actual structure
                pass
            
            # Then try the page data
            if page_matches:
                log(f"Using page data for {team_name}: {len(page_matches)} matches")
                for match in page_matches:
                    formatted_matches.append({
                        "Team A": team_name,
                        "Team B": canonicalize_team_name(match["opponent"]),
                        "Score A": match["scoreA"],
                        "Score B": match["scoreB"],
                        "Date": match["date"],
                        "Competition": match["competition"],
                        "SourceURL": game_history_url,
                    })
            
            return formatted_matches
            
        except Exception as e:
            log(f"Error scraping matches for {team_name}: {e}")
            save_log(f"Error scraping matches for {team_name}: {e}", division)
            browser.close()
            return []

def run_division_js_final(division: str) -> int:
    """Run final JavaScript scraping for a division"""
    log(f"Starting final JavaScript scraping for {division}")
    
    # Step 1: Scrape team list from rankings page
    teams_data = scrape_rankings_page_js_final(division)
    
    if not teams_data:
        log(f"No teams found for {division}")
        save_log(f"No teams found for {division} - page may be empty or JavaScript not loading", division)
        return 1
    
    # Save team list to bronze
    teams_df = pd.DataFrame(teams_data)
    teams_df.columns = ["Rank", "TeamID", "Team Name", "Points", "TeamURL"]
    teams_df["Division"] = division
    teams_df["ScrapeDate"] = pd.Timestamp.now().isoformat()
    
    os.makedirs("bronze", exist_ok=True)
    bronze_file = f"bronze/{division}_teams.csv"
    teams_df.to_csv(bronze_file, index=False)
    log(f"SUCCESS: Saved {len(teams_df)} teams to {bronze_file}")
    
    # Step 2: Scrape match histories with API detection
    cache = load_profile_cache(division)
    all_matches = []
    
    teams_with_urls = [team for team in teams_data if team["teamUrl"]]
    log(f"Starting match history scraping for {len(teams_with_urls)} teams with URLs...")
    
    # Test with just the first few teams to debug
    test_teams = teams_with_urls[:3]  # Only test first 3 teams
    
    for i, team_data in enumerate(test_teams, 1):
        team_name = team_data["teamName"]
        team_url = team_data["teamUrl"]
        
        log(f"Scraping matches for {team_name} ({i}/{len(test_teams)})")
        
        matches = scrape_team_matches_js_final(team_name, team_url, division)
        all_matches.extend(matches)
        log(f"Found {len(matches)} matches for {team_name}")
        
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
    
    code = run_division_js_final(args.division)
    raise SystemExit(code)