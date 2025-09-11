"""Module to extract PPR-01 records (diagnosis records)"""

import re
from pandas.core.series import Series
from ...extraction_utils import (
    hl7_to_list,
    extract_element,
    get_code_from_segment,
    extract_using_data_type,
)
from .....generals import general_config as config


def _parse_ppr_01(task: Series) -> list[list[str]]:
    """Opens an PPR-01 file and collects diagnosis records.

    A file is opened only if the 'condition flag' is 1, indicating the file is the latest version.
    Args:
        task (Series): Task passed by the '_extract_in_parallel' function.
            Its first element is patient ID, the second is the file condition flag
            (which can be either 0, 1, or 2), and the last one is the path to the file.
    Returns:
        rows (list): List that stores diagnosis records.
            Each sublist in the list is a diagnosis.
                List elements:
                    patient_id (str): Patient ID
                    primary_dx_system (str): Primary coding system for the diagnosis (MDCDX2 expected)
                    primary_dx_code (str): Primary code for the diagnosis
                    primary_dx_text (str): Primary name of the diagnosis
                    secondary_dx_system (str): Secondary coding system for the diagnosis (ICD-10 expected)
                    secondary_dx_code (str): Secondary code for the diagnosis
                    diagnosis_type (str): Type of the diagnosis (i.e., on admission, pre-operative, post-operative, etc.).
                    provisional (str): Binary flag for provisional diagnosis (1 or 0)
                    time_of_update (str): Latest time the record was updated
                    date_of_onset (str): Onset of the diagnosis
                    date_of_diagnosis (str): Time of diagnosis
            Missing elements are filled with empty strings.
    """
    rows = []
    if task[1] == "1":
        patient_id = task[0]
        file_path = task[-1]
        segments_parsed = ["PRB"]
        prbs = hl7_to_list(file_path, segments_parsed)

        # Loop through PRB segments
        for prb in prbs:
            if prb[1] == "AD":
                # Collect primary diagnosis code, which is supposed to be encoded by MDCDX2 (病名管理番号).
                (
                    primary_dx_code,
                    primary_dx_text,
                    primary_dx_system,
                    _,
                ) = get_code_from_segment(prb, 3, code_system_pattern=config.R_MDCDX2)

                # Collect secondary, optional diagnosis code, which is supposed to be encoded by ICD-10.
                (
                    secondary_dx_code,
                    _,
                    secondary_dx_system,
                    code_system_matched,
                ) = get_code_from_segment(prb, 10, code_system_pattern=config.R_ICD10)
                if not code_system_matched and re.match(
                    config.R_JHSD0004_DIAGNOSIS_TYPE, secondary_dx_system
                ):
                    secondary_dx_code, secondary_dx_system = "", ""

                if primary_dx_code or primary_dx_text or secondary_dx_code:
                    # Collect diagnostic type
                    diagnosis_type, _, _, code_system_matched = get_code_from_segment(
                        prb,
                        10,
                        code_system_pattern=config.R_JHSD0004_DIAGNOSIS_TYPE,
                    )
                    if not code_system_matched:
                        diagnosis_type = ""

                    # Collect provisional flag
                    provisional, _, _, code_system_matched = get_code_from_segment(
                        prb,
                        13,
                        code_system_pattern=config.R_JHSD0005_PROVISIONAL_FLAG,
                        default_value="0",
                    )
                    if not code_system_matched:
                        provisional = "0"

                    # Collect timestamps
                    time_of_update = extract_element(prb, 2)
                    date_of_onset = extract_element(prb, 16)
                    date_of_diagnosis = extract_element(prb, 7)

                    # Add a row
                    row = [
                        patient_id,
                        primary_dx_system,
                        primary_dx_code,
                        primary_dx_text,
                        secondary_dx_system,
                        secondary_dx_code,
                        diagnosis_type,
                        provisional,
                        time_of_update,
                        date_of_onset,
                        date_of_diagnosis,
                    ]
                    rows.append(row)
    return rows


def extract_ppr_01() -> dict:
    """Collects diagnosis records from PPR-01, saves them as CSV files.

    Returns:
        process_analytics (dict): Dictionary containing analytic data of this entire process.
    """
    # Perform extraction
    data_type = "PPR-01"
    process_analytics = extract_using_data_type(
        function=_parse_ppr_01,
        data_type=data_type,
        chunksize=-1,
        single_file=config.SINGLE_FILE[data_type],
    )

    return process_analytics
