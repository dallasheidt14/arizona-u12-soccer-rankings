"""
Test script for daily scraper
Run this to test the scraper before setting up automated scheduling
"""

import os
import sys
from pathlib import Path

def test_scraper():
    """Test the daily scraper functionality."""
    print("Testing Daily Soccer Scraper")
    print("=" * 50)
    
    # Check if required files exist
    required_files = [
        "scraper_config.py",
        "scraper_daily.py", 
        "AZ MALE U12 MASTER TEAM LIST.csv"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"ERROR: Missing required files: {missing_files}")
        return False
    
    print("SUCCESS: All required files present")
    
    # Test configuration loading
    try:
        import scraper_config as cfg
        print(f"SUCCESS: Configuration loaded: {len(cfg.SCRAPER_SOURCES)} sources configured")
    except Exception as e:
        print(f"ERROR: Configuration error: {e}")
        return False
    
    # Test data loader
    try:
        from data_loader import get_data_source_info
        data_info = get_data_source_info()
        print(f"SUCCESS: Data loader working: {data_info['data_source']}")
    except Exception as e:
        print(f"ERROR: Data loader error: {e}")
        return False
    
    # Test bootstrap aliases
    try:
        import bootstrap_aliases
        print("SUCCESS: Bootstrap aliases script ready")
    except Exception as e:
        print(f"ERROR: Bootstrap aliases error: {e}")
        return False
    
    print("\nREADY: Ready to run scraper!")
    print("Commands:")
    print("  python bootstrap_aliases.py    # Create team aliases")
    print("  python scraper_daily.py        # Run daily scrape")
    print("  python generate_team_rankings_v2.py  # Test ranking with new data")
    
    return True

def create_sample_data():
    """Create sample data structure for testing."""
    print("\nCreating sample data structure...")
    
    # Create directories
    dirs = [
        "data_ingest/bronze",
        "data_ingest/silver", 
        "data_ingest/gold"
    ]
    
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"SUCCESS: Created {dir_path}")
    
    # Create empty team aliases file
    aliases_path = Path("team_aliases.json")
    if not aliases_path.exists():
        import json
        with aliases_path.open("w") as f:
            json.dump({}, f)
        print(f"SUCCESS: Created {aliases_path}")

if __name__ == "__main__":
    success = test_scraper()
    
    if success:
        create_sample_data()
        print("\nSETUP COMPLETE: Ready for daily scraping.")
    else:
        print("\nSETUP FAILED: Please fix errors above.")
        sys.exit(1)
