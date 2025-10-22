import streamlit as st
import pandas as pd
import os
import glob
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Page configuration
st.set_page_config(
    page_title="Soccer Rankings Dashboard",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        color: #1f77b4;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .team-card {
        background-color: #ffffff;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 0.5rem 0;
    }
    .rank-badge {
        background-color: #1f77b4;
        color: white;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

def load_game_history_data():
    """Load the combined game history data"""
    try:
        # Try to load the combined game history
        game_files = [
            "data/Game History u10 and u11.csv",
            "data/processed/u10/U10_Enhanced.csv",
            "data/processed/u11/U11_Enhanced.csv"
        ]
        
        for file_path in game_files:
            if os.path.exists(file_path):
                df = pd.read_csv(file_path)
                # Clean column names
                df.columns = df.columns.str.strip()
                return df
        
        return None
    except Exception as e:
        st.error(f"Error loading game history: {str(e)}")
        return None

def get_team_game_history(team_name, game_history_df):
    """Get game history for a specific team"""
    if game_history_df is None:
        return None
    
    # Find games where team is either Team A or Team B
    team_a_games = game_history_df[game_history_df['Team A '].str.contains(team_name, case=False, na=False)]
    team_b_games = game_history_df[game_history_df['Team B '].str.contains(team_name, case=False, na=False)]
    
    # Combine and process games
    all_games = []
    
    # Process Team A games
    for _, game in team_a_games.iterrows():
        all_games.append({
            'Date': game.get('Date ', ''),
            'Team': team_name,
            'Opponent': game.get('Team B ', ''),
            'Score_For': game.get('Score A ', ''),
            'Score_Against': game.get('Score B ', ''),
            'Result': game.get('Team A Result', ''),
            'Event': game.get('Event', ''),
            'Was_Team_A': True
        })
    
    # Process Team B games
    for _, game in team_b_games.iterrows():
        all_games.append({
            'Date': game.get('Date ', ''),
            'Team': team_name,
            'Opponent': game.get('Team A ', ''),
            'Score_For': game.get('Score B ', ''),
            'Score_Against': game.get('Score A ', ''),
            'Result': 'Win' if game.get('Team A Result', '') == 'Loss' else 'Loss' if game.get('Team A Result', '') == 'Win' else 'Tie',
            'Event': game.get('Event', ''),
            'Was_Team_A': False
        })
    
    if all_games:
        df = pd.DataFrame(all_games)
        # Sort by date
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.sort_values('Date', ascending=False)
        return df
    
    return None

def load_rankings_data(age_group, gender, state="USA"):
    """Load rankings data based on selection"""
    try:
        if state == "USA" or state == "National":
            # Load national rankings
            file_pattern = f"data/output/National_U{age_group}_*_Rankings_CROSS_AGE.csv"
            files = glob.glob(file_pattern)
            
            if not files:
                # Try alternative pattern
                file_pattern = f"data/output/National_U{age_group}_Rankings_CROSS_AGE.csv"
                files = glob.glob(file_pattern)
            
            if files:
                df = pd.read_csv(files[0])
                return df, "National"
            else:
                st.error(f"No national rankings found for U{age_group}")
                return None, None
        else:
            # Load state rankings
            file_pattern = f"data/output/U{age_group}_Rankings_{state}_CROSS_AGE.csv"
            files = glob.glob(file_pattern)
            
            if not files:
                # Try alternative pattern
                file_pattern = f"data/output/U{age_group}_M_Rankings_{state}.csv"
                files = glob.glob(file_pattern)
            
            if files:
                df = pd.read_csv(files[0])
                return df, state
            else:
                st.error(f"No rankings found for {state} U{age_group}")
                return None, None
                
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None, None

def get_available_states():
    """Get list of available states from output files"""
    try:
        # Look for both CROSS_AGE and regular state files
        patterns = [
            "data/output/U*_Rankings_*_CROSS_AGE.csv",
            "data/output/U*_M_Rankings_*.csv",
            "data/output/U*_Rankings_*.csv"
        ]
        
        states = set()
        
        for pattern in patterns:
            files = glob.glob(pattern)
            for file in files:
                # Extract state from filename
                filename = os.path.basename(file)
                parts = filename.split("_")
                
                # Handle different filename patterns
                if "_CROSS_AGE.csv" in filename:
                    # Pattern: U10_Rankings_AZ_CROSS_AGE.csv
                    if len(parts) >= 4:
                        state = parts[-2]  # Second to last part
                        if state != "CROSS" and len(state) == 2:
                            states.add(state)
                elif "_M_Rankings_" in filename:
                    # Pattern: U10_M_Rankings_AZ.csv
                    if len(parts) >= 4:
                        state = parts[-1].replace(".csv", "")
                        if len(state) == 2:
                            states.add(state)
                else:
                    # Pattern: U10_Rankings_AZ.csv
                    if len(parts) >= 3:
                        state = parts[-1].replace(".csv", "")
                        if len(state) == 2:
                            states.add(state)
        
        return sorted(list(states))
    except Exception as e:
        print(f"Error getting states: {e}")
        return ["AZ", "CA", "TX", "FL", "NY", "OH", "IL", "PA", "NJ", "MI"]  # Fallback

def show_team_detail_page(team_name, team_data, game_history_df):
    """Show detailed team page with game history"""
    st.markdown('<h1 class="main-header">⚽ Team Details</h1>', unsafe_allow_html=True)
    
    # Back button
    if st.button("← Back to Rankings"):
        st.session_state.page = "rankings"
        st.rerun()
    
    # Team header
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown(f"## {team_name}")
        st.markdown(f"**State:** {team_data.get('State', 'Unknown')}")
        st.markdown(f"**National Rank:** #{team_data.get('National_Rank', 'N/A')}")
    
    with col2:
        st.metric("Power Score", f"{team_data.get('Power_Score', 0):.3f}")
        st.metric("Win %", f"{team_data.get('Win_Percentage', 0):.3f}")
    
    with col3:
        st.metric("Games Played", f"{team_data.get('Games_Played', 0)}")
        st.metric("SOS Score", f"{team_data.get('SOS_Score', 0):.3f}")
    
    # Get team game history
    team_games = get_team_game_history(team_name, game_history_df)
    
    if team_games is not None and len(team_games) > 0:
        st.markdown("---")
        st.header("📊 Game History")
        
        # Game statistics
        col1, col2, col3, col4 = st.columns(4)
        
        wins = len(team_games[team_games['Result'] == 'Win'])
        losses = len(team_games[team_games['Result'] == 'Loss'])
        ties = len(team_games[team_games['Result'] == 'Tie'])
        total_games = len(team_games)
        
        with col1:
            st.metric("Wins", wins)
        with col2:
            st.metric("Losses", losses)
        with col3:
            st.metric("Ties", ties)
        with col4:
            st.metric("Win %", f"{(wins/total_games*100):.1f}%" if total_games > 0 else "0%")
        
        # Recent games chart
        st.subheader("📈 Recent Performance")
        
        # Create performance trend
        recent_games = team_games.head(20)  # Last 20 games
        recent_games['Cumulative_Wins'] = (recent_games['Result'] == 'Win').cumsum()
        recent_games['Cumulative_Games'] = range(1, len(recent_games) + 1)
        recent_games['Win_Percentage'] = recent_games['Cumulative_Wins'] / recent_games['Cumulative_Games']
        
        fig = px.line(
            recent_games, 
            x='Cumulative_Games', 
            y='Win_Percentage',
            title=f"{team_name} - Win Percentage Trend (Last 20 Games)",
            labels={'Cumulative_Games': 'Games Played', 'Win_Percentage': 'Win Percentage'}
        )
        fig.update_layout(yaxis=dict(range=[0, 1]))
        st.plotly_chart(fig, use_container_width=True)
        
        # Game history table
        st.subheader("🎮 Game History")
        
        # Format the game history for display
        display_games = team_games.copy()
        display_games['Date'] = display_games['Date'].dt.strftime('%Y-%m-%d')
        
        # Add result color coding
        def color_result(val):
            if val == 'Win':
                return 'background-color: #d4edda'
            elif val == 'Loss':
                return 'background-color: #f8d7da'
            else:
                return 'background-color: #fff3cd'
        
        styled_games = display_games[['Date', 'Opponent', 'Score_For', 'Score_Against', 'Result', 'Event']].style.applymap(
            color_result, subset=['Result']
        )
        
        st.dataframe(
            styled_games,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Date": "Date",
                "Opponent": "Opponent",
                "Score_For": "Score For",
                "Score_Against": "Score Against", 
                "Result": "Result",
                "Event": "Event"
            }
        )
        
        # Download game history
        csv_data = display_games.to_csv(index=False)
        st.download_button(
            label="Download Game History as CSV",
            data=csv_data,
            file_name=f"{team_name}_Game_History.csv",
            mime="text/csv"
        )
        
    else:
        st.warning("No game history found for this team.")
    
    # Team analysis
    st.markdown("---")
    st.header("📈 Team Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Strengths")
        if team_data.get('Power_Score', 0) > 0.6:
            st.success("High Power Score - Strong overall performance")
        if team_data.get('SOS_Score', 0) > 0.5:
            st.success("Strong Schedule - Plays tough opponents")
        if team_data.get('Win_Percentage', 0) > 0.7:
            st.success("High Win Rate - Consistent victories")
    
    with col2:
        st.subheader("Areas for Improvement")
        if team_data.get('Power_Score', 0) < 0.4:
            st.warning("Low Power Score - Overall performance needs improvement")
        if team_data.get('SOS_Score', 0) < 0.3:
            st.warning("Weak Schedule - Consider playing stronger opponents")
        if team_data.get('Win_Percentage', 0) < 0.3:
            st.warning("Low Win Rate - Focus on fundamental improvements")

