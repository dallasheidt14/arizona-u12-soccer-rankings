import sys
from pathlib import Path
sys.path.append('.')  # Add current directory for utils imports

import pandas as pd
import pytest
from src.utils.division import parse_age_from_division, to_canonical_division
from src.utils.data_loader import resolve_input_path, load_games_frame

def test_division_parsing():
    """Test division string parsing utilities."""
    assert parse_age_from_division("az_boys_u11") == "U11"
    assert parse_age_from_division("AZ_Boys_U12") == "U12"
    assert parse_age_from_division("AZ-BOYS-U10") == "U10"
    assert to_canonical_division("az_boys_u11") == "AZ_Boys_U11"
    assert to_canonical_division("az_boys_u12") == "AZ_Boys_U12"

def test_gold_resolution_and_schema():
    """Test gold file resolution and schema validation."""
    # Test U11 resolution
    try:
        p = resolve_input_path("U11")
        assert p.exists()
        df = load_games_frame(p)
        for c in ["Team A", "Team B", "Score A", "Score B", "Date"]:
            assert c in df.columns
        assert len(df) > 0
        print(f"U11: Found {len(df)} games in {p}")
    except FileNotFoundError:
        pytest.skip("U11 gold file not found - run scraping first")
    
    # Test U12 resolution
    try:
        p = resolve_input_path("U12")
        assert p.exists()
        df = load_games_frame(p)
        for c in ["Team A", "Team B", "Score A", "Score B", "Date"]:
            assert c in df.columns
        assert len(df) > 0
        print(f"U12: Found {len(df)} games in {p}")
    except FileNotFoundError:
        pytest.skip("U12 gold file not found - run scraping first")

def test_team_name_display():
    """Test that rankings output has proper team names (not numeric)."""
    rankings_files = [
        "Rankings_AZ_M_U11_2025_v53e.csv",
        "Rankings_AZ_M_U12_2025_v53e.csv"
    ]
    
    for file_path in rankings_files:
        if Path(file_path).exists():
            df = pd.read_csv(file_path)
            
            # Check first 10 rows for numeric team names
            team_names = df["Team"].head(10).astype(str)
            numeric_names = team_names.str.isnumeric()
            
            if numeric_names.any():
                pytest.fail(f"Numeric team names found in {file_path}: {team_names[numeric_names].tolist()}")
            
            # Check that team names look reasonable
            assert len(df) > 0, f"No teams found in {file_path}"
            assert "Team" in df.columns, f"No Team column in {file_path}"
            
            print(f"PASS {file_path}: {len(df)} teams with proper names")

def test_team_count_ranges():
    """Test that team counts are within expected ranges."""
    expected_ranges = {
        "U10": (80, 100),
        "U11": (120, 160),
        "U12": (140, 180),
        "U13": (70, 120),  # More lenient range
        "U14": (60, 100)
    }
    
    for age, (min_count, max_count) in expected_ranges.items():
        file_path = f"Rankings_AZ_M_{age}_2025_v53e.csv"
        if Path(file_path).exists():
            df = pd.read_csv(file_path)
            team_count = len(df)
            
            if not (min_count <= team_count <= max_count):
                pytest.fail(f"{age}: Expected {min_count}-{max_count} teams, got {team_count}")
            
            print(f"PASS {age}: {team_count} teams (expected {min_count}-{max_count})")

def test_connectivity_reports():
    """Test that connectivity reports are generated."""
    connectivity_files = [
        "connectivity_report_u11_v53e.csv",
        "connectivity_report_u12_v53e.csv"
    ]
    
    for file_path in connectivity_files:
        if Path(file_path).exists():
            df = pd.read_csv(file_path)
            assert "Team" in df.columns
            assert "ComponentSize" in df.columns
            assert len(df) > 0
            
            # Check for isolated clusters
            isolated = df[df["ComponentSize"] < 3]
            if len(isolated) > 0:
                print(f"WARNING {file_path}: {len(isolated)} teams in isolated clusters")
            else:
                print(f"PASS {file_path}: No isolated clusters")

def test_powerscore_ranges():
    """Test that PowerScores are in reasonable ranges."""
    rankings_files = [
        "Rankings_AZ_M_U11_2025_v53e.csv",
        "Rankings_AZ_M_U12_2025_v53e.csv"
    ]
    
    for file_path in rankings_files:
        if Path(file_path).exists():
            df = pd.read_csv(file_path)
            
            if "PowerScore_adj" in df.columns:
                scores = df["PowerScore_adj"]
                assert scores.min() >= 0, f"Negative PowerScore found in {file_path}"
                assert scores.max() <= 1, f"PowerScore > 1 found in {file_path}"
                
                # Check top 5 teams have reasonable scores
                top_5_scores = scores.head(5)
                assert top_5_scores.min() >= 0.3, f"Top teams have low PowerScores in {file_path}"
                
                print(f"PASS {file_path}: PowerScores in range [{scores.min():.3f}, {scores.max():.3f}]")

if __name__ == "__main__":
    # Run tests manually
    test_division_parsing()
    test_gold_resolution_and_schema()
    test_team_name_display()
    test_team_count_ranges()
    test_connectivity_reports()
    test_powerscore_ranges()
    print("All tests passed!")
