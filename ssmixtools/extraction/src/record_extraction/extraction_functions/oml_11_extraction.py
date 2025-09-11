"""Module to extract OML-11 records (laboratory test results)"""

import os
import re
import pandas as pd
from pandas.core.series import Series
from ...extraction_utils import (
    get_code_from_segment,
    hl7_to_list,
    group_segments,
    extract_element,
    extract_using_csv,
)
from ...extraction_settings import get_ext_settings
from .....generals import general_config as config


def _parse_oml_11(task: Series) -> list[list]:
    """Opens an OML-11 file and collects records of laboratory test results.

    A file is opened only if the 'condition flag' is 1, indicating the file is the latest version.
    Args:
        task (Series): Task passed by the '_extract_in_parallel' function.
            Its first element is patient ID, the second is the file condition flag
            (which can be either 0, 1, or 2), and the last one is the path to the file.
            The file condition flags:
                0: Invalid, deleted
                1: Latest, valid file
                2: Old record (history)
    Returns:
        rows (list): List that stores laboratory test results.
            Each sublist in the list is a laboratory test record.
                List elements:
                    patient_id (str): Patient ID
                    lab_system (str): Coding system name of the laboratory test (JLAC10 expected)
                    lab_code (str): Standardized code for the laboratory test
                    lab_text (str): Name of the laboratory test
                    value (str): Test result value
                    unit_text (str): Unit for the result in text
                    unit_code (str): Standardized code of the unit
                    unit_system (str): Coding system name of the unit
                    time_sampled (str): Time of specimen sampling
                    time_tested (str): Time when the test was conducted
                    time_reported (str): Time when the test result was reported
            Missing elements are filled with empty strings.
    """
    rows = []
    # Old files are also parsed to accurately assign the time the results are uploaded.
    # NOTE: Because old files are selected, number of records is significantly increased.
    #       Duplicates must be handled properly in later steps.
    file_condition = task[1]
    if file_condition in ["1", "2"]:
        patient_id = task[0]
        file_path = task[-1]
        # Define variables necessary for data parsing
        segments_parsed = ["SPM", "OBR", "OBX", "TQ1"]
        # NOTE: These patterns allow zero OBX segements, which happens some times.
        #   If you don't allow zero OBX, all other following requests (OBR) are discarded by the regular expression matching.
        specimen_sequence_pattern = r"SPM(,OBR(,OBX)*)+"
        request_sequence_pattern = r"OBR(,OBX)*"
        # Normalize and convert an HL7 message to a list of segments
        hl7_message = hl7_to_list(file_path, segments_parsed)
        # Group by specimens (each group contains all the test results of the specimen.)
        specimens = group_segments(hl7_message, specimen_sequence_pattern)

        # Loop through specimens (i.e., blood, urine, etc.)
        for specimen in specimens:
            spm = specimen[0]  # 'SPM' segment
            time_sampled = extract_element(spm, 17)
            requests = group_segments(specimen, request_sequence_pattern)
            # Get specimen details (specimen type for SPM-4, specimen source for SPM-8)
            spm_code, spm_name, spm_system, _ = get_code_from_segment(
                spm, 4, config.R_JLAC10, default_value=""
            )
            spm_src_code, spm_src_name, spm_src_system, _ = get_code_from_segment(
                spm, 8, config.R_JLAC10, default_value=""
            )

            # Loop through OBR segments and their results
            for request in requests:
                obr = request[0]  # 'OBR' segment
                obxs = request[1:]  # List of 'OBX' segments
                time_reported = extract_element(obr, 22, default_value="")
                # Missing or unconvertable 'time_reported' affects the postprocessing; therefore, it is handled here.
                if time_reported == "":
                    time_reported_invalid = True
                else:
                    time_reported_invalid = pd.isna(
                        pd.to_datetime(time_reported, errors="coerce")
                    )
                # Parent lab reuslt
                # In HL7 ver2.5, OBR-26 is supposed to have three elements separated by ^
                parent_lab_result = extract_element(obr, 26).split("^")[-1]

                # Extract parent lab code and name from OBR-4
                # (Main lab codes are supposed to be stored in OBX-3, butoccasionally in OBR-4.
                # This may be important for microbiology culture results.)
                sup_lab_code, sup_lab_text, sup_lab_system, _ = get_code_from_segment(
                    segment=obr, index=4, code_system_pattern=config.R_JLAC10
                )

                # pylint:disable=invalid-unary-operand-type
                time_reported_valid = ~time_reported_invalid
                file_is_latest = file_condition == "1"
                if time_reported_valid or file_is_latest:
                    # Dictionary to store OBX-4 related results
                    related_results = {}
                    # Loop through OBX segments ('OBX' segments contain actual observed values.)
                    n_obx = len(obxs)
                    for obx in obxs:
                        # Extract main lab code, and its name etc.
                        lab_code, lab_text, lab_system, jc10_used = (
                            get_code_from_segment(
                                segment=obx,
                                index=3,
                                code_system_pattern=config.R_JLAC10,
                            )
                        )
                        jc10_pattern_match = re.fullmatch(
                            config.R_JLAC10_CODE, lab_code
                        )
                        jc10_confirmed = jc10_used and jc10_pattern_match

                        # Extract test value
                        value = extract_element(obx, 5)
                        n_hats_in_val = value.count("^")
                        if n_hats_in_val in (2, 5):
                            # If the value is separated into some segments, the second element is selected (usually value in plain text)
                            value_elements = value.split("^")
                            value = value_elements[1]
                        # Extract unit
                        unit_code, unit_text, unit_system, _ = get_code_from_segment(
                            segment=obx, index=6, code_system_pattern=config.R_ISO_PLUS
                        )
                        # Extract time tested
                        time_tested = extract_element(obx, 14)
                        # Sub ID (OBX-4)
                        related_val = ""  # Initialize related_val
                        sub_id = extract_element(obx, 4)
                        if sub_id != "":
                            if sub_id not in related_results:
                                # NOTE: Currently, this dictionary only records the first value in a series with the same OBX-4 value.
                                related_results[sub_id] = value
                            else:
                                related_val = related_results[sub_id]
                        # Special handlings for missing sub IDs
                        elif (n_obx == 2) and not jc10_confirmed:
                            # NOTE: Currently, this is only applicable for an OBR with two OBX segements.
                            if "ssmixtools_prov_sub_id" in related_results:
                                related_val = related_results["ssmixtools_prov_sub_id"]
                            else:
                                # Check OBX-5 (result value) to see if it can be a candidate for a related value of the next OBX entity
                                if n_hats_in_val in (2, 5):
                                    val_system = value_elements[2]
                                    if val_system.startswith("99"):
                                        related_results["ssmixtools_prov_sub_id"] = (
                                            value
                                        )

                        # ***************************************
                        # * Handle records without JLAC10 codes *
                        # ***************************************
                        # In this step, lab codes and names are modifed to make it easier to map them to JLAC10 in the cleaning step (optional)
                        if not jc10_confirmed:
                            # Exclude records that are obviously comments
                            if lab_code.endswith(config.LAB_COMMENT_SUFFIXES):
                                lab_code, lab_text, value = "", "", ""

                            # Modify lab codes, texts for possible mapping
                            else:
                                lab_code = "|".join(
                                    [
                                        spm_code,
                                        spm_src_code,
                                        sup_lab_code,
                                        lab_code,
                                    ]
                                )
                                lab_text = "|".join(
                                    [
                                        spm_name,
                                        spm_src_name,
                                        sup_lab_text,
                                        parent_lab_result,
                                        related_val,
                                        lab_text,
                                    ]
                                )
                                lab_system = "non-JC10"

                        if (lab_code != "" or lab_text != "") and (value != ""):
                            row = [
                                patient_id,
                                lab_system,
                                lab_code,
                                lab_text,
                                value,
                                unit_text,
                                unit_code,
                                unit_system,
                                time_sampled,
                                time_tested,
                                time_reported,
                            ]
                            rows.append(row)

    return rows


