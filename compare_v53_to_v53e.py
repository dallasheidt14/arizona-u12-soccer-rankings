#!/usr/bin/env python3
"""
V5.3 vs V5.3E Enhanced Rankings Comparison
==========================================

This script compares the standard V5.3 rankings with the enhanced V5.3E rankings
that include adaptive K-factor and outlier guards.

Analysis includes:
- Rank movement analysis
- PowerScore changes
- Spearman correlation
- Top teams comparison
- Teams most affected by enhancements

Usage:
    python compare_v53_to_v53e.py
"""

import pandas as pd
import numpy as np
import subprocess
import os
from scipy.stats import spearmanr
import matplotlib.pyplot as plt


def run_rankings_scripts():
    """Run both V5.3 and V5.3E ranking scripts."""
    print("Running V5.3 rankings...")
    result_v53 = subprocess.run([
        "python", "rankings/generate_team_rankings_v53.py",
        "--in", "Matched_Games.csv",
        "--out", "Rankings_v53.csv"
    ], capture_output=True, text=True)
    
    if result_v53.returncode != 0:
        raise RuntimeError(f"V5.3 rankings failed: {result_v53.stderr}")
    
    print("Running V5.3E enhanced rankings...")
    result_v53e = subprocess.run([
        "python", "rankings/generate_team_rankings_v53_enhanced.py",
        "--in", "Matched_Games.csv",
        "--out", "Rankings_v53_enhanced.csv"
    ], capture_output=True, text=True)
    
    if result_v53e.returncode != 0:
        raise RuntimeError(f"V5.3E rankings failed: {result_v53e.stderr}")
    
    print("Both ranking scripts completed successfully")


def load_rankings():
    """Load both ranking files."""
    v53 = pd.read_csv("Rankings_v53.csv")
    v53e = pd.read_csv("Rankings_v53_enhanced.csv")
    
    # Ensure Team column is string type for merging
    v53["Team"] = v53["Team"].astype(str)
    v53e["Team"] = v53e["Team"].astype(str)
    
    return v53, v53e


def analyze_rank_movement(v53, v53e):
    """Analyze rank movement between versions."""
    print("\n" + "="*60)
    print("RANK MOVEMENT ANALYSIS")
    print("="*60)
    
    # Merge rankings on Team
    merged = v53[["Team", "Rank", "PowerScore"]].merge(
        v53e[["Team", "Rank", "PowerScore"]], 
        on="Team", 
        suffixes=("_v53", "_v53e")
    )
    
    # Calculate rank movement
    merged["Rank_Movement"] = merged["Rank_v53"] - merged["Rank_v53e"]
    merged["PowerScore_Change"] = merged["PowerScore_v53e"] - merged["PowerScore_v53"]
    
    # Summary statistics
    print(f"Teams analyzed: {len(merged)}")
    print(f"Average rank movement: {merged['Rank_Movement'].mean():.2f}")
    print(f"Median rank movement: {merged['Rank_Movement'].median():.2f}")
    print(f"Max rank improvement: {merged['Rank_Movement'].max()}")
    print(f"Max rank decline: {merged['Rank_Movement'].min()}")
    
    # Teams with significant movement
    significant_movement = merged[abs(merged["Rank_Movement"]) >= 5]
    print(f"\nTeams with >=5 rank movement: {len(significant_movement)}")
    
    if len(significant_movement) > 0:
        print("\nTop 10 largest rank improvements:")
        top_improvements = significant_movement.nlargest(10, "Rank_Movement")
        for _, row in top_improvements.iterrows():
            print(f"  {row['Team']}: {row['Rank_v53']} -> {row['Rank_v53e']} (+{row['Rank_Movement']})")
        
        print("\nTop 10 largest rank declines:")
        top_declines = significant_movement.nsmallest(10, "Rank_Movement")
        for _, row in top_declines.iterrows():
            print(f"  {row['Team']}: {row['Rank_v53']} -> {row['Rank_v53e']} ({row['Rank_Movement']})")
    
    return merged


