#!/usr/bin/env python3
"""
Calibration Metrics Storage and Retrieval System (V5.3+)
======================================================

This module provides persistent storage and retrieval of calibration metrics
over time, enabling historical trend analysis and model performance tracking.

Key Features:
- JSON-based storage for calibration metrics
- Automatic timestamping and metadata tracking
- Trend analysis and visualization support
- Configuration-based performance comparison
- Export capabilities for external analysis

Author: Youth Soccer Rankings System
Version: V5.3+
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import os


class CalibrationMetricsStorage:
    """
    Handles storage and retrieval of calibration metrics over time.
    """
    
    def __init__(self, storage_file: str = "calibration_metrics.json"):
        """
        Initialize the calibration metrics storage.
        
        Args:
            storage_file: Path to JSON file for storing metrics
        """
        self.storage_file = Path(storage_file)
        self.metrics_history = self._load_metrics()
    
    def _load_metrics(self) -> List[Dict]:
        """Load existing metrics from storage file."""
        if self.storage_file.exists():
            try:
                with open(self.storage_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load metrics file: {e}")
                return []
        return []
    
    def _save_metrics(self) -> None:
        """Save metrics to storage file."""
        try:
            with open(self.storage_file, 'w') as f:
                json.dump(self.metrics_history, f, indent=2)
        except IOError as e:
            print(f"Error saving metrics: {e}")
    
    def add_metrics(
        self,
        brier_score: float,
        log_loss: float,
        auc: float,
        n_test: int,
        n_train: int,
        feature_set: str,
        calibration_method: str,
        split_mode: str,
        additional_metadata: Optional[Dict] = None
    ) -> None:
        """
        Add new calibration metrics to storage.
        
        Args:
            brier_score: Brier score metric
            log_loss: Log loss metric
            auc: Area under curve metric
            n_test: Number of test samples
            n_train: Number of training samples
            feature_set: Feature set used
            calibration_method: Calibration method used
            split_mode: Data split mode used
            additional_metadata: Additional metadata to store
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "brier_score": brier_score,
            "log_loss": log_loss,
            "auc": auc,
            "n_test": n_test,
            "n_train": n_train,
            "feature_set": feature_set,
            "calibration_method": calibration_method,
            "split_mode": split_mode,
            "metadata": additional_metadata or {}
        }
        
        self.metrics_history.append(entry)
        self._save_metrics()
    
    def get_metrics_history(
        self,
        days_back: Optional[int] = None,
        feature_set: Optional[str] = None,
        calibration_method: Optional[str] = None,
        split_mode: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Get metrics history with optional filtering.
        
        Args:
            days_back: Number of days to look back (None for all)
            feature_set: Filter by feature set
            calibration_method: Filter by calibration method
            split_mode: Filter by split mode
            
        Returns:
            DataFrame with filtered metrics history
        """
        df = pd.DataFrame(self.metrics_history)
        
        if df.empty:
            return df
        
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Filter by date range
        if days_back is not None:
            cutoff_date = datetime.now() - timedelta(days=days_back)
            df = df[df['timestamp'] >= cutoff_date]
        
        # Filter by configuration
        if feature_set is not None:
            df = df[df['feature_set'] == feature_set]
        
        if calibration_method is not None:
            df = df[df['calibration_method'] == calibration_method]
        
        if split_mode is not None:
            df = df[df['split_mode'] == split_mode]
        
        return df.sort_values('timestamp')
    
    def get_latest_metrics(self) -> Optional[Dict]:
        """Get the most recent calibration metrics."""
        if not self.metrics_history:
            return None
        
        return self.metrics_history[-1]
    
    def get_best_metrics(
        self,
        metric: str = "brier_score",
        minimize: bool = True,
        days_back: Optional[int] = None
    ) -> Optional[Dict]:
        """
        Get the best metrics based on a specific metric.
        
        Args:
            metric: Metric to optimize (brier_score, log_loss, auc)
            minimize: Whether to minimize (True) or maximize (False) the metric
            days_back: Number of days to look back
            
        Returns:
            Best metrics entry or None
        """
        df = self.get_metrics_history(days_back=days_back)
        
        if df.empty:
            return None
        
        if minimize:
            best_idx = df[metric].idxmin()
        else:
            best_idx = df[metric].idxmax()
        
        return df.loc[best_idx].to_dict()
    
    def get_trend_analysis(
        self,
        metric: str = "brier_score",
        days_back: Optional[int] = None
    ) -> Dict:
        """
        Perform trend analysis on a specific metric.
        
        Args:
            metric: Metric to analyze
            days_back: Number of days to look back
            
        Returns:
            Dictionary with trend analysis results
        """
        df = self.get_metrics_history(days_back=days_back)
        
        if df.empty or len(df) < 2:
            return {"error": "Insufficient data for trend analysis"}
        
        # Calculate trend
        x = np.arange(len(df))
        y = df[metric].values
        
        # Linear regression for trend
        coeffs = np.polyfit(x, y, 1)
        slope = coeffs[0]
        
        # Calculate trend direction and strength
        if abs(slope) < 0.001:
            trend_direction = "stable"
        elif slope > 0:
            trend_direction = "improving" if metric in ["auc"] else "worsening"
        else:
            trend_direction = "worsening" if metric in ["auc"] else "improving"
        
        # Calculate trend strength (R-squared)
        y_pred = np.polyval(coeffs, x)
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        # Calculate volatility
        volatility = df[metric].std()
        
        return {
            "metric": metric,
            "trend_direction": trend_direction,
            "trend_strength": r_squared,
            "slope": slope,
            "volatility": volatility,
            "latest_value": df[metric].iloc[-1],
            "earliest_value": df[metric].iloc[0],
            "change": df[metric].iloc[-1] - df[metric].iloc[0],
            "data_points": len(df)
        }
    
    def get_configuration_comparison(
        self,
        days_back: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Compare performance across different configurations.
        
        Args:
            days_back: Number of days to look back
            
        Returns:
            DataFrame with configuration comparison
        """
        df = self.get_metrics_history(days_back=days_back)
        
        if df.empty:
            return pd.DataFrame()
        
        # Group by configuration
        comparison = df.groupby(['feature_set', 'calibration_method', 'split_mode']).agg({
            'brier_score': ['mean', 'std', 'count'],
            'log_loss': ['mean', 'std'],
            'auc': ['mean', 'std'],
            'n_test': ['mean', 'sum']
        }).round(4)
        
        # Flatten column names
        comparison.columns = ['_'.join(col).strip() for col in comparison.columns]
        
        return comparison.reset_index()
    
    def export_metrics(
        self,
        output_file: str,
        format: str = "csv",
        days_back: Optional[int] = None,
        **filters
    ) -> None:
        """
        Export metrics to file.
        
        Args:
            output_file: Output file path
            format: Export format (csv, json, excel)
            days_back: Number of days to look back
            **filters: Additional filters to apply
        """
        df = self.get_metrics_history(days_back=days_back, **filters)
        
        if df.empty:
            print("No data to export")
            return
        
        output_path = Path(output_file)
        
        if format.lower() == "csv":
            df.to_csv(output_path, index=False)
        elif format.lower() == "json":
            df.to_json(output_path, orient='records', indent=2)
        elif format.lower() == "excel":
            df.to_excel(output_path, index=False)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        print(f"Metrics exported to {output_path}")
    
    def get_summary_statistics(self, days_back: Optional[int] = None) -> Dict:
        """
        Get summary statistics for all metrics.
        
        Args:
            days_back: Number of days to look back
            
        Returns:
            Dictionary with summary statistics
        """
        df = self.get_metrics_history(days_back=days_back)
        
        if df.empty:
            return {"error": "No data available"}
        
        metrics = ['brier_score', 'log_loss', 'auc']
        summary = {}
        
        for metric in metrics:
            summary[metric] = {
                'mean': df[metric].mean(),
                'std': df[metric].std(),
                'min': df[metric].min(),
                'max': df[metric].max(),
                'median': df[metric].median(),
                'latest': df[metric].iloc[-1] if len(df) > 0 else None
            }
        
        summary['total_runs'] = len(df)
        summary['date_range'] = {
            'start': df['timestamp'].min().isoformat() if len(df) > 0 else None,
            'end': df['timestamp'].max().isoformat() if len(df) > 0 else None
        }
        
        return summary


def create_calibration_report(
    storage: CalibrationMetricsStorage,
    days_back: int = 30,
    output_file: Optional[str] = None
) -> str:
    """
    Create a comprehensive calibration report.
    
    Args:
        storage: CalibrationMetricsStorage instance
        days_back: Number of days to analyze
        output_file: Optional output file path
        
    Returns:
        Report text
    """
    report_lines = []
    report_lines.append("=" * 60)
    report_lines.append("CALIBRATION METRICS REPORT")
    report_lines.append("=" * 60)
    report_lines.append(f"Analysis Period: Last {days_back} days")
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")
    
    # Summary statistics
    summary = storage.get_summary_statistics(days_back=days_back)
    
    if "error" in summary:
        report_lines.append("No data available for the specified period.")
        return "\n".join(report_lines)
    
    report_lines.append("SUMMARY STATISTICS")
    report_lines.append("-" * 20)
    report_lines.append(f"Total Runs: {summary['total_runs']}")
    report_lines.append(f"Date Range: {summary['date_range']['start']} to {summary['date_range']['end']}")
    report_lines.append("")
    
    # Metric summaries
    for metric in ['brier_score', 'log_loss', 'auc']:
        report_lines.append(f"{metric.upper().replace('_', ' ')}")
        report_lines.append(f"  Latest: {summary[metric]['latest']:.4f}")
        report_lines.append(f"  Mean:   {summary[metric]['mean']:.4f}")
        report_lines.append(f"  Std:    {summary[metric]['std']:.4f}")
        report_lines.append(f"  Range:  {summary[metric]['min']:.4f} - {summary[metric]['max']:.4f}")
        report_lines.append("")
    
    # Trend analysis
    report_lines.append("TREND ANALYSIS")
    report_lines.append("-" * 15)
    
    for metric in ['brier_score', 'log_loss', 'auc']:
        trend = storage.get_trend_analysis(metric, days_back)
        if "error" not in trend:
            report_lines.append(f"{metric.upper().replace('_', ' ')}")
            report_lines.append(f"  Trend: {trend['trend_direction']} (strength: {trend['trend_strength']:.3f})")
            report_lines.append(f"  Change: {trend['change']:.4f}")
            report_lines.append("")
    
    # Configuration comparison
    report_lines.append("CONFIGURATION COMPARISON")
    report_lines.append("-" * 25)
    
    config_df = storage.get_configuration_comparison(days_back)
    if not config_df.empty:
        report_lines.append(config_df.to_string(index=False))
    else:
        report_lines.append("No configuration data available.")
    
    report_lines.append("")
    report_lines.append("=" * 60)
    
    report_text = "\n".join(report_lines)
    
    if output_file:
        with open(output_file, 'w') as f:
            f.write(report_text)
        print(f"Report saved to {output_file}")
    
    return report_text


# Example usage and testing
if __name__ == "__main__":
    # Create storage instance
    storage = CalibrationMetricsStorage("test_calibration_metrics.json")
    
    # Add some sample metrics
    storage.add_metrics(
        brier_score=0.2156,
        log_loss=0.6234,
        auc=0.7123,
        n_test=150,
        n_train=600,
        feature_set="Default",
        calibration_method="Platt Scaling",
        split_mode="chronological"
    )
    
    storage.add_metrics(
        brier_score=0.2089,
        log_loss=0.6156,
        auc=0.7234,
        n_test=145,
        n_train=580,
        feature_set="Power + ELO",
        calibration_method="Isotonic Regression",
        split_mode="kfold"
    )
    
    # Get history
    history_df = storage.get_metrics_history()
    print("Metrics History:")
    print(history_df)
    
    # Get trend analysis
    trend = storage.get_trend_analysis("brier_score")
    print("\nTrend Analysis:")
    print(trend)
    
    # Create report
    report = create_calibration_report(storage)
    print("\nCalibration Report:")
    print(report)
