"""Module to clean JLAC10 codes with an optional map."""

import os
import json
from typing import Literal
import pandas as pd
from ...cleaning_settings import get_cln_settings
from ...cleaning_utils import (
    parallel_map_partitions_cln,
    load_mapping_table,
    map_icd10_to_text,
    map_atc_to_text,
    map_jlac10_to_text,
)
from ...mapping_table_rendering.table_render_utils import save_table
from .....generals import general_config as config
from .....generals.general_utils import tally_stats


def _map_code_to_text(
    df: pd.DataFrame,
    # pylint: disable=reportInvalidTypeForm
    code_type: Literal[config.ICD10, config.ATC, config.JLAC10],
    mapping_table: pd.DataFrame,
) -> tuple:
    """Helper function to map codes to texts.

    Args:
        df (pd.DataFrame): Dataframe to be processed.
        code_type (Literal[config.ICD10, config.ATC, config.JLAC10]): Type of codes
        mapping_table (pd.DataFrame): Table to map codes.
    Returns:
        df (pd.DataFrame): Dataframe with mapped text for codes.
        process_analytics (dict): Summary of the code mapping process.
    """

    # Initialize
    process_analytics = {}

    # Translate codes
    if code_type == config.ICD10:
        translated = map_icd10_to_text(
            df[config.COL_ITEM_CODE], icd10_to_text=mapping_table
        )
    elif code_type == config.ATC:
        translated = map_atc_to_text(
            df[config.COL_ITEM_CODE], atc_to_text=mapping_table
        )
    elif code_type == config.JLAC10:
        translated = map_jlac10_to_text(
            df[config.COL_ITEM_CODE],
            readable=True,
            japanese=False,
            segments_to_text=mapping_table,
        )
    else:
        raise ValueError("Unknow code type.")

    # Insert the translated texts
    df = df.rename(columns={config.COL_ITEM_NAME: config.COL_ITEM_NAME_LC})
    columns = df.columns.tolist()
    inserted_pos = columns.index(config.COL_ITEM_NAME_LC)
    columns.insert(inserted_pos, config.COL_ITEM_NAME)
    df[config.COL_ITEM_NAME] = translated
    df = df[columns]

    # Stats
    code_exists = ~(df[config.COL_ITEM_CODE].isna() | df[config.COL_ITEM_CODE] == "")
    no_translation = df[config.COL_ITEM_NAME].isna() | (df[config.COL_ITEM_NAME] == "")
    untranslated = code_exists & no_translation
    untranslated_codes = (
        df.loc[untranslated, config.COL_ITEM_CODE].dropna().unique().tolist()
    )

    # Saving analytics to the dictionary
    process_analytics[code_type] = {"untranslated_codes": untranslated_codes}
    # Collect unique codes for JLAC10
    if code_type == config.JLAC10:
        unique_codes = df[config.COL_ITEM_CODE].unique().tolist()
        process_analytics[code_type]["unique_codes"] = unique_codes

    return df, process_analytics


def map_code_to_text():
    """Maps standardized codes (e.g., ICD-10, ATC, JLAC10) to English text descriptions."""
    # Initialize variables
    source_tables_dir = get_cln_settings("CLN_OUTPUT_TABLES_DIR")
    internal_dir = get_cln_settings("CLN_INTERNAL_DIR")
    mapping_sheet_pattern = get_cln_settings("CLN_MAPPING_SHEET_PTN")
    icd10_to_text = load_mapping_table(config.ICD10, "text", target_col_idx=1)
    atc_to_text = load_mapping_table(config.ATC, "text", target_col_idx=1)
    segments_to_text = load_mapping_table("JLAC10_segments", "text", target_col_idx=1)
    mapping_table_dict = {
        config.ICD10: icd10_to_text,
        config.ATC: atc_to_text,
        config.JLAC10: segments_to_text,
    }
    mapping_params = {
        "PPR-01": {
            "code_type": config.ICD10,
            "file_pattern": config.DIAGNOSIS_TABLE_PATTERN,
        },
        "OMP-01": {
            "code_type": config.ATC,
            "file_pattern": config.PRESCRIPTION_ORDER_TABLE_PATTERN,
        },
        "OMP-02": {
            "code_type": config.ATC,
            "file_pattern": config.INJECTION_ORDER_TABLE_PATTERN,
        },
        "OML-11": {
            "code_type": config.JLAC10,
            "file_pattern": config.LAB_RESULT_TABLE_PATTERN,
        },
    }
    all_stats = []
    for data_type, param in mapping_params.items():
        code_type = param["code_type"]
        file_pattern = param["file_pattern"]
        mapping_table = mapping_table_dict[code_type]
        csv_path_pattern = os.path.join(source_tables_dir, "**", file_pattern)
        output_csv_path = os.path.join(internal_dir, file_pattern)
        single_file = config.SINGLE_FILE[data_type]

        # Execute the helper function
        stats_list = parallel_map_partitions_cln(
            csv_path_pattern=csv_path_pattern,
            function=_map_code_to_text,
            output_csv_path=output_csv_path,
            chunksize=-1,
            single_file=single_file,
            single_stat_file=True,
            code_type=code_type,
            mapping_table=mapping_table,
        )
        all_stats += stats_list
    process_analytics = tally_stats(all_stats)

    # Clean the stats
    for code_type in process_analytics:
        process_analytics[code_type]["untranslated_codes"] = sorted(
            list(set(process_analytics[code_type]["untranslated_codes"]))
        )
    # Collect unique JLAC10 codes (method agnostic)
    unique_jlac10s = sorted(list(set(process_analytics[config.JLAC10]["unique_codes"])))
    del process_analytics[config.JLAC10]["unique_codes"]

    # Save the mapping results as JSON
    json_path = mapping_sheet_pattern.replace("*", "code_to_text")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(process_analytics, f, indent=2, ensure_ascii=False)

    # Render a table to map methodagnostic JLAC10 code to text
    jlac10_meth_table = pd.DataFrame({config.COL_ITEM_CODE: unique_jlac10s})
    jlac10_meth_table[config.COL_ITEM_NAME] = map_jlac10_to_text(
        jlac10_meth_table[config.COL_ITEM_CODE],
        readable=True,
        japanese=False,
        segments_to_text=segments_to_text,
    )
    # Save
    jlac10_meth_table = jlac10_meth_table.replace("", None)
    created_ref_dir = get_cln_settings("CLN_CREATED_REF_DIR")
    save_table(
        jlac10_meth_table,
        created_ref_dir,
        "methodagnostic_JLAC10",
        "text",
        columns=[config.COL_ITEM_CODE, config.COL_ITEM_NAME],
    )
