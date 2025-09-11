"""Module to clean OML-11"""

import os
import numpy as np
import pandas as pd
from ...cleaning_utils import (
    parallel_map_partitions_cln,
    convert_timedelta_to_timestamp,
    assign_unique_record_numbers,
)
from ...cleaning_settings import get_cln_settings
from .....generals import general_config as config


def _get_power(matchobj):
    pre = matchobj.group(1)
    number = matchobj.group(2)
    post = matchobj.group(3)
    n_zeros = number.count("0")
    if n_zeros > 1:
        return f"{pre}10^{n_zeros}{post}"
    return number


def normalize_exponentials(df: pd.DataFrame, col: str) -> np.ndarray:
    """Normalizes powers of 10 (e.g., 100, 1000, 10000, etc)"""
    # Values in integers
    pattern = r"(\D*)(1[,0]+)(\D*)"
    normalized_units = (
        df[col].fillna("").str.replace(pattern, repl=_get_power, regex=True)
    )

    return normalized_units.values


def _clean_oml_11(
    df: pd.DataFrame,
    file_tag: str,
    pid: int,
    timestamp_cols: list,
    final_cols: list,
    dob_map: pd.DataFrame,
) -> pd.DataFrame:
    """Cleans OML-11 tables.

    Cleaning steps:

        - Convert timedelta values back to timestamps
        - Clean JLAC10 codes
            - Validate JLAC10 codes
            - Drop irregular codes
        - Clean Units
            - Drop coded unit values
            - Select unit values of plain text expression as the 'unit' column
            - Normalize unit values
        - Drop unnecessary columns
        - Assign unique record IDs

    Args:
        df (pd.DataFrame): Dataframe to be cleaned.
        file_tag (str): File identity tag, passed from 'parallel_map_partitions_cln'
        pid (int): Child process ID
        timestamp_cols (list): Values in the columns in this list are converted to timestamps.
        final_cols (list): List of column names included in the final product table.
            Columns not in this list are all dropped.
        dob_map (pd.DataFrame): Table containing a column of patient IDs and another column of DOBs.
    Returns:
        df (pd.DataFrame): Cleaned dataframe.

    NOTE: The SS-MIX2 implementation guidelines allow to record units for laboratory test
        results both in standardized codes such as ISO and plain text expressions such
        as 'mg/dL'; however, many units for laboratory values are lacking in standardized
        coding schemes, plain text expressions of units are selected.
    """
    # Convert timedelta to timestamp
    df = convert_timedelta_to_timestamp(df, timestamp_cols, dob_map)

    # Create a column to store plain text prescription data.
    df[config.COL_ITEM_NAME] = df["lab_text"].fillna("")

    # Create a column for JLAC10 codes, replacing obviously irregular codes with empty strings
    jlac10_mask = df["lab_code"].fillna("").str.contains(
        config.R_JLAC10_CODE, na=False
    ) & df["lab_coding_system"].fillna("").str.contains(config.R_JLAC10, na=False)
    df[config.COL_ITEM_CODE] = df["lab_code"].mask(~jlac10_mask, "")
    df[config.COL_ITEM_CODE] = df["lab_code"].copy()

    # Create a column for unit (combining 'unit text' and 'unit code').
    df["unit"] = df["unit_text"].fillna(df["unit_code"])

    # Normalize units (e.g., 'ml' is replaced with 'mL')
    df["unit"] = df["unit"].fillna("").replace(config.UNIT_NORMALIZE_DICT, regex=True)

    # Normalize powers of 10
    df["unit"] = normalize_exponentials(df, "unit")

    # Remove unnecessary marks (e.g., '?' etc)
    remove_dict = {k: "" for k in config.LAB_REMOVED_MARKS}
    df["value"] = df["value"].str.translate(str.maketrans(remove_dict))
    df["value"] = df["value"].str.strip()

    # Split values into 'numeric' and 'nonnumeric'.
    df[config.COL_NUMERIC] = pd.to_numeric(df["value"], errors="coerce")
    non_numeric_mask = df[config.COL_NUMERIC].isna()
    df[config.COL_NONNUMERIC] = df["value"].mask(~non_numeric_mask, None)

    # Normalize variable expressions of (+), (-), (+-)
    pos_neg_expressions = config.POS_NEG_EXPRESSIONS
    pos_neg_replacement_dict = {k: v for v, l in pos_neg_expressions.items() for k in l}
    df[config.COL_NONNUMERIC] = (
        df[config.COL_NONNUMERIC].str.strip().replace(pos_neg_replacement_dict)
    )

    # Set placeholders ('no_unit') for numeric values with no units
    # (This is supposed to be applied to numeric values that intrinsically do not have units, such as ratios.)
    missing_unit = df["unit"].fillna("") == ""
    numeric_present = ~(df[config.COL_NUMERIC].isna())
    df["unit"] = df["unit"].mask(missing_unit & numeric_present, "no_unit")

    # Drop unnecessary columns and reorder columns.
    df = df[final_cols]

    # Assign unique record IDs
    df = assign_unique_record_numbers(
        df, data_type_tag="oml11", file_tag=file_tag, pid=pid
    )

    return df


def clean_oml_11():
    """Cleans OML-11 tables.
    See the helper function '_clean_oml_11' for the processing details.
    """
    source_dir = get_cln_settings("CLN_SOURCE_DIR")
    internal_dir = get_cln_settings("CLN_INTERNAL_DIR")
    data_type = "OML-11"
    timestamp_cols = config.RECORD_TABLE_PARAMS[data_type]["timestamps"]
    final_cols = config.RECORD_TABLE_PARAMS[data_type]["final_columns"]
    file_name_pattern = config.RECORD_TABLE_PARAMS[data_type]["file_name_pattern"]
    csv_path_pattern = os.path.join(source_dir, "**", f"{data_type}_*.csv")
    output_csv_path = os.path.join(internal_dir, file_name_pattern)
    single_file = config.SINGLE_FILE[data_type]

    _ = parallel_map_partitions_cln(
        csv_path_pattern=csv_path_pattern,
        function=_clean_oml_11,
        output_csv_path=output_csv_path,
        chunksize=-1,
        single_file=single_file,
        file_tag_as_arg=True,
        pid_as_arg=True,
        dob_map_as_arg=True,
        timestamp_cols=timestamp_cols,
        final_cols=final_cols,
    )
