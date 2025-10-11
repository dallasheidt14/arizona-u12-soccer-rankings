#!/usr/bin/env python3
"""
Enhanced Streamlit Dashboard with Predictive Backbone Integration (V5.3+)
=======================================================================

This dashboard provides comprehensive predictive analytics including:
- Live calibration curves and metrics
- Overperforming teams leaderboard
- Historical calibration trends
- Interactive match predictions
- Iterative SOS integration for Phase C1
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import sys
import json
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent))

try:
    from analytics.predictive_backbone_v53 import (
        load_games_and_rankings, 
        run_backtest, 
        interactive_predict,
        default_feature_builder,
        power_plus_elo_feature_builder
    )
    from analytics.iterative_opponent_strength_v53 import compute_iterative_sos
except ImportError as e:
    st.error(f"Could not import predictive modules: {e}")
    st.stop()

# Page configuration
st.set_page_config(
    page_title="Predictive Analytics Dashboard - V5.3+",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title and description
st.title("🔮 Predictive Analytics Dashboard")
st.caption("Live calibration curves, overperforming teams, and match predictions powered by V5.3+")

# Initialize session state
if 'calibration_history' not in st.session_state:
    st.session_state.calibration_history = []

# Sidebar controls
st.sidebar.header("📊 Analysis Controls")

# File selection
rankings_file = st.sidebar.selectbox(
    "Select Rankings File",
    ["Rankings_v53.csv", "Rankings_v52b.csv", "Rankings_v52a.csv"],
    index=0
)

games_file = st.sidebar.selectbox(
    "Select Games File",
    ["Matched_Games.csv", "Team_Game_Histories_COMPREHENSIVE.csv"],
    index=0
)

# Analysis options
st.sidebar.header("🎯 Predictive Options")
feature_set = st.sidebar.selectbox(
    "Feature Set",
    ["Default", "Power + ELO", "Minimal"],
    index=0
)

calibration_method = st.sidebar.selectbox(
    "Calibration Method",
    ["Platt Scaling", "Isotonic Regression", "None"],
    index=0
)

split_mode = st.sidebar.selectbox(
    "Split Mode",
    ["Chronological", "K-Fold"],
    index=0
)

# Main content tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Live Calibration", 
    "🏆 Overperforming Teams", 
    "📊 Historical Trends", 
    "🎮 Match Predictor", 
    "🔬 Phase C1 Preview"
])

with tab1:
    st.header("📈 Live Calibration Analysis")
    
    if st.button("🔄 Run Live Calibration", type="primary"):
        with st.spinner("Running calibration analysis..."):
            try:
                # Load data
                games_df, rankings_df = load_games_and_rankings(games_file, rankings_file)
                
                # Select feature builder
                feature_fn_map = {
                    "Default": default_feature_builder,
                    "Power + ELO": power_plus_elo_feature_builder,
                    "Minimal": lambda x: (x[["PowerDiff"]] if "PowerDiff" in x.columns else pd.DataFrame({"BiasOnly": np.zeros(len(x))}), ["PowerDiff"] if "PowerDiff" in x.columns else ["BiasOnly"])
                }
                
                feature_fn = feature_fn_map[feature_set]
                
                # Select calibration method
                calibration_map = {
                    "Platt Scaling": True,
                    "Isotonic Regression": True,
                    "None": False
                }
                
                calibrated = calibration_map[calibration_method]
                
                # Select split mode
                split_map = {
                    "Chronological": "chronological",
                    "K-Fold": "kfold"
                }
                
                split = split_map[split_mode]
                
                # Run backtest
                result = run_backtest(
                    games_df=games_df,
                    rankings_df=rankings_df,
                    feature_fn=feature_fn,
                    split_mode=split,
                    calibrated=calibrated
                )
                
                # Store calibration metrics
                calibration_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "brier_score": result.brier_score,
                    "log_loss": result.log_loss,
                    "auc": result.auc,
                    "n_test": result.n_test,
                    "n_train": result.n_train,
                    "feature_set": feature_set,
                    "calibration_method": calibration_method,
                    "split_mode": split_mode
                }
                
                st.session_state.calibration_history.append(calibration_entry)
                
                # Display metrics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric(
                        "Brier Score", 
                        f"{result.brier_score:.4f}",
                        help="Lower is better. Perfect calibration = 0.0"
                    )
                
                with col2:
                    st.metric(
                        "Log Loss", 
                        f"{result.log_loss:.4f}",
                        help="Lower is better. Perfect predictions = 0.0"
                    )
                
                with col3:
                    st.metric(
                        "AUC", 
                        f"{result.auc:.4f}",
                        help="Higher is better. Random = 0.5, Perfect = 1.0"
                    )
                
                with col4:
                    st.metric(
                        "Test Games", 
                        f"{result.n_test:,}",
                        help="Number of games used for testing"
                    )
                
                # Calibration curve
                if result.calibration_curve:
                    st.subheader("🎯 Calibration Curve")
                    
                    fig = go.Figure()
                    
                    # Perfect calibration line
                    fig.add_trace(go.Scatter(
                        x=[0, 1], y=[0, 1],
                        mode='lines',
                        name='Perfect Calibration',
                        line=dict(dash='dash', color='gray')
                    ))
                    
                    # Actual calibration
                    fig.add_trace(go.Scatter(
                        x=result.calibration_curve['bin_centers'],
                        y=result.calibration_curve['fraction_positives'],
                        mode='markers+lines',
                        name='Model Calibration',
                        marker=dict(size=8, color='blue'),
                        line=dict(color='blue')
                    ))
                    
                    fig.update_layout(
                        title="Calibration Curve",
                        xaxis_title="Mean Predicted Probability",
                        yaxis_title="Fraction of Positives",
                        xaxis=dict(range=[0, 1]),
                        yaxis=dict(range=[0, 1]),
                        width=600,
                        height=400
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                
                # Feature importance
                if result.feature_importance:
                    st.subheader("🔍 Feature Importance")
                    
                    importance_df = pd.DataFrame([
                        {"Feature": feat, "Importance": abs(imp)}
                        for feat, imp in result.feature_importance.items()
                    ]).sort_values("Importance", ascending=False)
                    
                    fig = px.bar(
                        importance_df, 
                        x="Importance", 
                        y="Feature",
                        orientation='h',
                        title="Feature Importance (Absolute Values)"
                    )
                    fig.update_layout(height=300)
                    st.plotly_chart(fig, use_container_width=True)
                
                st.success("✅ Calibration analysis completed!")
                
            except Exception as e:
                st.error(f"Error running calibration: {e}")
                st.exception(e)

with tab2:
    st.header("🏆 Overperforming Teams Leaderboard")
    
    if st.button("🔄 Calculate Overperforming Teams", type="primary"):
        with st.spinner("Analyzing team performance..."):
            try:
                # Load comprehensive history
                history_df = pd.read_csv("Team_Game_Histories_COMPREHENSIVE.csv")
                
                # Calculate performance metrics
                performance_metrics = []
                
                for team in history_df['Team'].unique():
                    team_games = history_df[history_df['Team'] == team]
                    
                    if len(team_games) < 5:  # Skip teams with too few games
                        continue
                    
                    # Calculate overperformance metrics
                    overperformed_games = team_games[team_games['performance'] == 'overperformed']
                    underperformed_games = team_games[team_games['performance'] == 'underperformed']
                    neutral_games = team_games[team_games['performance'] == 'neutral']
                    
                    total_games = len(team_games)
                    overperformance_rate = len(overperformed_games) / total_games
                    underperformance_rate = len(underperformed_games) / total_games
                    neutral_rate = len(neutral_games) / total_games
                    
                    # Calculate average performance delta
                    avg_performance_delta = team_games['gd_delta'].mean()
                    
                    # Recent form (last 10 games)
                    recent_games = team_games.head(10)
                    recent_overperformance = len(recent_games[recent_games['performance'] == 'overperformed']) / len(recent_games)
                    
                    performance_metrics.append({
                        'Team': team,
                        'Total Games': total_games,
                        'Overperformance Rate': overperformance_rate,
                        'Underperformance Rate': underperformance_rate,
                        'Neutral Rate': neutral_rate,
                        'Avg Performance Delta': avg_performance_delta,
                        'Recent Overperformance': recent_overperformance,
                        'Overperformed Games': len(overperformed_games),
                        'Underperformed Games': len(underperformed_games)
                    })
                
                performance_df = pd.DataFrame(performance_metrics)
                
                # Sort by overperformance rate
                performance_df = performance_df.sort_values('Overperformance Rate', ascending=False)
                
                # Display top performers
                st.subheader("🥇 Top Overperforming Teams")
                
                top_performers = performance_df.head(10)
                
                # Create metrics display
                cols = st.columns(3)
                with cols[0]:
                    st.metric("Best Overperformance Rate", f"{top_performers.iloc[0]['Overperformance Rate']:.1%}")
                with cols[1]:
                    st.metric("Most Overperformed Games", f"{top_performers.iloc[0]['Overperformed Games']}")
                with cols[2]:
                    st.metric("Best Recent Form", f"{top_performers.iloc[0]['Recent Overperformance']:.1%}")
                
                # Display table
                st.dataframe(
                    top_performers[['Team', 'Overperformance Rate', 'Overperformed Games', 'Recent Overperformance', 'Avg Performance Delta']],
                    use_container_width=True
                )
                
                # Visualization
                st.subheader("📊 Performance Distribution")
                
                fig = make_subplots(
                    rows=2, cols=2,
                    subplot_titles=('Overperformance Rate', 'Performance Delta Distribution', 'Recent Form', 'Games Distribution'),
                    specs=[[{"secondary_y": False}, {"secondary_y": False}],
                           [{"secondary_y": False}, {"secondary_y": False}]]
                )
                
                # Overperformance rate histogram
                fig.add_trace(
                    go.Histogram(x=performance_df['Overperformance Rate'], name='Overperformance Rate'),
                    row=1, col=1
                )
                
                # Performance delta distribution
                fig.add_trace(
                    go.Histogram(x=performance_df['Avg Performance Delta'], name='Performance Delta'),
                    row=1, col=2
                )
                
                # Recent form scatter
                fig.add_trace(
                    go.Scatter(
                        x=performance_df['Overperformance Rate'],
                        y=performance_df['Recent Overperformance'],
                        mode='markers',
                        name='Recent vs Overall',
                        text=performance_df['Team'],
                        hovertemplate='<b>%{text}</b><br>Overall: %{x:.1%}<br>Recent: %{y:.1%}<extra></extra>'
                    ),
                    row=2, col=1
                )
                
                # Games distribution
                fig.add_trace(
                    go.Histogram(x=performance_df['Total Games'], name='Total Games'),
                    row=2, col=2
                )
                
                fig.update_layout(height=600, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
                
                st.success("✅ Overperforming teams analysis completed!")
                
            except Exception as e:
                st.error(f"Error analyzing overperforming teams: {e}")
                st.exception(e)

with tab3:
    st.header("📊 Historical Calibration Trends")
    
    if st.session_state.calibration_history:
        st.subheader("📈 Calibration Metrics Over Time")
        
        # Convert to DataFrame
        history_df = pd.DataFrame(st.session_state.calibration_history)
        history_df['timestamp'] = pd.to_datetime(history_df['timestamp'])
        
        # Create trend visualization
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Brier Score Trend', 'Log Loss Trend', 'AUC Trend', 'Test Games Trend'),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        # Brier Score trend
        fig.add_trace(
            go.Scatter(
                x=history_df['timestamp'],
                y=history_df['brier_score'],
                mode='lines+markers',
                name='Brier Score',
                line=dict(color='red')
            ),
            row=1, col=1
        )
        
        # Log Loss trend
        fig.add_trace(
            go.Scatter(
                x=history_df['timestamp'],
                y=history_df['log_loss'],
                mode='lines+markers',
                name='Log Loss',
                line=dict(color='orange')
            ),
            row=1, col=2
        )
        
        # AUC trend
        fig.add_trace(
            go.Scatter(
                x=history_df['timestamp'],
                y=history_df['auc'],
                mode='lines+markers',
                name='AUC',
                line=dict(color='green')
            ),
            row=2, col=1
        )
        
        # Test Games trend
        fig.add_trace(
            go.Scatter(
                x=history_df['timestamp'],
                y=history_df['n_test'],
                mode='lines+markers',
                name='Test Games',
                line=dict(color='blue')
            ),
            row=2, col=2
        )
        
        fig.update_layout(height=600, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        
        # Summary statistics
        st.subheader("📊 Summary Statistics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Latest Brier Score", f"{history_df['brier_score'].iloc[-1]:.4f}")
        with col2:
            st.metric("Latest Log Loss", f"{history_df['log_loss'].iloc[-1]:.4f}")
        with col3:
            st.metric("Latest AUC", f"{history_df['auc'].iloc[-1]:.4f}")
        with col4:
            st.metric("Total Runs", f"{len(history_df)}")
        
        # Configuration analysis
        st.subheader("🔧 Configuration Analysis")
        
        config_summary = history_df.groupby(['feature_set', 'calibration_method', 'split_mode']).agg({
            'brier_score': ['mean', 'std'],
            'log_loss': ['mean', 'std'],
            'auc': ['mean', 'std']
        }).round(4)
        
        st.dataframe(config_summary, use_container_width=True)
        
    else:
        st.info("No calibration history available. Run calibration analysis in the 'Live Calibration' tab first.")

with tab4:
    st.header("🎮 Interactive Match Predictor")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Team Selection")
        
        # Load rankings for team selection
        try:
            rankings_df = pd.read_csv(rankings_file)
            team_list = sorted(rankings_df['Team'].tolist())
            
            team_a = st.selectbox("Select Team A", team_list)
            team_b = st.selectbox("Select Team B", team_list)
            
            prediction_mode = st.selectbox("Prediction Mode", ["Simple", "Advanced"])
            
            if st.button("🎯 Predict Match Outcome", type="primary"):
                try:
                    # Run prediction
                    result = interactive_predict(
                        team_a=team_a,
                        team_b=team_b,
                        rankings_df=rankings_df,
                        mode=prediction_mode.lower()
                    )
                    
                    # Display results
                    st.subheader("🎯 Prediction Results")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric(
                            f"{team_a} Win Probability",
                            f"{result['P_A_win']:.1%}",
                            delta=None
                        )
                    
                    with col2:
                        if prediction_mode == "Advanced":
                            st.metric(
                                "Draw Probability",
                                f"{result['P_Draw']:.1%}",
                                delta=None
                            )
                        else:
                            st.metric(
                                f"{team_b} Win Probability",
                                f"{result['P_B_win']:.1%}",
                                delta=None
                            )
                    
                    with col3:
                        if prediction_mode == "Advanced":
                            st.metric(
                                f"{team_b} Win Probability",
                                f"{result['P_B_win']:.1%}",
                                delta=None
                            )
                        else:
                            st.metric(
                                "Predicted Winner",
                                result['predicted_winner'],
                                delta=None
                            )
                    
                    # Confidence indicator
                    max_prob = max(result['P_A_win'], result['P_B_win'])
                    if prediction_mode == "Advanced":
                        max_prob = max(result['P_A_win'], result['P_Draw'], result['P_B_win'])
                    
                    confidence_level = "High" if max_prob > 0.7 else "Medium" if max_prob > 0.6 else "Low"
                    confidence_color = "green" if max_prob > 0.7 else "orange" if max_prob > 0.6 else "red"
                    
                    st.markdown(f"**Confidence Level:** :{confidence_color}[{confidence_level}] ({max_prob:.1%})")
                    
                except Exception as e:
                    st.error(f"Error making prediction: {e}")
        
        except Exception as e:
            st.error(f"Error loading rankings: {e}")
    
    with col2:
        st.subheader("📊 Team Comparison")
        
        if 'team_a' in locals() and 'team_b' in locals():
            try:
                team_a_data = rankings_df[rankings_df['Team'] == team_a].iloc[0]
                team_b_data = rankings_df[rankings_df['Team'] == team_b].iloc[0]
                
                comparison_data = {
                    'Metric': ['PowerScore', 'Games Played', 'SAO (Offense)', 'SAD (Defense)', 'SOS'],
                    team_a: [
                        f"{team_a_data['PowerScore']:.3f}",
                        f"{team_a_data['GamesPlayed']}",
                        f"{team_a_data.get('SAO_norm', 'N/A')}",
                        f"{team_a_data.get('SAD_norm', 'N/A')}",
                        f"{team_a_data.get('SOS_norm', 'N/A')}"
                    ],
                    team_b: [
                        f"{team_b_data['PowerScore']:.3f}",
                        f"{team_b_data['GamesPlayed']}",
                        f"{team_b_data.get('SAO_norm', 'N/A')}",
                        f"{team_b_data.get('SAD_norm', 'N/A')}",
                        f"{team_b_data.get('SOS_norm', 'N/A')}"
                    ]
                }
                
                comparison_df = pd.DataFrame(comparison_data)
                st.dataframe(comparison_df, use_container_width=True)
                
            except Exception as e:
                st.error(f"Error loading team comparison: {e}")

with tab5:
    st.header("🔬 Phase C1 Preview: Iterative SOS Integration")
    
    st.info("🚧 **Phase C1 Preview** - This section demonstrates the integration of Iterative SOS ratings into the predictive backbone for enhanced win probability forecasting.")
    
    if st.button("🔄 Run Iterative SOS Analysis", type="primary"):
        with st.spinner("Computing Iterative SOS ratings..."):
            try:
                # Compute Iterative SOS
                sos_iterative_dict = compute_iterative_sos("Matched_Games.csv")
                
                st.subheader("📊 Iterative SOS Summary")
                
                # Convert to DataFrame for analysis
                sos_df = pd.DataFrame([
                    {"Team": team, "Iterative_SOS": rating}
                    for team, rating in sos_iterative_dict.items()
                ]).sort_values("Iterative_SOS", ascending=False)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("Teams Analyzed", len(sos_df))
                    st.metric("SOS Range", f"{sos_df['Iterative_SOS'].min():.3f} - {sos_df['Iterative_SOS'].max():.3f}")
                
                with col2:
                    st.metric("Mean SOS", f"{sos_df['Iterative_SOS'].mean():.3f}")
                    st.metric("SOS Std Dev", f"{sos_df['Iterative_SOS'].std():.3f}")
                
                # Top and bottom teams
                st.subheader("🏆 Top Iterative SOS Teams")
                st.dataframe(sos_df.head(10), use_container_width=True)
                
                st.subheader("📉 Bottom Iterative SOS Teams")
                st.dataframe(sos_df.tail(10), use_container_width=True)
                
                # Distribution visualization
                st.subheader("📊 Iterative SOS Distribution")
                
                fig = make_subplots(
                    rows=1, cols=2,
                    subplot_titles=('SOS Distribution', 'SOS vs Traditional SOS Comparison')
                )
                
                # Histogram
                fig.add_trace(
                    go.Histogram(x=sos_df['Iterative_SOS'], name='Iterative SOS'),
                    row=1, col=1
                )
                
                # Comparison with traditional SOS (if available)
                try:
                    rankings_df = pd.read_csv(rankings_file)
                    if 'SOS_norm' in rankings_df.columns:
                        comparison_df = rankings_df.merge(sos_df, on='Team', how='inner')
                        
                        fig.add_trace(
                            go.Scatter(
                                x=comparison_df['SOS_norm'],
                                y=comparison_df['Iterative_SOS'],
                                mode='markers',
                                name='SOS Comparison',
                                text=comparison_df['Team'],
                                hovertemplate='<b>%{text}</b><br>Traditional: %{x:.3f}<br>Iterative: %{y:.3f}<extra></extra>'
                            ),
                            row=1, col=2
                        )
                        
                        # Calculate correlation
                        correlation = comparison_df['SOS_norm'].corr(comparison_df['Iterative_SOS'])
                        st.metric("SOS Correlation", f"{correlation:.3f}")
                
                except Exception as e:
                    st.warning(f"Could not load traditional SOS for comparison: {e}")
                
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
                
                # Phase C1 Integration Preview
                st.subheader("🔮 Phase C1 Integration Preview")
                
                st.markdown("""
                **Enhanced Predictive Features with Iterative SOS:**
                
                1. **ELO-Informed Win Probability**: Use Iterative SOS ratings as additional features
                2. **Dynamic Rating Updates**: Incorporate real-time rating changes
                3. **Opponent Strength Context**: More nuanced opponent strength assessment
                4. **Convergence-Based Confidence**: Use convergence metrics for prediction confidence
                
                **Next Steps:**
                - Integrate Iterative SOS into `power_plus_elo_feature_builder`
                - Add ELO rating differences as predictive features
                - Implement dynamic rating updates during backtesting
                - Create convergence-based confidence scoring
                """)
                
                st.success("✅ Iterative SOS analysis completed!")
                
            except Exception as e:
                st.error(f"Error running Iterative SOS analysis: {e}")
                st.exception(e)

# Footer
st.markdown("---")
st.caption("🔮 Predictive Analytics Dashboard - V5.3+ | Powered by Youth Soccer Rankings System")
