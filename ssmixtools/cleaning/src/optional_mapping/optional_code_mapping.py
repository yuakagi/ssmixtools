from .optional_mapping_function import (
    map_omp_01_optional,
    map_omp_02_optional,
    map_oml_11_optional,
    map_code_to_text,
)
from ..cleaning_settings import get_cln_settings
from ....generals.general_utils import function_wrapper


def map_data_with_optional_maps():
    """Maps data with optionally created maps"""
    functions = [map_omp_01_optional, map_omp_02_optional, map_oml_11_optional]
    descriptions = [
        "map OMP-01 with an optionally created map",
        "map OMP-02 with an optionally created map",
        "map OML-11 with an optionally created map",
    ]

    for function, description in zip(functions, descriptions):
        function_wrapper(
            function=function,
            section_description="Optional data mapping",
            step_description=description,
            file_path=get_cln_settings("CLN_PERFORMANCE_PTH"),
        )


def translate_codes():
    """Maps standardized codes such as ICD-10 and ATC to English terms"""
    functions = [map_code_to_text]
    descriptions = ["map codes to English terms"]

    for function, description in zip(functions, descriptions):
        function_wrapper(
            function=function,
            section_description="Code translation",
            step_description=description,
            file_path=get_cln_settings("CLN_PERFORMANCE_PTH"),
        )
