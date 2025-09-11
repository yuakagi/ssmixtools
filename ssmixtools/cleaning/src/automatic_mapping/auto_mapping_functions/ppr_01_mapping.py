"""Module to map codes in PPR-01 records"""

import os
import json
import pandas as pd
from ...cleaning_settings import get_cln_settings
from ...cleaning_utils import (
    load_mapping_table,
    map_by_merge,
    backup_fill_from_secondary_code,
    parallel_map_partitions_cln,
)
from .....generals import general_config as config
from .....generals.general_utils import tally_stats, all_values_to_int


def _map_ppr_01(df: pd.DataFrame, mdcdx2_to_icd10: pd.DataFrame):
    """Maps the Japanese diagnosis codes (MDCDX2) to ICD-10 codes.

    This also inspects irregular codes.

    Args:
        df (pd.DataFrame): Dataframe to be processed.
        mdcdx2_to_icd10 (pd.DataFrame): Mapping table to map MDCDX2 codes to ICD-10 codes.
    Returns:
        df (pd.DataFrame): Dataframe with a new column of ICD-10 codes.
        process_analytics (dict): Result of code mapping inspection.
    """
    # Initialize a dictionary to store analytics
    process_analytics = {}

    # Create a new column 'ICD-10' by mapping MDCDX2 to ICD-10
    df = map_by_merge(
        df,
        mapping_table=mdcdx2_to_icd10,
        original_code_col="primary_diagnosis_code",
        new_col_name=config.COL_ITEM_CODE,
        original_code_pattern=config.R_MDCDX2_CODE,
        original_system_col="primary_diagnosis_coding_system",
        original_system_pattern=config.R_MDCDX2,
    )

    # Filling missing 'ICD-10' column values with 'secondary diagnosis code'.
    df[config.COL_ITEM_CODE] = backup_fill_from_secondary_code(
        df,
        target_col=config.COL_ITEM_CODE,
        secondary_code_col="secondary_diagnosis_code",
        secondary_coding_system_col="secondary_diagnosis_coding_system",
        standardized_code_pattern=config.R_ICD10_CODE,
        standardized_code_system_pattern=config.R_ICD10,
    )

    # Clean data while inspecting data.
    irregular_icd10_mask = ~(
        df[config.COL_ITEM_CODE].str.contains(config.R_ICD10_CODE, na=True)
    )
    missing_icd10_mask = df[config.COL_ITEM_CODE].isna()
    mdcdx2_existing_mask = df["primary_diagnosis_coding_system"].str.contains(
        config.R_MDCDX2, na=False
    ) & ~(df["primary_diagnosis_code"].isna())
    unmappable_mdcdx2_mask = mdcdx2_existing_mask & missing_icd10_mask

    total_rows = len(df)
    n_irregular_icd10 = int(irregular_icd10_mask.sum())
    n_missing_icd10 = int(missing_icd10_mask.sum())
    n_regular_icd10 = total_rows - (n_missing_icd10 + n_irregular_icd10)
    n_unmappable_mdcdx2 = int(unmappable_mdcdx2_mask.sum())
    n_missing_mdcdx2 = int((~mdcdx2_existing_mask).sum())
    irregular_icd10_counts = all_values_to_int(
        df[irregular_icd10_mask][config.COL_ITEM_CODE].value_counts().to_dict()
    )
    unmappable_mdcdx2_counts = all_values_to_int(
        df[unmappable_mdcdx2_mask]["primary_diagnosis_code"].value_counts().to_dict()
    )

    # Saving analytics to the dictionary
    process_analytics["records before cleaning"] = total_rows
    process_analytics["properly mapped records"] = n_regular_icd10
    process_analytics["irregular ICD-10 codes after mapping"] = n_irregular_icd10
    process_analytics["missing ICD-10 after mapping"] = n_missing_icd10
    process_analytics["unmappable MDCDX2"] = n_unmappable_mdcdx2
    process_analytics["missing MDCDX2"] = n_missing_mdcdx2
    process_analytics["irregular ICD-10 code counts"] = irregular_icd10_counts
    process_analytics["unmappable MDCDX2 code counts"] = unmappable_mdcdx2_counts

    return df, process_analytics


def map_ppr_01():
    """Maps diagnosis records in PPR-01 tables to ICD-10 codes.
    See the helper function '_map_ppr_01' for the processing details.
    Analytical data is saved as a JSON file.
    """
    source_dir = get_cln_settings("CLN_SOURCE_DIR")
    internal_dir = get_cln_settings("CLN_INTERNAL_DIR")
    mapping_sheet_pattern = get_cln_settings("CLN_MAPPING_SHEET_PTN")
    data_type = "PPR-01"
    csv_path_pattern = os.path.join(source_dir, "**", f"{data_type}_*.csv")
    output_csv_path = os.path.join(internal_dir, config.DIAGNOSIS_TABLE_PATTERN)
    json_path = mapping_sheet_pattern.replace("*", data_type)
    single_file = config.SINGLE_FILE[data_type]

    # Load mapping tables.
    mdcdx2_to_icd10 = load_mapping_table(
        original_code_system=config.MDCDX2, target_code_system=config.ICD10
    )
    # Execute the helper function
    stats_list = parallel_map_partitions_cln(
        csv_path_pattern=csv_path_pattern,
        function=_map_ppr_01,
        output_csv_path=output_csv_path,
        chunksize=-1,
        single_file=single_file,
        single_stat_file=False,
        mdcdx2_to_icd10=mdcdx2_to_icd10,
    )
    process_analytics = tally_stats(stats_list)

    # Save the mapping results as JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(process_analytics, f, indent=2, ensure_ascii=False)
