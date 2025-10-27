#!/usr/bin/env python3
"""
Alias Confidence Report Generator

Generates diagnostic reports showing alias confidence distribution.
Helps identify clusters of borderline matches that might need manual cleanup.

Usage:
    python scripts/generate_alias_confidence_report.py
"""

import pandas as pd
import os
import sys
from datetime import datetime
from typing import Dict, List, Tuple

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

def load_alias_table(alias_csv_path: str) -> pd.DataFrame:
    """Load the main alias table."""
    if not os.path.exists(alias_csv_path):
        print(f"❌ Alias table not found: {alias_csv_path}")
        return pd.DataFrame()
    
    try:
        df = pd.read_csv(alias_csv_path)
        print(f"✅ Loaded {len(df)} aliases from {alias_csv_path}")
        return df
    except Exception as e:
        print(f"❌ Error loading alias table: {e}")
        return pd.DataFrame()

def calculate_confidence_distribution(df: pd.DataFrame) -> Dict[str, int]:
    """
    Calculate confidence distribution across different ranges.
    
    Args:
        df: DataFrame with alias data
        
    Returns:
        Dictionary with confidence ranges and counts
    """
    if df.empty or 'confidence' not in df.columns:
        return {}
    
    # Convert confidence to numeric if it's not already
    df['confidence'] = pd.to_numeric(df['confidence'], errors='coerce')
    
    # Remove any NaN values
    df = df.dropna(subset=['confidence'])
    
    # Calculate distribution
    high_confidence = len(df[df['confidence'] >= 0.9])
    medium_confidence = len(df[(df['confidence'] >= 0.8) & (df['confidence'] < 0.9)])
    low_confidence = len(df[df['confidence'] < 0.8])
    
    return {
        'high': high_confidence,
        'medium': medium_confidence,
        'low': low_confidence,
        'total': len(df)
    }

def generate_confidence_report(distribution: Dict[str, int]) -> str:
    """
    Generate a formatted confidence report.
    
    Args:
        distribution: Confidence distribution dictionary
        
    Returns:
        Formatted report string
    """
    if not distribution:
        return "No confidence data available."
    
    report_lines = [
        "🧩 Alias Confidence Report",
        "━" * 35,
        f"> 0.9  : {distribution['high']:4d} aliases ✅ (High confidence)",
        f"0.8-0.9: {distribution['medium']:4d} aliases ⚠️  (Medium confidence)",
        f"< 0.8  : {distribution['low']:4d} aliases 🔍 (Review suggested)",
        "━" * 35,
        f"Total  : {distribution['total']:4d} aliases"
    ]
    
    return "\n".join(report_lines)

def get_low_confidence_aliases(df: pd.DataFrame, threshold: float = 0.8) -> pd.DataFrame:
    """
    Get aliases with low confidence scores for review.
    
    Args:
        df: DataFrame with alias data
        threshold: Confidence threshold (default 0.8)
        
    Returns:
        DataFrame with low confidence aliases
    """
    if df.empty or 'confidence' not in df.columns:
        return pd.DataFrame()
    
    df['confidence'] = pd.to_numeric(df['confidence'], errors='coerce')
    low_conf_df = df[df['confidence'] < threshold].copy()
    
    # Sort by confidence (lowest first)
    low_conf_df = low_conf_df.sort_values('confidence')
    
    return low_conf_df

def save_low_confidence_report(low_conf_df: pd.DataFrame, output_path: str):
    """Save low confidence aliases to CSV for review."""
    if low_conf_df.empty:
        print("ℹ️  No low confidence aliases found.")
        return
    
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save to CSV
        low_conf_df.to_csv(output_path, index=False)
        print(f"📋 Saved {len(low_conf_df)} low confidence aliases to: {output_path}")
        
    except Exception as e:
        print(f"❌ Error saving low confidence report: {e}")

def generate_detailed_stats(df: pd.DataFrame) -> str:
    """
    Generate detailed statistics about the alias table.
    
    Args:
        df: DataFrame with alias data
        
    Returns:
        Detailed statistics string
    """
    if df.empty:
        return "No data available for detailed statistics."
    
    stats_lines = [
        "\n📊 Detailed Statistics:",
        "━" * 25,
        f"Total aliases: {len(df)}",
        f"Unique canonical teams: {df['canonical_team_name'].nunique() if 'canonical_team_name' in df.columns else 'N/A'}",
        f"Average confidence: {df['confidence'].mean():.3f}" if 'confidence' in df.columns else "N/A",
        f"Median confidence: {df['confidence'].median():.3f}" if 'confidence' in df.columns else "N/A",
        f"Min confidence: {df['confidence'].min():.3f}" if 'confidence' in df.columns else "N/A",
        f"Max confidence: {df['confidence'].max():.3f}" if 'confidence' in df.columns else "N/A"
    ]
    
    return "\n".join(stats_lines)

def main():
    """Main function for generating alias confidence report."""
    print("=== ALIAS CONFIDENCE REPORT GENERATOR ===")
    
    # File paths
    alias_csv_path = "data/mappings/team_alias_table.csv"
    low_conf_output_path = "data/mappings/review/low_confidence_aliases.csv"
    
    # Load alias table
    df = load_alias_table(alias_csv_path)
    if df.empty:
        print("\n📋 To generate this report:")
        print("1. Run the alias resolver to create team_alias_table.csv")
        print("2. Run this script again")
        return
    
    # Calculate confidence distribution
    distribution = calculate_confidence_distribution(df)
    
    # Generate and display report
    report = generate_confidence_report(distribution)
    print(f"\n{report}")
    
    # Generate detailed statistics
    detailed_stats = generate_detailed_stats(df)
    print(detailed_stats)
    
    # Get low confidence aliases
    low_conf_df = get_low_confidence_aliases(df)
    
    # Save low confidence report
    save_low_confidence_report(low_conf_df, low_conf_output_path)
    
    # Recommendations
    print(f"\n💡 Recommendations:")
    if distribution['low'] > 0:
        print(f"   • Review {distribution['low']} low confidence aliases")
        print(f"   • Check low_confidence_aliases.csv for manual cleanup")
    if distribution['medium'] > 0:
        print(f"   • Consider reviewing {distribution['medium']} medium confidence aliases")
    if distribution['high'] > distribution['total'] * 0.8:
        print(f"   • Great! {distribution['high']}/{distribution['total']} aliases are high confidence")
    else:
        print(f"   • Consider improving matching thresholds or normalization")

if __name__ == "__main__":
    main()
