#!/usr/bin/env python3
"""
Check the structure of the AZ Master Team List
"""

import pandas as pd

def check_master_list():
    # Load the master team list to see its structure
    master_teams = pd.read_csv('AZ MALE U12 MASTER TEAM LIST.csv')

    print('Columns in AZ MALE U12 MASTER TEAM LIST.csv:')
    for col in master_teams.columns:
        print(f'  - {col}')

    print(f'\nTotal teams: {len(master_teams)}')
    print('\nFirst 5 teams:')
    for i, team in master_teams.head().iterrows():
        col_a = team.iloc[0] if len(team) > 0 else "N/A"
        col_b = team.iloc[1] if len(team) > 1 else "N/A"
        print(f'  {i+1}. Column A: "{col_a}" | Column B: "{col_b}"')

if __name__ == "__main__":
    check_master_list()
