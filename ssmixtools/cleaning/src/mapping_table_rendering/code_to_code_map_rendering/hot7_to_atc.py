"""Module to create a table that maps HOT7 to ATC"""

from pandas import DataFrame
from ..table_render_utils import (
    aggregate_source_tables,
    clean_and_inspect_mapping_table,
    save_table,
    save_analytics,
)
from .....generals import general_config as config


def create_hot7_to_atc_table(
    output_dir: str,
    atc_tables: list[DataFrame],
):
    """Creates a table to map HOT7 to ATC.

    Args:
        output_dir (str): Directory for saving the output.
        atc_tables (list[DataFrame]): Tables for ATC code mapping.
            This list can be created using 'load_atc_tables()'.
    """
    # Define variables
    original_code_system = "HOT7"
    target_code_system = "ATC"
    original_col = "HOT番号"
    target_col = "ATC7"
    secondary_target_col = "ATC5"
    text_col = "商品名"
    columns_used = [original_col, target_col, secondary_target_col, text_col]

    # Collecet and process tables
    mapping_table = aggregate_source_tables(
        tables=atc_tables,
        columns_used=columns_used,
        original_col=original_col,
        target_col=target_col,
        secondary_target_col=secondary_target_col,
        cropped_cols=[original_col],
        cropped_lengths=[7],
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
