#!/usr/bin/env python3
"""
Monitor script to check alias resolver progress
"""

import os
import time
from datetime import datetime

def monitor_progress():
    """Monitor the progress of the alias resolver"""
    print("=== MONITORING ALIAS RESOLVER PROGRESS ===")
    
    # Check for alias table
    alias_file = 'data/mappings/team_alias_table.csv'
    if os.path.exists(alias_file):
        with open(alias_file, 'r') as f:
            lines = f.readlines()
        print(f"✅ Alias table exists with {len(lines)-1} entries")
        if len(lines) > 1:
            print(f"Latest entry: {lines[-1].strip()}")
    else:
        print("❌ Alias table not yet created")
    
    # Check for delta logs
    logs_dir = 'data/mappings/logs'
    if os.path.exists(logs_dir):
        log_files = [f for f in os.listdir(logs_dir) if f.endswith('.csv')]
        if log_files:
            print(f"✅ Found {len(log_files)} delta log files")
            latest_log = max(log_files, key=lambda x: os.path.getctime(os.path.join(logs_dir, x)))
            print(f"Latest log: {latest_log}")
        else:
            print("❌ No delta log files found")
    else:
        print("❌ Logs directory not found")
    
    # Check for output files
    output_dir = 'data/output'
    if os.path.exists(output_dir):
        output_files = [f for f in os.listdir(output_dir) if 'ALIAS' in f]
        if output_files:
            print(f"✅ Found {len(output_files)} ALIAS output files")
            latest_output = max(output_files, key=lambda x: os.path.getctime(os.path.join(output_dir, x)))
            print(f"Latest output: {latest_output}")
        else:
            print("❌ No ALIAS output files found")
    else:
        print("❌ Output directory not found")

if __name__ == "__main__":
    monitor_progress()
