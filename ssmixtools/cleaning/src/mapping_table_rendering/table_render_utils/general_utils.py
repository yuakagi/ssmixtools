"""General utils"""

import os
import re
from typing import Iterable
import json
import codecs
import unicodedata
import chardet
from tqdm import tqdm
import pandas as pd
from .....generals import general_config as config
from .....generals.general_utils import archive_file


def normalize_column_names(cols: list[str]):
    """Normalizes column names."""
    cols = [unicodedata.normalize("NFKC", col).strip() for col in cols]
    cols = [re.sub(config.R_DASHES, "-", col) for col in cols]
    cols = [re.sub(r"\s+", " ", col) for col in cols]
    return cols

def convert_to_utf8(file_path: str):
    """Converts file encodings to UTF-8"""
    # Detect encoding
    with open(file_path, "rb") as file:
        raw_data = file.read()
        encoding = chardet.detect(raw_data)["encoding"]
    # Format
    with codecs.open(file_path, "r", encoding) as file:
        content = file.read()
    with codecs.open(file_path, "w", "utf-8") as file:
        file.write(content)


def save_table(
    table: pd.DataFrame,
    output_dir: str,
    original_code_system: str,
    target_code_system: str,
    columns: list[str],
):
    """Save a table as a csv file."""
    # Determine the path
    code_pair = f"{original_code_system}_to_{target_code_system}"
    file_name = f"{code_pair}.csv"
    csv_path = os.path.join(output_dir, file_name)
    if os.path.exists(csv_path):
        archive_file(csv_path)
        print(f"{csv_path} already exists. This old file was archived.")
    # Save
    table.columns = columns
    table.to_csv(csv_path, mode="w", header=True, index=False)


def save_analytics(
    analytics: dict,
    output_dir: str,
    original_code_system: str,
    target_code_system: str,
):
    """Save analytic data as a json file."""
    # Determine the path
    analytics_dir = os.path.join(output_dir, "analytics/")
    if not os.path.exists(analytics_dir):
        os.mkdir(analytics_dir)
    code_pair = f"{original_code_system}_to_{target_code_system}"
    file_name = f"{code_pair}_analytics.json"
    analytic_sheet_path = os.path.join(analytics_dir, file_name)
    if os.path.exists(analytic_sheet_path):
        archive_file(analytic_sheet_path)
        print(f"{analytic_sheet_path} already exists. This old file was archived.")
    # Save
    with open(analytic_sheet_path, mode="w", encoding="utf-8") as f:
        json.dump(analytics, f, ensure_ascii=False, indent=2)


def common_df_cleaning(df: pd.DataFrame, columns_used: list = None) -> pd.DataFrame:
    """Performs cleaning operations that are applied to most tables.

    Args:
        df (pd.DataFrame): The table to be processed.
        columns_used (list, optional): A list of columns that are not dropped.
            If not specified, all columns are used.
    Returns:
        df (pd.DataFrame): The cleaned dataframe
    """
    # Normalize column names
    cols = df.columns.tolist()
    cols = normalize_column_names(cols)
    df.columns = cols
    # Drop unnecessary columns
    if columns_used:
        columns_used = [
            unicodedata.normalize("NFKC", col).strip() for col in columns_used
        ]
        df = df[columns_used]

    # Clean values
    for col in df.columns:
        # Convert data type to str
        df.loc[:, col] = df[col].fillna("").astype(str)
        # Normalize white spaces
        df.loc[:, col] = df[col].str.strip()
        df.loc[:, col] = df[col].replace(r"\s+", " ", regex=True)
        # Normalize strings
        df.loc[:, col] = df[col].apply(lambda x: unicodedata.normalize("NFKC", x))
        # Normalize dashes
        df.loc[:, col] = df[col].replace(config.R_DASHES, "-", regex=True)
        # Replace empty strings with pd.NA
        df.loc[:, col] = df[col].replace("", pd.NA)

    return df


def _inspect_one_to_many(
    mapping_table: pd.DataFrame,
    original_col: str,
    target_col: str,
    text_col: str = None,
) -> tuple[pd.DataFrame, dict]:
    """Inspects records with OneToMany relationships.

    This function selects the rows that comes first, therefore the rows must be ordered before this function is applied.
    OneToMany relationships need to be evaluated and handled properly, otherwise a code can be
    mapped to more than two target codes otherwise.
    """

    # Create a column to count OneToMany
    mapping_table["one to many count"] = (
        mapping_table[[original_col, target_col]]
        .replace("", pd.NA)
        .groupby(original_col)
        .transform("count")
    )

    # Create a mask to filter records with OneToMany relationships
    one_to_many_mask = mapping_table["one to many count"] > 1

    # Create a list of codes with OneToMany relationships
    one_to_many_keys = (
        mapping_table.loc[one_to_many_mask, original_col].unique().tolist()
    )

    # Drop the 'one to many count' column
    mapping_table = mapping_table.drop("one to many count", axis=1)

    # Count unique codes with OneToMany relationships
    one_to_many_uniques = {}
    non_missing_target = mapping_table[target_col] != ""
    for key in one_to_many_keys:
        key_rows = mapping_table[original_col] == key
        group = mapping_table.loc[non_missing_target & key_rows, :]
        if text_col:
            uniques = (
                group[target_col] + "(" + group[text_col].fillna("") + ")"
            ).tolist()
        else:
            uniques = group[target_col].tolist()
        one_to_many_uniques[key] = uniques
    n_one_to_many = len(one_to_many_uniques)
    one_to_many_analytics = {
        "number of codes with OneToMany relationship": n_one_to_many,
        "OneToMany list": one_to_many_uniques,
    }

    # Drop OneToManys by selecting the first rows
    one_to_many_selection_mask = ~(mapping_table[original_col].duplicated(keep="first"))
    mapping_table = mapping_table[one_to_many_selection_mask]

    return mapping_table, one_to_many_analytics


