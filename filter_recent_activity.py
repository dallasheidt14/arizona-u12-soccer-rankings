#!/usr/bin/env python3
"""
Filter Teams and Games by Recent Activity
=========================================

Filters teams and games based on:
1. Exclude teams with NO game history in the last 9 months
2. Only include game history from the last 18 months
"""

import pandas as pd
import json
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

def filter_recent_activity():
    """Filter teams and games based on recent activity requirements"""
    
    print("FILTERING TEAMS AND GAMES BY RECENT ACTIVITY")
    print("=" * 60)
    
    # Load the clean dataset
    try:
        df = pd.read_csv("arizona_u12_games_CLEAN_20251008_103719.csv")
        print(f"Loaded clean dataset: {len(df)} games")
    except Exception as e:
        print(f"Error loading dataset: {e}")
        return
    
    # Define date thresholds
    today = datetime.now()
    six_months_ago = today - timedelta(days=180)  # 6 months
    eighteen_months_ago = today - timedelta(days=540)  # 18 months
    
    print(f"Date thresholds:")
    print(f"  Today: {today.strftime('%Y-%m-%d')}")
    print(f"  6 months ago: {six_months_ago.strftime('%Y-%m-%d')}")
    print(f"  18 months ago: {eighteen_months_ago.strftime('%Y-%m-%d')}")
    
    # Convert date column to datetime
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    
    # Filter 1: Only include games from the last 18 months
    print(f"\nSTEP 1: Filtering games to last 18 months...")
    recent_games = df[df['Date'] >= eighteen_months_ago].copy()
    print(f"  Original games: {len(df)}")
    print(f"  Games in last 18 months: {len(recent_games)}")
    print(f"  Games excluded (older than 18 months): {len(df) - len(recent_games)}")
    
    if len(recent_games) == 0:
        print("  ERROR: No games found in the last 18 months!")
        return
    
    # Filter 2: Find teams with activity in the last 6 months
    print(f"\nSTEP 2: Finding teams with activity in last 6 months...")
    
    # Get all unique teams
    all_teams = set(recent_games['Team A'].tolist() + recent_games['Team B'].tolist())
    print(f"  Total unique teams in last 18 months: {len(all_teams)}")
    
    # Find teams with games in the last 6 months
    very_recent_games = recent_games[recent_games['Date'] >= six_months_ago]
    active_teams = set(very_recent_games['Team A'].tolist() + very_recent_games['Team B'].tolist())
    print(f"  Teams with activity in last 6 months: {len(active_teams)}")
    
    # Filter 3: Only include games involving active teams
    print(f"\nSTEP 3: Filtering games to only include active teams...")
    filtered_games = recent_games[
        (recent_games['Team A'].isin(active_teams)) & 
        (recent_games['Team B'].isin(active_teams))
    ].copy()
    
    print(f"  Games involving active teams: {len(filtered_games)}")
    print(f"  Games excluded (inactive teams): {len(recent_games) - len(filtered_games)}")
    
    # Show summary statistics
    print(f"\nFILTERING RESULTS:")
    print(f"=" * 40)
    print(f"Original games: {len(df):,}")
    print(f"Games in last 18 months: {len(recent_games):,}")
    print(f"Final filtered games: {len(filtered_games):,}")
    print(f"Games excluded: {len(df) - len(filtered_games):,}")
    print(f"Retention rate: {len(filtered_games) / len(df) * 100:.1f}%")
    
    # Show team statistics
    final_teams = set(filtered_games['Team A'].tolist() + filtered_games['Team B'].tolist())
    print(f"\nTEAM STATISTICS:")
    print(f"  Original teams: {len(set(df['Team A'].tolist() + df['Team B'].tolist()))}")
    print(f"  Teams in last 18 months: {len(all_teams)}")
    print(f"  Active teams (last 6 months): {len(active_teams)}")
    print(f"  Final teams: {len(final_teams)}")
    
    # Show date range of filtered data
    if len(filtered_games) > 0:
        min_date = filtered_games['Date'].min()
        max_date = filtered_games['Date'].max()
        print(f"\nDATE RANGE OF FILTERED DATA:")
        print(f"  Earliest game: {min_date.strftime('%Y-%m-%d')}")
        print(f"  Latest game: {max_date.strftime('%Y-%m-%d')}")
        print(f"  Span: {(max_date - min_date).days} days")
    
    # Show games by month
    print(f"\nGAMES BY MONTH (last 18 months):")
    filtered_games['YearMonth'] = filtered_games['Date'].dt.to_period('M')
    monthly_counts = filtered_games['YearMonth'].value_counts().sort_index()
    
    for month, count in monthly_counts.items():
        print(f"  {month}: {count} games")
    
    # Save filtered data
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save filtered games
    games_filename = f"arizona_u12_games_FILTERED_{timestamp}.csv"
    filtered_games.drop('YearMonth', axis=1).to_csv(games_filename, index=False, encoding='utf-8')
    print(f"\nFiltered games saved to: {games_filename}")
    
    # Create team summary
    team_summary = []
    for team in final_teams:
        team_games = filtered_games[
            (filtered_games['Team A'] == team) | (filtered_games['Team B'] == team)
        ]
        
        # Count wins, losses, ties for this team
        wins = 0
        losses = 0
        ties = 0
        
        for _, game in team_games.iterrows():
            if game['Team A'] == team:
                if game['Result A'] == 'W':
                    wins += 1
                elif game['Result A'] == 'L':
                    losses += 1
                else:
                    ties += 1
            else:  # Team B
                if game['Result B'] == 'W':
                    wins += 1
                elif game['Result B'] == 'L':
                    losses += 1
                else:
                    ties += 1
        
        team_summary.append({
            'Team Name': team,
            'Total Games': len(team_games),
            'Wins': wins,
            'Losses': losses,
            'Ties': ties,
            'Win Percentage': (wins / len(team_games) * 100) if len(team_games) > 0 else 0,
            'First Game': team_games['Date'].min().strftime('%Y-%m-%d') if len(team_games) > 0 else '',
            'Last Game': team_games['Date'].max().strftime('%Y-%m-%d') if len(team_games) > 0 else ''
        })
    
    # Save team summary
    teams_filename = f"arizona_u12_teams_FILTERED_{timestamp}.csv"
    team_df = pd.DataFrame(team_summary)
    team_df = team_df.sort_values('Total Games', ascending=False)
    team_df.to_csv(teams_filename, index=False, encoding='utf-8')
    print(f"Filtered teams saved to: {teams_filename}")
    
    # Show top teams by game count
    print(f"\nTOP 10 TEAMS BY GAME COUNT (filtered):")
    print(f"{'Team Name':<35} {'Games':<6} {'W-L-T':<12} {'Win%':<6} {'Last Game':<12}")
    print("-" * 80)
    
    for i, team in team_df.head(10).iterrows():
        name = team['Team Name'][:34] if len(team['Team Name']) > 34 else team['Team Name']
        record = f"{team['Wins']}-{team['Losses']}-{team['Ties']}"
        win_pct = f"{team['Win Percentage']:.1f}%"
        last_game = team['Last Game']
        
        print(f"{name:<35} {team['Total Games']:<6} {record:<12} {win_pct:<6} {last_game:<12}")
    
    # Save summary report
    summary = {
        "filter_date": datetime.now().isoformat(),
        "filters_applied": {
            "exclude_teams_no_activity_6_months": True,
            "only_games_last_18_months": True
        },
        "date_thresholds": {
            "six_months_ago": six_months_ago.strftime('%Y-%m-%d'),
            "eighteen_months_ago": eighteen_months_ago.strftime('%Y-%m-%d'),
            "today": today.strftime('%Y-%m-%d')
        },
        "results": {
            "original_games": len(df),
            "games_last_18_months": len(recent_games),
            "final_filtered_games": len(filtered_games),
            "games_excluded": len(df) - len(filtered_games),
            "retention_rate_percent": len(filtered_games) / len(df) * 100,
            "original_teams": len(set(df['Team A'].tolist() + df['Team B'].tolist())),
            "teams_last_18_months": len(all_teams),
            "active_teams_6_months": len(active_teams),
            "final_teams": len(final_teams)
        },
        "files_created": {
            "filtered_games": games_filename,
            "filtered_teams": teams_filename
        }
    }
    
    summary_filename = f"filtering_summary_{timestamp}.json"
    with open(summary_filename, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"Summary report saved to: {summary_filename}")
    
    print(f"\nFILTERING COMPLETE!")
    print(f"=" * 30)
    print(f"Final dataset: {len(filtered_games)} games, {len(final_teams)} teams")
    print(f"Files created: {games_filename}, {teams_filename}, {summary_filename}")
    
    return filtered_games, team_df

if __name__ == "__main__":
    filtered_games, team_summary = filter_recent_activity()
