"""
scrapers/scrape_team_history_js_comprehensive.py
Purpose: Comprehensive JavaScript scraper that looks for ALL API calls and page content
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

def log(msg: str): print(f"[scrape_js_comp] {msg}")

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

def scrape_rankings_page_js_comp(division: str) -> List[Dict]:
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

def scrape_team_matches_js_comp(team_name: str, team_url: str, division: str) -> List[Dict]:
    """Comprehensive match scraping - look for ALL API calls and page content"""
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
        
        # Track ALL API calls
        all_api_calls = []
        potential_match_data = []
        
        def handle_response(response):
            url = response.url
            method = response.request.method
            
            # Log all API calls for debugging
            if any(keyword in url.lower() for keyword in ['api', 'data', 'matches', 'games', 'results', 'team', 'gotsport']):
                all_api_calls.append({
                    'url': url,
                    'method': method,
                    'status': response.status
                })
                log(f"API call: {method} {url} -> {response.status}")
                
                # Try to get response body for potential match data
                try:
                    if response.status == 200:
                        # For GET requests, try to get response body
                        if method == "GET":
                            try:
                                response_text = response.text()
                                if response_text and len(response_text) > 100:  # Only log substantial responses
                                    log(f"Response body preview: {response_text[:200]}...")
                                    
                                    # Look for JSON data
                                    try:
                                        data = json.loads(response_text)
                                        if isinstance(data, (dict, list)) and any(keyword in str(data).lower() for keyword in ['match', 'game', 'result', 'score', 'opponent']):
                                            potential_match_data.append(data)
                                            log(f"Found potential match data in {url}")
                                    except:
                                        pass
                            except:
                                pass
                except Exception as e:
                    log(f"Error processing response from {url}: {e}")
        
        page.on("response", handle_response)
        
        try:
            log(f"Scraping game history from: {game_history_url}")
            page.goto(game_history_url, timeout=TIMEOUT, wait_until="domcontentloaded")
            
            # Wait longer for all API calls to complete
            page.wait_for_timeout(15000)
            
            # Try to extract match data from the page content
            page_data = page.evaluate("""
                () => {
                    const result = {
                        tables: [],
                        scripts: [],
                        divs: [],
                        allText: document.body.textContent || ''
                    };
                    
                    // Look for tables
                    const tables = document.querySelectorAll('table');
                    for (const table of tables) {
                        const rows = Array.from(table.querySelectorAll('tr'));
                        const tableData = [];
                        for (let i = 0; i < rows.length; i++) {
                            const cells = rows[i].querySelectorAll('td, th');
                            const rowData = Array.from(cells).map(cell => cell.textContent.trim());
                            tableData.push(rowData);
                        }
                        result.tables.push(tableData);
                    }
                    
                    // Look for script tags with potential data
                    const scripts = document.querySelectorAll('script');
                    for (const script of scripts) {
                        const content = script.textContent;
                        if (content && content.length > 50) {
                            result.scripts.push(content.substring(0, 500)); // First 500 chars
                        }
                    }
                    
                    // Look for divs that might contain match data
                    const divs = document.querySelectorAll('div');
                    for (const div of divs) {
                        const text = div.textContent;
                        if (text && text.length > 20 && (text.includes('vs') || text.includes('score') || text.includes('match'))) {
                            result.divs.push(text.substring(0, 200));
                        }
                    }
                    
                    return result;
                }
            """)
            
            browser.close()
            
            # Analyze the data we found
            log(f"Found {len(all_api_calls)} API calls")
            log(f"Found {len(potential_match_data)} potential match data sources")
            log(f"Found {len(page_data['tables'])} tables on page")
            log(f"Found {len(page_data['scripts'])} script tags")
            log(f"Found {len(page_data['divs'])} relevant divs")
            
            # Try to extract matches from page data
            formatted_matches = []
            
            # Check tables for match data
            for table in page_data['tables']:
                for row in table:
                    if len(row) >= 3:
                        # Look for score patterns
                        for cell in row:
                            score_match = re.search(r'(\d+)\s*[-:]\s*(\d+)', cell)
                            if score_match:
                                # Found a score, try to extract match data
                                log(f"Found score pattern: {cell}")
                                # This would need more sophisticated parsing
            
            # Check scripts for match data
            for script in page_data['scripts']:
                if any(keyword in script.lower() for keyword in ['match', 'game', 'result', 'score']):
                    log(f"Found relevant script: {script[:100]}...")
            
            # Check divs for match data
            for div in page_data['divs']:
                log(f"Found relevant div: {div[:100]}...")
            
            return formatted_matches
            
        except Exception as e:
            log(f"Error scraping matches for {team_name}: {e}")
            save_log(f"Error scraping matches for {team_name}: {e}", division)
            browser.close()
            return []

def run_division_js_comp(division: str) -> int:
    """Run comprehensive JavaScript scraping for a division"""
    log(f"Starting comprehensive JavaScript scraping for {division}")
    
    # Step 1: Scrape team list from rankings page
    teams_data = scrape_rankings_page_js_comp(division)
    
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
    
    # Step 2: Scrape match histories comprehensively
    cache = load_profile_cache(division)
    all_matches = []
    
    teams_with_urls = [team for team in teams_data if team["teamUrl"]]
    log(f"Starting comprehensive match history scraping for {len(teams_with_urls)} teams with URLs...")
    
    # Test with just the first team to debug
    test_teams = teams_with_urls[:1]  # Only test first team
    
    for i, team_data in enumerate(test_teams, 1):
        team_name = team_data["teamName"]
        team_url = team_data["teamUrl"]
        
        log(f"Comprehensive scraping for {team_name} ({i}/{len(test_teams)})")
        
        matches = scrape_team_matches_js_comp(team_name, team_url, division)
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
    
    code = run_division_js_comp(args.division)
    raise SystemExit(code)
