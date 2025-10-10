"""
Bronze Data Schema Validation
Validates bronze layer data to prevent regressions like storing team IDs instead of team names.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_bronze_teams(csv_path: str) -> bool:
    """
    Validate bronze teams CSV to ensure Team Name column contains actual team names.
    
    Args:
        csv_path: Path to bronze teams CSV file
        
    Returns:
        True if validation passes
        
    Raises:
        ValueError: If validation fails
    """
    logger.info(f"Validating bronze teams file: {csv_path}")
    
    if not Path(csv_path).exists():
        raise FileNotFoundError(f"Bronze file not found: {csv_path}")
    
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        raise ValueError(f"Failed to read CSV file {csv_path}: {e}")
    
    # Check if Team Name column exists
    if "Team Name" not in df.columns:
        raise ValueError(f"Missing 'Team Name' column in {csv_path}")
    
    # Check if Team Name column is numeric
    if pd.api.types.is_numeric_dtype(df["Team Name"]):
        raise ValueError(f"Team Name column is numeric in {csv_path}")
    
    # Check if too many values look like IDs (pure numeric strings)
    team_names = df["Team Name"].astype(str).str.strip()
    numeric_mask = team_names.str.fullmatch(r"\d+")
    numeric_pct = numeric_mask.mean()
    
    if numeric_pct > 0.1:  # More than 10% numeric
        raise ValueError(f"Team Name appears to contain IDs ({numeric_pct:.1%} numeric) in {csv_path}")
    
    # Check for suspiciously short team names (likely IDs)
    short_names = team_names.str.len() <= 3
    short_pct = short_names.mean()
    
    if short_pct > 0.2:  # More than 20% very short names
        raise ValueError(f"Too many short team names ({short_pct:.1%} <= 3 chars) in {csv_path}")
    
    # Check for common team name patterns
    has_common_patterns = (
        team_names.str.contains(r"\d{4}", regex=True).any() or  # Birth years
        team_names.str.contains("boys|girls", case=False).any() or  # Gender
        team_names.str.contains("fc|sc|united|academy", case=False).any()  # Common suffixes
    )
    
    if not has_common_patterns and len(team_names) > 10:
        logger.warning(f"No common team name patterns found in {csv_path}")
    
    logger.info(f"✅ Bronze teams validation passed for {csv_path}")
    return True

def validate_bronze_games(csv_path: str) -> bool:
    """
    Validate bronze games CSV to ensure proper structure.
    
    Args:
        csv_path: Path to bronze games CSV file
        
    Returns:
        True if validation passes
        
    Raises:
        ValueError: If validation fails
    """
    logger.info(f"Validating bronze games file: {csv_path}")
    
    if not Path(csv_path).exists():
        raise FileNotFoundError(f"Bronze file not found: {csv_path}")
    
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        raise ValueError(f"Failed to read CSV file {csv_path}: {e}")
    
    # Check for required columns
    required_columns = ["Team", "Opponent", "TeamScore", "OpponentScore", "Date"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        raise ValueError(f"Missing required columns in {csv_path}: {missing_columns}")
    
    # Check for empty file
    if len(df) == 0:
        raise ValueError(f"Empty games file: {csv_path}")
    
    # Check for reasonable data ranges
    if "TeamScore" in df.columns and "OpponentScore" in df.columns:
        scores = pd.concat([df["TeamScore"], df["OpponentScore"]])
        scores = pd.to_numeric(scores, errors='coerce').dropna()
        
        if len(scores) > 0:
            max_score = scores.max()
            if max_score > 20:  # Unreasonably high scores
                logger.warning(f"Very high scores found in {csv_path}: max = {max_score}")
    
    logger.info(f"✅ Bronze games validation passed for {csv_path}")
    return True

def validate_all_bronze_data() -> bool:
    """
    Validate all bronze data files in the bronze directory.
    
    Returns:
        True if all validations pass
        
    Raises:
        ValueError: If any validation fails
    """
    bronze_dir = Path("bronze")
    
    if not bronze_dir.exists():
        logger.warning("Bronze directory not found")
        return True
    
    validation_errors = []
    
    # Find all CSV files in bronze directory
    csv_files = list(bronze_dir.glob("*.csv"))
    
    for csv_file in csv_files:
        try:
            if "teams" in csv_file.name.lower():
                validate_bronze_teams(str(csv_file))
            elif "games" in csv_file.name.lower():
                validate_bronze_games(str(csv_file))
            else:
                logger.info(f"Skipping unknown bronze file: {csv_file}")
        except Exception as e:
            validation_errors.append(f"{csv_file}: {e}")
    
    if validation_errors:
        error_msg = "Bronze data validation failed:\n" + "\n".join(validation_errors)
        raise ValueError(error_msg)
    
    logger.info("✅ All bronze data validation passed")
    return True

def main():
    """Main function for CLI usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate bronze data schema")
    parser.add_argument("--file", help="Specific file to validate")
    parser.add_argument("--all", action="store_true", help="Validate all bronze files")
    
    args = parser.parse_args()
    
    try:
        if args.file:
            if "teams" in args.file.lower():
                validate_bronze_teams(args.file)
            elif "games" in args.file.lower():
                validate_bronze_games(args.file)
            else:
                logger.error(f"Unknown file type: {args.file}")
                return 1
        elif args.all:
            validate_all_bronze_data()
        else:
            logger.error("Must specify --file or --all")
            return 1
        
        print("SUCCESS: Validation passed")
        return 0
        
    except Exception as e:
        print(f"ERROR: Validation failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
