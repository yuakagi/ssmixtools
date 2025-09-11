"""Module to initialize data cleaning"""

import os
from ..cleaning_settings import CleaningSettingsManager


def initialize_cleaning(
    source_dir: str,
    output_dir: str,
    reference_dir: str,
    max_workers: int,
    test: bool,
    test_chunks: int,
    internal_dir: str,
):
    """Initializes the data cleaning process.
    Returns:
        bool : True if the initialization is finished successfully.
    """
    print("Initiating the cleaning process.")

    # Path validation
    path_valid = False
    if not os.path.exists(source_dir):
        print("The directory for the source files (source_dir) does not exist.")
    elif not os.path.exists(output_dir):
        print("The path for saving extracted data (output_dir) does not exist.")
    else:
        path_valid = True

    if path_valid:
        # Instantiate a setting manager
        settings_manager = CleaningSettingsManager(
            source_dir=source_dir,
            output_dir=output_dir,
            reference_dir=reference_dir,
            max_workers=max_workers,
            test=test,
            test_chunks=test_chunks,
            internal_dir=internal_dir,
        )
        # Write settings to the environment
        settings_manager.write()
        # Create directories
        settings_manager.create_necessary_dirs()

        print("Initialization finished.")

        return True

    return False
