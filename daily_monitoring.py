"""
Daily Monitoring Fields - Phase C
Enhanced monitoring for production deployment
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import config

def generate_daily_monitoring_summary(
    rankings_df: pd.DataFrame,
    game_histories_df: pd.DataFrame,
    yesterday_date: datetime = None
) -> Dict[str, any]:
    """
    Generate daily monitoring summary for Slack/webhook.
    
    Returns:
        Dictionary with monitoring fields for production alerts
    """
    if yesterday_date is None:
        yesterday_date = datetime.now().date() - timedelta(days=1)
    
    summary = {
        "date": yesterday_date.isoformat(),
        "timestamp": datetime.now().isoformat()
    }
    
    # Expectation model status
    summary.update(get_expectation_model_status(game_histories_df))
    
    # Game activity metrics
    summary.update(get_game_activity_metrics(game_histories_df, yesterday_date))
    
    # Team resolution metrics
    summary.update(get_team_resolution_metrics())
    
    # Impact bucket distribution
    summary.update(get_impact_bucket_metrics(game_histories_df))
    
    # Anomaly detection
    summary.update(get_anomaly_alerts(rankings_df, game_histories_df, yesterday_date))
    
    return summary

def get_expectation_model_status(game_histories_df: pd.DataFrame) -> Dict[str, any]:
    """Get expectation model calibration status."""
    status = {
        "expect_calibrated": False,
        "calibration_gamma": 1.0,
        "calibration_delta": 0.0,
        "calibration_samples": 0
    }
    
    if "expected_gd" in game_histories_df.columns:
        valid_data = game_histories_df[game_histories_df["expected_gd"].notna()]
        
        if len(valid_data) > 0:
            # Check if model is calibrated (mean close to 0)
            mean_expected = valid_data["expected_gd"].mean()
            status["expect_calibrated"] = abs(mean_expected) < 0.15
            
            # Get calibration parameters (if available)
            if hasattr(config, 'EXPECT_CALIBRATE') and config.EXPECT_CALIBRATE:
                status["calibration_samples"] = len(valid_data)
                
                # Try to extract calibration info from logs or config
                # This would be enhanced with actual calibration storage
                status["calibration_gamma"] = 1.0  # Placeholder
                status["calibration_delta"] = 0.0  # Placeholder
    
    return status

def get_game_activity_metrics(game_histories_df: pd.DataFrame, target_date: datetime) -> Dict[str, int]:
    """Get game activity metrics for the target date."""
    target_date_str = target_date.strftime('%Y-%m-%d')
    
    # Filter games for target date
    if "Date" in game_histories_df.columns:
        game_histories_df["Date"] = pd.to_datetime(game_histories_df["Date"])
        target_games = game_histories_df[game_histories_df["Date"].dt.date == target_date]
        
        new_games = len(target_games)
        
        # Count changed games (simplified - would need historical comparison)
        changed_games = 0  # Placeholder for actual change detection
        
        return {
            "new_games": new_games,
            "changed_games": changed_games
        }
    
    return {"new_games": 0, "changed_games": 0}

def get_team_resolution_metrics() -> Dict[str, int]:
    """Get team resolution metrics."""
    unresolved_teams = 0
    
    # Check for unresolved teams in review queue
    review_path = "data_ingest/silver/team_resolution_review.csv"
    try:
        review_df = pd.read_csv(review_path)
        unresolved_teams = len(review_df)
    except FileNotFoundError:
        pass
    
    return {"unresolved_teams": unresolved_teams}

def get_impact_bucket_metrics(game_histories_df: pd.DataFrame) -> Dict[str, int]:
    """Get impact bucket distribution metrics."""
    bucket_counts = {
        "good_count": 0,
        "neutral_count": 0,
        "weak_count": 0,
        "no_data_count": 0
    }
    
    if "impact_bucket" in game_histories_df.columns:
        bucket_dist = game_histories_df["impact_bucket"].value_counts()
        
        bucket_counts["good_count"] = bucket_dist.get("good", 0)
        bucket_counts["neutral_count"] = bucket_dist.get("neutral", 0)
        bucket_counts["weak_count"] = bucket_dist.get("weak", 0)
        bucket_counts["no_data_count"] = bucket_dist.get("no_data", 0)
    
    return bucket_counts

def get_anomaly_alerts(
    rankings_df: pd.DataFrame,
    game_histories_df: pd.DataFrame,
    target_date: datetime
) -> Dict[str, List[str]]:
    """Detect anomalies and generate alerts."""
    alerts = []
    
    # Check for weekend with no games
    if target_date.weekday() in [5, 6]:  # Saturday or Sunday
        target_games = game_histories_df[
            pd.to_datetime(game_histories_df["Date"]).dt.date == target_date
        ]
        if len(target_games) == 0:
            alerts.append("No new games on weekend")
    
    # Check calibration sample threshold
    if "expected_gd" in game_histories_df.columns:
        valid_data = game_histories_df[game_histories_df["expected_gd"].notna()]
        if len(valid_data) < config.EXPECT_CALIB_MIN_SAMPLES:
            alerts.append(f"Calibration samples below threshold ({len(valid_data)} < {config.EXPECT_CALIB_MIN_SAMPLES})")
    
    # Check for inactive teams spike
    if "inactivity_flag" in rankings_df.columns:
        inactive_count = len(rankings_df[rankings_df["inactivity_flag"] == "inactive"])
        total_teams = len(rankings_df)
        inactive_percentage = (inactive_count / total_teams) * 100
        
        if inactive_percentage > 20:  # Alert if >20% inactive
            alerts.append(f"High inactive team percentage: {inactive_percentage:.1f}%")
    
    # Check for provisional teams spike
    if "provisional_flag" in rankings_df.columns:
        provisional_count = len(rankings_df[rankings_df["provisional_flag"] == "provisional"])
        total_teams = len(rankings_df)
        provisional_percentage = (provisional_count / total_teams) * 100
        
        if provisional_percentage > 30:  # Alert if >30% provisional
            alerts.append(f"High provisional team percentage: {provisional_percentage:.1f}%")
    
    return {"anomalies": alerts}

def format_slack_message(summary: Dict[str, any]) -> str:
    """Format monitoring summary as Slack message."""
    message = f"Daily Soccer Rankings Summary - {summary['date']}\n\n"
    
    # Expectation model status
    if summary["expect_calibrated"]:
        message += f"SUCCESS: Model Status: Calibrated (gamma={summary['calibration_gamma']:.2f}, delta={summary['calibration_delta']:.2f})\n"
    else:
        message += f"WARNING: Model Status: Not calibrated (using raw values)\n"
    
    # Game activity
    message += f"Activity: {summary['new_games']} new games, {summary['changed_games']} changed\n"
    
    # Team resolution
    if summary['unresolved_teams'] > 0:
        message += f"Resolution: {summary['unresolved_teams']} teams need review\n"
    
    # Impact buckets
    total_games = sum([
        summary['good_count'],
        summary['neutral_count'], 
        summary['weak_count'],
        summary['no_data_count']
    ])
    
    if total_games > 0:
        message += f"Impact Distribution: "
        message += f"Good: {summary['good_count']} ({summary['good_count']/total_games*100:.1f}%), "
        message += f"Neutral: {summary['neutral_count']} ({summary['neutral_count']/total_games*100:.1f}%), "
        message += f"Weak: {summary['weak_count']} ({summary['weak_count']/total_games*100:.1f}%)\n"
    
    # Anomalies
    if summary['anomalies']:
        message += f"\nAlerts:\n"
        for alert in summary['anomalies']:
            message += f"- {alert}\n"
    
    message += f"\n_Generated at {summary['timestamp']}_"
    
    return message

def save_monitoring_summary(summary: Dict[str, any], output_path: str = None):
    """Save monitoring summary to file."""
    if output_path is None:
        output_path = f"monitoring_summary_{summary['date']}.json"
    
    import json
    # Convert any non-serializable objects to strings
    serializable_summary = {}
    for key, value in summary.items():
        if isinstance(value, (bool, np.bool_)):
            serializable_summary[key] = bool(value)
        elif isinstance(value, (np.integer, np.floating)):
            serializable_summary[key] = float(value)
        else:
            serializable_summary[key] = value
    
    with open(output_path, 'w') as f:
        json.dump(serializable_summary, f, indent=2)
    
    return output_path

# Example usage
if __name__ == "__main__":
    # Load sample data
    try:
        rankings_df = pd.read_csv("Rankings_PowerScore.csv")
        game_histories_df = pd.read_csv("Team_Game_Histories.csv")
        
        # Generate summary
        summary = generate_daily_monitoring_summary(rankings_df, game_histories_df)
        
        # Format for Slack
        slack_message = format_slack_message(summary)
        print(slack_message)
        
        # Save summary
        output_file = save_monitoring_summary(summary)
        print(f"\nSummary saved to: {output_file}")
        
    except FileNotFoundError as e:
        print(f"Data files not found: {e}")
        print("Run the ranking system first to generate monitoring data.")
