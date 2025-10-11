#!/usr/bin/env python3
import pandas as pd

# Load the national U11 teams file
df = pd.read_csv('data/master/all_u11_teams_master.csv')

# Filter for Arizona teams
az_teams = df[df['state'] == 'Arizona']

print(f"Arizona teams in national file: {len(az_teams)}")
print("\nSample Arizona teams:")
for _, row in az_teams.head(10).iterrows():
    print(f"  {row['display_name']}")

print(f"\nAll Arizona teams:")
for _, row in az_teams.iterrows():
    print(f"  {row['display_name']}")
