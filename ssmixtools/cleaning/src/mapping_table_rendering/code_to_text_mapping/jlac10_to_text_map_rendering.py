"""Module to map JLAC10 codes to texts"""

import pandas as pd
from ..table_render_utils import (
    load_jlac10_tables,
    common_df_cleaning,
    clean_and_inspect_mapping_table,
    save_table,
    save_analytics,
)
from .....generals import general_config as config


def _common_segment_cleaning(
    table: pd.DataFrame,
) -> tuple[pd.DataFrame, dict]:
    """Performs common cleaning operations to tables for JLAC10 segments."""
    # Fill nan with empty strings
    table = table.fillna("")
    # Fill missing English names with Japanese names.
    missing_en = table["english"] == ""
    table.loc[missing_en, "english"] = "(jp: " + table.loc[missing_en, "japanese"] + ")"
    # Sort and clean
    table, analytics = clean_and_inspect_mapping_table(
        table, original_col="code", target_col="english", sort_by_original=True
    )

    return table, analytics


def _preprocess_jlac10_tables(tables: list[pd.DataFrame]) -> tuple:
    """Performs the common preprocessing steps to JLAC10 tables.
    The tables are the list returned from load_jlac10_tables().
    """
    # Variables
    process_analytics = {}

    # Get the table for the full-length JLAC10 codes
    full_jlac10_table = tables[0]

    # Process code segments for the analytes
    analyte_table = tables[1]
    analyte_table["code"] += "*" * 12
    analyte_table, analytics = _common_segment_cleaning(analyte_table)
    process_analytics["analyte"] = analytics

    # Process code segments for the identifications
    id_table = tables[2]
    id_table["code"] = ("*" * 5) + id_table["code"] + ("*" * 8)
    id_table, analytic = _common_segment_cleaning(id_table)
    process_analytics["identification"] = analytic

    # Process code segments for the specimens
    specimen_table = tables[3]
    specimen_table["code"] = ("*" * 9) + specimen_table["code"] + ("*" * 5)
    specimen_table, analytic = _common_segment_cleaning(specimen_table)
    process_analytics["specimen"] = analytic

    # Process code segments for the methods
    method_table = tables[4]
    method_table["code"] = ("*" * 12) + method_table["code"] + ("*" * 2)
    method_table, analytic = _common_segment_cleaning(method_table)
    process_analytics["methodology"] = analytic

    # Process code segments for the common result identifiers
    common_result_id_table = tables[5]
    common_result_id_table["code"] = ("*" * 15) + common_result_id_table["code"]
    common_result_id_table, analytic = _common_segment_cleaning(common_result_id_table)
    process_analytics["common result identifiers"] = analytic

    # Process code segments for the unique result identifiers
    unique_result_id_table = tables[6]
    unique_result_id_table["code"] = (
        unique_result_id_table["code"].str.slice(0, 9)
        + ("*" * 6)
        + unique_result_id_table["code"].str.slice(9, 11)
    )
    unique_result_id_table, analytic = _common_segment_cleaning(unique_result_id_table)
    process_analytics["unique result identifiers"] = analytic

    # Concatenate segment tables
    segments = [
        analyte_table,
        id_table,
        specimen_table,
        method_table,
        common_result_id_table,
        unique_result_id_table,
    ]
    full_segments_table = pd.concat(segments)
    full_segments_table = full_segments_table.rename(columns={"code": "segment"})
    full_segments_table = full_segments_table[["segment", "english", "japanese"]]

    # Mapping the full-length JLAC10 codes to texts
    segment_spans = [[0, 5], [5, 9], [9, 12], [12, 15], [15, 17]]
    descriptions = [
        "analyte",
        "identification",
        "specimen",
        "methodology",
        "result_identifier",
    ]
    for span, description in zip(segment_spans, descriptions):
        start, end = span
        full_jlac10_table["segment"] = (
            "*" * start
            + full_jlac10_table["code"].str.slice(start, end)
            + "*" * (17 - end)
        )
        full_jlac10_table = full_jlac10_table.merge(
            full_segments_table, how="left", on="segment"
        )
        full_jlac10_table["japanese"] = full_jlac10_table["japanese"].fillna("")
        full_jlac10_table["english"] = full_jlac10_table["english"].fillna("")
        full_jlac10_table = full_jlac10_table.rename(
            columns={
                "japanese": f"{description}_japanese",
                "english": f"{description}_english",
            }
        )
    # Additionally, mapping the JLCC10 codes with unique result identifiers
    description = "result_identifier"
    full_jlac10_table["segment"] = (
        full_jlac10_table["code"].str.slice(0, 9)
        + "*" * 6
        + full_jlac10_table["code"].str.slice(15, 17)
    )
    full_jlac10_table = full_jlac10_table.merge(
        full_segments_table, how="left", on="segment"
    )
    full_jlac10_table["japanese"] = full_jlac10_table["japanese"].fillna("")
    full_jlac10_table["english"] = full_jlac10_table["english"].fillna("")
    full_jlac10_table[f"{description}_japanese"] = full_jlac10_table["japanese"].mask(
        full_jlac10_table["japanese"] == "",
        full_jlac10_table[f"{description}_japanese"],
    )
    full_jlac10_table[f"{description}_english"] = full_jlac10_table["english"].mask(
        full_jlac10_table["english"] == "",
        full_jlac10_table[f"{description}_english"],
    )
    full_jlac10_table = full_jlac10_table.drop(["japanese", "english"], axis=1)
    full_jlac10_table = full_jlac10_table.drop(["segment"], axis=1)

    # Concatenate all the texts expressions of the segments
    for language in ["japanese", "english"]:
        full_jlac10_table[language] = ""
        for description in descriptions:
            full_jlac10_table[f"{description}_{language}"] = full_jlac10_table[
                f"{description}_{language}"
            ].astype(str)
            full_jlac10_table[language] = (
                full_jlac10_table[language]
                + full_jlac10_table[f"{description}_{language}"]
                + "/"
            )

    # Replace empty Japanese expressions
    full_jlac10_table = full_jlac10_table.replace(r"\(jp:\s*\)", "", regex=True)
    full_segments_table = full_segments_table.replace(r"\(jp:\s*\)", "", regex=True)

    # Replace common Japanese terms into English
    jp_mapping = {
        "(jp: 定量値)": "quantitative",
        "(jp: 構成比)": "composition ratio",
        "(jp: クレアチニン補正値)": "creatinine-adjusted",
        "(jp: 判定)": "interpretation",
        "(jp: コントロール比)": "ratio to control",
        "(jp: 陽性コントロール比)": "ratio to positive control",
        "(jp: 陰性コントロール比)": "ratio to negative control",
        "(jp: 抗核抗体)": "antinuclear antibody",
        "(jp: 型)": "type",
        "(jp: スコア)": "score",
        "(jp: 別紙報告)": "reported separately",
        "(jp: 単位時間総量)": "total amount per unit time",
        "(jp: 活性化部分トロンボプラスチン時間)": "activated partial thromboplastin time",
        "(jp: 部分トロンボプラスチン時間)": "partial thromboplastin time",
        "(jp: トロンボプラスチン時間)": "thromboplastin time",
        "(jp: プロトロンビン時間)": "prothrombin time",
    }
    full_jlac10_table = full_jlac10_table.replace(jp_mapping)
    full_segments_table = full_segments_table.replace(jp_mapping)

    # Replace words optionally
    opt_mapping = {"platelet clit": "platelet crit"}
    full_jlac10_table = full_jlac10_table.replace(opt_mapping)
    full_segments_table = full_segments_table.replace(opt_mapping)

    # Process the table
    full_jlac10_table = common_df_cleaning(
        full_jlac10_table, columns_used=full_jlac10_table.columns.tolist()
    )
    # Sort and clean
    full_jlac10_table, analytic = clean_and_inspect_mapping_table(
        full_jlac10_table,
        original_col="code",
        target_col="english",
        sort_by_original=True,
    )
    process_analytics["full-length JLAC10"] = analytic

    return (full_jlac10_table, full_segments_table, process_analytics)


