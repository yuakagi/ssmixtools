"""Module to map HOT codes to YJ codes"""

from pandas import DataFrame
from ..table_render_utils import (
    load_hot_tables,
    aggregate_source_tables,
    clean_and_inspect_mapping_table,
    save_table,
    save_analytics,
)
from .....generals import general_config as config


def create_hot7_to_yj7_table(output_dir: str, medis_hot_tables: list[DataFrame] = None):
    """Create a table to map HOT7 codes to YJ7 codes.

    Args:
        output_dir (str): Directory for saving the output.
        medis_hot_tables (list[DataFrame]): Tables for HOT codes released by MEDIS.
            This list can be created using 'load_hot_tables()'.
            Default is none, and this function loads the tables on its own.
    """
    # Define variables
    original_code_system = "HOT7"
    target_code_system = "YJ7"
    original_col = "基準番号(HOTコード)"
    target_col = "個別医薬品コード"
    secondary_target_col = "薬価基準収載医薬品コード"
    text_col = "告示名称"
    columns_used = [original_col, target_col, secondary_target_col, text_col]

    # Define the source table iterator
    if medis_hot_tables is None:
        valid_df, deleted_df = load_hot_tables()
        medis_hot_tables = [valid_df, deleted_df]

    # Aggregate the source tables
    mapping_table = aggregate_source_tables(
        tables=medis_hot_tables,
        columns_used=columns_used,
        original_col=original_col,
        target_col=target_col,
        secondary_target_col=secondary_target_col,
        cropped_cols=[original_col, target_col, secondary_target_col],
        cropped_lengths=[7, 7, 7],
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
