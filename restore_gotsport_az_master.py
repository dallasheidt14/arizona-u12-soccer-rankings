#!/usr/bin/env python3
import pandas as pd
from pathlib import Path
from src.utils.id_codec import make_team_id

# Load the national U11 teams file
df = pd.read_csv('data/master/all_u11_teams_master.csv')

# Filter for Arizona teams
az_teams = df[df['state'] == 'Arizona'].copy()

print(f"Found {len(az_teams)} Arizona teams from GotSport")

# Generate team_ids for Arizona teams
az_teams['team_id'] = az_teams['display_name'].apply(lambda x: make_team_id(x, "az_boys_u11_2025"))

# Create the proper master list structure
master_data = az_teams[['team_id', 'display_name', 'club']].copy()

# Save to the correct location
output_dir = Path("data/master/az_boys_u11_2025")
output_dir.mkdir(parents=True, exist_ok=True)
output_path = output_dir / "master_teams.csv"

master_data.to_csv(output_path, index=False)
print(f"Saved GotSport Arizona master list to {output_path}")

print(f"\nSample GotSport Arizona teams:")
for _, row in master_data.head(10).iterrows():
    print(f"  {row['team_id']}: {row['display_name']}")

print(f"\nTotal teams: {len(master_data)}")
