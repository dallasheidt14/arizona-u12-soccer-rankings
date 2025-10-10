"""
analyze_sos_impact.py
Analyzes the impact of SOS stretching in V5.2b.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def analyze_sos_stretching():
    """Analyze the impact of SOS power stretching."""
    
    # Load V5.2a and V5.2b data
    v52a = pd.read_csv("Rankings_v52a.csv")
    v52b = pd.read_csv("Rankings_v52b.csv")
    
    # Normalize team names
    v52a["team"] = v52a["Team"].str.strip().str.lower()
    v52b["team"] = v52b["Team"].str.strip().str.lower()
    
    # Merge data
    merged = v52a.merge(v52b, on="team", how="inner", suffixes=("_v52a", "_v52b"))
    
    print("SOS Stretching Impact Analysis")
    print("=" * 60)
    
    # Basic statistics
    print(f"SOS Unique Values:")
    print(f"  V5.2a: {merged['SOS_norm_v52a'].nunique()}")
    print(f"  V5.2b: {merged['SOS_norm_v52b'].nunique()}")
    
    print(f"\nSOS Range:")
    print(f"  V5.2a: [{merged['SOS_norm_v52a'].min():.3f}, {merged['SOS_norm_v52a'].max():.3f}]")
    print(f"  V5.2b: [{merged['SOS_norm_v52b'].min():.3f}, {merged['SOS_norm_v52b'].max():.3f}]")
    
    # Teams with highest SOS gain
    merged["sos_gain"] = merged["SOS_norm_v52b"] - merged["SOS_norm_v52a"]
    top_sos_gainers = merged.nlargest(10, "sos_gain")[["team", "SOS_norm_v52a", "SOS_norm_v52b", "sos_gain"]]
    
    print(f"\nTop 10 SOS Gainers:")
    print("-" * 60)
    for _, row in top_sos_gainers.iterrows():
        print(f"{row['team']:<40} {row['SOS_norm_v52a']:.3f} -> {row['SOS_norm_v52b']:.3f} (+{row['sos_gain']:.3f})")
    
    # Correlation analysis
    sos_corr = np.corrcoef(merged["SOS_norm_v52a"], merged["SOS_norm_v52b"])[0, 1]
    print(f"\nSOS Correlation (V5.2a vs V5.2b): {sos_corr:.3f}")
    
    # PowerScore vs SOS correlation
    ps_sos_corr_v52a = np.corrcoef(merged["PowerScore_v52a"], merged["SOS_norm_v52a"])[0, 1]
    ps_sos_corr_v52b = np.corrcoef(merged["PowerScore_v52b"], merged["SOS_norm_v52b"])[0, 1]
    
    print(f"\nPowerScore vs SOS Correlation:")
    print(f"  V5.2a: {ps_sos_corr_v52a:.3f}")
    print(f"  V5.2b: {ps_sos_corr_v52b:.3f}")
    
    # Top teams SOS analysis
    print(f"\nTop 10 Teams SOS Analysis:")
    print("-" * 60)
    top_10_v52b = merged.nsmallest(10, "Rank_v52b")
    for _, row in top_10_v52b.iterrows():
        print(f"#{row['Rank_v52b']:2d} {row['team']:<40} SOS: {row['SOS_norm_v52b']:.3f}")
    
    # Strong schedule teams analysis
    print(f"\nStrong Schedule Teams SOS:")
    print("-" * 60)
    strong_teams = ["next level", "phoenix united", "dynamos", "gsa", "fc tucson"]
    for team_pattern in strong_teams:
        team_matches = merged[merged["team"].str.contains(team_pattern, case=False, na=False)]
        if len(team_matches) > 0:
            team_row = team_matches.iloc[0]
            print(f"{team_row['team']:<40} SOS: {team_row['SOS_norm_v52b']:.3f} Rank: #{team_row['Rank_v52b']}")
    
    return merged

def create_sos_plots(merged_data):
    """Create plots showing SOS distribution changes."""
    try:
        import matplotlib.pyplot as plt
        
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        
        # Plot 1: SOS distribution comparison
        axes[0, 0].hist(merged_data["SOS_norm_v52a"], bins=20, alpha=0.7, label="V5.2a", color="blue")
        axes[0, 0].hist(merged_data["SOS_norm_v52b"], bins=20, alpha=0.7, label="V5.2b", color="red")
        axes[0, 0].set_title("SOS Distribution Comparison")
        axes[0, 0].set_xlabel("SOS_norm")
        axes[0, 0].set_ylabel("Frequency")
        axes[0, 0].legend()
        
        # Plot 2: SOS stretching effect
        axes[0, 1].scatter(merged_data["SOS_norm_v52a"], merged_data["SOS_norm_v52b"], alpha=0.6)
        axes[0, 1].plot([0, 1], [0, 1], 'k--', alpha=0.5)
        axes[0, 1].set_title("SOS Stretching Effect")
        axes[0, 1].set_xlabel("V5.2a SOS")
        axes[0, 1].set_ylabel("V5.2b SOS")
        
        # Plot 3: PowerScore vs SOS correlation
        axes[1, 0].scatter(merged_data["SOS_norm_v52a"], merged_data["PowerScore_v52a"], alpha=0.6, label="V5.2a")
        axes[1, 0].scatter(merged_data["SOS_norm_v52b"], merged_data["PowerScore_v52b"], alpha=0.6, label="V5.2b")
        axes[1, 0].set_title("PowerScore vs SOS")
        axes[1, 0].set_xlabel("SOS_norm")
        axes[1, 0].set_ylabel("PowerScore")
        axes[1, 0].legend()
        
        # Plot 4: Rank vs SOS gain
        axes[1, 1].scatter(merged_data["Rank_v52b"], merged_data["sos_gain"], alpha=0.6)
        axes[1, 1].set_title("Rank vs SOS Gain")
        axes[1, 1].set_xlabel("V5.2b Rank")
        axes[1, 1].set_ylabel("SOS Gain")
        
        plt.tight_layout()
        plt.savefig("sos_analysis.png", dpi=150, bbox_inches="tight")
        print(f"\nPlots saved to: sos_analysis.png")
        
    except ImportError:
        print(f"\nMatplotlib not available - skipping plots")

if __name__ == "__main__":
    merged = analyze_sos_stretching()
    create_sos_plots(merged)




