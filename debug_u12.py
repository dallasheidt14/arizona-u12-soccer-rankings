import pandas as pd
from src.utils.team_aliases import resolve_team_name

# Load U12 data
games = pd.read_csv('data/gold/Matched_Games_AZ_BOYS_U12.csv')
master = pd.read_csv('data/bronze/AZ MALE u12 MASTER TEAM LIST.csv')

print('Sample U12 games teams:')
for t in games['Team A'].unique()[:5]:
    canonical = resolve_team_name(t)
    print(f'  "{t}" -> "{canonical}"')

print('\nSample U12 master teams:')
for t in master['Team Name'].unique()[:5]:
    canonical = resolve_team_name(t)
    print(f'  "{t}" -> "{canonical}"')

# Check for matches
games_canonical = set(resolve_team_name(t) for t in games['Team A'].unique())
master_canonical = set(resolve_team_name(t) for t in master['Team Name'].unique())

matches = games_canonical.intersection(master_canonical)
print(f'\nMatches found: {len(matches)}')
print(f'Games teams: {len(games_canonical)}')
print(f'Master teams: {len(master_canonical)}')

if len(matches) < 10:
    print('\nFirst few matches:')
    for m in list(matches)[:5]:
        print(f'  {m}')

