"""
scrapers/scrape_team_history_js_matches_api.py
Purpose: Final JavaScript scraper that targets the correct matches API endpoint
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

def log(msg: str): print(f"[scrape_js_matches] {msg}")

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

def scrape_rankings_page_js_matches(division: str) -> List[Dict]:
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

def scrape_team_matches_js_matches(team_name: str, team_url: str, division: str) -> List[Dict]:
    """Scrape individual team matches by targeting the correct API endpoint"""
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
        
        # Track the specific matches API call
        matches_data = [None]  # Use list to allow modification in nested function
        
        def handle_response(response):
            url = response.url
            if "system.gotsport.com/api/v1/teams" in url and "matches" in url and "past=true" in url:
                try:
                    if response.status == 200:
                        response_text = response.text()
                        log(f"Found matches API call: {url}")
                        log(f"Response preview: {response_text[:200]}...")
                        
                        try:
                            data = json.loads(response_text)
                            matches_data[0] = data  # Store in the list
                            log(f"Successfully parsed matches data for {team_name}")
                        except Exception as e:
                            log(f"Error parsing matches JSON: {e}")
                except Exception as e:
                    log(f"Error processing matches response: {e}")
        
        page.on("response", handle_response)
        
        try:
            log(f"Scraping game history from: {game_history_url}")
            page.goto(game_history_url, timeout=TIMEOUT, wait_until="domcontentloaded")
            
            # Wait longer for all API calls to complete
            page.wait_for_timeout(15000)
            
            browser.close()
            
            # Process the matches data
            formatted_matches = []
            
            if matches_data[0]:
                log(f"Processing {len(matches_data[0])} matches for {team_name}")
                log(f"Matches data type: {type(matches_data[0])}")
                log(f"First match sample: {matches_data[0][0] if matches_data[0] else 'None'}")
                
                # The API response is an array of match objects
                if isinstance(matches_data[0], list):
                    for i, match in enumerate(matches_data[0]):
                        log(f"Processing match {i+1}: {match.get('title', 'No title')}")
                        try:
                            # Extract data from the actual API response structure
                            title = match.get('title', '')
                            match_time = match.get('matchTime', '')
                            
                            # Parse the title to extract opponent and scores
                            # Format: "Tuzos Academy GTA 2016 vs. Southeast 2016 Boys Black"
                            if ' vs. ' in title:
                                parts = title.split(' vs. ')
                                if len(parts) == 2:
                                    team_a = parts[0].strip()
                                    team_b = parts[1].strip()
                                    
                                    # Determine which team is the current team and which is the opponent
                                    if team_name.lower() in team_a.lower():
                                        opponent = team_b
                                    elif team_name.lower() in team_b.lower():
                                        opponent = team_a
                                    else:
                                        # If team name doesn't match exactly, use the other team as opponent
                                        opponent = team_b if team_name.lower() in team_a.lower() else team_a
                                    
                                    # Extract actual scores from the API response
                                    home_score = match.get('home_score', 0)
                                    away_score = match.get('away_score', 0)
                                    
                                    # Determine which team is which based on the title
                                    if team_name.lower() in team_a.lower():
                                        # Current team is team A (home), opponent is team B (away)
                                        score_a = home_score
                                        score_b = away_score
                                    elif team_name.lower() in team_b.lower():
                                        # Current team is team B (away), opponent is team A (home)
                                        score_a = away_score
                                        score_b = home_score
                                    else:
                                        # Fallback - use home/away scores as-is
                                        score_a = home_score
                                        score_b = away_score
                                    
                                    # Parse the match time
                                    date = ''
                                    if match_time:
                                        try:
                                            # Convert ISO format to readable date
                                            from datetime import datetime
                                            dt = datetime.fromisoformat(match_time.replace('Z', '+00:00'))
                                            date = dt.strftime('%Y-%m-%d')
                                        except:
                                            date = match_time
                                    
                                    formatted_matches.append({
                                        "Team A": team_name,
                                        "Team B": canonicalize_team_name(opponent),
                                        "Score A": score_a,
                                        "Score B": score_b,
                                        "Date": date,
                                        "Competition": match.get('event_name', ''),
                                        "SourceURL": game_history_url,
                                    })
                                    
                                    log(f"Added match: {team_name} vs {opponent} ({score_a}-{score_b}) on {date}")
                        except Exception as e:
                            log(f"Error processing match: {e}")
                            continue
                else:
                    log(f"Unexpected matches data format: {type(matches_data)}")
            else:
                log(f"No matches data found for {team_name}")
            
            return formatted_matches
            
        except Exception as e:
            log(f"Error scraping matches for {team_name}: {e}")
            save_log(f"Error scraping matches for {team_name}: {e}", division)
            browser.close()
            return []

def run_division_js_matches(division: str) -> int:
    """Run matches API targeting JavaScript scraping for a division"""
    log(f"Starting matches API targeting JavaScript scraping for {division}")
    
    # Step 1: Scrape team list from rankings page
    teams_data = scrape_rankings_page_js_matches(division)
    
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
    
    # Step 2: Load comprehensive team list if available
    comprehensive_file = f"bronze/{division}_comprehensive_teams.csv"
    if os.path.exists(comprehensive_file):
        log(f"Using comprehensive team list: {comprehensive_file}")
        comprehensive_df = pd.read_csv(comprehensive_file)
        comprehensive_teams = []
        for _, row in comprehensive_df.iterrows():
            # Handle NaN values from pandas
            team_url = row.get("TeamURL", "")
            if pd.isna(team_url):
                team_url = ""
            
            comprehensive_teams.append({
                "teamName": row["Team Name"],
                "teamUrl": team_url,
                "teamId": row.get("TeamID", "")
            })
        teams_data = comprehensive_teams
        log(f"Loaded {len(teams_data)} teams from comprehensive list")
    
    # Step 3: Scrape match histories using the correct API
    cache = load_profile_cache(division)
    all_matches = []
    
    # Since we're using comprehensive list, all teams are Arizona teams
    # But we need to find their GotSport URLs first
    log(f"Processing {len(teams_data)} Arizona teams from comprehensive list...")
    
    # For teams without URLs, we'll need to search for them
    teams_with_urls = [team for team in teams_data if team["teamUrl"]]
    teams_without_urls = [team for team in teams_data if not team["teamUrl"]]
    
    log(f"Teams with URLs: {len(teams_with_urls)}")
    log(f"Teams without URLs: {len(teams_without_urls)}")
    
    # Process teams with URLs first
    test_teams = teams_with_urls
    
    for i, team_data in enumerate(test_teams, 1):
        team_name = team_data["teamName"]
        team_url = team_data["teamUrl"]
        
        log(f"Scraping matches for {team_name} ({i}/{len(test_teams)})")
        
        matches = scrape_team_matches_js_matches(team_name, team_url, division)
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
    
    code = run_division_js_matches(args.division)
    raise SystemExit(code)
