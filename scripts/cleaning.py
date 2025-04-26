import pandas as pd
import re
import os
import glob

# -- Fix date function --
def fix_match_date(date_value):
    """
    Ensure date_value is a clean pandas Timestamp.
    Handles strings, datetime objects, and NaNs safely.
    """
    if pd.isna(date_value):
        return pd.NaT  # Not-a-Time for missing dates
    if isinstance(date_value, pd.Timestamp):
        return date_value  # Already good
    try:
        # Try parsing if it's a string or weird format
        return pd.to_datetime(date_value, errors='coerce')
    except Exception:
        return pd.NaT


# -- Parse division level --
def parse_division_level(division_name):
    """
    Parse division into clean labels: 'Major', 'A', 'B', 'C'.
    No numbers. No Categorical here yet.
    """
    if pd.isna(division_name) or not isinstance(division_name, str):
        return None
    
    division_name = division_name.strip()
    
    if division_name.startswith('Major') or division_name.startswith('Majors'):
        return 'Major'
    elif division_name.startswith('A'):
        return 'A'
    elif division_name.startswith('B'):
        return 'B'
    elif division_name.startswith('C'):
        return 'C'
    else:
        return None
 
# -- Turn division level into ordered categorical --

def cast_division_level(series):
    """
    Cast a pandas Series to an ordered Categorical type for division levels.
    
    Assumes input Series contains clean strings: 'Major', 'A', 'B', 'C' or None.

    Returns:
        pandas Series: ordered Categorical
    """
    division_order = ['Major', 'A', 'B', 'C']
    return pd.Series(
        pd.Categorical(series, categories=division_order, ordered=True),
        index=series.index
    )

# -- Validate line nubmers --
def validate_line(line_value):
    """
    Validate that line is an integer between 1 and 6 (inclusive).
    Returns the line value if valid, else None.
    """
    valid_lines = {1, 2, 3, 4, 5, 6}
    
    if pd.isna(line_value):
        return None
    
    try:
        line_value = int(line_value)
    except ValueError:
        return None
    
    if line_value in valid_lines:
        return line_value
    else:
        return None

# --- ID and label functions ---
def create_team_match_id(df, date_col='Date_fixed', division_col='Division', 
                         home_col='Home Team', away_col='Away Team'):
    """
    Create temp_team_match_id (shared across all matches in a team match)
    and a readable team_match_id_label.
    
    Returns:
        DataFrame with new columns added.
    """
    df = df.copy()

    # Step 1: Sort by match date to keep IDs sequential
    df = df.sort_values(by=[date_col, division_col, home_col, away_col]).reset_index(drop=True)

    # Step 2: Group rows by team match (Date + Division + Home + Away)
    team_keys = df[[date_col, division_col, home_col, away_col]].astype(str)

    # Step 3: Create group ID (simple increasing ID)
    df['temp_team_match_id'] = (
        team_keys
        .drop_duplicates()
        .reset_index(drop=True)
        .reset_index()  # this gives a sequential ID
        .merge(team_keys, on=[date_col, division_col, home_col, away_col], how='right')
        .sort_index()['index'] + 1  # start IDs from 1
    )

    # Step 4: Create readable team_match_id_label
    df['team_match_id_label'] = (
        df[date_col].dt.strftime('%Y-%m-%d') + ' ' +
        df[division_col].astype(str) + ' ' +
        df[home_col].astype(str) + ' vs ' +
        df[away_col].astype(str)
    )

    return df