def clean_and_inspect_mapping_table(
    mapping_table: pd.DataFrame,
    original_col: str,
    target_col: str,
    text_col: str = None,
    sort_by_original: bool = False,
):
    """Inspects and cleans a table.

    This function performs:

        1: Sorting rows : by lengths (descending) first, and then lexicographically.
        2: Inspecting and handling OneToMany relationships.
        3: Inspecting and cleaning missing values.

    By default, the sorting uses the target values; however,
    the table can be sorted using the original values by setting sort_by_original to true.

    Args:
        mapping_table (pd.DataFrame): The mapping table to be examined.
        original_col (str): The primary column that contains the original values.
        target_col (str): The primary column that contains the target values.
        text_col (str, optional): A column that contains text names of the target values.
            The default is None.
        sort_by_original (bool, optional): If true, the table is ordered by the  original values.
    """
    # Initialize
    process_analytics = {}

    # Sort the target column by string length, and then in lexicographical order.
    if sort_by_original:
        sort_col = original_col
    else:
        sort_col = target_col
    mapping_table["code length"] = mapping_table[sort_col].fillna("").str.len()
    mapping_table = mapping_table.sort_values(
        ["code length", sort_col], ascending=[False, True]
    )
    mapping_table = mapping_table.drop("code length", axis=1)

    # Inspect OneToMany relationships, and handle them.
    mapping_table, one_to_many_analytics = _inspect_one_to_many(
        mapping_table=mapping_table,
        original_col=original_col,
        target_col=target_col,
        text_col=text_col,
    )
    process_analytics["OneToMany"] = one_to_many_analytics

    # Inspect missing target codes after excluding duplications, and drop rows with missing target values.
    mapping_table[target_col] = mapping_table[target_col].fillna("")
    missing_targets = mapping_table[target_col] == ""
    n_missing = int(missing_targets.sum())
    if text_col:
        missing_uniques = (
            (
                mapping_table.loc[missing_targets, target_col]
                + "("
                + mapping_table.loc[missing_targets, text_col]
                + ")"
            )
            .unique()
            .tolist()
        )
    else:
        missing_uniques = (
            mapping_table.loc[missing_targets, target_col].unique().tolist()
        )

    process_analytics["missing target codes"] = {
        "number of missing target codes": n_missing,
        "corresponding original codes": missing_uniques,
    }
    mapping_table = mapping_table[~missing_targets]

    return mapping_table, process_analytics


def aggregate_source_tables(
    tables: Iterable,
    columns_used: list[str],
    original_col: str,
    target_col: str,
    secondary_target_col: str = None,
    cropped_cols: list[str] = None,
    cropped_lengths: list[int] = None,
) -> pd.DataFrame:
    """Concatenate tables.

    Duplicated records are dropped except for the first ones.
    """
    # Params
    aggregated = None
    dup_subset = [original_col, target_col]
    secondary_available = isinstance(secondary_target_col, str)
    if secondary_available:
        dup_subset.append(secondary_target_col)
    # Cleaning and concatenate
    for i, df in tqdm(enumerate(tables)):
        # Process the table
        df = common_df_cleaning(df, columns_used=columns_used)
        # Crop codes
        if cropped_cols:
            for col, length in zip(cropped_cols, cropped_lengths):
                df.loc[:, col] = df[col].str.slice(0, length)
        # Drop records with missing original codes.
        df = df.fillna("")
        df = df[df[original_col] != ""]
        # Drop duplicated records.
        df = df.drop_duplicates(subset=dup_subset)
        # Add the table number
        df["table_no"] = i

        # Concatenate the table to the mapping table. Replace if the mapping table is empty.
        if aggregated is None:
            aggregated = df
        else:
            aggregated = pd.concat([aggregated, df], ignore_index=True)
            aggregated = aggregated.sort_values("table_no", ascending=True)
            aggregated = aggregated.drop_duplicates(subset=dup_subset, keep="first")

    # Fill missing primary target code values with secondary values.
    if secondary_available:
        missing_primary_target = aggregated[target_col] == ""
        aggregated[target_col] = aggregated[target_col].mask(
            missing_primary_target, aggregated[secondary_target_col]
        )
        # Drop secondary target column
        aggregated = aggregated.drop(secondary_target_col, axis=1)
        # Drop duplicates again
        aggregated = aggregated.sort_values("table_no", ascending=True)
        aggregated = aggregated.drop_duplicates(
            subset=[original_col, target_col], keep="first"
        )
        aggregated = aggregated.reset_index(drop=True)
    aggregated = aggregated.drop("table_no", axis=1)

    # Sort columns
    final_cols = []
    for c in columns_used:
        if c in aggregated.columns:
            final_cols.append(c)
    aggregated = aggregated[final_cols]

    return aggregated
