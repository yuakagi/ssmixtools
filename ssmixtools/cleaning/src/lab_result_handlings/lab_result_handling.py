"""Module to clean lab values"""

from .lab_result_functions import (
    create_jlac10_cleaning_table,
    extract_units_and_nonnumerics,
    clean_units_and_nonnumerics,
)
from ..cleaning_settings import get_cln_settings
from ....generals.general_utils import function_wrapper


def create_jlac10_cleaning_ref():
    """Creates a reference table for inspection of JLAC10 codes."""
    # Define parameters
    functions = [create_jlac10_cleaning_table]
    descriptions = [
        "Create table for JLAC10 optional inspection",
    ]
    for function, description in zip(functions, descriptions):
        function_wrapper(
            function=function,
            section_description="JLAC10 inspection table creation",
            step_description=description,
            file_path=get_cln_settings("CLN_PERFORMANCE_PTH"),
        )


def extract_unique_lab_values():
    """Extracts unique units for numeric test results, and unique nonnumeric test result values."""
    # Define parameters
    functions = [extract_units_and_nonnumerics]
    descriptions = [
        "Extract unique units and nonnumeric values from laboratory results",
    ]
    for function, description in zip(functions, descriptions):
        function_wrapper(
            function=function,
            section_description="Unique laboratory value extraction",
            step_description=description,
            file_path=get_cln_settings("CLN_PERFORMANCE_PTH"),
        )


def clean_lab_values():
    """Cleans laboratory value units and nonnumeric values."""
    # Define parameters
    functions = [
        clean_units_and_nonnumerics,
    ]
    descriptions = [
        "clean units and nonnumeric values",
    ]

    for function, description in zip(functions, descriptions):
        function_wrapper(
            function=function,
            section_description="Cleaning lab values",
            step_description=description,
            file_path=get_cln_settings("CLN_PERFORMANCE_PTH"),
        )
