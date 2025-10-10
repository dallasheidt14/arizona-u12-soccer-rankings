"""
compare_v52a_to_v52b.py
Compares rankings between V5.2a and V5.2b implementations.
Shows competitive tuning improvements and PRFC movement.
"""
import pandas as pd
import numpy as np
from scipy.stats import spearmanr

# --- File paths ---
V52A_FILE = "Rankings_v52a.csv"
V52B_FILE = "Rankings_v52b.csv"

# --- Load both versions ---
v52a = pd.read_csv(V52A_FILE)
v52b = pd.read_csv(V52B_FILE)

# --- Normalize column names ---
v52a.columns = [c.strip().lower() for c in v52a.columns]
v52b.columns = [c.strip().lower() for c in v52b.columns]

# --- Ensure consistent team casing ---
v52a["team"] = v52a["team"].str.strip().str.lower()
v52b["team"] = v52b["team"].str.strip().str.lower()

# --- Keep only team and rank ---
if "rank" not in v52a.columns:
    v52a["rank"] = v52a["powerscore"].rank(ascending=False).astype(int)
if "rank" not in v52b.columns:
    v52b["rank"] = v52b["powerscore"].rank(ascending=False).astype(int)

v52a = v52a[["team", "rank", "powerscore", "sao_norm", "sad_norm", "sos_norm", "gamesplayed"]].rename(
    columns={"rank": "v52a_rank", "powerscore": "v52a_score", "sao_norm": "v52a_sao", "sad_norm": "v52a_sad", "sos_norm": "v52a_sos", "gamesplayed": "v52a_gp"})
v52b = v52b[["team", "rank", "powerscore", "sao_norm", "sad_norm", "sos_norm", "gamesplayed"]].rename(
    columns={"rank": "v52b_rank", "powerscore": "v52b_score", "sao_norm": "v52b_sao", "sad_norm": "v52b_sad", "sos_norm": "v52b_sos", "gamesplayed": "v52b_gp"})

# --- Merge and compute deltas ---
merged = v52a.merge(v52b, on="team", how="inner")
merged["delta_rank"] = merged["v52a_rank"] - merged["v52b_rank"]
merged["delta_score"] = merged["v52b_score"] - merged["v52a_score"]

# --- PRFC Scottsdale Analysis ---
print("\nPRFC Scottsdale Movement:")
print("=" * 60)

prfc = merged[merged["team"].str.contains("prfc scottsdale", case=False, na=False)]
if len(prfc) > 0:
    prfc_row = prfc.iloc[0]
    print(f"V5.2a Rank: {prfc_row['v52a_rank']}")
    print(f"V5.2b Rank: {prfc_row['v52b_rank']}")
    print(f"Change: {prfc_row['delta_rank']:+d} positions")
    print(f"PowerScore: {prfc_row['v52a_score']:.4f} -> {prfc_row['v52b_score']:.4f}")
    print(f"SOS: {prfc_row['v52a_sos']:.3f} -> {prfc_row['v52b_sos']:.3f}")
else:
    print("PRFC Scottsdale not found")

# --- Top 10 Comparison ---
print("\nTop 10 Teams Comparison:")
print("=" * 60)

top10_v52a = merged.nsmallest(10, "v52a_rank")[["team", "v52a_rank", "v52b_rank", "v52a_gp", "v52b_gp"]]
top10_v52b = merged.nsmallest(10, "v52b_rank")[["team", "v52a_rank", "v52b_rank", "v52a_gp", "v52b_gp"]]

print("V5.2a Top 10:")
for _, row in top10_v52a.iterrows():
    print(f"{row['v52a_rank']:2d} -> {row['v52b_rank']:2d} {row['team']:<40} GP:{row['v52a_gp']}")

print("\nV5.2b Top 10:")
for _, row in top10_v52b.iterrows():
    print(f"{row['v52a_rank']:2d} -> {row['v52b_rank']:2d} {row['team']:<40} GP:{row['v52b_gp']}")

# --- Strong Schedule Teams Analysis ---
print("\nStrong Schedule Teams Movement:")
print("=" * 60)

strong_teams = ["next level", "phoenix united", "dynamos", "gsa", "fc tucson"]
for team_pattern in strong_teams:
    team_matches = merged[merged["team"].str.contains(team_pattern, case=False, na=False)]
    if len(team_matches) > 0:
        team_row = team_matches.iloc[0]
        print(f"{team_row['team']:<40} {team_row['v52a_rank']:2d} -> {team_row['v52b_rank']:2d} ({team_row['delta_rank']:+d})")

# --- SOS Distribution Analysis ---
print("\nSOS Distribution Analysis:")
print("=" * 60)

v52a_sos_unique = merged["v52a_sos"].nunique()
v52b_sos_unique = merged["v52b_sos"].nunique()

v52a_sos_range = merged["v52a_sos"].max() - merged["v52a_sos"].min()
v52b_sos_range = merged["v52b_sos"].max() - merged["v52b_sos"].min()

print(f"SOS Unique Values: V5.2a={v52a_sos_unique}, V5.2b={v52b_sos_unique}")
print(f"SOS Range: V5.2a={v52a_sos_range:.3f}, V5.2b={v52b_sos_range:.3f}")

# --- PowerScore Precision Analysis ---
print("\nPowerScore Precision Analysis:")
print("=" * 60)

top20_v52a = merged.nsmallest(20, "v52a_rank")
top20_v52b = merged.nsmallest(20, "v52b_rank")

v52a_ties = top20_v52a["v52a_score"].nunique()
v52b_ties = top20_v52b["v52b_score"].nunique()

print(f"Unique PowerScores in top 20: V5.2a={v52a_ties}, V5.2b={v52b_ties}")

# --- Spearman correlation ---
corr, p_value = spearmanr(merged["v52a_rank"], merged["v52b_rank"])
print(f"\nSpearman Correlation: {corr:.3f} (p={p_value:.3f})")
print(f"Stability Check: {'PASS' if 0.55 <= corr <= 0.70 else 'FAIL'} (expect 0.55-0.70)")

# --- Summary stats ---
print(f"\nSummary Statistics:")
print(f"Teams analyzed: {len(merged)}")
print(f"Average rank change: {merged['delta_rank'].mean():.1f}")
print(f"Max rank improvement: +{merged['delta_rank'].max()}")
print(f"Max rank decline: {merged['delta_rank'].min()}")

# --- Save comparison ---
merged.to_csv("V52a_vs_V52b_Rank_Comparison.csv", index=False)
print(f"\nDetailed comparison saved to: V52a_vs_V52b_Rank_Comparison.csv")




