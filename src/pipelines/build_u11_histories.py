#!/usr/bin/env python3
"""
Build U11 team histories with team IDs.

This script creates team history data with stable team IDs for U11,
mapping both team and opponent names to IDs using the name mapping.
"""
import pandas as pd
from pathlib import Path
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.name_map_builder import load_name_map


def main():
    """Build U11 team histories."""
    
    # Configuration
    division_key = "az_boys_u11_2025"
    games_file = "data/gold/Matched_Games_U11_CLEAN.csv"
    output_csv = "data/outputs/az_boys_u11_2025/histories.csv"
    output_parquet = "data/outputs/az_boys_u11_2025/histories.parquet"
    
    print(f"Building U11 team histories...")
    print(f"Division key: {division_key}")
    print(f"Games file: {games_file}")
    print(f"Output CSV: {output_csv}")
    print(f"Output Parquet: {output_parquet}")
    
    # Load games data
    if not Path(games_file).exists():
        raise FileNotFoundError(f"Games file not found: {games_file}")
    
    games_df = pd.read_csv(games_file)
    print(f"Loaded {len(games_df)} games from games data")
    
    # Load name mapping
    name_map = load_name_map(division_key)
    print(f"Loaded name mapping with {len(name_map)} entries")
    
    # Create mapping dictionaries
    raw_to_id = name_map.set_index("raw_name")["team_id"].to_dict()
    id_to_display = name_map.set_index("team_id")["display_name"].to_dict()
    
    # Map team names to IDs
    games_df["team_id"] = games_df["Team A"].map(raw_to_id)
    games_df["opponent_team_id"] = games_df["Team B"].map(raw_to_id)
    
    # Check for unmapped teams
    unmapped_team = games_df[games_df["team_id"].isna()]["Team A"].unique()
    unmapped_opp = games_df[games_df["opponent_team_id"].isna()]["Team B"].unique()
    if len(unmapped_team) > 0 or len(unmapped_opp) > 0:
        print(f"WARNING: {len(unmapped_team)} Team A and {len(unmapped_opp)} Team B names not mapped")
        print(f"Sample unmapped Team A: {unmapped_team[:3]}")
        print(f"Sample unmapped Team B: {unmapped_opp[:3]}")
    
    # Filter out unmapped teams
    games_df = games_df.dropna(subset=["team_id", "opponent_team_id"])
    print(f"After filtering unmapped teams: {len(games_df)} games")
    
    # Create history records for both teams
    histories = []
    
    for _, game in games_df.iterrows():
        # Team A perspective
        histories.append({
            "team_id": game["team_id"],
            "opponent_team_id": game["opponent_team_id"],
            "date": game["Date"],
            "goals_for": game["Score A"],
            "goals_against": game["Score B"],
            "result": "W" if game["Score A"] > game["Score B"] else ("L" if game["Score A"] < game["Score B"] else "D"),
            "display_name": id_to_display[game["team_id"]],
            "opponent_display_name": id_to_display[game["opponent_team_id"]]
        })
        
        # Team B perspective
        histories.append({
            "team_id": game["opponent_team_id"],
            "opponent_team_id": game["team_id"],
            "date": game["Date"],
            "goals_for": game["Score B"],
            "goals_against": game["Score A"],
            "result": "W" if game["Score B"] > game["Score A"] else ("L" if game["Score B"] < game["Score A"] else "D"),
            "display_name": id_to_display[game["opponent_team_id"]],
            "opponent_display_name": id_to_display[game["team_id"]]
        })
    
    # Create DataFrame
    histories_df = pd.DataFrame(histories)
    print(f"Created {len(histories_df)} history records")
    
    # Sort by team_id and date
    histories_df = histories_df.sort_values(["team_id", "date"])
    
    # Create output directory
    output_dir = Path(output_csv).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save CSV
    histories_df.to_csv(output_csv, index=False)
    print(f"Saved histories to: {output_csv}")
    
    # Save Parquet
    histories_df.to_parquet(output_parquet, index=False)
    print(f"Saved histories to: {output_parquet}")
    
    # Display sample
    print("\nSample history records:")
    print(histories_df.head(10))
    
    # Statistics
    unique_teams = histories_df["team_id"].nunique()
    total_games = len(histories_df)
    avg_games_per_team = total_games / unique_teams if unique_teams > 0 else 0
    
    print(f"\nStatistics:")
    print(f"  Unique teams: {unique_teams}")
    print(f"  Total history records: {total_games}")
    print(f"  Average games per team: {avg_games_per_team:.1f}")
    
    print(f"\nSuccessfully built U11 team histories")


if __name__ == "__main__":
    main()
