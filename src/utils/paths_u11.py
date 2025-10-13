# src/utils/paths_u11.py
from pathlib import Path

def _state(st: str) -> str:
    return (st or "").strip().upper()

def _season_key(st: str, season: int) -> str:
    return f"{st.lower()}_boys_u11_{season}"

def _first_existing(paths: list[Path]) -> Path:
    for p in paths:
        if p.exists():
            return p
    return paths[0]  # create here if none exist

# Master teams by state (per your restructure)
def master_state_path(state: str) -> Path:
    st = _state(state)
    return Path(f"data/master/U11 BOYS/{st}/{st}_teams.csv")

# Scraped game histories from your Step 3 script
def scraped_histories_path(state: str) -> Path:
    st = _state(state)
    return Path(f"data/game_histories/U11 BOYS/{st}/game_histories.csv")

# Canonical raw games used by matcher (NEW preferred; legacy fallback)
def canonical_raw_path(state: str, season: int = 2025) -> Path:
    st = _state(state)
    preferred = Path(f"data/raw/U11 Boys/{st}/games_raw.csv")
    legacy    = Path(f"data/raw/{_season_key(state, season)}/games_raw.csv")
    p = _first_existing([preferred, legacy])
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

# Mappings dir (NEW preferred; legacy fallback)
def mappings_dir(state: str, season: int = 2025) -> Path:
    st = _state(state)
    preferred = Path(f"Data/mappings/U11 Boys/{st}")  # note capital 'D' + spaces
    legacy    = Path(f"data/mappings/{_season_key(state, season)}")
    d = _first_existing([preferred, legacy])
    d.mkdir(parents=True, exist_ok=True)
    return d

# Logs dir (NEW preferred; legacy fallback)
def logs_dir(state: str, season: int = 2025) -> Path:
    st = _state(state)
    preferred = Path(f"data/logs/U11 Boys/{st}")
    legacy    = Path(f"data/logs/{_season_key(state, season)}")
    d = _first_existing([preferred, legacy])
    d.mkdir(parents=True, exist_ok=True)
    return d

# Outputs (histories) dir (NEW preferred; legacy fallback)
def outputs_dir(state: str, season: int = 2025) -> Path:
    st = _state(state)
    preferred = Path(f"data/outputs/U11 Boys/{st}")  # Updated to match your structure
    legacy    = Path(f"data/outputs/{_season_key(state, season)}")
    d = _first_existing([preferred, legacy])
    d.mkdir(parents=True, exist_ok=True)
    return d

# Gold/compat dir & file
def gold_dir(state: str) -> Path:
    st = _state(state)
    d = Path(f"data/gold/U11 Boys/{st}")
    d.mkdir(parents=True, exist_ok=True)
    return d

def compat_path(state: str) -> Path:
    return gold_dir(state) / "Matched_Games_U11_COMPAT.csv"