def create_jlac10_to_text_tables(output_dir: str):
    """Creates tables mapping JLAC10 codes to descriptive texts and recommended units.
    This function produces the following tables:
        JLAC10_to_text.csv (table to map full-length JLAC10 codes to texts)
        JLAC10_segments_to_text.csv (table to map JLAC10 segments to texts)
        JLAC10_to_unit.csv (table to map full-length JLAC10 codes to recommended units)
    """
    # Define variables
    process_analytics = {}

    # Download tables
    tables = load_jlac10_tables()
    full_jlac10_table, full_segments_table, process_analytics = (
        _preprocess_jlac10_tables(tables)
    )

    # Full-length JLAC10 to text
    jlac10_to_text_table = full_jlac10_table.loc[:, ["code", "english", "japanese"]]

    # Full-length JLAC10 to unit
    jlac10_to_unit_table = full_jlac10_table.loc[:, ["code", "unit"]]
    jlac10_to_unit_table = jlac10_to_unit_table.replace(
        r".*[未設定]{1}.*", pd.NA, regex=True
    )
    jlac10_to_unit_table = jlac10_to_unit_table.replace("", pd.NA)
    jlac10_to_unit_table = jlac10_to_unit_table.dropna(subset=["unit"], how="any")

    # Save the maps
    save_table(
        jlac10_to_text_table,
        output_dir,
        "full_JLAC10",
        "text",
        columns=[config.COL_ORIGINAL, "english", "japanese"],
    )
    save_table(
        full_segments_table,
        output_dir,
        "JLAC10_segments",
        "text",
        columns=[config.COL_ORIGINAL, "english", "japanese"],
    )
    save_table(
        jlac10_to_unit_table,
        output_dir,
        "JLAC10",
        "unit",
        columns=[config.COL_ORIGINAL, "unit"],
    )
    # Save the analytic sheet
    save_analytics(process_analytics, output_dir, "JLAC10", "text")
