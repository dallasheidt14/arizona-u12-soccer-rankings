"""
Convert to Ranking Format Utility
Normalizes data format for ranking algorithm input
"""

import pandas as pd

def convert_to_ranking_format(input_path, output_path):
    """Convert any division data to standard ranking format"""
    df = pd.read_csv(input_path)
    
    print(f"Input file: {input_path}")
    print(f"Input shape: {df.shape}")
    print(f"Input columns: {df.columns.tolist()}")
    
    # Normalize column naming to match ranking script expectations
    rename_map = {
        'TeamName': 'Team A',
        'Team_Canonical': 'Team A', 
        'TeamCanonical': 'Team A',
        'OpponentName': 'Team B',
        'Opponent_Canonical': 'Team B',
        'Team': 'Team A',
        'Opponent': 'Team B',
        'TeamScore': 'Score A',
        'OpponentScore': 'Score B'
    }
    
    # Apply renames for columns that exist
    existing_renames = {k: v for k, v in rename_map.items() if k in df.columns}
    df.rename(columns=existing_renames, inplace=True)
    
    if existing_renames:
        print(f"Renamed columns: {existing_renames}")
    
    # Ensure we have the required columns
    required_cols = ['Team A', 'Team B', 'Score A', 'Score B', 'Date']
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        print(f"Missing required columns: {missing_cols}")
        print("Available columns:", df.columns.tolist())
        return False
    
    # Ensure correct types
    df['Team A'] = df['Team A'].astype(str).str.strip()
    df['Team B'] = df['Team B'].astype(str).str.strip()
    
    # Handle numeric scores
    df['Score A'] = pd.to_numeric(df['Score A'], errors='coerce').fillna(0)
    df['Score B'] = pd.to_numeric(df['Score B'], errors='coerce').fillna(0)
    
    # Reset index if necessary
    if df.index.name or "Unnamed: 0" in df.columns:
        df.reset_index(drop=True, inplace=True)
        print("Reset DataFrame index")
    
    # Drop duplicate rows
    initial_count = len(df)
    df.drop_duplicates(subset=['Team A', 'Team B', 'Date'], inplace=True)
    final_count = len(df)
    
    if initial_count != final_count:
        print(f"Removed {initial_count - final_count} duplicate rows")
    
    # Select only required columns for ranking
    df_clean = df[required_cols].copy()
    
    # Save cleaned file
    df_clean.to_csv(output_path, index=False)
    print(f"Converted {len(df_clean)} rows to {output_path}")
    
    # Show sample
    print("\nSample cleaned data:")
    print(df_clean.head(3))
    
    return True

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python convert_to_ranking_format.py <input_path> <output_path>")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    convert_to_ranking_format(input_path, output_path)
