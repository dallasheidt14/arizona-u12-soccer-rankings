# scripts/smoke_rankings.py
import requests, sys, json

base = "http://localhost:8000"
params = {"state":"AZ", "gender":"MALE", "year":2014}

def check(path):
    r = requests.get(f"{base}{path}", params=params, timeout=10)
    print(path, r.status_code)
    if r.ok:
        try:
            data = r.json()
            if isinstance(data, list):
                print("rows:", len(data), "sample:", json.dumps(data[:2], indent=2)[:500])
            else:
                print(json.dumps(data, indent=2)[:800])
        except Exception as e:
            print("JSON parse error:", e, r.text[:500])
    else:
        print("Error body:", r.text[:500])

if __name__ == "__main__":
    check("/api/debug_paths")
    check("/api/rankings")  # should return an array of rows
