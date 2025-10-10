"""
Calibration Tab for Streamlit Dashboard (V5.3+)

This module provides the calibration visualization tab for the Streamlit dashboard,
displaying predictive model performance metrics, trends, and calibration curves.

Key Features:
- Recent metrics table with performance indicators
- Trend charts for Brier Score, Log Loss, and AUC
- Calibration curve visualization
- Interpretation guide for stakeholders
- Error handling for missing data

Author: Youth Soccer Rankings System
Version: V5.3+
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Optional, Dict, List, Tuple


def load_metrics_data(log_path: str) -> Optional[pd.DataFrame]:
    """
    Load metrics data from CSV log.
    
    Args:
        log_path: Path to metrics log CSV
        
    Returns:
        DataFrame with metrics or None if file doesn't exist
    """
    try:
        if not Path(log_path).exists():
            return None
        
        df = pd.read_csv(log_path)
        
        # Convert timestamp to datetime
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')
        
        return df
        
    except Exception as e:
        st.error(f"Error loading metrics data: {e}")
        return None


def get_latest_calibration_plot(plots_dir: str) -> Optional[str]:
    """
    Get the path to the latest calibration plot.
    
    Args:
        plots_dir: Directory containing calibration plots
        
    Returns:
        Path to latest plot or None if not found
    """
    try:
        plots_path = Path(plots_dir)
        if not plots_path.exists():
            return None
        
        # Find PNG files with calibration_curve prefix
        plot_files = list(plots_path.glob("calibration_curve_*.png"))
        
        if not plot_files:
            return None
        
        # Sort by modification time and get latest
        latest_plot = max(plot_files, key=lambda p: p.stat().st_mtime)
        return str(latest_plot)
        
    except Exception as e:
        st.error(f"Error finding calibration plot: {e}")
        return None


def create_metrics_summary_cards(df: pd.DataFrame) -> None:
    """
    Create summary metric cards.
    
    Args:
        df: Metrics DataFrame
    """
    if df.empty:
        st.warning("No metrics data available")
        return
    
    latest = df.iloc[-1]
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Latest Brier Score",
            value=f"{latest['brier_score']:.4f}",
            delta=f"{latest['brier_score'] - df.iloc[-2]['brier_score']:.4f}" if len(df) > 1 else None,
            help="Lower is better. Target: < 0.20"
        )
    
    with col2:
        st.metric(
            label="Latest Log Loss",
            value=f"{latest['log_loss']:.4f}",
            delta=f"{latest['log_loss'] - df.iloc[-2]['log_loss']:.4f}" if len(df) > 1 else None,
            help="Lower is better. Target: < 0.45"
        )
    
    with col3:
        st.metric(
            label="Latest AUC",
            value=f"{latest['auc']:.4f}",
            delta=f"{latest['auc'] - df.iloc[-2]['auc']:.4f}" if len(df) > 1 else None,
            help="Higher is better. Target: > 0.70"
        )
    
    with col4:
        st.metric(
            label="Latest Calibration Slope",
            value=f"{latest['calibration_slope']:.3f}",
            delta=f"{latest['calibration_slope'] - df.iloc[-2]['calibration_slope']:.3f}" if len(df) > 1 else None,
            help="Closer to 1.0 is better. Target: 0.8 - 1.2"
        )


def create_metrics_trend_chart(df: pd.DataFrame) -> None:
    """
    Create trend chart for metrics over time.
    
    Args:
        df: Metrics DataFrame
    """
    if df.empty or len(df) < 2:
        st.info("Need at least 2 data points to show trends")
        return
    
    # Create subplot with secondary y-axis
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Brier Score Trend', 'Log Loss Trend', 'AUC Trend', 'Calibration Slope Trend'),
        vertical_spacing=0.1,
        horizontal_spacing=0.1
    )
    
    # Brier Score
    fig.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=df['brier_score'],
            mode='lines+markers',
            name='Brier Score',
            line=dict(color='red', width=2),
            marker=dict(size=6)
        ),
        row=1, col=1
    )
    
    # Add target line
    fig.add_hline(y=0.20, line_dash="dash", line_color="red", opacity=0.5, row=1, col=1)
    
    # Log Loss
    fig.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=df['log_loss'],
            mode='lines+markers',
            name='Log Loss',
            line=dict(color='orange', width=2),
            marker=dict(size=6),
            showlegend=False
        ),
        row=1, col=2
    )
    
    # Add target line
    fig.add_hline(y=0.45, line_dash="dash", line_color="orange", opacity=0.5, row=1, col=2)
    
    # AUC
    fig.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=df['auc'],
            mode='lines+markers',
            name='AUC',
            line=dict(color='green', width=2),
            marker=dict(size=6),
            showlegend=False
        ),
        row=2, col=1
    )
    
    # Add target line
    fig.add_hline(y=0.70, line_dash="dash", line_color="green", opacity=0.5, row=2, col=1)
    
    # Calibration Slope
    fig.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=df['calibration_slope'],
            mode='lines+markers',
            name='Calibration Slope',
            line=dict(color='blue', width=2),
            marker=dict(size=6),
            showlegend=False
        ),
        row=2, col=2
    )
    
    # Add target range
    fig.add_hline(y=1.0, line_dash="dash", line_color="blue", opacity=0.5, row=2, col=2)
    fig.add_hline(y=0.8, line_dash="dot", line_color="blue", opacity=0.3, row=2, col=2)
    fig.add_hline(y=1.2, line_dash="dot", line_color="blue", opacity=0.3, row=2, col=2)
    
    # Update layout
    fig.update_layout(
        height=600,
        title_text="Model Performance Trends Over Time",
        title_x=0.5,
        showlegend=True
    )
    
    # Update x-axis labels
    fig.update_xaxes(title_text="Date", row=2, col=1)
    fig.update_xaxes(title_text="Date", row=2, col=2)
    
    # Update y-axis labels
    fig.update_yaxes(title_text="Brier Score", row=1, col=1)
    fig.update_yaxes(title_text="Log Loss", row=1, col=2)
    fig.update_yaxes(title_text="AUC", row=2, col=1)
    fig.update_yaxes(title_text="Calibration Slope", row=2, col=2)
    
    st.plotly_chart(fig, use_container_width=True)


def create_recent_metrics_table(df: pd.DataFrame) -> None:
    """
    Create table showing recent metrics.
    
    Args:
        df: Metrics DataFrame
    """
    if df.empty:
        st.warning("No metrics data available")
        return
    
    # Show last 10 entries
    recent_df = df.tail(10).copy()
    
    # Format columns for display
    display_df = recent_df.copy()
    
    # Format timestamp
    if 'timestamp' in display_df.columns:
        display_df['timestamp'] = display_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M')
    
    # Format numeric columns
    numeric_cols = ['brier_score', 'log_loss', 'auc', 'calibration_slope', 'ece']
    for col in numeric_cols:
        if col in display_df.columns:
            display_df[col] = display_df[col].round(4)
    
    # Select columns to display
    display_cols = [
        'timestamp', 'split_mode', 'calibration_method', 'feature_set',
        'n_test', 'brier_score', 'log_loss', 'auc', 'calibration_slope'
    ]
    
    available_cols = [col for col in display_cols if col in display_df.columns]
    display_df = display_df[available_cols]
    
    # Rename columns for display
    column_names = {
        'timestamp': 'Date/Time',
        'split_mode': 'Split Mode',
        'calibration_method': 'Calibration',
        'feature_set': 'Features',
        'n_test': 'Test Samples',
        'brier_score': 'Brier Score',
        'log_loss': 'Log Loss',
        'auc': 'AUC',
        'calibration_slope': 'Calibration Slope'
    }
    
    display_df = display_df.rename(columns=column_names)
    
    st.subheader("Recent Model Performance")
    st.dataframe(display_df, use_container_width=True)


def create_calibration_curve_plot(plot_path: Optional[str]) -> None:
    """
    Display calibration curve plot.
    
    Args:
        plot_path: Path to calibration plot image
    """
    st.subheader("Latest Calibration Curve")
    
    if plot_path and Path(plot_path).exists():
        st.image(plot_path, use_container_width=True)
        
        # Add interpretation
        st.info("""
        **Calibration Curve Interpretation:**
        - **Perfect Calibration**: Points lie on the diagonal line
        - **Overconfident**: Points below diagonal (predicted probabilities too high)
        - **Underconfident**: Points above diagonal (predicted probabilities too low)
        - **ECE (Expected Calibration Error)**: Lower is better, measures deviation from perfect calibration
        """)
    else:
        st.warning("No calibration plot available. Run the weekly predictive job to generate plots.")


def create_interpretation_guide() -> None:
    """
    Create interpretation guide for stakeholders.
    """
    st.subheader("Model Performance Interpretation Guide")
    
    with st.expander("📊 Metrics Explained", expanded=True):
        st.markdown("""
        **Brier Score** (Target: < 0.20)
        - Measures calibration of probability predictions
        - Lower values indicate better calibration
        - Perfect calibration = 0.0, worst possible = 1.0
        
        **Log Loss** (Target: < 0.45)
        - Measures accuracy of probability predictions
        - Penalizes confident wrong predictions heavily
        - Lower values indicate better accuracy
        
        **AUC** (Target: > 0.70)
        - Measures discriminative power (ability to distinguish winners from losers)
        - Higher values indicate better discrimination
        - Perfect discrimination = 1.0, random = 0.5
        
        **Calibration Slope** (Target: 0.8 - 1.2)
        - Measures how well predicted probabilities match actual frequencies
        - Slope = 1.0 indicates perfect calibration
        - Slope < 1.0: overconfident, Slope > 1.0: underconfident
        """)
    
    with st.expander("🎯 Win Probability Interpretation", expanded=False):
        st.markdown("""
        **Probability Ranges:**
        - **50% ± 5%**: Even matchup - coin flip game
        - **60-70%**: Slight favorite - moderate advantage
        - **75-85%**: Strong favorite - clear advantage
        - **> 90%**: Heavy favorite - overwhelming advantage
        - **< 30%**: Underdog - significant challenge
        
        **For Coaches:**
        - Use probabilities to set realistic expectations
        - Focus on improving in areas where you're consistently underperforming
        - Consider opponent strength when planning strategy
        """)
    
    with st.expander("📈 Trend Analysis", expanded=False):
        st.markdown("""
        **Improving Trends:**
        - Brier Score decreasing over time
        - Log Loss decreasing over time
        - AUC increasing over time
        - Calibration Slope approaching 1.0
        
        **Concerning Trends:**
        - Metrics getting worse over time
        - High variability in performance
        - Calibration slope far from 1.0
        
        **Action Items:**
        - Monitor trends weekly
        - Investigate sudden changes
        - Consider retraining if performance degrades significantly
        """)


def create_model_comparison(df: pd.DataFrame) -> None:
    """
    Create model comparison section.
    
    Args:
        df: Metrics DataFrame
    """
    if df.empty:
        return
    
    st.subheader("Model Configuration Comparison")
    
    # Group by configuration
    config_cols = ['split_mode', 'calibration_method', 'feature_set']
    available_config_cols = [col for col in config_cols if col in df.columns]
    
    if not available_config_cols:
        st.info("No configuration data available for comparison")
        return
    
    # Create comparison table
    comparison_df = df.groupby(available_config_cols).agg({
        'brier_score': ['mean', 'std', 'count'],
        'log_loss': ['mean', 'std'],
        'auc': ['mean', 'std'],
        'calibration_slope': ['mean', 'std']
    }).round(4)
    
    # Flatten column names
    comparison_df.columns = ['_'.join(col).strip() for col in comparison_df.columns]
    comparison_df = comparison_df.reset_index()
    
    # Display comparison
    st.dataframe(comparison_df, use_container_width=True)
    
    # Create visualization
    if len(available_config_cols) >= 2:
        fig = px.box(
            df,
            x=available_config_cols[0],
            y='brier_score',
            color=available_config_cols[1] if len(available_config_cols) > 1 else None,
            title="Brier Score Distribution by Configuration"
        )
        st.plotly_chart(fig, use_container_width=True)


def render_calibration_tab(
    metrics_log_path: str = "predictive_metrics_log.csv",
    plots_dir: str = "predictive_reports"
) -> None:
    """
    Render the calibration tab for the Streamlit dashboard.
    
    Args:
        metrics_log_path: Path to metrics log CSV
        plots_dir: Directory containing calibration plots
    """
    st.header("🎯 Predictive Calibration & Accuracy")
    st.caption("Monitor model performance and calibration over time")
    
    # Load data
    df = load_metrics_data(metrics_log_path)
    
    if df is None or df.empty:
        st.warning("No metrics data available. Run the weekly predictive job to generate data.")
        st.info("""
        To generate metrics data:
        1. Run: `python -m analytics.weekly_predictive_job --games Matched_Games.csv --rankings Rankings_v53.csv`
        2. Or use the GitHub Actions workflow for automated weekly runs
        """)
        return
    
    # Create tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "📈 Trends", "🔍 Details", "📚 Guide"])
    
    with tab1:
        st.subheader("Performance Overview")
        
        # Summary cards
        create_metrics_summary_cards(df)
        
        # Recent metrics table
        create_recent_metrics_table(df)
        
        # Latest calibration plot
        plot_path = get_latest_calibration_plot(plots_dir)
        create_calibration_curve_plot(plot_path)
    
    with tab2:
        st.subheader("Performance Trends")
        
        # Trend charts
        create_metrics_trend_chart(df)
        
        # Model comparison
        create_model_comparison(df)
    
    with tab3:
        st.subheader("Detailed Analysis")
        
        # Full metrics table
        st.subheader("All Metrics Data")
        
        # Add filters
        col1, col2 = st.columns(2)
        
        with col1:
            if 'calibration_method' in df.columns:
                calibration_methods = st.multiselect(
                    "Calibration Methods",
                    options=df['calibration_method'].unique(),
                    default=df['calibration_method'].unique()
                )
                df = df[df['calibration_method'].isin(calibration_methods)]
        
        with col2:
            if 'feature_set' in df.columns:
                feature_sets = st.multiselect(
                    "Feature Sets",
                    options=df['feature_set'].unique(),
                    default=df['feature_set'].unique()
                )
                df = df[df['feature_set'].isin(feature_sets)]
        
        # Display filtered data
        st.dataframe(df, use_container_width=True)
        
        # Download button
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download Metrics Data",
            data=csv,
            file_name=f"predictive_metrics_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    with tab4:
        # Interpretation guide
        create_interpretation_guide()


if __name__ == "__main__":
    # Example usage for testing
    st.set_page_config(
        page_title="Predictive Calibration Dashboard",
        layout="wide"
    )
    
    render_calibration_tab()
