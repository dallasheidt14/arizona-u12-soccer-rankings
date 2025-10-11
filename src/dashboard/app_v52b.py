"""
Arizona U12 Soccer Analytics Hub - V5.2b Dashboard

Interactive dashboard for Arizona Boys U12 soccer rankings, match predictions,
and model performance monitoring.
"""
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from analytics.projected_outcomes_v52b import interactive_predict, evaluate_predictions

# Page setup
st.set_page_config(page_title="AZ Boys U12 Rankings Dashboard", layout="wide")
st.title("⚽ Arizona Boys U12 Soccer Analytics Hub — V5.2b")
st.caption("Powered by Strength-Adjusted PowerScores and Predictive Outcomes")

# Load data
@st.cache_data
def load_rankings():
    """Load rankings data with caching."""
    try:
        return pd.read_csv("Rankings_v52b.csv")
    except FileNotFoundError:
        # Try fallback files
        for fallback in ["Rankings_v52a.csv", "Rankings_v52.csv", "Rankings_v51.csv", "Rankings_v5.csv"]:
            try:
                return pd.read_csv(fallback)
            except FileNotFoundError:
                continue
        st.error("No ranking files found. Please ensure Rankings_v52b.csv exists.")
        return None

@st.cache_data
def load_predictions():
    """Load historical predictions with caching."""
    try:
        return pd.read_csv("Predicted_Outcomes_v52b.csv")
    except FileNotFoundError:
        return None

# Load data
rankings = load_rankings()
predictions = load_predictions()

if rankings is None:
    st.stop()

# Sidebar - Match Predictor
st.sidebar.header("🔍 Match Predictor")
team_list = sorted(rankings["Team"].unique().tolist())

team_a = st.sidebar.selectbox("Select Team A", team_list)
team_b = st.sidebar.selectbox("Select Team B", team_list)
mode = st.sidebar.radio("Prediction Mode", ["simple", "advanced"])

if st.sidebar.button("Predict Outcome"):
    try:
        result = interactive_predict(team_a, team_b, rankings, mode)
        
        if "error" in result:
            st.sidebar.error(f"Error: {result['error']}")
        else:
            st.sidebar.success("✅ Prediction Complete!")
            
            # Display results
            st.sidebar.markdown("### Prediction Results")
            st.sidebar.markdown(f"**{result['team_a']}** vs **{result['team_b']}**")
            
            if mode == "advanced":
                col1, col2, col3 = st.sidebar.columns(3)
                with col1:
                    st.metric("Win", f"{result['p_a_win']:.1%}")
                with col2:
                    st.metric("Draw", f"{result['p_draw']:.1%}")
                with col3:
                    st.metric("Loss", f"{result['p_b_win']:.1%}")
                
                st.sidebar.markdown(f"**Predicted Winner:** {result['predicted_winner']}")
                st.sidebar.markdown(f"**Confidence:** {result['confidence']:.1%}")
            else:
                col1, col2 = st.sidebar.columns(2)
                with col1:
                    st.metric("Team A Win", f"{result['p_a_win']:.1%}")
                with col2:
                    st.metric("Team B Win", f"{result['p_b_win']:.1%}")
                
                st.sidebar.markdown(f"**Predicted Winner:** {result['predicted_winner']}")
                st.sidebar.markdown(f"**Confidence:** {result['confidence']:.1%}")
            
            # Show PowerScores
            st.sidebar.markdown("### PowerScores")
            st.sidebar.markdown(f"**{result['team_a']}:** {result['ps_a']:.3f}")
            st.sidebar.markdown(f"**{result['team_b']}:** {result['ps_b']:.3f}")
            
    except Exception as e:
        st.sidebar.error(f"Prediction failed: {str(e)}")

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("🏆 Current Rankings (V5.2b)")
    
    # Display rankings table with styling
    display_cols = ["Team", "GamesPlayed", "PowerScore", "SAO_norm", "SAD_norm", "SOS_norm"]
    available_cols = [col for col in display_cols if col in rankings.columns]
    
    if available_cols:
        rankings_display = rankings[available_cols].copy()
        rankings_display = rankings_display.sort_values("PowerScore", ascending=False)
        rankings_display["Rank"] = range(1, len(rankings_display) + 1)
        
        # Reorder columns to put Rank first
        cols = ["Rank"] + [col for col in rankings_display.columns if col != "Rank"]
        rankings_display = rankings_display[cols]
        
        # Style the dataframe
        styled_df = rankings_display.style.background_gradient(
            cmap="YlGnBu", 
            subset=["PowerScore"]
        ).format({
            "PowerScore": "{:.3f}",
            "SAO_norm": "{:.3f}",
            "SAD_norm": "{:.3f}",
            "SOS_norm": "{:.3f}"
        })
        
        st.dataframe(styled_df, use_container_width=True)
    else:
        st.dataframe(rankings.head(20), use_container_width=True)

