# U11 Boys Soccer Rankings - Complete End-to-End Workflow

## Overview
This document provides a comprehensive guide to the U11 Boys soccer rankings system, covering the complete data pipeline from scraping to frontend display. The system processes U11 boys' teams from Arizona and generates PowerScore-based rankings.

## Current Status
- **Total U11 Teams**: 173 teams in rankings
- **Issue**: 9 U9/U10 teams incorrectly included (need cleanup)
- **API**: Running on http://localhost:8000
- **Frontend**: Integrated and functional

---

## 1. FOLDER STRUCTURE

### Primary Data Directories
```
data/
├── master/U11 BOYS/
│   ├── ALL STATES/
│   │   └── all_u11_teams_with_clubs_[timestamp].csv  # Master scraped file
│   └── AZ/
│       └── AZ_teams.csv                              # Arizona teams (186 teams)
├── game_histories/U11 BOYS/AZ/
│   └── game_histories.csv                            # Raw scraped game data (4,471 games)
├── raw/U11 Boys/AZ/
│   └── games_raw.csv                                 # Canonical game format
├── mappings/U11 Boys/AZ/
│   └── name_map.csv                                  # Team name mappings
├── logs/U11 BOYS/AZ/
│   ├── unmatched.csv                                 # Teams that couldn't be matched
│   └── external_candidates.csv                       # External team IDs
├── outputs/U11 Boys/AZ/
│   └── rankings.csv                                  # Final rankings (173 teams)
└── gold/U11 BOYS/AZ/
    └── Matched_Games_U11_COMPAT.csv                  # Compatibility format for generator
```

### Legacy Directories (Fallback)
```
data/
├── master/az_boys_u11_2025/master_teams.csv          # Legacy master path
├── raw/az_boys_u11_2025/games_raw.csv                # Legacy raw path
├── mappings/az_boys_u11_2025/name_map.csv           # Legacy mappings path
└── outputs/az_boys_u11_2025/rankings.csv             # Legacy output path
```

---

## 2. SCRAPING WORKFLOW

### Step 1: Scrape All U11 Teams
**Script**: `scrape_all_u11_final.py`
**Command**: `python scrape_all_u11_final.py`

**What it does**:
- Scrapes ALL U11 boys teams from GotSport API
- Uses endpoint: `https://system.gotsport.com/api/v1/team_ranking_data`
- Parameters: `search[age]=11`, `search[gender]=m`
- **CRITICAL**: Uses `team.get('team_id')` for matches API (not `team.get('id')`)
- Captures: `team_name`, `club_name`, `gotsport_team_id`, `state`

**Output**: `data/master/U11 BOYS/ALL STATES/all_u11_teams_[timestamp].csv`
- **Total teams**: ~8,400 U11 teams across all states
- **Arizona teams**: 186 teams

### Step 2: Organize by State
**Script**: `organize_u11_teams_by_state.py`
**Command**: `python organize_u11_teams_by_state.py`

**What it does**:
- Reads master CSV from `data/master/U11 BOYS/ALL STATES/`
- Groups teams by `state` column
- Handles California consolidation: 'CAN' + 'CAS' → 'CA'
- Creates state folders under `data/master/U11 BOYS/`
- Saves each state as `[STATE]_teams.csv`

**Output**: `data/master/U11 BOYS/AZ/AZ_teams.csv`
- **Arizona teams**: 186 teams

### Step 3: Scrape Game Histories
**Script**: `scrape_az_u11_game_histories.py`
**Command**: `python scrape_az_u11_game_histories.py`

**What it does**:
- Loads Arizona teams from `data/master/U11 BOYS/AZ/AZ_teams.csv`
- Uses `team_id` with matches API: `https://system.gotsport.com/api/v1/teams/{team_id}/matches?past=true`
- **CRITICAL**: Includes proper headers for API access
- Handles API response as direct list (not dict with 'matches' key)
- Extracts opponent names from `title` field when needed

**Output**: `data/game_histories/U11 BOYS/AZ/game_histories.csv`
- **Total games**: 4,471 games from 186 AZ U11 teams
- **Unique events**: 89
- **Unique competitions**: 70

---

## 3. DATA PROCESSING PIPELINE

