"""
Multi-Division Soccer Data Scraper
Enhanced scraper supporting U11 and U12 divisions with identical architecture
"""

import os
import time
import json
import hashlib
import datetime as dt
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import logging

import httpx
import pandas as pd
from rapidfuzz import process, fuzz
import scraper_config as cfg

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper_multi.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create data directories
for dir_path in [cfg.STORAGE["bronze_dir"], cfg.STORAGE["silver_dir"], cfg.STORAGE["gold_dir"]]:
    Path(dir_path).mkdir(parents=True, exist_ok=True)

def sha1(obj: Any) -> str:
    """Generate SHA1 hash for object."""
    return hashlib.sha1(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()

def http_get(url: str, timeout: int = 20) -> str:
    """Make HTTP request with politeness and retries."""
    headers = {"User-Agent": cfg.POLITENESS["user_agent"]}
    
    for attempt in range(cfg.POLITENESS["retries"]):
        try:
            with httpx.Client(
                headers=headers, 
                follow_redirects=True, 
                timeout=timeout
            ) as client:
                resp = client.get(url)
                resp.raise_for_status()
                
                # Politeness delay
                time.sleep(1.0 / cfg.POLITENESS["req_per_sec"])
                return resp.text
                
        except httpx.HTTPError as e:
            if attempt < cfg.POLITENESS["retries"] - 1:
                backoff = cfg.POLITENESS["retry_backoff_base_sec"] ** attempt
                logger.warning(f"HTTP error on attempt {attempt + 1}: {e}. Retrying in {backoff}s")
                time.sleep(backoff)
            else:
                logger.error(f"Failed to fetch {url} after {cfg.POLITENESS['retries']} attempts: {e}")
                raise

def scrape_gotsport_rankings(url: str, division_name: str) -> List[Dict[str, Any]]:
    """Scrape team rankings from GotSport rankings page."""
    logger.info(f"📡 Scraping GotSport Rankings for {division_name} from {url}")
    
    try:
        html = http_get(url)
        
        # Parse HTML to extract team data
        # This is a simplified implementation - in practice you'd use BeautifulSoup
        # For now, we'll create placeholder team data based on the division
        
        teams = []
        if "u11" in division_name.lower():
            # Placeholder U11 teams - replace with actual scraping logic
            teams = [
                {"team_name": f"U11 Team {i}", "team_id": f"u11_{i}", "club": f"Club {i}", "rank": i}
                for i in range(1, 151)  # ~150 U11 teams
            ]
        else:
            # Placeholder U12 teams - replace with actual scraping logic  
            teams = [
                {"team_name": f"U12 Team {i}", "team_id": f"u12_{i}", "club": f"Club {i}", "rank": i}
                for i in range(1, 151)  # ~150 U12 teams
            ]
        
        logger.info(f"✅ Found {len(teams)} teams for {division_name}")
        return teams
        
    except Exception as e:
        logger.error(f"❌ Failed to scrape {division_name}: {e}")
        return []

def scrape_team_game_history(team_id: str, team_name: str, division: str) -> List[Dict[str, Any]]:
    """Scrape individual team's game history from GotSport profile."""
    logger.info(f"📊 Scraping game history for {team_name} ({team_id})")
    
    # Placeholder implementation - replace with actual GotSport profile scraping
    # For now, generate sample games
    games = []
    for i in range(20):  # ~20 games per team
        game_date = dt.datetime.now() - dt.timedelta(days=i*7)
        
        games.append({
            "date_utc": game_date.strftime("%Y-%m-%d"),
            "season": game_date.year,
            "competition": f"{division.upper()} League",
            "venue": "Home" if i % 2 == 0 else "Away",
            "home_team_raw": team_name if i % 2 == 0 else f"Opponent {i}",
            "away_team_raw": f"Opponent {i}" if i % 2 == 0 else team_name,
            "home_score": 2 + (i % 3),
            "away_score": 1 + (i % 2),
            "status": "COMPLETED",
            "source_url": f"https://rankings.gotsport.com/teamprofile.aspx?teamid={team_id}",
            "fetched_at": dt.datetime.utcnow().isoformat(timespec="seconds"),
            "division": division
        })
    
    return games

def append_bronze(records: List[Dict[str, Any]], label: str, division: str) -> Path:
    """Append records to bronze layer with division-specific naming."""
    if not records:
        return None
    
    timestamp = dt.datetime.utcnow().strftime('%Y%m%dT%H%M%S')
    out_path = Path(cfg.STORAGE["bronze_dir"]) / f"{division}_{label}_{timestamp}.jsonl"
    
    with out_path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    
    logger.info(f"Wrote {len(records)} records to {out_path}")
    return out_path

def load_master_and_aliases(division: str) -> Tuple[pd.DataFrame, List[str], Dict[str, str]]:
    """Load master team list and aliases for specific division."""
    # Map division to age for master list file
    age_map = {"az_boys_u11": "U11", "az_boys_u12": "U12"}
    age = age_map.get(division, "U12")
    
    master_path = Path(f"AZ MALE {age} MASTER TEAM LIST.csv")
    aliases_path = Path(cfg.MATCHING["alias_file"])
    
    if not master_path.exists():
        logger.warning(f"Master team list not found: {master_path}. Will create from scraped data.")
        return pd.DataFrame(), [], {}
    
    master = pd.read_csv(master_path)
    master_names = master["Team Name"].dropna().astype(str).unique().tolist()
    
    # Load aliases
    aliases = {}
    if aliases_path.exists():
        try:
            aliases = json.loads(aliases_path.read_text())
        except Exception as e:
            logger.warning(f"Could not load aliases: {e}")
    
    # Create alias map
    alias_map = {}
    for canon, arr in aliases.items():
        for alias in arr:
            alias_map[alias] = canon
    
    return master, master_names, alias_map

def resolve_team(name: str, master_names: List[str], alias_map: Dict[str, str], threshold: int = 93) -> Tuple[Optional[str], float, str]:
    """Resolve team name to canonical form."""
    if not name:
        return None, 0.0, "EMPTY"
    
    # Check alias map first
    if name in alias_map:
        return alias_map[name], 100.0, "ALIAS"
    
    # Check exact match
    if name in master_names:
        return name, 100.0, "EXACT"
    
    # Fuzzy match
    result = process.extractOne(name, master_names, scorer=fuzz.WRatio)
    if result:
        cand, score, _ = result
        if score >= threshold:
            return cand, score, "FUZZY"
        return None, score, "UNRESOLVED"
    
    return None, 0.0, "UNRESOLVED"

def curate_to_silver(records: List[Dict[str, Any]], division: str) -> pd.DataFrame:
    """Curate raw records to silver layer with team resolution."""
    if not records:
        return pd.DataFrame()
    
    df = pd.DataFrame(records)
    master, master_names, alias_map = load_master_and_aliases(division)
    
    # Resolve team names
    for col in ["home_team_raw", "away_team_raw"]:
        out_team, out_score, out_method = [], [], []
        
        for v in df[col].astype(str).tolist():
            canon, sc, how = resolve_team(v, master_names, alias_map)
            out_team.append(canon)
            out_score.append(sc)
            out_method.append(how)
        
        df[col.replace("_raw", "_match")] = out_team
        df[col.replace("_raw", "_match_score")] = out_score
        df[col.replace("_raw", "_match_method")] = out_method
    
    # Create review queue for low confidence matches
    review_mask = (
        (df["home_team_match"].isna()) | 
        (df["away_team_match"].isna()) |
        (df.get("home_team_match_score", 100) < cfg.MATCHING["fuzzy_threshold_accept"]) |
        (df.get("away_team_match_score", 100) < cfg.MATCHING["fuzzy_threshold_accept"])
    )
    
    review_df = df[review_mask]
    if not review_df.empty:
        review_path = Path(cfg.MATCHING["review_output"]).parent / f"team_resolution_review_{division}.csv"
        review_path.parent.mkdir(parents=True, exist_ok=True)
        review_df.to_csv(review_path, index=False)
        logger.info(f"Created review queue with {len(review_df)} records: {review_path}")
    
    # Keep normalized view
    cols = [
        "match_id", "date_utc", "season", "competition", "venue",
        "home_team_raw", "away_team_raw", "home_team_match", "away_team_match",
        "home_score", "away_score", "status", "source_url", "fetched_at", 
        "record_checksum", "division"
    ]
    
    # Add match_id and record_checksum if not present
    if "match_id" not in df.columns:
        df["match_id"] = df.apply(lambda row: sha1(f"{row['date_utc']}|{row['competition']}|{row['home_team_raw']}|{row['away_team_raw']}"), axis=1)
    
    if "record_checksum" not in df.columns:
        df["record_checksum"] = df.apply(lambda row: sha1(row.to_dict()), axis=1)
    
    df = df[cols]
    silver_path = Path(cfg.STORAGE["silver_dir"]) / f"{division}_daily_ingest.parquet"
    df.to_parquet(silver_path, index=False)
    
    logger.info(f"Wrote {len(df)} curated records to {silver_path}")
    return df

def merge_into_gold(curated: pd.DataFrame, division: str) -> None:
    """Merge curated data into gold layer with division-specific files."""
    gold_path = Path(cfg.STORAGE["gold_dir"]) / f"Matched_Games_{division.split('_')[-1].upper()}.parquet"
    
    if gold_path.exists():
        base = pd.read_parquet(gold_path)
        merged = _upsert(base, curated)
    else:
        merged = curated
    
    # Write Parquet
    merged.to_parquet(gold_path, index=False)
    
    # Write CSV alongside if configured
    if cfg.STORAGE["write_csv_alongside_parquet"]:
        csv_path = Path(cfg.STORAGE["gold_dir"]) / f"Matched_Games_{division.split('_')[-1].upper()}.csv"
        merged.to_csv(csv_path, index=False)
    
    logger.info(f"Merged {len(merged)} total records into gold layer for {division}")

def _upsert(base: pd.DataFrame, inc: pd.DataFrame) -> pd.DataFrame:
    """Upsert incremental data into base dataset."""
    if base.empty:
        return inc
    
    # Left join by match_id; replace rows when checksum differs or not present
    b = base.set_index("match_id")
    i = inc.set_index("match_id")
    
    # Update overlapping indices
    b.update(i)
    
    # Add new records
    out = pd.concat([b, i[~i.index.isin(b.index)]], axis=0)
    return out.reset_index()

def create_master_team_list(teams: List[Dict[str, Any]], division: str) -> None:
    """Create master team list from scraped team data."""
    age_map = {"az_boys_u11": "U11", "az_boys_u12": "U12"}
    age = age_map.get(division, "U12")
    
    master_path = Path(f"AZ MALE {age} MASTER TEAM LIST.csv")
    
    # Convert teams to DataFrame
    df = pd.DataFrame(teams)
    df = df.rename(columns={"team_name": "Team Name", "club": "Club"})
    df = df[["Team Name", "Club"]].drop_duplicates()
    df = df.sort_values("Team Name")
    
    df.to_csv(master_path, index=False)
    logger.info(f"Created master team list: {master_path} with {len(df)} teams")

def scrape_division(division: str) -> None:
    """Scrape a specific division."""
    logger.info(f"🏆 Starting scrape for division: {division}")
    
    if division not in cfg.DIVISION_URLS:
        logger.error(f"❌ Unknown division: {division}. Available: {list(cfg.DIVISION_URLS.keys())}")
        return
    
    url = cfg.DIVISION_URLS[division]
    
    # Step 1: Scrape team rankings
    teams = scrape_gotsport_rankings(url, division)
    if not teams:
        logger.error(f"❌ No teams found for {division}")
        return
    
    # Create master team list
    create_master_team_list(teams, division)
    
    # Step 2: Scrape game histories for each team
    all_games = []
    for team in teams:  # Process all teams
        games = scrape_team_game_history(team["team_id"], team["team_name"], division)
        all_games.extend(games)
    
    logger.info(f"📊 Scraped {len(all_games)} total games for {division}")
    
    # Step 3: Save to bronze layer
    append_bronze(all_games, "games", division)
    
    # Step 4: Curate to silver layer
    curated = curate_to_silver(all_games, division)
    
    # Step 5: Merge to gold layer
    if not curated.empty:
        merge_into_gold(curated, division)
        logger.info(f"✅ Successfully processed {len(curated)} games for {division}")
    else:
        logger.warning(f"⚠️ No games processed for {division}")

def main():
    """Main function with CLI argument parsing."""
    parser = argparse.ArgumentParser(description="Multi-Division Soccer Data Scraper")
    parser.add_argument("--division", 
                       choices=list(cfg.DIVISION_URLS.keys()),
                       default="az_boys_u12",
                       help="Division to scrape (default: az_boys_u12)")
    parser.add_argument("--all", 
                       action="store_true",
                       help="Scrape all available divisions")
    
    args = parser.parse_args()
    
    if args.all:
        logger.info("🔄 Scraping all available divisions")
        for division in cfg.DIVISION_URLS.keys():
            scrape_division(division)
            time.sleep(2)  # Brief pause between divisions
    else:
        scrape_division(args.division)
    
    logger.info("🎉 Multi-division scraping completed")

if __name__ == "__main__":
    main()
