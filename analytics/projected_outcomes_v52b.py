"""
Projected Match Outcome Module (V5.2b)

Transform the ranking system from descriptive to predictive by adding win/draw/loss 
probability calculations based on PowerScore differentials. Validate model accuracy 
using 18 months of historical data with Brier score and accuracy metrics.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.metrics import brier_score_loss, accuracy_score

# Configurable parameters
K_COEFFICIENT = 8.0  # Logistic steepness (6-10 range)
DRAW_WIDTH = 0.03    # PowerScore window for draw probability
DRAW_BASELINE = 0.20 # Base draw probability for equal teams


def win_probability(ps_a: float, ps_b: float, k: float = K_COEFFICIENT) -> float:
    """
    Simple logistic win probability based on PowerScore differential.
    
    Args:
        ps_a: Team A PowerScore
        ps_b: Team B PowerScore
        k: Steepness coefficient (default 8.0)
        
    Returns:
        Probability of Team A winning (0.0 to 1.0)
    """
    return 1.0 / (1.0 + np.exp(-k * (ps_a - ps_b)))


def win_draw_loss_probabilities(
    ps_a: float, 
    ps_b: float, 
    k: float = K_COEFFICIENT,
    draw_width: float = DRAW_WIDTH
) -> tuple[float, float, float]:
    """
    Advanced probability model with draw outcomes.
    
    Returns:
        (p_a_win, p_draw, p_b_win) summing to 1.0
    """
    diff = ps_a - ps_b
    p_a_win = 1.0 / (1.0 + np.exp(-k * diff))
    p_b_win = 1.0 - p_a_win
    
    # Draw probability peaks at equal PowerScores
    draw_factor = np.exp(-((diff / draw_width) ** 2))
    p_draw = DRAW_BASELINE * draw_factor
    
    # Normalize to sum to 1.0
    scale = p_a_win + p_b_win + p_draw
    return p_a_win / scale, p_draw / scale, p_b_win / scale


def add_predicted_outcomes(games_df: pd.DataFrame, rankings_df: pd.DataFrame, mode: str = "advanced") -> pd.DataFrame:
    """
    Merge PowerScores and compute predicted outcomes for historical games.
    
    Args:
        games_df: Historical games with TeamA, TeamB, ScoreA, ScoreB
        rankings_df: Rankings with Team, PowerScore
        mode: "simple" or "advanced" (with draws)
        
    Returns:
        Games dataframe with predicted probabilities
    """
    # Merge Team A PowerScores
    merged = games_df.merge(
        rankings_df[["Team", "PowerScore"]],
        left_on="Team", 
        right_on="Team", 
        how="left"
    ).rename(columns={"PowerScore": "PS_A"})
    
    # Merge Team B (opponent) PowerScores
    merged = merged.merge(
        rankings_df[["Team", "PowerScore"]],
        left_on="Opponent",
        right_on="Team",
        how="left",
        suffixes=("", "_opp")
    ).rename(columns={"PowerScore": "PS_B"})
    
    # Drop duplicate Team columns
    merged = merged.drop(columns=["Team_opp"], errors="ignore")
    
    if mode == "simple":
        merged["P_A_win"] = merged.apply(
            lambda row: win_probability(row["PS_A"], row["PS_B"]) 
            if pd.notna(row["PS_A"]) and pd.notna(row["PS_B"]) else np.nan,
            axis=1
        )
        merged["P_B_win"] = 1.0 - merged["P_A_win"]
        merged["P_Draw"] = 0.0
    else:
        # Advanced mode with draws
        probs = merged.apply(
            lambda row: win_draw_loss_probabilities(row["PS_A"], row["PS_B"])
            if pd.notna(row["PS_A"]) and pd.notna(row["PS_B"]) 
            else (np.nan, np.nan, np.nan),
            axis=1
        )
        merged["P_A_win"] = probs.apply(lambda x: x[0])
        merged["P_Draw"] = probs.apply(lambda x: x[1])
        merged["P_B_win"] = probs.apply(lambda x: x[2])
    
    # Determine predicted winner
    merged["PredictedWinner"] = merged.apply(
        lambda row: row["Team"] if row["P_A_win"] >= max(row["P_Draw"], row["P_B_win"])
        else ("Draw" if row["P_Draw"] >= row["P_B_win"] else row["Opponent"]),
        axis=1
    )
    
    return merged


def add_actual_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Add actual match outcomes for validation."""
    # Handle different column naming conventions
    gf_col = "GoalsFor" if "GoalsFor" in df.columns else "GF"
    ga_col = "GoalsAgainst" if "GoalsAgainst" in df.columns else "GA"
    
    df["ActualWinner"] = np.where(
        df[gf_col] > df[ga_col], df["Team"],
        np.where(df[ga_col] > df[gf_col], df["Opponent"], "Draw")
    )
    df["A_win_actual"] = (df["ActualWinner"] == df["Team"]).astype(int)
    return df


