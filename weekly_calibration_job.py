#!/usr/bin/env python3
"""
Weekly Calibration Job Script (V5.3+)
=====================================

This script automates weekly calibration runs for the predictive backbone,
storing metrics over time and generating trend analysis reports.

Key Features:
- Automated calibration runs with different configurations
- Historical metrics storage and trend analysis
- Performance monitoring and alerting
- Report generation and export
- Integration with calibration storage system

Author: Youth Soccer Rankings System
Version: V5.3+
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import json

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent))

try:
    from analytics.predictive_backbone_v53 import (
        load_games_and_rankings, 
        run_backtest,
        default_feature_builder,
        power_plus_elo_feature_builder
    )
    from analytics.calibration_storage_v53 import CalibrationMetricsStorage, create_calibration_report
    from analytics.phase_c1_feature_builders import (
        elo_enhanced_feature_builder,
        convergence_aware_feature_builder,
        phase_c1_comprehensive_feature_builder
    )
except ImportError as e:
    print(f"Error importing required modules: {e}")
    sys.exit(1)


def run_weekly_calibration_job(
    games_file: str = "Matched_Games.csv",
    rankings_file: str = "Rankings_v53.csv",
    storage_file: str = "calibration_metrics.json",
    output_dir: str = "weekly_reports",
    configs: list = None
) -> dict:
    """
    Run weekly calibration job with multiple configurations.
    
    Args:
        games_file: Path to games data file
        rankings_file: Path to rankings data file
        storage_file: Path to calibration metrics storage file
        output_dir: Directory for output reports
        configs: List of configuration dictionaries
        
    Returns:
        Dictionary with job results
    """
    print("=" * 60)
    print("WEEKLY CALIBRATION JOB - V5.3+")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Games file: {games_file}")
    print(f"Rankings file: {rankings_file}")
    print(f"Storage file: {storage_file}")
    print(f"Output directory: {output_dir}")
    print()
    
    # Default configurations if none provided
    if configs is None:
        configs = [
            {
                "name": "Default Features",
                "feature_builder": default_feature_builder,
                "calibration_method": "Platt Scaling",
                "split_mode": "chronological"
            },
            {
                "name": "Power + ELO Features",
                "feature_builder": power_plus_elo_feature_builder,
                "calibration_method": "Isotonic Regression",
                "split_mode": "kfold"
            },
            {
                "name": "ELO Enhanced Features",
                "feature_builder": elo_enhanced_feature_builder,
                "calibration_method": "Platt Scaling",
                "split_mode": "chronological"
            },
            {
                "name": "Convergence Aware Features",
                "feature_builder": convergence_aware_feature_builder,
                "calibration_method": "Isotonic Regression",
                "split_mode": "kfold"
            },
            {
                "name": "Phase C1 Comprehensive",
                "feature_builder": phase_c1_comprehensive_feature_builder,
                "calibration_method": "Platt Scaling",
                "split_mode": "chronological"
            }
        ]
    
    # Initialize storage
    storage = CalibrationMetricsStorage(storage_file)
    
    # Load data
    print("Loading data...")
    try:
        games_df, rankings_df = load_games_and_rankings(games_file, rankings_file)
        print(f"Loaded {len(games_df)} games and {len(rankings_df)} team rankings")
    except Exception as e:
        print(f"Error loading data: {e}")
        return {"error": f"Data loading failed: {e}"}
    
    # Run calibrations
    results = []
    successful_runs = 0
    
    for i, config in enumerate(configs, 1):
        print(f"\n--- Configuration {i}/{len(configs)}: {config['name']} ---")
        
        try:
            # Run backtest
            result = run_backtest(
                games_df=games_df,
                rankings_df=rankings_df,
                feature_fn=config['feature_builder'],
                split_mode=config['split_mode'],
                calibrated=(config['calibration_method'] != "None")
            )
            
            # Store metrics
            storage.add_metrics(
                brier_score=result.brier_score,
                log_loss=result.log_loss,
                auc=result.auc,
                n_test=result.n_test,
                n_train=result.n_train,
                feature_set=config['name'],
                calibration_method=config['calibration_method'],
                split_mode=config['split_mode'],
                additional_metadata={
                    "config_id": i,
                    "run_timestamp": datetime.now().isoformat(),
                    "feature_count": len(result.feature_importance) if result.feature_importance else 0
                }
            )
            
            # Store result
            results.append({
                "config": config['name'],
                "brier_score": result.brier_score,
                "log_loss": result.log_loss,
                "auc": result.auc,
                "n_test": result.n_test,
                "n_train": result.n_train,
                "success": True
            })
            
            successful_runs += 1
            
            print(f"✅ Success: Brier={result.brier_score:.4f}, AUC={result.auc:.4f}")
            
        except Exception as e:
            print(f"❌ Failed: {e}")
            results.append({
                "config": config['name'],
                "error": str(e),
                "success": False
            })
    
    # Generate reports
    print(f"\n--- Generating Reports ---")
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Generate calibration report
    report_file = output_path / f"calibration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    report = create_calibration_report(storage, days_back=30, output_file=str(report_file))
    
    # Generate summary report
    summary_file = output_path / f"weekly_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    summary = {
        "job_timestamp": datetime.now().isoformat(),
        "total_configurations": len(configs),
        "successful_runs": successful_runs,
        "failed_runs": len(configs) - successful_runs,
        "results": results,
        "best_config": None,
        "trend_analysis": {}
    }
    
    # Find best configuration
    if successful_runs > 0:
        successful_results = [r for r in results if r['success']]
        best_result = min(successful_results, key=lambda x: x['brier_score'])
        summary['best_config'] = best_result['config']
        
        # Trend analysis
        for metric in ['brier_score', 'log_loss', 'auc']:
            trend = storage.get_trend_analysis(metric, days_back=7)
            if 'error' not in trend:
                summary['trend_analysis'][metric] = {
                    'direction': trend['trend_direction'],
                    'strength': trend['trend_strength'],
                    'change': trend['change']
                }
    
    # Save summary
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    # Export metrics
    export_file = output_path / f"metrics_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    storage.export_metrics(str(export_file), format="csv", days_back=30)
    
    # Print summary
    print(f"\n--- Job Summary ---")
    print(f"Total configurations: {len(configs)}")
    print(f"Successful runs: {successful_runs}")
    print(f"Failed runs: {len(configs) - successful_runs}")
    
    if summary['best_config']:
        print(f"Best configuration: {summary['best_config']}")
        print(f"Best Brier score: {best_result['brier_score']:.4f}")
    
    print(f"\nReports generated:")
    print(f"  - Calibration report: {report_file}")
    print(f"  - Weekly summary: {summary_file}")
    print(f"  - Metrics export: {export_file}")
    
    print(f"\nJob completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    return summary


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(
        description="Weekly Calibration Job for Predictive Backbone V5.3+",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python weekly_calibration_job.py
  python weekly_calibration_job.py --games-file Team_Game_Histories_COMPREHENSIVE.csv
  python weekly_calibration_job.py --output-dir reports --storage-file metrics.json
        """
    )
    
    parser.add_argument(
        "--games-file",
        default="Matched_Games.csv",
        help="Path to games data file (default: Matched_Games.csv)"
    )
    
    parser.add_argument(
        "--rankings-file",
        default="Rankings_v53.csv",
        help="Path to rankings data file (default: Rankings_v53.csv)"
    )
    
    parser.add_argument(
        "--storage-file",
        default="calibration_metrics.json",
        help="Path to calibration metrics storage file (default: calibration_metrics.json)"
    )
    
    parser.add_argument(
        "--output-dir",
        default="weekly_reports",
        help="Directory for output reports (default: weekly_reports)"
    )
    
    parser.add_argument(
        "--configs",
        nargs="+",
        choices=["default", "power_elo", "elo_enhanced", "convergence", "phase_c1"],
        default=["default", "power_elo", "elo_enhanced", "convergence", "phase_c1"],
        help="Configuration types to run (default: all)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be run without actually executing"
    )
    
    args = parser.parse_args()
    
    # Map config names to actual configurations
    config_map = {
        "default": {
            "name": "Default Features",
            "feature_builder": default_feature_builder,
            "calibration_method": "Platt Scaling",
            "split_mode": "chronological"
        },
        "power_elo": {
            "name": "Power + ELO Features",
            "feature_builder": power_plus_elo_feature_builder,
            "calibration_method": "Isotonic Regression",
            "split_mode": "kfold"
        },
        "elo_enhanced": {
            "name": "ELO Enhanced Features",
            "feature_builder": elo_enhanced_feature_builder,
            "calibration_method": "Platt Scaling",
            "split_mode": "chronological"
        },
        "convergence": {
            "name": "Convergence Aware Features",
            "feature_builder": convergence_aware_feature_builder,
            "calibration_method": "Isotonic Regression",
            "split_mode": "kfold"
        },
        "phase_c1": {
            "name": "Phase C1 Comprehensive",
            "feature_builder": phase_c1_comprehensive_feature_builder,
            "calibration_method": "Platt Scaling",
            "split_mode": "chronological"
        }
    }
    
    # Select configurations
    configs = [config_map[name] for name in args.configs if name in config_map]
    
    if args.dry_run:
        print("DRY RUN - Would execute the following configurations:")
        for i, config in enumerate(configs, 1):
            print(f"  {i}. {config['name']} ({config['calibration_method']}, {config['split_mode']})")
        print(f"\nWould use:")
        print(f"  Games file: {args.games_file}")
        print(f"  Rankings file: {args.rankings_file}")
        print(f"  Storage file: {args.storage_file}")
        print(f"  Output directory: {args.output_dir}")
        return
    
    # Run the job
    try:
        result = run_weekly_calibration_job(
            games_file=args.games_file,
            rankings_file=args.rankings_file,
            storage_file=args.storage_file,
            output_dir=args.output_dir,
            configs=configs
        )
        
        if "error" in result:
            print(f"Job failed: {result['error']}")
            sys.exit(1)
        else:
            print("Job completed successfully!")
            
    except KeyboardInterrupt:
        print("\nJob interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
