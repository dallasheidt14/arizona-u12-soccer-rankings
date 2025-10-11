"""
utils/validate_gold.py
Purpose: Validate gold layer CSV files for schema compliance and data quality
Usage: python -m utils.validate_gold <gold_csv_path>
"""

import sys
import pandas as pd

REQ = ["Team A", "Team B", "Score A", "Score B", "Date"]

if len(sys.argv) < 2:
    raise SystemExit("Usage: python -m utils.validate_gold <gold_csv_path>")

path = sys.argv[1]

try:
    df = pd.read_csv(path)
except Exception as e:
    raise SystemExit(f"ERROR: Failed to read CSV: {e}")

# Check required columns
missing = [c for c in REQ if c not in df.columns]
if missing:
    raise SystemExit(f"ERROR: Missing columns: {missing}")

# Get unique teams
teams = pd.unique(pd.concat([df["Team A"], df["Team B"]], ignore_index=True))

# Display statistics
print(f"SUCCESS: {len(df)} matches across {len(teams)} teams.")

# Check date coverage
if "Date" in df:
    date_coverage = df["Date"].notna().mean()
    print(f"Dates present in {date_coverage:.1%} of rows")
else:
    print("WARNING: No Date column found")

# Check team game coverage
teams_with_games = set(df["Team A"].unique())
coverage = len(teams_with_games) / max(1, len(teams))
print(f"Teams with >=1 game: {coverage:.1%}")

# Warn if low coverage
if coverage < 0.80:
    print(f"WARNING: Only {coverage:.1%} of teams have games (threshold: 80%)")
    sys.exit(1)

print("SUCCESS: Validation passed!")

