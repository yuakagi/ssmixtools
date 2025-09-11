"""The main module for file decryption"""

import os
import tempfile
from .initialization import initialize_decryption
from .decrypting_data import decrypt_data
from .finalization import finalize_process


def decrypt(
    source_dir: str,
    output_dir: str,
    private_key_path: str,
    max_workers: int = None,
) -> None:
    """
    **Top-Level Module for Decrypting Clinical Records**

    This module decrypts clinical records extracted using
    :meth:`ssmixtools.extraction.extract`. The encrypted data is processed
    using a hybrid cryptosystem (AES + RSA) to ensure secure handling and decryption.

    Note:
        - **Private Key Requirement**: The RSA private key used for decryption must match the public key used during encryption.
        - **Input Directory Structure**: The `source_dir` must contain files encrypted using`ssmixtools.extraction.extract`.

    Args:
        source_dir (str): Absolute path to the directory containing encrypted files.
        output_dir (str): Absolute path to the directory for saving decrypted files.
        private_key_path (str): Path to the RSA private key used for decryption.
        max_workers (int, optional): Maximum number of parallel workers for decryption. Defaults to the number of physical CPU cores minus 1.

    Returns:
        None:
            This function saves decrypted files to the specified output directory.

    **Workflow**

        1. **Initialization**:
            - Verifies input paths and prepares temporary storage for decryption.
        2. **Decryption**:
            - Decrypts encrypted files using the specified private key.
            - Organizes decrypted files by identity tags.
        3. **Finalization**:
            - Validates and prepares decrypted files for downstream processes.

    **Example Usage**

        Decrypt files using the `decrypt` function::

            import ssmixtools

            def main():
                ssmixtools.decryption.decrypt(
                    source_dir="/path/to/extracted/binary/files",
                    output_dir="/directory/for/saving/decrypted/files",
                    private_key_path="/path/to/your/private/key",
                    max_workers=None,
                )

            if __name__ == "__main__":
                main()

    **Decrypted Records**

        The decrypted files are organized into subdirectories based on identity tags.
        For example, if the data is extracted from two storages with identity tags `UT`
        and `UK`, the output directory structure will look like this:

        .. code-block:: text

            output_dir
            ├── UT
            │   ├── patient_id_UT.csv
            │   ├── DOB_UT.csv
            │   ├── patient_metadata_UT.csv
            │   ├── ADT-12_0_UT.csv
            │   └── ...
            └── UK
                ├── patient_id_UK.csv
                ├── ...
                └── OML-11_35_UK.csv

    **Post-Decryption**

        - After decryption, clean the CSV files using :mod:`ssmixtools.cleaning.mandatory`.
    """

    child_output_dir = os.path.join(output_dir, "decrypted_by_ssmixtools/")
    if not os.path.exists(child_output_dir):
        os.mkdir(child_output_dir)
    with tempfile.TemporaryDirectory(dir=output_dir) as temp_dir:
        # Initialize
        print("Initializing the decryption process.")
        initialized = initialize_decryption(
            source_dir=source_dir,
            output_dir=child_output_dir,
            private_key_path=private_key_path,
            max_workers=max_workers,
            temp_dir=temp_dir,
        )
        if initialized:
            print("Initialization done.")
            print("Decryption initiated.")
            # Decrypt
            decrypt_data()
            print("Finalizing the process.")
            # Finalize decrypted files
            finalize_process()
            print("All processes completed.")
        else:
            print("Initialization failed.")
