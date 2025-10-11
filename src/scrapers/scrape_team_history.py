"""
scrapers/scrape_team_history.py
Purpose: Step-2 scraper to fetch GotSport match histories per team for any AZ Boys division.
Inputs:  bronze/<division>_teams.csv  (columns: "Team Name", "Club")
Outputs: gold/Matched_Games_<DIV>.csv (columns: Team A, Team B, Score A, Score B, Date)
"""

import argparse, os, re, json, time, random
from typing import List, Dict
import requests
import pandas as pd
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---- Integration: reuse your normalizer/aliases
try:
    from utils.team_normalizer import canonicalize_team_name
except Exception:
    def canonicalize_team_name(s: str) -> str:
        return re.sub(r"\s+", " ", str(s or "").strip().lower())

BASE_URL = "https://rankings.gotsport.com"
SEARCH_URL = f"{BASE_URL}/team_search?search="
TIMEOUT = 12
MAX_WORKERS = 6
RETRIES = 3
BACKOFFS = [2, 4, 8]  # seconds
SLEEP_JITTER = (1.5, 3.5)

def log(msg: str): print(f"[scrape_team_history] {msg}")

def save_log(line: str, division: str):
    os.makedirs("logs", exist_ok=True)
    with open(f"logs/scrape_errors_{division}.log", "a", encoding="utf-8") as f:
        f.write(line.rstrip() + "\n")

def load_profile_cache(division: str) -> Dict[str, str]:
    path = f"bronze/team_profiles_{division}.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_profile_cache(cache: Dict[str, str], division: str):
    os.makedirs("bronze", exist_ok=True)
    path = f"bronze/team_profiles_{division}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def http_get(url: str) -> requests.Response:
    for i in range(RETRIES):
        try:
            resp = requests.get(url, timeout=TIMEOUT, headers={"User-Agent":"AZRankBot/1.0 (+pipeline)"})
            if resp.status_code == 200:
                return resp
            save_log(f"HTTP {resp.status_code} for {url}", "generic")
        except Exception as e:
            save_log(f"GET failed {url}: {e}", "generic")
        time.sleep(BACKOFFS[min(i, len(BACKOFFS)-1)])
    raise RuntimeError(f"Failed to GET after {RETRIES} tries: {url}")

# ---- Tiered team search
def find_team_profile_url(team_name: str, division: str, cache: Dict[str, str]) -> str:
    key = team_name.strip()
    if key in cache and cache[key]:
        return cache[key]

    # 1) exact anchor match
    resp = http_get(SEARCH_URL + requests.utils.quote(team_name))
    soup = BeautifulSoup(resp.text, "html.parser")
    for a in soup.find_all("a", href=True):
        text = (a.get_text() or "").strip()
        if text.lower() == team_name.strip().lower():
            url = BASE_URL + a["href"]
            cache[key] = url
            return url

    # 2) canonicalized match
    team_norm = canonicalize_team_name(team_name)
    best_url = None
    for a in soup.find_all("a", href=True):
        text = (a.get_text() or "").strip()
        if canonicalize_team_name(text) == team_norm:
            best_url = BASE_URL + a["href"]
            break
    if best_url:
        cache[key] = best_url
        return best_url

    # 3) fallback: partial token overlap
    tokens = set(team_norm.split())
    best, best_score = None, 0.0
    for a in soup.find_all("a", href=True):
        text = (a.get_text() or "").strip()
        norm = canonicalize_team_name(text)
        if not norm: continue
        overlap = len(tokens & set(norm.split())) / max(1, len(tokens))
        if overlap > best_score:
            best, best_score = a, overlap
    if best and best_score >= 0.6:
        cache[key] = BASE_URL + best["href"]
        return cache[key]

    save_log(f"Profile not found via search: {team_name}", division)
    return ""

