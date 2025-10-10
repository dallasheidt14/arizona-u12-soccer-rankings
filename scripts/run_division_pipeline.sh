#!/usr/bin/env bash
# scripts/run_division_pipeline.sh
# Purpose: Run complete pipeline for a single division (Step 1-4)
# Usage: bash scripts/run_division_pipeline.sh az_boys_u10

set -euo pipefail

if [ $# -eq 0 ]; then
    echo "Usage: bash scripts/run_division_pipeline.sh <division>"
    echo "Example: bash scripts/run_division_pipeline.sh az_boys_u10"
    exit 1
fi

DIV="$1" # e.g., az_boys_u10

echo ""
echo "========================================"
echo "Running Pipeline for: $DIV"
echo "========================================"
echo ""

# Step 1: Scrape team list
echo "[1/4] Scraping team list → bronze/"
python scrapers/scraper_multi_division.py --division "$DIV" --mode teams

# Step 2: Scrape match histories
echo ""
echo "[2/4] Scraping match histories → gold/"
python scrapers/scrape_team_history.py --division "$DIV"

# Extract uppercase division for file paths
DIV_UP="$(echo "$DIV" | tr '[:lower:]' '[:upper:]')"

# Step 3: Validate gold output
echo ""
echo "[3/4] Validating gold layer"
python -m utils.validate_gold "gold/Matched_Games_${DIV_UP}.csv"

# Step 4: Generate rankings
echo ""
echo "[4/4] Generating rankings → rankings/"

# Convert division format: az_boys_u10 → AZ_Boys_U10
IFS='_' read -ra PARTS <<< "$DIV"
STATE="${PARTS[0]}"
GENDER="${PARTS[1]}"
AGE="${PARTS[2]}"

STATE_CAP="$(echo "${STATE:0:1}" | tr '[:lower:]' '[:upper:]')${STATE:1}"
GENDER_CAP="$(echo "${GENDER:0:1}" | tr '[:lower:]' '[:upper:]')${GENDER:1}"
AGE_UP="$(echo "$AGE" | tr '[:lower:]' '[:upper:]')"

DIV_ARG="${STATE_CAP}_${GENDER_CAP}_${AGE_UP}"

python rankings/generate_team_rankings_v53_enhanced_multi.py --division "$DIV_ARG"

echo ""
echo "========================================"
echo "✅ Pipeline complete for $DIV"
echo "========================================"
echo ""
echo "Output files:"
echo "  - bronze/${DIV}_teams.csv"
echo "  - gold/Matched_Games_${DIV_UP}.csv"
echo "  - rankings/Rankings_AZ_M_${AGE}_2025_v53e.csv"
echo ""