def _postprocess_oml_11(df: pd.DataFrame) -> pd.DataFrame:
    """Postprocesses the created table."""
    default_cols = df.columns
    df["reported_time_dt"] = pd.to_datetime(
        df["reported_time"], format="mixed", errors="coerce"
    )
    df["missing_reported_time"] = df["reported_time_dt"].isna().astype(int)
    df = df.fillna("")
    # First, drop duplicated test results, leaving ones with oldest reported time.
    # NOTE: Missing reported time indicates records are from the latest file, because it is only allowed in files whose names end with 1 (latest file).
    df = df.sort_values(
        by=["missing_reported_time", "reported_time_dt"], ascending=[True, True]
    )
    df = df.drop_duplicates(
        subset=[
            config.COL_PID,
            "lab_code",
            "lab_text",
            "value",
            "unit_text",
            "unit_code",
            "sampled_time",
        ],
        keep="first",
    )
    # Then, select the final results only
    df = df.sort_values(
        by=["missing_reported_time", "reported_time_dt"], ascending=[False, False]
    )
    df = df.drop_duplicates(
        subset=[
            config.COL_PID,
            "lab_code",
            "lab_text",
            "sampled_time",
        ],
        keep="first",
    )
    df = df[default_cols]
    return df


def extract_oml_11() -> dict:
    """Collects patient records of laboratory test results from OML-11, saves them as CSV files.

    Returns:
        process_analytics (dict): Dictionary containing analytic data of this entire process.
    """
    # Perform extraction
    data_type = "OML-11"
    file_paths_dir = get_ext_settings("EXT_FILE_PATHS_DIR")
    raw_table_dir = get_ext_settings("EXT_RAW_TABLE_DIR")
    # NOTE: By using the following file name pattern, this function searches OML-12 as well.
    loaded_csv_name = config.DATA_TYPE_PATH_PATTERN.replace("*", "OML-1[12]_*")
    loaded_csv_pattern = os.path.join(file_paths_dir, loaded_csv_name)
    # NOTE: Saved files are alled named with OML-11, even if the source is OML-12
    output_csv_name = config.TIME_SERIES_DATA_PATTERN.replace("*", f"{data_type}_*")
    output_csv_path = os.path.join(raw_table_dir, output_csv_name)
    output_csv_col_names = config.RECORD_TABLE_PARAMS[data_type]["all"]

    process_analytics = extract_using_csv(
        function=_parse_oml_11,
        chunksize=-1,
        loaded_csv_path=loaded_csv_pattern,
        output_csv_path=output_csv_path,
        output_csv_col_names=output_csv_col_names,
        single_file=config.SINGLE_FILE[data_type],
        postprocess_fn=_postprocess_oml_11,
    )

    return process_analytics
