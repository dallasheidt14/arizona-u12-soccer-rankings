"""
FastAPI Web API for Arizona U12 Soccer Rankings
Read-only API to power dashboard and share data slices
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd
from pathlib import Path
from typing import Optional, List, Dict, Any
import json
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Arizona U12 Soccer Rankings API",
    description="Read-only API for soccer rankings and team data",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cache for slice responses (15 minutes)
from functools import lru_cache
import time

@lru_cache(maxsize=100)
def get_cached_data(cache_key: str, timestamp: int):
    """Simple cache with timestamp-based invalidation."""
    return None

def get_cache_key(division: Optional[str], state: Optional[str], gender: Optional[str], year: Optional[int]) -> str:
    """Generate cache key for slice data."""
    return f"{division or 'all'}_{state or 'all'}_{gender or 'all'}_{year or 'all'}"

def load_rankings_data(division: Optional[str] = None) -> pd.DataFrame:
    """Load rankings data with fallback logic."""
    # If division is specified, try division-specific file first
    if division:
        division_file = f"Rankings_AZ_M_{division.split('_')[-1].lower()}_2025_v53e.csv"
        if Path(division_file).exists():
            logger.info(f"Loading division-specific rankings: {division_file}")
            return pd.read_csv(division_file)
        else:
            logger.warning(f"Division file not found: {division_file}")
    
    # Try Gold layer first
    gold_path = Path("data_ingest/gold/All_Games.parquet")
    if gold_path.exists():
        logger.info("Loading rankings from Gold layer")
        return pd.read_parquet(gold_path)
    
    # Fallback to legacy CSV
    legacy_path = Path("Rankings.csv")
    if legacy_path.exists():
        logger.info("Loading rankings from legacy CSV")
        return pd.read_csv(legacy_path)
    
    raise HTTPException(status_code=404, detail="No rankings data available")

def load_game_histories() -> pd.DataFrame:
    """Load game histories data."""
    hist_path = Path("Team_Game_Histories.csv")
    if hist_path.exists():
        return pd.read_csv(hist_path)
    
    # Try Gold layer
    gold_path = Path("data_ingest/gold/All_Games.parquet")
    if gold_path.exists():
        df = pd.read_parquet(gold_path)
        # Convert Gold schema to legacy schema
        return convert_gold_to_legacy_schema(df)
    
    raise HTTPException(status_code=404, detail="No game histories available")

def convert_gold_to_legacy_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Convert Gold layer schema to legacy schema for API responses."""
    if df.empty:
        return df
    
    legacy_df = pd.DataFrame()
    legacy_df["Date"] = pd.to_datetime(df["date_utc"], errors="coerce")
    legacy_df["Team"] = df["home_team_raw"]  # Simplified for API
    legacy_df["Opponent"] = df["away_team_raw"]
    legacy_df["Goals For"] = df["home_score"]
    legacy_df["Goals Against"] = df["away_score"]
    legacy_df["Result"] = df["status"]
    
    return legacy_df

@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "message": "Arizona U12 Soccer Rankings API",
        "version": "1.0.0",
        "endpoints": {
            "rankings": "/api/rankings",
            "team_history": "/api/team/{team}/history",
            "slices": "/api/slices",
            "health": "/api/health"
        }
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check if data files exist
        gold_exists = Path("data_ingest/gold/All_Games.parquet").exists()
        legacy_exists = Path("Rankings.csv").exists()
        
        return {
            "status": "healthy",
            "data_available": gold_exists or legacy_exists,
            "gold_layer": gold_exists,
            "legacy_fallback": legacy_exists,
            "timestamp": pd.Timestamp.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "unhealthy", "error": str(e)}
        )