def analyze_powerscore_changes(merged):
    """Analyze PowerScore changes between versions."""
    print("\n" + "="*60)
    print("POWERSCORE CHANGES ANALYSIS")
    print("="*60)
    
    # PowerScore change statistics
    print(f"Average PowerScore change: {merged['PowerScore_Change'].mean():.4f}")
    print(f"Median PowerScore change: {merged['PowerScore_Change'].median():.4f}")
    print(f"Max PowerScore increase: {merged['PowerScore_Change'].max():.4f}")
    print(f"Max PowerScore decrease: {merged['PowerScore_Change'].min():.4f}")
    
    # Teams with significant PowerScore changes
    significant_ps_change = merged[abs(merged["PowerScore_Change"]) >= 0.01]
    print(f"\nTeams with >=0.01 PowerScore change: {len(significant_ps_change)}")
    
    if len(significant_ps_change) > 0:
        print("\nTop 10 largest PowerScore increases:")
        top_increases = significant_ps_change.nlargest(10, "PowerScore_Change")
        for _, row in top_increases.iterrows():
            print(f"  {row['Team']}: {row['PowerScore_v53']:.3f} -> {row['PowerScore_v53e']:.3f} (+{row['PowerScore_Change']:.3f})")
        
        print("\nTop 10 largest PowerScore decreases:")
        top_decreases = significant_ps_change.nsmallest(10, "PowerScore_Change")
        for _, row in top_decreases.iterrows():
            print(f"  {row['Team']}: {row['PowerScore_v53']:.3f} -> {row['PowerScore_v53e']:.3f} ({row['PowerScore_Change']:.3f})")


def calculate_correlation(merged):
    """Calculate Spearman correlation between versions."""
    print("\n" + "="*60)
    print("CORRELATION ANALYSIS")
    print("="*60)
    
    # Rank correlation
    rank_corr, rank_p = spearmanr(merged["Rank_v53"], merged["Rank_v53e"])
    print(f"Rank correlation (Spearman): {rank_corr:.4f} (p={rank_p:.4f})")
    
    # PowerScore correlation
    ps_corr, ps_p = spearmanr(merged["PowerScore_v53"], merged["PowerScore_v53e"])
    print(f"PowerScore correlation (Spearman): {ps_corr:.4f} (p={ps_p:.4f})")
    
    # Interpretation
    if rank_corr > 0.95:
        print("Excellent rank stability")
    elif rank_corr > 0.90:
        print("Good rank stability")
    elif rank_corr > 0.80:
        print("Moderate rank changes")
    else:
        print("Significant rank changes")
    
    return rank_corr, ps_corr


def compare_top_teams(v53, v53e, n=20):
    """Compare top N teams between versions."""
    print(f"\n" + "="*60)
    print(f"TOP {n} TEAMS COMPARISON")
    print("="*60)
    
    top_v53 = v53.head(n)
    top_v53e = v53e.head(n)
    
    print(f"{'Rank':<4} {'Team':<40} {'V5.3':<8} {'V5.3E':<8} {'Change':<8}")
    print("-" * 80)
    
    for i in range(n):
        team_v53 = top_v53.iloc[i]["Team"]
        ps_v53 = top_v53.iloc[i]["PowerScore"]
        
        # Find same team in V5.3E
        team_v53e_row = v53e[v53e["Team"] == team_v53]
        if len(team_v53e_row) > 0:
            rank_v53e = team_v53e_row.iloc[0]["Rank"]
            ps_v53e = team_v53e_row.iloc[0]["PowerScore"]
            change = ps_v53e - ps_v53
            print(f"{i+1:<4} {team_v53:<40} {ps_v53:<8.3f} {ps_v53e:<8.3f} {change:+.3f}")
        else:
            print(f"{i+1:<4} {team_v53:<40} {ps_v53:<8.3f} {'N/A':<8} {'N/A':<8}")


