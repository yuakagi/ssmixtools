""" Module to inspect ADT-12 tables"""

import pandas as pd
from ...extraction_utils import inspect_csv, inspect_timestamps
from .....generals import general_config as config
from .....generals.general_utils import all_values_to_int


def _inspect_adt_12(df: pd.DataFrame) -> tuple:
    """Helper function to inspect a chunk of ADT-12 record files.

    Args:
        df (pd.DataFrame): Data frame chunk.
    Returns:
        df (pd.DataFrame): DataFrame passed as an argument is directly returned without
            any modifications to it. This is for consistency with 'parallel_map_partitions_ext' function.
        stats (dict): Dictionary that stores inspection results. This is the main product of this function.
    """
    data_type = "ADT-12"
    # Initialize a dictionary to store analytics
    stats = {}

    # Count records
    n_records = df.count().to_dict()
    n_records = all_values_to_int(n_records)
    stats["number of records"] = n_records

    # Inspect timestamp columns
    stats["timestamps"] = inspect_timestamps(
        df,
        timestamp_cols=config.RECORD_TABLE_PARAMS[data_type]["timestamps"],
    )

    return df, stats


def inspect_adt_12():
    """Inspects all ADT-12 records and save the inspection results as a JSON file."""
    # Inspect
    data_type = "ADT-12"
    inspect_csv(data_type=data_type, function=_inspect_adt_12, chunksize=-1)
