from metadata_utils import (
    fix_match_date, 
    parse_division_level, 
    cast_division_level, 
    validate_line,
    create_team_match_id,
    create_match_id
    )

from validation_utils import (
    validate_dates, validate_division_levels, validate_line_values,
    validate_team_match_lines, validate_unique_temp_match_ids
)


def clean_metadata_pipeline(df_raw):
    """
    Clean and validate metadata (dates, divisions, lines, IDs) from a raw DataFrame.
    
    Parameters:
    -----------
    df_raw : pandas.DataFrame
        Raw match data with columns like 'Date', 'Division', 'Line', 'Home Team', 'Away Team'.
    
    Returns:
    --------
    df_clean : pandas.DataFrame
        Cleaned and validated DataFrame.
    """
    # --- Step 1: Dates ---
    df_raw['Date_fixed'] = df_raw['Date'].apply(fix_match_date)
    validate_dates(df_raw)

    # --- Step 2: Divisions ---
    df_raw['division_level'] = df_raw['Division'].apply(parse_division_level)
    df_raw['division_level'] = cast_division_level(df_raw['division_level'])
    validate_division_levels(df_raw)

    # --- Step 3: Lines ---
    df_raw['Line_validated'] = df_raw['Line'].apply(validate_line)
    validate_line_values(df_raw)

    # --- Step 4: Team Match IDs ---
    df_raw = create_team_match_id(df_raw)
    validate_team_match_lines(df_raw)

    # --- Step 5: Individual Match IDs ---
    df_raw = create_match_id(df_raw)
    validate_unique_temp_match_ids(df_raw)

    return df_raw


