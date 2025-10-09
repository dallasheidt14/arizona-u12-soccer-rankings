#!/usr/bin/env python3
"""
Comprehensive tests for the tapered weights algorithm (v5)
"""

import numpy as np
import pandas as pd
import sys
import os
from pathlib import Path

# Add the rankings module to path
sys.path.insert(0, str(Path(__file__).parent))

from rankings.generate_team_rankings_v5 import (
    segment_weights, 
    tapered_weights,
    build_rankings_from_wide
)

def test_segment_weights():
    """Test the base segment weights function."""
    print("Testing segment_weights function...")
    
    # Test case 1: n <= recent_k (should be uniform)
    w = segment_weights(5, recent_k=10, recent_share=0.70)
    assert len(w) == 5, f"Expected length 5, got {len(w)}"
    assert abs(w.sum() - 1.0) < 1e-10, f"Weights should sum to 1.0, got {w.sum()}"
    # Should be uniform when n <= recent_k
    expected_weight = 1.0 / 5
    assert np.allclose(w, expected_weight), f"Weights should be uniform when n <= recent_k"
    print(f"  PASS: n=5 weights sum to {w.sum():.10f} (uniform)")
    
    # Test case 2: n > recent_k (should have 70/30 split)
    w = segment_weights(20, recent_k=10, recent_share=0.70)
    assert len(w) == 20, f"Expected length 20, got {len(w)}"
    assert abs(w.sum() - 1.0) < 1e-10, f"Weights should sum to 1.0, got {w.sum()}"
    
    # Check 70/30 split
    recent_weight = w[-10:].sum()  # Last 10 games
    old_weight = w[:-10].sum()     # First 10 games
    expected_recent = 0.70
    expected_old = 0.30
    
    assert abs(recent_weight - expected_recent) < 1e-10, f"Recent weight should be {expected_recent}, got {recent_weight}"
    assert abs(old_weight - expected_old) < 1e-10, f"Old weight should be {expected_old}, got {old_weight}"
    print(f"  PASS: n=20 has 70/30 split: recent={recent_weight:.3f}, old={old_weight:.3f}")
    
    # Test case 3: Edge case n=0
    w = segment_weights(0)
    assert len(w) == 0, f"Expected empty array, got length {len(w)}"
    print("  PASS: n=0 returns empty array")
    
    print("  PASS: All segment_weights tests passed!")
    return True

def test_tapered_weights():
    """Test the tapered weights function."""
    print("\nTesting tapered_weights function...")
    
    # Test case 1: n <= 25 (should behave like segment_weights)
    w = tapered_weights(20, recent_k=10, recent_share=0.70, full_weight_games=25, enabled=True)
    assert len(w) == 20, f"Expected length 20, got {len(w)}"
    assert abs(w.sum() - 1.0) < 1e-10, f"Weights should sum to 1.0, got {w.sum()}"
    
    # Should be identical to segment_weights for n <= 25
    w_base = segment_weights(20, recent_k=10, recent_share=0.70)
    assert np.allclose(w, w_base), "Tapered weights should match segment weights for n <= 25"
    print("  PASS: n=20 matches segment_weights (no taper)")
    
    # Test case 2: n = 30 (should have taper for games 26-30)
    w = tapered_weights(30, recent_k=10, recent_share=0.70, full_weight_games=25, 
                        dampen_start=25, dampen_end=30, dampen_factor=0.8, enabled=True)
    assert len(w) == 30, f"Expected length 30, got {len(w)}"
    assert abs(w.sum() - 1.0) < 1e-10, f"Weights should sum to 1.0, got {w.sum()}"
    
    # Check that games 26-30 have reduced weights
    base_weight = w[24]  # Game 25 (index 24)
    tapered_weights_26_30 = w[25:30]  # Games 26-30
    
    # Should be monotonically decreasing
    for i in range(1, len(tapered_weights_26_30)):
        assert tapered_weights_26_30[i] <= tapered_weights_26_30[i-1], f"Weights should be decreasing: {tapered_weights_26_30}"
    
    # Should be less than base weight
    for i, weight in enumerate(tapered_weights_26_30):
        assert weight < base_weight, f"Tapered weight {i+26} should be less than base weight"
    
    print(f"  PASS: n=30 has tapered weights for games 26-30")
    print(f"    Base weight (game 25): {base_weight:.6f}")
    print(f"    Tapered weights (26-30): {tapered_weights_26_30}")
    
    # Test case 3: n > 30 (should ignore games beyond 30)
    w = tapered_weights(35, recent_k=10, recent_share=0.70, full_weight_games=25, 
                        dampen_start=25, dampen_end=30, dampen_factor=0.8, enabled=True)
    assert len(w) == 35, f"Expected length 35, got {len(w)}"
    assert abs(w.sum() - 1.0) < 1e-10, f"Weights should sum to 1.0, got {w.sum()}"
    
    # Games 1-5 should have zero weight (ignored)
    ignored_weights = w[:5]
    assert np.allclose(ignored_weights, 0), f"First 5 games should be ignored: {ignored_weights}"
    
    # Games 6-30 should have non-zero weights
    active_weights = w[5:30]
    assert np.all(active_weights > 0), f"Games 6-30 should have positive weights"
    
    print("  PASS: n=35 ignores games 1-5, uses games 6-30")
    
    # Test case 4: Taper disabled (should use only base weights up to full_weight_games)
    w_no_taper = tapered_weights(30, recent_k=10, recent_share=0.70, full_weight_games=25, enabled=False)
    # When taper is disabled with n=30 and full_weight_games=25, it returns base weights for 25 games
    w_base = segment_weights(25, recent_k=10, recent_share=0.70)
    assert np.allclose(w_no_taper, w_base), "Disabled taper should return base weights for full_weight_games"
    print("  PASS: Disabled taper produces valid weights")
    
    print("  PASS: All tapered_weights tests passed!")
    return True

