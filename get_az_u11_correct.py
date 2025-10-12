#!/usr/bin/env python3
"""
Quick fix: Get Arizona U11 teams with correct team_id field
"""
import requests
import pandas as pd
import time
from datetime import datetime

def get_az_u11_teams():
    """Get Arizona U11 teams with correct team_id"""
    print("Getting Arizona U11 teams with correct team_id...")
    
    az_teams = []
    page = 1
    
    while page <= 50:  # Limit to first 50 pages to avoid timeout
        print(f"Page {page}...")
        
        url = "https://system.gotsport.com/api/v1/team_ranking_data"
        params = {
            "search[team_country]": "USA",
            "search[age]": "11", 
            "search[gender]": "m",
            "search[page]": page
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Origin': 'https://rankings.gotsport.com',
            'Referer': 'https://rankings.gotsport.com/'
        }
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if not data.get('team_ranking_data'):
                print(f"No more teams on page {page}")
                break
            
            teams = data['team_ranking_data']
            print(f"  Found {len(teams)} teams")
            
            for team in teams:
                team_name = team.get('team_name', '')
                ranking_id = team.get('id')  # This is the ranking ID (42162343)
                team_id = team.get('team_id')  # This is the match ID (163451)
                team_association = team.get('team_association', '')
                
                # Only get Arizona teams
                if team_association == 'AZ' and team_id and team_name:
                    az_teams.append({
                        'team_name': team_name,
                        'ranking_id': ranking_id,  # Keep for reference
                        'team_id': team_id,        # This is what we need!
                        'state': team_association,
                        'club_name': team.get('club_name', ''),
                        'total_points': team.get('total_points', 0),
                        'total_matches': team.get('total_matches', 0)
                    })
            
            page += 1
            time.sleep(0.3)  # Faster requests
            
        except Exception as e:
            print(f"Error on page {page}: {e}")
            break
    
    if not az_teams:
        print("No Arizona U11 teams found!")
        return None
    
    # Convert to DataFrame
    df = pd.DataFrame(az_teams)
    
    # Save to current directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"AZ_teams_CORRECTED_{timestamp}.csv"
    df.to_csv(output_file, index=False)
    
    print(f"\nSUCCESS!")
    print(f"Found {len(df)} Arizona U11 teams with CORRECT team_ids")
    print(f"Saved to: {output_file}")
    
    # Show first 10 results
    print(f"\nFIRST 10 RESULTS:")
    print("=" * 80)
    print(df[['team_name', 'ranking_id', 'team_id', 'total_matches']].head(10).to_string(index=False))
    
    # Test a few team_ids
    print(f"\nTesting team_ids with matches API...")
    for i, row in df.head(3).iterrows():
        team_id = row['team_id']
        team_name = row['team_name']
        
        url = f"https://system.gotsport.com/api/v1/teams/{team_id}/matches?past=true"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Origin': 'https://rankings.gotsport.com',
            'Referer': 'https://rankings.gotsport.com/'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                match_count = len(data) if isinstance(data, list) else 0
                print(f"✅ {team_name}: Team ID {team_id} -> {match_count} matches")
            else:
                print(f"❌ {team_name}: Team ID {team_id} -> Status {response.status_code}")
        except Exception as e:
            print(f"❌ {team_name}: Team ID {team_id} -> Error: {e}")
        
        time.sleep(0.5)
    
    return df

if __name__ == "__main__":
    df = get_az_u11_teams()

