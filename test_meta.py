#!/usr/bin/env python3
"""
Test the enhanced API meta structure
"""

import requests
import json

def test_enhanced_meta():
    """Test the enhanced meta structure"""
    print("Testing Enhanced Meta Structure")
    print("=" * 40)
    
    try:
        # Test the rankings endpoint
        r = requests.get("http://localhost:8000/api/rankings?state=AZ&gender=MALE&year=2014&limit=3")
        data = r.json()
        
        print(f"Status: {r.status_code}")
        print(f"Meta keys: {list(data['meta'].keys())}")
        print(f"Meta content: {json.dumps(data['meta'], indent=2)}")
        
        # Check for enhanced fields
        meta = data['meta']
        expected_fields = ['hidden_inactive', 'slice', 'records', 'total_available']
        
        print("\nField verification:")
        for field in expected_fields:
            if field in meta:
                print(f"  PASS: {field} = {meta[field]}")
            else:
                print(f"  MISSING: {field}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    test_enhanced_meta()

