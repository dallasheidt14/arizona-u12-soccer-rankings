#!/usr/bin/env python3
"""
Multi-State Soccer Rankings Scraper
===================================

Immediate implementation for scraping multiple states and genders
"""

import requests
import csv
import json
import time
import pandas as pd
from datetime import datetime
from typing import List, Dict, Tuple

class MultiStateScraper:
    """Scraper for multiple states and genders"""
    
    def __init__(self):
        self.base_url = "https://system.gotsport.com/api/v1/team_ranking_data"
        self.matches_url = "https://system.gotsport.com/api/v1/teams/{team_id}/matches"
        self.headers = {
            "Accept": "application/json",
            "Referer": "https://system.gotsport.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
        }
        
        # Priority states for initial scraping
        self.priority_states = [
            'CA', 'TX', 'FL', 'NY', 'PA', 'IL', 'OH', 'GA', 'NC', 'MI', 
            'NJ', 'VA', 'WA', 'AZ', 'MA', 'TN', 'IN', 'MO', 'MD', 'WI'
        ]
        
        # Popular age groups
        self.popular_ages = [10, 12, 14, 16, 18]
        
        # Genders
        self.genders = ['m', 'f']
    
    def get_teams_for_state_gender_age(self, state: str, gender: str, age: int) -> List[Dict]:
        """Get all teams for a specific state, gender, and age group"""
        
        all_teams = []
        page = 1
        
        print(f"  Fetching {state} {gender.upper()} U{age} teams...")
        
        while True:
            params = {
                "search[team_country]": "USA",
                "search[age]": age,
                "search[gender]": gender,
                "search[team_or_club_name]": "",
                "search[team_association]": state,
                "search[filter_by]": "state",
                "search[page]": page
            }
            
            try:
                response = requests.get(self.base_url, params=params, headers=self.headers, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                teams = data.get("team_ranking_data", [])
                
                if not teams:
                    break
                
                print(f"    Page {page}: {len(teams)} teams")
                
                for team in teams:
                    team_data = {
                        "Team Name": team.get("team_name", ""),
                        "Club": team.get("club_name", ""),
                        "Team ID": team.get("team_id", ""),
                        "Points": team.get("total_points", 0),
                        "Wins": team.get("total_wins", 0),
                        "Losses": team.get("total_losses", 0),
                        "Ties": team.get("total_draws", 0),
                        "Games Played": team.get("total_matches", 0),
                        "Rank": team.get("national_rank", 0),
                        "State": team.get("team_association", ""),
                        "Region": team.get("team_region", ""),
                        "Win Percentage": team.get("win_percent", 0),
                        "State Rank": team.get("association_rank", 0),
                        "Regional Rank": team.get("regional_rank", 0),
                        "Goal Ratio": team.get("goal_ratio", 0),
                        "Team URL": f"https://rankings.gotsport.com/teams/{team.get('team_id', '')}",
                        "Last Activity": team.get("ranking_date", ""),
                        "Gender": gender.upper(),
                        "Age Group": f"U{age}",
                        "State Code": state
                    }
                    all_teams.append(team_data)
                
                page += 1
                time.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                print(f"    Error on page {page}: {e}")
                break
        
        print(f"  Total {state} {gender.upper()} U{age} teams: {len(all_teams)}")
        return all_teams
    
    def scrape_priority_combinations(self, max_teams_per_state: int = 20) -> Dict:
        """Scrape priority state/gender/age combinations"""
        
        print("MULTI-STATE SOCCER RANKINGS SCRAPER")
        print("=" * 50)
        
        all_teams = []
        all_games = []
        results = {}
        
        total_combinations = len(self.priority_states) * len(self.popular_ages) * len(self.genders)
        current_combination = 0
        
        for state in self.priority_states:
            for age in self.popular_ages:
                for gender in self.genders:
                    current_combination += 1
                    
                    print(f"\n{current_combination}/{total_combinations}: {state} {gender.upper()} U{age}")
                    print("-" * 40)
                    
                    try:
                        # Get teams
                        teams = self.get_teams_for_state_gender_age(state, gender, age)
                        
                        if not teams:
                            print(f"No teams found for {state} {gender.upper()} U{age}")
                            continue
                        
                        # Limit teams if specified
                        if max_teams_per_state and len(teams) > max_teams_per_state:
                            teams = teams[:max_teams_per_state]
                            print(f"Limited to first {max_teams_per_state} teams")
                        
                        # Add to results
                        all_teams.extend(teams)
                        results[f"{state}_{gender.upper()}_U{age}"] = {
                            "teams": len(teams),
                            "games": 0  # We'll add games later if needed
                        }
                        
                        print(f"Added {len(teams)} teams for {state} {gender.upper()} U{age}")
                        
                    except Exception as e:
                        print(f"Error scraping {state} {gender.upper()} U{age}: {e}")
                        continue
                    
                    time.sleep(1)  # Be respectful between combinations
        
        return {
            "all_teams": all_teams,
            "all_games": all_games,
            "results": results,
            "total_teams": len(all_teams)
        }
    
    def save_multi_state_data(self, data: Dict):
        """Save multi-state data to files"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save teams
        if data["all_teams"]:
            teams_filename = f"multi_state_teams_{timestamp}.csv"
            teams_df = pd.DataFrame(data["all_teams"])
            teams_df.to_csv(teams_filename, index=False, encoding='utf-8')
            print(f"Teams saved to: {teams_filename}")
        
        # Save results summary
        results_filename = f"multi_state_results_{timestamp}.json"
        with open(results_filename, "w", encoding="utf-8") as f:
            json.dump({
                "scrape_date": datetime.now().isoformat(),
                "total_teams": data["total_teams"],
                "combinations_scraped": len(data["results"]),
                "results_by_combination": data["results"]
            }, f, indent=2, ensure_ascii=False)
        print(f"Results saved to: {results_filename}")
        
        return teams_filename, results_filename

def main():
    """Main execution function"""
    
    scraper = MultiStateScraper()
    
    print("MULTI-STATE SOCCER RANKINGS SCRAPER")
    print("=" * 50)
    print(f"Priority States: {', '.join(scraper.priority_states)}")
    print(f"Age Groups: U{', U'.join(map(str, scraper.popular_ages))}")
    print(f"Genders: {', '.join(scraper.genders).upper()}")
    print(f"Total Combinations: {len(scraper.priority_states) * len(scraper.popular_ages) * len(scraper.genders)}")
    
    # Ask user for confirmation
    max_teams = input("\nMax teams per state/age/gender (0 for all): ").strip()
    max_teams = int(max_teams) if max_teams else 20
    
    print(f"\nStarting scraping with max {max_teams} teams per combination...")
    
    # Scrape data
    data = scraper.scrape_priority_combinations(max_teams)
    
    # Save data
    teams_file, results_file = scraper.save_multi_state_data(data)
    
    # Show summary
    print(f"\nSCRAPING COMPLETE!")
    print(f"=" * 30)
    print(f"Total teams collected: {data['total_teams']}")
    print(f"Combinations scraped: {len(data['results'])}")
    print(f"Files created: {teams_file}, {results_file}")
    
    # Show breakdown by state
    print(f"\nBREAKDOWN BY STATE:")
    state_totals = {}
    for team in data["all_teams"]:
        state = team["State Code"]
        state_totals[state] = state_totals.get(state, 0) + 1
    
    for state, count in sorted(state_totals.items()):
        print(f"  {state}: {count} teams")

if __name__ == "__main__":
    main()
