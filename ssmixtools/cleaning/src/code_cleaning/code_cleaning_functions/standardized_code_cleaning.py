import pandas as pd
from .....generals import general_config as config
from ...cleaning_utils import remove_method_from_jlac10


def _clean_standardized_codes(
    df: pd.DataFrame,
    code_col: str,
    min_length: int,
    max_length: int,
    code_regex: str,
    truncate_long_codes: bool = True,
) -> tuple:
    """Cleans standardized codes such as ICD-10, ATC and JLAC10 codes.

    This process takes following steps:

        - 1. Exclude records with missing codes
        - 2. Exclude codes shorter than the minimal code length
        - 3. Exclude or truncate coder longer  than the max code length
        - 4. Validate codes with regular expression, and exclude irregular codes

    Stats of these irregular codes are summarized in a dictionary.

    Args:
        df (pd.DataFrame): Target dataframe.
        code_col (str): Name of the column that contains coded values.
        min_length (int): Minimal code length.
        max_length (int): Maximal code length.
        code_regex (str): Regular expression to validate codes.
        truncate_long_codes (bool): If true, codes longer than 'max_length' are truncated.
            to 'max_length'. If false, long codes are dropped.
    Returns:
        df (pd.DataFrame): Cleaned dataframe.
        irregular_code_stats (dict): Dictionary that contains summary of irregular code stats.
    """
    # Original length
    original_n_records = len(df)
    # Replacing missing values with empty strings ("") for string operations
    df[code_col] = df[code_col].fillna("")

    # Inspect and drop missing codes first
    missing_mask = df[code_col] == ""
    n_missing = missing_mask.sum()
    df = df.loc[~missing_mask]

    # Inspect code length
    df["code_length"] = df[code_col].str.len()
    short_mask = df["code_length"] < min_length
    long_mask = df["code_length"] > max_length
    short_codes = df.loc[short_mask, code_col].value_counts().to_dict()
    short_total = sum(i for i in short_codes.values())
    long_codes = df.loc[long_mask, code_col].value_counts().to_dict()
    long_total = sum(i for i in long_codes.values())
    df = df.drop("code_length", axis=1)
    if truncate_long_codes:
        df[code_col] = df[code_col].str.slice(0, max_length)
        df = df.loc[~short_mask]
    else:
        df = df.loc[~(short_mask | long_mask)]

    # Inspect codes with regular expression
    valid_pattern_mask = df[code_col].str.match(code_regex, na=True)
    invalid_pattern_mask = ~valid_pattern_mask
    invalid_codes = df.loc[invalid_pattern_mask, code_col].value_counts().to_dict()
    invalid_total = sum(i for i in invalid_codes.values())
    df = df.loc[~invalid_pattern_mask]

    # Count the number of dropped records
    n_dropped = original_n_records - len(df)

    # Write summary
    long_code_handling = "truncated" if truncate_long_codes else "excluded"
    irregular_code_stats = {
        "missing_codes": {"total": n_missing},
        "short_codes_(excluded)": {
            "total": short_total,
            "unique_values": short_codes,
        },
        f"long_codes_({long_code_handling})": {
            "total": long_total,
            "unique_values": long_codes,
        },
        "irregular_codes_after_code_length_handling": {
            "total": invalid_total,
            "unique_values": invalid_codes,
        },
        "total_number_of_records_excluded": n_dropped,
    }

    return df, irregular_code_stats


def clean_icd10_codes(df: pd.DataFrame):
    """Helper function for cleaning irregular ICD-10 codes"""
    df, irregular_code_stats = _clean_standardized_codes(
        df=df,
        code_col=config.COL_ITEM_CODE,
        min_length=3,
        max_length=5,
        code_regex=config.R_ICD10_CODE,
        truncate_long_codes=True,
    )
    # Remove dots '.' from ICD10 codes
    df[config.COL_ITEM_CODE] = df[config.COL_ITEM_CODE].replace(".", "", regex=False)
    return df, irregular_code_stats


def clean_atc_codes(df: pd.DataFrame):
    """Helper function for cleaning irregular ATC codes"""
    df, irregular_code_stats = _clean_standardized_codes(
        df=df,
        code_col=config.COL_ITEM_CODE,
        min_length=4,
        max_length=7,
        code_regex=config.R_ATC_CODE,
        truncate_long_codes=False,
    )
    return df, irregular_code_stats


def clean_jlac10_result_codes(df: pd.DataFrame):
    """Helper function for cleaning irregular JLAC10 codes"""
    df, irregular_code_stats = _clean_standardized_codes(
        df=df,
        code_col=config.COL_ITEM_CODE,
        min_length=17,
        max_length=17,
        code_regex=config.R_JLAC10_CODE,
        truncate_long_codes=False,
    )
    # Replace the three characters for methodology with '---'
    df[config.COL_ITEM_CODE] = remove_method_from_jlac10(df[config.COL_ITEM_CODE])
    return df, irregular_code_stats
