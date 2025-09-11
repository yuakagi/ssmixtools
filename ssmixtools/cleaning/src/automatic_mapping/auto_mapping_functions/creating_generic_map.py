"""Module to create generic maps"""

import os
import glob
import pandas as pd
from ...cleaning_utils import clean_drug_names, parallel_map_partitions_cln
from ...cleaning_settings import get_cln_settings
from .....generals import general_config as config


def _create_generic_text_to_atc(
    df: pd.DataFrame,
    temp_map_path_pattern: str,
    pid: int,
):
    """Creates a generic text-to-ATC mapping table.

    This function extracts unique text-ATC pairs from the input DataFrame,
    creating intermediate mapping tables saved by child processes. These
    intermediate tables are later aggregated into a final mapping table.

    Args:
        df (pd.DataFrame): Input DataFrame containing drug names and ATC codes.
        temp_map_path_pattern (str): Path pattern for saving intermediate mapping tables.
        pid (int): Process ID, used to differentiate temporary file paths.

    Returns:
        pd.DataFrame: Returns the input DataFrame for consistency.
    """

    generic_map = pd.DataFrame(columns=["text", config.COL_ATC])
    generic_map["text"] = clean_drug_names(df[config.COL_ITEM_NAME])
    generic_map[config.COL_ATC] = df[config.COL_ITEM_CODE]
    generic_map = generic_map.drop_duplicates()
    generic_map = generic_map.dropna(how="any")

    # Determine the path to save the intermediate table
    temp_file_path = temp_map_path_pattern.replace("*", str(pid))

    # Concatenate the table with the existing table
    if os.path.exists(temp_file_path):
        existing_table = pd.read_pickle(temp_file_path)
        generic_map = pd.concat([generic_map, existing_table])
        generic_map = generic_map.drop_duplicates()

    # Save the intermediate table as a pickled object
    generic_map.to_pickle(temp_file_path)

    return df


def create_generic_text_to_atc():
    """Generates a generic text-to-ATC mapping table.

    This function creates a mapping table from existing drug name-ATC code mappings
    (e.g., OMP-01, OMP-02). It enhances the mapping performance by aggregating unique
    text-ATC pairs into a single table.

    Args:
        None

    Returns:
        None: Saves the generated mapping table as a CSV file.
    """

    # Initialize variables
    temp_dir = get_cln_settings("CLN_TEMP_DIR")
    internal_dir = get_cln_settings("CLN_INTERNAL_DIR")
    generic_map_pattern = get_cln_settings("CLN_GENERIC_MAP_PTN")
    temp_map_name_pattern = (
        os.path.basename(generic_map_pattern)
        .replace(".csv", ".pkl")
        .replace("*", "text_to_ATC_*")
    )
    temp_map_path_pattern = os.path.join(temp_dir, temp_map_name_pattern)
    omp01_path_pattern = os.path.join(
        internal_dir, config.PRESCRIPTION_ORDER_TABLE_PATTERN
    )
    omp02_path_pattern = os.path.join(
        internal_dir, config.INJECTION_ORDER_TABLE_PATTERN
    )
    omp01_files = glob.glob(omp01_path_pattern)
    omp02_files = glob.glob(omp02_path_pattern)
    drug_table_files = omp01_files + omp02_files

    # Collect unique text-ATC pairs in parallel, and save the results by child processes
    _ = parallel_map_partitions_cln(
        csv_path_pattern=drug_table_files,
        function=_create_generic_text_to_atc,
        chunksize=-1,
        pid_as_arg=True,
        temp_map_path_pattern=temp_map_path_pattern,
    )

    # Aggregate temporary tables saved by child processes
    temp_map_paths = glob.glob(temp_map_path_pattern)
    generic_map = None
    for path in temp_map_paths:
        temp_map = pd.read_pickle(path)
        if generic_map is None:
            generic_map = temp_map
        else:
            generic_map = pd.concat([generic_map, temp_map]).drop_duplicates()

        os.remove(path)

    # Save the final product
    output_path = generic_map_pattern.replace("*", "text_to_ATC")
    generic_map.columns = [config.COL_ORIGINAL, config.COL_TARGET]
    generic_map.to_csv(output_path, header=True, index=False)
