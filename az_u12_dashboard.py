#!/usr/bin/env python3
"""
AZ U12 Rankings Dashboard
========================

Interactive Streamlit dashboard to visualize and explore team rankings,
statistics, and game histories.

Features:
- Interactive team rankings table
- Team detail views with game history
- Filtering by club, games played, etc.
- Charts and visualizations
- Export capabilities
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os

# Page configuration
st.set_page_config(
    page_title="AZ U12 Rankings Dashboard",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
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
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    """Load and cache the ranking data"""
    try:
        # Use full path to the CSV files
        base_path = r"C:\Users\Dallas Heidt\Desktop\Soccer Rankings v2"
        rankings_df = pd.read_csv(f"{base_path}\\Rankings_PowerScore_NEW.csv")
        game_histories_df = pd.read_csv(f"{base_path}\\Team_Game_Histories_NEW.csv")
        
        # Convert date column
        game_histories_df['Date'] = pd.to_datetime(game_histories_df['Date'], errors='coerce')
        
        return rankings_df, game_histories_df
    except FileNotFoundError as e:
        st.error(f"Data files not found: {e}")
        st.info("Please ensure Rankings_PowerScore.csv and Team_Game_Histories.csv are in the current directory.")
        return None, None

def create_summary_metrics(rankings_df):
    """Create summary metrics cards"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total Teams",
            value=f"{len(rankings_df):,}",
            delta=None
        )
    
    with col2:
        avg_games = rankings_df['Games Played'].mean()
        st.metric(
            label="Avg Games/Team",
            value=f"{avg_games:.1f}",
            delta=None
        )
    
    with col3:
        total_games = rankings_df['Games Played'].sum()
        st.metric(
            label="Total Games",
            value=f"{total_games:,}",
            delta=None
        )
    
    with col4:
        top_team = rankings_df.iloc[0]['Team']
        st.metric(
            label="#1 Team",
            value=top_team[:20] + "..." if len(top_team) > 20 else top_team,
            delta=None
        )

def create_rankings_table(rankings_df, game_histories_df):
    """Create interactive rankings table with team selection"""
    st.subheader("🏆 Team Rankings")
    
    # Add filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        clubs = ['All'] + sorted(rankings_df['Club'].unique().tolist())
        selected_club = st.selectbox("Filter by Club:", clubs)
    
    with col2:
        min_games = st.slider("Minimum Games:", 1, int(rankings_df['Games Played'].max()), 1)
    
    with col3:
        show_top = st.selectbox("Show Top N Teams:", [10, 25, 50, 100, "All"])
    
    # Apply filters
    filtered_df = rankings_df.copy()
    
    if selected_club != 'All':
        filtered_df = filtered_df[filtered_df['Club'] == selected_club]
    
    filtered_df = filtered_df[filtered_df['Games Played'] >= min_games]
    
    if show_top != "All":
        filtered_df = filtered_df.head(show_top)
    
    # Display table
    st.dataframe(
        filtered_df[['Rank', 'Team', 'Club', 'Games Played', 'Wins', 'Losses', 'Ties', 
                    'Goals For', 'Goals Against', 'Goal Differential', 'Power Score']],
        width='stretch',
        height=400
    )
    
    # Add team selection for quick access
    st.subheader("🔍 Quick Team Lookup")
    col1, col2 = st.columns([2, 1])
    
    with col1:
        selected_team = st.selectbox(
            "Select a team to view details:",
            [''] + sorted(filtered_df['Team'].tolist()),
            key="quick_team_selector"
        )
    
    with col2:
        if st.button("View Team Details", disabled=not selected_team):
            st.session_state.selected_team = selected_team
            st.rerun()
    
    return filtered_df

