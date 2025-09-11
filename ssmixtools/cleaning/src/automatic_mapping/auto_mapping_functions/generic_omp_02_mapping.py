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


def _map_omp_02_generic(
    df: pd.DataFrame,
    text_to_atc: pd.DataFrame,
) -> tuple:
    """
    Maps drug names in plain text to ATC codes using a generic text-to-ATC mapping table.

    Args:
        df (pd.DataFrame): Dataframe to be processed.
        text_to_atc (pd.DataFrame): Mapping table to map plain text names of medications to
            ATC codes.
    Returns:
        df (pd.DataFrame): Dataframe with a new column of ATC codes.
        process_analytics (dict): Result of code mapping inspection.
    """
    df, process_analytics = map_text_to_atc(df, text_to_atc)

    return df, process_analytics


def map_omp_02_generic():
    """
    This function maps drug names in plain texts to ATC codes using a generic text-to-ATC mapping table.
    During this process, additionally mapped OMP-02 tables are saved, and process analytics are also saved as a JSON file.
    See '_map_omp_02_generic' for details.
    """
    # Initialize variables
    internal_dir = get_cln_settings("CLN_INTERNAL_DIR")
    mapping_sheet_pattern = get_cln_settings("CLN_MAPPING_SHEET_PTN")
    optional_map_pattern = get_cln_settings("CLN_OPTIONAL_MAP_PTN")
    data_type = "OMP-02"
    csv_path_pattern = os.path.join(internal_dir, config.INJECTION_ORDER_TABLE_PATTERN)
    output_csv_path = os.path.join(internal_dir, config.INJECTION_ORDER_TABLE_PATTERN)
    json_path = mapping_sheet_pattern.replace("*", f"{data_type}_generic")
    single_file = config.SINGLE_FILE[data_type]

    # Load mapping tables.
    text_to_atc = load_mapping_table(
        original_code_system="text",
        target_code_system=config.ATC,
        prefix="generic",
    )

    # Execute the helper function
    stats_list = parallel_map_partitions_cln(
        csv_path_pattern=csv_path_pattern,
        function=_map_omp_02_generic,
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
        {
            "text": missing_atc_counts.keys(),
            "counts": missing_atc_counts.values(),
        }
    )
    missing_atc_counts_df[config.COL_ATC] = ""
    missing_text_mask = missing_atc_counts_df["text"].replace("", None).isna()
    missing_atc_counts_df = missing_atc_counts_df[~missing_text_mask]
    missing_atc_output_path = optional_map_pattern.replace("*", "text_to_ATC")
    if os.path.exists(missing_atc_output_path):
        existing_table_from_oml_01 = pd.read_csv(
            missing_atc_output_path,
            header=0,
            dtype={"text": str, config.COL_ATC: str, "counts": int},
            na_values=config.NA_VALUES,
        )
        missing_atc_counts_df = pd.concat(
            [missing_atc_counts_df, existing_table_from_oml_01]
        )
    missing_atc_counts_df = missing_atc_counts_df.sort_values("counts", ascending=False)
    missing_atc_counts_df.to_csv(missing_atc_output_path, header=True, index=False)

    # Save the mapping results as JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(process_analytics, f, indent=2, ensure_ascii=False)
