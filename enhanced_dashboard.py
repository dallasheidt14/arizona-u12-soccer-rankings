"""
Enhanced Arizona U12 Soccer Rankings Dashboard
Phase A: UI toggles, color coding, and "What changed today?" panel
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
import config

def load_data():
    """Load rankings and game history data."""
    base_path = os.path.dirname(os.path.abspath(__file__))
    
    try:
        rankings_df = pd.read_csv(f"{base_path}\\Rankings_PowerScore.csv")
        game_histories_df = pd.read_csv(f"{base_path}\\Team_Game_Histories.csv")
        
        # Convert Date column to datetime
        game_histories_df["Date"] = pd.to_datetime(game_histories_df["Date"])
        
        return rankings_df, game_histories_df
    except FileNotFoundError as e:
        st.error(f"Data files not found: {e}")
        st.stop()

def get_sorting_options():
    """Get available sorting options based on feature flags."""
    options = {
        "Power Score": "Power Score",
        "Games Played": "Games Played", 
        "Wins": "Wins",
        "Goal Differential": "Goal Differential"
    }
    
    if config.ENABLE_UI_TOGGLES:
        options.update({
            "Offensive Rating": "Goals For/Game",
            "Defensive Rating": "Goals Against/Game", 
            "SOS": "SOS"
        })
    
    return options

def create_what_changed_panel(rankings_df, game_histories_df):
    """Create the 'What changed today?' panel with calibration info."""
    if not config.ENABLE_WHAT_CHANGED:
        return None
    
    today = datetime.now().date()
    
    # Find games from today
    today_games = game_histories_df[game_histories_df["Date"].dt.date == today]
    
    # Calculate basic metrics
    new_games = len(today_games)
    total_teams = len(rankings_df)
    active_teams = len(rankings_df)  # Simplified for now
    
    # Check expectation model status
    model_status = "Advanced (Opponent-Adjusted)" if config.EXPECTATION_MODEL == "opponent_adjusted_v1" else "Simple"
    calibration_status = "Calibrated" if config.EXPECT_CALIBRATE else "Raw Values"
    
    # Create panel
    with st.container():
        st.markdown("### 📊 What Changed Today?")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("New Games", new_games)
        
        with col2:
            st.metric("Total Teams", total_teams)
        
        with col3:
            st.metric("Active Teams", active_teams)
        
        if new_games > 0:
            st.markdown(f"**Latest games:** {new_games} games played today")
            
            # Show recent games
            if not today_games.empty:
                st.markdown("**Recent Results:**")
                recent_display = today_games[["Team", "Opponent", "Goals For", "Goals Against"]].head(5)
                st.dataframe(recent_display, use_container_width=True)
        else:
            st.info("No games played today")
        
        # Model status (admin info)
        st.markdown("**Model Status:**")
        st.markdown(f"• Expectation Model: {model_status}")
        st.markdown(f"• Calibration: {calibration_status}")
        
        st.markdown(f"*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")

def get_result_color(impact_bucket):
    """Get color for result based on impact bucket."""
    if not config.ENABLE_COLOR_CODING:
        return None
    
    color_map = {
        "good": "#d4edda",      # Light green
        "neutral": "#f8f9fa",    # Light gray
        "weak": "#f8d7da"       # Light red
    }
    
    return color_map.get(impact_bucket, "#f8f9fa")

def get_result_badge(impact_bucket):
    """Get badge for result based on impact bucket."""
    if not config.ENABLE_COLOR_CODING:
        return ""
    
    badge_map = {
        "good": "↑ Above Expected",
        "neutral": "• As Expected", 
        "weak": "↓ Below Expected"
    }
    
    return badge_map.get(impact_bucket, "")

def create_rankings_table(rankings_df, game_histories_df):
    """Create enhanced rankings table with toggles and color coding."""
    
    # Sorting options
    sort_options = get_sorting_options()
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("### 🏆 Team Rankings")
    
    with col2:
        if config.ENABLE_UI_TOGGLES:
            sort_by = st.selectbox(
                "Sort by:",
                options=list(sort_options.keys()),
                index=0,
                key="sort_rankings"
            )
            
            # Apply sorting
            if sort_by in sort_options:
                sort_column = sort_options[sort_by]
                if sort_column in rankings_df.columns:
                    ascending = sort_column in ["Goals Against/Game"]  # Lower is better for defense
                    rankings_df = rankings_df.sort_values(sort_column, ascending=ascending)
    
    # Display rankings table
    display_columns = [
        "Rank", "Team", "Club", "Games Played", "Wins", "Losses", "Ties",
        "Goal Differential", "Power Score"
    ]
    
    if config.ENABLE_UI_TOGGLES:
        display_columns.extend(["Goals For/Game", "Goals Against/Game", "SOS"])
    
    # Filter columns that exist
    available_columns = [col for col in display_columns if col in rankings_df.columns]
    
    st.dataframe(
        rankings_df[available_columns],
        use_container_width=True,
        height=400
    )
    
    # Quick team lookup
    st.markdown("#### 🔍 Quick Team Lookup")
    team_names = rankings_df["Team"].tolist()
    selected_team = st.selectbox("Select a team:", team_names, key="team_lookup")
    
    if st.button("View Team Details", key="view_details"):
        st.session_state.selected_team = selected_team
        st.rerun()

def create_team_detail_view(rankings_df, game_histories_df):
    """Create detailed team view with enhanced features."""
    
    # Get selected team from session state or default
    if "selected_team" in st.session_state:
        selected_team = st.session_state.selected_team
    else:
        selected_team = rankings_df.iloc[0]["Team"]
    
    # Team selection
    team_names = rankings_df["Team"].tolist()
    selected_team = st.selectbox(
        "Select Team:",
        team_names,
        index=team_names.index(selected_team) if selected_team in team_names else 0,
        key="team_detail_select"
    )
    
    # Get team data
    team_data = rankings_df[rankings_df["Team"] == selected_team].iloc[0]
    team_games = game_histories_df[game_histories_df["Team"] == selected_team].copy()
    
    if team_games.empty:
        st.warning(f"No game history found for {selected_team}")
        return
    
    # Team info cards
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Rank", f"#{team_data.get('Rank', 'N/A')}")
    
    with col2:
        st.metric("Power Score", f"{team_data.get('Power Score', 0):.3f}")
    
    with col3:
        st.metric("Games Played", team_data.get("Games Played", 0))
    
    with col4:
        win_pct = (team_data.get("Wins", 0) / team_data.get("Games Played", 1)) * 100
        st.metric("Win %", f"{win_pct:.1f}%")
    
    with col5:
        st.metric("Goal Diff", team_data.get("Goal Differential", 0))
    
    # Detailed statistics
    st.markdown("#### 📊 Detailed Statistics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Offensive Stats:**")
        st.write(f"• Goals For: {team_data.get('Goals For', 0)}")
        st.write(f"• Goals/Game: {team_data.get('Goals For/Game', 0):.2f}")
        if config.ENABLE_UI_TOGGLES:
            st.write(f"• Offensive Rating: {team_data.get('Goals For/Game', 0):.3f}")
    
    with col2:
        st.markdown("**Defensive Stats:**")
        st.write(f"• Goals Against: {team_data.get('Goals Against', 0)}")
        st.write(f"• Goals Against/Game: {team_data.get('Goals Against/Game', 0):.2f}")
        if config.ENABLE_UI_TOGGLES:
            st.write(f"• Defensive Rating: {team_data.get('Goals Against/Game', 0):.3f}")
    
    # Record breakdown
    st.markdown("#### 📈 Record Breakdown")
    
    wins = team_data.get("Wins", 0)
    losses = team_data.get("Losses", 0)
    ties = team_data.get("Ties", 0)
    total_games = wins + losses + ties
    
    if total_games > 0:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Wins", f"{wins} ({wins/total_games*100:.1f}%)")
        
        with col2:
            st.metric("Losses", f"{losses} ({losses/total_games*100:.1f}%)")
        
        with col3:
            st.metric("Ties", f"{ties} ({ties/total_games*100:.1f}%)")
    
    # Game history with enhanced features
    st.markdown("#### 🎮 Game History")
    
    # Filters
    col1, col2 = st.columns(2)
    
    with col1:
        game_filter = st.selectbox(
            "Show games:",
            ["All", "Last 10", "Last 20", "Last 50"],
            key="game_filter"
        )
    
    with col2:
        result_filter = st.selectbox(
            "Filter by result:",
            ["All", "Wins", "Losses", "Ties"],
            key="result_filter"
        )
    
    # Apply filters
    filtered_games = team_games.copy()
    
    if game_filter != "All":
        n_games = int(game_filter.split()[-1])
        filtered_games = filtered_games.head(n_games)
    
    if result_filter != "All":
        if result_filter == "Wins":
            filtered_games = filtered_games[filtered_games["Goals For"] > filtered_games["Goals Against"]]
        elif result_filter == "Losses":
            filtered_games = filtered_games[filtered_games["Goals For"] < filtered_games["Goals Against"]]
        elif result_filter == "Ties":
            filtered_games = filtered_games[filtered_games["Goals For"] == filtered_games["Goals Against"]]
    
    # Display games with enhanced color coding
    if not filtered_games.empty:
        # Add result and goal differential columns
        filtered_games["Result"] = filtered_games.apply(
            lambda row: "W" if row["Goals For"] > row["Goals Against"] 
            else "L" if row["Goals For"] < row["Goals Against"] 
            else "T", axis=1
        )
        filtered_games["GD"] = filtered_games["Goals For"] - filtered_games["Goals Against"]
        
        # Add impact bucket if available
        if "impact_bucket" in filtered_games.columns:
            filtered_games["Impact"] = filtered_games["impact_bucket"].apply(get_result_badge)
        
        # Display columns
        display_cols = ["Date", "Opponent", "Goals For", "Goals Against", "Result", "GD"]
        if "Impact" in filtered_games.columns:
            display_cols.append("Impact")
        
        # Create styled dataframe
        styled_df = filtered_games[display_cols].copy()
        
        # Apply color coding if enabled
        if config.ENABLE_COLOR_CODING and "impact_bucket" in filtered_games.columns:
            def highlight_row(row):
                color = get_result_color(row["impact_bucket"])
                return [f"background-color: {color}"] * len(row)
            
            styled_df = styled_df.style.apply(highlight_row, axis=1, subset=display_cols)
        
        # Add expectation tooltips if available
        if "expected_gd" in filtered_games.columns and "gd_delta" in filtered_games.columns:
            st.markdown("**Expectation Analysis:**")
            expectation_display = filtered_games[["Date", "Opponent", "Goals For", "Goals Against", "Result", "expected_gd", "gd_delta", "Impact"]].head(10)
            st.dataframe(expectation_display, use_container_width=True)
            
            # Show expectation summary
            valid_expectations = filtered_games[filtered_games["expected_gd"].notna()]
            if not valid_expectations.empty:
                avg_expected = valid_expectations["expected_gd"].mean()
                avg_delta = valid_expectations["gd_delta"].mean()
                st.markdown(f"**Team Performance vs Expectations:**")
                st.markdown(f"• Average Expected GD: {avg_expected:.2f}")
                st.markdown(f"• Average Performance Delta: {avg_delta:.2f}")
                
                if avg_delta > 0.1:
                    st.success("✓ Team performing above expectations")
                elif avg_delta < -0.1:
                    st.warning("⚠ Team performing below expectations")
                else:
                    st.info("• Team performing as expected")
        
        st.dataframe(styled_df, use_container_width=True)
        
        # Game trends
        if st.button("Show Game Trends", key="show_trends"):
            create_game_trends_chart(filtered_games)
    
    # Game summary
    st.markdown("#### 📋 Game Summary")
    
    if not team_games.empty:
        avg_gf = team_games["Goals For"].mean()
        avg_ga = team_games["Goals Against"].mean()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Average Goals For:** {avg_gf:.2f}")
            st.write(f"**Average Goals Against:** {avg_ga:.2f}")
        
        with col2:
            st.write(f"**Last 5 Games Form:**")
            last_5 = team_games.head(5)
            form_results = last_5.apply(
                lambda row: "W" if row["Goals For"] > row["Goals Against"] 
                else "L" if row["Goals For"] < row["Goals Against"] 
                else "T", axis=1
            ).tolist()
            st.write(" ".join(form_results))

def create_game_trends_chart(games_df):
    """Create game trends chart."""
    if games_df.empty:
        return
    
    # Create cumulative win/loss/tie trends
    games_df = games_df.sort_values("Date")
    
    cumulative_wins = []
    cumulative_losses = []
    cumulative_ties = []
    
    wins = losses = ties = 0
    
    for _, game in games_df.iterrows():
        if game["Goals For"] > game["Goals Against"]:
            wins += 1
        elif game["Goals For"] < game["Goals Against"]:
            losses += 1
        else:
            ties += 1
        
        cumulative_wins.append(wins)
        cumulative_losses.append(losses)
        cumulative_ties.append(ties)
    
    # Create plot
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=games_df["Date"],
        y=cumulative_wins,
        mode='lines+markers',
        name='Wins',
        line=dict(color='green', width=3)
    ))
    
    fig.add_trace(go.Scatter(
        x=games_df["Date"],
        y=cumulative_losses,
        mode='lines+markers',
        name='Losses',
        line=dict(color='red', width=3)
    ))
    
    fig.add_trace(go.Scatter(
        x=games_df["Date"],
        y=cumulative_ties,
        mode='lines+markers',
        name='Ties',
        line=dict(color='gray', width=3)
    ))
    
    fig.update_layout(
        title="Cumulative Win/Loss/Tie Trends",
        xaxis_title="Date",
        yaxis_title="Cumulative Count",
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)

def main():
    """Main dashboard function."""
    st.set_page_config(
        page_title="Arizona U12 Soccer Rankings - Enhanced",
        page_icon="⚽",
        layout="wide"
    )
    
    st.title("⚽ Arizona U12 Soccer Rankings - Enhanced Dashboard")
    st.markdown("---")
    
    # Load data
    rankings_df, game_histories_df = load_data()
    
    # Main layout
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Rankings table
        create_rankings_table(rankings_df, game_histories_df)
    
    with col2:
        # What changed today panel
        create_what_changed_panel(rankings_df, game_histories_df)
    
    st.markdown("---")
    
    # Team detail view
    create_team_detail_view(rankings_df, game_histories_df)
    
    # Footer
    st.markdown("---")
    st.markdown("*Enhanced Arizona U12 Soccer Rankings Dashboard - Phase A Features*")

if __name__ == "__main__":
    main()
