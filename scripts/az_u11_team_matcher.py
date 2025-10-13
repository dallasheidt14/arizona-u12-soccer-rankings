#!/usr/bin/env python3
"""
AZ U11 Game History Team Matcher (ID-aware, U12-style)
======================================================

Mirrors U12 normalize+fuzzy pipeline and reporting.
Produces:
  * data/mappings/az_boys_u11_2025/name_map.csv         (raw_name -> team_id, display_name)
  * data/logs/az_boys_u11_2025/unmatched.csv            (review queue; fail-fast if non-empty)
  * data/logs/az_boys_u11_2025/external_candidates.csv  (FYI only, auto-generated IDs)
  * data/outputs/az_boys_u11_2025/histories.csv         (ID-based, two-directional)
  * data/gold/Matched_Games_U11_COMPAT.csv              (TeamKey/OppKey... for v53 generator)
  * match_summary_u11.txt                               (console-style report like U12)
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

import pandas as pd
from src.pipelines.u11_team_matcher import run_u11_matching, MatchingResults

# ========= CONFIG (mirror U12 style) =========
FUZZY_MATCH_THRESHOLD = 90  # keep parity with U12
DIV = "az_boys_u11_2025"

MASTER   = Path(f"data/master/{DIV}/master_teams.csv")        # must have: gotsport_team_id,display_name
RAW      = Path(f"data/raw/{DIV}/games_raw.csv")              # expects Team A/Team B/Score A/Score B/Date
NAME_MAP = Path(f"data/mappings/{DIV}/name_map.csv")
UNMATCH  = Path(f"data/logs/{DIV}/unmatched.csv")
EXTERNAL = Path(f"data/logs/{DIV}/external_candidates.csv")
HIST     = Path(f"data/outputs/{DIV}/histories.csv")
COMPAT   = Path("data/gold/Matched_Games_U11_COMPAT.csv")     # legacy generator format
SUMMARY  = Path("match_summary_u11.txt")

def ensure_dirs():
    """Create necessary directories."""
    for p in (NAME_MAP.parent, UNMATCH.parent, HIST.parent, COMPAT.parent):
        p.mkdir(parents=True, exist_ok=True)

def main():
    """Main matching function."""
    print("AZ U11 Team Matcher (ID-aware, U12-style)")
    print("=" * 60)
    print(f"Fuzzy Match Threshold: {FUZZY_MATCH_THRESHOLD}%")
    ensure_dirs()

    # ===== Step 1: Validate inputs =====
    if not MASTER.exists():
        print(f"[ERROR] Master file not found: {MASTER}")
        return 1
    
    if not RAW.exists():
        print(f"[ERROR] Raw games file not found: {RAW}")
        return 1
    
    # Load and validate master
    master = pd.read_csv(MASTER)
    required_cols = {"gotsport_team_id", "display_name"}
    missing_cols = required_cols - set(master.columns)
    if missing_cols:
        print(f"[ERROR] Master missing required columns: {missing_cols}")
        return 1
    
    # Load games
    games = pd.read_csv(RAW)
    required_game_cols = {"Team A", "Team B", "Score A", "Score B", "Date"}
    missing_game_cols = required_game_cols - set(games.columns)
    if missing_game_cols:
        print(f"[ERROR] Games missing required columns: {missing_game_cols}")
        return 1
    
    print(f"[INFO] Loaded master teams: {len(master):,}")
    print(f"[INFO] Loaded raw games: {len(games):,}")

    # ===== Step 2: Run matching =====
    try:
        results = run_u11_matching(MASTER, RAW)
    except Exception as e:
        print(f"[ERROR] Matching failed: {e}")
        return 1

    # ===== Step 3: Write outputs =====
    
    # Name mapping
    results.name_mapping.to_csv(NAME_MAP, index=False)
    print(f"[OK] Wrote name_map: {NAME_MAP} ({len(results.name_mapping)} rows)")
    
    # Unmatched teams (fail-fast if non-empty)
    if not results.unmatched.empty:
        results.unmatched.to_csv(UNMATCH, index=False)
        print(f"[ERROR] Unmatched names: {len(results.unmatched)} — see {UNMATCH}")
        print("\nUnmatched teams:")
        for _, row in results.unmatched.head(10).iterrows():
            print(f"  - {row['raw_name']} ({row['category']}, {row['appearances']} games)")
        if len(results.unmatched) > 10:
            print(f"  ... and {len(results.unmatched) - 10} more")
        return 2
    
    print("[OK] No unmatched teams")
    
    # External candidates (FYI only)
    if not results.external_candidates.empty:
        results.external_candidates.to_csv(EXTERNAL, index=False)
        print(f"[INFO] External candidates: {len(results.external_candidates)} — see {EXTERNAL}")
    
    # Game histories
    results.game_histories.to_csv(HIST, index=False)
    print(f"[OK] Wrote histories: {HIST} ({len(results.game_histories)} rows)")
    
    # Compatibility format
    results.compat_games.to_csv(COMPAT, index=False)
    print(f"[OK] Wrote legacy-compat games: {COMPAT} ({len(results.compat_games)} rows)")

    # ===== Step 4: Summary report (U12-style) =====
    stats = results.summary_stats
    
    summary = f"""
AZ U11 Team Matching Report
===========================
Generated: {datetime.now():%Y-%m-%d %H:%M:%S}

MATCHING STATS
--------------
Total Games Processed: {stats['total_games']:,}
Total Teams Processed: {stats['total_teams']:,}

Match Types:
  + Exact: {stats['exact_matches']:,}
  ? Fuzzy: {stats['fuzzy_matches']:,}
  ~ External: {stats['external_matches']:,}
  ! Unmatched: {stats['unmatched_count']:,}

Outputs:
  + {NAME_MAP}
  + {UNMATCH}
  + {EXTERNAL}
  + {HIST}
  + {COMPAT}
""".strip()

    with open(SUMMARY, "w", encoding="utf-8") as f:
        f.write(summary)

    print("\n" + summary)
    print("\n[OK] Done. Next: run your rankings generator on COMPAT, or consume histories.csv directly.")

    return 0

if __name__ == "__main__":
    sys.exit(main())
