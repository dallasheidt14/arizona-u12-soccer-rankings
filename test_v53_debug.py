#!/usr/bin/env python3
"""
test_v53_debug.py

Debug script to understand why V5.3 is making dramatic changes.
"""
import pandas as pd
import numpy as np

# Load both ranking files
v52b = pd.read_csv("Rankings_v52b.csv")
v53 = pd.read_csv("Rankings_v53.csv")

print("V5.2b top 10:")
print(v52b[["Rank", "Team", "PowerScore"]].head(10))

print("\nV5.3 top 10:")
print(v53[["Rank", "Team", "PowerScore"]].head(10))

print("\nPowerScore comparison (first 10 teams):")
comparison = v52b.merge(v53, on="Team", how="inner", suffixes=("_v52b", "_v53"))
comparison["PowerScore_diff"] = comparison["PowerScore_v53"] - comparison["PowerScore_v52b"]
print(comparison[["Team", "PowerScore_v52b", "PowerScore_v53", "PowerScore_diff"]].head(10))

print(f"\nMax PowerScore difference: {comparison['PowerScore_diff'].max():.4f}")
print(f"Min PowerScore difference: {comparison['PowerScore_diff'].min():.4f}")
print(f"Mean PowerScore difference: {comparison['PowerScore_diff'].mean():.4f}")
print(f"Std PowerScore difference: {comparison['PowerScore_diff'].std():.4f}")

# Check if the issue is with the Expected GD calculation
print("\nChecking if Expected GD calculation is the issue...")
print("The performance multiplier should be very small (±0.0037 max)")
print("But we're seeing large rank changes, suggesting the issue is elsewhere.")
