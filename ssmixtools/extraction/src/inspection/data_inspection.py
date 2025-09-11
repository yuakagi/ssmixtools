"""The main module for data inspection"""

from .inspection_functions import (
    inspect_ppr_01,
    inspect_omp_01,
    inspect_omp_02,
    inspect_oml_11,
    inspect_adt_12,
    inspect_adt_22,
    inspect_adt_52,
)

from ..extraction_settings import get_ext_settings
from ....generals.general_utils import function_wrapper


def inspect_data():
    """Inspects extracted records individually by data types.
    Inspection protocols are customized to each data type. See each function docstring for details.
    This inspection process generally checks missing values, standardization compliance, irregular values, and timestamp variations.
    Inspection results are saved as a JSON file by data types.

    """
    functions = [
        inspect_adt_12,
        inspect_adt_22,
        inspect_adt_52,
        inspect_ppr_01,
        inspect_omp_01,
        inspect_omp_02,
        inspect_oml_11,
    ]
    descriptions = [
        "inspect ADT-12",
        "inspect ADT-22",
        "inspect ADT-52",
        "inspect PPR-01",
        "inspect OMP-01",
        "inspect OMP-02",
        "inspect OML-11",
    ]

    for function, description in zip(functions, descriptions):
        function_wrapper(
            function=function,
            section_description="Data inspection",
            step_description=description,
            file_path=get_ext_settings("EXT_PERFORMANCE_PTH"),
        )

    print("Inspection done.")
