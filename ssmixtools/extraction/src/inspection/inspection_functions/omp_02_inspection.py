""" Module to inspect OMP-02 tables"""

import pandas as pd
from ...extraction_utils import (
    inspect_csv,
    inspect_timestamps,
    count_unique_values,
)
from .....generals import general_config as config
from .....generals.general_utils import all_values_to_int


def _inspect_omp_02(df: pd.DataFrame) -> tuple:
    """Helper function that inspects a chunk of OMP-02 record files.

    Args:
        df (pd.DataFrame): Data frame chunk.
    Returns:
        df (pd.DataFrame): DataFrame passed as an argument is directly returned without
            any modifications to it. This is for consistency with 'parallel_map_partitions_ext' function.
        stats (dict): Dictionary that stores inspection results. This is the main product of this function.
    """
    data_type = "OMP-02"

    # Initialize a dictionary to store analytics
    stats = {}

    # Define masks
    hot_named = df["primary_component_coding_system"].str.contains(
        config.R_HOT, na=False
    )
    hot_code_pattern = df["primary_component_code"].str.contains(
        config.R_HOT_CODE, na=False
    )
    yj_myak_named = df["secondary_component_coding_system"].str.contains(
        config.R_YJ_OR_MYAK, na=False
    )
    yj_myak_code_pattern = df["secondary_component_code"].str.contains(
        config.R_YJ_OR_MYAK_CODE, na=False
    )
    missing_primary_code = df["primary_component_code"].isnull()
    missing_primary_system = df["primary_component_coding_system"].isnull()
    missing_secondary_code = df["secondary_component_code"].isnull()
    missing_secondary_system = df["secondary_component_coding_system"].isnull()

    # Create a mask dictionary for just counting records
    counting_masks = {
        "either HOT or YJ/MYAK available": (hot_code_pattern & hot_named)
        | (yj_myak_code_pattern & yj_myak_named),
        "both HOT and YJ/MYAK available": hot_code_pattern
        & hot_named
        & yj_myak_code_pattern
        & yj_myak_named,
        "only HOT available": hot_code_pattern
        & hot_named
        & ~(yj_myak_code_pattern & yj_myak_named),
        "only YJ/MYAK available": ~(hot_code_pattern & hot_named)
        & yj_myak_code_pattern
        & yj_myak_named,
        "primary component code exists but HOT not named": ~(missing_primary_code)
        & ~(hot_named),
        "secondary component code exists but YJ/MYAK not named": ~(
            missing_secondary_code
        )
        & ~(yj_myak_named),
        "component in plain text available but both primary and secondary codes missing": missing_primary_code
        & missing_secondary_code,
    }

    # Create a mask dictionary for unique value counts
    counting_params = {
        "neither HOT nor YJ/MYAK available": {
            "mask": ~(
                (hot_code_pattern & hot_named) | (yj_myak_code_pattern & yj_myak_named)
            ),
            "value_cols": [
                "primary_component_code",
                "primary_component_text",
            ],
        },
        "HOT named but irregular HOT code": {
            "mask": ~(hot_code_pattern) & hot_named,
            "value_cols": [
                "primary_component_code",
                "primary_component_text",
            ],
        },
        "YJ/MYAK named but irregular YJ/MYAK code": {
            "mask": ~(yj_myak_code_pattern) & yj_myak_named,
            "value_cols": [
                "secondary_component_code",
                "secondary_component_text",
            ],
        },
        "code is HOT-like but primary coding system missing": {
            "mask": hot_code_pattern & missing_primary_system,
            "value_cols": [
                "primary_component_code",
                "primary_component_text",
            ],
        },
        "code is YJ/MYAK-like but secondary coding system missing": {
            "mask": yj_myak_code_pattern & missing_secondary_system,
            "value_cols": [
                "secondary_component_code",
                "secondary_component_text",
            ],
        },
    }

    # Count records
    n_records = df.count().to_dict()
    n_records = all_values_to_int(n_records)
    stats["number of records"] = n_records

    # Counting timestamp columns
    stats["timestamps"] = inspect_timestamps(
        df,
        timestamp_cols=config.RECORD_TABLE_PARAMS[data_type]["timestamps"],
    )

    # Count values with respect to standardization
    stats["standardization"] = {}
    for key, val in counting_masks.items():
        stats["standardization"][key] = int(val.sum())

    # Diagnostic systems
    primary_system_counts = (
        df["primary_component_coding_system"].value_counts().to_dict()
    )
    primary_system_counts = all_values_to_int(primary_system_counts)

    secondary_system_counts = (
        df["secondary_component_coding_system"].value_counts().to_dict()
    )
    secondary_system_counts = all_values_to_int(secondary_system_counts)

    stats["component code systems"] = {}
    stats["component code systems"]["primary"] = primary_system_counts
    stats["component code systems"]["secondary"] = secondary_system_counts

    # Collect unique values seen in irregular records
    stats["unique values"] = {}

    unique_counts, total_irregular_counts = count_unique_values(df, counting_params)
    stats["unique values"] = unique_counts
    stats["standardization"] = {**stats["standardization"], **total_irregular_counts}

    return df, stats


def inspect_omp_02():
    """Inspects all OMP-02 record CSV files and save the inspection results as a JSON file."""
    # Define variables
    data_type = "OMP-02"
    inspect_csv(data_type=data_type, function=_inspect_omp_02, chunksize=-1)
