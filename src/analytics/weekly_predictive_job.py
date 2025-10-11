"""
Weekly Predictive Job Automation Script (V5.3+)

This script provides automated weekly backtesting and calibration for the predictive
backbone system. It can be run manually or via GitHub Actions for continuous
monitoring of model performance.

Key Features:
- CLI interface with configurable parameters
- Automatic data loading and validation
- Backtest execution with multiple split modes
- Calibration plot generation
- CSV metrics logging
- Error handling and graceful degradation

Author: Youth Soccer Rankings System
Version: V5.3+
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import sys
import os
import traceback
from typing import Optional, Dict, Any

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from analytics.predictive_backbone_v53 import (
    load_games_and_rankings,
    run_backtest,
    plot_calibration_curve,
    BacktestResult
)
from analytics.feature_builders_v53 import (
    default_feature_builder,
    power_plus_elo_feature_builder,
    comprehensive_feature_builder,
    minimal_feature_builder
)


def setup_output_directory(outdir: str) -> Path:
    """
    Create output directory if it doesn't exist.
    
    Args:
        outdir: Output directory path
        
    Returns:
        Path object for output directory
    """
    output_path = Path(outdir)
    output_path.mkdir(parents=True, exist_ok=True)
    return output_path


def load_metrics_log(log_path: str) -> pd.DataFrame:
    """
    Load existing metrics log or create new one.
    
    Args:
        log_path: Path to metrics log CSV
        
    Returns:
        DataFrame with existing metrics
    """
    if Path(log_path).exists():
        try:
            df = pd.read_csv(log_path)
            print(f"Loaded existing metrics log with {len(df)} entries")
            return df
        except Exception as e:
            print(f"Warning: Could not load existing metrics log: {e}")
            print("Creating new metrics log")
    else:
        print("Creating new metrics log")
    
    # Create empty DataFrame with expected columns
    columns = [
        'timestamp', 'split_mode', 'calibration_method', 'feature_set',
        'n_train', 'n_test', 'brier_score', 'log_loss', 'auc',
        'calibration_slope', 'ece', 'notes'
    ]
    return pd.DataFrame(columns=columns)


def append_metrics_to_log(
    log_df: pd.DataFrame,
    result: BacktestResult,
    feature_set: str,
    notes: str = ""
) -> pd.DataFrame:
    """
    Append new metrics to the log DataFrame.
    
    Args:
        log_df: Existing metrics DataFrame
        result: BacktestResult with metrics
        feature_set: Name of feature set used
        notes: Additional notes
        
    Returns:
        Updated DataFrame with new metrics
    """
    # Calculate calibration slope from calibration curve
    calibration_slope = 1.0
    ece = 0.0
    
    if result.calibration_curve:
        curve_data = result.calibration_curve
        ece = curve_data.get('ece', 0.0)
        
        # Calculate slope from calibration curve
        bin_confidences = curve_data['bin_confidences']
        bin_accuracies = curve_data['bin_accuracies']
        
        if len(bin_confidences) > 1 and len(bin_accuracies) > 1:
            # Simple linear regression slope
            x_mean = np.mean(bin_confidences)
            y_mean = np.mean(bin_accuracies)
            
            numerator = sum((x - x_mean) * (y - y_mean) 
                           for x, y in zip(bin_confidences, bin_accuracies))
            denominator = sum((x - x_mean) ** 2 for x in bin_confidences)
            
            if denominator > 0:
                calibration_slope = numerator / denominator
    
    new_row = {
        'timestamp': datetime.now().isoformat(),
        'split_mode': result.split_mode,
        'calibration_method': result.calibration_method,
        'feature_set': feature_set,
        'n_train': result.n_train,
        'n_test': result.n_test,
        'brier_score': result.brier_score,
        'log_loss': result.log_loss,
        'auc': result.auc,
        'calibration_slope': calibration_slope,
        'ece': ece,
        'notes': notes
    }
    
    # Append new row
    new_df = pd.concat([log_df, pd.DataFrame([new_row])], ignore_index=True)
    
    print(f"Added metrics entry: Brier={result.brier_score:.4f}, AUC={result.auc:.4f}")
    return new_df


def save_metrics_log(log_df: pd.DataFrame, log_path: str) -> None:
    """
    Save metrics log to CSV.
    
    Args:
        log_df: Metrics DataFrame
        log_path: Path to save CSV
    """
    try:
        log_df.to_csv(log_path, index=False)
        print(f"Saved metrics log to {log_path}")
    except Exception as e:
        print(f"Error saving metrics log: {e}")


def generate_calibration_plot(
    result: BacktestResult,
    output_dir: Path,
    timestamp: str
) -> Optional[str]:
    """
    Generate and save calibration plot.
    
    Args:
        result: BacktestResult with calibration data
        output_dir: Output directory
        timestamp: Timestamp for filename
        
    Returns:
        Path to saved plot file
    """
    try:
        plot_filename = f"calibration_curve_{timestamp}.png"
        plot_path = output_dir / plot_filename
        
        # Generate plot
        plot_calibration_curve(result, str(plot_path))
        
        print(f"Calibration plot saved to {plot_path}")
        return str(plot_path)
        
    except Exception as e:
        print(f"Error generating calibration plot: {e}")
        return None


def parse_split_mode(split_str: str) -> tuple:
    """
    Parse split mode string.
    
    Args:
        split_str: Split mode string (e.g., "chronological:0.8" or "kfold:5")
        
    Returns:
        Tuple of (mode, parameter)
    """
    if ':' in split_str:
        mode, param = split_str.split(':', 1)
        if mode == 'chronological':
            return 'chronological', float(param)
        elif mode == 'kfold':
            return 'kfold', int(param)
        else:
            raise ValueError(f"Unknown split mode: {mode}")
    else:
        if split_str == 'chronological':
            return 'chronological', 0.8
        elif split_str == 'kfold':
            return 'kfold', 5
        else:
            raise ValueError(f"Unknown split mode: {split_str}")


def get_feature_builder(feature_set: str):
    """
    Get feature builder function by name.
    
    Args:
        feature_set: Name of feature set
        
    Returns:
        Feature builder function
    """
    builders = {
        'default': default_feature_builder,
        'power_plus_elo': power_plus_elo_feature_builder,
        'comprehensive': comprehensive_feature_builder,
        'minimal': minimal_feature_builder
    }
    
    if feature_set not in builders:
        raise ValueError(f"Unknown feature set: {feature_set}. Available: {list(builders.keys())}")
    
    return builders[feature_set]


def run_weekly_job(
    games_path: str,
    rankings_path: str,
    outdir: str,
    log_path: str,
    calibration: str = "isotonic",
    features: str = "power_plus_elo",
    split: str = "chronological:0.8",
    n_bins: int = 10,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Run the weekly predictive job.
    
    Args:
        games_path: Path to Matched_Games.csv
        rankings_path: Path to Rankings_v53.csv
        outdir: Output directory for plots
        log_path: Path to metrics log CSV
        calibration: Calibration method ("platt", "isotonic", "none")
        features: Feature set name
        split: Split mode string
        n_bins: Number of bins for calibration curve
        verbose: Whether to print verbose output
        
    Returns:
        Dictionary with job results
    """
    start_time = datetime.now()
    timestamp = start_time.strftime("%Y%m%d_%H%M%S")
    
    print(f"Starting weekly predictive job at {start_time}")
    print(f"Timestamp: {timestamp}")
    print(f"Games: {games_path}")
    print(f"Rankings: {rankings_path}")
    print(f"Output: {outdir}")
    print(f"Log: {log_path}")
    print(f"Calibration: {calibration}")
    print(f"Features: {features}")
    print(f"Split: {split}")
    print(f"Bins: {n_bins}")
    print("-" * 50)
    
    results = {
        'timestamp': timestamp,
        'success': False,
        'error': None,
        'metrics': None,
        'plot_path': None
    }
    
    try:
        # Setup output directory
        output_dir = setup_output_directory(outdir)
        
        # Load data
        print("Loading games and rankings data...")
        games_df, rankings_df = load_games_and_rankings(games_path, rankings_path)
        
        # Parse split mode
        split_mode, split_param = parse_split_mode(split)
        
        # Get feature builder
        feature_builder = get_feature_builder(features)
        
        # Run backtest
        print(f"Running backtest with {split_mode} split...")
        result = run_backtest(
            games_df=games_df,
            rankings_df=rankings_df,
            feature_fn=feature_builder,
            split_mode=split_mode,
            calibrated=(calibration != "none"),
            n_bins=n_bins,
            save_plots_dir=str(output_dir)
        )
        
        # Load existing metrics log
        log_df = load_metrics_log(log_path)
        
        # Append new metrics
        log_df = append_metrics_to_log(
            log_df, result, features, 
            f"Weekly job run at {timestamp}"
        )
        
        # Save metrics log
        save_metrics_log(log_df, log_path)
        
        # Generate calibration plot
        plot_path = generate_calibration_plot(result, output_dir, timestamp)
        
        # Store results
        results.update({
            'success': True,
            'metrics': {
                'brier_score': result.brier_score,
                'log_loss': result.log_loss,
                'auc': result.auc,
                'n_train': result.n_train,
                'n_test': result.n_test,
                'calibration_method': result.calibration_method
            },
            'plot_path': plot_path
        })
        
        # Print summary
        print("\n" + "=" * 50)
        print("WEEKLY JOB COMPLETED SUCCESSFULLY")
        print("=" * 50)
        print(f"Brier Score: {result.brier_score:.4f}")
        print(f"Log Loss: {result.log_loss:.4f}")
        print(f"AUC: {result.auc:.4f}")
        print(f"Calibration Method: {result.calibration_method}")
        print(f"Training Samples: {result.n_train}")
        print(f"Test Samples: {result.n_test}")
        
        if plot_path:
            print(f"Calibration Plot: {plot_path}")
        
        print(f"Metrics Log: {log_path}")
        
    except Exception as e:
        error_msg = f"Error in weekly job: {str(e)}"
        print(f"\nERROR: {error_msg}")
        
        if verbose:
            print("\nFull traceback:")
            traceback.print_exc()
        
        results.update({
            'success': False,
            'error': error_msg
        })
    
    end_time = datetime.now()
    duration = end_time - start_time
    print(f"\nJob completed in {duration.total_seconds():.1f} seconds")
    
    return results


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Weekly Predictive Job for Youth Soccer Rankings V5.3+",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic weekly job
  python -m analytics.weekly_predictive_job --games Matched_Games.csv --rankings Rankings_v53.csv
  
  # Custom parameters
  python -m analytics.weekly_predictive_job \\
    --games Matched_Games.csv \\
    --rankings Rankings_v53.csv \\
    --outdir predictive_reports \\
    --log predictive_metrics_log.csv \\
    --calibration isotonic \\
    --features power_plus_elo \\
    --split chronological:0.8 \\
    --bins 15 \\
    --verbose
        """
    )
    
    parser.add_argument(
        '--games', '-g',
        required=True,
        help='Path to Matched_Games.csv'
    )
    
    parser.add_argument(
        '--rankings', '-r',
        required=True,
        help='Path to Rankings_v53.csv'
    )
    
    parser.add_argument(
        '--outdir', '-o',
        default='predictive_reports',
        help='Output directory for plots (default: predictive_reports)'
    )
    
    parser.add_argument(
        '--log', '-l',
        default='predictive_metrics_log.csv',
        help='Path to metrics log CSV (default: predictive_metrics_log.csv)'
    )
    
    parser.add_argument(
        '--calibration', '-c',
        choices=['platt', 'isotonic', 'none'],
        default='isotonic',
        help='Calibration method (default: isotonic)'
    )
    
    parser.add_argument(
        '--features', '-f',
        choices=['default', 'power_plus_elo', 'comprehensive', 'minimal'],
        default='power_plus_elo',
        help='Feature set to use (default: power_plus_elo)'
    )
    
    parser.add_argument(
        '--split', '-s',
        default='chronological:0.8',
        help='Split mode: chronological:0.8 or kfold:5 (default: chronological:0.8)'
    )
    
    parser.add_argument(
        '--bins', '-b',
        type=int,
        default=10,
        help='Number of bins for calibration curve (default: 10)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Print verbose output including full tracebacks'
    )
    
    args = parser.parse_args()
    
    # Validate file paths
    if not Path(args.games).exists():
        print(f"Error: Games file not found: {args.games}")
        sys.exit(1)
    
    if not Path(args.rankings).exists():
        print(f"Error: Rankings file not found: {args.rankings}")
        sys.exit(1)
    
    # Run the job
    results = run_weekly_job(
        games_path=args.games,
        rankings_path=args.rankings,
        outdir=args.outdir,
        log_path=args.log,
        calibration=args.calibration,
        features=args.features,
        split=args.split,
        n_bins=args.bins,
        verbose=args.verbose
    )
    
    # Exit with appropriate code
    if results['success']:
        print("\n✅ Weekly job completed successfully!")
        sys.exit(0)
    else:
        print(f"\n❌ Weekly job failed: {results['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
