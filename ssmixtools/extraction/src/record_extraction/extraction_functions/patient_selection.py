"""Patient selection"""

import warnings
import numpy as np
import pandas as pd
from ...extraction_settings import get_ext_settings
from ...extraction_utils import parallel_map_partitions_ext
from .....generals import general_config as config
from .....generals.general_utils import tally_stats, all_values_to_int


warnings.filterwarnings("ignore")


def _select_patients(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Selects patient IDs using patient metadata.

    Patient filtering details:
        - Default filtering:
            1) Exclude patients without valid DOB records
            2) Exclude patients without gender records
        - Optional filtering:
            1) Exclude patients with number of visit dates fewer than a given threshold ('MIN_ENCOUNTERS')
            2) Exclude patients whose last visit date is before a given threshold ('MIN_VISIT_DATE')
            3) Exclude patients whose first visit date is after a given threshold ('MAX_VISIT_DATE')

    Args:
        df (pd.DataFrame): Chunk of a CSV file read by pd.read_csv.
    Returns:
        df (pd.DataFrame): Table containing the list of the selected patients.
        analytics (dictionary): Dictionary that contain the process analytics of the patient selection.
    """
    # Initialize a record
    analytics = {}
    # Count the total number of patients
    total_patients = len(df)
    analytics["total_unique_patient_IDs"] = total_patients

    # *****************************************************************************
    # * Default filtering *********************************************************
    # *****************************************************************************
    # * In this section, these patients are excluded from record extraction:
    # *     - Patients without valid DOB records
    # *     - Patients without records of their sex
    # *****************************************************************************

    # Filtering missing DOB
    missing_dob = df[config.COL_DOB].isnull()

    # Check irregular DOB expression patterns both with convesion to datetime object and a regular expression for robustness.
    irregular_dob_by_regex = ~(
        df[config.COL_DOB].str.contains(config.R_ALL_TIME_PATTERNS, na=True)
    )
    dobs_dt = pd.to_datetime(
        df[config.COL_DOB].str.slice(0, 8), format="%Y%m%d", errors="coerce"
    )
    irregular_dob_by_conversion_error = dobs_dt.isnull() & ~(missing_dob)
    irregular_dob = irregular_dob_by_regex | irregular_dob_by_conversion_error

    # Filter for sex
    missing_sex = df[config.COL_SEX].isnull()  # Patients with missing sex are excluded.

    # Create an exclusion mask
    default_optional_exclusion_mask = missing_dob | irregular_dob | missing_sex

    # Write to analytics
    analytics["missing DOB"] = int(missing_dob.sum())
    analytics["irregular DOB"] = {
        "total": int(irregular_dob.sum()),
        "unique values": all_values_to_int(
            df.loc[irregular_dob, config.COL_DOB].value_counts().to_dict()
        ),
    }
    analytics["missing sex"] = int(missing_sex.sum())

    # Exclude patients
    df = df[~default_optional_exclusion_mask]

    # *****************************************************************************
    # * Optional filtering ********************************************************
    # *****************************************************************************
    # * In this section, optional filterings are applied.
    # *****************************************************************************

    # Check datatypes
    for col in [config.COL_LAST_VISIT_DATE, config.COL_FIRST_VISIT_DATE]:
        df[col] = pd.to_datetime(df[col])
    df[config.COL_N_ENCOUNTERS] = df[config.COL_N_ENCOUNTERS].astype(float).astype(int)

    # Initialize mask
    optional_exclusion_mask = pd.Series(np.full(len(df), False, dtype=bool))
    optional_exclusion_mask.index = df.index

    # Load params
    min_encounters = get_ext_settings("MIN_ENCOUNTERS")
    extraction_period_start = get_ext_settings("EXT_PERIOD_START")
    extraction_period_end = get_ext_settings("EXT_PERIOD_END")

    # Adding optional masks
    min_options = [
        [
            min_encounters,
            config.COL_N_ENCOUNTERS,
            f"encounters fewer than {min_encounters}",
        ],
        [
            extraction_period_start,
            config.COL_LAST_VISIT_DATE,
            f"latest visiting dates before {extraction_period_start}",
        ],
    ]
    max_options = [
        [
            extraction_period_end,
            config.COL_FIRST_VISIT_DATE,
            f"oldest visiting dates after {extraction_period_end}",
        ],
    ]

    for limit, col, description in min_options:
        if limit is not None:
            mask = df[col] <= limit
            # Update optional_exclusion_mask
            optional_exclusion_mask = optional_exclusion_mask | mask
            # Save selection process
            analytics[description] = int(mask.sum())

    for limit, col, description in max_options:
        if limit is not None:
            mask = df[col] >= limit
            # Update optional_exclusion_mask
            optional_exclusion_mask = optional_exclusion_mask | mask
            # Save selection process
            analytics[description] = int(mask.sum())

    # Finalize dataframe
    df = df.loc[~optional_exclusion_mask, config.COL_PID]

    # Write to analytics
    analytics["included_patients"] = len(df)

    # Save the list of selected patient as a CSV file
    return df, analytics


def select_patients() -> dict:
    """
    Perform patient ID selection.
    """
    # Execute the helper function
    selected_ids_path = get_ext_settings("EXT_SELECTED_IDS_PTH")
    all_metadata_path = get_ext_settings("EXT_ALL_METADATA_PTH")
    list_of_analytics = parallel_map_partitions_ext(
        csv_path=all_metadata_path,
        output_csv_path=selected_ids_path,
        chunksize=config.CHUNKSIZES["patient_selection"],
        function=_select_patients,
        single_file=True,
    )

    # Tally recods.
    process_analytics = tally_stats(list_of_analytics)

    return process_analytics
