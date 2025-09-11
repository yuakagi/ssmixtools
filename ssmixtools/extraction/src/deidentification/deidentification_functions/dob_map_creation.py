"""Module for creating a table to map deidentified patient IDs to dates of birth"""

import pandas as pd
from ...extraction_settings import get_ext_settings
from ...extraction_utils import parallel_map_partitions_ext
from .....generals import general_config as config
from .....generals.general_utils import tally_stats


def _create_dob_map(df):
    """Helper function for 'create_dob_map'"""
    analytics = {}

    # Load deidentified ID map
    id_map_path = get_ext_settings("EXT_ID_MAP_PTH")
    patient_id_map = pd.read_csv(
        id_map_path,
        dtype=str,
        na_values=config.NA_VALUES,
    )

    # Deidentify patient IDs, and drop patients who were not selected (dropping is done by 'inner' join)
    df = df.merge(patient_id_map, how="inner", on=config.COL_PID)
    df = df.drop(config.COL_PID, axis=1)
    df = df.rename(columns={config.COL_DID: config.COL_PID})

    # Ensure that data are "YYYYMMDD".
    # Unconvertable, irregular, missing values should have been excluded by 'patient selection' process.
    df[config.COL_DOB] = df[config.COL_DOB].str.strip().str.slice(0, 8)

    # Save DOB map as a dictionary.
    dob_df = df[[config.COL_PID, config.COL_DOB]].copy()
    dob_dict = dob_df.to_dict(orient="list")
    analytics["dob_dict"] = dob_dict

    # Drop DOB column and save the rest as the cleaned metadata (containing no identifiable patient data).
    df = df.drop(config.COL_DOB, axis=1)

    # Record the length of the table.
    analytics["number_of_DOB_records"] = len(df)

    return df, analytics


def create_dob_map() -> dict:
    """Creates a table that contains pairs of deidentified patient ID and DOB.
    Returns:
        process_analytics: Dictionary contains analytics of this process.
    """
    csv_path = get_ext_settings("EXT_ALL_METADATA_PTH")
    deidentified_metadata_path = get_ext_settings("EXT_DEIDENTIFIED_METADATA_PTH")
    dob_map_path = get_ext_settings("EXT_DOB_MAP_PTH")

    # Process, and save the deidentified patient metadata, which is a by-product of this process.
    stats_list = parallel_map_partitions_ext(
        csv_path=csv_path,
        function=_create_dob_map,
        output_csv_path=deidentified_metadata_path,
        single_file=True,
        chunksize=-1,
    )

    # Tally analytics.
    process_analytics = tally_stats(stats_list)

    # Create patient DOB mapping table and save it as a csv.
    dob_dict = process_analytics["dob_dict"]
    dob_map = pd.DataFrame(dob_dict)
    dob_map.to_csv(dob_map_path, mode="w", header=True, index=False)
    del process_analytics["dob_dict"]

    return process_analytics
