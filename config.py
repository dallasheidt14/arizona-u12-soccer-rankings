#!/usr/bin/env python3
"""
Configuration for Arizona U12 Soccer Rankings System
===================================================

Centralized configuration with sensible defaults.
Can be overridden via command-line arguments.
"""

# =============================
# 📊 RANKING ALGORITHM CONFIG
# =============================

# Recent games weighting
RECENT_WINDOW = 10          # Number of recent games to weight more heavily
RECENT_WEIGHT = 0.70        # Weight for recent games (last N games)

# Power Score component weights
OFFENSE_WEIGHT = 0.375      # Weight for offensive performance
DEFENSE_WEIGHT = 0.375      # Weight for defensive performance  
SOS_WEIGHT = 0.25          # Weight for strength of schedule

# Game count penalty thresholds
GAMES_PENALTY_THRESHOLDS = {
    "full": 20,             # >= 20 games: no penalty
    "moderate": 10,         # 10-19 games: moderate penalty
    "low_penalty": 0.90,    # multiplier for moderate penalty
    "high_penalty": 0.75    # multiplier for heavy penalty
}

# Robust normalization settings
ROBUST_MIN_Q = 0.05        # 5th percentile for outlier clipping
ROBUST_MAX_Q = 0.95        # 95th percentile for outlier clipping

# =============================
# 📁 FILE PATHS
# =============================

# Input files
MATCHED_GAMES_FILE = "Matched_Games.csv"
MASTER_TEAM_LIST_FILE = "AZ MALE U12 MASTER TEAM LIST.csv"

# Output files
RANKINGS_FILE = "Rankings.csv"
GAME_HISTORIES_FILE = "Team_Game_Histories.csv"
LOGS_FILE = "Ranking_Logs.txt"

# =============================
# 🔍 FILTERING DEFAULTS
# =============================

# Default filters (None = no filter applied)
DEFAULT_STATE = None        # e.g., "AZ"
DEFAULT_GENDER = None       # e.g., "MALE" 
DEFAULT_YEAR = None         # e.g., 2025

# =============================
# 📈 OUTPUT CONFIGURATION
# =============================

# Materialized output settings
MATERIALIZE_OUTPUTS = False  # Whether to create per-segment files
OUTPUT_PATTERN = "Rankings_{STATE}_{GENDER}_{YEAR}.csv"

# Column configuration
INCLUDE_RAW_STATS = True    # Include GFPG, GAPG, SOS_raw columns
INCLUDE_NORMALIZED = True   # Include normalized component scores
INCLUDE_WLT_STRING = True   # Include W-L-T formatted string

# =============================
# 🛠️ PROCESSING CONFIG
# =============================

# Data validation
REQUIRE_MIN_GAMES = 1       # Minimum games required for ranking
VALIDATE_SCORES = True      # Validate that scores are non-negative integers
VALIDATE_DATES = True       # Validate that dates can be parsed

# Error handling
FAIL_ON_MISSING_COLS = True # Fail if required columns are missing
LOG_OUTLIERS = True         # Log teams with extreme statistics
AUTO_HANDLE_NANS = True     # Automatically handle NaN values

# =============================
# 📊 LOGGING CONFIG
# =============================

LOG_LEVEL = "INFO"         # DEBUG, INFO, WARNING, ERROR
LOG_OUTLIER_THRESHOLD = 3.0  # Standard deviations for outlier detection
LOG_DETAILED_STATS = True   # Log detailed statistics for each team

# =============================
# 🚀 ENHANCED FEATURES CONFIG
# =============================

# Enhanced ranking window
RANK_WINDOW_DAYS = 365      # Only consider games within this many days
RANK_MAX_MATCHES = 20       # Maximum games to consider for ranking

# Expectation tracking
EXPECTATION_MODEL = "opponent_adjusted_v1"  # or "simple" for legacy
EXPECT_ALPHA = 1.0           # weight on (Off_A - Def_B)
EXPECT_BETA = 0.5           # weight on (Off_B - Def_A), subtracted
EXPECT_GOAL_CLIP = 4.0      # cap on absolute expected GD

