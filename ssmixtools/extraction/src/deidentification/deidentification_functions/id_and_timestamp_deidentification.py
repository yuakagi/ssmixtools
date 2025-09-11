"""Module to deidentify patient IDs and timestamps"""

import os
import warnings
import datetime
import pandas as pd
from ...extraction_settings import get_ext_settings
from ...extraction_utils import parallel_map_partitions_ext, all_values_to_int
from .....generals import general_config as config
from .....generals.general_utils import tally_stats


warnings.filterwarnings("ignore")


def _deidentify_timestamp(df, timestamp_cols):
    """Deidentifies timestamps.

    This function performs deidentification step-by-step:
        -1. Validate timestamp expressions using regular expressions and create masks for the dataframe.
            Irregular timestamps are counted and recorded in a dictionary, and dropped eventually.
        -2. Pad timestamps with zeros to ensure that all timestamps have the same length of 20 (to the level of microseconds).
            The number of zeros padded to the level of 'milliseconds' (not MICROseconds) are recorded as microsecond in order to inform users which zeros are
            actually recorded values and which are padded. For example, if the raw extracted timestamp is '201305160000',
            then the timestamp is '20130516000000000005' after padding.
            Because millisecond is the smallest unit used in SS-MIX2, this modification of timestamps does not affect the actual timestamps
            stored.
        -3. Handle hours expressed with integers over 23. If recorded timestamps contain numbers from 24 to 47,
            24 is extracted and then a timedelta of 'one day' is added to the timestamp.
            Hours over 47 are treated as irregular, and thus invalid timestamps.
        -4. Drop missing and irregular timestamps. These values are counted and recorded in a dictionary.
        -5. Converting timestamps into timedelta objects by subtracting DOB from timestamps.
    Args:
        df (pd.DataFrame): Chunk of a csv file.
        timestamp_cols (list): List of columns. Timestamps in columns in this list are subject to deidentification.
    Returns:
        df (pd.DataFrame): Deidentified data frame indexed by deidentified patient IDs.
        irregular_timestamps (dict): Dictionary contains stats about timestamps found during this deidentification process.
    """
    # Create a dictionary to store irregular unconvertable values and their counts
    irregular_timestamps = {}

    # Convert DOB to datetime
    # Irregular DOB patterns should have been excluded by 'patient selection' process.
    df[config.COL_DOB] = pd.to_datetime(df[config.COL_DOB], format="%Y%m%d")

    # *********************************************************************************************************
    # Step1: Timestamp validation and creating masks***********************************************************
    # *********************************************************************************************************
    for col in timestamp_cols:
        # Define masks
        match_YYYYMMDD = df[col].str.contains(config.R_YYYYMMDD, na=False)
        match_YYYYMMDDHHMM = df[col].str.contains(config.R_YYYYMMDDHHMM, na=False)
        match_YYYYMMDDHHMMSS = df[col].str.contains(config.R_YYYYMMDDHHMMSS, na=False)
        match_YYYYMMDDHHMMSSFFF = df[col].str.contains(
            config.R_YYYYMMDDHHMMSSFFF, na=False
        )
        match_YYYYMMDDHHMMSSFFF_dot = df[col].str.contains(
            config.R_YYYYMMDDHHMMSSFFF_DOT, na=False
        )
        hours_over_23 = df[col].str.contains(config.R_HOURS_24_TO_47, na=False)
        missing_timestamp = df[col].isnull()
        padding_masks = [
            match_YYYYMMDD,
            match_YYYYMMDDHHMM,
            match_YYYYMMDDHHMMSS,
            match_YYYYMMDDHHMMSSFFF,
            match_YYYYMMDDHHMMSSFFF_dot,
        ]

        # *********************************************************************************************************
        # Step2: Padding timestamps *******************************************************************************
        # *********************************************************************************************************
        # Remove dot
        df.loc[match_YYYYMMDDHHMMSSFFF_dot, col] = df.loc[
            match_YYYYMMDDHHMMSSFFF_dot, col
        ].str.replace(".", "", regex=False)

        # Pad timestamps to the length of 20 (to the level of microsecond).
        padded_lengths = [9, 5, 3, 0, 0]
        df[col] = df[col].str.ljust(19, "0")
        for mask, padded_length in zip(padding_masks, padded_lengths):
            # Add the number of padded zeros as a microsecond value
            last_value = (mask * padded_length).astype(str)
            last_value = last_value.mask(last_value == "0", "")
            df[col] = df[col] + last_value

        # *********************************************************************************************************
        # Step3: Handling timestamps over 23 **********************************************************************
        # *********************************************************************************************************
        timestamps = df[col].str.slice(0, 10)
        timestamps = timestamps.fillna("0").astype(int)
        subs = hours_over_23 * 24
        timestamps = timestamps - subs
        timestamps = timestamps.astype(str)
        timestamps = timestamps + df[col].str.slice(10, 20)
        timestamps = timestamps.mask(timestamps == "0", "")
        timestamps = pd.to_datetime(
            timestamps, format="%Y%m%d%H%M%S%f", errors="coerce"
        )
        added_one_day = hours_over_23 * datetime.timedelta(days=1)
        timestamps = timestamps + added_one_day

        # *********************************************************************************************************
        # Step4: Drop missing and irregular timestamps ************************************************************
        # *********************************************************************************************************
        unconvertables = timestamps.isnull() & ~(missing_timestamp)
        irregular_timestamps[col] = all_values_to_int(
            df[unconvertables][col].value_counts().to_dict()
        )

        # *********************************************************************************************************
        # Step5: Subtract DOB from timestamps *********************************************************************
        # *********************************************************************************************************
        df[col] = (timestamps - df[config.COL_DOB]).astype(str)

    return irregular_timestamps


