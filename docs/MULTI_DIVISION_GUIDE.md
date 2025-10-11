# Multi-Division Soccer Rankings Guide

## Overview

This guide covers the Division Registry System and how to manage multiple soccer divisions (U10-U19 Boys/Girls) in the Arizona Soccer Rankings platform.

## Division Registry System

The Division Registry System (`data/divisions.json`) provides centralized configuration management for all divisions. This enables zero-code-change addition of new divisions and automatic discovery by all components.

### Registry Structure

```json
{
  "az_boys_u11": {
    "age": 11,
    "gender": "m",
    "state": "AZ",
    "url": "https://rankings.gotsport.com/?team_country=USA&age=11&gender=m&state=AZ",
    "active": true
  }
}
```

### Registry Fields

- **age**: Division age (10-19)
- **gender**: "m" for boys, "f" for girls
- **state**: State code (e.g., "AZ")
- **url**: GotSport rankings URL
- **active**: Boolean flag for enabling/disabling divisions

## Adding a New Division

### Step 1: Edit Registry

Add a new entry to `data/divisions.json`:

```json
"az_boys_u15": {
  "age": 15,
  "gender": "m",
  "state": "AZ",
  "url": "https://rankings.gotsport.com/?team_country=USA&age=15&gender=m&state=AZ",
  "active": true
}
```

### Step 2: Create Master Team List

Create the master team list file:
```bash
# File should be named: data/bronze/AZ MALE u15 MASTER TEAM LIST.csv
# Format: Team Name (one per line)
```

### Step 3: Run Pipeline

```bash
# Scrape teams
python src/scrapers/scraper_multi_division.py --division az_boys_u15 --mode teams

# Scrape games
python src/scrapers/scraper_multi_division.py --division az_boys_u15 --mode games

# Generate rankings
python src/rankings/generate_team_rankings_v53_enhanced_multi.py --division az_boys_u15
```

### Step 4: Verify Dashboard

The dashboard will automatically discover the new division and display it in the dropdown.

## Registry Helper Functions

### Core Functions

```python
from src.utils.division_registry import (
    load_divisions,           # Load all divisions
    get_division,             # Get single division config
    list_active_divisions,    # List active divisions only
    get_gotsport_url,         # Get GotSport URL
    get_master_list_path,     # Get master list file path
    get_rankings_output_path, # Get rankings output path
    validate_division_key     # Validate division exists
)
```

### Usage Examples

```python
# Load all divisions
divisions = load_divisions()

# Get active divisions
active = list_active_divisions()
# Returns: ['az_boys_u10', 'az_boys_u11', 'az_boys_u12', 'az_boys_u13', 'az_boys_u14']

# Get division URL
url = get_gotsport_url("az_boys_u11")
# Returns: "https://rankings.gotsport.com/?team_country=USA&age=11&gender=m&state=AZ"

# Get master list path
path = get_master_list_path("az_boys_u11")
# Returns: Path("data/bronze/AZ MALE u11 MASTER TEAM LIST.csv")

# Validate division
is_valid = validate_division_key("az_boys_u11")
# Returns: True
```

## Component Integration

### Scraper Integration

The scraper automatically uses the registry for URL lookup:

```python
# Automatically resolves to registry URL
python src/scrapers/scraper_multi_division.py --division az_boys_u11 --mode teams
```

### Rankings Integration

The rankings script uses the registry for master list paths:

```python
# Automatically finds master list via registry
python src/rankings/generate_team_rankings_v53_enhanced_multi.py --division az_boys_u11
```

### Dashboard Integration

The dashboard auto-discovers active divisions:

```python
# Dashboard automatically loads all active divisions from registry
streamlit run src/dashboard/app_v53_multi_division.py
```

## File Structure

```
data/
├── divisions.json                    # Division registry
├── bronze/                          # Master team lists
│   ├── AZ MALE u10 MASTER TEAM LIST.csv
│   ├── AZ MALE u11 MASTER TEAM LIST.csv
│   └── ...
├── gold/                            # Clean match data
│   ├── Matched_Games_U10.csv
│   ├── Matched_Games_U11.csv
│   └── ...
└── outputs/                         # Final rankings
    ├── Rankings_AZ_M_U10_2025_v53e.csv
    ├── Rankings_AZ_M_U11_2025_v53e.csv
    └── ...
```

## Testing New Divisions

### Unit Tests

```bash
# Test registry functions
python -m pytest tests/test_division_registry.py -v
```

### Integration Tests

```bash
# Test scraper integration
python src/scrapers/scraper_multi_division.py --division az_boys_u11 --mode teams

# Test rankings generation
python src/rankings/generate_team_rankings_v53_enhanced_multi.py --division az_boys_u11

# Test dashboard loading
python -c "from src.dashboard.app_v53_multi_division import DIVISIONS; print(list(DIVISIONS.keys()))"
```

## Troubleshooting

### Common Issues

1. **Division not found in registry**
   - Check `data/divisions.json` exists
   - Verify division key spelling
   - Ensure JSON is valid

2. **Master list not found**
   - Check file exists in `data/bronze/`
   - Verify naming convention: `AZ MALE u{age} MASTER TEAM LIST.csv`
   - Ensure file is readable

3. **Dashboard not showing division**
   - Check `active: true` in registry
   - Verify rankings file exists in `data/outputs/`
   - Check dashboard logs for errors

4. **Scraper URL not found**
   - Verify URL in registry is correct
   - Check GotSport site accessibility
   - Ensure URL format matches GotSport requirements

### Error Messages

- `Division 'xyz' not found in registry`: Division key doesn't exist
- `Division registry not found`: `data/divisions.json` missing
- `Missing required fields`: Registry entry incomplete
- `Master list not found`: Master team list file missing

## Best Practices

1. **Always test new divisions** before marking as active
2. **Use consistent naming** for division keys (`az_boys_u11`)
3. **Keep registry JSON valid** - use JSON validator if needed
4. **Backup registry** before making changes
5. **Document division additions** in commit messages

## Future Enhancements

- **Multi-state support**: Expand beyond Arizona
- **Auto-generate Makefile targets** from registry
- **Division-aware alias management**
- **API integration** with registry
- **Web-based registry editor**

## Support

For issues or questions:
1. Check this guide first
2. Review error messages carefully
3. Test with existing divisions (U11, U12)
4. Check registry JSON validity
5. Verify file paths and permissions