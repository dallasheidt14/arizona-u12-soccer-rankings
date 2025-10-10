# Multi-Division Support Guide

## Overview

The Soccer Rankings system now supports multiple age divisions (U11, U12, etc.) with identical architecture and ranking logic. This guide explains how to add new divisions and use the multi-division features.

## Architecture

The system follows a consistent pipeline for all divisions:

```
Scraper → Bronze Layer → Silver Layer → Gold Layer → Rankings → API → Frontend
```

Each division maintains separate data files while sharing the same processing logic.

## Division Configuration

### 1. Scraper Configuration (`scraper_config.py`)

Add new divisions to the `DIVISION_URLS` dictionary:

```python
DIVISION_URLS = {
    "az_boys_u12": "https://rankings.gotsport.com/?team_country=USA&age=12&gender=m&state=AZ",
    "az_boys_u11": "https://rankings.gotsport.com/?team_country=USA&age=11&gender=m&state=AZ",
    # Add new divisions here
    "az_boys_u10": "https://rankings.gotsport.com/?team_country=USA&age=10&gender=m&state=AZ",
}
```

### 2. File Naming Conventions

The system uses consistent naming patterns:

- **Master Team Lists**: `AZ MALE {AGE} MASTER TEAM LIST.csv`
- **Rankings**: `Rankings_AZ_M_{AGE}_2025_v53e.csv`
- **Game Data**: `Matched_Games_{AGE}.csv`
- **Connectivity Reports**: `connectivity_report_{age}_v53e.csv`

Where `{AGE}` is U11, U12, U13, etc.

## Adding a New Division

### Step 1: Configure Scraper

1. Add the division URL to `scraper_config.py`
2. Update the scraper to handle the new division

### Step 2: Run Data Pipeline

```bash
# Scrape the new division
python scraper_multi_division.py --division az_boys_u10

# Generate rankings
python rankings/generate_team_rankings_v53_enhanced_multi.py --division AZ_Boys_U10
```

### Step 3: Update Frontend

Add the new division to `src/SelectorHero.jsx`:

```jsx
<option value="az_boys_u10" style={{ color: '#1e293b' }}>Arizona Boys U10 (2016)</option>
```

### Step 4: Update Dashboard

Add the new division to `dashboard/app_v53_multi_division.py`:

```python
DIVISIONS = {
    # ... existing divisions
    "az_boys_u10": {
        "label": "Arizona Boys U10 (2016)",
        "rankings_file": "Rankings_AZ_M_U10_2025_v53e.csv",
        "fallback_files": ["Rankings_AZ_M_U10_2025.csv"],
        "predictions_file": "Predicted_Outcomes_U10_v52b.csv"
    }
}
```

## API Usage

### Division-Specific Endpoints

```bash
# U12 rankings
GET /api/rankings?division=az_boys_u12

# U11 rankings  
GET /api/rankings?division=az_boys_u11

# U10 rankings (when added)
GET /api/rankings?division=az_boys_u10
```

### Response Format

All division endpoints return the same JSON structure:

```json
{
  "meta": {
    "division": "az_boys_u11",
    "total_teams": 150,
    "active_teams": 145,
    "provisional_teams": 5
  },
  "data": [
    {
      "Rank": 1,
      "Team": "Team Name",
      "PowerScore": 0.832,
      "SAO_norm": 0.721,
      "SAD_norm": 0.689,
      "SOS_norm": 0.756,
      "GamesPlayed": 25,
      "Status": "Active"
    }
  ],
  "active": [...],
  "provisional": [...]
}
```

## Frontend Integration

### Division Selector

The React frontend includes a division dropdown in the selector page:

```jsx
<select value={division} onChange={(e) => setDivision(e.target.value)}>
  <option value="az_boys_u12">Arizona Boys U12 (2014)</option>
  <option value="az_boys_u11">Arizona Boys U11 (2015)</option>
</select>
```

### Dynamic Data Fetching

The frontend automatically fetches data based on the selected division:

```jsx
const url = `/api/rankings?division=${division}&state=${state}&gender=${gender}&year=${year}`;
```

## Dashboard Usage

### Multi-Division Dashboard

Run the multi-division dashboard:

```bash
streamlit run dashboard/app_v53_multi_division.py
```

The dashboard includes:
- Division selector in the sidebar
- Division-specific rankings tables
- Match prediction tools
- Model performance metrics

## Automation

### Nightly Pipeline

Add new divisions to your automation scripts:

```bash
# Scrape all divisions
python scraper_multi_division.py --all

# Generate rankings for all divisions
python rankings/generate_team_rankings_v53_enhanced_multi.py --division AZ_Boys_U12
python rankings/generate_team_rankings_v53_enhanced_multi.py --division AZ_Boys_U11
```

### Batch Scripts

Use the provided batch scripts:

- `run_u11_pipeline.bat` - Complete U11 pipeline
- `start_system_multi.bat` - Start system with multi-division support

## Validation Checklist

When adding a new division, verify:

- [ ] Division URL added to `scraper_config.py`
- [ ] Scraper successfully extracts team data
- [ ] Master team list generated
- [ ] Rankings file created with expected team count
- [ ] API endpoint returns data: `/api/rankings?division=az_boys_{age}`
- [ ] Frontend dropdown includes new division
- [ ] Dashboard supports new division
- [ ] SOS coverage >90%, match rate >95%

## Troubleshooting

### Common Issues

1. **No rankings file found**
   - Ensure the scraper ran successfully
   - Check file naming conventions
   - Verify master team list exists

2. **API returns 404**
   - Check division parameter spelling
   - Verify rankings file exists
   - Check API file discovery logic

3. **Frontend shows no data**
   - Verify API endpoint works
   - Check browser console for errors
   - Ensure division parameter is passed correctly

### File Locations

- **Scraper Config**: `scraper_config.py`
- **Multi-Division Scraper**: `scraper_multi_division.py`
- **Multi-Division Rankings**: `rankings/generate_team_rankings_v53_enhanced_multi.py`
- **API**: `app.py`
- **Frontend**: `src/YouthRankingsApp.jsx`, `src/SelectorHero.jsx`
- **Dashboard**: `dashboard/app_v53_multi_division.py`

## Future Enhancements

- Support for girls divisions
- Cross-division game analysis
- Division comparison tools
- Automated division discovery
- Multi-state support per division
