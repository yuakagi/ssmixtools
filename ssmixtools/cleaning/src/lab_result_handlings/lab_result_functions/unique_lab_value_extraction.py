"""Module to extract unique values for laboratory data cleaning"""

import os
import glob
import pandas as pd
from .....generals import general_config as config
from .....generals.general_utils import archive_file
from ...cleaning_utils import (
    parallel_map_partitions_cln,
    get_cln_settings,
    load_mapping_table,
    map_jlac10_to_text,
)


def _extract_unique_lab_units(df: pd.DataFrame) -> pd.DataFrame:
    """Counts unique units seen in a given dataframe.

    Args:
        df (pd.DataFrame): Target dataframe to be processed. This is supposed to be a chunk
            loaded from a laboratory test result table.
    Returns:
        unique_unit_df (pd.DataFrame): Dataframe that stores unique unit counts
    """
    # Select rows with JLAC10 codes only
    jlac10_mask = (
        df[config.COL_ITEM_CODE].fillna("").str.contains(config.R_JLAC10_CODE, na=False)
    )
    df = df[jlac10_mask]
    # Select rows with numeric values
    df = df.sort_values(config.COL_ITEM_CODE)
    df[config.COL_NUMERIC] = pd.to_numeric(df[config.COL_NUMERIC], errors="coerce")
    numeric_mask = ~(df[config.COL_NUMERIC].isna())
    df = df.loc[numeric_mask, :]
    # Count unique unit values by JLAC10 codes
    unique_unit_df = (
        df.groupby([config.COL_ITEM_CODE, "unit"])[config.COL_NUMERIC]
        .agg(["mean", "count"])
        .reset_index()
    )

    return unique_unit_df


def _extract_unique_nonnumeric_values(df: pd.DataFrame) -> pd.DataFrame:
    """Counts unique nonnumeric values seen in a given dataframe.

    Args:
        df (pd.DataFrame): Target dataframe to be processed. This is supposed to be a chunk
            loaded from a laboratory test result table.
    Returns:
        unique_nonnumeric_df (pd.DataFrame): Dataframe that stores unique nonnumeric value counts.
    """
    # Select rows with JLAC10 codes only
    jlac10_mask = (
        df[config.COL_ITEM_CODE].fillna("").str.contains(config.R_JLAC10_CODE, na=False)
    )
    df = df[jlac10_mask]
    # Select rows with nonnumeric values
    df = df.sort_values(config.COL_ITEM_CODE)
    df[config.COL_NONNUMERIC] = df[config.COL_NONNUMERIC].fillna("")
    nonnum_mask = df[config.COL_NONNUMERIC] != ""
    df = df.loc[nonnum_mask, :]

    # Count unique non-unumeric test result values by JLAC10 codes
    unique_nonnum_df = df.groupby([config.COL_ITEM_CODE])[
        config.COL_NONNUMERIC
    ].value_counts()
    unique_nonnum_df.name = "count"
    unique_nonnum_df = unique_nonnum_df.reset_index()

    return unique_nonnum_df


