"""
Optional Data Cleaning Module
"""

import os
import tempfile
from .initialization import initialize_cleaning
from .optional_mapping import map_data_with_optional_maps, translate_codes
from .lab_result_handlings import extract_unique_lab_values, clean_lab_values
from .cleaning_utils import move_internal_files
from .record_cleaning import perform_final_data_cleaning
from ...generals.general_utils import LogRedirector


def step1(
    source_dir: str,
    reference_dir: str,
    max_workers: int = None,
    log_dir: str = None,
):
    """
    Maps codes using optional mappings and extracts unique laboratory values for the next step (step2).

    Note:
        - Ensure that `optional_text_to_ATC.csv` and `optional_JLAC10_to_JLAC10.csv` are completed before performing this step. These files should have been created in `reference_dir/created_reference` by :meth:`ssmixtools.cleaning.mandatory.clean`

    Args:
        source_dir (str): Path to the directory containing source data cleaned by :meth:`ssmixtools.cleaning.mandatory.clean`.
        reference_dir (str): Path to the directory containing reference mapping files for code mapping.
        max_workers (int, optional): Maximum number of workers for parallel processing. Defaults to the number of physical CPU cores minus 1.
        log_dir (str, optional): Directory for saving log files. If None, logs are printed to the console.

    Returns:
        None

    **Example Usage**

        .. code-block:: python

            import ssmixtools

            ssmixtools.cleaning.optional.step1(
                source_dir='/path/to/source/data',
                reference_dir='/path/to/reference/mapping/files',
                max_workers=None,
                log_dir='/path/to/log/dir',
            )

    **Workflow**

        1. **Optional Code Mapping**:
            - Applies optional mapping tables to clean and standardize clinical codes.

        2. **Unique Laboratory Value Extraction**:
            - Extracts unique units and nonnumeric laboratory values for the optional laboratory data cleaning (step2).
    """

    # Debugging config
    debug_flag = os.environ.get("DEBUG_MODE")
    test = debug_flag == "1"
    test_chunks = 2 if test else 0

    with LogRedirector(log_dir=log_dir, file_name=None):
        # Create a temp dir in the parent directory of source_dir
        with tempfile.TemporaryDirectory(dir=source_dir) as temp_dir:
            # Initialize
            initialized = initialize_cleaning(
                source_dir=source_dir,
                output_dir=source_dir,
                reference_dir=reference_dir,
                max_workers=max_workers,
                test=test,
                test_chunks=test_chunks,
                internal_dir=temp_dir,
            )
            if initialized:
                print("Mapping codes...")
                map_data_with_optional_maps()
                print("Mapping done, preparing for the next step ...")
                extract_unique_lab_values()
                move_internal_files()
                print("All processes completed.")
            else:
                print("Initialization for cleaning failed.")


def step2(
    source_dir: str,
    reference_dir: str,
    max_workers: int = None,
    log_dir: str = None,
):
    """
    Cleans laboratory test results using optionally created mapping tables for units and nonnumeric values.

    Note:
        - Ensure that `lab_nonnumerics.csv` and `lab_units.csv` are completed before performing this step. These files should have been created in `reference_dir/created_reference` by :meth:`ssmixtools.cleaning.optional.step1`

    Args:
        source_dir (str): Path to the directory containing source data cleaned by :meth:`ssmixtools.cleaning.optional.step1`.
        reference_dir (str): Path to the directory containing reference mapping files.
        max_workers (int, optional): Maximum number of workers for parallel processing. Defaults to the number of physical CPU cores minus 1.
        log_dir (str, optional): Directory for saving log files. Defaults to None.

    Returns:
        None

    **Example Usage**

        .. code-block:: python

            import ssmixtools

            ssmixtools.cleaning.optional.step2(
                source_dir='/path/to/source/data',
                reference_dir='/path/to/reference/mapping/files',
                max_workers=None,
                log_dir='/path/to/log/dir',
            )

    **Workflow**

        1. **Unit Mapping and Standardization**:
            - Maps original units to standardized units using a predefined mapping table.
            - Applies unit-specific value corrections through addition and multiplication rules.

        2. **Nonnumeric Value Mapping**:
            - Maps nonnumeric test result values (e.g., "Positive," "Negative") to standardized equivalents.
            - Detects numeric values mistakenly recorded as nonnumeric and moves them to the numeric column.

        3. **Handling Missing and Invalid Records**:
            - Removes rows flagged as non-records or rows missing both numeric and nonnumeric results after cleaning.
            - Ensures that all rows represent valid laboratory results.
    """

    # Debugging config
    debug_flag = os.environ.get("DEBUG_MODE")
    test = debug_flag == "1"
    test_chunks = 2 if test else 0
    with LogRedirector(log_dir=log_dir, file_name=None):
        # Create a temp dir in the parent directory of source_dir
        with tempfile.TemporaryDirectory(dir=source_dir) as temp_dir:
            # Initialize
            initialized = initialize_cleaning(
                source_dir=source_dir,
                output_dir=source_dir,
                reference_dir=reference_dir,
                max_workers=max_workers,
                test=test,
                test_chunks=test_chunks,
                internal_dir=temp_dir,
            )
            if initialized:
                print("Cleaning lab values...")
                clean_lab_values()
                move_internal_files()
                print("All processes completed.")
            else:
                print("Initialization for cleaning failed.")


