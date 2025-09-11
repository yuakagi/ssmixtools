"""Module for extracting OMP-02 records (injection agent orders)"""

from pandas.core.series import Series
from ...extraction_utils import (
    get_code_from_segment,
    hl7_to_list,
    group_segments,
    extract_element,
    extract_using_data_type,
)
from .....generals import general_config as config


def _parse_omp_02(task: Series) -> list[list[str]]:
    """Opens an OMP-02 file and collects records of pharmacy orders for injections.

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
                    rx_type_system (str): Coding system for treatment types (such as blood products etc.)
                    rx_type_code (str): Code for the treatment type
                    rx_type_text (str): Name of the treatment type
                    primary_rx_system (str): Primary coding system name of the medication (HOT expected)
                    primary_rx_code (str): Primary medication code
                    primary_rx_text (str): Primary name of the medication
                    secondary_rx_system (str): Secondary coding system name of the medication (YJ or MYAK expected)
                    secondary_rx_code (str): Secondary medication code
                    secondary_rx_text (str): Secondary name of the medication
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
        segments_parsed = ["ORC", "RXE", "RXC", "TQ1"]
        order_sequence_pattern = r"ORC,RXE,TQ1(,RXC)*"
        # Convert an HL7 message to a list of segments of interest
        hl7_message = hl7_to_list(file_path, segments_parsed)
        # Group segments by orders
        orders = group_segments(hl7_message, order_sequence_pattern)

        # Loop through orders
        for order in orders:
            orc = order[0]  # ORC segment
            rxe = order[1]  # RXE segment
            tq1 = order[2]  # TQ1 segment
            rxcs = order[3:] if len(order) > 3 else []
            order_type = extract_element(orc, 1)

            # Ensure that the order type is order creation/update ('NW'), not order deletion.
            if order_type == "NW":
                # Extract time when the order was created.
                time_of_order = extract_element(orc, 9)

                # **************************************************
                # * WARNING !! THIS MUST BE DELTEDE FOR PRODUCTION *
                # **************************************************
                # * Description:
                # *     On 2023/12/26, time of order reocrds (ORC-9) in coi21 server of OMP-02 are erroneous.
                # *     Seemingly, all values have the timestamp format of 'YYYYmmDD00HHMM', that is, extra two zeros '00' are inserted after days.
                # *     To counteract this error, the lines below is added for developpment purpous.
                # *     This must be handled properly later.
                if time_of_order[8:10] == "00":
                    if int(time_of_order[10:12]) < 24:
                        time_of_order = time_of_order[0:8] + time_of_order[10:] + "00"
                # **************************************************

                # Create a dictionary to store secondary injection component records. Used mainly to store YJ or MYAK codes.
                secondary_dict = {}
                # RXE-31 contain a list of component records. Each record is concatenated with '~', and each element of a component record is separated with '^'.
                rxe31 = extract_element(rxe, 31).split("~")

                if rxe31:
                    # Loop through component records.
                    for component in rxe31:
                        elements = component.split("^")
                        local_code = ""
                        # Seach for local and standardized code pairs.
                        if len(elements) > 2:
                            # In case the local code comes first
                            if elements[2].startswith(
                                "99"
                            ):  # <- in HL7 v2.5, local code system starts with '99'
                                local_code = elements[0]
                                secondary_code = extract_element(elements, 3)
                                secondary_text = extract_element(elements, 4)
                                secondary_system = extract_element(elements, 5)
                            # In case the local code comes at the end
                            elif len(elements) > 5:
                                if elements[5].startswith("99"):
                                    local_code = elements[3]
                                    secondary_code = extract_element(elements, 0)
                                    secondary_text = extract_element(elements, 1)
                                    secondary_system = extract_element(elements, 2)
                        if local_code and (secondary_code or secondary_text):
                            secondary_dict[local_code] = {
                                "code": secondary_code,
                                "text": secondary_text,
                                "system": secondary_system,
                            }
                # Extract data related to injecton type
                rx_type_code, rx_type_text, rx_type_system, _ = get_code_from_segment(
                    rxe,
                    2,
                    code_system_pattern=config.R_JHSI0002_INJECTION_TYPE,
                )

                # Extract timestamps
                start_of_order = extract_element(tq1, 7)
                end_of_order = extract_element(tq1, 8)

                # Loop through RXC segments. Each RXC segment contains an injection component.
                for rxc in rxcs:
                    # Extract primary drug code (supposed to be encoded by HOT).
                    (
                        primary_rx_code,
                        primary_rx_text,
                        primary_rx_system,
                        _,
                    ) = get_code_from_segment(
                        rxc,
                        2,
                        code_system_pattern=config.R_HOT,
                    )

                    # Proceed if components records are properly stored in RXE-31.
                    secondary_rx_code = ""
                    secondary_rx_text = ""
                    secondary_rx_system = ""
                    if secondary_dict:
                        # Extract local code to refer to RXE-31, in order to extract secondary drug code.
                        if primary_rx_system.startswith("99"):
                            # In case 'primary_rx_code' is a local code
                            local_primary_rx_code = primary_rx_code
                        else:
                            # Search actively for local codes
                            local_primary_rx_code, _, _, _ = get_code_from_segment(
                                rxc,
                                2,
                                code_system_pattern=config.R_LOCAL_SYSTEM,
                                force_output=False,
                            )

                        # Extract secondary code using the local code as a key
                        if local_primary_rx_code in secondary_dict:
                            subdict = secondary_dict.get(local_primary_rx_code)
                            secondary_rx_code = subdict.get("code")
                            secondary_rx_text = subdict.get("text")
                            secondary_rx_system = subdict.get("system")

                    # Add the record only if injection component in code or plain text is available.
                    if (
                        (primary_rx_code != "")
                        or (primary_rx_text != "")
                        or (secondary_rx_code != "")
                        or (secondary_rx_text != "")
                    ):
                        row = [
                            patient_id,
                            rx_type_system,
                            rx_type_code,
                            rx_type_text,
                            primary_rx_system,
                            primary_rx_code,
                            primary_rx_text,
                            secondary_rx_system,
                            secondary_rx_code,
                            secondary_rx_text,
                            time_of_order,
                            start_of_order,
                            end_of_order,
                        ]
                        rows.append(row)
    return rows


def extract_omp_02() -> dict:
    """Collects patient records of pharmacy orders for injections from OMP-02, saves them as CSV files.

    Returns:
        process_analytics (dict): Dictionary containing analytic data of this entire process.
    """
    # Perform extraction
    data_type = "OMP-02"
    process_analytics = extract_using_data_type(
        function=_parse_omp_02,
        data_type=data_type,
        chunksize=-1,
        single_file=config.SINGLE_FILE[data_type],
    )

    return process_analytics