# Calibration
EXPECT_CALIBRATE = True
EXPECT_CALIB_WINDOW_DAYS = 365
EXPECT_CALIB_MIN_SAMPLES = 300  # fallback to raw if fewer
EXPECT_CALIB_FALLBACK_WINDOW_DAYS = 180
IMPACT_THRESHOLDS = (-0.5, 0.5)  # weak < -0.5, neutral in [-0.5,0.5], good > 0.5

# Provisional gating
PROVISIONAL_MIN_GAMES = 6           # Minimum games for full ranking
PROVISIONAL_MIN_CROSS_CLUSTER = 3   # Minimum cross-cluster opponents

# Inactivity policy
INACTIVE_WARN_DAYS = 180    # 6 months - show warning
INACTIVE_HIDE_DAYS = 210    # 7 months - hide from main lists

# Feature flags (Phase A/B/C rollout)
ENABLE_UI_TOGGLES = True           # Phase A: UI sorting toggles
ENABLE_COLOR_CODING = True         # Phase A: Result color coding
ENABLE_WHAT_CHANGED = True         # Phase A: What changed today panel
ENABLE_EXPECTATION_TRACKING = True # Phase B: Expectation tracking
ENABLE_INACTIVITY_FLAGGING = True  # Phase B: Inactivity flags
ENABLE_PROVISIONAL_GATING = True  # Phase C: Provisional rankings
ENABLE_CLUB_RANKINGS = False       # Phase C: Club aggregate rankings (locked off)
ENABLE_ADMIN_UI = True             # Phase C: Admin review interface
ENABLE_PK_HANDLING = True          # Phase C: PK vs regulation score handling

# =============================
# 🎯 VALIDATION RANGES
# =============================

# Valid ranges for configuration values
VALID_WEIGHTS = {
    "min": 0.0,
    "max": 1.0,
    "sum_max": 1.0
}

VALID_RECENT_WINDOW = {
    "min": 1,
    "max": 50
}

VALID_PENALTY_MULTIPLIERS = {
    "min": 0.0,
    "max": 1.0
}

# =============================
# 🔧 UTILITY FUNCTIONS
# =============================

def validate_config():
    """Validate configuration values are within acceptable ranges."""
    errors = []
    
    # Check weights sum to 1.0
    weight_sum = OFFENSE_WEIGHT + DEFENSE_WEIGHT + SOS_WEIGHT
    if abs(weight_sum - 1.0) > 0.001:
        errors.append(f"Weights sum to {weight_sum:.3f}, should be 1.0")
    
    # Check individual weights
    for name, weight in [("OFFENSE", OFFENSE_WEIGHT), ("DEFENSE", DEFENSE_WEIGHT), ("SOS", SOS_WEIGHT)]:
        if not (0 <= weight <= 1):
            errors.append(f"{name}_WEIGHT ({weight}) must be between 0 and 1")
    
    # Check recent window
    if not (1 <= RECENT_WINDOW <= 50):
        errors.append(f"RECENT_WINDOW ({RECENT_WINDOW}) must be between 1 and 50")
    
    # Check recent weight
    if not (0 <= RECENT_WEIGHT <= 1):
        errors.append(f"RECENT_WEIGHT ({RECENT_WEIGHT}) must be between 0 and 1")
    
    if errors:
        raise ValueError("Configuration validation failed:\n" + "\n".join(errors))
    
    return True

def get_config_summary():
    """Get a summary of current configuration."""
    return {
        "recent_window": RECENT_WINDOW,
        "recent_weight": RECENT_WEIGHT,
        "offense_weight": OFFENSE_WEIGHT,
        "defense_weight": DEFENSE_WEIGHT,
        "sos_weight": SOS_WEIGHT,
        "penalty_thresholds": GAMES_PENALTY_THRESHOLDS,
        "filters": {
            "state": DEFAULT_STATE,
            "gender": DEFAULT_GENDER,
            "year": DEFAULT_YEAR
        },
        "materialize": MATERIALIZE_OUTPUTS
    }

if __name__ == "__main__":
    # Validate configuration when run directly
    try:
        validate_config()
        print("Configuration is valid")
        print("\nCurrent configuration:")
        import json
        print(json.dumps(get_config_summary(), indent=2))
    except ValueError as e:
        print(f"Configuration error: {e}")
        exit(1)
