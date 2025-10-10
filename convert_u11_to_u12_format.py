"""
Convert U11 Games to U12 Format
Converts U11 games data to match U12 expected format for ranking algorithm
"""

import pandas as pd

def convert_u11_to_u12_format():
    """Convert U11 games to U12 format"""
    
    # Read U11 games
    u11_path = "gold/Matched_Games_U11.csv"
    df_u11 = pd.read_csv(u11_path)
    
    print(f"U11 games shape: {df_u11.shape}")
    print(f"U11 columns: {df_u11.columns.tolist()}")
    
    # Convert to U12 format
    converted_games = []
    
    for _, row in df_u11.iterrows():
        # Create game entry in U12 format
        game = {
            'Date': row['Date'],
            'Team A': row['TeamRaw'],  # Use raw team names
            'Team B': row['OpponentRaw'],  # Use raw opponent names
            'Score A': row['TeamScore'] if pd.notna(row['TeamScore']) else 0,
            'Score B': row['OpponentScore'] if pd.notna(row['OpponentScore']) else 0,
            'Result A': 'W' if row['TeamScore'] > row['OpponentScore'] else ('L' if row['TeamScore'] < row['OpponentScore'] else 'T'),
            'Result B': 'W' if row['OpponentScore'] > row['TeamScore'] else ('L' if row['OpponentScore'] < row['TeamScore'] else 'T'),
            'Event': row['Competition'],
            'Competition': row['Competition'],
            'Division': 'U11',
            'Venue': 'Unknown',
            'Location': 'Arizona',
            'Match ID': f"u11_{len(converted_games)}",
            'Original Team ID': '',
            'Team A Normalized': row['Team'],
            'Team B Normalized': row['Opponent'],
            'Team A Match': row['TeamRaw'],
            'Team A Match Type': 'EXACT',
            'Team B Match': row['OpponentRaw'],
            'Team B Match Type': 'EXACT'
        }
        converted_games.append(game)
    
    # Create DataFrame
    df_converted = pd.DataFrame(converted_games)
    
    print(f"Converted games shape: {df_converted.shape}")
    print(f"Converted columns: {df_converted.columns.tolist()}")
    
    # Save converted games
    output_path = "gold/Matched_Games_U11_Converted.csv"
    df_converted.to_csv(output_path, index=False)
    print(f"Saved converted U11 games to {output_path}")
    
    # Show sample
    print("\nSample converted U11 games:")
    print(df_converted[['Date', 'Team A', 'Team B', 'Score A', 'Score B', 'Division']].head(10))
    
    return df_converted

if __name__ == "__main__":
    convert_u11_to_u12_format()
