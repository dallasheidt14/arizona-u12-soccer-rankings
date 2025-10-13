#!/usr/bin/env python3
"""Analyze U11 rankings to understand team count"""

import pandas as pd

# Load rankings
rankings = pd.read_csv('data/outputs/az_boys_u11_2025/rankings.csv')

print(f"Total teams in rankings: {len(rankings)}")

# Check team_id patterns
real_teams = rankings[rankings["team_id"].str.startswith("42", na=False)]
external_teams = rankings[~rankings["team_id"].str.startswith("42", na=False)]

print(f"Real GotSport teams (ID starts with 42): {len(real_teams)}")
print(f"External/generated teams: {len(external_teams)}")

print("\nSample external team IDs:")
print(external_teams["team_id"].head(10).tolist())

print("\nSample external team names:")
print(external_teams["Team"].head(10).tolist())

# Check the name mapping
print("\n" + "="*50)
print("NAME MAPPING ANALYSIS")
print("="*50)

mapping = pd.read_csv('data/mappings/az_boys_u11_2025/name_map.csv')
print(f"Total teams in mapping: {len(mapping)}")

exact_matches = mapping[mapping["match_type"] == "EXACT"]
fuzzy_matches = mapping[mapping["match_type"] == "FUZZY"] 
external_matches = mapping[mapping["match_type"] == "EXTERNAL"]

print(f"Exact matches: {len(exact_matches)}")
print(f"Fuzzy matches: {len(fuzzy_matches)}")
print(f"External matches: {len(external_matches)}")

print("\nSample external team names from mapping:")
print(external_matches["raw_name"].head(10).tolist())
