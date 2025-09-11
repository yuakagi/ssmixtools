import os
import json
import pandas as pd
from ...cleaning_settings import get_cln_settings
from ...cleaning_utils import (
    load_mapping_table,
    parallel_map_partitions_cln,
    map_text_to_atc,
)
from .....generals import general_config as config
from .....generals.general_utils import tally_stats, archive_file


def _map_omp_01_generic(
    df: pd.DataFrame,
    text_to_atc: pd.DataFrame,
) -> tuple:
    """Maps drug names in plain text to ATC codes using a generic text-to-ATC mapping table.

    Args:
        df (pd.DataFrame): DataFrame containing drug names to process.
        text_to_atc (pd.DataFrame): Mapping table for converting drug names to ATC codes.

    Returns:
        tuple:
            - pd.DataFrame: Updated DataFrame with a new column for ATC codes.
            - dict: Dictionary summarizing mapping results and analytics.
    """

    df, process_analytics = map_text_to_atc(df, text_to_atc)

    return df, process_analytics


def map_omp_01_generic():
    """Maps drug names in OMP-01 tables to ATC codes using a generic text-to-ATC mapping table.

    This function processes OMP-01 data to map drug names in plain text to ATC codes.
    The results include cleaned data saved as a CSV file and process analytics saved
    as a JSON file.

    See `_map_omp_01_generic` for details.

    Args:
        None

    Returns:
        None: Saves the processed data and analytics as files.
    """

    # Initialize variables
    internal_dir = get_cln_settings("CLN_INTERNAL_DIR")
    mapping_sheet_pattern = get_cln_settings("CLN_MAPPING_SHEET_PTN")
    optional_map_pattern = get_cln_settings("CLN_OPTIONAL_MAP_PTN")
    data_type = "OMP-01"
    csv_path_pattern = os.path.join(
        internal_dir, config.PRESCRIPTION_ORDER_TABLE_PATTERN
    )
    output_csv_path = os.path.join(
        internal_dir, config.PRESCRIPTION_ORDER_TABLE_PATTERN
    )
    json_path = mapping_sheet_pattern.replace("*", f"{data_type}_generic")
    single_file = config.SINGLE_FILE[data_type]

    # Load mapping tables.
    text_to_atc = load_mapping_table(
        original_code_system="text",
        target_code_system=config.ATC,
        prefix="generic",
        preprocess_drug_names=True,
    )

    # Execute the helper function
    stats_list = parallel_map_partitions_cln(
        csv_path_pattern=csv_path_pattern,
        function=_map_omp_01_generic,
        output_csv_path=output_csv_path,
        chunksize=-1,
        single_file=single_file,
        single_stat_file=False,
        text_to_atc=text_to_atc,
    )
    process_analytics = tally_stats(stats_list)

    # Create a mapping template table for optional text-to-ATC mapping table creation
    missing_atc_counts_chunks = []
    for v in process_analytics.values():
        missing_atc_counts_chunks.append(v["drug_names_with_missing_ATC_codes"])
    missing_atc_counts = tally_stats(missing_atc_counts_chunks)
    missing_atc_counts_df = pd.DataFrame(
        {"text": missing_atc_counts.keys(), "counts": missing_atc_counts.values()}
    )
    missing_atc_counts_df[config.COL_ATC] = ""
    missing_text_mask = missing_atc_counts_df["text"].replace("", None).isna()
    missing_atc_counts_df = missing_atc_counts_df[~missing_text_mask]
    missing_atc_counts_df = missing_atc_counts_df.sort_values("counts", ascending=False)
    missing_atc_output_path = optional_map_pattern.replace("*", "text_to_ATC")
    if os.path.exists(missing_atc_output_path):
        archive_file(missing_atc_output_path)
    missing_atc_counts_df.to_csv(missing_atc_output_path, header=True, index=False)

    # Save the mapping results as JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(process_analytics, f, indent=2, ensure_ascii=False)