def create_match_id(df, 
                    date_col='Date_fixed', 
                    division_col='Division', 
                    home_col='Home Team', 
                    away_col='Away Team', 
                    line_col='Line_validated',
                    home_p1_col='Home Player 1',
                    home_p2_col='Home Player 2',
                    away_p1_col='Away Player 1',
                    away_p2_col='Away Player 2'):
    """
    Create temp_match_id for individual matches (including players and line),
    and a readable temp_match_id_label.
    
    Returns:
        DataFrame with new columns added.
    """
    
    # Map line numbers to line names
    line_mapping = {
            1: "Ladies",
            2: "Mixed 1",
            3: "Mixed 2",
            4: "Mens",
            5: "Open 1",
            6: "Open 2"
        }

    df['Line_label'] = df[line_col].map(line_mapping)

    df = df.copy()

    # Step 1: Sort by match key columns
    df = df.sort_values(
        by=[date_col, division_col, home_col, away_col, line_col, home_p1_col, home_p2_col, away_p1_col, away_p2_col]
    ).reset_index(drop=True)

    # Step 2: Build a unique grouping key
    match_keys = df[[date_col, division_col, home_col, away_col, line_col, home_p1_col, home_p2_col, away_p1_col, away_p2_col]].astype(str)

    # Step 3: Create group ID (simple increasing ID)
    df['temp_match_id'] = (
        match_keys
        .drop_duplicates()
        .reset_index(drop=True)
        .reset_index()
        .merge(match_keys, on=[date_col, division_col, home_col, away_col, line_col, home_p1_col, home_p2_col, away_p1_col, away_p2_col], how='right')
        .sort_index()['index'] + 1
    )

    # Step 4: Create a readable label
    df['temp_match_id_label'] = (
        df[date_col].dt.strftime('%Y-%m-%d') + ' ' +
        df[division_col].astype(str) + ' ' +
        df[home_col].astype(str) + ' vs ' +
        df[away_col].astype(str) + ' (' +
        df[line_col].astype(str) + ' - ' +
        df['Line_label'].astype(str) + ')' + ' - ' +
        df[home_p1_col].astype(str) + ' & ' +
        df[home_p2_col].astype(str) + ' vs ' +
        df[away_p1_col].astype(str) + ' & ' +
        df[away_p2_col].astype(str)
    )
    
    return df








def scan_weird_scores(score_str):
    """
    Detects if a score string contains suspicious patterns like 1-1 [..] or 0-0 [..].
    Returns True if suspicious, False otherwise.
    """
    if pd.isna(score_str) or not isinstance(score_str, str):
        return False
    
    # Look for patterns like 1-1 [something], 0-0 [something]
    if re.search(r'\b(1-1|0-0)\s*\[\d+[^\d]+\d+\]', score_str):
        return True
    else:
        return False


# --- Parsing functions ---
def parse_score_string(score_str):
    """
    Parse a match score string into a list of dictionaries, each containing:
    - home_games
    - away_games
    - home_tb_points
    - away_tb_points
    - tiebreak_type ('none', 'regular', 'super')
    
    Parameters:
        score_str (str): The raw match score string (e.g., '6-4, 6-7 [4-7], 10-8')

    Returns:
        list of dicts: One dict per set
    """
    if pd.isna(score_str) or not isinstance(score_str, str):
        return []
    
    parsed_sets = []
    
    # Split score string by commas
    set_strings = score_str.split(',')
    
    for set_str in set_strings:
        set_str = set_str.strip()
        
        # Extract any tiebreak score inside brackets
        tiebreak_match = re.search(r'\[(\d+)[^\d]+(\d+)\]', set_str)
        if tiebreak_match:
            home_tb_points = int(tiebreak_match.group(1))
            away_tb_points = int(tiebreak_match.group(2))
        else:
            home_tb_points = None
            away_tb_points = None
        
        # Remove brackets from the set score for main parsing
        set_str_clean = re.sub(r'\[.*?\]', '', set_str).strip()
        
        # Extract home and away games
        main_match = re.match(r'(\d+)[^\d]+(\d+)', set_str_clean)
        if not main_match:
            # Skip if can't parse properly
            continue
        
        home_games = int(main_match.group(1))
        away_games = int(main_match.group(2))
        
        # Determine tiebreak type based on games
        if (home_games == 7 and away_games == 6) or (home_games == 6 and away_games == 7):
            tiebreak_type = 'regular'
        elif (home_games == 1 and away_games == 0) or (home_games == 0 and away_games == 1):
            tiebreak_type = 'super'
        else:
            tiebreak_type = 'none'
        
        parsed_sets.append({
            'home_games': home_games,
            'away_games': away_games,
            'home_tb_points': home_tb_points,
            'away_tb_points': away_tb_points,
            'tiebreak_type': tiebreak_type
        })
    
    return parsed_sets




# --- Calculation functions ---

def calculate_set_wins(score_list):
    pass

def calculate_game_wins(score_list):
    pass

def determine_winner(set_wins_home, set_wins_away):
    pass

# --- Row cleaning ---

def clean_match_row(row):
    pass

# --- Full DataFrame cleaning ---

def clean_full_dataframe(df):
    pass