def evaluate_predictions(df: pd.DataFrame, mode: str = "advanced") -> dict:
    """
    Compute Brier score and accuracy for model calibration.
    
    Returns:
        dict with brier_score, accuracy, total_games
    """
    # Only use games with valid predictions
    valid = df.dropna(subset=["P_A_win", "A_win_actual"]).copy()
    
    if len(valid) == 0:
        return {"brier_score": np.nan, "accuracy": np.nan, "total_games": 0}
    
    # Brier score (lower is better, 0.20-0.25 is excellent)
    brier = brier_score_loss(valid["A_win_actual"], valid["P_A_win"])
    
    # Accuracy (% correct winner predictions)
    predicted_wins = (valid["P_A_win"] >= 0.5).astype(int)
    acc = accuracy_score(valid["A_win_actual"], predicted_wins)
    
    return {
        "brier_score": brier,
        "accuracy": acc,
        "total_games": len(valid)
    }


def print_evaluation_summary(metrics: dict):
    """Print formatted evaluation results."""
    print("\n" + "="*60)
    print("Model Evaluation Summary")
    print("="*60)
    print(f"Total Games Evaluated: {metrics['total_games']}")
    print(f"Brier Score: {metrics['brier_score']:.4f} (target: 0.20-0.25)")
    print(f"Accuracy: {metrics['accuracy']:.3f} (target: 0.60-0.65)")
    print("="*60)
    
    # Interpretation
    if metrics['brier_score'] <= 0.25:
        print("[OK] Excellent calibration - probabilities align well with reality")
    elif metrics['brier_score'] <= 0.30:
        print("[OK] Good calibration - model is reasonably accurate")
    else:
        print("[WARN] Poor calibration - consider adjusting k coefficient")
    
    if metrics['accuracy'] >= 0.60:
        print("[OK] Strong predictive power - correct winner ~2/3 of the time")
    else:
        print("[WARN] Weak predictive power - model needs improvement")


def interactive_predict(
    team_a: str, 
    team_b: str, 
    rankings_df: pd.DataFrame, 
    mode: str = "advanced"
) -> dict:
    """
    Predict outcome for a specific matchup.
    
    Args:
        team_a: Team A name (case-insensitive)
        team_b: Team B name (case-insensitive)
        rankings_df: Rankings dataframe
        mode: "simple" or "advanced"
        
    Returns:
        dict with probabilities and recommendation
    """
    # Case-insensitive lookup
    rankings_lower = rankings_df.copy()
    rankings_lower["Team_lower"] = rankings_lower["Team"].str.lower()
    
    team_a_lower = team_a.lower()
    team_b_lower = team_b.lower()
    
    match_a = rankings_lower[rankings_lower["Team_lower"].str.contains(team_a_lower, na=False)]
    match_b = rankings_lower[rankings_lower["Team_lower"].str.contains(team_b_lower, na=False)]
    
    if len(match_a) == 0:
        return {"error": f"Team '{team_a}' not found in rankings"}
    if len(match_b) == 0:
        return {"error": f"Team '{team_b}' not found in rankings"}
    
    ps_a = match_a.iloc[0]["PowerScore"]
    ps_b = match_b.iloc[0]["PowerScore"]
    team_a_full = match_a.iloc[0]["Team"]
    team_b_full = match_b.iloc[0]["Team"]
    
    if mode == "simple":
        p_a_win = win_probability(ps_a, ps_b)
        return {
            "team_a": team_a_full,
            "team_b": team_b_full,
            "ps_a": ps_a,
            "ps_b": ps_b,
            "p_a_win": p_a_win,
            "p_b_win": 1.0 - p_a_win,
            "predicted_winner": team_a_full if p_a_win >= 0.5 else team_b_full,
            "confidence": abs(p_a_win - 0.5) * 2
        }
    else:
        p_a, p_d, p_b = win_draw_loss_probabilities(ps_a, ps_b)
        winner = team_a_full if p_a >= max(p_d, p_b) else ("Draw" if p_d >= p_b else team_b_full)
        return {
            "team_a": team_a_full,
            "team_b": team_b_full,
            "ps_a": ps_a,
            "ps_b": ps_b,
            "p_a_win": p_a,
            "p_draw": p_d,
            "p_b_win": p_b,
            "predicted_winner": winner,
            "confidence": max(p_a, p_d, p_b)
        }


