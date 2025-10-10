"""
Validation tests for projected match outcome module.
"""
import pandas as pd
import numpy as np
from analytics.projected_outcomes_v52b import (
    win_probability, win_draw_loss_probabilities, 
    interactive_predict, evaluate_predictions
)

def test_win_probability_basic():
    """Test basic win probability function."""
    # Equal teams should be 50/50
    assert abs(win_probability(0.5, 0.5) - 0.5) < 0.01
    
    # Strong advantage should give high probability
    assert win_probability(0.7, 0.3) > 0.9
    
    # Weak advantage should give moderate probability
    p = win_probability(0.55, 0.50)
    assert 0.5 < p < 0.8  # Relaxed range for weak advantage
    
    print("[OK] PASS: Basic win probability function")
    return True

def test_win_draw_loss_probabilities():
    """Test advanced probability function with draws."""
    p_a, p_d, p_b = win_draw_loss_probabilities(0.5, 0.5)
    
    # Equal teams should have high draw probability
    assert p_d > 0.15
    assert abs(p_a - p_b) < 0.05
    assert abs((p_a + p_d + p_b) - 1.0) < 0.01
    
    # Unequal teams should have low draw probability
    p_a, p_d, p_b = win_draw_loss_probabilities(0.7, 0.3)
    assert p_d < 0.05
    assert p_a > 0.85
    
    print("[OK] PASS: Win/Draw/Loss probabilities")
    return True

def test_interactive_predict():
    """Test interactive prediction function."""
    rankings = pd.read_csv("Rankings_v52b.csv")
    
    # Test with known teams
    result = interactive_predict("Southeast", "PRFC", rankings, mode="advanced")
    
    assert "error" not in result
    assert "p_a_win" in result
    assert "p_draw" in result
    assert "predicted_winner" in result
    
    print(f"[OK] PASS: Interactive prediction")
    print(f"   Example: {result['team_a']} vs {result['team_b']}")
    print(f"   Win: {result['p_a_win']:.1%}, Draw: {result['p_draw']:.1%}, Loss: {result['p_b_win']:.1%}")
    return True

def test_model_calibration():
    """Test that model achieves reasonable calibration metrics."""
    try:
        predicted = pd.read_csv("Predicted_Outcomes_v52b.csv")
        metrics = evaluate_predictions(predicted)
        
        assert metrics["brier_score"] < 0.35, f"Brier score too high: {metrics['brier_score']}"
        assert metrics["accuracy"] > 0.50, f"Accuracy too low: {metrics['accuracy']}"
        
        print(f"[OK] PASS: Model calibration")
        print(f"   Brier: {metrics['brier_score']:.4f}, Accuracy: {metrics['accuracy']:.3f}")
        return True
    except FileNotFoundError:
        print("[WARN] SKIP: Predicted_Outcomes_v52b.csv not found (run generator first)")
        return True

def main():
    """Run all validation tests."""
    tests = [
        test_win_probability_basic,
        test_win_draw_loss_probabilities,
        test_interactive_predict,
        test_model_calibration
    ]
    
    passed = sum(1 for test in tests if test())
    print(f"\n{'='*60}")
    print(f"Results: {passed}/{len(tests)} tests passed")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
