"""Module to map codes in OMP-02 records"""

import os
import json
import pandas as pd
from ...cleaning_settings import get_cln_settings
from ...cleaning_utils import (
    load_mapping_table,
    map_by_merge,
    backup_fill_from_secondary_code,
    parallel_map_partitions_cln,
    clean_drug_names,
)
from .....generals import general_config as config
from .....generals.general_utils import tally_stats, all_values_to_int


def _map_omp_02(
    df: pd.DataFrame,
    hot7_to_yj7: pd.DataFrame,
    text_to_yj7: pd.DataFrame,
    yj7_to_atc: pd.DataFrame,
    hot7_to_atc: pd.DataFrame,
    text_to_atc: pd.DataFrame,
) -> tuple:
    """Maps Japanese domestic medication codes (HOT and YJ codes) to ATC codes.

    This process inspects irregular codes, such as those not mappable to ATC codes, and records the results in a dictionary.

    Args:
        df (pd.DataFrame): Dataframe to be processed.
        hot7_to_yj7 (pd.DataFrame): Mapping table to map first seven characters of HOT codes to
            those of YJ codes.
        text_to_yj7 (pd.DataFrame): Mapping table to map plain text names of medications to
            YJ codes.
        yj7_to_atc (pd.DataFrame): Mapping table to map first seven characters of YJ codes to
            ATC codes.
        hot7_to_atc (pd.DataFrame): Mapping table to map first seven characters of HOT codes to
            those of ATC codes.
        text_to_atc (pd.DataFrame): Mapping table to map plain text names of medications to
            ATC codes.
    Returns:
        df (pd.DataFrame): Dataframe with a new column of ATC codes.
        process_analytics (dict): Result of code mapping inspection.
    """
    # Initialize
    process_analytics = {}
    original_text_cols = ["primary_component_text", "secondary_component_text"]
    cropped_text_cols = [
        "cropped_primary_component_text",
        "cropped_secondary_component_text",
    ]

    # Crop text product names for text-to-code mapping
    for cropped_col, original_col in zip(cropped_text_cols, original_text_cols):
        df[cropped_col] = clean_drug_names(df[original_col])

    # Create a new column 'YJ7' by mapping HOT to YJ7
    df = map_by_merge(
        df,
        hot7_to_yj7,
        original_code_col="primary_component_code",
        original_cropped_length=7,
        original_code_pattern=config.R_HOT_CODE,
        original_system_col="primary_component_coding_system",
        original_system_pattern=config.R_HOT,
        new_col_name="mapped_yj7",
    )

    # Fill missing 'YJ7' column values with 'secondary component code'.
    df["mapped_yj7"] = backup_fill_from_secondary_code(
        df,
        target_col="mapped_yj7",
        secondary_code_col="secondary_component_code",
        secondary_coding_system_col="secondary_component_coding_system",
        standardized_code_pattern=config.R_YJ_OR_MYAK_CODE,
        standardized_code_system_pattern=config.R_YJ_OR_MYAK,
        secondary_cropped_length=7,
    )

    # Try to fill still missing 'YJ7' with text-to-code mapping
    for cropped_text_col in cropped_text_cols:
        df = map_by_merge(
            df,
            text_to_yj7,
            original_code_col=cropped_text_col,
            new_col_name="yj7_by_text",
        )
        df["mapped_yj7"] = backup_fill_from_secondary_code(
            df,
            target_col="mapped_yj7",
            secondary_code_col="yj7_by_text",
        )
        df = df.drop("yj7_by_text", axis=1)

    # Create a new column 'ATC' by mapping YJ7 to ATC
    df = map_by_merge(
        df,
        yj7_to_atc,
        new_col_name=config.COL_ITEM_CODE,
        original_code_col="mapped_yj7",
        original_cropped_length=7,
    )
    df = df.drop("mapped_yj7", axis=1)

    # Create a new column 'backup ATC' by mapping HOT7 to ATC
    df = map_by_merge(
        df,
        hot7_to_atc,
        original_code_col="primary_component_code",
        original_cropped_length=7,
        new_col_name="backup_atc",
        original_code_pattern=config.R_HOT_CODE,
        original_system_col="primary_component_coding_system",
        original_system_pattern=config.R_HOT,
    )

    # Fill missing 'ATC' column values with 'backup ATC'.
    df[config.COL_ITEM_CODE] = backup_fill_from_secondary_code(
        df,
        target_col=config.COL_ITEM_CODE,
        secondary_code_col="backup_atc",
    )
    df = df.drop("backup_atc", axis=1)

    # Try to fill still missing 'ATC' with text-to-code mapping
    for cropped_text_col in cropped_text_cols:
        df = map_by_merge(
            df,
            text_to_atc,
            original_code_col=cropped_text_col,
            new_col_name="atc_by_text",
        )
        df[config.COL_ITEM_CODE] = backup_fill_from_secondary_code(
            df,
            target_col=config.COL_ITEM_CODE,
            secondary_code_col="atc_by_text",
        )
        df = df.drop("atc_by_text", axis=1)
    df = df.drop(cropped_text_cols, axis=1)

    # Clean data while inspecting data.
    irregular_atc_mask = ~(
        df[config.COL_ITEM_CODE].str.contains(config.R_ATC_CODE, na=True)
    )
    missing_atc_mask = df[config.COL_ITEM_CODE].isna()
    hot_existing_mask = df["primary_component_coding_system"].str.contains(
        config.R_HOT, na=False
    ) & ~(df["primary_component_code"].isna())
    unmappable_hot_mask = hot_existing_mask & missing_atc_mask

    total_rows = len(df)
    n_irregular_atc = int(irregular_atc_mask.sum())
    n_missing_atc = int(missing_atc_mask.sum())
    n_regular_atc = total_rows - (n_missing_atc + n_irregular_atc)
    n_unmappable_hot = int(unmappable_hot_mask.sum())
    n_missing_hot = int((~hot_existing_mask).sum())
    irregular_atc_counts = all_values_to_int(
        df[irregular_atc_mask][config.COL_ITEM_CODE].value_counts().to_dict()
    )
    unmappable_hot_counts = all_values_to_int(
        df[unmappable_hot_mask]["primary_component_code"].value_counts().to_dict()
    )
    all_unmappables = all_values_to_int(
        df[missing_atc_mask | irregular_atc_mask]["primary_component_text"]
        .value_counts()
        .to_dict()
    )

    # Saving analytics to the dictionary
    process_analytics["records before cleaning"] = total_rows
    process_analytics["properly mapped records"] = n_regular_atc
    process_analytics["Irregular ATC codes after mapping"] = n_irregular_atc
    process_analytics["missing ATC after mapping"] = n_missing_atc
    process_analytics["unmappable HOT"] = n_unmappable_hot
    process_analytics["missing HOT"] = n_missing_hot
    process_analytics["irregular ATC code counts"] = irregular_atc_counts
    process_analytics["unmappable HOT code counts"] = unmappable_hot_counts
    process_analytics["unmappable items in text"] = all_unmappables

    return df, process_analytics


