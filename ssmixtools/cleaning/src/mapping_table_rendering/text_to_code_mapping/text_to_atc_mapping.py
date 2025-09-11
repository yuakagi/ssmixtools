"""Module to map drug names to ATC codes"""

from pandas import DataFrame
from ..table_render_utils import (
    aggregate_source_tables,
    clean_and_inspect_mapping_table,
    save_table,
    save_analytics,
)
from .....generals import general_config as config


def create_text_to_atc_table(output_dir: str, atc_tables: list[DataFrame]):
    """Creates a table to map drug names to ATC codes.

    Args:
        output_dir (str): Directory for saving the output.
        atc_tables (list[DataFrame]): Tables for ATC code mapping.
            This list can be created using 'load_atc_tables()'.
    """
    # Define variables
    original_code_system = "text"
    target_code_system = "ATC"
    text_col = "商品名"
    target_col = "ATC7"
    secondary_target_col = "ATC5"
    columns_used = [text_col, target_col, secondary_target_col]

    # Initialize a dataframe
    mapping_table = aggregate_source_tables(
        tables=atc_tables,
        columns_used=columns_used,
        original_col=text_col,
        target_col=target_col,
        secondary_target_col=secondary_target_col,
    )

    # Sort and clean the table
    mapping_table, process_analytics = clean_and_inspect_mapping_table(
        mapping_table,
        original_col=text_col,
        target_col=target_col,
    )

    # Save the map
    save_table(
        mapping_table,
        output_dir,
        original_code_system,
        target_code_system,
        columns=[config.COL_ORIGINAL, config.COL_TARGET],
    )

    # Save the analytic sheet
    save_analytics(
        process_analytics, output_dir, original_code_system, target_code_system
    )
