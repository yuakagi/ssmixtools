"Module to clean demographics"

import os
import pandas as pd
from ...cleaning_utils import parallel_map_partitions_cln, assign_unique_record_numbers
from ...cleaning_settings import get_cln_settings
from .....generals import general_config as config


def _clean_demographics(
    df: pd.DataFrame, file_tag: str, pid: int, timestamp_cols: list, final_cols: list
) -> pd.DataFrame:
    """Cleans demographic record tables.

    Note that the dataframe chunk that is passed to this function comes from the table extracted as 'patient_metadata'.
    The original metadata table contains many non-demographic data such as number of visits.
    This function selectively picks up columns.

    Cleaning steps:

        - Validate patient sex expressions, and drop irregular sex values.
        - Format timestamps
        - Drop unnecessary columns
        - Assign unique record IDs

    Args:
        df (pd.DataFrame): Dataframe to be cleaned.
        file_tag (str): File identity tag, passed from 'parallel_map_partitions_cln'
        pid (int): Child process ID
        timestamp_cols (list): Values in the columns in this list are converted to timestamps.
        final_cols (list): List of column names included in the final product table.
            Columns not in this list are all dropped.
    Returns:
        df (pd.DataFrame): Cleaned dataframe.
    """
    # Clean patient sex column
    standard_sex_mask = df[config.COL_SEX].fillna("").isin(config.SEX_TYPES)
    df[config.COL_SEX] = df[config.COL_SEX].mask(~standard_sex_mask, "")

    # Format timestamps
    for col in timestamp_cols:
        df[col] = pd.to_datetime(df[col])

    # Drop unnecessary columns and reorder columns.
    df = df[final_cols]

    # Assign unique record IDs
    df = assign_unique_record_numbers(
        df, data_type_tag="dmg", file_tag=file_tag, pid=pid
    )

    return df


def clean_demographics():
    """Creates demographic data tables.
    See the helper function '_clean_demographics' for the processing details.
    """
    source_dir = get_cln_settings("CLN_SOURCE_DIR")
    internal_dir = get_cln_settings("CLN_INTERNAL_DIR")
    data_type = "demographics"
    timestamp_cols = config.RECORD_TABLE_PARAMS[data_type]["timestamps"]
    final_cols = config.RECORD_TABLE_PARAMS[data_type]["final_columns"]
    file_name_pattern = config.RECORD_TABLE_PARAMS[data_type]["file_name_pattern"]
    csv_path_pattern = os.path.join(source_dir, "**", config.METADATA_TABLE_PATTERN)
    output_csv_path = os.path.join(internal_dir, file_name_pattern)
    single_file = config.SINGLE_FILE[data_type]

    _ = parallel_map_partitions_cln(
        csv_path_pattern=csv_path_pattern,
        function=_clean_demographics,
        output_csv_path=output_csv_path,
        chunksize=-1,
        single_file=single_file,
        file_tag_as_arg=True,
        pid_as_arg=True,
        timestamp_cols=timestamp_cols,
        final_cols=final_cols,
    )
