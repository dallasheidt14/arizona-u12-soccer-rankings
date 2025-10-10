"""
Format Validator Utility
Ensures all division data matches U12 schema for scalability
"""

import pandas as pd
from pathlib import Path

EXPECTED_COLS = ["Team A", "Team B", "Score A", "Score B", "Date"]

def validate_format(path):
    """Validate that a games file matches the expected U12 format"""
    if not Path(path).exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    df = pd.read_csv(path)
    missing = [c for c in EXPECTED_COLS if c not in df.columns]
    
    if missing:
        raise ValueError(f"{path} is missing columns: {missing}")
    
    print(f"PASS: {path} matches expected format ({len(df)} rows)")
    return True

def validate_master_list_format(path):
    """Validate that a master team list matches the expected format"""
    if not Path(path).exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    df = pd.read_csv(path)
    required_cols = ["Team Name", "Club", "Age Group"]
    missing = [c for c in required_cols if c not in df.columns]
    
    if missing:
        raise ValueError(f"{path} is missing columns: {missing}")
    
    print(f"PASS: {path} matches expected master list format ({len(df)} teams)")
    return True

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python -m utils.validate_format <file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    if "master" in file_path.lower():
        validate_master_list_format(file_path)
    else:
        validate_format(file_path)
