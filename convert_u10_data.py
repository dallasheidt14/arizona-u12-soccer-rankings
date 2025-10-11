"""
Convert existing U10 match data to the format expected by the ranking system
"""
import pandas as pd
from utils.team_normalizer import canonicalize_team_name

def convert_u10_data():
    # Read the existing U10 data
    df = pd.read_csv("gold/Matched_Games_U10.csv")
    
    print(f"Converting {len(df)} matches from {len(set(df['Team'].unique()) | set(df['Opponent'].unique()))} teams...")
    
    # Convert to the expected format
    converted_matches = []
    
    for _, row in df.iterrows():
        # Convert to the expected schema
        match = {
            "Team A": canonicalize_team_name(row["Team"]),
            "Team B": canonicalize_team_name(row["Opponent"]),
            "Score A": row["TeamScore"],
            "Score B": row["OpponentScore"],
            "Date": row["Date"],
            "Competition": row["Competition"],
            "SourceURL": row.get("TeamURL", "")
        }
        converted_matches.append(match)
    
    # Save in the expected format
    converted_df = pd.DataFrame(converted_matches)
    output_file = "gold/Matched_Games_AZ_BOYS_U10.csv"
    converted_df.to_csv(output_file, index=False)
    
    print(f"SUCCESS: Converted and saved {len(converted_matches)} matches to {output_file}")
    
    # Show sample of converted data
    print("\nSample converted matches:")
    print(converted_df.head())
    
    # Show team statistics
    all_teams = set(converted_df["Team A"].unique()) | set(converted_df["Team B"].unique())
    print(f"\nTotal unique teams: {len(all_teams)}")
    
    return converted_df

if __name__ == "__main__":
    convert_u10_data()
