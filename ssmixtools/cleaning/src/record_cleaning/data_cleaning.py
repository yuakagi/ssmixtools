"""Module for record cleaning"""

from .cleaning_functions import (
    clean_demographics,
    clean_adt_12,
    clean_adt_22,
    clean_adt_52,
    clean_ppr_01,
    clean_omp_01,
    clean_omp_02,
    clean_oml_11,
    clean_optional,
)
from ..cleaning_settings import get_cln_settings
from ....generals.general_utils import function_wrapper


def clean_data():
    """Cleans records by data types.

    See each function's docstrings for details.
    """
    functions = [
        clean_demographics,
        clean_adt_12,
        clean_adt_22,
        clean_adt_52,
        clean_ppr_01,
        clean_omp_01,
        clean_omp_02,
        clean_oml_11,
    ]
    descriptions = [
        "clean patient demographic data",
        "clean ADT-12",
        "clean ADT-22",
        "clean ADT-52",
        "clean PPR-01",
        "clean OMP-01",
        "clean OMP-02",
        "clean OML-11",
    ]
    for function, description in zip(functions, descriptions):
        function_wrapper(
            function=function,
            section_description="Data cleaning",
            step_description=description,
            file_path=get_cln_settings("CLN_PERFORMANCE_PTH"),
        )


def perform_final_data_cleaning():
    """Performs final data cleaning."""
    functions = [clean_optional]
    descriptions = ["Perform final data cleaning"]
    for function, description in zip(functions, descriptions):
        function_wrapper(
            function=function,
            section_description="Final data cleaning",
            step_description=description,
            file_path=get_cln_settings("CLN_PERFORMANCE_PTH"),
        )
