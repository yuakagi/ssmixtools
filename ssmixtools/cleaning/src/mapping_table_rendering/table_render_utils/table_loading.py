"""Module to download tables form websites"""

import os
import re
import io
import time
import zipfile
import tempfile
from urllib import request
from tqdm import tqdm
import requests
import chardet
from bs4 import BeautifulSoup
from bs4.element import Tag
import numpy as np
import pandas as pd
from .general_utils import convert_to_utf8, common_df_cleaning, normalize_column_names

import chardet



def get_soup(url: str, delay: int = 10) -> BeautifulSoup:
    """Gets a BeautifulSoup object from the URL.

    This function ensures delays between scraping.

    Args:
        url (str): The URL for scraping.
        delay (int): The seconds to wait for the next scraping. The default delay is 10 seconds
    """
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "lxml")
    time.sleep(delay)
    return soup


def p_items_to_dict(p_items: Tag) -> dict:
    """Makes elements in <p> tags into a dictionary."""
    p_dict = {}
    items = []
    for item in p_items:
        text = item.text.strip()
        if text:
            items.append(text)
    len_items = len(items)
    n_categories = int(len_items // 2)
    for i in range(n_categories):
        category = items[i * 2]
        description = items[i * 2 + 1]
        p_dict[category] = description

    return p_dict


def get_first_table_from_soup(soup: BeautifulSoup | Tag) -> pd.DataFrame:
    """
    Extracts a table from a BeautifulSoup object and converts it to a pandas DataFrame.

    Args:
        soup (BeautifulSoup|Tag): The BeautifulSoup object containing the parsed HTML,
            or a Tag object that represents a filtered section of the HTML.
    Returns:
        pd.DataFrame: A DataFrame containing the extracted table data.
    """
    # Find the first table in the soup (you can modify this to target specific tables)
    table = soup.find("table")
    # Extract rows
    headers = [header.text.strip() for header in table.find_all("th")]
    rows = []
    for row in table.find_all("tr"):
        cells = [cell.text.strip() for cell in row.find_all("td")]
        if cells:  # Only add rows with data
            rows.append(cells)
    # Create DataFrame
    df = pd.DataFrame(rows, columns=headers if headers else None)
    return df


def _clean_jlac10_tables(table: pd.DataFrame, code_regex: str, code_col: str = "code"):
    """Selects rows with valid JLAC10 codes.

    Because the original tables are saved as Excel sheets with many merged cells,
    selecting relevant rows is essential in preparing each table in the table sets.
    """
    # Common cleaning operations
    table = common_df_cleaning(table)
    # Extract code components that match with the given pattern
    matched_codes = table[code_col].str.extract(code_regex, expand=True).iloc[:, 0]
    table[code_col] = matched_codes.values
    table = table.loc[~table[code_col].isna(), :]
    return table


def load_jlac10_tables() -> list[pd.DataFrame]:
    """Downloads the latest JLAC10 tables.

    Because the tables have many columns, this function selects some relevant columns.
    The function returns the following tables:
        - Table for the full-length codes:
            full_table:
                columns:
                    'code': The 17-character JLAC10 codes.
                    'unit': The standardized units for the results.
        - Table for JLAC10 code segments:
            Columns:
                All of the returned tables have the same set of columns:
                'code': JLAC10 code segments
                'japanese': Japanese names of the segments
                'english': English names of the segments
            Tables:
                full_table: Contains the full 17-character codes
                analyte_table: Contains 1st-5th characters of JLAC10 codes
                id_table: 6st-9th characters
                specimen_table: 10st-12th characters
                method_table: 13st-15th characters
                common_result_id_table: 16st-17th characters
                unique_result_id_table: Contains the unique result identifiers
    """
    # Get the link to the latest tables
    home_url = "https://www.idial.or.jp/dwnld/clinicalexam-master_matome.html"
    base_url = "https://www.idial.or.jp/dwnld/file/*"
    link_regex = re.compile(r"\d+_matome\.zip")
    soup = get_soup(home_url)
    a_items = soup.find_all("a", attrs={"href": link_regex})
    links = [a.get("href") for a in a_items]
    # Extract file names
    file_name_regex = r".*/((\d+)_matome\.zip).*"
    files = []
    file_versions = []
    for link in links:
        matched = re.match(
            file_name_regex,
            link,
        )
        files.append(matched[1])
        file_versions.append(int(matched[2]))
    latest_idx = np.argmax(np.array(file_versions))
    latest_file = files[latest_idx]
    latest_file_url = base_url.replace("*", latest_file)

    # Open the file
    response = requests.get(latest_file_url, stream=True)
    response.raise_for_status()
    with (
        io.BytesIO(response.content) as bytes_io,
        zipfile.ZipFile(bytes_io) as zip_file,
        tempfile.TemporaryDirectory() as tempdir,
    ):
        zip_file.extractall(tempdir)
        # Get the first encountered .xlsx file.
        # NOTE: Update if necessary
        unzipped = os.listdir(tempdir)
        for uz in unzipped:
            uz_path = os.path.join(tempdir, uz)
            for r, d, fs in os.walk(uz_path):
                for f in fs:
                    if f.endswith(".xlsx"):
                        table_path = os.path.join(r, f)
                        break
                else:
                    continue
                break
            else:
                continue
            break

        # Load the table for the full-length jlac10 codes (17 characters)
        full_table = pd.read_excel(
            table_path,
            sheet_name=0,
            skiprows=4,
            usecols=[2, 23],
            dtype=str,
            header=None,
        )
        full_table.columns = ["code", "unit"]
        full_table = _clean_jlac10_tables(full_table, code_regex=r"(\d[A-Z]\d{15})")
        # Load the table for the 1st segment of JLAC10 codes (1st-5th characters)
        analyte_table = pd.read_excel(
            table_path, sheet_name=1, usecols=[0, 2, 4], dtype=str, header=None
        )
        analyte_table.columns = ["code", "japanese", "english"]
        analyte_table = _clean_jlac10_tables(
            analyte_table, code_regex=r"(\d[A-Z]\d{3})"
        )
        # Load the table for the 2nd segment of JLAC10 codes (6st-9th characters)
        id_table = pd.read_excel(
            table_path, sheet_name=2, usecols=[0, 2, 4], dtype=str, header=None
        )
        id_table.columns = ["code", "japanese", "english"]
        id_table = _clean_jlac10_tables(id_table, code_regex=r"(\d{4})")
        # Load the table for the 3rd segment of JLAC10 codes (10st-12th characters)
        specimen_table = pd.read_excel(
            table_path, sheet_name=3, usecols=[0, 2, 3], dtype=str, header=None
        )
        specimen_table.columns = ["code", "japanese", "english"]
        specimen_table = _clean_jlac10_tables(specimen_table, code_regex=r"(\d{3})")
        # Load the table for the 4th segment of JLAC10 codes (13st-15th characters)
        method_table = pd.read_excel(
            table_path, sheet_name=4, usecols=[0, 2, 3, 5], dtype=str, header=None
        )
        with_submethod = ~(method_table.loc[:, 3].isna())
        method_table.loc[with_submethod, 2] = (
            method_table.loc[with_submethod, 2]
            + ":"
            + method_table.loc[with_submethod, 3]
        )
        method_table = method_table.drop(3, axis=1)
        method_table.columns = ["code", "japanese", "english"]
        method_table = _clean_jlac10_tables(method_table, code_regex=r"(\d{3})")
        # Load the table for the 5th segment of JLAC10 codes (16st-17th characters)
        common_result_id_table = pd.read_excel(
            table_path, sheet_name=5, usecols=[0, 2], dtype=str, header=None
        )
        common_result_id_table["english"] = (
            "(jp: " + common_result_id_table.iloc[:, 1] + ")"
        )
        common_result_id_table.columns = ["code", "japanese", "english"]
        common_result_id_table = _clean_jlac10_tables(
            common_result_id_table, code_regex=r"(\d{2})"
        )
        # Load the table for the unique result identifiers
        unique_result_id_table = pd.read_excel(
            table_path, sheet_name=6, usecols=[4, 6, 7], dtype=str, header=None
        )
        unique_result_id_table.columns = ["code", "japanese", "english"]
        unique_result_id_table = _clean_jlac10_tables(
            unique_result_id_table, code_regex=r"(\d[A-Z]\d{9})"
        )

    tables = [
        full_table,
        analyte_table,
        id_table,
        specimen_table,
        method_table,
        common_result_id_table,
        unique_result_id_table,
    ]

    return tables


def load_dx_tables() -> list[pd.DataFrame]:
    """Downloads the current MDCDX2 tables."""
    # Get all file versions
    home_url = "http://www2.medis.or.jp/stdcd/byomei/download2019.html"
    version_regex = re.compile(r"byomei\d{3}.zip")
    soup = get_soup(home_url)
    links = soup.find_all("a", attrs={"href": version_regex})
    versions = [a.get("href") for a in links]
    versions = list(set([re.search(version_regex, version)[0] for version in versions]))
    versions = sorted(
        [version.replace(".zip", "").replace("byomei", "") for version in versions],
        reverse=True,
    )

    # Collect and process tables
    base_url = "http://www2.medis.or.jp/stdcd/byomei/download/file/byomei*.zip"
    dx_tables = []
    for version in tqdm(versions, desc="Loading ICD-10 tables"):
        # Download a table
        url = base_url.replace("*", version)
        main_file = "byomei*/main/nmain*.txt".replace("*", version, 2)
        title_file = "byomei*/option/ttl_main.txt".replace("*", version)
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with (
            io.BytesIO(response.content) as bytes_io,
            zipfile.ZipFile(bytes_io) as zip_file,
            tempfile.TemporaryDirectory() as tempdir,
        ):
            zip_file.extractall(tempdir)
            main_path = os.path.join(tempdir, main_file)
            title_path = os.path.join(tempdir, title_file)
            if not os.path.exists(title_path):
                # Older versions have the slightly different directory structure
                title_file = "byomei*/option/n_title/ttl_main.txt".replace("*", version)
                title_path = os.path.join(tempdir, title_file)
            convert_to_utf8(main_path)
            convert_to_utf8(title_path)
            with open(title_path, "r", encoding="utf-8") as f:
                title_text = f.read()
                columns = title_text.split(",")
                columns = [col.strip('"') for col in columns]
                columns = normalize_column_names(columns)
                # Older versions have 'ICD10' instead of 'ICD10-2013'
                if "ICD10-2013" not in columns:
                    icd10_col_idx = columns.index("ICD10")
                    columns[icd10_col_idx] = "ICD10-2013"

            df = pd.read_csv(main_path, dtype=str, header=None, na_values=["", "-"])
            df.columns = columns
        dx_tables.append(df)

    return dx_tables


def load_hot_tables() -> list[pd.DataFrame, pd.DataFrame]:
    """Downloads HOT code tables from MEDIS website"""
    # Get the latest version of the valid code list
    home_url = "http://www2.medis.or.jp/hcode/"
    version_regex = re.compile(r"h\d{8}\.zip")
    soup = get_soup(home_url)
    links = soup.find_all("a", attrs={"href": version_regex})
    versions = [a.get("href") for a in links]
    versions = list(set([re.search(version_regex, version)[0] for version in versions]))
    versions = sorted(
        [version.replace(".zip", "").replace("h", "") for version in versions],
        reverse=True,
    )
    latest_valid_version = versions[0]

    # Get the deleted item list version
    home_url = "http://www2.medis.or.jp/hcode/"
    version_regex = re.compile(r"h\d{8}_HOT9del\.txt")
    soup = get_soup(home_url)
    links = soup.find_all("a", attrs={"href": version_regex})
    versions = [a.get("href") for a in links]
    versions = list(set([re.search(version_regex, version)[0] for version in versions]))
    versions = sorted(
        [version.replace("_HOT9del.txt", "").replace("h", "") for version in versions],
        reverse=True,
    )
    latest_deleted_version = versions[0]

    # Download
    valid_table_url = (
        f"http://www2.medis.or.jp/hcode/moto_data/h{latest_valid_version}.zip"
    )
    deleted_table_url = (
        f"http://www2.medis.or.jp/hcode/moto_data/h{latest_deleted_version}_HOT9del.txt"
    )
    valid_file = "h*/MEDIS*_HOT9.TXT".replace("*", latest_valid_version, 2)
    deleted_file = "deleted.txt"
    response = requests.get(valid_table_url, stream=True)
    response.raise_for_status()
    with (
        io.BytesIO(response.content) as bytes_io,
        zipfile.ZipFile(bytes_io) as zip_file,
        tempfile.TemporaryDirectory() as tempdir,
    ):
        # Process the valid item table
        zip_file.extractall(tempdir)
        valid_file_path = os.path.join(tempdir, valid_file)
        convert_to_utf8(valid_file_path)
        valid_df = pd.read_csv(
            valid_file_path, header=0, na_values=["", "-"], dtype=str
        )

        # Process the deleted item table
        data = request.urlopen(deleted_table_url).read()
        deleted_file_path = os.path.join(tempdir, deleted_file)
        with open(deleted_file_path, mode="wb") as f:
            f.write(data)
        convert_to_utf8(deleted_file_path)
        deleted_df = pd.read_csv(
            deleted_file_path, header=0, na_values=["", "-"], dtype=str
        )
    hot_tables = [valid_df, deleted_df]
    return hot_tables


def get_atc_alterations() -> pd.DataFrame:
    """
    Create a table of ATC code alterations.
    Returns:
        pd.DataFrame: A DataFrame containing the extracted table data.
    """
    soup = get_soup(
        "https://atcddd.fhi.no/atc_ddd_alterations__cumulative/atc_alterations/"
    )
    # Find the first table in the soup (you can modify this to target specific tables)
    table_div = soup.find("div", class_="listtable")
    alt_table = get_first_table_from_soup(table_div)
    alt_table.columns = ["old_atc", "name", "new_atc", "year"]
    alt_table = alt_table.dropna(subset=["old_atc", "new_atc", "year"], how="any")
    alt_table["year"] = alt_table["year"].str.strip().str[:4].astype(int)
    # Drop ATC codes with annotations (possibly altered in a complex way)
    with_annots = alt_table["old_atc"].str.strip().str.len() > 7
    alt_table = alt_table.loc[~with_annots]
    for atc_col in ["old_atc", "new_atc"]:
        alt_table[atc_col] = alt_table[atc_col].str.strip()
        alt_table[atc_col] = alt_table[atc_col].str[:7]
    # Remove split ATC codes from the list
    alt_table = alt_table.drop_duplicates(subset="old_atc", keep=False)

    # Check for multiple updates
    alt_table = alt_table.sort_values("year", ascending=False)
    multiple_update_mask = alt_table["old_atc"].isin(alt_table["new_atc"])
    if multiple_update_mask.any():
        updated_codes = alt_table.loc[multiple_update_mask, "old_atc"].tolist()
        for c in updated_codes:
            updated_c = alt_table.loc[alt_table["old_atc"] == c, "new_atc"].tolist()[0]
            if c != updated_c:
                # Update the old_atc code in the DataFrame to reflect the latest new_atc code
                alt_table.loc[alt_table["new_atc"] == c, "new_atc"] = updated_c
    # Select columns
    alt_table = alt_table[["old_atc", "new_atc"]]
    alt_table = alt_table.drop_duplicates(subset="old_atc")

    return alt_table


def update_atc(df: pd.DataFrame, atc_col: str, atc_alt_table: pd.DataFrame):
    """Update ATC codes using the ATC alteration table.

    Args:
        df (pd.DataFrame): Dataframe to be cleaned.
        atc_col (str): Column of ATC codes.
        atc_alt_table (pd.DataFrame): ATC alteration table.
            This is prepared by 'get_atc_alterations()'.
    Returns:
        df (pd.DataFrame): Cleaned dataframe.
    """
    atc_alt_table.columns = ["old_atc", "new_atc"]
    merged_df = pd.merge(
        df, atc_alt_table, left_on=atc_col, right_on="old_atc", how="left"
    )
    merged_df[atc_col] = merged_df[atc_col].mask(
        ~merged_df["new_atc"].isna(), merged_df["new_atc"]
    )
    merged_df = merged_df.drop(columns=["new_atc", "old_atc"])
    return df


def load_atc_tables(atc_tables_dir: str) -> list[pd.DataFrame]:
    """Loads tables for ATC code mapping using the source files.
    This function loads from newer files.

    Args:
        atc_tables_dir (str): Directory that stores ATC code tables.
            This directory must contain a CSV file named 'info_atc.csv'.
    Returns:
        atc_tables (list[pd.DataFrame]): List of loaded ATC tables.
    """
    # Initialize
    na_values = ["", "-"]
    atc_tables = []
    atc_alt_table = get_atc_alterations()

    # Load files (info_atc.csv)
    atc_file = os.path.join(atc_tables_dir, "info_atc.csv")
    if os.path.exists(atc_file):
        df = pd.read_csv(atc_file, na_values=na_values)
        df.columns = normalize_column_names(df.columns)
        df = df[["商品名", "HOT番号", "YJコード", "ATC5", "ATC7"]]
        atc_tables = [df]

    else:
        # ****************************************************************************
        # Loading from raw text data (pairs of 'japic_who_atc.txt' and 'info_all.txt')
        # ****************************************************************************
        # NOTE: Tables that JAPIC provides sometimes place '-' for missing values.
        # Therefore, na_values=["", "-"] is set for each pd.read_csv().
        file_bundles = []
        for d in os.listdir(atc_tables_dir):
            group = re.match(r"(\d{8})_[Ff]iles", d)
            if group:
                e = (d, int(group[1]))
                file_bundles.append(e)
        file_bundles.sort(key=lambda x: x[1], reverse=True)
        file_bundles = [e[0] for e in file_bundles]
        # Load tables
        for d in file_bundles:
            info_path = os.path.join(atc_tables_dir, d, "TENPU/", "info_all.txt")
            atc_path = os.path.join(atc_tables_dir, d, "ATC/", "japic_who_atc.txt")
            if os.path.exists(info_path) and os.path.exists(atc_path):
                try:
                    info_df = pd.read_csv(
                        info_path, dtype=str, encoding="CP932", na_values=na_values
                    )
                except UnicodeDecodeError:
                    with open(info_path, "rb") as f:
                        info_enc = chardet.detect(f.read())["encoding"]
                    print(f"Irregular encoding ({info_enc}) detected.")
                    info_df = pd.read_csv(
                        info_path, dtype=str, encoding=info_enc, na_values=na_values
                    )
                try:
                    atc_df = pd.read_csv(
                        atc_path, dtype=str, encoding="CP932", na_values=na_values
                    )
                except UnicodeDecodeError:
                    with open(atc_path, "rb") as f:
                        atc_enc = chardet.detect(f.read())["encoding"]
                    print(f"Irregular encoding ({atc_enc}) detected.")
                    atc_df = pd.read_csv(
                        atc_path, dtype=str, encoding=atc_enc, na_values=na_values
                    )
                # Clean column names
                info_df.columns = normalize_column_names(info_df.columns)
                atc_df.columns = [
                    "添付文書ID",
                    "枝番号",
                    "ATC5",
                    "ATC7",
                    "ATC分類",
                    "ATC分類E",
                ]
                # Select columns
                atc_df = atc_df[["添付文書ID", "枝番号", "ATC5", "ATC7"]]
                # Merge
                final_df = pd.merge(
                    info_df, atc_df, on=["添付文書ID", "枝番号"], how="left"
                )
                # Drop columns
                final_df = final_df[["商品名", "HOT番号", "YJコード", "ATC5", "ATC7"]]
                for atc_col in ["ATC5", "ATC7"]:
                    final_df = update_atc(final_df, atc_col, atc_alt_table)
                atc_tables.append(final_df)
            else:
                print(f"Either info_all.txt or japic_who_atc.txt missing in {d}.")

    if atc_tables:
        return atc_tables

    raise ValueError("ATC-related source tables were not found.")
