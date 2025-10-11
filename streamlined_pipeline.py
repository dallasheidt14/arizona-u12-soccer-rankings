"""
Streamlined Data Conversion Pipeline for Multiple Age Groups
Converts existing match data to proper format and generates rankings
"""
import pandas as pd
import os
from utils.team_normalizer import canonicalize_team_name

def extract_club_name(team_name):
    """Extract club name from team name using U12-style patterns"""
    team_lower = team_name.lower()
    
    # U12-style club patterns (matching the working U12 format)
    club_patterns = [
        ('fc elite arizona', 'FC Elite Arizona'),
        ('arizona soccer club', 'Arizona Soccer Club'),
        ('phoenix premier', 'Phoenix Premier'),
        ('rsl-az', 'RSL-AZ'),
        ('next level soccer', 'Next Level Soccer'),
        ('tuzos', 'Tuzos'),
        ('legends fc', 'Legends FC'),
        ('dynamos sc', 'Dynamos SC'),
        ('scottsdale', 'Scottsdale'),
        ('mesa soccer club', 'Mesa Soccer Club'),
        ('chandler soccer club', 'Chandler Soccer Club'),
        ('glendale soccer club', 'Glendale Soccer Club'),
        ('tempe soccer club', 'Tempe Soccer Club'),
        ('peoria soccer club', 'Peoria Soccer Club'),
        ('surprise soccer club', 'Surprise Soccer Club'),
        ('gilbert soccer club', 'Gilbert Soccer Club'),
        ('avondale soccer club', 'Avondale Soccer Club'),
        ('goodyear soccer club', 'Goodyear Soccer Club'),
        ('buckeye soccer club', 'Buckeye Soccer Club'),
        ('casa grande soccer club', 'Casa Grande Soccer Club'),
        ('fountain hills soccer club', 'Fountain Hills Soccer Club'),
        ('fc tucson youth soccer', 'FC Tucson Youth Soccer'),
        ('phoenix united futbol club', 'Phoenix United Futbol Club')
    ]
    
    for pattern, club_name in club_patterns:
        if pattern in team_lower:
            return club_name
    
    # Fallback to first word capitalized
    return team_name.split()[0].title() if team_name.split() else team_name

def convert_age_group_data(age_group):
    """Convert existing age group data to proper format"""
    
    # Input file paths
    input_file = f"gold/Matched_Games_{age_group}.csv"
    output_file = f"gold/Matched_Games_AZ_BOYS_{age_group}.csv"
    
    print(f"Converting {age_group} data...")
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"ERROR: Input file not found: {input_file}")
        return False
    
    # Read the existing data
    df = pd.read_csv(input_file)
    print(f"Loaded {len(df)} matches from {input_file}")
    
    # Convert to the expected format with proper team name formatting
    converted_matches = []
    
    for _, row in df.iterrows():
        # Format team names to match U12 format: just the team name, no club name
        team_a_name = canonicalize_team_name(row["Team"])
        team_b_name = canonicalize_team_name(row["Opponent"])
        
        # Use team names as-is, don't add club names (U12 style)
        team_a_full = team_a_name
        team_b_full = team_b_name
        
        match = {
            "Team A": team_a_full,
            "Team B": team_b_full,
            "Score A": row["TeamScore"],
            "Score B": row["OpponentScore"],
            "Date": row["Date"],
            "Competition": row["Competition"],
            "SourceURL": row.get("TeamURL", "")
        }
        converted_matches.append(match)
    
    # Save in the expected format
    converted_df = pd.DataFrame(converted_matches)
    converted_df.to_csv(output_file, index=False)
    
    print(f"SUCCESS: Converted and saved {len(converted_matches)} matches to {output_file}")
    
    # Show statistics
    all_teams = set(converted_df["Team A"].unique()) | set(converted_df["Team B"].unique())
    print(f"Total unique teams: {len(all_teams)}")
    
    return True

