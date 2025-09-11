"""The main module for record deidentification"""

from .deidentification_functions import (
    create_dob_map,
    create_deidentified_patient_id_map,
    deidentify_id_and_timestamp,
)
from ..extraction_settings import get_ext_settings
from ....generals.general_utils import function_wrapper
from ....generals import general_config as config


def deidentify_data():
    """Deidentifies patient IDs and timestamps of all records.
    The tables to map patient IDs and DOBs are also created and saved.
    """
    functions = [
        create_deidentified_patient_id_map,
        create_dob_map,
    ]
    descriptions = [
        "create deidentified patient IDs",
        "create deidentified patient ID and DOB pairs",
    ]
    data_types = ["ADT-12", "ADT-22", "ADT-52", "PPR-01", "OMP-01", "OMP-02", "OML-11"]

    # Create maps first.
    for function, description in zip(functions, descriptions):
        function_wrapper(
            function=function,
            section_description="Deidentification",
            step_description=description,
            file_path=get_ext_settings("EXT_PERFORMANCE_PTH"),
        )
    # Deidentify records.
    for data_type in data_types:
        col_names = config.RECORD_TABLE_PARAMS[data_type]
        timestamp_cols = col_names["timestamps"]
        function_wrapper(
            function=deidentify_id_and_timestamp,
            section_description="Deidentification",
            step_description=f"Deidentify {data_type} records",
            file_path=get_ext_settings("EXT_PERFORMANCE_PTH"),
            data_type=data_type,
            timestamp_cols=timestamp_cols,
            single_file=config.SINGLE_FILE[data_type],
        )
