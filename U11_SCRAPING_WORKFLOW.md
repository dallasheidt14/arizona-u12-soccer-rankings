# U11 Team Scraping & Organization Workflow

## Step 1: Scrape Master Team List
**Script**: `scrape_all_u11_final.py`

**What it does:**
- Scrapes ALL teams for U11 from `https://system.gotsport.com/api/v1/team_ranking_data`
- **CRITICAL**: Uses `team.get('team_id')` NOT `team.get('id')` for the matches API
- Gets: `team_name`, `gotsport_team_id` (for matches), `state` (from team_association)
- Saves to timestamped CSV: `all_u11_teams_[timestamp].csv`

**Key Code:**
```python
# CORRECT - Use team_id for matches API
gotsport_team_id = team.get('team_id')  # This works with matches API

# WRONG - This is ranking ID only  
ranking_id = team.get('id')  # This does NOT work with matches API
```

**Saves to**: `data/Master/U11 BOYS/ALL STATES/all_u11_teams_[timestamp].csv`

**Results**: 8,400 U11 teams across 65 states/regions

## Step 2: Organize by State
**Script**: `scripts/organize_u11_teams_by_state.py`

**What it does:**
- Reads the master CSV from `data/Master/U11 BOYS/ALL STATES/`
- Creates folder structure: `data/master/U11 BOYS/[STATE]/`
- Saves each state as: `[STATE]_teams.csv`
- **Note**: CAN and CAS are both California - kept separate as requested

**Refined Structure:**
```
data/master/U11 BOYS/
├── AZ/AZ_teams.csv (186 teams)
├── CAN/CAN_teams.csv (626 teams - California North)
├── CAS/CAS_teams.csv (645 teams - California South)
├── FL/FL_teams.csv (519 teams)
├── NJ/NJ_teams.csv (469 teams)
├── TXS/TXS_teams.csv (454 teams - Texas South)
├── TXN/TXN_teams.csv (334 teams - Texas North)
└── ... (58 more state folders)
```

**Top 10 States by Team Count:**
1. CAS: 645 teams (California South)
2. CAN: 626 teams (California North)
3. FL: 519 teams
4. NJ: 469 teams
5. TXS: 454 teams (Texas South)
6. NYE: 432 teams (New York East)
7. OH: 428 teams
8. IL: 427 teams
9. TXN: 334 teams (Texas North)
10. PAE: 305 teams (Pennsylvania East)

## Step 3: Scrape Game Histories
**Script**: `scripts/scrape_az_u11_game_histories.py`

**Command**: 
```bash
cd "C:\Users\Dallas Heidt\Desktop\Soccer Rankings v2"; python scripts/scrape_az_u11_game_histories.py
```

**What it does:**
- Loads the state-specific team list from `data/master/U11 BOYS/AZ/AZ_teams.csv`
- Uses `team_id` (NOT ranking_id) with `https://system.gotsport.com/api/v1/teams/{team_id}/matches?past=true`
- **CRITICAL**: Includes proper headers for API access
- Captures essential event data:
  - **Event Name**: "Arsenal Challenge 2025", "The Derby 2025"
  - **Competition**: "Arsenal Challenge", "The Derby 2025"
  - **Scores**: `home_score`, `away_score`
  - **Teams**: `home_team_name`, `away_team_name`
  - **Venue**: `venue_name`, `venue_address`
  - **Date**: `match_date_formatted` (e.g., "Saturday, October 11, 2025")

**Key Code:**
```python
# Use the CORRECT team_id from Step 1
url = f"https://system.gotsport.com/api/v1/teams/{team_id}/matches?past=true"

# CRITICAL: Include proper headers
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
    'Origin': 'https://rankings.gotsport.com',
    'Referer': 'https://rankings.gotsport.com/'
}

response = requests.get(url, headers=headers, timeout=30)
data = response.json()

# API returns a list directly, not a dict with 'matches' key
if isinstance(data, list) and data:
    matches = data
    
    for match in matches:
        game_data = {
            'event_name': match.get('event_name', ''),           # "Arsenal Challenge 2025"
            'competition_name': match.get('competition_name', ''), # "Arsenal Challenge"
            'home_score': match.get('home_score'),               # 12
            'away_score': match.get('away_score'),                # 0
            'venue_name': match.get('venue', {}).get('name', '') if isinstance(match.get('venue'), dict) else '', # "Arizona Athletic Grounds"
            'match_date_formatted': match.get('match_date_formatted', {}).get('long', '') if isinstance(match.get('match_date_formatted'), dict) else match.get('match_date_formatted', '')
        }
```

**Saves to**: `data/game_histories/U11 BOYS/AZ/game_histories.csv`

**Test Results**:
- ✅ **API Working**: Returns HTTP 200 with proper headers
- ✅ **Data Format**: Returns list directly (not dict with 'matches' key)
- ✅ **Sample Results**: 239 games from 5 teams (56+50+49+40+44 matches)
- ✅ **Events Found**: 46 unique events, 39 competitions
- ✅ **Top Events**: The Derby 2025, Desert Classic 2025, Phoenix Rising Cup 2025

## Step 4: Extract State-Specific Teams
**For Arizona Rankings**: Use `data/master/U11 BOYS/AZ/AZ_teams.csv` (186 teams)

**Sample AZ Teams:**
- AZ Arsenal Pre-ECNL B15: `163451`
- Chelsea 15B: `334055`
- Phoenix United 2015 Elite: `367030`

## Scalability Notes

**For Other Age Groups:**
1. Update `scrape_all_u11_final.py` → `scrape_all_[age]_final.py`
2. Change API parameter: `"search[age]": "11"` → `"search[age]": "[age]"`
3. Update output paths: `U11 BOYS` → `[AGE] BOYS`
4. Run `organize_[age]_teams_by_state.py` with same logic

**Key Success Factors:**
- ✅ Always use `team.get('team_id')` for matches API compatibility
- ✅ Organize by state for scalable processing
- ✅ Maintain consistent folder structure across age groups
- ✅ Keep CAN/CAS separate (California North/South distinction)

## Next Steps
1. Use AZ teams file for game history scraping
2. Generate U11 rankings using state-specific data
3. Scale to U10, U13, U14 using same pattern
