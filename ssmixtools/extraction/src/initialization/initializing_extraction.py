"""Module responsible for initializing extraction process"""

import os
from ..extraction_settings import ExtractionSettingsManager


def initialize_protocol(
    ssmix_root: str,
    output_dir: str,
    internal_dir: str,
    pubkey_path: str,
    identity_tag: str,
    test: bool,
    max_workers: int,
    extraction_period_start: str = None,
    extraction_period_end: str = None,
    min_encounters: int = 1,
    test_chunks: int = 2,
) -> bool:
    """Initializes for extraction.
    Args:
        ssmix_root (str): Path to an SS-MIX2 root directory.
        output_dir (str): Directory for saving the final products.
        internal_dir (str): Director for saving temporary files.
        pubkey_path (str): Path to a RSA public key used for file encryption.
        identity_tag (str): File identity tag.
        test (bool): If true, the extraction process runs on the test mode.
        max_workers (int): Maximum number of workers involved in multiprocessing.
        extraction_period_start (str, optional): Oldest visit date that is valid for inclusion.
        extraction_period_end (str, optional): Latest date that is valid for inclusion.
        min_encounters (int, optional): Minimum number of visit dates for inclusion.
        test_chunks (int, optional): Number of chunks used for testing purposes. The default is 2.
    Returns:
        bool : True if the initialization is finished successfully.
    """
    print("Initiating an extraction process.")
    path_valid = False
    # Validate the given SS-MIX2 root directory
    if not os.path.exists(ssmix_root):
        print("The SS-MIX2 root path you set does not exist.")
    # Validate the output directory
    elif not os.path.exists(output_dir):
        print("The path for saving extracted data (output_dir) does not exist.")
    elif os.listdir(output_dir):
        print("The directory for saving extracted data (output_dir) is not empty.")
        print("Please set an empty directory for output_dir.")
    # Validate the public key path
    elif not os.path.exists(pubkey_path):
        print("The path to the RSA public key does not exist.")
    else:
        path_valid = True

    if path_valid:
        # Instantiate
        settings_manager = ExtractionSettingsManager(
            ssmix_root=ssmix_root,
            output_dir=output_dir,
            pubkey_path=pubkey_path,
            internal_dir=internal_dir,
            identity_tag=identity_tag,
            test=test,
            max_workers=max_workers,
            extraction_period_start=extraction_period_start,
            extraction_period_end=extraction_period_end,
            min_encounters=min_encounters,
            test_chunks=test_chunks,
        )
        # Write settings to the environment
        settings_manager.write()
        # Create directories
        settings_manager.create_necessary_dirs()

        print("Initialization finished.")

        return True

    return False
