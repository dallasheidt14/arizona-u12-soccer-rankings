# GotSport Two-Step Scraper Implementation

## Overview

This document describes the production-ready two-step scraping architecture implemented for extracting team and game data from GotSport rankings.

## Architecture

### Step 1: Team List Scraping (Bronze Layer)
**Script**: `scrapers/scraper_multi_division.py --mode teams`

**Purpose**: Extract master team lists from GotSport rankings pages

**Output**: `bronze/{division}_teams.csv`

**Columns**: TeamName, TeamCanonical, Club, Rank, Points, TeamURL, Division, ScrapeDate

### Step 2: Match History Scraping (Gold Layer)
**Script**: `scrapers/scrape_team_history.py`

**Purpose**: Extract individual team match histories from team profile pages

**Output**: `gold/Matched_Games_{DIVISION}.csv`

**Columns**: Team A, Team B, Score A, Score B, Date, Competition, SourceURL

### Step 3: Ranking Generation
**Script**: `rankings/generate_team_rankings_v53_enhanced_multi.py`

**Purpose**: Generate PowerScore rankings using V5.3E algorithm

**Output**: `rankings/Rankings_AZ_M_{age}_2025_v53e.csv`

## Key Features

### Tiered Team Search Strategy
1. **Exact Match**: Direct anchor text comparison
2. **Normalized Match**: Canonicalized name comparison using `utils/team_normalizer.py`
3. **Fuzzy Match**: Token overlap ≥0.6 threshold for partial matches

### Profile URL Caching
- Cache location: `bronze/team_profiles_{division}.json`
- Persistent across runs to avoid redundant searches
- Automatically updates on 404 errors

### Error Handling & Resilience
- **Retry Logic**: 3 attempts with exponential backoff (2s, 4s, 8s)
- **Error Logging**: `logs/scrape_errors_{division}.log`
- **Graceful Degradation**: Continue on individual team failures
- **Threshold Alerts**: Warn if >10% of teams fail

### Rate Limiting
- **Sleep Jitter**: Random 1.5-3.5 seconds between team requests
- **Parallel Execution**: ThreadPoolExecutor with max_workers=6
- **Configurable**: Constants in script header

## Usage

### Complete Pipeline (Automated)
```bash
# Windows
scripts\run_division_pipeline.bat az_boys_u10

# Unix/Mac
bash scripts/run_division_pipeline.sh az_boys_u10
```

### Manual Step-by-Step
```bash
# Step 1: Scrape team list
python scrapers/scraper_multi_division.py --division az_boys_u10 --mode teams

# Step 2: Scrape match histories
python scrapers/scrape_team_history.py --division az_boys_u10

# Step 3: Validate gold output
python -m utils.validate_gold gold/Matched_Games_AZ_BOYS_U10.csv

# Step 4: Generate rankings
python rankings/generate_team_rankings_v53_enhanced_multi.py --division AZ_Boys_U10
```

### Validation Only
```bash
python -m utils.validate_gold gold/Matched_Games_AZ_BOYS_U10.csv
```

## Current Status (October 2025)

### GotSport Data Availability

| Division | GotSport Status | Data Source | Notes |
|----------|----------------|-------------|-------|
| U10 | ❌ No data | Synthetic | Rankings page empty |
| U11 | ❌ No data | Synthetic | Rankings page empty |
| U12 | ❌ No data | Synthetic | Rankings page empty (was working previously) |
| U13 | ❌ No data | Synthetic | Rankings page empty |
| U14 | ❌ No data | Synthetic | Rankings page empty |

**Analysis**: As of October 10, 2025, all GotSport rankings pages return minimal HTML with no ranking tables. This may indicate:
1. Off-season period (no active leagues)
2. Website maintenance or restructuring
3. Temporary technical issues

**Response**: Synthetic data generation scripts were created to populate the pipeline with realistic test data until real GotSport leagues become active.

### Implementation Status

