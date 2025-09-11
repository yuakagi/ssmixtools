"""Module to clean lab values"""

import os
import json
import pandas as pd
from ...cleaning_utils import parallel_map_partitions_cln, get_cln_settings
from .....generals import general_config as config
from .....generals.general_utils import tally_stats, all_values_to_int


def _clean_units_and_nonnumerics(
    df: pd.DataFrame, unit_map: pd.DataFrame, nonnum_map: pd.DataFrame
) -> pd.DataFrame:
    """Helper function that converts units and nonnumeric values into cleaned ones using
    optionally modified mapping tables.

    Args:
        df (pd.DataFrame): Dataframe to be processed.
        unit_map (pd.DataFrame): Mapping table to map original units to cleaned units. This is loaded
            from 'config.EXTRACTED_UNIQUE_LAB_UNITS_MODIFIED'
        nonnum_map (pd.DataFrame): Mapping table to map original nonnumeric test result values to
            values. This is loaded from 'config.EXTRACTED_UNIQUE_NONNUMERICS_MODIFIED'
    Returns:
        df (pd.DataFrame): Cleaned dataframe
    """
    process_analytics = {"rows_before_unit_nonnumeric_cleaning": len(df)}
    # Save the default columns
    default_cols = list(df.columns)
    # Create a new column for cleaned units (column name: 'modified')
    df = pd.merge(
        left=df, right=unit_map, on=[config.COL_ITEM_CODE, "unit"], how="left"
    )
    # Drop the original units, and rename the added new column to 'units'
    df = df.drop("unit", axis=1)
    df = df.rename(columns={"modified": "unit"})
    # Value correction
    numeric_cols = [
        config.COL_NUMERIC,
        "add_before_multiplication",
        "multiply_by",
        "add_after_multiplication",
    ]
    for col in numeric_cols:
        df.loc[:, col] = pd.to_numeric(df[col], errors="coerce")
    df.loc[:, config.COL_NUMERIC] += df.loc[:, "add_before_multiplication"]
    df.loc[:, config.COL_NUMERIC] *= df.loc[:, "multiply_by"]
    df.loc[:, config.COL_NUMERIC] += df.loc[:, "add_after_multiplication"]

    # Create a new column for cleaned nonnumeric values (column name: 'modified')
    df = pd.merge(
        left=df,
        right=nonnum_map,
        on=[config.COL_ITEM_CODE, config.COL_NONNUMERIC],
        how="left",
    )
    # Drop the original nonnumerics, and rename the added new column to 'nonnumeric'
    df = df.drop(config.COL_NONNUMERIC, axis=1)
    df = df.rename(columns={"modified": config.COL_NONNUMERIC})

    # Find numeric values mixed in the nonnumeric column, and move them to the numeric column if any
    df["numerics_added"] = pd.to_numeric(df[config.COL_NONNUMERIC], errors="coerce")
    added_numeric_mask = ~df["numerics_added"].isna()
    df[config.COL_NUMERIC] = df[config.COL_NUMERIC].mask(
        added_numeric_mask, df["numerics_added"]
    )
    df["unit"] = df["unit"].mask(added_numeric_mask, df["new_unit"])
    df[config.COL_NONNUMERIC] = df[config.COL_NONNUMERIC].mask(added_numeric_mask, None)
    # Drop cols
    df = df[default_cols]

    # Find non-record rows and drop them
    unit_nar_mask = df["unit"] == config.LAB_NOT_A_RECORD
    nonnum_nar_mask = df[config.COL_NONNUMERIC] == config.LAB_NOT_A_RECORD
    total_nar_mask = unit_nar_mask | nonnum_nar_mask
    df = df.loc[~total_nar_mask, :]
    process_analytics["non_laboratory_result_rows"] = int(total_nar_mask.sum())

    # Find rows without results after cleaning and drop them
    with_numerics = (~df[config.COL_NUMERIC].isna()) & (
        ~df["unit"].replace("", None).isna()
    )
    with_nonnumerics = ~df[config.COL_NONNUMERIC].replace("", None).isna()
    missing_results = ~(with_numerics | with_nonnumerics)
    jlac10s_missing_results = all_values_to_int(
        df.loc[missing_results, config.COL_ITEM_CODE].value_counts().to_dict()
    )
    process_analytics["missing_results_after_cleaning"] = int(missing_results.sum())
    process_analytics["codes_with_missing_results"] = jlac10s_missing_results

    # Final stats
    process_analytics["rows_after_cleaning"] = len(df)

    return df, process_analytics


def clean_units_and_nonnumerics():
    """Cleans units and nonnumeric values.
    See helper functions for details.
    """
    source_dir = get_cln_settings("CLN_OUTPUT_TABLES_DIR")
    internal_dir = get_cln_settings("CLN_INTERNAL_DIR")
    units_path = get_cln_settings("CLN_LAB_UNITS_PTH")
    nonnum_path = get_cln_settings("CLN_LAB_NONUM_PTH")
    mapping_sheet_pattern = get_cln_settings("CLN_MAPPING_SHEET_PTN")
    json_path = mapping_sheet_pattern.replace("*", "unit_nonnumeric_optional")
    data_type = "OML-11"
    file_name_pattern = config.RECORD_TABLE_PARAMS[data_type]["file_name_pattern"]
    csv_path_pattern = os.path.join(source_dir, "**", file_name_pattern)
    output_csv_path = os.path.join(internal_dir, file_name_pattern)
    single_file = config.SINGLE_FILE[data_type]
    # Load tables
    unit_map = pd.read_csv(units_path, dtype=str, na_values=config.NA_VALUES, header=0)
    unit_map = unit_map[
        [
            config.COL_ITEM_CODE,
            "unit",
            "modified",
            "add_before_multiplication",
            "multiply_by",
            "add_after_multiplication",
        ]
    ]
    nonnum_map = pd.read_csv(
        nonnum_path, dtype=str, na_values=config.NA_VALUES, header=0
    )
    nonnum_map = nonnum_map[
        [config.COL_ITEM_CODE, config.COL_NONNUMERIC, "modified", "new_unit"]
    ]

    stats_list = parallel_map_partitions_cln(
        csv_path_pattern=csv_path_pattern,
        function=_clean_units_and_nonnumerics,
        chunksize=-1,
        output_csv_path=output_csv_path,
        single_file=single_file,
        unit_map=unit_map,
        nonnum_map=nonnum_map,
    )
    process_analytics = tally_stats(stats_list)

    # Save the mapping results as JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(process_analytics, f, indent=2, ensure_ascii=False)