def parse_matches_from_profile(team_name: str, profile_url: str, division: str) -> List[Dict]:
    if not profile_url:
        return []
    try:
        r = http_get(profile_url)
        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.find("table", {"id": "team_matches"}) or soup.find("table", {"class": "table"})
        if not table:
            save_log(f"No team_matches table: {team_name} | {profile_url}", division)
            return []
        out = []
        for tr in table.find_all("tr")[1:]:
            tds = tr.find_all("td")
            if len(tds) < 4: 
                continue
            opp = (tds[1].get_text() or "").strip()
            score = (tds[2].get_text() or "").strip().replace("–","-").replace("—","-")
            date = (tds[3].get_text() or "").strip()

            m = re.match(r"^\s*(\d+)\s*[-:]\s*(\d+)\s*$", score)
            if not m:
                # sometimes score is "W 3-1" etc.
                m2 = re.search(r"(\d+)\s*[-:]\s*(\d+)", score)
                if not m2:
                    continue
                gfa, gga = m2.group(1), m2.group(2)
            else:
                gfa, gga = m.group(1), m.group(2)

            out.append({
                "Team A": team_name,
                "Team B": canonicalize_team_name(opp),
                "Score A": int(gfa),
                "Score B": int(gga),
                "Date": date,
                # Optional (safe to keep; ranking engine ignores unknown columns)
                "Competition": (tds[0].get_text() or "").strip() if len(tds) > 4 else "",
                "SourceURL": profile_url,
            })
        return out
    except Exception as e:
        save_log(f"Parse fail for {team_name}: {e}", division)
        return []

def scrape_one_team(team_name: str, division: str, cache: Dict[str, str]) -> List[Dict]:
    url = find_team_profile_url(team_name, division, cache)
    if not url:
        return []
    matches = parse_matches_from_profile(team_name, url, division)
    # polite jitter per team (even when parallel)
    time.sleep(random.uniform(*SLEEP_JITTER))
    return matches

def run_division(division: str, parallel: bool = True) -> int:
    bronze = f"bronze/{division}_teams.csv"
    if not os.path.exists(bronze):
        raise FileNotFoundError(f"Missing master team list: {bronze}")

    teams_df = pd.read_csv(bronze)
    if "Team Name" not in teams_df.columns:
        raise ValueError(f"{bronze} must contain a 'Team Name' column.")
    team_names = teams_df["Team Name"].dropna().astype(str).tolist()
    log(f"Found {len(team_names)} teams in {division}")

    cache = load_profile_cache(division)
    all_rows: List[Dict] = []

    if parallel:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futs = {ex.submit(scrape_one_team, t, division, cache): t for t in team_names}
            for fut in as_completed(futs):
                t = futs[fut]
                try:
                    rows = fut.result()
                    all_rows.extend(rows)
                except Exception as e:
                    save_log(f"Team scrape error {t}: {e}", division)
    else:
        for t in team_names:
            all_rows.extend(scrape_one_team(t, division, cache))

    # Persist cache
    save_profile_cache(cache, division)

    # Write gold output
    os.makedirs("gold", exist_ok=True)
    div_up = division.upper()  # e.g., AZ_BOYS_U10
    out_path = f"gold/Matched_Games_{div_up}.csv"
    pd.DataFrame(all_rows).to_csv(out_path, index=False)
    log(f"✅ Saved {len(all_rows)} matches → {out_path}")

    # Warn if many teams yielded no matches
    teams_with_games = {r["Team A"] for r in all_rows}
    failed_count = len([t for t in team_names if t not in teams_with_games])
    fail_pct = failed_count / max(1, len(team_names))
    if fail_pct > 0.10:
        save_log(f"High fail rate: {failed_count}/{len(team_names)} teams no matches ({fail_pct:.1%})", division)
        return 2  # non-zero for CI
    return 0

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--division", required=True, help="az_boys_u10 | az_boys_u11 | az_boys_u12 | az_boys_u13 | az_boys_u14")
    p.add_argument("--no-parallel", action="store_true")
    args = p.parse_args()
    code = run_division(args.division, parallel=not args.no_parallel)
    raise SystemExit(code)

