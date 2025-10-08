#!/usr/bin/env python3
"""
AZ U12 Game History Team Matcher & Categorizer
==============================================

🔹 GOAL:
Cleanly associate teams from the AZ MASTER TEAM LIST with games from the AZ U12 Game History.
Handle naming variations, group teams under clubs, categorize unmatched teams smartly for review, 
and prepare for Strength of Schedule (SOS) scoring.

📁 Files Involved:
- AZ MALE U12 MASTER TEAM LIST.csv
- AZ MALE U12 GAME HISTORY LAST 18 MONTHS.csv

✅ Goals:
- Match game history team names to master list teams — including fuzzy matching and club/team variations
- Group unmatched teams into categories: AZ_2014_PROBABLE, OUT_OF_STATE, AGE_MISMATCH, or UNKNOWN_MISC
- Prepare clean Matched_Games.csv and Unmatched_Teams_Log.csv for review and SOS scoring
"""

import pandas as pd
import re
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from collections import Counter
import os
from datetime import datetime

# ========== CONFIGURATION ========== #
FUZZY_MATCH_THRESHOLD = 90  # Configurable threshold for fuzzy matching

# Regex patterns for categorization
AGE_MISMATCH_PATTERN = r'\b(2013|2015|13|15|u13|u15|14g|girls)\b'
OUT_OF_STATE_PATTERN = r'\b(ca|nv|tx|nm|co|wa|ut|or|dc|pr|hi|ak|can|mexico|bc|ab)\b'

# Output file names
MATCHED_GAMES_FILE = "Matched_Games.csv"
UNMATCHED_TEAMS_FILE = "Unmatched_Teams_Log.csv"
CONFLICTING_MATCH_FILE = "Conflicting_Match_Log.csv"
MATCH_SUMMARY_FILE = "match_summary.txt"

def normalize_name(name):
    """Normalize team names for consistent matching"""
    if pd.isnull(name) or not isinstance(name, str):
        return ""
    
    # Convert to lowercase and remove punctuation
    name = name.lower()
    name = re.sub(r"[^a-z0-9 ]", "", name)  # remove punctuation
    name = re.sub(r"\s+", " ", name).strip()  # normalize spaces
    return name

def categorize_unmatched(team_name):
    """Categorize unmatched teams based on name patterns"""
    if not isinstance(team_name, str):
        return "UNKNOWN_MISC"
    
    name = team_name.lower()
    
    # Check for age mismatches
    if re.search(AGE_MISMATCH_PATTERN, name):
        return "AGE_MISMATCH"
    
    # Check for out-of-state teams
    if re.search(OUT_OF_STATE_PATTERN, name):
        return "OUT_OF_STATE"
    
    return "UNKNOWN_MISC"

def match_team_to_master(team_name, master_df, fuzzy_threshold=FUZZY_MATCH_THRESHOLD):
    """Match a team name to the master list using exact and fuzzy matching"""
    if not team_name or pd.isnull(team_name):
        return None, "EMPTY"
    
    normalized_name = normalize_name(team_name)
    
    # Try exact match first
    exact_matches = master_df[master_df["NormalizedTeam"] == normalized_name]
    if not exact_matches.empty:
        return exact_matches.iloc[0]["Team Name"], "EXACT"
    
    # Try fuzzy match
    all_master_names = master_df["NormalizedTeam"].tolist()
    if normalized_name in all_master_names:
        return None, "NO_MATCH"
    
    match, score = process.extractOne(normalized_name, all_master_names)
    if score >= fuzzy_threshold:
        # Find the original team name for the fuzzy match
        fuzzy_matches = master_df[master_df["NormalizedTeam"] == match]
        if not fuzzy_matches.empty:
            return fuzzy_matches.iloc[0]["Team Name"], "FUZZY"
    
    return None, "NO_MATCH"

def analyze_team_appearances(games_df, team_column):
    """Analyze how many times each team appears and their opponents"""
    team_stats = {}
    
    for _, row in games_df.iterrows():
        team = row[team_column]
        opponent_col = "Team B" if team_column == "Team A" else "Team A"
        opponent = row[opponent_col]
        
        if team not in team_stats:
            team_stats[team] = {
                'appearances': 0,
                'opponents': []
            }
        
        team_stats[team]['appearances'] += 1
        team_stats[team]['opponents'].append(opponent)
    
    # Get top 3 opponents for each team
    for team in team_stats:
        opponent_counts = Counter(team_stats[team]['opponents'])
        team_stats[team]['top_opponents'] = [opp for opp, count in opponent_counts.most_common(3)]
    
    return team_stats

