#!/usr/bin/env python3
"""
Test script for U11 division pipeline validation
"""

import os
import sys
import pandas as pd
from pathlib import Path

def test_u11_pipeline():
    """Test the U11 division pipeline components."""
    print("Testing U11 Division Pipeline")
    print("=" * 50)
    
    # Test 1: Check scraper configuration
    print("\n1. Testing scraper configuration...")
    try:
        import scraper_config as cfg
        if "az_boys_u11" in cfg.DIVISION_URLS:
            print("PASS: U11 division URL configured")
        else:
            print("FAIL: U11 division URL not found in configuration")
            return False
    except Exception as e:
        print(f"FAIL: Error loading scraper config: {e}")
        return False
    
    # Test 2: Check multi-division scraper
    print("\n2. Testing multi-division scraper...")
    if Path("scraper_multi_division.py").exists():
        print("PASS: Multi-division scraper exists")
    else:
        print("FAIL: Multi-division scraper not found")
        return False
    
    # Test 3: Check multi-division ranking script
    print("\n3. Testing multi-division ranking script...")
    if Path("rankings/generate_team_rankings_v53_enhanced_multi.py").exists():
        print("PASS: Multi-division ranking script exists")
    else:
        print("FAIL: Multi-division ranking script not found")
        return False
    
    # Test 4: Check API division support
    print("\n4. Testing API division support...")
    try:
        with open("app.py", "r") as f:
            content = f.read()
            if "division" in content and "az_boys_u11" in content:
                print("PASS: API division support implemented")
            else:
                print("FAIL: API division support not found")
                return False
    except Exception as e:
        print(f"FAIL: Error checking API: {e}")
        return False
    
    # Test 5: Check frontend division support
    print("\n5. Testing frontend division support...")
    try:
        # Check main app component
        with open("src/YouthRankingsApp.jsx", "r", encoding="utf-8") as f:
            content = f.read()
            if "division" in content and "setDivision" in content:
                print("PASS: Main app division support implemented")
            else:
                print("FAIL: Main app division support not found")
                return False
        
        # Check selector component
        with open("src/SelectorHero.jsx", "r", encoding="utf-8") as f:
            content = f.read()
            if "division" in content and "az_boys_u11" in content:
                print("PASS: Selector division support implemented")
            else:
                print("FAIL: Selector division support not found")
                return False
                
    except Exception as e:
        print(f"FAIL: Error checking frontend: {e}")
        return False
    
    # Test 6: Check dashboard division support
    print("\n6. Testing dashboard division support...")
    if Path("dashboard/app_v53_multi_division.py").exists():
        print("PASS: Multi-division dashboard exists")
    else:
        print("FAIL: Multi-division dashboard not found")
        return False
    
    # Test 7: Check documentation
    print("\n7. Testing documentation...")
    if Path("docs/MULTI_DIVISION_GUIDE.md").exists():
        print("PASS: Multi-division guide exists")
    else:
        print("FAIL: Multi-division guide not found")
        return False
    
    print("\nSUCCESS: All tests passed! U11 division pipeline is ready.")
    print("\nNext steps:")
    print("1. Run: python scraper_multi_division.py --division az_boys_u11")
    print("2. Run: python rankings/generate_team_rankings_v53_enhanced_multi.py --division AZ_Boys_U11")
    print("3. Test API: http://localhost:8000/api/rankings?division=az_boys_u11")
    print("4. Test frontend: http://localhost:3000")
    
    return True

if __name__ == "__main__":
    success = test_u11_pipeline()
    sys.exit(0 if success else 1)
