"""
Main Module for Automatic Data Cleaning

This module provides the core functionality for cleaning clinical records extracted
from SS-MIX2 storage. The automatic cleaning process includes rendering mapping tables,
mapping clinical codes to standardized ones, cleaning records, and preparing the dataset
for optional cleaning.
"""

import os
import shutil
import tempfile
from .initialization import initialize_cleaning
from .mapping_table_rendering import render_mapping_tables
from .automatic_mapping import map_codes_auto, map_codes_generic
from .record_cleaning import clean_data
from .lab_result_handlings import create_jlac10_cleaning_ref
from .cleaning_utils import move_internal_files
from .cleaning_settings import get_cln_settings
from ...generals.general_utils import LogRedirector
from ...generals import general_config as config


def render_maps(
    reference_dir: str,
    atc_tables_dir: str,
    log_dir: str = None,
):
    """
    **Renders Mapping Tables for Data Cleaning**

    This function prepares and renders mapping tables required for cleaning clinical data.

    Warnings:
        - **Internet Usage**: This function downloads necessary tables from external sources. Ensure a stable internet connection and review the implications of downloading content from these sources.
        - **Terms of Use**: Tables are sourced from the Medical Information System Development Center (https://www.medis.or.jp/). Users must comply with MEDIS terms of use before proceeding.
        - **ATC Tables Requirement**: This package does not provide ATC-related source tables. Users must prepare these tables themselves. Ensure the prepared tables include mappings from local codes and drug product names to ATC codes. Japan Pharmaceutical Information Center (JAPIC) provides useful resources.
        - **External Dependencies**: The fetches data from external sources. If the structure of these sources changes, the function may fail, and this package needs to be updated accordingly. In this case, please report the issue on GitHub.
        
    Note:
        - Rendered mapping tables are used in subsequent data cleaning processes.

    Args:
        reference_dir (str):
            Directory where the rendered mapping tables will be saved.
        atc_tables_dir (str):
            Directory containing ATC-related source tables. This directory must contain a CSV file named 'info_atc.csv'.
        log_dir (str, optional):
            Directory for saving log files. If `None`, logs are printed to the console.

    Returns:
        None:
            The function saves mapping tables and related analytics in the specified `reference_dir`.


    **Example Usage**

        .. code-block:: python

            render_maps(
                reference_dir="/path/to/reference",
                atc_tables_dir="/path/to/atc/tables",
                log_dir="/path/to/log/dir"
            )
    """

    with LogRedirector(log_dir=log_dir, file_name=None):
        render_mapping_tables(output_dir=reference_dir, atc_tables_dir=atc_tables_dir)
    print("Mapping tables are ready.")


def clean(
    source_dir: str,
    output_dir: str,
    reference_dir: str,
    max_workers: int = None,
    log_dir: str = None,
):
    """
    **Cleans Clinical Records Extracted from SS-MIX2 Storage**

    This function processes clinical records using multiple cleaning steps to standardize
    and validate the dataset for downstream analysis. The cleaning pipeline includes code
    mapping, unit normalization, handling missing values, and ensuring the consistency of
    clinical data formats.

    Note:
        - Detailed process analytics are also saved in `output_dir`.
        - The cleaning process heavily relies on the provided reference tables; ensure they are updated and accurate.

    Args:
        source_dir (str):
            Path to the directory containing source data to be cleaned.
        output_dir (str):
            Path to the directory where cleaned data will be saved.
        reference_dir (str):
            Path to the directory containing reference mapping files.
        max_workers (int, optional):
            Maximum number of workers for parallel processing. Defaults to the number of physical CPU cores minus 1.
        log_dir (str, optional):
            Directory for saving log files. If `None`, logs are printed to the console.

    Returns:
        None:
            The function saves cleaned datasets and analytics in the specified `output_dir`.

    **Example Usage**

        .. code-block:: python

            clean(
                source_dir='/path/to/source/data',
                output_dir='/path/to/cleaned/data',
                reference_dir='/path/to/reference/files',
                max_workers=4,
                log_dir='/path/to/log/dir',
        )

    **Workflow**

        1. **Initialization**:
            - Sets up directories and configurations for cleaning.
        2. **Code Mapping**:
            - Maps local clinical codes to standardized codes using reference tables.
        3. **Laboratory Data Cleaning**:
            - Standardizes units and cleans laboratory data for consistency.
            - Aggregates numerical and non-numerical test results.
    """

    # Debugging config
    debug_flag = os.environ.get("DEBUG_MODE")
    test = debug_flag == "1"
    test_chunks = 2 if test else 0

    with LogRedirector(log_dir=log_dir, file_name=None):
        child_output_dir = os.path.join(output_dir, "cleaned_by_ssmixtools/")
        if not os.path.exists(child_output_dir):
            os.mkdir(child_output_dir)
        with tempfile.TemporaryDirectory(dir=output_dir) as temp_dir:
            # Initialize
            initialized = initialize_cleaning(
                source_dir=source_dir,
                output_dir=child_output_dir,
                reference_dir=reference_dir,
                max_workers=max_workers,
                test=test,
                test_chunks=test_chunks,
                internal_dir=temp_dir,
            )
            if initialized:
                map_codes_auto()
                clean_data()
                map_codes_generic()
                create_jlac10_cleaning_ref()
                move_internal_files()
                # Create copies of DOB mapping tables
                output_tables_dir = get_cln_settings("CLN_OUTPUT_TABLES_DIR")
                for tag in os.listdir(source_dir):
                    src = os.path.join(
                        source_dir,
                        tag,
                        config.DOB_MAP_PATTERN.replace("*", tag),
                    )
                    dst = os.path.join(output_tables_dir, tag, os.path.basename(src))
                    if os.path.exists(dst):
                        temp_dst = dst.replace(".csv", "_new.csv")
                        shutil.copy(src, temp_dst)
                        os.remove(dst)
                        os.rename(temp_dst, dst)
                    else:
                        shutil.copy(src, dst)
                print("The automatic data cleaning is completed.")
                created_ref_dir = get_cln_settings("CLN_CREATED_REF_DIR")
                print(
                    f"Templates for optional code mapping are created in {created_ref_dir}"
                )
                print("Please modify these tables, and go on to the next .")
            else:
                print("Initialization for cleaning failed.")
