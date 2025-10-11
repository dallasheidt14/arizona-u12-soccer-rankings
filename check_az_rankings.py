#!/usr/bin/env python3
import pandas as pd

rankings = pd.read_csv('data/outputs/az_boys_u11_2025/rankings.csv')
az_teams = rankings[~rankings['team_id'].str.startswith('ext_')]

print('Arizona teams in rankings:')
for _, row in az_teams.iterrows():
    print(f'  {row["rank"]}. {row["display_name"]} - {row["power_score"]:.3f} ({row["games_played"]} games)')

print(f'\nTotal Arizona teams: {len(az_teams)}')
print(f'Total teams: {len(rankings)}')
