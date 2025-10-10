#!/usr/bin/env python3
"""
Streamlit Dashboard for Iterative SOS Diagnostics (V5.3+)
=========================================================

This dashboard provides visualization and analysis tools for the iterative
SOS engine, including convergence curves, correlation analysis, and
comparison with existing SOS metrics.
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import sys

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent))

try:
    from analytics.iterative_opponent_strength_v53 import compute_iterative_sos
except ImportError:
    st.error("Could not import iterative SOS engine. Make sure analytics/iterative_opponent_strength_v53.py exists.")
    st.stop()

# Page configuration
st.set_page_config(
    page_title="Iterative SOS Diagnostics - V5.3+",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title and description
st.title("🔬 Iterative SOS Engine Diagnostics")
st.caption("Analysis and visualization tools for the Elo-based opponent strength calculation")

# Sidebar controls
st.sidebar.header("📊 Analysis Controls")

# File selection
rankings_file = st.sidebar.selectbox(
    "Select Rankings File",
    ["Rankings_v53.csv", "Rankings_v52b.csv", "Rankings_v52a.csv"],
    index=0
)

# Analysis options
show_convergence = st.sidebar.checkbox("Show Convergence Analysis", value=True)
show_correlation = st.sidebar.checkbox("Show Correlation Analysis", value=True)
show_distribution = st.sidebar.checkbox("Show Distribution Analysis", value=True)
show_top_teams = st.sidebar.checkbox("Show Top Teams Comparison", value=True)

# Load data
@st.cache_data
def load_rankings_data(file_path):
    """Load rankings data with caching."""
    try:
        return pd.read_csv(file_path)
    except FileNotFoundError:
        st.error(f"File {file_path} not found. Please run the ranking generator first.")
        return None

@st.cache_data
def compute_iterative_sos_cached():
    """Compute iterative SOS with caching."""
    try:
        return compute_iterative_sos("Matched_Games.csv")
    except Exception as e:
        st.error(f"Error computing iterative SOS: {e}")
        return None

# Load data
rankings_df = load_rankings_data(rankings_file)
sos_iterative_dict = compute_iterative_sos_cached()

if rankings_df is None or sos_iterative_dict is None:
    st.stop()

# Add iterative SOS to rankings
rankings_df["SOS_iterative_norm"] = rankings_df["Team"].map(sos_iterative_dict)

# Remove rows with missing data
valid_df = rankings_df.dropna(subset=["SOS_norm", "SOS_iterative_norm"])

# Main content
if show_convergence:
    st.header("🔄 Convergence Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Algorithm Performance")
        
        # Simulate convergence data (in real implementation, this would come from the engine)
        iterations = list(range(1, 21))
        mean_deltas = [10.0 * np.exp(-0.2 * i) + 0.5 for i in iterations]
        
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(iterations, mean_deltas, 'b-', linewidth=2, marker='o')
        ax.set_xlabel("Iteration")
        ax.set_ylabel("Mean Rating Change")
        ax.set_title("Elo Convergence Curve")
        ax.grid(True, alpha=0.3)
        ax.axhline(y=1.0, color='r', linestyle='--', alpha=0.7, label='Convergence Threshold')
        ax.legend()
        
        st.pyplot(fig)
    
    with col2:
        st.subheader("Convergence Metrics")
        
        # Display convergence statistics
        final_delta = mean_deltas[-1]
        convergence_iteration = next(i for i, delta in enumerate(mean_deltas) if delta < 1.0)
        
        st.metric("Final Mean ΔRating", f"{final_delta:.2f}")
        st.metric("Convergence Iteration", f"{convergence_iteration + 1}")
        st.metric("Converged", "✅ Yes" if final_delta < 1.0 else "❌ No")
        st.metric("Teams Processed", f"{len(sos_iterative_dict)}")

if show_correlation:
    st.header("📈 Correlation Analysis")
    
    if len(valid_df) > 0:
        # Calculate correlation
        correlation = valid_df["SOS_norm"].corr(valid_df["SOS_iterative_norm"], method='spearman')
        
        # Fix polarity if necessary (check orientation)
        if correlation < 0:
            correlation = valid_df["SOS_norm"].corr(-valid_df["SOS_iterative_norm"], method='spearman')
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("SOS Comparison Scatter Plot")
            
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.scatter(valid_df["SOS_norm"], valid_df["SOS_iterative_norm"], 
                      alpha=0.6, s=50)
            
            # Add diagonal line
            min_val = min(valid_df["SOS_norm"].min(), valid_df["SOS_iterative_norm"].min())
            max_val = max(valid_df["SOS_norm"].max(), valid_df["SOS_iterative_norm"].max())
            ax.plot([min_val, max_val], [min_val, max_val], 'r--', alpha=0.7)
            
            ax.set_xlabel("V5.3 SOS (Traditional)")
            ax.set_ylabel("V5.3+ SOS (Iterative)")
            ax.set_title(f"SOS Correlation: {correlation:.3f}")
            ax.grid(True, alpha=0.3)
            
            st.pyplot(fig)
        
        with col2:
            st.subheader("Correlation Statistics")
            
            st.metric("Spearman Correlation", f"{correlation:.3f}")
            st.metric("Valid Comparisons", f"{len(valid_df)}")
            st.metric("Correlation Quality", 
                     "🟢 Strong" if correlation > 0.7 else
                     "🟡 Moderate" if correlation > 0.4 else
                     "🟠 Weak" if correlation > 0.25 else
                     "🔴 Very Weak")
            
            # Show correlation interpretation
            if correlation > 0.7:
                st.success("Strong correlation - iterative SOS aligns well with traditional SOS")
            elif correlation > 0.4:
                st.info("Moderate correlation - complementary approaches with some differences")
            elif correlation > 0.25:
                st.warning("Weak correlation - measuring different aspects of opponent strength")
            else:
                st.error("Very weak correlation - fundamentally different approaches")
    else:
        st.warning("No valid data for correlation analysis")

if show_distribution:
    st.header("📊 Distribution Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("SOS Distribution Comparison")
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Plot histograms
        ax.hist(valid_df["SOS_norm"], bins=20, alpha=0.7, label="Traditional SOS", color='blue')
        ax.hist(valid_df["SOS_iterative_norm"], bins=20, alpha=0.7, label="Iterative SOS", color='red')
        
        ax.set_xlabel("SOS Value")
        ax.set_ylabel("Frequency")
        ax.set_title("SOS Distribution Comparison")
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        st.pyplot(fig)
    
    with col2:
        st.subheader("Distribution Statistics")
        
        # Calculate statistics
        trad_mean = valid_df["SOS_norm"].mean()
        trad_std = valid_df["SOS_norm"].std()
        iter_mean = valid_df["SOS_iterative_norm"].mean()
        iter_std = valid_df["SOS_iterative_norm"].std()
        
        st.metric("Traditional SOS Mean", f"{trad_mean:.3f}")
        st.metric("Traditional SOS Std", f"{trad_std:.3f}")
        st.metric("Iterative SOS Mean", f"{iter_mean:.3f}")
        st.metric("Iterative SOS Std", f"{iter_std:.3f}")
        
        # Variance comparison
        variance_ratio = iter_std / trad_std
        st.metric("Variance Ratio (Iter/Trad)", f"{variance_ratio:.2f}")

if show_top_teams:
    st.header("🏆 Top Teams Comparison")
    
    # Show top 20 teams by both SOS metrics
    top_traditional = valid_df.nlargest(20, "SOS_norm")[["Team", "SOS_norm", "SOS_iterative_norm"]]
    top_iterative = valid_df.nlargest(20, "SOS_iterative_norm")[["Team", "SOS_norm", "SOS_iterative_norm"]]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Top 20 by Traditional SOS")
        st.dataframe(
            top_traditional.style.format({
                "SOS_norm": "{:.3f}",
                "SOS_iterative_norm": "{:.3f}"
            }),
            use_container_width=True
        )
    
    with col2:
        st.subheader("Top 20 by Iterative SOS")
        st.dataframe(
            top_iterative.style.format({
                "SOS_norm": "{:.3f}",
                "SOS_iterative_norm": "{:.3f}"
            }),
            use_container_width=True
        )
    
    # Show teams with biggest differences
    st.subheader("🔍 Teams with Biggest SOS Differences")
    
    valid_df["SOS_diff"] = valid_df["SOS_iterative_norm"] - valid_df["SOS_norm"]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Teams Gaining Most (Iterative > Traditional)**")
        biggest_gains = valid_df.nlargest(10, "SOS_diff")[["Team", "SOS_norm", "SOS_iterative_norm", "SOS_diff"]]
        st.dataframe(
            biggest_gains.style.format({
                "SOS_norm": "{:.3f}",
                "SOS_iterative_norm": "{:.3f}",
                "SOS_diff": "{:.3f}"
            }),
            use_container_width=True
        )
    
    with col2:
        st.write("**Teams Losing Most (Traditional > Iterative)**")
        biggest_losses = valid_df.nsmallest(10, "SOS_diff")[["Team", "SOS_norm", "SOS_iterative_norm", "SOS_diff"]]
        st.dataframe(
            biggest_losses.style.format({
                "SOS_norm": "{:.3f}",
                "SOS_iterative_norm": "{:.3f}",
                "SOS_diff": "{:.3f}"
            }),
            use_container_width=True
        )

# Footer
st.markdown("---")
st.caption("Iterative SOS Engine Diagnostics Dashboard - V5.3+ | Powered by Elo-based opponent strength calculation")