def _deidentify_id_and_timestamp(
    df: pd.DataFrame,
    timestamp_cols: list[str],
    patient_id_map: pd.DataFrame,
    patient_dob_map: pd.DataFrame,
) -> tuple:
    """Deidentifies both patient ID and timestamps in a table.

    Args:
        df (pd.DataFrame): Chunk of a csv file.
        timestamp_cols (list): List of columns. Timestamps in columns in this list are subject to deidentification.
        patient_id_map (pd.DataFrame): Mapping table to deidentify patient IDs.
        patient_dob_map (pd.DataFrame): Mapping table to deidentify timestamps.
    Returns:
        df (pd.DataFrame): Deidentified data frame indexed by deidentified patient IDs.
        irregular_timestamps (dict): Dictionary contains stats of timestamps found during this deidentification process.
    """
    # Save the original column order
    original_cols = df.columns
    # Add 'deidentified patient ID'.
    df = pd.merge(left=df, right=patient_id_map, how="left", on=config.COL_PID)
    df = df.drop(config.COL_PID, axis=1)
    # NOTE: Column 'patient ID' is the deidentified patient ID thereafter
    df = df.rename(columns={config.COL_DID: config.COL_PID})
    # Add 'date of birth'
    # NOTE: COL_PID in both df and patient_dob_map are deidentified already.
    df = pd.merge(left=df, right=patient_dob_map, how="left", on=config.COL_PID)
    # Deidentify timestamps
    irregular_timestamps = _deidentify_timestamp(df, timestamp_cols=timestamp_cols)
    # Drop DOB
    df = df.drop(config.COL_DOB, axis=1)
    # Sort columns
    df = df[original_cols]

    return df, irregular_timestamps


def deidentify_id_and_timestamp(
    data_type: str, timestamp_cols: list[str], single_file: bool = False
) -> dict:
    """deidentifies patient IDs and timestamps.
    IDs are replaced by randomly assigned. numbers concatenated with an identity tag of the storage.
    Timestamps are subtracted by DOB.

    Args:
        data_type (str): SS-MIX2 data type.
        timestamp_cols (list): List of columns contain timestamps.
        single_file (bool, optional): If False, processed tables are saved separately by child processes.
    Returns:
        process_analytics: Dictionary contains analytics of this process.
    """
    # Define variables
    raw_table_dir = get_ext_settings("EXT_RAW_TABLE_DIR")
    id_map_path = get_ext_settings("EXT_ID_MAP_PTH")
    dob_map_path = get_ext_settings("EXT_DOB_MAP_PTH")
    deidentified_tables_dir = get_ext_settings("EXT_DEIDENTIFIED_TABLES_DIR")
    process_analytics = {}
    csv_name = config.TIME_SERIES_DATA_PATTERN.replace("*", f"{data_type}_*")
    csv_path_pattern = os.path.join(raw_table_dir, csv_name)
    output_csv_path = os.path.join(deidentified_tables_dir, csv_name)

    # Load mapping tables
    patient_id_map = pd.read_csv(id_map_path, dtype=str, na_values=config.NA_VALUES)
    patient_dob_map = pd.read_csv(
        dob_map_path,
        dtype=str,
        na_values=config.NA_VALUES,
    )

    # Map the custom function.
    stats_list = parallel_map_partitions_ext(
        csv_path=csv_path_pattern,
        function=_deidentify_id_and_timestamp,
        single_file=single_file,
        chunksize=-1,
        index=False,
        output_csv_path=output_csv_path,
        timestamp_cols=timestamp_cols,
        patient_id_map=patient_id_map,
        patient_dob_map=patient_dob_map,
    )

    # Tally stats.
    irregular_timestamps = tally_stats(stats_list)
    process_analytics["irregular_timestamps"] = irregular_timestamps

    return process_analytics
