#!/usr/bin/env python3
import pandas as pd

# Load raw games
games = pd.read_csv('data/raw/az_boys_u11_2025/games_raw.csv')
print("Sample team names from raw games:")
for name in games['team_name_a'].head(10):
    print(f"  {name}")

print("\nSample team names from master list:")
master = pd.read_csv('data/master/az_boys_u11_2025/master_teams.csv')
for _, row in master.head(10).iterrows():
    print(f"  {row['display_name']}")

print(f"\nRaw games teams: {games['team_name_a'].nunique()}")
print(f"Master teams: {len(master)}")
