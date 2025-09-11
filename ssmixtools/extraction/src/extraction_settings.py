"""Settings related to record extraction"""

import os
from typing import Union, Optional
from datetime import datetime
import chardet
from ...generals import general_config as config
from ...generals.general_utils import define_max_workers

# Constants
INT_VALS = [
    "MIN_ENCOUNTERS",
    "EXT_TEST",
    "EXT_TEST_CHUNKS",
    "EXT_MAX_WORKERS",
]
TS_VALS = {
    "EXT_PERIOD_START": "%Y/%m/%d",
    "EXT_PERIOD_END": "%Y/%m/%d",
}


def get_ext_settings(name: str) -> Optional[Union[int, str, datetime, None]]:
    """Retrieves environment variables set by the ExtractionSettingsManager.

    Args:
        name (str): Name of an environment variable.
    Returns:
        value (Optional[Union[int, str, datetime]]): Environment variable, converted to the appropriate data type.
    """
    value = os.environ.get(name)
    if value is not None:
        if name in INT_VALS:
            value = int(value)
        elif name in TS_VALS:
            value = datetime.strptime(value, TS_VALS[name])

    return value


class ExtractionSettingsManager:
    """Class to handle settings.

    On instantiation, this class defines environment variables related to the extraction
    (called 'settings' in this package) and stores them as the attribute 'self.variables'.
    These variables are written to environment variables using the 'write()' method.
    Written variables can be accessed using os.environ.get(); however,
    using the 'get_ext_settings' function is recommended for consistency.

    Attributes:
        self.variables (dict): Dictionary that contains all the settings.
            This dictionary has the names of the environment variables as its keys, and the settings as its values.

    NOTE: Please follow these naming rules for the setting variables:
        1. Directory names must end with 'DIR'.
        2. Paths must end with 'PTH'.
        3. Name patterns must end with 'PTN'.
        4. Names should start with 'EXT' if related to extraction.
    """

    def __init__(
        self,
        ssmix_root: str,
        output_dir: str,
        internal_dir: str,
        pubkey_path: str,
        identity_tag: str,
        test: bool,
        max_workers: int = None,
        extraction_period_start: str = None,
        extraction_period_end: str = None,
        min_encounters: int = 1,
        test_chunks: int = 2,
    ):
        """
        Args:
            ssmix_root (str): Root directory for the SS-MIX storage.
            output_dir (str): Directory where output files will be stored.
            internal_dir (str): Internal directory for temporary and raw files.
            pubkey_path (str): Path to the public key used for encryption.
            identity_tag (str): Identity tag for the extraction process.
            test (bool): Flag to enable test mode.
            max_workers (int, optional): Maximum number of workers for multiprocessing. Defaults to None.
            extraction_period_start (str, optional): Start date of the extraction period in '%Y/%m/%d' format.
            extraction_period_end (str, optional): End date of the extraction period in '%Y/%m/%d' format.
            min_encounters (int, optional): Minimum number of encounters required. Defaults to 1.
            test_chunks (int, optional): Number of chunks for testing. Defaults to 2.
        """
        # Ensure that directories for saving files are empty
        if os.listdir(output_dir):
            raise OSError(f"Output directory '{output_dir}' is not empty.")
        # Define variables
        initialized_time = datetime.now().strftime("%Y%m%d%H%M%S")
        test_mode = int(test)
        if max_workers is None:
            max_workers = define_max_workers()
        # Ensure that ssmix_root is an absolute path
        ssmix_root = os.path.abspath(ssmix_root)
        # Detect encoding of HL7 messages
        encoding_params = None
        print("Detecting file encoding...")
        for root, _, files in os.walk(ssmix_root):
            for file in files:
                file_path = os.path.join(root, file)
                with open(file_path, "rb") as f:
                    sample_text = f.read()
                    encoding_params = chardet.detect(sample_text)
                if encoding_params:
                    break
            if encoding_params:
                break
        encoding = encoding_params["encoding"]
        print(f"Encoding detected: {encoding}")
        print("Encoding detection details:", encoding_params)
        # Define directories
        file_path_dir = os.path.join(internal_dir, "paths/")
        deidentified_dir = os.path.join(internal_dir, "deidentified/")
        deidentified_tables_dir = os.path.join(deidentified_dir, "tables/")
        analytics_dir = os.path.join(output_dir, f"analytics_{identity_tag}/")
        inspection_dir = os.path.join(analytics_dir, f"inspection_{identity_tag}/")
        # Set given parameters
        self.variables = {
            # Variables related to the extraction environment
            "EXT_INIT_TIME": initialized_time,
            "IDENTITY_TAG": identity_tag,
            "SS-MIX_ROOT": ssmix_root,
            "MIN_ENCOUNTERS": min_encounters,
            "HL7_ENCODING": encoding,
            "EXT_PUBKEY_PATH": pubkey_path,
            "EXT_PERIOD_START": extraction_period_start,
            "EXT_PERIOD_END": extraction_period_end,
            "EXT_TEST": test_mode,
            "EXT_TEST_CHUNKS": test_chunks,
            "EXT_MAX_WORKERS": max_workers,
            # Directories
            "EXT_OUTPUT_DIR": output_dir,
            "EXT_INTERNAL_DIR": internal_dir,
            "EXT_TEMP_DIR": os.path.join(internal_dir, "temp/"),
            "EXT_ANALYTICS_DIR": analytics_dir,
            "EXT_INSPECTION_DIR": inspection_dir,
            "EXT_FILE_PATHS_DIR": file_path_dir,
            "EXT_RAW_TABLE_DIR": os.path.join(internal_dir, "raw/"),
            "EXT_DEIDENTIFIED_DIR": deidentified_dir,
            "EXT_DEIDENTIFIED_TABLES_DIR": deidentified_tables_dir,
            "EXT_OUTPUT_TABLES_DIR": os.path.join(
                output_dir, f"tables_{identity_tag}/"
            ),
            # Paths and path patterns
            "EXT_PERFORMANCE_PTH": os.path.join(
                analytics_dir, "EXT_performance_sheet.json"
            ),
            "EXT_INSPECTION_SHEET_PTN": os.path.join(
                inspection_dir, "*_inspection_sheet.json"
            ),
            "EXT_ALL_IDS_PTH": os.path.join(file_path_dir, "all_patient_ids.csv"),
            "EXT_SELECTED_IDS_PTH": os.path.join(
                file_path_dir, "selected_patient_ids.csv"
            ),
            "EXT_ALL_METADATA_PTH": os.path.join(
                internal_dir, "all_patient_metadata.csv"
            ),
            "EXT_DEIDENTIFIED_METADATA_PTH": os.path.join(
                deidentified_tables_dir, config.METADATA_TABLE_PATTERN.replace("_*", "")
            ),
            "EXT_ID_MAP_PTH": os.path.join(internal_dir, "patient_id_map.csv"),
            "EXT_DOB_MAP_PTH": os.path.join(internal_dir, "patient_dob_map.csv"),
        }

    def write(self) -> None:
        """Writes settings as environment variables."""
        for k, v in self.variables.items():
            if v is not None:
                if k in INT_VALS:
                    os.environ[k] = str(v)
                else:
                    os.environ[k] = v

    def create_necessary_dirs(self) -> None:
        """Creates directories necessary for extraction."""
        for k, v in self.variables.items():
            if k.endswith("_DIR"):
                if not os.path.exists(v):
                    os.mkdir(v)