def create_master_team_list(age_group):
    """Create master team list from converted match data"""
    
    # File paths
    games_path = f"gold/Matched_Games_AZ_BOYS_{age_group}.csv"
    output_path = f"bronze/AZ MALE {age_group.lower()} MASTER TEAM LIST.csv"
    
    print(f"Creating master team list for {age_group}...")
    
    # Read games data
    df_games = pd.read_csv(games_path)
    print(f"Loaded {len(df_games)} games from {games_path}")

    # Get all unique teams
    all_teams = set(df_games['Team A'].unique()) | set(df_games['Team B'].unique())
    print(f"Found {len(all_teams)} unique teams")

    team_stats = {}
    for idx, team_name in enumerate(sorted(all_teams)):
        team_canonical = team_name.lower() 

        team_games = df_games[
            (df_games['Team A'].str.lower() == team_canonical) | 
            (df_games['Team B'].str.lower() == team_canonical)
        ]

        wins = 0
        losses = 0
        ties = 0
        goals_for = 0
        goals_against = 0

        for _, game in team_games.iterrows():
            team_a_lower = game['Team A'].lower()
            team_b_lower = game['Team B'].lower()

            if team_a_lower == team_canonical:
                team_score = game['Score A']
                opp_score = game['Score B']
            elif team_b_lower == team_canonical:
                team_score = game['Score B']
                opp_score = game['Score A']
            else:
                continue

            goals_for += team_score if pd.notna(team_score) else 0
            goals_against += opp_score if pd.notna(opp_score) else 0

            if pd.notna(team_score) and pd.notna(opp_score):
                if team_score > opp_score:
                    wins += 1
                elif team_score < opp_score:
                    losses += 1
                else:
                    ties += 1
        
        games_played = wins + losses + ties
        win_percentage = wins / games_played if games_played > 0 else 0.0
        goal_ratio = goals_for / goals_against if goals_against > 0 else float('inf')

        team_stats[team_name] = {
            'Team ID': f"{age_group.lower()}_{idx+1:03d}",
            'Wins': wins,
            'Losses': losses,
            'Ties': ties,
            'Games Played': games_played,
            'Goals For': goals_for,
            'Goals Against': goals_against,
            'Win Percentage': win_percentage,
            'Goal Ratio': goal_ratio
        }

    # Create master team list
    master_teams = []
    for idx, team_name in enumerate(sorted(all_teams)):
        stats = team_stats.get(team_name, {})
        
        # Extract club name using U12-style patterns
        club_name = extract_club_name(team_name)
        
        # Use team name as-is (U12 style - no club name added)
        full_team_name = team_name.lower()
        
        master_team = {
            'Team Name': full_team_name,
            'Club': club_name,
            'Team ID': stats.get('Team ID', f"{age_group.lower()}_{idx+1:03d}"),
            'Wins': stats.get('Wins', 0),
            'Losses': stats.get('Losses', 0),
            'Ties': stats.get('Ties', 0),
            'Games Played': stats.get('Games Played', 0),
            'State': 'AZ',
            'Win Percentage': stats.get('Win Percentage', 0.0),
            'State Rank': idx+1,
            'Goal Ratio': stats.get('Goal Ratio', 0.0),
            'Team URL': '',
            'Gender': 'M',
            'Age Group': age_group.upper()
        }
        master_teams.append(master_team)

    df_master = pd.DataFrame(master_teams)
    df_master.to_csv(output_path, index=False)
    print(f"Saved master team list to {output_path}")
    
    # Show top teams
    print(f"\nTop 5 teams by win percentage:")
    top_teams = df_master[df_master['Games Played'] > 0].nlargest(5, 'Win Percentage')
    print(top_teams[['Team Name', 'Club', 'Games Played', 'Wins', 'Losses', 'Win Percentage']])
    
    return True

def setup_ranking_files(age_group):
    """Copy files to locations expected by ranking generator"""
    
    # Copy match data to expected location
    source_file = f"gold/Matched_Games_AZ_BOYS_{age_group}.csv"
    target_file = f"data_ingest/gold/Matched_Games_{age_group}.csv"
    
    # Create directory if needed
    os.makedirs("data_ingest/gold", exist_ok=True)
    
    # Copy file
    import shutil
    shutil.copy2(source_file, target_file)
    print(f"Copied {source_file} to {target_file}")
    
    # Copy master team list to root
    source_master = f"bronze/AZ MALE {age_group.lower()} MASTER TEAM LIST.csv"
    target_master = f"AZ MALE {age_group.lower()} MASTER TEAM LIST.csv"
    
    shutil.copy2(source_master, target_master)
    print(f"Copied {source_master} to {target_master}")
    
    return True

def process_age_group(age_group):
    """Complete pipeline for an age group"""
    
    print(f"\n{'='*50}")
    print(f"Processing {age_group} Age Group")
    print(f"{'='*50}")
    
    # Step 1: Convert data format
    if not convert_age_group_data(age_group):
        return False
    
    # Step 2: Create master team list
    if not create_master_team_list(age_group):
        return False
    
    # Step 3: Setup files for ranking generator
    if not setup_ranking_files(age_group):
        return False
    
    print(f"\nSUCCESS: {age_group} pipeline complete!")
    print(f"Ready to run: python rankings/generate_team_rankings_v53_enhanced_multi.py --division Az_Boys_{age_group}")
    
    return True

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python streamlined_pipeline.py <age_group>")
        print("Example: python streamlined_pipeline.py U11")
        sys.exit(1)
    
    age_group = sys.argv[1].upper()
    process_age_group(age_group)
