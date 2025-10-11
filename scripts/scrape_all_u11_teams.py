#!/usr/bin/env python3
"""
Scrape ALL U11 Boys teams from GotSport API and organize by state.
This creates a comprehensive master list for all 50 states.
"""

import requests
import pandas as pd
import sys
import os
from pathlib import Path
import time

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.id_codec import make_team_id

def scrape_all_u11_teams():
    """Scrape all U11 Boys teams from GotSport API."""
    
    base_url = "https://system.gotsport.com/api/v1/team_ranking_data"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Origin': 'https://rankings.gotsport.com',
        'Referer': 'https://rankings.gotsport.com/',
        'Sec-Ch-Ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
    }
    
    all_teams = []
    page = 1
    max_pages = 420  # Total pages from pagination
    
    print(f"Scraping ALL U11 Boys teams from {max_pages} pages...")
    
    while page <= max_pages:
        params = {
            'search[team_country]': 'USA',
            'search[age]': '11',
            'search[gender]': 'm',
            'search[page]': str(page),
            'search[team_association]': 'AZ'  # This seems to return all teams, not just AZ
        }
        
        if page % 50 == 0:
            print(f"Scraping page {page}/{max_pages}...")
        
        try:
            response = requests.get(base_url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if 'team_ranking_data' not in data:
                break
            
            teams_data = data['team_ranking_data']
            
            if not teams_data:
                break
            
            # Extract all teams
            for team_record in teams_data:
                if isinstance(team_record, dict) and 'team_name' in team_record:
                    team_name = team_record['team_name']
                    club_name = team_record.get('club_name', '') or ''
                    
                    all_teams.append({
                        'team_name': team_name,
                        'club_name': club_name,
                        'page': page
                    })
            
            # Check pagination
            if 'pagination' in data:
                pagination = data['pagination']
                current_page = pagination.get('current_page', page)
                total_pages = pagination.get('total_pages', 1)
                
                if current_page >= total_pages:
                    break
            
            page += 1
            
            # Small delay
            time.sleep(0.1)
            
        except Exception as e:
            print(f"Error on page {page}: {e}")
            break
    
    print(f"\nScraped {len(all_teams)} total teams")
    return all_teams

def organize_by_state(all_teams):
    """Organize teams by state."""
    
    # State mapping
    state_mapping = {
        'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California',
        'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 'FL': 'Florida', 'GA': 'Georgia',
        'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa',
        'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
        'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri',
        'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey',
        'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio',
        'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
        'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont',
        'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming'
    }
    
    teams_by_state = {}
    
    for team in all_teams:
        team_name = team['team_name']
        club_name = team['club_name']
        
        # Try to determine state from team name or club name
        state = None
        state_code = None
        
        # Check for state codes and names
        text_to_check = f"{team_name} {club_name}".upper()
        
        for code, full_name in state_mapping.items():
            if code in text_to_check or full_name.upper() in text_to_check:
                state = full_name
                state_code = code
                break
        
        # If no state found, try common city indicators
        if not state:
            city_indicators = {
                'PHOENIX': 'AZ', 'SCOTTSDALE': 'AZ', 'TUCSON': 'AZ', 'MESA': 'AZ', 'CHANDLER': 'AZ',
                'LAS VEGAS': 'NV', 'HENDERSON': 'NV', 'RENO': 'NV',
                'LOS ANGELES': 'CA', 'SAN DIEGO': 'CA', 'SAN FRANCISCO': 'CA', 'SACRAMENTO': 'CA',
                'MIAMI': 'FL', 'ORLANDO': 'FL', 'TAMPA': 'FL', 'JACKSONVILLE': 'FL',
                'HOUSTON': 'TX', 'DALLAS': 'TX', 'AUSTIN': 'TX', 'SAN ANTONIO': 'TX',
                'CHICAGO': 'IL', 'SPRINGFIELD': 'IL',
                'NEW YORK': 'NY', 'BUFFALO': 'NY', 'ROCHESTER': 'NY',
                'BOSTON': 'MA', 'WORCESTER': 'MA',
                'PHILADELPHIA': 'PA', 'PITTSBURGH': 'PA',
                'DETROIT': 'MI', 'GRAND RAPIDS': 'MI',
                'ATLANTA': 'GA', 'SAVANNAH': 'GA',
                'DENVER': 'CO', 'BOULDER': 'CO',
                'SEATTLE': 'WA', 'SPOKANE': 'WA',
                'PORTLAND': 'OR', 'EUGENE': 'OR',
                'SALT LAKE CITY': 'UT', 'PROVO': 'UT',
                'NASHVILLE': 'TN', 'MEMPHIS': 'TN',
                'KANSAS CITY': 'MO', 'ST LOUIS': 'MO',
                'MINNEAPOLIS': 'MN', 'ST PAUL': 'MN',
                'MILWAUKEE': 'WI', 'MADISON': 'WI',
                'INDIANAPOLIS': 'IN', 'FORT WAYNE': 'IN',
                'COLUMBUS': 'OH', 'CLEVELAND': 'OH', 'CINCINNATI': 'OH',
                'LOUISVILLE': 'KY', 'LEXINGTON': 'KY',
                'CHARLOTTE': 'NC', 'RALEIGH': 'NC',
                'CHARLESTON': 'SC', 'COLUMBIA': 'SC',
                'BIRMINGHAM': 'AL', 'MONTGOMERY': 'AL',
                'JACKSON': 'MS', 'GULFPORT': 'MS',
                'LITTLE ROCK': 'AR', 'FORT SMITH': 'AR',
                'OKLAHOMA CITY': 'OK', 'TULSA': 'OK',
                'DES MOINES': 'IA', 'CEDAR RAPIDS': 'IA',
                'OMAHA': 'NE', 'LINCOLN': 'NE',
                'FARGO': 'ND', 'BISMARCK': 'ND',
                'SIOUX FALLS': 'SD', 'RAPID CITY': 'SD',
                'CHEYENNE': 'WY', 'CASPER': 'WY',
                'BILLINGS': 'MT', 'MISSOULA': 'MT',
                'BOISE': 'ID', 'NAMPA': 'ID',
                'SALT LAKE CITY': 'UT', 'WEST VALLEY CITY': 'UT',
                'CARSON CITY': 'NV', 'NORTH LAS VEGAS': 'NV',
                'ANCHORAGE': 'AK', 'FAIRBANKS': 'AK',
                'HONOLULU': 'HI', 'PEARL CITY': 'HI',
                'BURLINGTON': 'VT', 'MONTPELIER': 'VT',
                'CONCORD': 'NH', 'MANCHESTER': 'NH',
                'AUGUSTA': 'ME', 'PORTLAND': 'ME',
                'PROVIDENCE': 'RI', 'WARWICK': 'RI',
                'HARTFORD': 'CT', 'BRIDGEPORT': 'CT',
                'DOVER': 'DE', 'WILMINGTON': 'DE',
                'ANNAPOLIS': 'MD', 'BALTIMORE': 'MD',
                'RICHMOND': 'VA', 'VIRGINIA BEACH': 'VA',
                'CHARLESTON': 'WV', 'HUNTINGTON': 'WV',
                'FRANKFORT': 'KY', 'LEXINGTON': 'KY',
                'JEFFERSON CITY': 'MO', 'KANSAS CITY': 'MO',
                'LINCOLN': 'NE', 'OMAHA': 'NE',
                'PIERRE': 'SD', 'SIOUX FALLS': 'SD',
                'BISMARCK': 'ND', 'FARGO': 'ND',
                'HELENA': 'MT', 'BILLINGS': 'MT',
                'CHEYENNE': 'WY', 'CASPER': 'WY',
                'BOISE': 'ID', 'NAMPA': 'ID',
                'SALT LAKE CITY': 'UT', 'WEST VALLEY CITY': 'UT',
                'CARSON CITY': 'NV', 'NORTH LAS VEGAS': 'NV',
                'ANCHORAGE': 'AK', 'FAIRBANKS': 'AK',
                'HONOLULU': 'HI', 'PEARL CITY': 'HI'
            }
            
            for city, code in city_indicators.items():
                if city in text_to_check:
                    state = state_mapping[code]
                    state_code = code
                    break
        
        # If still no state, mark as unknown
        if not state:
            state = 'Unknown'
            state_code = 'UNK'
        
        if state not in teams_by_state:
            teams_by_state[state] = []
        
        teams_by_state[state].append({
            'team_name': team_name,
            'club_name': club_name,
            'state': state,
            'state_code': state_code
        })
    
    return teams_by_state

def save_master_lists(teams_by_state):
    """Save master lists for each state."""
    
    # Create output directory
    output_dir = Path("data/master")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save comprehensive list
    all_teams_list = []
    for state, teams in teams_by_state.items():
        for team in teams:
            team_id = make_team_id(team['team_name'], f"us_boys_u11_2025")
            all_teams_list.append({
                'team_id': team_id,
                'display_name': team['team_name'],
                'club': team['club_name'],
                'state': team['state'],
                'state_code': team['state_code']
            })
    
    all_teams_df = pd.DataFrame(all_teams_list)
    all_teams_df.to_csv(output_dir / "all_u11_teams_master.csv", index=False)
    print(f"Saved comprehensive master list: {len(all_teams_df)} teams")
    
    # Save Arizona teams specifically
    if 'Arizona' in teams_by_state:
        az_teams = teams_by_state['Arizona']
        az_master_data = []
        for team in az_teams:
            team_id = make_team_id(team['team_name'], "az_boys_u11_2025")
            az_master_data.append({
                'team_id': team_id,
                'display_name': team['team_name'],
                'club': team['club_name']
            })
        
        az_master_df = pd.DataFrame(az_master_data)
        az_output_dir = Path("data/master/az_boys_u11_2025")
        az_output_dir.mkdir(parents=True, exist_ok=True)
        az_master_df.to_csv(az_output_dir / "master_teams.csv", index=False)
        print(f"Saved Arizona master list: {len(az_master_df)} teams")
    
    # Show summary by state
    print(f"\nTeams by state:")
    for state in sorted(teams_by_state.keys()):
        count = len(teams_by_state[state])
        print(f"  {state}: {count} teams")

if __name__ == "__main__":
    try:
        # Scrape all teams
        all_teams = scrape_all_u11_teams()
        
        if all_teams:
            # Organize by state
            teams_by_state = organize_by_state(all_teams)
            
            # Save master lists
            save_master_lists(teams_by_state)
            
            print(f"\nSuccessfully created master lists for all states!")
        else:
            print("No teams scraped")
            
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
