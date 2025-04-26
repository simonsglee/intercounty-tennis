import pandas as pd
import re
import os
import glob
from cleaning import (
    fix_match_date, 
    parse_division_level, 
    cast_division_level, 
    validate_line,
    create_team_match_id,
    create_match_id
    )

# Import any other cleaning functions you have (e.g., fix_bad_scores later)

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

clean_data_path = os.path.join(project_root, "data", "ic_mixed_matches_cleaned.csv")

df_clean = pd.read_csv(clean_data_path)


# Grab all match files from the 'data/processed' folder
match_files = glob.glob(os.path.join(project_root, "data", "processed", "ic_mixed_matches*.csv"))

# Combine them into one DataFrame
df_raw = pd.concat([pd.read_csv(f) for f in match_files], ignore_index=True)


# --- Step 2: Fix Dates ---
df_raw['Date_fixed'] = df_raw['Date'].apply(fix_match_date)

# Number of missing (bad) dates
num_bad_dates = df_raw['Date_fixed'].isna().sum()
print(f"⚠️  Number of bad (missing) dates: {num_bad_dates}")

# Group by Year-Month for clean dates
if num_bad_dates < len(df_raw):
    df_raw['year'] = df_raw['Date_fixed'].dt.year
    df_raw['month'] = df_raw['Date_fixed'].dt.month
    
    date_summary = df_raw.groupby(['year', 'month']).size().sort_index()
    print("📅 Match counts by Year and Month:")
    print(date_summary)
else:
    print("⚠️  All dates missing — check your data!")


# --- Step 3: Parse Division Level ---
df_raw['division_level'] = df_raw['Division'].apply(parse_division_level)

# --- Step 4: Cast Division Level to Ordered Categorical ---
df_raw['division_level'] = cast_division_level(df_raw['division_level'])

# --- Step 4.1: Check for Bad Divisions ---

# Find any rows where division_level is missing
bad_divisions = df_raw[df_raw['division_level'].isna()]

if not bad_divisions.empty:
    print("⚠️  Warning: Found divisions that don't fit the expected schema (Major, A, B, C):")
    print(bad_divisions['Division'].value_counts())
else:
    print("✅ All divisions fit expected schema.")

# --- Step 5: Validate Line Column ---
df_raw['Line_validated'] = df_raw['Line'].apply(validate_line)

# --- Step 5.1: Check for Bad Line Values ---

bad_lines = df_raw[df_raw['Line_validated'].isna()]

if not bad_lines.empty:
    print("⚠️  Warning: Found invalid Line values (should be 1–6 only):")
    print(bad_lines['Line'].value_counts())
else:
    print("✅ All Line values are valid (1–6).")


# --- Step 6: Create Team Match IDs ---
df_clean = create_team_match_id(df_raw)

# Print number of unique team matches created
num_team_matches = df_clean['temp_team_match_id'].nunique()
print(f"✅ Created {num_team_matches} unique team matches.")

# --- Step 6.1: Validate Lines Within Team Matches ---

# Group by team match
bad_team_matches = []

for team_id, group in df_clean.groupby('temp_team_match_id'):
    lines = group['Line_validated'].dropna().tolist()
    unique_lines = set(lines)

    # Check for duplicates or invalid lines
    if len(lines) != len(unique_lines) or not unique_lines.issubset({1, 2, 3, 4, 5, 6}):
        bad_team_matches.append(team_id)

if bad_team_matches:
    print(f"⚠️  Warning: Found {len(bad_team_matches)} team matches with invalid or duplicate Lines.")
    print("Problematic team_match_ids:", bad_team_matches)
else:
    print("✅ All team matches have valid, distinct Lines (1–6).")
    
    
# --- Step 7: Create Match IDs ---
df_clean = create_match_id(df_clean)

# --- Step 7.1: Validate Unique Matches ---

num_rows = len(df_clean)
num_unique_matches = df_clean['temp_match_id'].nunique()

if num_rows == num_unique_matches:
    print(f"✅ All {num_rows} individual matches have unique match IDs.")
else:
    print(f"⚠️  Warning: Found {num_rows} rows but only {num_unique_matches} unique temp_match_ids!")
