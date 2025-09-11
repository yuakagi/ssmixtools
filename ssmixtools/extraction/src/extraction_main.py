"""
Top-Level Module for Extracting Data from SS-MIX2 Storage

"""

import os
import sys
import tempfile
import traceback
from .initialization import initialize_protocol
from .record_extraction import extract_records
from .inspection import inspect_data
from .deidentification import deidentify_data
from .encryption import encrypt_outputs
from .extraction_utils import copy_intermediate_files
from ...generals.general_utils import LogRedirector


def extract(
    ssmix_root: str,
    output_dir: str,
    pubkey_path: str,
    identity_tag: str,
    max_workers: int = None,
    extraction_period_start: str = None,
    extraction_period_end: str = None,
    min_encounters: int = 1,
    log_dir: str = None,
) -> None:
    """
    **Top-Level Module for Extracting Data from SS-MIX2 Storage**

    This module extracts clinical records from SS-MIX2 storage, processes them, and saves
    the results in a structured format. The extracted data is encrypted using a hybrid cryptosystem
    (AES + RSA) for secure handling.

    Warnings:
        - Keep your private RSA key secure; it is required for decryption.
        - Ensure the SS-MIX2 root directory is properly structured according to the SS-MIX2 implementation guidelines.

    Note:
        - Patient IDs are deidentified by random shuffling and reassignment. The mapping between original and deidentified IDs is stored in the patient ID table.
        - Deidentification is irreversible if the patient ID table is deleted.
        - Extracted data is encrypted. Use the provided RSA private key to decrypt it.

    Args:
        ssmix_root (str): Path to the SS-MIX2 root directory.
        output_dir (str): Directory for saving the extracted files.
        pubkey_path (str): Path to an RSA public key used for encrypting the data.
        identity_tag (str): Identity tag appended to filenames for source identification.
        max_workers (int, optional): Maximum number of workers for multiprocessing. Defaults to the number of physical CPU cores minus 1.
        extraction_period_start (str, optional): Earliest visit date for inclusion in the extraction.
        extraction_period_end (str, optional): Latest visit date for inclusion in the extraction.
            Records of all visits are included if at least one visit falls within this range.
        min_encounters (int, optional): Minimum number of visit dates required for inclusion.
        log_dir (str, optional): Directory for saving logs generated during extraction.

    Returns:
        None: Extracted data and analytics are saved in the specified output directory.

    **Workflow**

        1. **Initialization**:
            Configures the extraction protocol and verifies prerequisites.
        2. **Data Extraction**:
            Extracts records from SS-MIX2 storage and organizes them by record types.
        3. **Inspection and Deidentification**:
            Inspects extracted data for quality and deidentifies patient IDs.
        4. **Encryption**:
            Encrypts the extracted data using the provided RSA public key.

    **Extracted Records**

        The following clinical record tables are extracted:

        .. csv-table:: Clinical Record Tables
           :header: "File Name Pattern", "Contents"

           "ADT-22_*.bin", "Admission records"
           "ADT-52_*.bin", "Discharge records"
           "ADT-12_*.bin", "Outpatient visits"
           "PPR-01_*.bin", "Diagnosis records"
           "OMP-01_*.bin", "Prescription orders"
           "OMP-02_*.bin", "Injection orders"
           "OML-11_*.bin", "Laboratory test results"

        Additionally, the following tables are created:

        .. csv-table:: Additional Tables
           :header: "File Name Pattern", "Contents"

           "patient_id_*.bin", "Pairs of original and deidentified patient IDs"
           "DOB_*.bin", "Patients' dates of birth"
           "patient_metadata_*.bin", "Patient metadata including sex"

    **Example Usage**

        Generate RSA keys

        .. code-block:: bash

            ssh-keygen -t rsa -b 2048 -f my_rsa_key

        Extract Data

        .. code-block:: python

            import ssmixtools

            def main():
                ssmixtools.extraction.extract(
                    ssmix_root='/path/to/ssmix/root',
                    output_dir='/directory/for/saving/extracted/files',
                    pubkey_path='/path/to/your/rsa/public/key',
                    identity_tag='UT',
                    max_workers=None,
                    extraction_period_start='2011/01/01',
                    extraction_period_end='2023/12/31',
                    min_encounters=1,
                    log_dir='/directory/for/leaving/logs'
                )

            if __name__ == "__main__":
                main()

        Output Directory Structure

        .. code-block:: text

            output_dir
            ├── analytics
            └── tables
                ├── patient_id_UT.bin
                ├── DOB_UT.bin
                ├── patient_metadata_UT.bin
                ├── ADT-12_0_UT.bin
                ├── ...
                └── OML-11_76_UT.bin
    """

    # Debugging config
    # NOTE: You can run the debug mode by setting DEBUG_MODE == 1
    debug_flag = os.environ.get("DEBUG_MODE")
    test = debug_flag == "1"
    test_chunks = 2 if test else 0

    with LogRedirector(log_dir=log_dir, file_name=None):
        child_output_dir = os.path.join(output_dir, "extracted_by_ssmixtools/")
        if not os.path.exists(child_output_dir):
            os.mkdir(child_output_dir)
        with tempfile.TemporaryDirectory(dir=output_dir) as temp_dir:
            # Initialize
            initialized = initialize_protocol(
                ssmix_root=ssmix_root,
                output_dir=child_output_dir,
                pubkey_path=pubkey_path,
                identity_tag=identity_tag,
                internal_dir=temp_dir,
                test=test,
                max_workers=max_workers,
                extraction_period_start=extraction_period_start,
                extraction_period_end=extraction_period_end,
                min_encounters=min_encounters,
                test_chunks=test_chunks,
            )

            if initialized:
                try:
                    # Extraction
                    extract_records()
                    inspect_data()
                    deidentify_data()
                    encrypt_outputs()
                    print("All steps completed.")
                except Exception as e:
                    print("======================================")
                    print("Error during extraction:")
                    print("Exception:", e)
                    print("Traceback:")
                    traceback.print_exc(file=sys.stdout)
                    print("======================================")
                finally:
                    # Copy intermediate files for debug
                    if test:
                        copy_intermediate_files()

            else:
                print("Initialization failed")