def main():
    # Initialize session state
    if 'page' not in st.session_state:
        st.session_state.page = "rankings"
    if 'selected_team' not in st.session_state:
        st.session_state.selected_team = None
    
    # Load game history data once
    if 'game_history_df' not in st.session_state:
        with st.spinner("Loading game history data..."):
            st.session_state.game_history_df = load_game_history_data()
    
    # Show team detail page if a team is selected
    if st.session_state.page == "team_detail" and st.session_state.selected_team:
        show_team_detail_page(
            st.session_state.selected_team['name'], 
            st.session_state.selected_team['data'],
            st.session_state.game_history_df
        )
        return
    
    # Main rankings page
    st.markdown('<h1 class="main-header">⚽ Soccer Rankings Dashboard</h1>', unsafe_allow_html=True)
    
    # Sidebar for filters
    with st.sidebar:
        st.header("🎯 Filter Options")
        
        # Age Group Selection
        age_group = st.selectbox(
            "Age Group",
            options=["10", "11", "12", "13", "14", "15", "16", "17", "18"],
            index=0,
            help="Select the age group for rankings"
        )
        
        # Gender Selection
        gender = st.selectbox(
            "Gender",
            options=["Male", "Female"],
            index=0,
            help="Select gender for rankings"
        )
        
        # State/National Selection
        available_states = get_available_states()
        scope_options = ["USA (National)"] + available_states
        
        # Debug info (remove this in production)
        with st.expander("🔧 Debug Info"):
            st.write(f"Available states: {available_states}")
            st.write(f"Total state files found: {len(available_states)}")
        
        selected_scope = st.selectbox(
            "Scope",
            options=scope_options,
            index=0,
            help="Select national rankings or specific state"
        )
        
        # Extract state from selection
        if selected_scope == "USA (National)":
            state = "USA"
        else:
            state = selected_scope
    
    # Load data
    with st.spinner("Loading rankings data..."):
        df, scope_name = load_rankings_data(age_group, gender, state)
    
    if df is None:
        st.warning("No data available for the selected criteria. Please try different options.")
        return
    
    # Main content
    st.success(f"✅ Loaded {len(df)} teams for U{age_group} {gender} {scope_name} rankings")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total Teams",
            value=f"{len(df):,}",
            help="Total number of teams ranked"
        )
    
    with col2:
        avg_power = df['Power_Score'].mean()
        st.metric(
            label="Avg Power Score",
            value=f"{avg_power:.3f}",
            help="Average power score across all teams"
        )
    
    with col3:
        if 'Cross_Age_Games' in df.columns:
            total_cross_age = df['Cross_Age_Games'].sum()
            st.metric(
                label="Cross-Age Games",
                value=f"{total_cross_age:,}",
                help="Total cross-age games played"
            )
        else:
            st.metric(
                label="Games Played",
                value=f"{df['Games_Played'].sum():,}",
                help="Total games played"
            )
    
    with col4:
        if 'Cross_State_Games' in df.columns:
            total_cross_state = df['Cross_State_Games'].sum()
            st.metric(
                label="Cross-State Games",
                value=f"{total_cross_state:,}",
                help="Total cross-state games played"
            )
        else:
            avg_sos = df['SOS_Score'].mean()
            st.metric(
                label="Avg SOS Score",
                value=f"{avg_sos:.3f}",
                help="Average strength of schedule"
            )
    
    # Search functionality
    st.header("🔍 Search Teams")
    search_term = st.text_input(
        "Search for a team:",
        placeholder="Enter team name...",
        help="Search for specific teams in the rankings"
    )
    
    # Filter data based on search
    if search_term:
        search_mask = df['Team'].str.contains(search_term, case=False, na=False)
        filtered_df = df[search_mask]
        st.info(f"Found {len(filtered_df)} teams matching '{search_term}'")
    else:
        filtered_df = df
    
    # Display options
    display_option = st.radio(
        "Display Options:",
        options=["Top 25 Teams", "Top 50 Teams", "Top 100 Teams", "All Teams"],
        horizontal=True
    )
    
    # Determine number of teams to show
    if display_option == "Top 25 Teams":
        show_df = filtered_df.head(25)
    elif display_option == "Top 50 Teams":
        show_df = filtered_df.head(50)
    elif display_option == "Top 100 Teams":
        show_df = filtered_df.head(100)
    else:
        show_df = filtered_df
    
    # Rankings table
    st.header(f"🏆 {scope_name} U{age_group} {gender} Rankings")
    
    # Prepare columns for display
    display_columns = ['Team', 'State', 'Power_Score', 'Win_Percentage', 'Games_Played']
    
    # Add additional columns if available
    if 'SOS_Score' in df.columns:
        display_columns.append('SOS_Score')
    if 'Cross_Age_Games' in df.columns:
        display_columns.append('Cross_Age_Games')
    if 'Cross_State_Games' in df.columns:
        display_columns.append('Cross_State_Games')
    
    # Create ranking column
    show_df_display = show_df.copy()
    show_df_display['Rank'] = range(1, len(show_df_display) + 1)
    display_columns = ['Rank'] + display_columns
    
    # Format the dataframe
    formatted_df = show_df_display[display_columns].copy()
    
    # Format numeric columns
    if 'Power_Score' in formatted_df.columns:
        formatted_df['Power_Score'] = formatted_df['Power_Score'].round(3)
    if 'Win_Percentage' in formatted_df.columns:
        formatted_df['Win_Percentage'] = formatted_df['Win_Percentage'].round(3)
    if 'SOS_Score' in formatted_df.columns:
        formatted_df['SOS_Score'] = formatted_df['SOS_Score'].round(3)
    
    # Create clickable team names
    st.subheader("🏆 Click on any team name to view detailed stats and game history")
    
    # Display teams with clickable names
    for i, row in show_df_display.iterrows():
        col1, col2, col3, col4, col5 = st.columns([1, 3, 1, 1, 1])
        
        with col1:
            st.write(f"**#{row['Rank']}**")
        
        with col2:
            if st.button(f"🔍 {row['Team']}", key=f"team_{i}", help=f"Click to view {row['Team']} details"):
                st.session_state.selected_team = {
                    'name': row['Team'],
                    'data': row.to_dict()
                }
                st.session_state.page = "team_detail"
                st.rerun()
        
        with col3:
            st.write(f"{row['Power_Score']:.3f}")
        
        with col4:
            st.write(f"{row['Win_Percentage']:.3f}")
        
        with col5:
            st.write(f"{row['Games_Played']}")
    
    # Also show the full table for reference
    st.subheader("📊 Full Rankings Table")
    st.dataframe(
        formatted_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Rank": st.column_config.NumberColumn(
                "Rank",
                help="National/State ranking position",
                format="%d"
            ),
            "Team": st.column_config.TextColumn(
                "Team Name",
                help="Team name"
            ),
            "State": st.column_config.TextColumn(
                "State",
                help="Team's state"
            ),
            "Power_Score": st.column_config.NumberColumn(
                "Power Score",
                help="Overall power score (0-1)",
                format="%.3f"
            ),
            "Win_Percentage": st.column_config.NumberColumn(
                "Win %",
                help="Win percentage",
                format="%.3f"
            ),
            "Games_Played": st.column_config.NumberColumn(
                "Games",
                help="Total games played",
                format="%d"
            ),
            "SOS_Score": st.column_config.NumberColumn(
                "SOS Score",
                help="Strength of schedule",
                format="%.3f"
            ),
            "Cross_Age_Games": st.column_config.NumberColumn(
                "Cross-Age",
                help="Cross-age games played",
                format="%d"
            ),
            "Cross_State_Games": st.column_config.NumberColumn(
                "Cross-State",
                help="Cross-state games played",
                format="%d"
            )
        }
    )
    
    # Download option
    st.header("📥 Download Data")
    
    # Download filtered data (what's currently displayed)
    csv_data_filtered = formatted_df.to_csv(index=False)
    st.download_button(
        label="Download Filtered Rankings as CSV",
        data=csv_data_filtered,
        file_name=f"U{age_group}_{gender}_{scope_name}_Rankings_Filtered.csv",
        mime="text/csv",
        help="Downloads only the teams currently displayed"
    )
    
    # Download complete dataset (all columns)
    csv_data_complete = show_df_display.to_csv(index=False)
    st.download_button(
        label="Download Complete Rankings as CSV (All Columns)",
        data=csv_data_complete,
        file_name=f"U{age_group}_{gender}_{scope_name}_Rankings_Complete.csv",
        mime="text/csv",
        help="Downloads all teams with all available columns"
    )
    
    # Footer
    st.markdown("---")
    st.markdown(
        "**Soccer Rankings Dashboard** | Powered by V5.3E Enhanced Algorithm | "
        "Cross-Age & Cross-State Support | Default Strength for Unknown Opponents"
    )

if __name__ == "__main__":
    main()
