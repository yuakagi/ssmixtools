""" Module to inspect PPR-01 tables"""

import pandas as pd
from ...extraction_utils import (
    inspect_csv,
    inspect_timestamps,
    count_unique_values,
)
from .....generals import general_config as config
from .....generals.general_utils import all_values_to_int


def _inspect_ppr_01(df: pd.DataFrame) -> tuple:
    """Helper function to inspect a chunk of PPR-01 record files.

    Args:
        df (pd.DataFrame): Data frame chunk.
    Returns:
        df (pd.DataFrame): DataFrame passed as an argument is directly returned without
            any modifications to it. This is for consistency with 'parallel_map_partitions_ext' function.
        stats (dict): Dictionary that stores inspection results. This is the main product of this function.
    """
    data_type = "PPR-01"

    # Initialize a dictionary to store analytics
    stats = {}

    # Define masks
    mdcdx2_named = df["primary_diagnosis_coding_system"].str.contains(
        config.R_MDCDX2, na=False
    )
    mdcdx2_code_pattern = df["primary_diagnosis_code"].str.contains(
        config.R_MDCDX2_CODE, na=False
    )
    icd10_named = df["secondary_diagnosis_coding_system"].str.contains(
        config.R_ICD10, na=False
    )
    icd10_code_pattern = df["secondary_diagnosis_code"].str.contains(
        config.R_ICD10_CODE, na=False
    )
    irregular_diagnosis_type = ~(
        df["diagnosis_type"].isin(config.DIAGNOSIS_TYPES.keys())
    )
    missing_primary_code = df["primary_diagnosis_code"].isnull()
    missing_primary_system = df["primary_diagnosis_coding_system"].isnull()
    missing_secondary_code = df["secondary_diagnosis_code"].isnull()
    missing_secondary_system = df["secondary_diagnosis_coding_system"].isnull()
    missing_diagnosis_type = df["diagnosis_type"].isnull()

    # Create a mask dictionary for just counting records
    counting_masks = {
        "either MDCDX2 or ICD-10 available": (mdcdx2_code_pattern & mdcdx2_named)
        | (icd10_code_pattern & icd10_named),
        "both MDCDX2 and ICD-10 available": mdcdx2_code_pattern
        & mdcdx2_named
        & icd10_code_pattern
        & icd10_named,
        "only MDCDX2 available": mdcdx2_code_pattern
        & mdcdx2_named
        & ~(icd10_code_pattern & icd10_named),
        "only ICD-10 available": ~(mdcdx2_code_pattern & mdcdx2_named)
        & icd10_code_pattern
        & icd10_named,
        "primary diagnosis code exists but MDCDX2 not named": ~(missing_primary_code)
        & ~(mdcdx2_named),
        "secondary diagnosis code exists but ICD-10 not named": ~(
            missing_secondary_code
        )
        & ~(icd10_named),
        "diagnosis in plain text available but both primary and secondary codes missing": missing_primary_code
        & missing_secondary_code,
    }

    # Create a mask dictionary for unique value counts
    counting_params = {
        "neither MDCDX2 nor ICD-10 available": {
            "mask": ~(
                (mdcdx2_code_pattern & mdcdx2_named)
                | (icd10_code_pattern & icd10_named)
            ),
            "value_cols": [
                "primary_diagnosis_code",
                "primary_diagnosis_text",
            ],
        },
        "MDCDX2 named but irregular MDCDX2 code": {
            "mask": ~(mdcdx2_code_pattern) & mdcdx2_named,
            "value_cols": [
                "primary_diagnosis_code",
                "primary_diagnosis_text",
            ],
        },
        "ICD-10 named but irregular ICD-10 code": {
            "mask": ~(icd10_code_pattern) & icd10_named,
            "value_cols": [
                "secondary_diagnosis_code",
                "primary_diagnosis_text",
            ],
        },
        "code is MDCDX2-like but primary coding system missing": {
            "mask": mdcdx2_code_pattern & missing_primary_system,
            "value_cols": [
                "primary_diagnosis_code",
                "primary_diagnosis_text",
            ],
        },
        "code is ICD-10-like but secondary coding system missing": {
            "mask": icd10_code_pattern & missing_secondary_system,
            "value_cols": [
                "secondary_diagnosis_code",
                "primary_diagnosis_text",
            ],
        },
        "diagnosis type available but irregular diagnosis type": {
            "mask": irregular_diagnosis_type & ~(missing_diagnosis_type),
            "value_cols": ["diagnosis_type"],
        },
    }

    # Count records
    n_records = df.count().to_dict()
    n_records = all_values_to_int(n_records)
    stats["number of records"] = n_records

    # Counting timestamp columns
    stats["timestamps"] = inspect_timestamps(
        df,
        timestamp_cols=config.RECORD_TABLE_PARAMS[data_type]["timestamps"],
    )

    # Count values with respect to standardization
    stats["standardization"] = {}
    for key, val in counting_masks.items():
        stats["standardization"][key] = int(val.sum())

    # Diagnostic systems
    primary_system_counts = (
        df["primary_diagnosis_coding_system"].value_counts().to_dict()
    )
    primary_system_counts = all_values_to_int(primary_system_counts)

    secondary_system_counts = (
        df["secondary_diagnosis_coding_system"].value_counts().to_dict()
    )
    secondary_system_counts = all_values_to_int(secondary_system_counts)

    stats["diagnosis_code_systems"] = {}
    stats["diagnosis_code_systems"]["primary"] = primary_system_counts
    stats["diagnosis_code_systems"]["secondary"] = secondary_system_counts

    # Collect unique values seen in irregular records
    stats["unique values"] = {}
    unique_counts, total_irregular_counts = count_unique_values(df, counting_params)
    stats["unique values"] = unique_counts
    stats["standardization"] = {**stats["standardization"], **total_irregular_counts}

    return df, stats


def inspect_ppr_01():
    """Inspect all PPR-01 record CSV files and save the inspection results as a JSON file."""
    # Define variables
    data_type = "PPR-01"
    inspect_csv(data_type=data_type, function=_inspect_ppr_01, chunksize=-1)