✅ **Completed Components**:
- Two-step scraper architecture (`scrape_team_history.py`)
- Validation utility (`utils/validate_gold.py`)
- Mode flag for unified scraper entry point
- Automated pipeline scripts (`.bat` and `.sh`)
- Profile URL caching mechanism
- Tiered search strategy
- Error logging and retry logic
- Rate limiting and parallel execution

⏳ **Pending Real Data**:
- U10, U11, U13, U14: Waiting for GotSport leagues to start
- U12: Previously working, appears temporarily unavailable

## File Structure

```
scrapers/
  ├── scraper_multi_division.py    # Step 1: Team list scraper
  ├── scrape_team_history.py       # Step 2: Match history scraper
  └── scraper_config.py             # Division URLs configuration

utils/
  ├── validate_gold.py              # Gold layer validation
  └── team_normalizer.py            # Name canonicalization

scripts/
  ├── run_division_pipeline.bat     # Windows automation
  └── run_division_pipeline.sh      # Unix/Mac automation

bronze/
  ├── {division}_teams.csv          # Master team lists
  └── team_profiles_{division}.json # Profile URL cache

gold/
  └── Matched_Games_{DIVISION}.csv  # Match histories

rankings/
  └── Rankings_AZ_M_{age}_2025_v53e.csv  # Final rankings

logs/
  └── scrape_errors_{division}.log  # Error logs
```

## Integration Points

### Team Normalization
Uses existing `utils/team_normalizer.py::canonicalize_team_name()` for consistent name handling across the pipeline.

### Ranking Engine
Outputs match U12 schema exactly:
- Column format: `["Team A", "Team B", "Score A", "Score B", "Date"]`
- Additional columns (Competition, SourceURL) are preserved but ignored by ranking engine
- Deterministic output for reproducibility

### API & Frontend
- API endpoints configured for all divisions
- Frontend dropdown includes U10, U11, U13, U14
- No code changes needed when real data becomes available

## Safety Rails

### U12 Protection
- Never overwrite production U12 paths during testing
- Checksum validation before/after changes
- All new divisions use separate file paths

### Data Quality
- Required column validation
- ≥80% team coverage threshold
- Date presence verification
- Unique team counting

## Future Enhancements

1. **Automated Monitoring**: Add cron job to check GotSport availability
2. **Data Freshness Alerts**: Notify when data becomes stale
3. **Multi-State Support**: Extend to other states beyond Arizona
4. **Historical Archiving**: Store snapshots for trend analysis
5. **Performance Optimization**: Implement async scraping for faster execution

## Troubleshooting

### "No tables found on page"
**Cause**: GotSport rankings page is empty or structure changed

**Solutions**:
1. Check if league is in active season
2. Verify URL is correct in `scrapers/scraper_config.py`
3. Use synthetic data generation as fallback
4. Wait for GotSport to update their site

### "Profile not found via search"
**Cause**: Team search not returning results

**Solutions**:
1. Check team name spelling in bronze CSV
2. Verify team actually exists on GotSport
3. Try manual search on GotSport website
4. Update team aliases in `team_aliases.json`

### "High fail rate" warning
**Cause**: >10% of teams yielded no matches

**Solutions**:
1. Check error log: `logs/scrape_errors_{division}.log`
2. Verify GotSport site is responsive
3. Increase retry attempts or timeout values
4. Reduce parallel workers if rate-limited

## References

- **V5.3E Algorithm**: `docs/V53_ENHANCED_IMPLEMENTATION.md`
- **Multi-Division Guide**: `docs/MULTI_DIVISION_GUIDE.md`
- **API Documentation**: `API_ERROR_SUMMARY.md`
- **Ranking Core**: `enhanced_rank_core.py`

## Changelog

### 2025-10-10
- Initial implementation of two-step scraper architecture
- Added tiered search strategy with caching
- Created validation utilities
- Implemented automated pipeline scripts
- Documented GotSport data availability issues