def map_omp_02():
    """Maps injectable medication orders in OMP-02 tables to ATC codes.
    See the helper function '_map_omp_02' for the processing details.
    Analytical data are saved as a JSON file at the end.
    """
    source_dir = get_cln_settings("CLN_SOURCE_DIR")
    internal_dir = get_cln_settings("CLN_INTERNAL_DIR")
    mapping_sheet_pattern = get_cln_settings("CLN_MAPPING_SHEET_PTN")
    data_type = "OMP-02"
    csv_path_pattern = os.path.join(source_dir, "**", f"{data_type}_*.csv")
    output_csv_path = os.path.join(internal_dir, config.INJECTION_ORDER_TABLE_PATTERN)
    json_path = mapping_sheet_pattern.replace("*", data_type)
    single_file = config.SINGLE_FILE[data_type]

    # Load mapping tables.
    hot7_to_yj7 = load_mapping_table(
        original_code_system="HOT7", target_code_system="YJ7"
    )
    text_to_yj7 = load_mapping_table(
        original_code_system="text",
        target_code_system="YJ7",
        preprocess_drug_names=True,
    )
    yj7_to_atc = load_mapping_table(
        original_code_system="YJ7", target_code_system=config.ATC
    )
    hot7_to_atc = load_mapping_table(
        original_code_system="HOT7", target_code_system=config.ATC
    )
    text_to_atc = load_mapping_table(
        original_code_system="text",
        target_code_system=config.ATC,
        preprocess_drug_names=True,
    )

    # Execute the helper function
    stats_list = parallel_map_partitions_cln(
        csv_path_pattern=csv_path_pattern,
        function=_map_omp_02,
        output_csv_path=output_csv_path,
        chunksize=-1,
        single_file=single_file,
        single_stat_file=False,
        hot7_to_yj7=hot7_to_yj7,
        text_to_yj7=text_to_yj7,
        yj7_to_atc=yj7_to_atc,
        hot7_to_atc=hot7_to_atc,
        text_to_atc=text_to_atc,
    )
    process_analytics = tally_stats(stats_list)

    # Save the mapping results as JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(process_analytics, f, indent=2, ensure_ascii=False)
