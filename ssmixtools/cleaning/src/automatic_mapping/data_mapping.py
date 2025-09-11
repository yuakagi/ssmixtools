from .auto_mapping_functions import (
    map_ppr_01,
    map_omp_01,
    map_omp_02,
    create_generic_text_to_atc,
    map_omp_01_generic,
    map_omp_02_generic,
)
from ..cleaning_settings import get_cln_settings
from ....generals.general_utils import function_wrapper


def map_codes_auto():
    """
    This function maps Japanese domestic medical codes to universal standardized codes.
    Specifically, Japanese domestic medication codes, HOT and YJ codes are mapped to ATC codes.
    Japanese diagnosis codes, MDCDX2, are mapped to ICD-10 codes.
    As of 2023/11/18, there is no mapping scheme to map JLAC10 (Japanese domestic laboratory
    test coding system) to universally accepted coding systems such as LOINC, JLAC10 codes are
    not processed here.
    """
    functions = [map_ppr_01, map_omp_01, map_omp_02]
    descriptions = ["map PPR-01", "map OMP-01", "map OMP-02"]

    for function, description in zip(functions, descriptions):
        function_wrapper(
            function=function,
            section_description="Data mapping",
            step_description=description,
            file_path=get_cln_settings("CLN_PERFORMANCE_PTH"),
        )


def map_codes_generic():
    """Map codes with generic maps"""
    functions = [
        create_generic_text_to_atc,
        map_omp_01_generic,
        map_omp_02_generic,
    ]
    descriptions = [
        "create generic text-to-ATC map",
        "map OMP-01 with a generic map",
        "map OMP-02 with a generic map",
    ]
    for function, description in zip(functions, descriptions):
        function_wrapper(
            function=function,
            file_path=get_cln_settings("CLN_PERFORMANCE_PTH"),
            section_description="Secondary data mapping",
            step_description=description,
        )