def calibration_sweep(games_df: pd.DataFrame, rankings_df: pd.DataFrame, k_range: list = None) -> pd.DataFrame:
    """
    Test multiple k coefficients to find optimal calibration.
    
    Args:
        games_df: Historical games
        rankings_df: Rankings with PowerScores
        k_range: List of k values to test (default [6, 7, 8, 9, 10])
        
    Returns:
        DataFrame with k, brier_score, accuracy for each coefficient
    """
    if k_range is None:
        k_range = [6.0, 7.0, 8.0, 9.0, 10.0]
    
    results = []
    
    for k in k_range:
        # Temporarily override K_COEFFICIENT
        global K_COEFFICIENT
        old_k = K_COEFFICIENT
        K_COEFFICIENT = k
        
        # Compute predictions
        predicted = add_predicted_outcomes(games_df, rankings_df, mode="simple")
        predicted = add_actual_outcomes(predicted)
        
        # Evaluate
        metrics = evaluate_predictions(predicted)
        results.append({
            "k": k,
            "brier_score": metrics["brier_score"],
            "accuracy": metrics["accuracy"],
            "total_games": metrics["total_games"]
        })
        
        # Restore original k
        K_COEFFICIENT = old_k
    
    return pd.DataFrame(results)


def generate_predicted_outcomes(
    rankings_path: str = "Rankings_v52b.csv",
    history_path: str = "Team_Game_Histories_COMPREHENSIVE.csv",
    output_path: str = "Predicted_Outcomes_v52b.csv",
    mode: str = "advanced"
) -> pd.DataFrame:
    """
    Main pipeline: generate predictions and save to CSV.
    """
    print(f"Loading rankings from {rankings_path}...")
    rankings = pd.read_csv(rankings_path)
    
    print(f"Loading historical games from {history_path}...")
    history = pd.read_csv(history_path)
    
    print(f"Computing predicted outcomes ({mode} mode)...")
    predicted = add_predicted_outcomes(history, rankings, mode=mode)
    predicted = add_actual_outcomes(predicted)
    
    print(f"Evaluating model performance...")
    metrics = evaluate_predictions(predicted, mode=mode)
    print_evaluation_summary(metrics)
    
    print(f"\nSaving predictions to {output_path}...")
    predicted.to_csv(output_path, index=False)
    
    return predicted


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate projected match outcomes")
    parser.add_argument("--rankings", default="Rankings_v52b.csv", help="Rankings CSV path")
    parser.add_argument("--history", default="Team_Game_Histories_COMPREHENSIVE.csv", help="Historical games CSV")
    parser.add_argument("--output", default="Predicted_Outcomes_v52b.csv", help="Output CSV path")
    parser.add_argument("--mode", choices=["simple", "advanced"], default="advanced", help="Prediction mode")
    parser.add_argument("--calibrate", action="store_true", help="Run calibration sweep")
    
    args = parser.parse_args()
    
    if args.calibrate:
        print("Running calibration sweep...")
        rankings = pd.read_csv(args.rankings)
        history = pd.read_csv(args.history)
        sweep_results = calibration_sweep(history, rankings)
        print("\nCalibration Sweep Results:")
        print(sweep_results.to_string(index=False))
        sweep_results.to_csv("calibration_sweep_results.csv", index=False)
    else:
        generate_predicted_outcomes(args.rankings, args.history, args.output, args.mode)
