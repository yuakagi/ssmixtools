"""Module to clean JLAC10 codes with an optional map."""

import os
import json
import pandas as pd
from ...cleaning_settings import get_cln_settings
from ...cleaning_utils import parallel_map_partitions_cln
from .....generals import general_config as config
from .....generals.general_utils import tally_stats


def _map_oml_11_optional(
    df: pd.DataFrame,
    jlac10_to_jlac10: pd.DataFrame,
) -> tuple:
    """Helper function to map irregular JLAC10 codes to standardized JLAC10 codes.

    Args:
        df (pd.DataFrame): Dataframe to be processed.
        jlac10_to_jlac10 (pd.DataFrame): Mapping table for JLAC10 codes..
    Returns:
        df (pd.DataFrame): Dataframe with cleaned JLAC10 codes.
        process_analytics (dict): Summary of the code mapping process.
    """

    # Initialize
    # NOTE (Yu Akagi): At this point, the values in the column 'JLAC10' have not been cleaned, they are the original obseved values. Therefore, it contains local codes.
    process_analytics = {}
    jlac10_existing_before_mapping = (
        df[config.COL_ITEM_CODE].fillna("").str.contains(config.R_JLAC10_CODE, na=False)
    )

    # Merge and add the new column 'modified'
    jlac10_to_jlac10.loc[
        :, [config.COL_ITEM_CODE, config.COL_ITEM_NAME, "modified"]
    ] = jlac10_to_jlac10.loc[
        :, [config.COL_ITEM_CODE, config.COL_ITEM_NAME, "modified"]
    ].fillna(
        ""
    )
    df.loc[:, [config.COL_ITEM_CODE, config.COL_ITEM_NAME]] = df.loc[
        :, [config.COL_ITEM_CODE, config.COL_ITEM_NAME]
    ].fillna("")
    df = pd.merge(
        df,
        jlac10_to_jlac10,
        on=[config.COL_ITEM_CODE, config.COL_ITEM_NAME],
        how="left",
    )

    # If a modified code is missing (that is, deleted from the mapping table), the record is treated as 'not-a-record'
    df.loc[df["modified"].isna(), "modified"] = config.LAB_NOT_A_RECORD

    # Replace the old JLAC10 codes with the mapped codes
    df.loc[:, config.COL_ITEM_CODE] = df["modified"].copy()
    df = df.drop("modified", axis=1)
    df.loc[:, [config.COL_ITEM_CODE, config.COL_ITEM_NAME]] = df.loc[
        :, [config.COL_ITEM_CODE, config.COL_ITEM_NAME]
    ].replace("", None)

    # Handle rows that actually are not laboratory records ('not-a-record' rows, such as just comments.)
    # NOTE: These records are dropped here.
    nars = df[config.COL_ITEM_CODE] == config.LAB_NOT_A_RECORD
    n_initial_rows = len(df)
    n_nars = int(nars.sum())
    df = df.loc[~nars, :]
    n_lab_result_rows = len(df)

    # Count missing codes
    missing_after_mapping = df[config.COL_ITEM_CODE].isna()

    # Inspect data
    jlac10_existing_after_mapping = df[config.COL_ITEM_CODE].str.contains(
        config.R_JLAC10_CODE, na=False
    )
    irregular_jlac10_after_mapping = ~df[config.COL_ITEM_CODE].str.contains(
        config.R_JLAC10_CODE, na=True
    )
    irregular_jlac10_list = (
        df.loc[irregular_jlac10_after_mapping, config.COL_ITEM_CODE].unique().tolist()
    )

    # Saving analytics to the dictionary
    process_analytics["total_rows_before_mapping"] = n_initial_rows
    process_analytics["non_laboratory_result_rows"] = n_nars
    process_analytics["true_laboratory_result_rows"] = int(n_lab_result_rows)
    process_analytics["JLAC10_before_mapping"] = int(
        jlac10_existing_before_mapping.sum()
    )
    process_analytics["JLAC10_after_mapping"] = int(jlac10_existing_after_mapping.sum())
    process_analytics["JLAC10_missing_after_mapping"] = int(missing_after_mapping.sum())
    process_analytics["irregular_JLAC10_codes_after_mapping"] = int(
        (irregular_jlac10_after_mapping).sum()
    )
    process_analytics["total_rows_after_mapping"] = len(df)
    process_analytics["irregular_JLAC10_list"] = irregular_jlac10_list

    return df, process_analytics


def map_oml_11_optional():
    """Maps irregular JLAC10 codes to standardized JLAC10 codes"""
    # Initialize variables
    source_tables_dir = get_cln_settings("CLN_OUTPUT_TABLES_DIR")
    internal_dir = get_cln_settings("CLN_INTERNAL_DIR")
    mapping_sheet_pattern = get_cln_settings("CLN_MAPPING_SHEET_PTN")
    data_type = "OML-11"
    file_name_pattern = config.RECORD_TABLE_PARAMS[data_type]["file_name_pattern"]
    csv_path_pattern = os.path.join(source_tables_dir, "**", file_name_pattern)
    output_csv_path = os.path.join(internal_dir, file_name_pattern)
    json_path = mapping_sheet_pattern.replace("*", "JLAC10_optional")
    single_file = config.SINGLE_FILE[data_type]

    # Load mapping tables.
    optional_jlac10_map_pattern = get_cln_settings("CLN_OPTIONAL_MAP_PTN")
    optional_jlac10_path = optional_jlac10_map_pattern.replace("*", "JLAC10_to_JLAC10")
    jlac10_to_jlac10 = pd.read_csv(
        optional_jlac10_path,
        na_values=config.NA_VALUES,
        dtype=str,
        usecols=[config.COL_ITEM_CODE, config.COL_ITEM_NAME, "modified"],
    )
    for col in [config.COL_ITEM_CODE, config.COL_ITEM_NAME]:
        # Fill the missing values with empty strings
        jlac10_to_jlac10[col] = jlac10_to_jlac10[col].fillna("").str.strip()
    jlac10_to_jlac10 = jlac10_to_jlac10.drop_duplicates(
        subset=([config.COL_ITEM_CODE, config.COL_ITEM_NAME])
    )

    # Execute the helper function
    stats_list = parallel_map_partitions_cln(
        csv_path_pattern=csv_path_pattern,
        function=_map_oml_11_optional,
        output_csv_path=output_csv_path,
        chunksize=-1,
        single_file=single_file,
        single_stat_file=False,
        jlac10_to_jlac10=jlac10_to_jlac10,
    )
    process_analytics = tally_stats(stats_list)
    for k in process_analytics:
        process_analytics[k]["irregular_JLAC10_list"] = list(
            set(process_analytics[k]["irregular_JLAC10_list"])
        )

    # Save the mapping results as JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(process_analytics, f, indent=2, ensure_ascii=False)
