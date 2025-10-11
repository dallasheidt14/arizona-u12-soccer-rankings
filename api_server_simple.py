"""
Simplified API Server for Arizona Boys Soccer Rankings
Uses simple age groups (U10, U11, U12, U13, U14) instead of complex divisions
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import pandas as pd
from typing import Optional, List
import json

app = FastAPI(title="Arizona Boys Soccer Rankings API", version="2.0")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data directory
DATA_DIR = Path("data/outputs")

# Age group to file mapping
AGE_GROUP_FILES = {
    "U10": "Rankings_AZ_M_u10_2025_v53e.csv",
    "U11": "Rankings_AZ_M_u11_2025_v53e.csv", 
    "U12": "Rankings_AZ_M_U12_2025_v53e.csv",
    "U13": "Rankings_AZ_M_u13_2025_v53e.csv",
    "U14": "Rankings_AZ_M_u14_2025_v53e.csv"
}

# Fallback files for each age group
AGE_GROUP_FALLBACKS = {
    "U10": ["Rankings_AZ_M_U10_2025.csv", "Rankings_U10_v53e.csv"],
    "U11": ["Rankings_AZ_M_U11_2025.csv", "Rankings_U11_v53e.csv"],
    "U12": ["Rankings_v53_enhanced.csv", "Rankings_v53.csv", "Rankings_v52b.csv"],
    "U13": ["Rankings_AZ_M_U13_2025.csv", "Rankings_U13_v53e.csv"],
    "U14": ["Rankings_AZ_M_U14_2025.csv", "Rankings_U14_v53e.csv"]
}

def find_rankings_file(age_group: str) -> Path:
    """Find the rankings file for a given age group."""
    # Try primary file first
    primary_file = DATA_DIR / AGE_GROUP_FILES[age_group]
    if primary_file.exists():
        return primary_file
    
    # Try fallback files
    for fallback in AGE_GROUP_FALLBACKS[age_group]:
        fallback_file = DATA_DIR / fallback
        if fallback_file.exists():
            return fallback_file
    
    raise FileNotFoundError(f"No rankings file found for age group {age_group}")

def load_rankings(age_group: str) -> pd.DataFrame:
    """Load rankings for a specific age group."""
    try:
        file_path = find_rankings_file(age_group)
        df = pd.read_csv(file_path)
        
        # Ensure required columns exist
        if "Team" not in df.columns:
            raise ValueError(f"Missing 'Team' column in {file_path}")
        if "PowerScore" not in df.columns and "PowerScore_adj" not in df.columns:
            raise ValueError(f"Missing PowerScore column in {file_path}")
        
        # Use PowerScore_adj if available, otherwise PowerScore
        if "PowerScore_adj" in df.columns and "PowerScore" not in df.columns:
            df["PowerScore"] = df["PowerScore_adj"]
        
        return df
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Error loading rankings for {age_group}: {str(e)}")

@app.get("/")
def root():
    return {
        "message": "Arizona Boys Soccer Rankings API",
        "version": "2.0",
        "age_groups": list(AGE_GROUP_FILES.keys()),
        "endpoints": {
            "rankings": "/api/rankings?age_group=U12",
            "age_groups": "/api/age_groups",
            "health": "/api/health"
        }
    }

@app.get("/api/age_groups")
def api_age_groups():
    """Get available age groups."""
    return {
        "age_groups": [
            {"code": "U10", "label": "Arizona Boys U10 (2016)"},
            {"code": "U11", "label": "Arizona Boys U11 (2015)"},
            {"code": "U12", "label": "Arizona Boys U12 (2014)"},
            {"code": "U13", "label": "Arizona Boys U13 (2013)"},
            {"code": "U14", "label": "Arizona Boys U14 (2012)"}
        ]
    }

@app.get("/api/slices")
def api_slices():
    """Get available data slices for the frontend."""
    slices = []
    for age_group in AGE_GROUP_FILES.keys():
        try:
            df = load_rankings(age_group)
            # Only include slices with actual data
            if len(df) > 0:
                slices.append({
                    "state": "AZ",
                    "gender": "MALE", 
                    "year": str(2014 + (12 - int(age_group[1:]))),  # Convert U12 -> 2014, U11 -> 2015, etc.
                    "age_group": age_group,
                    "rankings": AGE_GROUP_FILES[age_group],
                    "teams": len(df),
                    "games": df["GamesPlayed"].sum() if "GamesPlayed" in df.columns else 0
                })
        except Exception as e:
            # Skip age groups that don't have data
            print(f"Skipping {age_group}: {e}")
            continue
    
    return {"slices": slices}

@app.get("/api/rankings")
def api_rankings(
    age_group: str = Query(..., description="Age group: U10, U11, U12, U13, U14"),
    q: Optional[str] = Query(None, description="Search team name"),
    sort: str = Query("PowerScore", description="Sort by: PowerScore, GamesPlayed, Team"),
    order: str = Query("desc", description="Sort order: asc, desc"),
    limit: int = Query(500, ge=1, le=5000, description="Number of results to return"),
    include_inactive: bool = Query(True, description="Include inactive teams")
):
    """Get rankings for a specific age group."""
    
    # Validate age group
    if age_group not in AGE_GROUP_FILES:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid age group '{age_group}'. Must be one of: {list(AGE_GROUP_FILES.keys())}"
        )
    
    # Load rankings
    df = load_rankings(age_group)
    
    # Search filter
    if q and "Team" in df.columns:
        df = df[df["Team"].str.contains(q, case=False, na=False)]
    
    # Filter inactive teams if requested
    if not include_inactive and "is_active" in df.columns:
        df = df[df["is_active"] == True]
    
    # Sort
    if sort in df.columns:
        ascending = order.lower() == "asc"
        df = df.sort_values(sort, ascending=ascending)
    elif sort == "Team" and "Team" in df.columns:
        ascending = order.lower() == "asc"
        df = df.sort_values("Team", ascending=ascending)
    else:
        # Default sort by PowerScore descending
        df = df.sort_values("PowerScore", ascending=False)
    
    # Limit results
    df = df.head(limit)
    
    # Add rank if not present
    if "Rank" not in df.columns:
        df["Rank"] = range(1, len(df) + 1)
    
    # Select key columns for response
    response_cols = ["Rank", "Team", "PowerScore", "GamesPlayed"]
    available_cols = [col for col in response_cols if col in df.columns]
    
    # Add additional columns if available
    additional_cols = ["SAO_norm", "SAD_norm", "SOS_norm", "Status", "is_active", "LastGame"]
    for col in additional_cols:
        if col in df.columns:
            available_cols.append(col)
    
    result_df = df[available_cols]
    
    # Convert to the format expected by React app
    rankings_data = result_df.to_dict("records")
    
    return {
        "meta": {
            "age_group": age_group,
            "total_teams": len(df),
            "active_teams": len(df[df.get("is_active", True) == True]) if "is_active" in df.columns else len(df),
            "provisional_teams": len(df[df.get("is_active", False) == False]) if "is_active" in df.columns else 0
        },
        "data": rankings_data,
        "active": rankings_data,  # All teams are active for now
        "provisional": []  # No provisional teams for now
    }

@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "age_groups_available": len(AGE_GROUP_FILES)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
