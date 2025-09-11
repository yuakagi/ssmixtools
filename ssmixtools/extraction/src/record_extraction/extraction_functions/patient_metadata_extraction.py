"""Module to extract patient metadata"""

import os
import re
from pandas.core.series import Series
from ...extraction_settings import get_ext_settings
from ...extraction_utils import (
    normalize_line,
    patient_id_to_path,
    extract_using_csv,
    extract_element,
)
from .....generals import general_config as config


def _extract_patient_metadata(task: Series) -> list[list[str]]:
    """Parses a patient's directory tree to extract metadata.

    A file is opened only if the 'condition flag' is 1, indicating the file is the latest version.
    Args:
        task (Series): Task passed by the '_extract_in_parallel' function.
    Returns:
        rows (list): List that stores patient metadata.
            This is a list with a single element of a list for consistency.
            The child list is the main data.
                List elements:
                [patient_id, sex, dob, n_dates, first_date, last_date, n_admissions
                    patient_id (str): Patient ID
                    sex (str): Patient's gander
                    dob (str): Date of birth
                    n_dates (str): Number of visits of the patient
                    first_date (str): First visiting date of the patient
                    last_date (str): Last visiting date of the patient
                    n_admissions (str): Number of admissions
            Missing elements are filled with empty strings.
    """
    # Initialize variables
    patient_id = task[0]
    patient_path = patient_id_to_path(patient_id)
    encoding = get_ext_settings("HL7_ENCODING")
    dob = ""
    sex = ""
    first_date = ""
    last_date = ""
    # Collect sex and DOB
    adt_00_path = os.path.join(patient_path, "-", "ADT-00")
    if os.path.exists(adt_00_path):
        adt_00_files = []
        for file in os.listdir(adt_00_path):
            if file.strip().endswith("1"):
                adt_00_files.append(file)
        if adt_00_files:
            adt_00_file_path = os.path.join(adt_00_path, adt_00_files[0])
            # Extract PID segment
            with open(adt_00_file_path, encoding=encoding) as f:
                for line in f:
                    line = normalize_line(line)
                    if line.startswith("PID"):
                        pid = line.split("|")
                        dob = extract_element(pid, 7)
                        sex = extract_element(pid, 8)
                        break

    # Collect metadata about dates
    dates = []
    for date in os.listdir(patient_path):
        date = date.strip()
        if re.fullmatch(config.R_YYYYMMDD, date.strip()):
            dates.append(date)
    n_dates = len(dates)

    # Collect admission history
    n_admissions = 0
    if n_dates > 0:
        for date in dates:
            adt_22_path = os.path.join(patient_path, date, "ADT-22")
            if os.path.exists(adt_22_path):
                adt_22_files = []
                for file in os.listdir(adt_22_path):
                    if file.strip().endswith("1"):
                        adt_22_files.append(file)
                for adt_22_file in adt_22_files:
                    adt_22_file_path = os.path.join(adt_22_path, adt_22_file)
                    with open(adt_22_file_path, encoding=encoding) as f:
                        line = f.readline().strip()
                        msh = (
                            line.split("|") if line.startswith("MSH") else []
                        )  # MSH segment
                        message_type = extract_element(
                            msh, 8
                        ).strip()  # Caution !! In MSH, the index of MSH-9 is 8. (Because MSH-1 is a separator '|'.)
                        n_admissions += 1 if message_type.startswith("ADT^A01") else 0

    # Extract the first and the last visiting dates
    if n_dates > 0:
        int_dates = []
        for d in dates:
            try:
                int_d = int(d)
                int_dates.append(int_d)
            except ValueError:
                pass
        int_dates = sorted(int_dates)
        first_date = str(int_dates[0])
        last_date = str(int_dates[-1])

    rows = [[patient_id, sex, dob, n_dates, first_date, last_date, n_admissions]]

    return rows


def extract_patient_metadata() -> dict:
    """Extracts metadata of a patient"""
    # Perform extraction
    all_ids_path = get_ext_settings("EXT_ALL_IDS_PTH")
    all_metadata_path = get_ext_settings("EXT_ALL_METADATA_PTH")
    process_analytics = extract_using_csv(
        loaded_csv_path=all_ids_path,
        output_csv_path=all_metadata_path,
        function=_extract_patient_metadata,
        output_csv_col_names=config.META_TABLE_PARAMS["metadata"]["all"],
        chunksize=config.CHUNKSIZES["patient_metadata_extraction"],
        single_file=True,
    )
    return process_analytics
