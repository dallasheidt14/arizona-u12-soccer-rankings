"""
Multi-Division Soccer Data Scraper
Production-ready scraper supporting U11 and U12 divisions with identical architecture
"""

import os
import re
import time
import argparse
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

# Optional canonicalizer (shared with U12)
try:
    from utils.team_normalizer import canonicalize_team_name
except ImportError:
    def canonicalize_team_name(x): return x.strip().lower()

# ------------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------------
BASE_URL = "https://rankings.gotsport.com/"
DIVISION_URLS = {
    "az_boys_u12": "https://rankings.gotsport.com/?team_country=USA&age=12&gender=m&state=AZ",
    "az_boys_u11": "https://rankings.gotsport.com/?team_country=USA&age=11&gender=m&state=AZ",
    "az_boys_u10": "https://rankings.gotsport.com/?team_country=USA&age=10&gender=m&state=AZ",
    "az_boys_u13": "https://rankings.gotsport.com/?team_country=USA&age=13&gender=m&state=AZ",
    "az_boys_u14": "https://rankings.gotsport.com/?team_country=USA&age=14&gender=m&state=AZ",
}
BRONZE_DIR, GOLD_DIR = "bronze", "gold"
REQUEST_DELAY = 1.0
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}

# ------------------------------------------------------------------
# SCRAPE RANKINGS TABLE (TEAM LIST)
# ------------------------------------------------------------------
def scrape_team_list(division_key: str) -> pd.DataFrame:
    """Scrape team names and profile URLs from GotSport rankings page."""
    url = DIVISION_URLS[division_key]
    print(f"Scraping {division_key} rankings from {url}")
    
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        print(f"Response status: {r.status_code}")
        print(f"Response length: {len(r.text)} characters")
        soup = BeautifulSoup(r.text, "html.parser")

        rows = []
        # Try multiple possible table selectors
        table = soup.find("table", {"id": "ranking_table"})
        if not table:
            table = soup.find("table", {"id": "ranking-table"})
        if not table:
            table = soup.find("table", {"class": "ranking-table"})
        if not table:
            # Fallback: find any table with ranking-like content
            tables = soup.find_all("table")
            print(f"Found {len(tables)} tables on page")
            for i, t in enumerate(tables):
                table_text = t.get_text().lower()
                print(f"Table {i}: {table_text[:100]}...")
                if "rank" in table_text or "team" in table_text or "points" in table_text:
                    table = t
                    print(f"Using table {i}")
                    break
        
        if not table:
            # Debug: print page content to understand structure
            print("Page content preview:")
            print(soup.get_text()[:500])
            raise RuntimeError("Ranking table not found (page layout may have changed).")

        for tr in table.find_all("tr")[1:]:  # Skip header row
            tds = tr.find_all("td")
            if len(tds) < 3:
                continue
                
            rank = tds[0].get_text(strip=True)
            team_name = tds[1].get_text(strip=True)
            a = tds[1].find("a")
            team_url = urljoin(BASE_URL, a["href"]) if a and a.get("href") else None
            club = tds[2].get_text(strip=True) if len(tds) > 2 else "Unknown"
            pts = tds[3].get_text(strip=True) if len(tds) > 3 else None
            
            rows.append({
                "Rank": int(rank) if rank.isdigit() else None,
                "TeamName": team_name,
                "TeamCanonical": canonicalize_team_name(team_name),
                "Club": club,
                "Points": pts,
                "TeamURL": team_url,
                "Division": division_key,
                "ScrapeDate": datetime.utcnow().isoformat()
            })

        df = pd.DataFrame(rows)
        os.makedirs(BRONZE_DIR, exist_ok=True)
        out_path = os.path.join(BRONZE_DIR, f"{division_key}_teams.csv")
        df.to_csv(out_path, index=False)
        print(f"Saved {len(df)} teams to {out_path}")
        return df
        
    except Exception as e:
        print(f"Failed to scrape {division_key}: {e}")
        return pd.DataFrame()


