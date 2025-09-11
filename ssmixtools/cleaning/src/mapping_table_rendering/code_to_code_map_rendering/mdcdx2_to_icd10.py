"""Module to map MDCDX2 to ICD-10"""

from pandas import DataFrame
from ..table_render_utils import (
    load_dx_tables,
    aggregate_source_tables,
    clean_and_inspect_mapping_table,
    save_table,
    save_analytics,
)
from .....generals import general_config as config


def create_mdcdx2_to_icd10_table(
    output_dir: str, medis_dx_tables: list[DataFrame] = None
):
    """Create a table to map MDCDX2 codes to ICD-10 codes.

    Args:
        output_dir (str): Directory for saving the output.
        medis_dx_tables (list[DataFrame]): Tables for diagnosis codes released by MEDIS.
            This list can be created using the iterator 'load_dx_tables()'.
            Default is none, and this function loads the tables on its own.
    """
    # Define variables
    original_code_system = "MDCDX2"
    target_code_system = "ICD10"
    original_col = "病名管理番号"
    target_col = "ICD10-2013"
    text_col = "病名表記"
    columns_used = [original_col, target_col, text_col]

    # Define the source-table iterator
    if medis_dx_tables is None:
        medis_dx_tables = load_dx_tables()

    # Aggregate source tables
    mapping_table = aggregate_source_tables(
        tables=medis_dx_tables,
        columns_used=columns_used,
        original_col=original_col,
        target_col=target_col,
    )

    # Sort and clean the table
    mapping_table, process_analytics = clean_and_inspect_mapping_table(
        mapping_table,
        original_col=original_col,
        target_col=target_col,
        text_col=text_col,
    )

    # Save the map
    final_cols = [config.COL_ORIGINAL, config.COL_TARGET, "text"]
    save_table(
        mapping_table,
        output_dir,
        original_code_system,
        target_code_system,
        columns=final_cols,
    )

    # Save the analytic sheet
    save_analytics(
        process_analytics, output_dir, original_code_system, target_code_system
    )
