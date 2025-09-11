"""Module to clean ADT-52"""

import os
import pandas as pd
from ...cleaning_utils import (
    parallel_map_partitions_cln,
    convert_timedelta_to_timestamp,
    assign_unique_record_numbers,
)
from ...cleaning_settings import get_cln_settings
from .....generals import general_config as config


def _clean_adt_52(
    df: pd.DataFrame,
    file_tag: str,
    pid: int,
    timestamp_cols: list,
    final_cols: list,
    dob_map: pd.DataFrame,
) -> pd.DataFrame:
    """Cleans ADT-52 record tables.

    Cleaning steps:

        - Convert timedelta values back to timestamps
        - Validate patient discharge disposition codes, and drop irregular ones.
            (using the user-defined Table 0112 of HL7 version 2.5)
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

    # Clean patient discharge disposition codes.
    standardized_disposition_mask = (
        df["disposition"]
        .fillna("")
        .str.contains(config.R_USER_DEFINED_TABLE_0112_CODE, na=False)
    )
    df["disposition"] = df["disposition"].mask(~standardized_disposition_mask, "")

    # Map disposition codes to binary indicators (survived:1 or died:0)
    df["disposition"] = df["disposition"].replace(
        config.DISCHARGE_STATUS_MAP, regex=True
    )

    # Drop unnecessary columns and reorder columns.
    df = df[final_cols]

    # Assign unique record IDs
    df = assign_unique_record_numbers(
        df, data_type_tag="adt52", file_tag=file_tag, pid=pid
    )

    return df


def clean_adt_52():
    """Cleans ADT-52 tables.
    See the helper function '_clean_adt_52' for the processing details.
    """
    source_dir = get_cln_settings("CLN_SOURCE_DIR")
    internal_dir = get_cln_settings("CLN_INTERNAL_DIR")
    data_type = "ADT-52"
    timestamp_cols = config.RECORD_TABLE_PARAMS[data_type]["timestamps"]
    final_cols = config.RECORD_TABLE_PARAMS[data_type]["final_columns"]
    file_name_pattern = config.RECORD_TABLE_PARAMS[data_type]["file_name_pattern"]
    csv_path_pattern = os.path.join(source_dir, "**", f"{data_type}_*.csv")
    output_csv_path = os.path.join(internal_dir, file_name_pattern)
    single_file = config.SINGLE_FILE[data_type]

    _ = parallel_map_partitions_cln(
        csv_path_pattern=csv_path_pattern,
        function=_clean_adt_52,
        output_csv_path=output_csv_path,
        chunksize=-1,
        single_file=single_file,
        file_tag_as_arg=True,
        pid_as_arg=True,
        dob_map_as_arg=True,
        timestamp_cols=timestamp_cols,
        final_cols=final_cols,
    )
