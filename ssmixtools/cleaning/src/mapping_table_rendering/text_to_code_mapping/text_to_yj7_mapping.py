"""Module to map drug names to YJ codes"""

import pandas as pd
from .....generals import general_config as config
from ..table_render_utils import (
    load_hot_tables,
    aggregate_source_tables,
    clean_and_inspect_mapping_table,
    save_table,
    save_analytics,
)


def create_text_to_yj7_table(
    output_dir: str,
    atc_tables: list[pd.DataFrame],
    medis_hot_tables: list[pd.DataFrame] = None,
):
    """Creates a table to map drug names to YJ7

    Args:
        output_dir (str): Directory for saving the output.
        atc_tables (list[DataFrame]): Tables for ATC code mapping.
            This list can be created using 'load_atc_tables()'.
        medis_hot_tables (list[DataFrame]): Tables for HOT codes released by MEDIS.
            This list can be created using 'load_hot_tables()'.
            Default is none, and this function loads the tables on its own.
    """
    # Variables
    original_code_system = "text"
    target_code_system = "YJ7"

    # Define the table iterator
    if medis_hot_tables is None:
        medis_hot_tables = load_hot_tables()

    # Create a dictionary of arguments for 'aggregate_source_tables'
    params = [
        {
            "tables": medis_hot_tables,
            "columns_used": [
                "告示名称",
                "個別医薬品コード",
                "薬価基準収載医薬品コード",
            ],
            "original_col": "告示名称",
            "target_col": "個別医薬品コード",
            "secondary_target_col": "薬価基準収載医薬品コード",
            "cropped_cols": ["個別医薬品コード", "薬価基準収載医薬品コード"],
            "cropped_lengths": [7, 7],
        },
        {
            "tables": medis_hot_tables,
            "columns_used": [
                "レセプト電算処理システム医薬品名",
                "個別医薬品コード",
                "薬価基準収載医薬品コード",
            ],
            "original_col": "レセプト電算処理システム医薬品名",
            "target_col": "個別医薬品コード",
            "secondary_target_col": "薬価基準収載医薬品コード",
            "cropped_cols": ["個別医薬品コード", "薬価基準収載医薬品コード"],
            "cropped_lengths": [7, 7],
        },
        {
            "tables": atc_tables,
            "columns_used": ["商品名", "YJコード"],
            "original_col": "商品名",
            "target_col": "YJコード",
            "cropped_cols": ["YJコード"],
            "cropped_lengths": [7],
        },
    ]

    # Loop
    aggregated_tables = []
    for param in params:
        table = aggregate_source_tables(**param)
        table = table.rename(
            columns={
                param["original_col"]: config.COL_ORIGINAL,
                param["target_col"]: config.COL_TARGET,
            }
        )
        aggregated_tables.append(table)
    # Concatenate them all
    mapping_table = pd.concat(aggregated_tables)
    mapping_table = mapping_table.drop_duplicates()

    # Inspect
    mapping_table, process_analytics = clean_and_inspect_mapping_table(
        mapping_table,
        original_col=config.COL_ORIGINAL,
        target_col=config.COL_TARGET,
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