def step3(
    source_dir: str,
    reference_dir: str,
    max_workers: int = None,
    log_dir: str = None,
):
    """
    Performs final data cleaning.

    Note:
        - After this step, all JLAC10 codes becomes the method-agnostic form (e.g., 5E0560000001---11).

    Args:
        source_dir (str): Path to the directory containing source data cleaned by :meth:`ssmixtools.cleaning.optional.step2`.
        reference_dir (str): Path to the directory containing reference mapping files for cleaning.
        max_workers (int, optional): Maximum number of workers for parallel processing. Defaults to the number of physical CPU cores minus 1.
        log_dir (str, optional): Directory for saving log files. Defaults to None.

    Returns:
        None

    **Example Usage**

        .. code-block:: python

            import ssmixtools

            ssmixtools.cleaning.optional.step3(
                source_dir='/path/to/source/data',
                reference_dir='/path/to/reference/mapping/files',
                max_workers=None,
                log_dir='/path/to/log/dir',
            )


    **Workflow**

        1. **Standardized Code Validation**:
            - Validates and cleans standardized codes (ICD-10, ATC, and JLAC10).
            - Removes missing or irregular codes, truncates excessively long codes, and ensures consistency using regular expressions.

        2. **Handling Missing Values**:
            - Drops records with missing values in critical columns.
    """

    # Debugging config
    debug_flag = os.environ.get("DEBUG_MODE")
    test = debug_flag == "1"
    test_chunks = 2 if test else 0
    with LogRedirector(log_dir=log_dir, file_name=None):
        # Create a temp dir in the parent directory of source_dir
        with tempfile.TemporaryDirectory(dir=source_dir) as temp_dir:
            # Initialize
            initialized = initialize_cleaning(
                source_dir=source_dir,
                output_dir=source_dir,
                reference_dir=reference_dir,
                max_workers=max_workers,
                test=test,
                test_chunks=test_chunks,
                internal_dir=temp_dir,
            )
            if initialized:
                print("Cleaning data...")
                perform_final_data_cleaning()
                move_internal_files()
                print("All processes completed.")
            else:
                print("Initialization for cleaning failed.")


def step4(
    source_dir: str,
    reference_dir: str,
    max_workers: int = None,
    log_dir: str = None,
):
    """
    Translates clinical codes into English terms.

    This step translates standardized clinical codes (e.g., ICD-10, ATC, JLAC10) into their corresponding English terms using reference mapping tables.

    Note:
        - Ensure that you have prepared ICD10_to_text.csv and ATC_to_text.csv in `reference_dir`.
        - A new column `local_item_name` is created, and the original item names before translation are copied in this column.
        - Untranslated codes are logged for manual review.
        - A reference table to map JLAC10 codes to English terms is generated to facilitate method-agnostic mapping.

    Args:
        source_dir (str): Path to the directory containing source data cleaned by :meth:`ssmixtools.cleaning.optional.step3`.
        reference_dir (str): Path to the directory containing reference mapping files for code translation.
        max_workers (int, optional): Maximum number of workers for parallel processing. Defaults to the number of physical CPU cores minus 1.
        log_dir (str, optional): Directory for saving log files. If None, logs are printed to the console.

    Returns:
        None

    **Example Usage**

        .. code-block:: python

            import ssmixtools

            ssmixtools.cleaning.optional.step4(
                source_dir='/path/to/source/data',
                reference_dir='/path/to/reference/mapping/files',
                max_workers=None,
                log_dir='/path/to/log/dir',
            )
    """

    # Debugging config
    debug_flag = os.environ.get("DEBUG_MODE")
    test = debug_flag == "1"
    test_chunks = 2 if test else 0

    with LogRedirector(log_dir=log_dir, file_name=None):
        # Create a temp dir in the parent directory of source_dir
        with tempfile.TemporaryDirectory(dir=source_dir) as temp_dir:
            # Initialize
            initialized = initialize_cleaning(
                source_dir=source_dir,
                output_dir=source_dir,
                reference_dir=reference_dir,
                max_workers=max_workers,
                test=test,
                test_chunks=test_chunks,
                internal_dir=temp_dir,
            )
            if initialized:
                print("Translating codes...")
                translate_codes()
                move_internal_files()
                print("All processes completed.")
            else:
                print("Initialization for cleaning failed.")
