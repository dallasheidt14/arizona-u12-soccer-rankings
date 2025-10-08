#!/usr/bin/env python3
"""
Match Arizona Teams to Game History
=================================

Use the existing 170 Arizona U12 Male teams list and match them
to our game history dataset for accurate state identification.
"""

import pandas as pd
import json
from datetime import datetime
from typing import Set, Dict

def match_arizona_teams_to_games():
    """Match the 170 Arizona teams to our game history dataset"""
    
    print("MATCHING ARIZONA TEAMS TO GAME HISTORY")
    print("=" * 45)
    
    # Load the 170 Arizona teams from our existing file
    try:
        arizona_teams_df = pd.read_csv("real_arizona_u12_teams_20251008_112058.csv")
        print(f"Loaded {len(arizona_teams_df)} Arizona teams from existing file")
    except Exception as e:
        print(f"Error loading Arizona teams: {e}")
        return
    
    # Load our game history dataset
    try:
        df = pd.read_csv("arizona_u12_games_BETTER_20251008_112641.csv")
        print(f"Loaded game history dataset: {len(df)} games")
    except Exception as e:
        print(f"Error loading game history: {e}")
        return
    
    # Get all unique teams from game history
    all_game_teams = set(df['Team A'].tolist() + df['Team B'].tolist())
    print(f"Total unique teams in game history: {len(all_game_teams)}")
    
    # Create Arizona teams set (normalized for matching)
    arizona_team_names = set(arizona_teams_df['Team Name'].str.strip())
    print(f"Arizona teams from API: {len(arizona_team_names)}")
    
    # Show some Arizona teams
    print(f"\nSAMPLE ARIZONA TEAMS:")
    print("-" * 25)
    for i, team in enumerate(arizona_team_names):
        if i < 10:
            print(f"{i+1:2d}. {team}")
    
    # Match teams using exact matching
    matched_arizona_teams = set()
    unmatched_teams = set()
    
    for game_team in all_game_teams:
        game_team_str = str(game_team).strip()
        
        # Try exact match
        if game_team_str in arizona_team_names:
            matched_arizona_teams.add(game_team)
        else:
            unmatched_teams.add(game_team)
    
    print(f"\nMATCHING RESULTS:")
    print("-" * 20)
    print(f"Arizona teams matched: {len(matched_arizona_teams)}")
    print(f"Teams not matched: {len(unmatched_teams)}")
    print(f"Match rate: {len(matched_arizona_teams)/len(all_game_teams)*100:.1f}%")
    
    # Show some matched teams
    print(f"\nSAMPLE MATCHED ARIZONA TEAMS:")
    print("-" * 35)
    for i, team in enumerate(list(matched_arizona_teams)[:15]):
        print(f"{i+1:2d}. {team}")
    
    # Show some unmatched teams
    print(f"\nSAMPLE UNMATCHED TEAMS:")
    print("-" * 25)
    for i, team in enumerate(list(unmatched_teams)[:15]):
        print(f"{i+1:2d}. {team}")
    
    # Check specific teams mentioned by user
    test_teams = [
        "Playmaker Futbol Academy 14B Gold",
        "Playmaker Futbol Academy 14B Black", 
        "Southeast 2014 Boys Black",
        "Next Level Soccer Southeast 2014 Boys Red",
        "Avalanche 14B Gray SL"
    ]
    
    print(f"\nSPECIFIC TEAM VERIFICATION:")
    print("-" * 30)
    for team in test_teams:
        if team in matched_arizona_teams:
            status = "AZ (Matched)"
        elif team in unmatched_teams:
            status = "Non-AZ (Not matched)"
        else:
            status = "Not in dataset"
        print(f"  {team}: {status}")
    
    # Create final dataset with correct Arizona identification
    def is_arizona_team(team_name):
        return team_name in matched_arizona_teams
    
    df['Team A Is Arizona'] = df['Team A'].apply(is_arizona_team)
    df['Team B Is Arizona'] = df['Team B'].apply(is_arizona_team)
    
    # Save final dataset
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    final_filename = f"arizona_u12_games_FINAL_{timestamp}.csv"
    df.to_csv(final_filename, index=False, encoding='utf-8')
    print(f"\nFinal dataset saved to: {final_filename}")
    
    # Create team summary
    team_summary = []
    for team in all_game_teams:
        team_games = df[(df['Team A'] == team) | (df['Team B'] == team)]
        
        # Count wins, losses, ties
        wins = 0
        losses = 0
        ties = 0
        
        for _, game in team_games.iterrows():
            if game['Team A'] == team:
                if game['Result A'] == 'W': wins += 1
                elif game['Result A'] == 'L': losses += 1
                else: ties += 1
            else:  # Team B
                if game['Result B'] == 'W': wins += 1
                elif game['Result B'] == 'L': losses += 1
                else: ties += 1
        
        team_summary.append({
            'Team Name': team,
            'Is Arizona': team in matched_arizona_teams,
            'Gender': 'M',
            'Total Games': len(team_games),
            'Wins': wins,
            'Losses': losses,
            'Ties': ties,
            'Win Percentage': (wins / len(team_games) * 100) if len(team_games) > 0 else 0,
            'First Game': team_games['Date'].min() if len(team_games) > 0 else '',
            'Last Game': team_games['Date'].max() if len(team_games) > 0 else ''
        })
    
    # Save team summary
    teams_filename = f"arizona_u12_teams_FINAL_{timestamp}.csv"
    team_df = pd.DataFrame(team_summary)
    team_df = team_df.sort_values(['Is Arizona', 'Total Games'], ascending=[False, False])
    team_df.to_csv(teams_filename, index=False, encoding='utf-8')
    print(f"Final team summary saved to: {teams_filename}")
    
    # Show final statistics
    print(f"\nFINAL STATISTICS:")
    print("-" * 20)
    print(f"Total teams in game history: {len(all_game_teams)}")
    print(f"Arizona teams: {len(matched_arizona_teams)}")
    print(f"Non-Arizona teams: {len(unmatched_teams)}")
    
    # Show games by type
    az_vs_az = len(df[(df['Team A Is Arizona'] == True) & (df['Team B Is Arizona'] == True)])
    az_vs_non_az = len(df[((df['Team A Is Arizona'] == True) & (df['Team B Is Arizona'] == False)) | 
                          ((df['Team A Is Arizona'] == False) & (df['Team B Is Arizona'] == True))])
    non_az_vs_non_az = len(df[(df['Team A Is Arizona'] == False) & (df['Team B Is Arizona'] == False)])
    
    print(f"\nGames by type:")
    print(f"  Arizona vs Arizona: {az_vs_az}")
    print(f"  Arizona vs Non-Arizona: {az_vs_non_az}")
    print(f"  Non-Arizona vs Non-Arizona: {non_az_vs_non_az}")
    
    # Show Arizona teams that weren't matched (teams in API but not in game history)
    arizona_not_in_games = arizona_team_names - matched_arizona_teams
    if arizona_not_in_games:
        print(f"\nArizona teams from API not in game history ({len(arizona_not_in_games)}):")
        print("-" * 55)
        for i, team in enumerate(list(arizona_not_in_games)[:10]):
            print(f"{i+1:2d}. {team}")
        if len(arizona_not_in_games) > 10:
            print(f"... and {len(arizona_not_in_games) - 10} more")
    
    print(f"\nFINAL MATCHING COMPLETE!")
    print(f"Files created: {final_filename}, {teams_filename}")
    
    return df, team_df

if __name__ == "__main__":
    final_games, final_teams = match_arizona_teams_to_games()
