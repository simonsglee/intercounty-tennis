# tests/test_cleaning.py

import pandas as pd
import pytest
from scripts.cleaning import (
    fix_match_date, 
    parse_division_level, 
    cast_division_level, 
    validate_line,
    create_team_match_id,
    create_match_id
    )

# --- Test fix_match_date ---

def test_fix_match_date_valid():
    assert fix_match_date('2025-06-03') == pd.Timestamp('2025-06-03')
    assert fix_match_date('6/3/2025') == pd.Timestamp('2025-06-03')
    assert fix_match_date('May 12th 2024') == pd.Timestamp('2024-05-12')
    assert fix_match_date('2025/08/13 7:00 PM') == pd.Timestamp('2025-08-13 19:00:00')

def test_fix_match_date_invalid():
    assert pd.isna(fix_match_date('invalid date'))
    assert pd.isna(fix_match_date(None))

# --- Test parse_division_level ---

def test_parse_division_level_valid():
    assert parse_division_level('A - West') == 'A'
    assert parse_division_level('Major - East') == 'Major'
    assert parse_division_level('Majors - Central') == 'Major'
    assert parse_division_level('C - North') == 'C'

def test_parse_division_level_invalid():
    assert parse_division_level('X - Division') is None
    assert parse_division_level(None) is None

# --- Test cast_division_level ---

def test_cast_division_level_order():
    series = pd.Series(['Major', 'A', 'B', 'C'])
    cat_series = cast_division_level(series)
    assert cat_series.cat.categories.tolist() == ['Major', 'A', 'B', 'C']
    assert cat_series.cat.ordered is True

# --- Test validate_line ---

def test_validate_line_valid():
    for i in range(1, 7):
        assert validate_line(i) == i

def test_validate_line_invalid():
    assert validate_line(0) is None
    assert validate_line(7) is None
    assert validate_line('Mixed Doubles') is None

# -- Test team match id --
def test_create_team_match_id_grouping():
    # Create a small test DataFrame
    test_df = pd.DataFrame({
        'Date_fixed': pd.to_datetime([
            '2025-06-01', '2025-06-01', '2025-06-03'
        ]),
        'Division': ['A', 'A', 'A'],
        'Home Team': ['Toronto Aces', 'Toronto Aces', 'Oakville Rockets'],
        'Away Team': ['Scarborough Smashers', 'Scarborough Smashers', 'Mississauga Smashers'],
        'Line': [1, 2, 1]
    })
    
    # Apply function
    df_result = create_team_match_id(test_df)

    # --- Assertions ---

    # Check that matches 0 and 1 (same matchup) have the same temp_team_match_id
    assert df_result.loc[0, 'temp_team_match_id'] == df_result.loc[1, 'temp_team_match_id']

    # Check that match 2 (different matchup) has a different temp_team_match_id
    assert df_result.loc[0, 'temp_team_match_id'] != df_result.loc[2, 'temp_team_match_id']

    # Check that team_match_id_label is formatted correctly
    assert df_result.loc[0, 'team_match_id_label'] == '2025-06-01 A Toronto Aces vs Scarborough Smashers'
    assert df_result.loc[2, 'team_match_id_label'] == '2025-06-03 A Oakville Rockets vs Mississauga Smashers'
    
def test_create_match_id_basic():
    # Create a small test DataFrame
    test_df = pd.DataFrame({
        'Date_fixed': pd.to_datetime([
            '2025-06-01', '2025-06-01', '2025-06-03'
        ]),
        'Division': ['A', 'A', 'A'],
        'Home Team': ['Toronto Aces', 'Toronto Aces', 'Oakville Rockets'],
        'Away Team': ['Scarborough Smashers', 'Scarborough Smashers', 'Mississauga Smashers'],
        'Line_validated': [1, 2, 1],
        'Home Player 1': ['Alice', 'Alice', 'Charlie'],
        'Home Player 2': ['Alice2', 'Alice2', 'Charlie2'],
        'Away Player 1': ['Bob', 'Bob', 'David'],
        'Away Player 2': ['Bob2', 'Bob2', 'David2']
    })

    # Apply the function
    df_result = create_match_id(test_df)

    # --- Assertions ---

    # Check number of matches = number of rows
    assert df_result['temp_match_id'].nunique() == len(df_result)

    # Check that labels contain both line number and name
    assert '(1 - Ladies)' in df_result.loc[0, 'temp_match_id_label']
    assert '(2 - Mixed 1)' in df_result.loc[1, 'temp_match_id_label']

    # Check player names are included in label
    assert 'Alice & Alice2' in df_result.loc[0, 'temp_match_id_label']
    assert 'Bob & Bob2' in df_result.loc[0, 'temp_match_id_label']