def analyze_games_played_impact(merged):
    """Analyze impact of enhancements on teams with different game counts."""
    print("\n" + "="*60)
    print("GAMES PLAYED IMPACT ANALYSIS")
    print("="*60)
    
    # Get games played from V5.3E (should be same as V5.3)
    v53e = pd.read_csv("Rankings_v53_enhanced.csv")
    merged_with_gp = merged.merge(v53e[["Team", "GamesPlayed"]], on="Team")
    
    # Group by games played ranges
    merged_with_gp["GP_Range"] = pd.cut(
        merged_with_gp["GamesPlayed"], 
        bins=[0, 5, 10, 15, 20, 30, 100], 
        labels=["1-5", "6-10", "11-15", "16-20", "21-30", "30+"]
    )
    
    gp_analysis = merged_with_gp.groupby("GP_Range").agg({
        "Rank_Movement": ["mean", "std", "count"],
        "PowerScore_Change": ["mean", "std"]
    }).round(3)
    
    print("Impact by Games Played Range:")
    print(gp_analysis)
    
    # Teams with low games (likely affected by adaptive K)
    low_gp_teams = merged_with_gp[merged_with_gp["GamesPlayed"] < 8]
    if len(low_gp_teams) > 0:
        print(f"\nTeams with <8 games (adaptive K impact): {len(low_gp_teams)}")
        print(f"Average rank movement: {low_gp_teams['Rank_Movement'].mean():.2f}")
        print(f"Average PowerScore change: {low_gp_teams['PowerScore_Change'].mean():.4f}")


def save_comparison_report(merged):
    """Save detailed comparison report to CSV."""
    output_file = "V53_vs_V53E_Rank_Comparison.csv"
    
    # Add additional analysis columns
    merged["Abs_Rank_Movement"] = abs(merged["Rank_Movement"])
    merged["Abs_PowerScore_Change"] = abs(merged["PowerScore_Change"])
    
    # Sort by rank movement for easy analysis
    merged_sorted = merged.sort_values("Abs_Rank_Movement", ascending=False)
    
    # Select key columns for output
    output_cols = [
        "Team", "Rank_v53", "Rank_v53e", "Rank_Movement", 
        "PowerScore_v53", "PowerScore_v53e", "PowerScore_Change",
        "Abs_Rank_Movement", "Abs_PowerScore_Change"
    ]
    
    merged_sorted[output_cols].to_csv(output_file, index=False)
    print(f"\nDetailed comparison saved to: {output_file}")


def main():
    """Main comparison analysis."""
    print("V5.3 vs V5.3E Enhanced Rankings Comparison")
    print("="*60)
    
    try:
        # Run ranking scripts
        run_rankings_scripts()
        
        # Load rankings
        v53, v53e = load_rankings()
        
        # Perform analysis
        merged = analyze_rank_movement(v53, v53e)
        analyze_powerscore_changes(merged)
        rank_corr, ps_corr = calculate_correlation(merged)
        compare_top_teams(v53, v53e)
        analyze_games_played_impact(merged)
        
        # Save detailed report
        save_comparison_report(merged)
        
        print("\n" + "="*60)
        print("COMPARISON SUMMARY")
        print("="*60)
        print(f"\nRank correlation: {rank_corr:.4f}")
        print(f"PowerScore correlation: {ps_corr:.4f}")
        print(f"Teams analyzed: {len(merged)}")
        print(f"Detailed report saved to: V53_vs_V53E_Rank_Comparison.csv")
        
        if rank_corr > 0.90:
            print("\nEnhanced rankings show excellent stability with V5.3!")
        elif rank_corr > 0.80:
            print("\nEnhanced rankings show good stability with V5.3")
        else:
            print("\nEnhanced rankings show significant changes from V5.3")
        
    except Exception as e:
        print(f"Comparison failed: {e}")
        raise


if __name__ == "__main__":
    main()
