#!/usr/bin/env python3
"""
Add manual aliases for unmatched Arizona teams.

These teams should match the master list but didn't due to formatting differences.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
from pathlib import Path

# Load master list
master = pd.read_csv('data/master/az_boys_u11_2025/master_teams.csv')
unmatched = pd.read_csv('data/logs/az_boys_u11_2025/unmatched.csv')

# Manual mapping for unmatched teams
manual_mappings = {
    "northwest 2015 boys black": "Northwest 2015 Boys Black",
    "15b nmarkette pre-mls next": "15B NMarkette Pre-MLS Next", 
    "15b garza pre mls next": "15B Garza Pre MLS Next",
    "fcda 15b pre - academy": "FCDA 2015B Pre - Academy",
    "sffa 2015 boys blue": "SFFA 2015 Boys Blue",  # This might not exist in master
    "2015 boys blue": "2015 Boys Blue",
    "southeast 2015 boys green": "Southeast 2015 Boys Green",
    "2014 rush boys": "2014 Rush Boys",  # This might not exist in master
    "northwest 2015 boys red": "Northwest 2015 Boys Red",
    "synergy fc 15/16b": "Synergy FC 15/16B Montone",  # Closest match
    "azzurri storm 2015 boys select": "Azzurri Storm 2015 Boys Select",
    "brazas fc 2015 boys black": "BRAZAS FC 2015 Boys Black",
    "15b achacon pre-mls next": "15B AChacon Pre-MLS Next",
    "az inferno 14 boys black": "AZ Inferno 15 Boys Black",  # Closest match
    "2014 boys blue": "2014 Boys Blue"  # This might not exist in master
}

print("Adding manual aliases for unmatched teams...")

# Create alias entries
aliases = []
for raw_name, master_name in manual_mappings.items():
    # Check if master team exists
    master_match = master[master['display_name'] == master_name]
    if not master_match.empty:
        team_id = master_match.iloc[0]['team_id']
        aliases.append({
            'raw_name': raw_name,
            'team_id': team_id,
            'display_name': master_name
        })
        print(f"  {raw_name} -> {master_name} ({team_id})")
    else:
        print(f"  WARNING: {master_name} not found in master list")

# Load existing name map
name_map = pd.read_csv('data/mappings/az_boys_u11_2025/name_map.csv')

# Update the name map with aliases
for alias in aliases:
    # Replace the external ID with the correct team_id
    mask = name_map['raw_name'] == alias['raw_name']
    name_map.loc[mask, 'team_id'] = alias['team_id']
    name_map.loc[mask, 'display_name'] = alias['display_name']

# Save updated name map
name_map.to_csv('data/mappings/az_boys_u11_2025/name_map.csv', index=False)
print(f"\nUpdated name map with {len(aliases)} manual aliases")

# Show final stats
az_teams = name_map[~name_map['team_id'].str.startswith('ext_')]
external_teams = name_map[name_map['team_id'].str.startswith('ext_')]
print(f"Final mapping: {len(az_teams)} AZ teams, {len(external_teams)} external teams")
