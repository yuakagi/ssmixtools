"""Module to map ATC codes with an optional map."""

import os
import json
import pandas as pd
from ...cleaning_settings import get_cln_settings
from ...cleaning_utils import (
    map_text_to_atc,
    load_mapping_table,
    parallel_map_partitions_cln,
)
from .....generals import general_config as config
from .....generals.general_utils import tally_stats


def _map_omp_02_optional(
    df: pd.DataFrame,
    text_to_atc: pd.DataFrame,
) -> tuple:
    """
    Helper function to map plain-text drug names to ATC codes using an optionally created text-to-ATC mapping table.

    Args:
        df (pd.DataFrame): Dataframe to be processed.
        text_to_atc (pd.DataFrame): Mapping table to map plain text names of medications to
            ATC codes.
    Returns:
        df (pd.DataFrame): Processed dataframe containing mapped ATC codes in a new column.
        process_analytics (dict): Result of code mapping inspection.
    """

    df, process_analytics = map_text_to_atc(df, text_to_atc)

    return df, process_analytics


def map_omp_02_optional():
    """
    Maps plain-text drug names to ATC codes using an optional mapping table using an optionally created text-to-ATC mapping table.
    The mapped OMP-02 tables are saved during this process, and process analytics are saved as a JSON file.
    See '_map_omp_02_optional' for details.
    """
    # Initialize variables
    source_tables_dir = get_cln_settings("CLN_OUTPUT_TABLES_DIR")
    internal_dir = get_cln_settings("CLN_INTERNAL_DIR")
    mapping_sheet_pattern = get_cln_settings("CLN_MAPPING_SHEET_PTN")
    data_type = "OMP-02"
    file_name_pattern = config.RECORD_TABLE_PARAMS[data_type]["file_name_pattern"]
    csv_path_pattern = os.path.join(source_tables_dir, "**", file_name_pattern)
    output_csv_path = os.path.join(internal_dir, file_name_pattern)
    json_path = mapping_sheet_pattern.replace("*", f"{data_type}_optional")
    single_file = config.SINGLE_FILE[data_type]

    # Load mapping tables.
    text_to_atc = load_mapping_table(
        original_code_system="text",
        target_code_system=config.ATC,
        prefix="optional",
        original_col_idx=0,
        target_col_idx=2,
        preprocess_drug_names=True,
    )

    # Execute the helper function
    stats_list = parallel_map_partitions_cln(
        csv_path_pattern=csv_path_pattern,
        function=_map_omp_02_optional,
        output_csv_path=output_csv_path,
        chunksize=-1,
        single_file=single_file,
        single_stat_file=False,
        text_to_atc=text_to_atc,
    )
    process_analytics = tally_stats(stats_list)

    # Save the mapping results as JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(process_analytics, f, indent=2, ensure_ascii=False)