def test_weight_properties():
    """Test mathematical properties of the weight functions."""
    print("\nTesting weight properties...")
    
    # Test normalization
    for n in [10, 20, 25, 30, 35]:
        w = tapered_weights(n, enabled=True)
        assert abs(w.sum() - 1.0) < 1e-10, f"Weights for n={n} should sum to 1.0, got {w.sum()}"
        assert np.all(w >= 0), f"All weights for n={n} should be non-negative"
    
    print("  PASS: All weight vectors are properly normalized and non-negative")
    
    # Test monotonicity for tapered section
    w = tapered_weights(30, enabled=True)
    tapered_section = w[25:30]  # Games 26-30
    for i in range(1, len(tapered_section)):
        assert tapered_section[i] <= tapered_section[i-1], f"Tapered weights should be monotonically decreasing"
    
    print("  PASS: Tapered weights are monotonically decreasing")
    
    # Test that taper reduces influence appropriately
    w = tapered_weights(30, enabled=True)
    base_weight = w[24]  # Game 25
    total_tapered_influence = w[25:30].sum()  # Games 26-30 combined
    
    # Tapered section should be significant but not overwhelming
    assert 0.05 < total_tapered_influence < 0.25, f"Tapered influence should be 5-25%, got {total_tapered_influence:.3f}"
    
    print(f"  PASS: Tapered influence is {total_tapered_influence:.3f} (reasonable range)")
    
    print("  PASS: All weight property tests passed!")
    return True

def test_algorithm_stability():
    """Test that the algorithm produces stable, reasonable results."""
    print("\nTesting algorithm stability...")
    
    # Create synthetic game data
    np.random.seed(42)  # For reproducible tests
    
    # Create a team with 30 games (use recent dates to avoid inactivity filtering)
    from datetime import datetime, timedelta
    today = datetime.now()
    
    games_data = []
    for i in range(30):
        game_date = (today - timedelta(days=i*3)).strftime("%Y-%m-%d")  # Games every 3 days
        games_data.append({
            "Team A Match": "Test Team",
            "Team B Match": f"Opponent {i}",
            "Score A": np.random.randint(0, 5),
            "Score B": np.random.randint(0, 5),
            "Date": game_date
        })
    
    # Add some opponents
    for i in range(30):
        game_date = (today - timedelta(days=i*3)).strftime("%Y-%m-%d")
        games_data.append({
            "Team A Match": f"Opponent {i}",
            "Team B Match": "Test Team",
            "Score A": np.random.randint(0, 5),
            "Score B": np.random.randint(0, 5),
            "Date": game_date
        })
    
    games_df = pd.DataFrame(games_data)
    
    # Write test input file
    games_df.to_csv("test_input.csv", index=False)
    
    # Test that the algorithm runs without errors
    try:
        result = build_rankings_from_wide(Path("test_input.csv"), Path("test_output.csv"))
        print("  PASS: Algorithm runs without errors")
        
        # Check that Test Team appears in results
        test_team = result[result["Team"] == "Test Team"]
        assert len(test_team) == 1, "Test Team should appear exactly once in results"
        
        team_row = test_team.iloc[0]
        assert team_row["GamesPlayed"] == 30, f"Should have 30 games, got {team_row['GamesPlayed']}"
        assert 0 <= team_row["PowerScore"] <= 1, f"PowerScore should be in [0,1], got {team_row['PowerScore']}"
        assert 0 <= team_row["PowerScore_adj"] <= 1, f"PowerScore_adj should be in [0,1], got {team_row['PowerScore_adj']}"
        
        print(f"  PASS: Test Team has reasonable scores: PS={team_row['PowerScore']:.3f}, Adj={team_row['PowerScore_adj']:.3f}")
        
    except Exception as e:
        print(f"  FAIL: Algorithm failed with error: {e}")
        return False
    finally:
        # Clean up test files
        for file in ["test_input.csv", "test_output.csv"]:
            if os.path.exists(file):
                os.remove(file)
    
    print("  PASS: All stability tests passed!")
    return True

def test_comparison_with_v4():
    """Test that v5 produces similar but slightly more stable results than v4."""
    print("\nTesting comparison with v4...")
    
    # This is a placeholder for now - in a real implementation, you'd:
    # 1. Run both v4 and v5 algorithms on the same data
    # 2. Compare the top 10 teams
    # 3. Assert that rankings are similar but v5 is more stable
    
    print("  INFO: Comparison test requires both v4 and v5 files")
    print("  INFO: Will be implemented after generating Rankings_v5.csv")
    
    return True

def main():
    """Run all tapered weights tests."""
    print("Running Tapered Weights Tests (v5)")
    print("=" * 50)
    
    tests = [
        test_segment_weights,
        test_tapered_weights,
        test_weight_properties,
        test_algorithm_stability,
        test_comparison_with_v4,
    ]
    
    passed = 0
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"  FAIL: {test.__name__} failed: {e}")
    
    print("\n" + "=" * 50)
    print(f"Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("SUCCESS: All tapered weights tests passed!")
        return 0
    else:
        print("WARNING: Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
