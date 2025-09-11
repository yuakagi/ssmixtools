"""Module to clean OML-11"""

import os
import json
import pandas as pd
from ...cleaning_utils import parallel_map_partitions_cln
from ...cleaning_settings import get_cln_settings
from ...cleaning_utils import remove_method_from_jlac10
from .....generals import general_config as config
from .....generals.general_utils import tally_stats


def _clean_standardized_codes(df: pd.DataFrame, code_type: str) -> tuple:
    """Cleans standardized codes such as ICD-10, ATC and JLAC10 codes.
    This process takes following steps:
        - 1. Exclude records with missing codes
        - 2. Exclude codes shorter than the minimal code length
        - 3. Exclude or truncate codes longer than the max code length
        - 4. Validate codes with regular expression, and exclude irregular codes
    Stats of these irregular codes are summarized in a dictionary.
    Args:
        df (pd.DataFrame): Target dataframe.
        code_col (str): Type of code (ICD-10, ATC, JLAC10).
    Returns:
        df (pd.DataFrame): Cleaned dataframe.
        irregular_code_stats (dict): Dictionary that contains summary of irregular code stats.
    """
    # Original length
    original_n_records = len(df)
    # Check params
    code_col = config.COL_ITEM_CODE
    params = config.CODE_PARAMS[code_type]
    min_length = params["min_length"]
    max_length = params["max_length"]
    code_regex = params["code_regex"]
    truncate_long_codes = params["truncate_long_code"]
    # Replacing missing values with empty strings ("") for string operations
    df[code_col] = df[code_col].fillna("")

    # ********************************
    # * Type specific preprocessings *
    # ********************************
    if code_type == config.ICD10:
        # Remove dots '.' from ICD10 codes
        df[code_col] = df[code_col].replace(r"(^[A-Z]\d{2})\.", r"\1", regex=True)

    #  Add more steps here if needed.
    #  ...
    #  ...

    # *************************
    # * Common cleaning steps *
    # *************************
    # Inspect and drop missing codes first
    missing_mask = df[code_col] == ""
    n_missing = missing_mask.sum()
    df = df.loc[~missing_mask]
    # Inspect code length
    df["code_length"] = df[code_col].str.len()
    short_mask = df["code_length"] < min_length
    long_mask = df["code_length"] > max_length
    short_codes = df.loc[short_mask, code_col].value_counts().to_dict()
    short_total = sum(i for i in short_codes.values())
    long_codes = df.loc[long_mask, code_col].value_counts().to_dict()
    long_total = sum(i for i in long_codes.values())
    df = df.drop("code_length", axis=1)
    if truncate_long_codes:
        df[code_col] = df[code_col].str.slice(0, max_length)
        df = df.loc[~short_mask]
    else:
        df = df.loc[~(short_mask | long_mask)]

    # Inspect codes with regular expression
    valid_pattern_mask = df[code_col].str.match(code_regex, na=True)
    invalid_pattern_mask = ~valid_pattern_mask
    invalid_codes = df.loc[invalid_pattern_mask, code_col].value_counts().to_dict()
    invalid_total = sum(i for i in invalid_codes.values())
    df = df.loc[~invalid_pattern_mask]

    # Count the number of dropped records
    n_dropped = original_n_records - len(df)
    # Write summary
    long_code_handling = "truncated" if truncate_long_codes else "excluded"
    irregular_code_stats = {
        "missing codes": {"total": n_missing},
        "short codes (excluded)": {
            "total": short_total,
            "unique values": short_codes,
        },
        f"long codes ({long_code_handling})": {
            "total": long_total,
            "unique values": long_codes,
        },
        "irregular codes after code length handling": {
            "total": invalid_total,
            "unique values": invalid_codes,
        },
        "total number of records excluded": n_dropped,
    }

    # ********************************
    # * Type specific preprocessings *
    # ********************************
    if code_type == config.JLAC10:
        df[code_col] = remove_method_from_jlac10(df[code_col])

    #  Add more steps here if needed.
    #  ...
    #  ...

    return df, irregular_code_stats


def _clean_optional(df: pd.DataFrame, params: dict):
    # Initialize stats
    stats = {}
    original_n_records = len(df)

    # *****************
    # * Code cleaning *
    # *****************
    code_type = params["code_type"]
    if code_type is not None:
        df, irregular_code_stats = _clean_standardized_codes(df, code_type=code_type)
        stats["code cleaning details"] = irregular_code_stats

    # ***********************
    # * Drop missing values *
    # ***********************
    # Replace empty strings with None
    df = df.replace("", None)
    # Dropna 'any'
    n_records = len(df)
    any_subset = params["dropna_any"]
    if any_subset is not None:
        # Count
        dropna_any_stats = {}
        for col in any_subset:
            dropna_any_stats[col] = df[col].isna().sum()
        # drop
        df = df.dropna(subset=any_subset, how="any")
        # Finalize stats
        dropna_any_stats["n excluded"] = n_records - len(df)
        stats["records with missing values (single col, excluded)"] = dropna_any_stats
    # Dropna 'all'
    n_records = len(df)
    all_subset = params["dropna_all"]
    if all_subset is not None:
        # Count
        dropna_all_stats = {}
        cols_str = "-".join(all_subset)
        dropna_all_stats[cols_str] = df[all_subset].isna().all(axis=1).sum()
        # drop
        df = df.dropna(subset=all_subset, how="all")
        # Finalize stats
        dropna_all_stats["n excluded"] = n_records - len(df)
        stats["records with values missing together (excluded)"] = dropna_all_stats

    # Collect stats
    stats["n excluded"] = original_n_records - len(df)
    stats["final n records"] = len(df)

    return df, stats


def clean_optional():
    """Performs optional cleaning steps.
    This process does not drop records with missing data.
    """
    # Initialize variables
    source_tables_dir = get_cln_settings("CLN_OUTPUT_TABLES_DIR")
    internal_dir = get_cln_settings("CLN_INTERNAL_DIR")
    sheet_pattern = get_cln_settings("CLN_CLEANING_SHEET_PTN")
    json_path = sheet_pattern.replace("*", "optional_cleaning")
    process_analytics = {}
    for data_type, params in config.RECORD_TABLE_PARAMS.items():
        file_name_pattern = params["file_name_pattern"]
        csv_path_pattern = os.path.join(source_tables_dir, "**", file_name_pattern)
        output_csv_path = os.path.join(internal_dir, file_name_pattern)
        single_file = config.SINGLE_FILE[data_type]

        # Execute the helper function
        stats_list = parallel_map_partitions_cln(
            csv_path_pattern=csv_path_pattern,
            function=_clean_optional,
            output_csv_path=output_csv_path,
            chunksize=-1,
            single_file=single_file,
            single_stat_file=False,
            params=config.RECORD_TABLE_PARAMS[data_type],
        )
        process_analytics[data_type] = tally_stats(stats_list)

    # Save the mapping results as JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(process_analytics, f, indent=2, ensure_ascii=False)
