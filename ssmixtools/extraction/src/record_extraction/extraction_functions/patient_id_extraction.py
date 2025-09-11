"""Module to extract target patient IDs"""

from ...extraction_settings import get_ext_settings
from ...extraction_utils import parse_tree, extract_using_generator
from .....generals import general_config as config


def lv1_to_patient_ids(lv1: str) -> list[list[str]]:
    """Helper function for 'extract_patient_ids'.

    Args:
        lv1 (str): One of the shallowest directories of the SS-MIX2 storage directory tree.
            This is supposed to be the first three characters of patient IDs.
    Returns:
        row (list): List of lists with a sublist containing a patient ID.
    """
    pid_generator = parse_tree(start_dir=lv1, target_level=3, abs_path=False)
    row = [[pid.strip()] for pid in pid_generator]
    return row


def extract_patient_ids() -> dict:
    """Extracts all patient IDs from an SS-MIX2 storage directory and saves them to a CSV file

    Returns:
        process_analytics (dict): Dictionary containing analytic data of this entire process.
    """
    # Perform extraction
    all_ids_path = get_ext_settings("EXT_ALL_IDS_PTH")
    ssmixroot = get_ext_settings("SS-MIX_ROOT")
    cols = [config.COL_PID]
    chunksize = config.CHUNKSIZES["all_patient_ID_extraction"]
    lv1_generator = parse_tree(start_dir=ssmixroot, target_level=1, abs_path=True)
    process_analytics = extract_using_generator(
        function=lv1_to_patient_ids,
        generator=lv1_generator,
        chunksize=chunksize,
        output_csv_path=all_ids_path,
        output_csv_col_names=cols,
        single_file=True,
    )

    return process_analytics
