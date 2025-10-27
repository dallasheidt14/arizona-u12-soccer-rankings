import pandas as pd
import glob
import os

# Simulate what the dashboard does
age_group = "11"
gender = "M"

patterns = [
    f"data/output/National_U{age_group}_Rankings_CROSS_AGE*.csv",  # U10 pattern
    f"data/output/National_U{age_group}_{gender}_Rankings*.csv",    # U11 pattern with versions
    f"data/output/National_U{age_group}_{gender}_Rankings.csv",    # U11 pattern without version
    f"data/output/National_U{age_group}_Rankings_CROSS_AGE.csv"    # Fallback
]

files = []
for pattern in patterns:
    found = glob.glob(pattern)
    print(f"Pattern: {pattern}")
    print(f"  Found: {found}")
    files.extend(found)

print(f"\nTotal files found: {len(files)}")
for f in files:
    print(f"  - {f}")

if files:
    # Try to load
    files_sorted = sorted(files, key=os.path.getmtime, reverse=True)
    print(f"\nLoading newest file: {files_sorted[0]}")
    df = pd.read_csv(files_sorted[0])
    print(f"✅ Loaded {len(df)} teams")
    print(f"Columns: {list(df.columns[:5])}")
else:
    print("❌ No files found")