def extract_units_and_nonnumerics():
    """Counts unique units and nonnumeric test result values seen in all laboratory test result tables.

    The results are saved as a csv file. You can use this table for optional data cleaning.
    """
    internal_dir = get_cln_settings("CLN_INTERNAL_DIR")
    units_path = get_cln_settings("CLN_LAB_UNITS_PTH")
    nonnum_path = get_cln_settings("CLN_LAB_NONUM_PTH")
    temp_units_path = os.path.join(internal_dir, os.path.basename(units_path))
    temp_nonnum_path = os.path.join(internal_dir, os.path.basename(nonnum_path))
    csv_path_pattern = os.path.join(internal_dir, config.LAB_RESULT_TABLE_PATTERN)

    # Prepare the table for adding the recommended units
    jlac10_to_unit = load_mapping_table(
        original_code_system=config.JLAC10, target_code_system="unit"
    )
    jlac10_to_unit = jlac10_to_unit.rename(
        columns={
            config.COL_ORIGINAL: config.COL_ITEM_CODE,
            config.COL_TARGET: "recommended_unit",
        }
    )

    # Extract unique laboratory test result units
    print("Extracting units...")
    _ = parallel_map_partitions_cln(
        csv_path_pattern=csv_path_pattern,
        function=_extract_unique_lab_units,
        chunksize=-1,
        output_csv_path=temp_units_path,
        single_file=False,
    )

    # Extract unique nonnumeric test result values
    print("Extracting nonnumeric values...")
    _ = parallel_map_partitions_cln(
        csv_path_pattern=csv_path_pattern,
        function=_extract_unique_nonnumeric_values,
        chunksize=-1,
        output_csv_path=temp_nonnum_path,
        single_file=False,
    )

    # Aggregate unit tables
    temp_unit_files = glob.glob(temp_units_path.replace(".csv", "*.csv"))
    unique_unit_df = None
    for file in temp_unit_files:
        temp_df = pd.read_csv(file, header=0, na_values=config.NA_VALUES)
        if unique_unit_df is None:
            unique_unit_df = temp_df
        else:
            unique_unit_df = pd.concat([unique_unit_df, temp_df])
            unique_unit_df["mean"] *= unique_unit_df["count"]
            unique_unit_df = (
                unique_unit_df.groupby([config.COL_ITEM_CODE, "unit"])
                .sum()
                .reset_index()
            )
            unique_unit_df["mean"] /= unique_unit_df["count"]
        os.remove(file)

    # Map JLAC10 codes to texts to make optional inspection of the tables easier
    unique_unit_df["text"] = map_jlac10_to_text(
        unique_unit_df[config.COL_ITEM_CODE],
        readable=False,
        japanese=True,
    )
    # Add a column for the recommended units
    unique_unit_df = pd.merge(
        unique_unit_df, jlac10_to_unit, on=config.COL_ITEM_CODE, how="left"
    )
    # Add columns for optional data entry
    unique_unit_df["method_agnostic"] = unique_unit_df[
        config.COL_ITEM_CODE
    ].str.replace(r"(\w{12})\w{3}(\w{2})", r"\1---\2", regex=True)
    unique_unit_df["modified"] = unique_unit_df["unit"].copy()
    unique_unit_df["add_before_multiplication"] = 0
    unique_unit_df["multiply_by"] = 1
    unique_unit_df["add_after_multiplication"] = 0
    unique_unit_df["comment"] = "comment:"

    # Organize columns
    unique_unit_df = unique_unit_df[
        [
            config.COL_ITEM_CODE,
            "method_agnostic",
            "unit",
            "modified",
            "recommended_unit",
            "add_before_multiplication",
            "multiply_by",
            "add_after_multiplication",
            "count",
            "mean",
            "text",
            "comment",
        ]
    ]

    # Aggregate nonnumeric value tables
    temp_nonum_files = glob.glob(temp_nonnum_path.replace(".csv", "*.csv"))
    unique_nonnumeric_df = None
    for file in temp_nonum_files:
        temp_df = pd.read_csv(file, header=0, na_values=config.NA_VALUES)
        if unique_nonnumeric_df is None:
            unique_nonnumeric_df = temp_df
        else:
            unique_nonnumeric_df = pd.concat([unique_nonnumeric_df, temp_df])
            unique_nonnumeric_df = (
                unique_nonnumeric_df.groupby(
                    [config.COL_ITEM_CODE, config.COL_NONNUMERIC]
                )
                .sum()
                .reset_index()
            )
        os.remove(file)
    # Map JLAC10 codes to texts to make optional inspection of the tables easier
    unique_nonnumeric_df["text"] = map_jlac10_to_text(
        unique_nonnumeric_df[config.COL_ITEM_CODE],
        readable=False,
        japanese=True,
    )
    # Copy 'config.COL_NONNUMERIC' column for optional modification process
    unique_nonnumeric_df["modified"] = unique_nonnumeric_df[
        config.COL_NONNUMERIC
    ].copy()
    # Add an empty column to store new units for nonnumeric values that are converted to numeric values
    unique_nonnumeric_df["new_unit"] = "no_unit"
    # Add a column for comments
    unique_nonnumeric_df["comment"] = "comment:"

    # Reorder columns
    unique_nonnumeric_df = unique_nonnumeric_df[
        [
            config.COL_ITEM_CODE,
            "text",
            config.COL_NONNUMERIC,
            "modified",
            "new_unit",
            "count",
            "comment",
        ]
    ]

    # Archive existing optional maps
    for path in [units_path, nonnum_path]:
        if os.path.exists(path):
            archive_file(path)

    # Save
    unique_unit_df.to_csv(units_path, header=True, index=False)
    unique_nonnumeric_df.to_csv(nonnum_path, header=True, index=False)
