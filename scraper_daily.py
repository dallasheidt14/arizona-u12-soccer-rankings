"""
Daily Soccer Data Scraper
Production-ready scraper for Arizona U12 Soccer Rankings System
"""

import os
import time
import json
import hashlib
import datetime as dt
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
        logging.FileHandler('scraper.log'),
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

def parse_score(text: str) -> Tuple[Optional[int], Optional[int]]:
    """Parse score text into home/away scores."""
    if not text:
        return None, None
    
    text = text.strip()
    if "-" in text:
        try:
            h, a = text.split("-", 1)
            return int(h.strip()), int(a.strip())
        except ValueError:
            return None, None
    return None, None

def infer_season(date_utc: Optional[dt.date]) -> Optional[int]:
    """Infer season year from date."""
    if not date_utc:
        return None
    return date_utc.year

def extract_games_from_gotsport_json(json_data: Dict[str, Any], source_url: str) -> List[Dict[str, Any]]:
    """Extract games from GotSport JSON API response."""
    games = []
    
    try:
        # GotSport API structure (adjust based on actual response)
        teams_data = json_data.get("team_ranking_data", [])
        
        for team in teams_data:
            # Extract team info
            team_name = team.get("team_name", "")
            team_id = team.get("id", "")
            
            # For now, we'll create placeholder games since GotSport API
            # doesn't directly provide game results in this endpoint
            # This would need to be adapted based on actual GotSport game data API
            
            raw = {
                "date_utc": None,  # Would need actual game date
                "season": None,
                "competition": "GotSport League",
                "venue": None,
                "home_team_raw": team_name,
                "away_team_raw": None,  # Would need opponent
                "home_score": None,
                "away_score": None,
                "status": "SCHEDULED",
                "source_url": source_url,
                "fetched_at": dt.datetime.utcnow().isoformat(timespec="seconds"),
            }
            
            # Generate match ID
            nk = f"{raw['date_utc']}|{raw['competition']}|{team_name}|{raw['away_team_raw']}"
            raw["match_id"] = sha1(nk)
            raw["record_checksum"] = sha1(raw)
            
            games.append(raw)
            
    except Exception as e:
        logger.error(f"Error parsing GotSport JSON: {e}")
    
    return games

def extract_games_from_html(html: str, source_url: str) -> List[Dict[str, Any]]:
    """Extract games from HTML page (placeholder - needs actual selectors)."""
    games = []
    
    # This is a placeholder implementation
    # In practice, you'd use selectolax or BeautifulSoup with actual selectors
    logger.info(f"HTML parsing not yet implemented for {source_url}")
    
    return games

def append_bronze(records: List[Dict[str, Any]], label: str) -> Path:
    """Append records to bronze layer."""
    if not records:
        return None
    
    timestamp = dt.datetime.utcnow().strftime('%Y%m%dT%H%M%S')
    out_path = Path(cfg.STORAGE["bronze_dir"]) / f"{label}_{timestamp}.jsonl"
    
    with out_path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    
    logger.info(f"Wrote {len(records)} records to {out_path}")
    return out_path

def load_master_and_aliases() -> Tuple[pd.DataFrame, List[str], Dict[str, str]]:
    """Load master team list and aliases."""
    master_path = Path("AZ MALE U12 MASTER TEAM LIST.csv")
    aliases_path = Path(cfg.MATCHING["alias_file"])
    
    if not master_path.exists():
        logger.error(f"Master team list not found: {master_path}")
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

def curate_to_silver(records: List[Dict[str, Any]]) -> pd.DataFrame:
    """Curate raw records to silver layer with team resolution."""
    if not records:
        return pd.DataFrame()
    
    df = pd.DataFrame(records)
    master, master_names, alias_map = load_master_and_aliases()
    
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
        review_path = Path(cfg.MATCHING["review_output"])
        review_path.parent.mkdir(parents=True, exist_ok=True)
        review_df.to_csv(review_path, index=False)
        logger.info(f"Created review queue with {len(review_df)} records: {review_path}")
    
    # Keep normalized view
    cols = [
        "match_id", "date_utc", "season", "competition", "venue",
        "home_team_raw", "away_team_raw", "home_team_match", "away_team_match",
        "home_score", "away_score", "status", "source_url", "fetched_at", "record_checksum"
    ]
    
    df = df[cols]
    silver_path = Path(cfg.STORAGE["silver_dir"]) / "daily_ingest.parquet"
    df.to_parquet(silver_path, index=False)
    
    logger.info(f"Wrote {len(df)} curated records to {silver_path}")
    return df

