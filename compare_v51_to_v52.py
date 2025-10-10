"""
compare_v51_to_v52.py
Compares rankings between V5.1 and V5.2 implementations.
Outputs movement (Δ Rank) for every team and highlights top gainers/droppers.
"""
import pandas as pd
import numpy as np
from scipy.stats import spearmanr

# --- File paths ---
V51_FILE = "Rankings_v51.csv"
V52_FILE = "Rankings_v52.csv"   # your new run output

# --- Load both versions ---
v51 = pd.read_csv(V51_FILE)
v52 = pd.read_csv(V52_FILE)

# --- Normalize column names ---
v51.columns = [c.strip().lower() for c in v51.columns]
v52.columns = [c.strip().lower() for c in v52.columns]

# --- Ensure consistent team casing ---
v51["team"] = v51["team"].str.strip().str.lower()
v52["team"] = v52["team"].str.strip().str.lower()

# --- Keep only team and rank ---
if "rank" not in v51.columns:
    v51["rank"] = v51["powerscore"].rank(ascending=False).astype(int)
if "rank" not in v52.columns:
    v52["rank"] = v52["powerscore"].rank(ascending=False).astype(int)

v51 = v51[["team", "rank", "powerscore"]].rename(columns={"rank": "v51_rank", "powerscore": "v51_score"})
v52 = v52[["team", "rank", "powerscore"]].rename(columns={"rank": "v52_rank", "powerscore": "v52_score"})

# --- Merge and compute deltas ---
merged = v51.merge(v52, on="team", how="inner")
merged["delta_rank"] = merged["v51_rank"] - merged["v52_rank"]
merged["delta_score"] = merged["v52_score"] - merged["v51_score"]

# --- Sort by improvement (positive delta_rank = moved up) ---
moved_up = merged.sort_values("delta_rank", ascending=False).head(15)
moved_down = merged.sort_values("delta_rank", ascending=True).head(15)

print("\nTop 15 Teams Moving UP in V5.2:")
print("=" * 60)
for _, row in moved_up.iterrows():
    print(f"{row['v52_rank']:2d} (+{row['delta_rank']:2d}) {row['team']:<40} {row['v52_score']:.3f}")

print("\nTop 15 Teams Moving DOWN in V5.2:")
print("=" * 60)
for _, row in moved_down.iterrows():
    print(f"{row['v52_rank']:2d} ({row['delta_rank']:2d}) {row['team']:<40} {row['v52_score']:.3f}")

# --- Spearman correlation ---
corr, p_value = spearmanr(merged["v51_rank"], merged["v52_rank"])
print(f"\nSpearman Correlation: {corr:.3f} (p={p_value:.3f})")
print(f"Stability Check: {'PASS' if corr >= 0.85 else 'FAIL'} (expect >= 0.85)")

# --- Summary stats ---
print(f"\nSummary Statistics:")
print(f"Teams analyzed: {len(merged)}")
print(f"Average rank change: {merged['delta_rank'].mean():.1f}")
print(f"Max rank improvement: +{merged['delta_rank'].max()}")
print(f"Max rank decline: {merged['delta_rank'].min()}")

# --- Save comparison ---
merged.to_csv("V51_vs_V52_Rank_Comparison.csv", index=False)
print(f"\nDetailed comparison saved to: V51_vs_V52_Rank_Comparison.csv")