def create_charts(rankings_df):
    """Create various charts and visualizations"""
    st.subheader("📊 Visualizations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Power Score Distribution
        fig_power = px.histogram(
            rankings_df, 
            x='Power Score',
            title='Power Score Distribution',
            nbins=20,
            color_discrete_sequence=['#1f77b4']
        )
        fig_power.update_layout(height=400)
        st.plotly_chart(fig_power, use_container_width=True)
    
    with col2:
        # Games Played vs Power Score
        fig_scatter = px.scatter(
            rankings_df,
            x='Games Played',
            y='Power Score',
            color='Club',
            title='Games Played vs Power Score',
            hover_data=['Team', 'Wins', 'Losses']
        )
        fig_scatter.update_layout(height=400)
        st.plotly_chart(fig_scatter, use_container_width=True)
    
    # Top 20 Teams Bar Chart
    st.subheader("🥇 Top 20 Teams by Power Score")
    top_20 = rankings_df.head(20)
    
    fig_bar = px.bar(
        top_20,
        x='Power Score',
        y='Team',
        orientation='h',
        title='Top 20 Teams',
        color='Power Score',
        color_continuous_scale='viridis'
    )
    fig_bar.update_layout(height=600, yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig_bar, use_container_width=True)

def create_team_detail_view(rankings_df, game_histories_df):
    """Create enhanced team detail view with comprehensive game history"""
    st.subheader("🔍 Team Detail View")
    
    # Check if team was selected from rankings page
    if 'selected_team' in st.session_state and st.session_state.selected_team:
        default_team = st.session_state.selected_team
        # Clear the session state after using it
        del st.session_state.selected_team
    else:
        default_team = None
    
    # Team selector
    team_names = rankings_df['Team'].tolist()
    selected_team = st.selectbox(
        "Select a team to view details:", 
        team_names,
        index=team_names.index(default_team) if default_team in team_names else 0
    )
    
    if selected_team:
        # Get team data
        team_data = rankings_df[rankings_df['Team'] == selected_team].iloc[0]
        team_games = game_histories_df[game_histories_df['Team'] == selected_team].sort_values('Date', ascending=False)
        
        # Team info header
        st.markdown(f"### 🏆 {selected_team}")
        
        # Team info cards
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Rank", f"#{team_data['Rank']}")
        
        with col2:
            st.metric("Power Score", f"{team_data['Power Score']:.3f}")
        
        with col3:
            st.metric("Games Played", team_data['Games Played'])
        
        with col4:
            win_pct = (team_data['Wins'] / team_data['Games Played']) * 100
            st.metric("Win %", f"{win_pct:.1f}%")
        
        with col5:
            st.metric("Goal Diff", f"{team_data['Goal Differential']:+.0f}")
        
        # Detailed statistics
        st.subheader("📊 Detailed Statistics")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Offensive Stats**")
            off_stats = {
                'Goals For': team_data['Goals For'],
                'Goals For/Game': f"{team_data['Goals For/Game']:.2f}",
                'Offense Score': f"{team_data['Offense Score']:.3f}"
            }
            for key, value in off_stats.items():
                st.write(f"• **{key}:** {value}")
        
        with col2:
            st.markdown("**Defensive Stats**")
            def_stats = {
                'Goals Against': team_data['Goals Against'],
                'Goals Against/Game': f"{team_data['Goals Against/Game']:.2f}",
                'Adj Defense Score': f"{team_data['Adj Defense Score']:.3f}"
            }
            for key, value in def_stats.items():
                st.write(f"• **{key}:** {value}")
        
        # Record breakdown
        st.subheader("🏆 Record Breakdown")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Wins", team_data['Wins'], f"{(team_data['Wins']/team_data['Games Played']*100):.1f}%")
        
        with col2:
            st.metric("Losses", team_data['Losses'], f"{(team_data['Losses']/team_data['Games Played']*100):.1f}%")
        
        with col3:
            st.metric("Ties", team_data['Ties'], f"{(team_data['Ties']/team_data['Games Played']*100):.1f}%")
        
        # Game history with enhanced features
        st.subheader("📅 Complete Game History")
        
        if not team_games.empty:
            # Add filters for game history
            col1, col2, col3 = st.columns(3)
            
            with col1:
                show_games = st.selectbox("Show Games:", ["Last 10", "Last 20", "Last 50", "All"])
            
            with col2:
                result_filter = st.selectbox("Filter by Result:", ["All", "Wins", "Losses", "Ties"])
            
            with col3:
                if st.button("📊 Show Game Trends"):
                    st.session_state.show_trends = True
            
            # Apply filters
            filtered_games = team_games.copy()
            
            if show_games != "All":
                num_games = int(show_games.split()[1])
                filtered_games = filtered_games.head(num_games)
            
            if result_filter != "All":
                if result_filter == "Wins":
                    filtered_games = filtered_games[filtered_games['Goals For'] > filtered_games['Goals Against']]
                elif result_filter == "Losses":
                    filtered_games = filtered_games[filtered_games['Goals For'] < filtered_games['Goals Against']]
                elif result_filter == "Ties":
                    filtered_games = filtered_games[filtered_games['Goals For'] == filtered_games['Goals Against']]
            
            # Add result column
            filtered_games = filtered_games.copy()
            filtered_games['Result'] = filtered_games.apply(
                lambda row: 'W' if row['Goals For'] > row['Goals Against'] 
                           else 'L' if row['Goals For'] < row['Goals Against'] 
                           else 'T', axis=1
            )
            
            # Add score display
            filtered_games['Score'] = filtered_games.apply(
                lambda row: f"{row['Goals For']}-{row['Goals Against']}", axis=1
            )
            
            # Display game history
            st.dataframe(
                filtered_games[['Date', 'Opponent', 'Score', 'Result']],
                width='stretch',
                hide_index=True
            )
            
            # Show trends if requested
            if 'show_trends' in st.session_state and st.session_state.show_trends:
                st.subheader("📈 Performance Trends")
                
                # Create trend chart
                trend_data = team_games.copy()
                trend_data['Cumulative_Wins'] = (trend_data['Goals For'] > trend_data['Goals Against']).cumsum()
                trend_data['Cumulative_Losses'] = (trend_data['Goals For'] < trend_data['Goals Against']).cumsum()
                trend_data['Cumulative_Ties'] = (trend_data['Goals For'] == trend_data['Goals Against']).cumsum()
                
                fig_trend = go.Figure()
                fig_trend.add_trace(go.Scatter(
                    x=trend_data['Date'], 
                    y=trend_data['Cumulative_Wins'],
                    mode='lines+markers',
                    name='Wins',
                    line=dict(color='green')
                ))
                fig_trend.add_trace(go.Scatter(
                    x=trend_data['Date'], 
                    y=trend_data['Cumulative_Losses'],
                    mode='lines+markers',
                    name='Losses',
                    line=dict(color='red')
                ))
                fig_trend.add_trace(go.Scatter(
                    x=trend_data['Date'], 
                    y=trend_data['Cumulative_Ties'],
                    mode='lines+markers',
                    name='Ties',
                    line=dict(color='orange')
                ))
                
                fig_trend.update_layout(
                    title=f"{selected_team} - Win/Loss/Tie Trends Over Time",
                    xaxis_title="Date",
                    yaxis_title="Cumulative Count",
                    height=400
                )
                
                st.plotly_chart(fig_trend, width='stretch')
                
                # Clear the trends flag
                del st.session_state.show_trends
            
            # Game summary stats
            st.subheader("📋 Game Summary")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                avg_gf = filtered_games['Goals For'].mean()
                st.metric("Avg Goals For", f"{avg_gf:.1f}")
            
            with col2:
                avg_ga = filtered_games['Goals Against'].mean()
                st.metric("Avg Goals Against", f"{avg_ga:.1f}")
            
            with col3:
                recent_form = filtered_games.head(5)['Result'].tolist()
                st.metric("Last 5 Games", " ".join(recent_form))
                
        else:
            st.info("No game history available for this team.")

def create_club_analysis(rankings_df):
    """Create club-level analysis"""
    st.subheader("🏢 Club Analysis")
    
    # Club statistics
    club_stats = rankings_df.groupby('Club').agg({
        'Team': 'count',
        'Power Score': 'mean',
        'Games Played': 'mean',
        'Wins': 'sum',
        'Losses': 'sum',
        'Ties': 'sum'
    }).round(3)
    
    club_stats.columns = ['Teams', 'Avg Power Score', 'Avg Games', 'Total Wins', 'Total Losses', 'Total Ties']
    club_stats = club_stats.sort_values('Avg Power Score', ascending=False)
    
    st.dataframe(club_stats, use_container_width=True)
    
    # Club comparison chart
    fig_club = px.bar(
        club_stats.head(10),
        x='Club',
        y='Avg Power Score',
        title='Top 10 Clubs by Average Power Score',
        color='Avg Power Score',
        color_continuous_scale='viridis'
    )
    fig_club.update_layout(height=500, xaxis_tickangle=-45)
    st.plotly_chart(fig_club, use_container_width=True)

def main():
    """Main dashboard function"""
    
    # Header
    st.markdown('<h1 class="main-header">⚽ AZ U12 Rankings Dashboard</h1>', unsafe_allow_html=True)
    
    # Load data
    rankings_df, game_histories_df = load_data()
    
    if rankings_df is None:
        st.stop()
    
    # Sidebar
    st.sidebar.title("🎛️ Dashboard Controls")
    
    # Last updated
    st.sidebar.info(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Navigation
    page = st.sidebar.selectbox(
        "Navigate to:",
        ["Overview", "Team Rankings", "Team Details", "Club Analysis", "Data Export"]
    )
    
    # Main content based on selected page
    if page == "Overview":
        st.header("📊 Overview")
        create_summary_metrics(rankings_df)
        create_charts(rankings_df)
        
    elif page == "Team Rankings":
        st.header("🏆 Team Rankings")
        create_rankings_table(rankings_df, game_histories_df)
        
    elif page == "Team Details":
        create_team_detail_view(rankings_df, game_histories_df)
        
    elif page == "Club Analysis":
        create_club_analysis(rankings_df)
        
    elif page == "Data Export":
        st.header("📥 Data Export")
        
        st.subheader("Download Rankings Data")
        csv_rankings = rankings_df.to_csv(index=False)
        st.download_button(
            label="Download Rankings CSV",
            data=csv_rankings,
            file_name=f"az_u12_rankings_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
        
        st.subheader("Download Game Histories")
        csv_games = game_histories_df.to_csv(index=False)
        st.download_button(
            label="Download Game Histories CSV",
            data=csv_games,
            file_name=f"az_u12_game_histories_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown("**About This Dashboard**")
    st.sidebar.markdown("""
    This dashboard provides interactive access to AZ U12 team rankings
    calculated using weighted offensive/defensive ratings and strength
    of schedule analysis.
    
    **Features:**
    - Recent game weighting (70% weight on last 10 games)
    - Game count penalties
    - Strength of Schedule calculations
    - Interactive filtering and visualization
    """)

if __name__ == "__main__":
    main()