@app.get("/api/rankings")
async def get_rankings(
    division: Optional[str] = Query(None, description="Division (e.g., az_boys_u11, az_boys_u12)"),
    state: Optional[str] = Query(None, description="Filter by state (e.g., AZ)"),
    gender: Optional[str] = Query(None, description="Filter by gender (e.g., MALE)"),
    year: Optional[int] = Query(None, description="Filter by year (e.g., 2025)"),
    limit: Optional[int] = Query(100, description="Maximum number of results")
):
    """Get rankings with optional filters."""
    try:
        # Check cache first
        cache_key = get_cache_key(division, state, gender, year)
        cache_timestamp = int(time.time() // 900)  # 15-minute cache
        
        cached_data = get_cached_data(cache_key, cache_timestamp)
        if cached_data is not None:
            return cached_data
        
        # Load and filter data
        df = load_rankings_data(division)
        
        # Apply filters
        if state:
            df = df[df["State"] == state]
        if gender:
            df = df[df["Gender"] == gender]
        if year:
            df = df[df["Year"] == year]
        
        # Limit results
        if limit:
            df = df.head(limit)
        
        # Convert to response format
        result = df.to_dict(orient="records")
        
        # Cache the result
        get_cached_data.cache_clear()  # Clear old cache entries
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting rankings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/team/{team}/history")
async def get_team_history(team: str):
    """Get game history for a specific team."""
    try:
        df = load_game_histories()
        
        # Filter by team (case-insensitive)
        team_games = df[df["Team"].str.lower() == team.lower()]
        
        if team_games.empty:
            raise HTTPException(status_code=404, detail=f"Team '{team}' not found")
        
        return team_games.to_dict(orient="records")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting team history for {team}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/slices")
async def get_available_slices():
    """Get available data slices from rankings index."""
    try:
        index_path = Path("rankings_index.json")
        if index_path.exists():
            with open(index_path, 'r') as f:
                return json.load(f)
        else:
            # Generate basic slice info from data
            df = load_rankings_data()
            
            slices = []
            if not df.empty:
                # Add "All" slice
                slices.append({
                    "state": None,
                    "gender": None,
                    "year": None,
                    "rankings": "Rankings.csv",
                    "histories": "Team_Game_Histories.csv",
                    "teams": len(df["Team"].unique()),
                    "games": len(df)
                })
                
                # Add specific slices
                for state in df["State"].unique():
                    if pd.notna(state):
                        state_df = df[df["State"] == state]
                        slices.append({
                            "state": state,
                            "gender": None,
                            "year": None,
                            "rankings": f"Rankings_{state}.csv",
                            "histories": f"Team_Game_Histories_{state}.csv",
                            "teams": len(state_df["Team"].unique()),
                            "games": len(state_df)
                        })
            
            return {"slices": slices}
            
    except Exception as e:
        logger.error(f"Error getting slices: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/team/{team}/stats")
async def get_team_stats(team: str):
    """Get detailed statistics for a specific team."""
    try:
        df = load_rankings_data()
        
        # Find team (case-insensitive)
        team_data = df[df["Team"].str.lower() == team.lower()]
        
        if team_data.empty:
            raise HTTPException(status_code=404, detail=f"Team '{team}' not found")
        
        team_row = team_data.iloc[0]
        
        # Get game history for additional stats
        hist_df = load_game_histories()
        team_games = hist_df[hist_df["Team"].str.lower() == team.lower()]
        
        # Calculate additional stats
        recent_games = team_games.head(10) if len(team_games) >= 10 else team_games
        
        stats = {
            "team": team_row["Team"],
            "rank": team_row.get("Rank", "N/A"),
            "power_score": team_row.get("Power Score", "N/A"),
            "games_played": team_row.get("Games Played", 0),
            "wins": team_row.get("Wins", 0),
            "losses": team_row.get("Losses", 0),
            "ties": team_row.get("Ties", 0),
            "goals_for": team_row.get("Goals For", 0),
            "goals_against": team_row.get("Goals Against", 0),
            "goal_differential": team_row.get("Goal Differential", 0),
            "gfpg": team_row.get("GFPG", 0),
            "gapg": team_row.get("GAPG", 0),
            "sos": team_row.get("SOS", 0),
            "recent_form": {
                "last_10_games": len(recent_games),
                "recent_wins": len(recent_games[recent_games["Goals For"] > recent_games["Goals Against"]]),
                "recent_losses": len(recent_games[recent_games["Goals For"] < recent_games["Goals Against"]]),
                "recent_ties": len(recent_games[recent_games["Goals For"] == recent_games["Goals Against"]])
            }
        }
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting team stats for {team}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
