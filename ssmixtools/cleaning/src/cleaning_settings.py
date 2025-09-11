"""Module responsible for initializing extraction process"""

import os
from typing import Union, Optional
from datetime import datetime
from ...generals.general_utils import define_max_workers

# Constants
INT_VALS = ["CLN_TEST", "CLN_TEST_CHUNKS", "CLN_MAX_WORKERS"]


def get_cln_settings(name: str) -> Optional[Union[int, str]]:
    """Loads environment variables written by CleaningSettingsManager.

    Variables listed in 'INT_VALS' are converted to integers.

    Args:
        name (str): Name of the environment variable to be loaded.
    Returns:
        value (str|int): Environment variable that is converted to the proper data type.
    """
    value = os.environ.get(name)
    if (value is not None) and (name in INT_VALS):
        value = int(value)
    return value


class CleaningSettingsManager(object):
    """A class to handle settings.

    On instantiation, this class defines environment-dependent variables related to the cleaning
    (called 'settings' in this package) and stores them as its attribute 'self.variables'.
    These variables are written as environment variables by .write().
    Written variables can be accessed using os.environ.get(); however,
    using the 'get_cln_settings' function is recommended for consistency.
    Attributes:
        self.variables (dict): Dictionary that contains all the settings.
            This dictionary has the names of the environment variables as its keys, and variables as its dictionary values.

    NOTE: Please follow these naming rules for the setting variables;
        1. Directory names must end with DIR.
        2. Paths must end with PTH.
        3. Name patterns must end with PTN.
        4. Names should start with CLN if related to data cleaning
    """

    def __init__(
        self,
        source_dir: str,
        output_dir: str,
        reference_dir: str,
        max_workers: int,
        test: bool,
        test_chunks: int,
        internal_dir: str,
    ):
        # Define variables
        initialized_time = datetime.now().strftime("%Y%m%d%H%M%S")
        test_mode = int(test)
        if max_workers is None:
            max_workers = define_max_workers()

        # Define directories
        analytics_dir = os.path.join(output_dir, "analytics")
        mapping_analytics_dir = os.path.join(analytics_dir, "mapping_analytics")
        cleaning_analytics_dir = os.path.join(analytics_dir, "cleaning_analytics")
        created_ref_dir = os.path.join(reference_dir, "created_reference/")

        # Set given parameters
        self.variables = {
            # Cleaning environment
            "CLN_INIT_TIME": initialized_time,
            "CLN_TEST": test_mode,
            "CLN_TEST_CHUNKS": test_chunks,
            "CLN_MAX_WORKERS": max_workers,
            # Directories
            "CLN_SOURCE_DIR": source_dir,
            "CLN_OUTPUT_DIR": output_dir,
            "CLN_OUTPUT_TABLES_DIR": os.path.join(output_dir, "tables"),
            "CLN_CREATED_REF_DIR": created_ref_dir,
            "CLN_INTERNAL_DIR": internal_dir,
            "CLN_TEMP_DIR": os.path.join(internal_dir, "temp/"),
            "CLN_REFERENCE_DIR": reference_dir,
            "CLN_ANALYTICS_DIR": analytics_dir,
            "CLN_MAPPING_ANALYTICS_DIR": mapping_analytics_dir,
            "CLN_CLEANING_ANALYTICS_DIR": cleaning_analytics_dir,
            # Paths and path patterns
            "CLN_PERFORMANCE_PTH": os.path.join(
                analytics_dir, "cleaning_performance_sheet.json"
            ),
            "CLN_MAPPING_SHEET_PTN": os.path.join(
                mapping_analytics_dir, "*_mapping_sheet.json"
            ),
            "CLN_CLEANING_SHEET_PTN": os.path.join(
                cleaning_analytics_dir, "*_code_cleaning_sheet.json"
            ),
            "CLN_GENERIC_MAP_PTN": os.path.join(created_ref_dir, "generic_*.csv"),
            "CLN_OPTIONAL_MAP_PTN": os.path.join(created_ref_dir, "optional_*.csv"),
            "CLN_LAB_UNITS_PTH": os.path.join(created_ref_dir, "lab_units.csv"),
            "CLN_LAB_NONUM_PTH": os.path.join(created_ref_dir, "lab_nonnumerics.csv"),
        }

    def write(self):
        """Writes settings as environment variables"""
        for k, v in self.variables.items():
            if v is not None:
                if k in INT_VALS:
                    os.environ[k] = str(v)
                else:
                    os.environ[k] = v

    def create_necessary_dirs(self):
        """Creates directories necessary for extraction"""
        for k, v in self.variables.items():
            if k.endswith("_DIR"):
                if not os.path.exists(v):
                    os.mkdir(v)
