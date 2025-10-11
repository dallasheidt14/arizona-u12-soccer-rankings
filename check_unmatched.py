#!/usr/bin/env python3
import pandas as pd

master = pd.read_csv('data/master/az_boys_u11_2025/master_teams.csv')
unmatched = pd.read_csv('data/logs/az_boys_u11_2025/unmatched.csv')

print("Master teams with similar names:")
for _, row in master.iterrows():
    name = row['display_name'].lower()
    if any(term in name for term in ['northwest', 'garza', 'nmarkette', 'brazas', 'azzurri']):
        print(f"  {row['display_name']}")

print("\nUnmatched teams:")
for _, row in unmatched.iterrows():
    print(f"  {row['raw_name']}")