def merge_into_gold(curated: pd.DataFrame) -> None:
    """Merge curated data into gold layer."""
    gold_path = Path(cfg.STORAGE["gold_dir"]) / f"{cfg.STORAGE['gold_basename']}.parquet"
    
    if gold_path.exists():
        base = pd.read_parquet(gold_path)
        merged = _upsert(base, curated)
    else:
        merged = curated
    
    # Write Parquet
    merged.to_parquet(gold_path, index=False)
    
    # Write CSV alongside if configured
    if cfg.STORAGE["write_csv_alongside_parquet"]:
        csv_path = Path(cfg.STORAGE["gold_dir"]) / f"{cfg.STORAGE['gold_basename']}.csv"
        merged.to_csv(csv_path, index=False)
    
    logger.info(f"Merged {len(merged)} total records into gold layer")

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

def send_alert(message: str, severity: str = "info") -> None:
    """Send alert via Slack webhook."""
    if not cfg.ALERTS["slack_webhook"]:
        logger.info(f"Alert ({severity}): {message}")
        return
    
    # Implement Slack webhook sending here
    logger.info(f"Would send Slack alert ({severity}): {message}")

def cleanup_old_bronze() -> None:
    """Clean up old bronze files based on retention policy."""
    bronze_dir = Path(cfg.STORAGE["bronze_dir"])
    cutoff_date = dt.datetime.utcnow() - dt.timedelta(days=cfg.STORAGE["retention_bronze_days"])
    
    removed_count = 0
    for file_path in bronze_dir.glob("*.jsonl"):
        if file_path.stat().st_mtime < cutoff_date.timestamp():
            file_path.unlink()
            removed_count += 1
    
    if removed_count > 0:
        logger.info(f"Cleaned up {removed_count} old bronze files")

def daily_run() -> None:
    """Main daily scraping routine."""
    logger.info("Starting daily soccer data scrape")
    
    all_new = []
    error_count = 0
    total_sources = len(cfg.SCRAPER_SOURCES)
    
    for source in cfg.SCRAPER_SOURCES:
        try:
            logger.info(f"Scraping {source['name']} from {source['url']}")
            
            if source["type"] == "json":
                html = http_get(source["url"])
                json_data = json.loads(html)
                games = extract_games_from_gotsport_json(json_data, source["url"])
            elif source["type"] == "html":
                html = http_get(source["url"])
                games = extract_games_from_html(html, source["url"])
            else:
                logger.warning(f"Unknown source type: {source['type']}")
                continue
            
            if games:
                append_bronze(games, source["name"])
                all_new.extend(games)
                logger.info(f"Extracted {len(games)} games from {source['name']}")
            
        except Exception as e:
            error_count += 1
            logger.error(f"Failed to scrape {source['name']}: {e}")
            continue
    
    # Calculate error rate
    error_rate = error_count / total_sources if total_sources > 0 else 0
    
    # Curate and merge
    curated = curate_to_silver(all_new)
    if not curated.empty:
        merge_into_gold(curated)
        logger.info(f"Successfully processed {len(curated)} new records")
    else:
        logger.info("No new records to process")
    
    # Cleanup old files
    cleanup_old_bronze()
    
    # Send summary alert
    unresolved_count = len(curated[curated["home_team_match"].isna() | curated["away_team_match"].isna()]) if not curated.empty else 0
    
    summary = f"Daily scrape complete: {len(all_new)} new games, {unresolved_count} unresolved teams, {error_count}/{total_sources} source errors"
    
    if error_rate >= cfg.ALERTS["severity_thresholds"]["error_rate_crit"]:
        send_alert(f"CRITICAL: {summary}", "critical")
    elif error_rate >= cfg.ALERTS["severity_thresholds"]["error_rate_warn"]:
        send_alert(f"WARNING: {summary}", "warning")
    elif unresolved_count > cfg.ALERTS["severity_thresholds"]["unresolved_max_per_day"]:
        send_alert(f"REVIEW NEEDED: {summary}", "warning")
    else:
        send_alert(summary, "info")
    
    logger.info("Daily scrape completed successfully")

if __name__ == "__main__":
    daily_run()