with col2:
    st.subheader("📊 Model Performance")
    
    if predictions is not None:
        try:
            metrics = evaluate_predictions(predictions)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Model Accuracy", f"{metrics['accuracy']:.1%}")
            with col2:
                st.metric("Brier Score", f"{metrics['brier_score']:.4f}")
            
            st.metric("Games Evaluated", f"{metrics['total_games']:,}")
            
            # Performance interpretation
            if metrics['brier_score'] <= 0.25:
                st.success("✅ Excellent calibration")
            elif metrics['brier_score'] <= 0.30:
                st.info("✅ Good calibration")
            else:
                st.warning("⚠️ Poor calibration")
                
            if metrics['accuracy'] >= 0.60:
                st.success("✅ Strong predictive power")
            else:
                st.warning("⚠️ Weak predictive power")
                
        except Exception as e:
            st.error(f"Error calculating metrics: {str(e)}")
    else:
        st.warning("Predicted_Outcomes_v52b.csv not found. Run analytics module first.")

# Historical Predictions Explorer
st.subheader("📈 Historical Predictions (Validation Dataset)")

if predictions is not None:
    # Show sample of predictions
    sample_predictions = predictions.dropna(subset=["P_A_win", "P_B_win"]).sample(min(10, len(predictions)))
    
    display_cols = ["Team", "Opponent", "P_A_win", "P_Draw", "P_B_win", "PredictedWinner", "ActualWinner"]
    available_display_cols = [col for col in display_cols if col in sample_predictions.columns]
    
    if available_display_cols:
        st.dataframe(
            sample_predictions[available_display_cols].style.format({
                "P_A_win": "{:.1%}",
                "P_Draw": "{:.1%}",
                "P_B_win": "{:.1%}"
            }),
            use_container_width=True
        )
    
    # Calibration curve
    st.subheader("🎯 Calibration Curve")
    
    try:
        valid_predictions = predictions.dropna(subset=["P_A_win", "A_win_actual"])
        
        if len(valid_predictions) > 0:
            # Create bins for calibration
            bins = np.linspace(0, 1, 11)
            valid_predictions["bin"] = pd.cut(valid_predictions["P_A_win"], bins)
            
            # Calculate calibration
            calibration = valid_predictions.groupby("bin")["A_win_actual"].mean()
            bin_centers = bins[:-1] + 0.05
            
            # Create plot
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.plot(bin_centers, calibration, marker="o", linewidth=2, markersize=6)
            ax.plot([0, 1], [0, 1], '--', color='gray', alpha=0.7, label='Perfect Calibration')
            ax.set_xlabel("Predicted Probability")
            ax.set_ylabel("Actual Win Rate")
            ax.set_title("Model Calibration Curve")
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            st.pyplot(fig)
        else:
            st.warning("No valid predictions found for calibration curve")
            
    except Exception as e:
        st.error(f"Error creating calibration curve: {str(e)}")

else:
    st.warning("Predicted_Outcomes_v52b.csv not found. Run analytics module first.")

# Footer
st.markdown("---")
st.markdown("**Data Sources:** Rankings_v52b.csv, Team_Game_Histories_COMPREHENSIVE.csv")
st.markdown("**Model:** V5.2b with Strength-Adjusted Offense/Defense and SOS Stretching")
st.markdown("**Last Updated:** Generated from latest game data")




