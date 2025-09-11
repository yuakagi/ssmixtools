"""Module to extract OMP-01 records (pharmacy orders, except for injection agents)"""

from pandas.core.series import Series
from ...extraction_utils import (
    get_code_from_segment,
    get_values_with_unit,
    hl7_to_list,
    group_segments,
    extract_element,
    extract_using_data_type,
)
from .....generals import general_config as config


def _parse_omp_01(task: Series) -> list[list[str]]:
    """Opens an OMP-01 file and collects records of pharmacy orders (except for injections).

    A file is opened only if the 'condition flag' is 1, indicating the file is the latest version.
    Args:
        task (Series): Task passed by the '_extract_in_parallel' function.
            Its first element is patient ID, the second is the file condition flag
            (which can be either 0, 1, or 2), and the last one is the path to the file.
    Returns:
        rows (list): List that stores pharmacy order records.
            Each sublist in the list is a pharmacy order.
                List elements:
                    patient_id (str): Patient ID
                    primary_rx_system (str): Primary coding system name of the medication (HOT expected)
                    primary_rx_code (str): Primary medication code
                    primary_rx_text (str): Primary name of the medication
                    secondary_rx_system (str): Secondary coding system name of the medication (YJ or MYAK expected)
                    secondary_rx_code (str): Secondary medication code
                    secondary_rx_text (str): Secondary name of the medication
                    duration (str): Prescription duration
                    time_of_order (str): Time when the order was made
                    start_of_order (str): Time when the order becomes valid
                    end_of_order (str): Time when the order expires
            Missing elements are filled with empty strings.
    """
    rows = []
    if task[1] == "1":
        patient_id = task[0]
        file_path = task[-1]
        # Initialize parameters necessary for data parsing
        segments_parsed = ["ORC", "RXE", "TQ1"]
        order_sequence_pattern = "ORC,RXE,TQ1"
        # Convert an HL7 message to a list of segments of interest
        hl7_message = hl7_to_list(file_path, segments_parsed)
        # Group segments by orders
        orders = group_segments(hl7_message, order_sequence_pattern)
        # Loop through orders
        for order in orders:
            orc = order[0]  # ORC segment
            rxe = order[1]  # RXE segment
            tq1 = order[2]  # TQ1 segment
            order_type = extract_element(orc, 1)
            time_of_order = extract_element(orc, 9)

            # Ensure that the order type is order creation/update ('NW'), not order deletion.
            if order_type == "NW":
                # Extract primary drug code from RXE-2, which is supposed to be encoded by HOT.
                (
                    primary_rx_code,
                    primary_rx_text,
                    primary_rx_system,
                    _,
                ) = get_code_from_segment(rxe, 2, code_system_pattern=config.R_HOT)

                # Extract secondary drug code from RXE-31, which is supposed to be encoded by either YJ or MYAK.
                (
                    secondary_rx_code,
                    secondary_rx_text,
                    secondary_rx_system,
                    _,
                ) = get_code_from_segment(
                    rxe,
                    31,
                    code_system_pattern=config.R_YJ_OR_MYAK,
                )

                # Extract other information only if any drug code or name exists
                if (
                    (primary_rx_code != "")
                    or (primary_rx_text != "")
                    or (secondary_rx_code != "")
                    or (secondary_rx_text != "")
                ):
                    duration = get_values_with_unit(tq1, 6)
                    start_of_order = extract_element(tq1, 7)
                    end_of_order = extract_element(tq1, 8)
                    row = [
                        patient_id,
                        primary_rx_system,
                        primary_rx_code,
                        primary_rx_text,
                        secondary_rx_system,
                        secondary_rx_code,
                        secondary_rx_text,
                        duration,
                        time_of_order,
                        start_of_order,
                        end_of_order,
                    ]
                    rows.append(row)
    return rows


def extract_omp_01() -> dict:
    """Collects patient records of pharmacy orders (except for injections) from OMP-01, saves them as CSV files.

    Returns:
        process_analytics (dict): Dictionary containing analytic data of this entire process.
    """
    # Perform extraction
    data_type = "OMP-01"
    process_analytics = extract_using_data_type(
        function=_parse_omp_01,
        data_type=data_type,
        chunksize=-1,
        single_file=config.SINGLE_FILE[data_type],
    )

    return process_analytics
