"""
Daily Soccer Data Scraper Configuration
Production-ready settings for Arizona U12/U11 Soccer Rankings System
"""

# Division-specific URLs for multi-division support
DIVISION_URLS = {
    "az_boys_u12": "https://rankings.gotsport.com/?team_country=USA&age=12&gender=m&state=AZ",
    "az_boys_u11": "https://rankings.gotsport.com/?team_country=USA&age=11&gender=m&state=AZ",
    "az_boys_u10": "https://rankings.gotsport.com/?team_country=USA&age=10&gender=m&state=AZ",
    "az_boys_u13": "https://rankings.gotsport.com/?team_country=USA&age=13&gender=m&state=AZ",
    "az_boys_u14": "https://rankings.gotsport.com/?team_country=USA&age=14&gender=m&state=AZ",
}

# Legacy SCRAPER_SOURCES for backwards compatibility
SCRAPER_SOURCES = [
    # Each entry is an adapter; add/remove freely.
    # Example stubs (fill with your real URLs):
    {"name": "gotsport_league", "type": "json", "url": "https://system.gotsport.com/api/v1/team_ranking_data?search[team_country]=USA&search[age]=12&search[gender]=m&search[team_association]=AZ"},
    {"name": "league_site_html", "type": "html", "url": "https://rankings.gotsport.com/teams?age=12&gender=m&state=AZ"},
]

POLITENESS = {
    "user_agent": "RightSideUp-U12-SoccerRankBot/1.0 (contact: dallas@rsu.example)",
    "req_per_sec": 1.5,
    "retries": 3,
    "retry_backoff_base_sec": 1.5,
}

MATCHING = {
    "alias_file": "team_aliases.json",
    "fuzzy_threshold_accept": 93,
    "fuzzy_threshold_review_min": 85,
    "review_output": "data_ingest/silver/team_resolution_review.csv",
}

STORAGE = {
    "bronze_dir": "data_ingest/bronze",
    "silver_dir": "data_ingest/silver",
    "gold_dir":   "data_ingest/gold",
    "gold_basename": "All_Games",
    "retention_bronze_days": 180,
    "write_csv_alongside_parquet": True,
}

SCHEDULING = {
    "cron_utc": "30 10 * * *",  # 10:30 UTC = 03:30 Phoenix (no DST)
}

ALERTS = {
    "slack_webhook": None,  # Set to your Slack webhook URL
    "severity_thresholds": {
        "unresolved_max_per_day": 10,
        "error_rate_warn": 0.1,
        "error_rate_crit": 0.2,
    }
}
