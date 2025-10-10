"""
compare_v52_to_v52a.py
Compares rankings between V5.2 and V5.2a implementations.
Shows distribution improvements and stability gains.
"""
import pandas as pd
import numpy as np
from scipy.stats import spearmanr

# --- File paths ---
V52_FILE = "Rankings_v52.csv"
V52A_FILE = "Rankings_v52a.csv"

# --- Load both versions ---
v52 = pd.read_csv(V52_FILE)
v52a = pd.read_csv(V52A_FILE)

# --- Normalize column names ---
v52.columns = [c.strip().lower() for c in v52.columns]
v52a.columns = [c.strip().lower() for c in v52a.columns]

# --- Ensure consistent team casing ---
v52["team"] = v52["team"].str.strip().str.lower()
v52a["team"] = v52a["team"].str.strip().str.lower()

# --- Keep only team and rank ---
if "rank" not in v52.columns:
    v52["rank"] = v52["powerscore"].rank(ascending=False).astype(int)
if "rank" not in v52a.columns:
    v52a["rank"] = v52a["powerscore"].rank(ascending=False).astype(int)

v52 = v52[["team", "rank", "powerscore", "sao_norm", "sad_norm", "sos_norm", "gamesplayed"]].rename(
    columns={"rank": "v52_rank", "powerscore": "v52_score", "sao_norm": "v52_sao", "sad_norm": "v52_sad", "sos_norm": "v52_sos", "gamesplayed": "v52_gp"})
v52a = v52a[["team", "rank", "powerscore", "sao_norm", "sad_norm", "sos_norm", "gamesplayed"]].rename(
    columns={"rank": "v52a_rank", "powerscore": "v52a_score", "sao_norm": "v52a_sao", "sad_norm": "v52a_sad", "sos_norm": "v52a_sos", "gamesplayed": "v52a_gp"})

# --- Merge and compute deltas ---
merged = v52.merge(v52a, on="team", how="inner")
merged["delta_rank"] = merged["v52_rank"] - merged["v52a_rank"]
merged["delta_score"] = merged["v52a_score"] - merged["v52_score"]

# --- Distribution Analysis ---
print("\nDistribution Analysis:")
print("=" * 60)

# SAO/SAD smoothness check
v52_binary_sao = ((merged["v52_sao"] == 0.0) | (merged["v52_sao"] == 1.0)).mean()
v52a_binary_sao = ((merged["v52a_sao"] == 0.0) | (merged["v52a_sao"] == 1.0)).mean()

v52_binary_sad = ((merged["v52_sad"] == 0.0) | (merged["v52_sad"] == 1.0)).mean()
v52a_binary_sad = ((merged["v52a_sad"] == 0.0) | (merged["v52a_sad"] == 1.0)).mean()

print(f"SAO Binary (0.0 or 1.0): V5.2={v52_binary_sao:.1%}, V5.2a={v52a_binary_sao:.1%}")
print(f"SAD Binary (0.0 or 1.0): V5.2={v52_binary_sad:.1%}, V5.2a={v52a_binary_sad:.1%}")

# Smooth range check (0.05 to 0.95)
v52_smooth_sao = merged["v52_sao"].between(0.05, 0.95).mean()
v52a_smooth_sao = merged["v52a_sao"].between(0.05, 0.95).mean()

v52_smooth_sad = merged["v52_sad"].between(0.05, 0.95).mean()
v52a_smooth_sad = merged["v52a_sad"].between(0.05, 0.95).mean()

print(f"SAO Smooth Range: V5.2={v52_smooth_sao:.1%}, V5.2a={v52a_smooth_sao:.1%}")
print(f"SAD Smooth Range: V5.2={v52_smooth_sad:.1%}, V5.2a={v52a_smooth_sad:.1%}")

# SOS variation
v52_sos_unique = merged["v52_sos"].nunique()
v52a_sos_unique = merged["v52a_sos"].nunique()

print(f"SOS Unique Values: V5.2={v52_sos_unique}, V5.2a={v52a_sos_unique}")

# --- Top 10 Analysis ---
print("\nTop 10 Teams Comparison:")
print("=" * 60)

top10_v52 = merged.nsmallest(10, "v52_rank")[["team", "v52_rank", "v52a_rank", "v52_gp", "v52a_gp"]]
top10_v52a = merged.nsmallest(10, "v52a_rank")[["team", "v52_rank", "v52a_rank", "v52_gp", "v52a_gp"]]

print("V5.2 Top 10:")
for _, row in top10_v52.iterrows():
    print(f"{row['v52_rank']:2d} -> {row['v52a_rank']:2d} {row['team']:<40} GP:{row['v52_gp']}")

print("\nV5.2a Top 10:")
for _, row in top10_v52a.iterrows():
    print(f"{row['v52_rank']:2d} -> {row['v52a_rank']:2d} {row['team']:<40} GP:{row['v52a_gp']}")

# --- Provisional Protection ---
print("\nProvisional Protection Analysis:")
print("=" * 60)

top20_v52 = merged.nsmallest(20, "v52_rank")
top20_v52a = merged.nsmallest(20, "v52a_rank")

low_gp_v52 = (top20_v52["v52_gp"] < 10).sum()
low_gp_v52a = (top20_v52a["v52a_gp"] < 10).sum()

print(f"Teams with <10 games in top 20: V5.2={low_gp_v52}, V5.2a={low_gp_v52a}")

# --- Spearman correlation ---
corr, p_value = spearmanr(merged["v52_rank"], merged["v52a_rank"])
print(f"\nSpearman Correlation: {corr:.3f} (p={p_value:.3f})")
print(f"Stability Check: {'PASS' if 0.6 <= corr <= 0.8 else 'FAIL'} (expect 0.6-0.8)")

# --- Summary stats ---
print(f"\nSummary Statistics:")
print(f"Teams analyzed: {len(merged)}")
print(f"Average rank change: {merged['delta_rank'].mean():.1f}")
print(f"Max rank improvement: +{merged['delta_rank'].max()}")
print(f"Max rank decline: {merged['delta_rank'].min()}")

# --- Save comparison ---
merged.to_csv("V52_vs_V52a_Rank_Comparison.csv", index=False)
print(f"\nDetailed comparison saved to: V52_vs_V52a_Rank_Comparison.csv")




