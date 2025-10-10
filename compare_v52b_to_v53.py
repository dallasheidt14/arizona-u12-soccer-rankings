#!/usr/bin/env python3
"""
compare_v52b_to_v53.py

Compares rankings between V5.2b and V5.3 implementations.
Outputs movement (delta Rank) for every team and highlights top gainers/droppers.
"""
import pandas as pd
import numpy as np

# --- File paths ---
V52B_FILE = "Rankings_v52b.csv"
V53_FILE = "Rankings_v53.csv"

# --- Load both versions ---
v52b = pd.read_csv(V52B_FILE)
v53 = pd.read_csv(V53_FILE)

# --- Normalize column names ---
v52b.columns = [c.strip().lower() for c in v52b.columns]
v53.columns = [c.strip().lower() for c in v53.columns]

# --- Ensure consistent team casing ---
v52b["team"] = v52b["team"].str.strip().str.lower()
v53["team"] = v53["team"].str.strip().str.lower()

# --- Keep only team and rank ---
if "rank" not in v52b.columns:
    v52b["rank"] = v52b["powerscore"].rank(ascending=False).astype(int)
if "rank" not in v53.columns:
    v53["rank"] = v53["powerscore"].rank(ascending=False).astype(int)

v52b = v52b[["team", "rank", "powerscore"]].rename(columns={"rank": "v52b_rank", "powerscore": "v52b_score"})
v53 = v53[["team", "rank", "powerscore"]].rename(columns={"rank": "v53_rank", "powerscore": "v53_score"})

# --- Merge and compute deltas ---
merged = v52b.merge(v53, on="team", how="inner")
merged["delta_rank"] = merged["v52b_rank"] - merged["v53_rank"]
merged["delta_score"] = merged["v53_score"] - merged["v52b_score"]

# --- Sort by improvement (positive delta_rank = moved up) ---
moved_up = merged.sort_values("delta_rank", ascending=False).head(15)
moved_down = merged.sort_values("delta_rank", ascending=True).head(15)

print("\nTop 15 Teams That Moved UP in V5.3:")
print(moved_up[["team", "v52b_rank", "v53_rank", "delta_rank"]].to_string(index=False))

print("\nTop 15 Teams That Moved DOWN in V5.3:")
print(moved_down[["team", "v52b_rank", "v53_rank", "delta_rank"]].to_string(index=False))

# --- Overall correlation ---
corr = merged["v52b_rank"].corr(merged["v53_rank"], method="spearman")
print(f"\nSpearman rank correlation (V5.2b vs V5.3): {corr:.3f}")

# --- Form analysis ---
print(f"\nForm Analysis:")
print(f"Teams with significant rank changes (|delta| >= 3): {len(merged[abs(merged['delta_rank']) >= 3])}")
print(f"Teams with moderate rank changes (|delta| >= 2): {len(merged[abs(merged['delta_rank']) >= 2])}")
print(f"Teams with minimal rank changes (|delta| <= 1): {len(merged[abs(merged['delta_rank']) <= 1])}")

# --- PowerScore analysis ---
print(f"\nPowerScore Analysis:")
print(f"Average PowerScore change: {merged['delta_score'].mean():.4f}")
print(f"PowerScore change std: {merged['delta_score'].std():.4f}")
print(f"Teams with PowerScore increase: {len(merged[merged['delta_score'] > 0])}")
print(f"Teams with PowerScore decrease: {len(merged[merged['delta_score'] < 0])}")

# --- Save full comparison table ---
merged = merged.sort_values("v53_rank")
merged.to_csv("V52B_vs_V53_Rank_Comparison.csv", index=False)
print("\nFull comparison saved to: V52B_vs_V53_Rank_Comparison.csv")

# --- Expected behavioral validation ---
print(f"\nV5.3 Behavioral Validation:")
print(f"Expected correlation range: 0.85-0.95")
print(f"Actual correlation: {corr:.3f}")
if 0.85 <= corr <= 0.95:
    print("PASS: Correlation within expected range")
else:
    print("WARNING: Correlation outside expected range")

print(f"Expected teams with significant changes: 10-30")
print(f"Actual teams with |delta| >= 3: {len(merged[abs(merged['delta_rank']) >= 3])}")
if 10 <= len(merged[abs(merged['delta_rank']) >= 3]) <= 30:
    print("PASS: Significant changes within expected range")
else:
    print("WARNING: Too many/few significant changes")