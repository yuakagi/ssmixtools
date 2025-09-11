"""Module to clean OML-11"""

import os
import glob
import pandas as pd
from ...cleaning_utils import (
    parallel_map_partitions_cln,
    load_mapping_table,
    map_jlac10_to_text,
    remove_method_from_jlac10,
)
from .....generals import general_config as config
from .....generals.general_utils import archive_file
from ...cleaning_settings import get_cln_settings


def _create_jlac10_cleaning_table(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Creates a DataFrame template for optional JLAC10 code mapping based on laboratory data"""
    # Select columns
    df = df.loc[
        :,
        [
            config.COL_ITEM_CODE,
            config.COL_ITEM_NAME,
            config.COL_NUMERIC,
            config.COL_NONNUMERIC,
            "unit",
        ],
    ]
    df[[config.COL_ITEM_CODE, config.COL_ITEM_NAME, "unit"]] = df[
        [config.COL_ITEM_CODE, config.COL_ITEM_NAME, "unit"]
    ].fillna("")
    df[config.COL_NUMERIC] = df[config.COL_NUMERIC].astype(float)

    # Compute basic stats
    map_df = (
        df.groupby([config.COL_ITEM_CODE, config.COL_ITEM_NAME])[config.COL_NUMERIC]
        .agg(["mean", "count"])
        .reset_index()
    )
    map_df = map_df.rename(columns={"count": "numeric_count"})
    # Count the number of numeric values seen
    df["is_nonnumeric"] = ~df[config.COL_NONNUMERIC].isna()
    map_df["nonnumeric_count"] = (
        df.groupby([config.COL_ITEM_CODE, config.COL_ITEM_NAME])["is_nonnumeric"]
        .sum()
        .values
    )
    # Select the most frequently seen unit for reference
    unit_counts = df.groupby(
        [config.COL_ITEM_CODE, config.COL_ITEM_NAME, "unit"]
    ).size()
    unit_counts.name = "count"
    unit_counts = unit_counts.reset_index()
    unit_counts = unit_counts.sort_values("count", ascending=False).drop_duplicates(
        subset=[config.COL_ITEM_CODE, config.COL_ITEM_NAME], keep="first"
    )
    unit_counts = unit_counts[[config.COL_ITEM_CODE, config.COL_ITEM_NAME, "unit"]]
    map_df = pd.merge(
        map_df, unit_counts, on=[config.COL_ITEM_CODE, config.COL_ITEM_NAME], how="left"
    )

    return map_df


def create_jlac10_cleaning_table():
    """Generates a CSV template for optional JLAC10 mapping and saves it for further processing"""
    internal_dir = get_cln_settings("CLN_INTERNAL_DIR")
    optional_jlac10_map_pattern = get_cln_settings("CLN_OPTIONAL_MAP_PTN")
    optional_jlac10_path = optional_jlac10_map_pattern.replace("*", "JLAC10_to_JLAC10")
    csv_path_pattern = os.path.join(internal_dir, config.LAB_RESULT_TABLE_PATTERN)
    output_csv_path = os.path.join(internal_dir, os.path.basename(optional_jlac10_path))

    # Load the standard full-length JLAC10 codes released by JAPIC
    jlac10_to_text = load_mapping_table(
        original_code_system="full_JLAC10", target_code_system="text"
    )
    standard_jlac10s = jlac10_to_text.iloc[:, 0]
    standard_jlac10s_method_agnostic = remove_method_from_jlac10(standard_jlac10s)

    _ = parallel_map_partitions_cln(
        csv_path_pattern=csv_path_pattern,
        function=_create_jlac10_cleaning_table,
        output_csv_path=output_csv_path,
        chunksize=-1,
        single_file=False,
    )

    # Aggregate the temporary tables
    temp_tables = []
    for file in glob.glob(output_csv_path.replace(".csv", "*.csv")):
        table = pd.read_csv(file, dtype=str)
        table[["mean", "numeric_count", "nonnumeric_count"]] = table[
            ["mean", "numeric_count", "nonnumeric_count"]
        ].astype(float)
        table[[config.COL_ITEM_CODE, config.COL_ITEM_NAME, "unit"]] = table[
            [config.COL_ITEM_CODE, config.COL_ITEM_NAME, "unit"]
        ].fillna("")
        temp_tables.append(table)
        os.remove(file)
    map_df = pd.concat(temp_tables)

    # Determine the most frequently seen units
    unit_counts = map_df.groupby(
        [config.COL_ITEM_CODE, config.COL_ITEM_NAME, "unit"]
    ).size()
    unit_counts.name = "count"
    unit_counts = unit_counts.reset_index()
    unit_counts = unit_counts.sort_values("count", ascending=False).drop_duplicates(
        subset=[config.COL_ITEM_CODE, config.COL_ITEM_NAME], keep="first"
    )

    unit_counts = unit_counts[[config.COL_ITEM_CODE, config.COL_ITEM_NAME, "unit"]]
    map_df = map_df.drop("unit", axis=1)
    map_df = pd.merge(
        map_df, unit_counts, on=[config.COL_ITEM_CODE, config.COL_ITEM_NAME]
    )
    # Tally the means and counts
    map_df["mean"] *= map_df["numeric_count"]
    map_df = (
        map_df.groupby([config.COL_ITEM_CODE, config.COL_ITEM_NAME, "unit"])
        .sum()
        .reset_index()
    )
    map_df["mean"] /= map_df["numeric_count"]
    # Create a column to indicate JLAC10 codes listed in the standard JLAC10 codes by MEDIS
    std_mask = map_df[config.COL_ITEM_CODE].isin(standard_jlac10s)
    method_agnostic_jlac10s = remove_method_from_jlac10(map_df[config.COL_ITEM_CODE])
    std_mask_method_agnostic = method_agnostic_jlac10s.isin(
        standard_jlac10s_method_agnostic
    )
    map_df["listed_by_MEDIS"] = "No"
    map_df.loc[std_mask, "listed_by_MEDIS"] = "Yes"
    map_df.loc[std_mask_method_agnostic, "listed_by_MEDIS"] = "Yes (except for method)"
    # Translate the observed codes into texts for reference
    map_df["translated"] = map_jlac10_to_text(
        map_df[config.COL_ITEM_CODE],
        readable=False,
        japanese=True,
    )
    map_df["translated"] = map_df["translated"].mask(
        ~map_df[config.COL_ITEM_CODE].str.contains(config.R_JLAC10_CODE), ""
    )

    # Change data type
    map_df[["numeric_count", "nonnumeric_count"]] = map_df[
        ["numeric_count", "nonnumeric_count"]
    ].astype(int)
    # Round float values
    map_df["mean"] = map_df["mean"].round(2)
    # Add a column for optional operation
    map_df["modified"] = map_df[config.COL_ITEM_CODE].copy()
    map_df["modified"] = map_df["modified"].mask(
        ~map_df["modified"].str.contains(config.R_JLAC10_CODE), ""
    )
    # Assign 'nar' (not-a-record) for comments
    # NOTE: Currently, codes ending with config.LAB_COMMENT_SUFFIXES are ignored at the extraction step
    comment_mask = map_df[config.COL_ITEM_CODE].str.endswith(
        config.LAB_COMMENT_SUFFIXES
    )
    map_df["modified"] = map_df["modified"].mask(comment_mask, config.LAB_NOT_A_RECORD)

    # Add a column for comments
    map_df["comment"] = "comment:"

    # Organize columns and rows
    map_df["total_count"] = map_df["numeric_count"] + map_df["nonnumeric_count"]
    map_df["code_length"] = map_df[config.COL_ITEM_CODE].str.len()
    map_df = map_df.sort_values(
        ["code_length", config.COL_ITEM_CODE], ascending=[False, True]
    )
    map_df = map_df.rename(columns={"unit": "frequent_unit"})
    map_df = map_df[
        [
            config.COL_ITEM_CODE,
            config.COL_ITEM_NAME,
            "modified",
            "listed_by_MEDIS",
            "mean",
            "frequent_unit",
            "numeric_count",
            "nonnumeric_count",
            "translated",
            "comment",
        ]
    ]

    # Save
    map_df = map_df.replace("", None)
    if os.path.exists(optional_jlac10_path):
        archive_file(optional_jlac10_path)
    map_df.to_csv(optional_jlac10_path, header=True, index=False)
