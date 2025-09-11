""" Module to inspect OML-11 tables"""

import pandas as pd
from ...extraction_utils import (
    inspect_csv,
    multiindex_dict_to_nested_dict,
    inspect_timestamps,
    count_unique_values,
)
from .....generals import general_config as config
from .....generals.general_utils import all_values_to_int


def _inspect_oml_11(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Helper function to inspect a chunk of OML-11 record files.

    Args:
        df (pd.DataFrame): Data frame chunk.
    Returns:
        df (pd.DataFrame): DataFrame passed as an argument is directly returned without
            any modifications to it. This is for consistency with 'parallel_map_partitions_ext' function.
        stats (dict): Dictionary that stores inspection results. This is the main product of this function.
    """
    data_type = "OML-11"

    # Initialize a dictionary to store analytics
    stats = {}

    # Define masks
    jlac10_named = df["lab_coding_system"].str.contains(config.R_JLAC10, na=False)
    jlac10_code_pattern = df["lab_code"].str.contains(config.R_JLAC10_CODE, na=False)
    iso_plus_named = df["unit_coding_system"].str.contains(config.R_ISO_PLUS, na=False)
    missing_item_code = df["lab_code"].isnull()
    missing_item_text = df["lab_text"].isnull()
    missing_item_coding_system = df["lab_coding_system"].isnull()
    missing_unit_code = df["unit_code"].isnull()
    missing_unit_text = df["unit_text"].isnull()
    missing_value = df["value"].isnull()
    unit_code_text_overlap = df["unit_code"] == df["unit_text"]

    valid_jlac10_codes = jlac10_code_pattern & jlac10_named

    # Create a mask dictionary for just counting records
    counting_masks = {
        "JLAC10_available": valid_jlac10_codes,
        "ISO named and both unit code and text available": iso_plus_named
        & ~(missing_unit_code | missing_unit_text),
        "ISO named and only unit code available": iso_plus_named
        & ~(missing_unit_code)
        & missing_unit_text,
        "ISO named and only unit text available": iso_plus_named
        & missing_unit_code
        & ~(missing_unit_text),
        "item code exists but JLAC10 not named": ~(missing_item_code) & ~(jlac10_named),
        "unit code exists but ISO not named": ~(missing_unit_code) & ~(iso_plus_named),
        "item in plain text available but item code missing": ~(missing_item_text)
        & missing_item_code,
        "both value and unit are missing": missing_value
        & (missing_unit_code | missing_unit_text),
    }

    # Create a param dict for irregular value counts
    counting_params = {
        "unit code and text not overlapping": {
            "mask": ~unit_code_text_overlap,
            "value_cols": [
                "unit_code",
                "unit_text",
            ],
        },
        "ISO named and either unit code or text available": {
            "mask": iso_plus_named & ~(missing_unit_code & missing_unit_text),
            "value_cols": [
                "unit_code",
                "unit_text",
            ],
        },
        "either unit code or text available but ISO not named": {
            "mask": ~(iso_plus_named) & ~(missing_unit_code & missing_unit_text),
            "value_cols": [
                "unit_code",
                "unit_text",
            ],
        },
        "JLAC10 not available": {
            "mask": ~(jlac10_code_pattern & jlac10_named),
            "value_cols": [
                "lab_code",
                "lab_text",
            ],
        },
        "JLAC10 named but irregular JLAC10 code": {
            "mask": ~(jlac10_code_pattern) & jlac10_named,
            "value_cols": [
                "lab_code",
                "lab_text",
            ],
        },
        "code is JLAC10-like but coding system missing": {
            "mask": jlac10_code_pattern & missing_item_coding_system,
            "value_cols": [
                "lab_code",
                "lab_text",
            ],
        },
    }

    # Count records
    n_records = df.count().to_dict()
    n_records = all_values_to_int(n_records)
    stats["number of records"] = n_records

    # Inspect timestamp columns
    stats["timestamps"] = inspect_timestamps(
        df,
        timestamp_cols=config.RECORD_TABLE_PARAMS[data_type]["timestamps"],
    )

    # Count values with respect to standardization
    stats["standardization"] = {}
    for key, val in counting_masks.items():
        stats["standardization"][key] = int(val.sum())

    # Inspect coding systems
    item_coding_system_counts = df["lab_coding_system"].value_counts().to_dict()
    item_coding_system_counts = all_values_to_int(item_coding_system_counts)

    unit_coding_system_counts = df["unit_coding_system"].value_counts().to_dict()
    unit_coding_system_counts = all_values_to_int(unit_coding_system_counts)

    stats["laboratory test code systems"] = {}
    stats["laboratory test code systems"]["item"] = item_coding_system_counts
    stats["laboratory test code systems"]["unit"] = unit_coding_system_counts

    # Collect unique values seen in irregular records
    unique_counts, total_irregular_counts = count_unique_values(df, counting_params)
    stats["standardization"] = {**stats["standardization"], **total_irregular_counts}

    # Inspect units in detail.
    mixed_unit_counts = {}
    unit_col_dict = {"text": "unit_text", "code": "unit_code"}
    for col_type, unit_col in unit_col_dict.items():
        unit_only_df = df[~missing_item_code][["lab_code", unit_col]].fillna("")
        grouped = unit_only_df.groupby("lab_code")[unit_col].nunique()
        filtered = grouped[grouped > 1]
        item_codes_with_multiple_units = filtered.index.tolist()
        multiple_unit_mask = unit_only_df["lab_code"].isin(
            item_codes_with_multiple_units
        )
        multiple_unit_jlac10_mask = (
            multiple_unit_mask & valid_jlac10_codes
        )  # <- JLAC10 selected here
        mixed_unit_counts = all_values_to_int(
            unit_only_df[multiple_unit_jlac10_mask]
            .groupby("lab_code")[unit_col]
            .value_counts()
            .to_dict()
        )
        mixed_unit_counts = {
            col_type: multiindex_dict_to_nested_dict(mixed_unit_counts)
        }

    # Inspect nonnumeric laboratory values
    non_numeric_value_mask = pd.to_numeric(df["value"], errors="coerce").isna() & ~(
        missing_value
    )
    non_numeric_item_codes = (
        df[non_numeric_value_mask & valid_jlac10_codes]["lab_code"]
        .fillna("")
        .unique()
        .tolist()
    )
    numeric_item_codes = (
        df[(~non_numeric_value_mask) & valid_jlac10_codes]["lab_code"]
        .fillna("")
        .unique()
        .tolist()
    )

    non_numeric_jlac10_mask = (
        non_numeric_value_mask & valid_jlac10_codes
    )  # <- JLAC10 selected here
    unique_non_numerics = all_values_to_int(
        df[non_numeric_jlac10_mask][["lab_code", "value"]]
        .groupby("lab_code")["value"]
        .value_counts()
        .to_dict()
    )
    unique_non_numerics = {
        "items with nonnumeric values": multiindex_dict_to_nested_dict(
            unique_non_numerics
        )
    }

    # Save unique values
    stats["unique values"] = {
        "unique irregular values": unique_counts,
        "values with mixed units": mixed_unit_counts,
        "unique nonnumeric test result values": unique_non_numerics,
    }

    return df, stats


def inspect_oml_11():
    """Inspects all OML-11 record CSV files and save the inspection results as a JSON file."""
    # Define variables
    data_type = "OML-11"
    inspect_csv(data_type=data_type, function=_inspect_oml_11, chunksize=-1)
