"""The main module for extracting data"""

from .extraction_functions import (
    extract_patient_ids,
    extract_patient_metadata,
    select_patients,
    segregate_paths_by_data_types,
    extract_ppr_01,
    extract_omp_01,
    extract_omp_02,
    extract_oml_11,
    extract_adt_12,
    extract_adt_22,
    extract_adt_52,
)
from ..extraction_settings import get_ext_settings
from ....generals.general_utils import function_wrapper


def extract_records():
    """Extracts records step by step."""
    # Define parameters
    functions = [
        extract_patient_ids,
        extract_patient_metadata,
        select_patients,
        segregate_paths_by_data_types,
        extract_adt_12,
        extract_adt_22,
        extract_adt_52,
        extract_ppr_01,
        extract_omp_01,
        extract_omp_02,
        extract_oml_11,
    ]
    descriptions = [
        "extract all patient IDs",
        "extract patient metadata",
        "select patients",
        "segregate file paths by data types",
        "extract outpatient visit records (ADT-12)",
        "extract admission records (ADT-22)",
        "extract discharge records (ADT-52)",
        "extract diagnostic codes (PPR-01)",
        "extract prescription orders (OMP-01)",
        "extract injection orders (OMP-02)",
        "extract laboratory test results (OML-11)",
    ]

    for function, description in zip(functions, descriptions):
        function_wrapper(
            function=function,
            section_description="Data extraction",
            step_description=description,
            file_path=get_ext_settings("EXT_PERFORMANCE_PTH"),
        )

    print("All records have been parsed.")
