"""
compare_v5_to_v51.py

Compares rankings between V5 and V5.1 implementations.
Outputs movement (Δ Rank) for every team and highlights top gainers/droppers.
"""

import pandas as pd

# --- File paths ---
V5_FILE = "Rankings_v5.csv"
V51_FILE = "Rankings_v51.csv"   # your new run output

# --- Load both versions ---
v5 = pd.read_csv(V5_FILE)
v51 = pd.read_csv(V51_FILE)

# --- Normalize column names ---
v5.columns = [c.strip().lower() for c in v5.columns]
v51.columns = [c.strip().lower() for c in v51.columns]

# --- Ensure consistent team casing ---
v5["team"] = v5["team"].str.strip().str.lower()
v51["team"] = v51["team"].str.strip().str.lower()

# --- Keep only team and rank ---
if "rank" not in v5.columns:
    v5["rank"] = v5["powerscore"].rank(ascending=False).astype(int)
if "rank" not in v51.columns:
    v51["rank"] = v51["powerscore"].rank(ascending=False).astype(int)

v5 = v5[["team", "rank", "powerscore"]].rename(columns={"rank": "v5_rank", "powerscore": "v5_score"})
v51 = v51[["team", "rank", "powerscore"]].rename(columns={"rank": "v51_rank", "powerscore": "v51_score"})

# --- Merge and compute deltas ---
merged = v5.merge(v51, on="team", how="inner")
merged["delta_rank"] = merged["v5_rank"] - merged["v51_rank"]
merged["delta_score"] = merged["v51_score"] - merged["v5_score"]

# --- Sort by improvement (positive delta_rank = moved up) ---
moved_up = merged.sort_values("delta_rank", ascending=False).head(15)
moved_down = merged.sort_values("delta_rank", ascending=True).head(15)

print("\nTop 15 Teams That Moved UP in V5.1:")
print(moved_up[["team", "v5_rank", "v51_rank", "delta_rank"]].to_string(index=False))

print("\nTop 15 Teams That Moved DOWN in V5.1:")
print(moved_down[["team", "v5_rank", "v51_rank", "delta_rank"]].to_string(index=False))

# --- Overall correlation ---
corr = merged["v5_rank"].corr(merged["v51_rank"], method="spearman")
print(f"\nSpearman rank correlation (V5 vs V5.1): {corr:.3f}")

# --- Save full comparison table ---
merged = merged.sort_values("v51_rank")
merged.to_csv("V5_vs_V51_Rank_Comparison.csv", index=False)
print("\nFull comparison saved to: V5_vs_V51_Rank_Comparison.csv")