### Step 4: Materialize Raw Games
**Script**: `scripts/u11_materialize_raw_games.py`
**Command**: `python scripts/u11_materialize_raw_games.py`

**What it does**:
- Transforms team-centric data to game-centric format
- Maps `home_team_name`/`away_team_name` → `Team A`/`Team B`
- Handles scores: `home_score`/`away_score` → `Score A`/`Score B`
- Removes duplicate games
- Sorts teams alphabetically for consistency

**Output**: `data/raw/U11 Boys/AZ/games_raw.csv`
- **Format**: `Team A`, `Team B`, `Score A`, `Score B`, `Date`, `Competition`, `Event`

### Step 5: Team Matching
**Script**: `src/pipelines/u11_team_matcher.py`
**Command**: `python -m src.pipelines.u11_team_matcher`

**What it does**:
- **Name Mapping**: Exact → fuzzy (90%) → external ID generation
- **Histories**: Creates bidirectional game records with team IDs
- **Compatibility**: Generates COMPAT file for existing generator
- Handles unmatched teams as "EXTERNAL" (doesn't fail)

**Outputs**:
- `data/mappings/U11 Boys/AZ/name_map.csv` - Team name mappings
- `data/outputs/U11 Boys/AZ/histories.csv` - ID-based game histories
- `data/gold/U11 BOYS/AZ/Matched_Games_U11_COMPAT.csv` - Compatibility format

---

## 4. RANKING GENERATION

### Step 6: Generate Rankings
**Script**: `src/rankings/generate_team_rankings_v53_enhanced_multi.py`
**Command**: `python -m src.rankings.generate_team_rankings_v53_enhanced_multi --input data/gold/U11\ BOYS/AZ/Matched_Games_U11_COMPAT.csv --division AZ_Boys_U11`

**What it does**:
- Uses PowerScore algorithm with Strength of Schedule (SOS)
- Applies temporal weighting (recent games weighted more)
- Filters to master teams only
- Handles external team IDs properly
- Generates comprehensive rankings with multiple metrics

**Output**: `data/outputs/U11 Boys/AZ/rankings.csv`
- **Total teams**: 173 teams
- **Issue**: Contains 9 U9/U10 teams (data quality issue)

---

## 5. API AND FRONTEND INTEGRATION

### API Server
**File**: `app.py`
**Endpoints**:
- `GET /api/v1/az/m/u11/rankings` - Returns rankings with team IDs
- `GET /api/v1/az/m/u11/teams/{team_id}/history` - Returns team game history

**Current Configuration**:
```python
# U11 Rankings endpoint
rankings_path = Path("data/outputs/U11 Boys/AZ/rankings.csv")

# U11 History endpoint  
histories_path = Path("data/game_histories/U11 BOYS/AZ/game_histories.csv")
```

### Frontend Integration
**Files**:
- `src/YouthRankingsApp.jsx` - Main React app
- `src/RankingsPage.jsx` - Rankings table display
- `src/TeamHistoryPage.jsx` - Team history display

**Features**:
- Dynamic rankings table with sorting
- Team history with opponent names
- PowerScore and SOS display
- Responsive design

---

## 6. KEY SCRIPTS AND THEIR PURPOSES

### Scraping Scripts
| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `scrape_all_u11_final.py` | Scrape all U11 teams | GotSport API | `data/master/U11 BOYS/ALL STATES/` |
| `organize_u11_teams_by_state.py` | Organize by state | Master CSV | `data/master/U11 BOYS/[STATE]/` |
| `scrape_az_u11_game_histories.py` | Scrape AZ game histories | AZ teams | `data/game_histories/U11 BOYS/AZ/` |

### Processing Scripts
| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `scripts/u11_materialize_raw_games.py` | Transform to game format | Game histories | `data/raw/U11 Boys/AZ/` |
| `src/pipelines/u11_team_matcher.py` | Match teams and build histories | Raw games + master | Mappings + histories + compat |

### Utility Scripts
| Script | Purpose |
|--------|---------|
| `src/utils/paths_u11.py` | Centralized path management |
| `scripts/validate_u11_paths.py` | Validate pipeline outputs |
| `scripts/deduplicate_u11_master.py` | Remove duplicate teams |

---

## 7. DATA QUALITY ISSUES

### Current Issues
1. **U9/U10 Teams in U11 Rankings**: 9 teams incorrectly included
   - Root cause: Master file contains non-U11 teams
   - Solution: Clean master file and regenerate rankings

2. **Team Name Inconsistencies**: Some teams have "nan" names
   - Root cause: Missing data in scraping
   - Solution: Improved normalization in frontend

### Data Validation
- **Master file**: 186 teams (should be ~78 U11 teams)
- **Game histories**: 4,471 games (good coverage)
- **Rankings**: 173 teams (includes incorrect U9/U10 teams)

---

## 8. COMPLETE WORKFLOW COMMANDS

### Full Pipeline Execution
```bash
# 1. Scrape all U11 teams
python scrape_all_u11_final.py

# 2. Organize by state
python organize_u11_teams_by_state.py

# 3. Scrape AZ game histories
python scrape_az_u11_game_histories.py

# 4. Materialize raw games
python scripts/u11_materialize_raw_games.py

# 5. Run team matcher
python -m src.pipelines.u11_team_matcher

# 6. Generate rankings
python -m src.rankings.generate_team_rankings_v53_enhanced_multi --input data/gold/U11\ BOYS/AZ/Matched_Games_U11_COMPAT.csv --division AZ_Boys_U11

# 7. Start API server
python app.py
```

### Validation Commands
```bash
# Validate pipeline outputs
python scripts/validate_u11_paths.py

# Test API endpoints
python test_u11_api.py

# Check for U9/U10 teams
python -c "import pandas as pd; df = pd.read_csv('data/outputs/U11 Boys/AZ/rankings.csv'); print(len(df[df['Team'].str.contains('U9|U10', na=False)]))"
```

---

## 9. TECHNICAL SPECIFICATIONS

### API Endpoints
- **Base URL**: `http://localhost:8000`
- **Rankings**: `GET /api/v1/az/m/u11/rankings`
- **History**: `GET /api/v1/az/m/u11/teams/{team_id}/history`

### Data Formats
- **Master Teams**: `team_name`, `gotsport_team_id`, `state`
- **Game Histories**: `team_id`, `opponent_name`, `home_score`, `away_score`, `match_date`
- **Rankings**: `Team`, `team_id`, `PowerScore`, `SOS_norm`, `Rank`

### Key Technologies
- **Backend**: FastAPI (Python)
- **Frontend**: React with Tailwind CSS
- **Data Processing**: Pandas
- **Matching**: FuzzyWuzzy (90% threshold)
- **API Integration**: Requests library

---

## 10. NEXT STEPS

### Immediate Actions Needed
1. **Clean Master File**: Remove U9/U10 teams from `data/master/U11 BOYS/AZ/AZ_teams.csv`
2. **Regenerate Rankings**: Run pipeline with cleaned master file
3. **Validate Results**: Ensure only U11 teams in final rankings

### Future Enhancements
1. **Multi-State Support**: Extend to other states beyond Arizona
2. **Age Group Validation**: Add age group filtering in scraping
3. **Data Quality Monitoring**: Automated validation of team ages
4. **Performance Optimization**: Caching and database integration

---

## 11. TROUBLESHOOTING

### Common Issues
1. **API 404 Errors**: Check file paths in `app.py`
2. **Missing Teams**: Verify master file contains correct teams
3. **Duplicate Teams**: Run deduplication script
4. **U9/U10 Teams**: Clean master file and regenerate

### Debug Commands
```bash
# Check file existence
ls -la "data/outputs/U11 Boys/AZ/rankings.csv"

# Validate data quality
python -c "import pandas as pd; df = pd.read_csv('data/outputs/U11 Boys/AZ/rankings.csv'); print(f'Total: {len(df)}, U9/U10: {len(df[df[\"Team\"].str.contains(\"U9|U10\", na=False)])}')"

# Test API response
curl http://localhost:8000/api/v1/az/m/u11/rankings
```

---

This comprehensive workflow document covers the complete U11 boys soccer rankings system from data scraping to frontend display, including all file locations, scripts, and technical specifications.
