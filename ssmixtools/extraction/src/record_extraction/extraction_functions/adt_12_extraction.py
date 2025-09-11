"""Module for extracting ADT-12 records (admission records)"""

from pandas.core.series import Series
from ...extraction_utils import hl7_to_list, extract_element, extract_using_data_type
from .....generals import general_config as config


def _parse_adt_12(task: Series) -> list[list]:
    """Opens an ADT-12 file and collects records of admissions.
    ADT-12 stores outpatient visit records.
    Message type is ADT^A04, using ADT^A01.

    A file is opened only if the 'condition flag' is 1, indicating the file is the latest version.
    Args:
        task (Series): Task passed by the '_extract_in_parallel' function.
            Its first element is patient ID, the second is the file condition flag
            (which can be either 0, 1, or 2), and the last one is the path to the file.
    Returns:
        rows (list): List that stores outpatient visit record elements.
            This is a list with a single element of a list for consistency.
            The child list is the main record component.
                List elements:
                    patient_id (str): Patient ID.
                    dept (str): Clinical department.
                    visiting_date (str): Date of visit.
            If the record is not a valid new outpatient visit record, an empty list is returned.
    """
    rows = []
    if task[1] == "1":
        patient_id = task[0]
        file_path = task[-1]
        # Convert an HL7 message to a list of segments of interest
        segments_parsed = ["MSH", "PV1"]
        hl7_message = hl7_to_list(file_path, segments_parsed)
        message_length = len(hl7_message)
        msh = hl7_message[0]  # MSH segment
        pv1 = hl7_message[1] if message_length > 1 else []  # PV1 segment
        # Check if the message represents an outpatient visit.
        if msh[8].startswith("ADT^A04"):
            visiting_date = extract_element(pv1, 44)
            dept = extract_element(pv1, 10)
            rows = [[patient_id, dept, visiting_date]]
    return rows


def extract_adt_12() -> dict:
    """Collects patient admission records from ADT-12 files, saves them as CSV.

    Returns:
        process_analytics (dict): Dictionary containing analytic data of this entire process.
    """

    # Perform extraction
    data_type = "ADT-12"
    process_analytics = extract_using_data_type(
        function=_parse_adt_12,
        data_type=data_type,
        chunksize=-1,
        single_file=config.SINGLE_FILE[data_type],
    )

    return process_analytics
