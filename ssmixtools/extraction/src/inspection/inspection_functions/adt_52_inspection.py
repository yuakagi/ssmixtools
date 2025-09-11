""" Module to inspect ADT-52 tables"""

import pandas as pd
from ...extraction_utils import inspect_csv, inspect_timestamps, count_unique_values
from .....generals import general_config as config
from .....generals.general_utils import all_values_to_int


def _inspect_adt_52(df: pd.DataFrame) -> tuple:
    """Helper function to inspect a chunk of ADT-52 record files.

    Args:
        df (pd.DataFrame): Data frame chunk.
    Returns:
        df (pd.DataFrame): DataFrame passed as an argument is directly returned without
            any modifications to it. This is for consistency with 'parallel_map_partitions_ext' function.
        stats (dict): Dictionary that stores inspection results. This is the main product of this function.
    """
    data_type = "ADT-52"

    # Initialize a dictionary to store analytics
    stats = {}

    # Define masks
    udt_0112_pattern = df["disposition"].str.contains(
        config.R_USER_DEFINED_TABLE_0112_CODE, na=False
    )
    missing_udt_0112 = df["disposition"].isnull()

    # Count records
    n_records = df.count().to_dict()
    n_records = all_values_to_int(n_records)
    stats["number of records"] = n_records

    # Inspect timestamp columns
    stats["timestamps"] = inspect_timestamps(
        df,
        timestamp_cols=config.RECORD_TABLE_PARAMS[data_type]["timestamps"],
    )
    # Create a param dict for irregular value counts
    counting_params = {
        "UDT-0112 available": {
            "mask": udt_0112_pattern & ~(missing_udt_0112),
            "value_cols": [
                "disposition",
            ],
        },
        "irregular UDT-0112": {
            "mask": ~(udt_0112_pattern) & ~(missing_udt_0112),
            "value_cols": [
                "disposition",
            ],
        },
    }
    # Collect unique values seen in irregular records
    unique_counts, total_irregular_counts = count_unique_values(df, counting_params)
    stats["irregular values"] = total_irregular_counts
    stats["unique values"] = unique_counts

    return df, stats


def inspect_adt_52():
    """Inspects all ADT-52 record CSV files and save the inspection results as a JSON file."""
    # Define variables
    data_type = "ADT-52"
    inspect_csv(data_type=data_type, function=_inspect_adt_52, chunksize=-1)
