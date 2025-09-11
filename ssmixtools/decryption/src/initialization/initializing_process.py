"""Module for initializing decryption"""

import os
import psutil
from ....generals import general_config as config


def initialize_decryption(
    source_dir: str,
    output_dir: str,
    private_key_path: str,
    max_workers: int,
    temp_dir: str,
) -> bool:
    """
    Initialize the decryption protocol.

    This function performs the following steps:
    1. Validates the input parameters.
    2. Writes validated parameters as environment variables.

    Returns:
        bool: Returns `True` if all parameters are valid, otherwise `False`.
    """

    # Validate parameters
    if not os.path.exists(source_dir):
        print("The directory for the encrypted files (source_dir) does not exist.")
        return False
    if not os.path.exists(output_dir):
        print("The directory for saving the outputs (output_dir) does not exist.")
        return False
    if not os.path.exists(private_key_path):
        print("The path to the private key (private_key_path) does not exist.")
        return False
    if max_workers is not None:
        if not isinstance(max_workers, int):
            print("The max_workers must be a integer.")

    # Determine max workers
    if max_workers is None:
        max_workers = psutil.cpu_count(logical=config.LOGICAL_CPU) - config.CPU_MARGIN

    # Write environment variables
    os.environ["DCRYP_SOURCE_DIR"] = source_dir
    os.environ["DCRYP_OUTPUT_DIR"] = output_dir
    os.environ["DCRYP_PRIVATE_KEY_PTH"] = private_key_path
    os.environ["DCRYP_MAX_WORKERS"] = str(max_workers)
    os.environ["DCRYP_TEMP_DIR"] = temp_dir

    return True
