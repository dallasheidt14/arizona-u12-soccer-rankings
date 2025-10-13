#!/usr/bin/env python3
"""
Test U11 API with correct rankings file
"""
import requests

def test_u11_api():
    print("Testing U11 API with rankings_new.csv...")
    
    response = requests.get('http://localhost:8000/api/v1/az/m/u11/rankings')
    data = response.json()
    
    print(f"Status: {response.status_code}")
    print(f"Total teams: {len(data.get('data', []))}")
    
    print("\nFirst 5 teams:")
    for i, team in enumerate(data['data'][:5]):
        print(f"  {i+1}. {team['Team']}")
    
    # Check for U9/U10 teams
    u10_teams = [team for team in data['data'] if 'U9' in team['Team'] or 'U10' in team['Team']]
    print(f"\nU9/U10 teams found: {len(u10_teams)}")
    if u10_teams:
        for team in u10_teams:
            print(f"  - {team['Team']}")

if __name__ == "__main__":
    test_u11_api()
