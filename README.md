# Youth Soccer Rankings System

## Overview

This is a comprehensive youth soccer rankings system that generates national and state-level rankings for U10, U11, U12, and other age groups with cross-age game support.

## Key Features

- **Cross-Age Game Support**: Teams can play opponents from adjacent age groups (e.g., U10 vs U11)
- **V5.3E Enhanced Algorithm**: Advanced ranking algorithm with strength of schedule calculations
- **National & State Rankings**: Complete rankings at both national and state levels
- **Scalable Architecture**: Easy to add new age groups and genders
- **Comprehensive Reporting**: Detailed statistics and analysis

## File Structure

```
data/
├── input/                          # Master team lists
│   ├── National_Male_U10_Master_Team_List.csv
│   ├── National_Male_U11_Master_Team_List.csv
│   └── National_Male_U12_Master_Team_List.csv
├── Game History u10 and u11.csv    # Combined game history
└── output/                         # Generated rankings
    ├── National_U10_M_Rankings.csv
    ├── U10_M_Rankings_AZ.csv
    └── U10_M_Rankings_Summary.txt

scripts/
├── generate_rankings.py            # Scalable template for any age group
├── generate_u10_rankings.py       # U10-specific rankings
└── auto_match/                     # Auto-matching scripts
    └── auto_match_team_b.py
```

## Usage

### Generate U10 Rankings
```bash
python scripts/generate_u10_rankings.py
```

### Generate Rankings for Any Age Group
```bash
python scripts/generate_rankings.py --age 11 --gender M
python scripts/generate_rankings.py --age 12 --gender M
python scripts/generate_rankings.py --age 10 --gender F
```

## Cross-Age Game Support

The system handles cross-age games intelligently:

- **U10 teams** can play **U11 opponents**
- **U11 teams** can play **U12 opponents**
- Cross-age games are included in strength of schedule calculations
- Opponents are looked up in the appropriate master team list

## Ranking Algorithm (V5.3E Enhanced)

The ranking algorithm combines multiple factors:

1. **Win Percentage** (20% weight)
2. **Goal Differential** (20% weight)
3. **Strength of Schedule** (60% weight)
4. **Game Count Penalty** (for provisional teams)

## Output Files

For each age group, the system generates:

- **National Rankings**: `National_U{age}_{gender}_Rankings.csv`
- **State Rankings**: `U{age}_{gender}_Rankings_{state}.csv`
- **Summary Report**: `U{age}_{gender}_Rankings_Summary.txt`

## Data Requirements

### Master Team Lists
- Must contain `Team_Name` and `State_Code` columns
- Should include GotSport IDs for accurate matching
- Format: `National_{Gender}_U{Age}_Master_Team_List.csv`

### Game History
- Must contain columns: `Date`, `Team A`, `Team B`, `Score A`, `Score B`, `Team A Result`, `Event`
- Should include age group information
- Format: Combined CSV with all age groups

## Adding New Age Groups

To add a new age group (e.g., U13):

1. Create master team list: `data/input/National_Male_U13_Master_Team_List.csv`
2. Run: `python scripts/generate_rankings.py --age 13 --gender M`
3. The system will automatically handle cross-age games with U12 teams

## Recent Updates

- **Cross-Age Support**: Added support for U10 vs U11 games
- **Scalable Template**: Created `generate_rankings.py` for any age group
- **Clean Architecture**: Removed duplicate files and standardized naming
- **Enhanced Reporting**: Added cross-age game statistics

## Current Status

- ✅ U10 Male Rankings (with cross-age support)
- 🔄 U11 Male Rankings (ready to generate)
- 🔄 U12 Male Rankings (ready to generate)
- 🔄 U10 Female Rankings (ready to generate)

## Next Steps

1. Generate U11 rankings using the scalable template
2. Generate U12 rankings using the scalable template
3. Add female team support
4. Expand to additional age groups (U13, U14, etc.)