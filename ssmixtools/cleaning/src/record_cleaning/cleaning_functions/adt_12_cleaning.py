"""Module to clean ADT-12"""

import os
import pandas as pd
from ...cleaning_utils import (
    parallel_map_partitions_cln,
    convert_timedelta_to_timestamp,
    assign_unique_record_numbers,
)
from ...cleaning_settings import get_cln_settings
from .....generals import general_config as config


def _clean_adt_12(
    df: pd.DataFrame,
    file_tag: str,
    pid: int,
    timestamp_cols: list,
    final_cols: list,
    dob_map: pd.DataFrame,
) -> pd.DataFrame:
    """Cleans ADT-12 record tables.

    Cleaning steps:

        - Convert timedelta values back to timestamps
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
    """
    # Convert timedelta to timestamp
    df = convert_timedelta_to_timestamp(df, timestamp_cols, dob_map)

    # Drop unnecessary columns and reorder columns.
    df = df[final_cols]

    # Assign unique record IDs
    df = assign_unique_record_numbers(
        df, data_type_tag="adt12", file_tag=file_tag, pid=pid
    )

    return df


def clean_adt_12():
    """Cleans ADT-12 tables.
    See the helper function '_clean_adt_12' for the processing details.
    """
    source_dir = get_cln_settings("CLN_SOURCE_DIR")
    internal_dir = get_cln_settings("CLN_INTERNAL_DIR")
    data_type = "ADT-12"
    timestamp_cols = config.RECORD_TABLE_PARAMS[data_type]["timestamps"]
    final_cols = config.RECORD_TABLE_PARAMS[data_type]["final_columns"]
    file_name_pattern = config.RECORD_TABLE_PARAMS[data_type]["file_name_pattern"]
    csv_path_pattern = os.path.join(source_dir, "**", f"{data_type}_*.csv")
    output_csv_path = os.path.join(internal_dir, file_name_pattern)
    single_file = config.SINGLE_FILE[data_type]

    _ = parallel_map_partitions_cln(
        csv_path_pattern=csv_path_pattern,
        function=_clean_adt_12,
        output_csv_path=output_csv_path,
        chunksize=-1,
        single_file=single_file,
        file_tag_as_arg=True,
        pid_as_arg=True,
        dob_map_as_arg=True,
        timestamp_cols=timestamp_cols,
        final_cols=final_cols,
    )