# ------------------------------------------------------------------
# SCRAPE GAME HISTORIES
# ------------------------------------------------------------------
def scrape_team_games(team_row) -> list:
    """Scrape all matches from a team's GotSport profile page."""
    team_name, team_url, division = team_row["TeamName"], team_row["TeamURL"], team_row["Division"]
    if not team_url:
        return []
        
    try:
        r = requests.get(team_url, headers=HEADERS, timeout=20)
        r.raise_for_status()
    except Exception as e:
        print(f"Warning: {team_name} failed: {e}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    games = []
    
    # Try multiple possible table selectors for game history
    table = soup.find("table", {"id": "team_matches"})
    if not table:
        table = soup.find("table", {"id": "team-matches"})
    if not table:
        table = soup.find("table", {"class": "matches"})
    if not table:
        # Fallback: find any table with match-like content
        tables = soup.find_all("table")
        for t in tables:
            if "match" in t.get_text().lower() or "game" in t.get_text().lower():
                table = t
                break
    
    if not table:
        return []

    for tr in table.find_all("tr")[1:]:  # Skip header row
        tds = tr.find_all("td")
        if len(tds) < 4:
            continue
            
        date = tds[0].get_text(strip=True)
        opp = tds[1].get_text(strip=True)
        score_text = tds[2].get_text(strip=True)
        comp = tds[3].get_text(strip=True) if len(tds) > 3 else "Unknown"

        # Parse score like "2 - 1" or "2:1"
        m = re.match(r"(\d+)\s*[-:]\s*(\d+)", score_text)
        team_score, opp_score = (int(m.group(1)), int(m.group(2))) if m else (None, None)

        games.append({
            "Team": canonicalize_team_name(team_name),
            "Opponent": canonicalize_team_name(opp),
            "TeamRaw": team_name,
            "OpponentRaw": opp,
            "TeamScore": team_score,
            "OpponentScore": opp_score,
            "Competition": comp,
            "Date": date,
            "Division": division,
            "TeamURL": team_url
        })
    return games


# ------------------------------------------------------------------
# MAIN RUNNER
# ------------------------------------------------------------------
def run_division_scrape(division_key: str):
    """Main function to scrape teams and games for a division."""
    print(f"Starting scrape for {division_key}")
    
    # Scrape team list
    teams_df = scrape_team_list(division_key)
    if teams_df.empty:
        print(f"No teams found for {division_key}")
        return pd.DataFrame()
    
    # Scrape game histories
    all_games = []
    total_teams = len(teams_df)
    
    for i, (_, team) in enumerate(teams_df.iterrows(), 1):
        print(f"Scraping games for {team['TeamName']} ({i}/{total_teams})")
        games = scrape_team_games(team)
        if games:
            all_games.extend(games)
        time.sleep(REQUEST_DELAY)  # Be respectful to the server

    # Save games
    games_df = pd.DataFrame(all_games)
    os.makedirs(GOLD_DIR, exist_ok=True)
    
    # Extract age group from division key for filename
    age_group = division_key.split('_')[-1].upper()  # u11 -> U11, u12 -> U12
    out_path = os.path.join(GOLD_DIR, f"Matched_Games_{age_group}.csv")
    
    games_df.to_csv(out_path, index=False)
    print(f"Saved {len(games_df)} games to {out_path}")
    
    # Summary
    print(f"\nSummary for {division_key}:")
    print(f"   Teams: {len(teams_df)}")
    print(f"   Games: {len(games_df)}")
    print(f"   Avg games per team: {len(games_df) / len(teams_df):.1f}")
    
    return games_df


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape GotSport team lists and game histories.")
    parser.add_argument("--division", choices=list(DIVISION_URLS.keys()), required=True,
                        help="Division key (e.g., az_boys_u11, az_boys_u12)")
    parser.add_argument("--mode", choices=["teams", "games"], default="teams",
                        help="Scraping mode: 'teams' for master list (Step 1), 'games' for match histories (Step 2)")
    args = parser.parse_args()
    
    if args.mode == "teams":
        # Step 1: Scrape team list only
        teams_df = scrape_team_list(args.division)
        if not teams_df.empty:
            print(f"✅ Step 1 complete: {len(teams_df)} teams scraped")
    elif args.mode == "games":
        # Step 2: Delegate to dedicated game history scraper
        import subprocess
        import sys
        sys.exit(subprocess.call([
            sys.executable, "scrapers/scrape_team_history.py",
            "--division", args.division
        ]))