def main():
    """Main function to run the team matching and categorization process"""
    
    print("AZ U12 Game History Team Matcher & Categorizer")
    print("=" * 60)
    print(f"Fuzzy Match Threshold: {FUZZY_MATCH_THRESHOLD}%")
    print()
    
    # ========== STEP 1: LOAD DATA ========== #
    print("Loading data files...")
    
    try:
        master_df = pd.read_csv("AZ MALE U12 MASTER TEAM LIST.csv")
        games_df = pd.read_csv("AZ MALE U12 GAME HISTORY LAST 18 MONTHS .csv")
        print(f"+ Loaded {len(master_df)} teams from master list")
        print(f"+ Loaded {len(games_df)} games from game history")
    except FileNotFoundError as e:
        print(f"- Error loading files: {e}")
        return
    except Exception as e:
        print(f"- Error processing files: {e}")
        return
    
    # Normalize column names
    games_df.columns = games_df.columns.str.strip()
    
    # ========== STEP 2: NORMALIZE TEAM NAMES FOR MATCHING ========== #
    print("\nNormalizing team names...")
    
    master_df["NormalizedTeam"] = master_df["Team Name"].apply(normalize_name)
    master_df["NormalizedClub"] = master_df["Club"].fillna("").apply(normalize_name)
    games_df["Team A Normalized"] = games_df["Team A"].apply(normalize_name)
    games_df["Team B Normalized"] = games_df["Team B"].apply(normalize_name)
    
    print("+ Team names normalized")
    
    # ========== STEP 3: MATCH TEAMS ========== #
    print("\nMatching teams to master list...")
    
    # Match Team A
    print("  Matching Team A...")
    team_a_matches = []
    team_a_match_types = []
    
    for team_name in games_df["Team A"]:
        match_result, match_type = match_team_to_master(team_name, master_df)
        team_a_matches.append(match_result)
        team_a_match_types.append(match_type)
    
    games_df["Team A Match"] = team_a_matches
    games_df["Team A Match Type"] = team_a_match_types
    
    # Match Team B
    print("  Matching Team B...")
    team_b_matches = []
    team_b_match_types = []
    
    for team_name in games_df["Team B"]:
        match_result, match_type = match_team_to_master(team_name, master_df)
        team_b_matches.append(match_result)
        team_b_match_types.append(match_type)
    
    games_df["Team B Match"] = team_b_matches
    games_df["Team B Match Type"] = team_b_match_types
    
    print("+ Team matching completed")
    
    # ========== STEP 4: CHECK FOR CONFLICTING MATCHES ========== #
    print("\nChecking for conflicting matches...")
    
    conflicting_matches = []
    
    # Get all unique teams that appear in both Team A and Team B
    all_teams = set(games_df["Team A"].tolist() + games_df["Team B"].tolist())
    
    for team in all_teams:
        team_a_games = games_df[games_df["Team A"] == team]
        team_b_games = games_df[games_df["Team B"] == team]
        
        if not team_a_games.empty and not team_b_games.empty:
            team_a_match = team_a_games["Team A Match"].iloc[0]
            team_b_match = team_b_games["Team B Match"].iloc[0]
            
            if team_a_match != team_b_match:
                conflicting_matches.append({
                    "Team Name": team,
                    "Team A Match": team_a_match,
                    "Team B Match": team_b_match,
                    "Team A Match Type": team_a_games["Team A Match Type"].iloc[0],
                    "Team B Match Type": team_b_games["Team B Match Type"].iloc[0]
                })
    
    if conflicting_matches:
        conflicting_df = pd.DataFrame(conflicting_matches)
        conflicting_df.to_csv(CONFLICTING_MATCH_FILE, index=False)
        print(f"! Found {len(conflicting_matches)} conflicting matches - saved to {CONFLICTING_MATCH_FILE}")
    else:
        print("+ No conflicting matches found")
    
    # ========== STEP 5: CATEGORIZE UNMATCHED TEAMS ========== #
    print("\nCategorizing unmatched teams...")
    
    # Get unmatched teams from both columns
    unmatched_teams = []
    
    # Team A unmatched
    unmatched_a = games_df[games_df["Team A Match"].isnull()]
    for _, row in unmatched_a.iterrows():
        unmatched_teams.append({
            "Unmatched Team": row["Team A"],
            "Column": "Team A",
            "Category": categorize_unmatched(row["Team A"])
        })
    
    # Team B unmatched
    unmatched_b = games_df[games_df["Team B Match"].isnull()]
    for _, row in unmatched_b.iterrows():
        unmatched_teams.append({
            "Unmatched Team": row["Team B"],
            "Column": "Team B",
            "Category": categorize_unmatched(row["Team B"])
        })
    
    # Analyze appearances and opponents for unmatched teams
    team_appearances = analyze_team_appearances(games_df, "Team A")
    team_appearances.update(analyze_team_appearances(games_df, "Team B"))
    
    # Add appearance data to unmatched teams
    for team_data in unmatched_teams:
        team_name = team_data["Unmatched Team"]
        if team_name in team_appearances:
            team_data["Appearances"] = team_appearances[team_name]["appearances"]
            team_data["Top Opponents"] = ", ".join(team_appearances[team_name]["top_opponents"])
        else:
            team_data["Appearances"] = 0
            team_data["Top Opponents"] = ""
    
    # Create unmatched teams DataFrame
    unmatched_df = pd.DataFrame(unmatched_teams)
    unmatched_df = unmatched_df.drop_duplicates(subset=["Unmatched Team"])
    unmatched_df = unmatched_df.sort_values(["Category", "Appearances"], ascending=[True, False])
    
    # Save unmatched teams log
    unmatched_df.to_csv(UNMATCHED_TEAMS_FILE, index=False)
    
    # ========== STEP 6: GENERATE SUMMARY STATISTICS ========== #
    print("\nGenerating summary statistics...")
    
    # Count match types
    total_games = len(games_df)
    exact_matches_a = len(games_df[games_df["Team A Match Type"] == "EXACT"])
    fuzzy_matches_a = len(games_df[games_df["Team A Match Type"] == "FUZZY"])
    no_matches_a = len(games_df[games_df["Team A Match Type"] == "NO_MATCH"])
    
    exact_matches_b = len(games_df[games_df["Team B Match Type"] == "EXACT"])
    fuzzy_matches_b = len(games_df[games_df["Team B Match Type"] == "FUZZY"])
    no_matches_b = len(games_df[games_df["Team B Match Type"] == "NO_MATCH"])
    
    # Calculate percentages
    exact_pct_a = (exact_matches_a / total_games) * 100
    fuzzy_pct_a = (fuzzy_matches_a / total_games) * 100
    no_match_pct_a = (no_matches_a / total_games) * 100
    
    exact_pct_b = (exact_matches_b / total_games) * 100
    fuzzy_pct_b = (fuzzy_matches_b / total_games) * 100
    no_match_pct_b = (no_matches_b / total_games) * 100
    
    # Unmatched team categories
    unmatched_summary = unmatched_df["Category"].value_counts()
    
    # ========== STEP 7: SAVE OUTPUT FILES ========== #
    print("\nSaving output files...")
    
    # Save matched games
    games_df.to_csv(MATCHED_GAMES_FILE, index=False)
    print(f"+ Saved matched games to {MATCHED_GAMES_FILE}")
    
    # Save unmatched teams log
    print(f"+ Saved unmatched teams log to {UNMATCHED_TEAMS_FILE}")
    
    # ========== STEP 8: GENERATE SUMMARY REPORT ========== #
    print("\nGenerating summary report...")
    
    summary_report = f"""
AZ U12 Team Matching & Categorization Report
============================================
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

MATCHING STATISTICS
---------------------
Total Games Processed: {total_games:,}

Team A Matching:
  + Exact Matches: {exact_matches_a:,} ({exact_pct_a:.1f}%)
  ? Fuzzy Matches: {fuzzy_matches_a:,} ({fuzzy_pct_a:.1f}%)
  ! No Matches: {no_matches_a:,} ({no_match_pct_a:.1f}%)

Team B Matching:
  + Exact Matches: {exact_matches_b:,} ({exact_pct_b:.1f}%)
  ? Fuzzy Matches: {fuzzy_matches_b:,} ({fuzzy_pct_b:.1f}%)
  ! No Matches: {no_matches_b:,} ({no_match_pct_b:.1f}%)

OVERALL MATCHING RATE
------------------------
Average Exact Match Rate: {(exact_pct_a + exact_pct_b) / 2:.1f}%
Average Fuzzy Match Rate: {(fuzzy_pct_a + fuzzy_pct_b) / 2:.1f}%
Average No Match Rate: {(no_match_pct_a + no_match_pct_b) / 2:.1f}%

UNMATCHED TEAMS BREAKDOWN
-----------------------------
Total Unique Unmatched Teams: {len(unmatched_df):,}

"""
    
    for category, count in unmatched_summary.items():
        summary_report += f"  - {category}: {count:,}\n"
    
    summary_report += f"""
OUTPUT FILES
--------------
+ {MATCHED_GAMES_FILE} - All games with match results
+ {UNMATCHED_TEAMS_FILE} - Unmatched teams with categories
"""
    
    if conflicting_matches:
        summary_report += f"! {CONFLICTING_MATCH_FILE} - Conflicting match cases\n"
    
    summary_report += f"""
CONFIGURATION USED
---------------------
Fuzzy Match Threshold: {FUZZY_MATCH_THRESHOLD}%
Age Mismatch Pattern: {AGE_MISMATCH_PATTERN}
Out-of-State Pattern: {OUT_OF_STATE_PATTERN}

PROCESSING COMPLETE!
"""
    
    # Save summary report
    with open(MATCH_SUMMARY_FILE, 'w', encoding='utf-8') as f:
        f.write(summary_report)
    
    print(f"+ Summary report saved to {MATCH_SUMMARY_FILE}")
    
    # Print summary to console
    print("\n" + "="*60)
    print("SUMMARY REPORT")
    print("="*60)
    print(summary_report)
    
    print(f"\nTeam matching and categorization complete!")
    print(f"Check the following files:")
    print(f"   - {MATCHED_GAMES_FILE}")
    print(f"   - {UNMATCHED_TEAMS_FILE}")
    if conflicting_matches:
        print(f"   - {CONFLICTING_MATCH_FILE}")
    print(f"   - {MATCH_SUMMARY_FILE}")

if __name__ == "__main__":
    main()
