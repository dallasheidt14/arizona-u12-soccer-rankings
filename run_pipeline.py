#!/usr/bin/env python3
"""
Arizona U12 Soccer Rankings Pipeline
===================================

Complete pipeline to generate U12 soccer rankings from raw data to final output.
This script orchestrates the entire process:

1. Team Matching & Data Cleaning
2. Comprehensive History Generation  
3. V5.3E Enhanced Ranking Calculation
4. Output Generation

Usage:
    python run_pipeline.py

Output Files:
    - data/output/Rankings_v53_enhanced.csv
    - data/output/connectivity_report_v53e.csv
"""

import subprocess
import sys
from pathlib import Path
import pandas as pd

def run_command(command, description):
    """Run a command and handle errors."""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(f"Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        print(f"Error: {e.stderr}")
        return False

def check_input_files():
    """Check that required input files exist."""
    required_files = [
        "data/input/AZ MALE U12 MASTER TEAM LIST.csv",
        "data/input/AZ MALE U12 GAME HISTORY LAST 18 MONTHS .csv"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print("❌ Missing required input files:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        return False
    
    print("✅ All required input files found")
    return True

def main():
    """Main pipeline execution."""
    print("🏆 Arizona U12 Soccer Rankings Pipeline")
    print("=" * 50)
    
    # Check input files
    if not check_input_files():
        sys.exit(1)
    
    # Step 1: Team Matching & Data Cleaning
    if not run_command(
        "python src/core/team_matcher.py",
        "Team Matching & Data Cleaning"
    ):
        sys.exit(1)
    
    # Step 2: Comprehensive History Generation
    if not run_command(
        "python src/core/history_generator.py",
        "Comprehensive History Generation"
    ):
        sys.exit(1)
    
    # Step 3: V5.3E Enhanced Ranking Calculation
    if not run_command(
        "python src/core/ranking_engine.py",
        "V5.3E Enhanced Ranking Calculation"
    ):
        sys.exit(1)
    
    # Verify outputs
    output_files = [
        "data/output/Rankings_v53_enhanced.csv",
        "data/output/connectivity_report_v53e.csv"
    ]
    
    print("\n📊 Pipeline Results:")
    for file_path in output_files:
        if Path(file_path).exists():
            df = pd.read_csv(file_path)
            print(f"✅ {file_path} - {len(df)} records")
        else:
            print(f"❌ {file_path} - Not found")
    
    print("\n🎉 Pipeline completed successfully!")
    print("Check data/output/ for final rankings and reports.")

if __name__ == "__main__":
    main()
