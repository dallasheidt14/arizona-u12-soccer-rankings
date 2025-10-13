# scripts/validate_u11_paths.py
import pandas as pd
from src.utils.paths_u11 import master_state_path, canonical_raw_path, mappings_dir, logs_dir, outputs_dir, compat_path

def run(state="AZ", season=2025):
    m = pd.read_csv(master_state_path(state))
    
    # Normalize column names (handle gotsport_team_id -> team_id, team_name -> display_name)
    if "gotsport_team_id" in m.columns:
        m = m.rename(columns={"gotsport_team_id": "team_id"})
    if "team_name" in m.columns:
        m = m.rename(columns={"team_name": "display_name"})
    
    assert {"team_id","display_name"}.issubset(m.columns), f"Master missing cols. Has: {list(m.columns)}"
    assert m["team_id"].is_unique, "Duplicate team_id in master"
    print(f"[OK] Master: {len(m)} teams")

    raw = pd.read_csv(canonical_raw_path(state, season))
    assert {"Team A","Team B","Score A","Score B","Date"}.issubset(raw.columns), "Raw missing required cols"
    print(f"[OK] Raw games: {len(raw)} games")

    mp = pd.read_csv(mappings_dir(state, season) / "name_map.csv")
    assert {"raw_name","team_id","display_name"}.issubset(mp.columns), "name_map missing cols"
    print(f"[OK] name_map: {len(mp)} mappings")

    h = pd.read_csv(outputs_dir(state, season) / "histories.csv")
    assert {"team_id","opponent_team_id","date","goals_for","goals_against","result"}.issubset(h.columns), "histories missing cols"
    print(f"[OK] histories: {len(h)} game records")

    c = pd.read_csv(compat_path(state))
    assert {"TeamKey","OppKey","Team","Opp","Score A","Score B","Date"}.issubset(c.columns), "compat missing cols"
    print(f"[OK] compat: {len(c)} records")
    
    print("\n[SUCCESS] Paths + schemas look good")

if __name__ == "__main__":
    run("AZ", 2025)

