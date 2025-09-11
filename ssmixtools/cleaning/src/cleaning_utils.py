"""general utils"""

import os
import glob
import shutil
from typing import Callable
from ctypes import c_int
from multiprocessing import Manager, current_process
from concurrent.futures import as_completed, ProcessPoolExecutor
from tqdm import tqdm
import numpy as np
import pandas as pd
from .cleaning_settings import get_cln_settings
from ...generals.general_utils import test_generator, all_values_to_int
from ...generals import general_config as config


def move_internal_files():
    """Moves internal files to the output directory"""
    internal_dir = get_cln_settings("CLN_INTERNAL_DIR")
    output_dir = get_cln_settings("CLN_OUTPUT_TABLES_DIR")
    for pattern in config.ALL_CLEANED_TABLE_PATTERNS:
        int_path_pattern = os.path.join(internal_dir, pattern)
        int_files = glob.glob(int_path_pattern)
        if int_files:
            # Delete old files
            del_file_pattern = os.path.join(output_dir, "**/", pattern)
            del_files = glob.glob(del_file_pattern, recursive=True)
            for file in del_files:
                if config.DEBUG_DIR not in file:
                    os.remove(file)
            # Move new files to the output directory
            for file in int_files:
                file_name = os.path.basename(file)
                file_tag = file_name.split("_")[-1].replace(".csv", "")
                dst_dir = os.path.join(output_dir, file_tag)
                if not os.path.exists(dst_dir):
                    os.mkdir(dst_dir)
                dst = os.path.join(dst_dir, file_name)
                shutil.move(file, dst)


def _parallel_map_partitions_cln(
    function: Callable,
    df: pd.DataFrame | str,
    temp_file_path: str,
    lock,
    shared_file_no: c_int,
    file_tag: str,
    single_file: bool,
    single_stat_file: bool,
    file_tag_as_arg: bool,
    pid_as_arg: bool,
    dob_map_as_arg: bool,
    dob_map: pd.DataFrame,
    header: bool,
    index: bool,
    **kwargs,
) -> dict:
    """Helper function for 'parallel_map_partitions_cln'.

    This function is passed to child processes, and each process executes it.
    See 'parallel_map_partitions_cln' for details.
    """
    # Get the child process ID
    process = current_process()
    pid = process.pid
    if isinstance(df, str):
        df = pd.read_csv(
            df,
            dtype=str,
            na_values=config.NA_VALUES,
            header=0,
        )

    # Execute the given custom function
    if file_tag_as_arg:
        kwargs = {"file_tag": file_tag, **kwargs}
    if pid_as_arg:
        kwargs = {"pid": pid, **kwargs}
    if dob_map_as_arg:
        kwargs = {"dob_map": dob_map, **kwargs}
    result = function(df, **kwargs)
    # If the result is a tuple, extract df and stats. Otherwise, only df is returned.
    if isinstance(result, tuple) and len(result) == 2:
        df, stats = result
    else:
        df = result
        stats = None

    # Save
    if temp_file_path is not None:
        # Aggregating files into a single file
        if single_file:
            if "*" in temp_file_path:
                if file_tag is not None:
                    saving_path = temp_file_path.replace("*", file_tag)
                else:
                    saving_path = temp_file_path.replace("*", "")
            else:
                if file_tag is not None:
                    saving_path = temp_file_path.replace(".csv", f"_{file_tag}.csv")
            with lock:
                if os.path.exists(saving_path):
                    df.to_csv(saving_path, mode="a", header=False, index=index)
                else:
                    df.to_csv(saving_path, mode="w", header=header, index=index)

        # Saving files separately by child processes
        else:
            # Count up the file number
            with lock:
                current_file_no = shared_file_no.value
                shared_file_no.value += 1
            if "*" in temp_file_path:
                saving_path = temp_file_path.replace(
                    "*", f"{current_file_no}_{file_tag}"
                )
            else:
                saving_path = temp_file_path.replace(
                    ".csv", f"_{current_file_no}_{file_tag}.csv"
                )
            df.to_csv(saving_path, mode="w", header=header, index=index)

    # Return stats
    if single_stat_file:
        return stats

    # If single_stat_file is false, then stats are returned separately by file tags.
    stats = {file_tag: stats}

    return stats


def parallel_map_partitions_cln(
    csv_path_pattern: str,
    function: Callable,
    chunksize: int,
    output_csv_path: str = None,
    single_file: bool = True,
    single_stat_file: bool = True,
    file_tag_as_arg: bool = False,
    pid_as_arg: bool = False,
    dob_map_as_arg: bool = False,
    header: bool = True,
    index: bool = False,
    clear_temp_dir=True,
    **kwargs,
) -> list[dict]:
    """Maps the custom function to chunks of a csv files using multiprocessing.

    The custom function must return a dataframe, and it can also return a analytics (dictionary) as additional output.
    That is, the custom function ends like the followings:'return df, analytics' or 'return df'

    Args:
        csv_path_pattern (str): Target tables are searched with this pattern. Ensure to include one wildcard '*' in it.
            Alternatively, you can pass a list of paths.
        function (Callable): Custom function that is to be mapped to the csv table.
            This function is expected to take a pd.DataFrame as its first argument.
        chunksize (int): Each table is loaded chunk by chunk with this chunk size.
        output_csv_path (str): Output tables are saved in this path. Include wildcards ('*') if necessary.
        single_file (bool): If true, all tables processed at child processes are aggregated and saved as a single file.
        single_stat_file (bool): If false, then stats are returned separately by file tags.
        file_tag_as_arg (bool): If True, the file identity tag 'file_tag' is passed as an argument to the custom function.
        pid_as_arg (bool): If true, a child process ID (pid) is passed as an argument to the custom function.
        dob_map_as_arg (bool): If true, a table containing ID-DOB pairs are loaded and passed to child processes.
        header (bool): If true, the processed tables are saved with header.
        index (bool): If true, the indexes of processed tables are also saved as a column of CSV file.
        clear_temp_dir (bool): If true, the temporary file directory is cleared.
            Set this to False if you use files remaining in the temporary directory.
    Returns:
        stats_list (list of dictionaries): List of dictionaries that store statistics.
    """
    # Define variables.
    temp_dir = get_cln_settings("CLN_TEMP_DIR")
    test = get_cln_settings("CLN_TEST")
    source_dir = get_cln_settings("CLN_SOURCE_DIR")
    max_workers = get_cln_settings("CLN_MAX_WORKERS")
    temp_file_name = os.path.basename(output_csv_path) if output_csv_path else None
    temp_file_path = os.path.join(temp_dir, temp_file_name) if output_csv_path else None

    # Clear the temporary file directory
    if clear_temp_dir:
        for file in os.listdir(temp_dir):
            path = os.path.join(temp_dir, file)
            os.remove(path)

    # Load all patient DOB tables if necessary
    dob_map_stock = {}
    if dob_map_as_arg:
        dob_path_pattern = os.path.join(source_dir, "**", config.DOB_MAP_PATTERN)
        dob_maps = glob.glob(dob_path_pattern, recursive=True)
        for file in dob_maps:
            file_tag = file.split("_")[-1].replace(".csv", "")
            dob_map = pd.read_csv(file, header=0, dtype=str, na_values=config.NA_VALUES)
            dob_map_stock[file_tag] = dob_map

    # Create a generator that yields dataframe chunks.
    def _dataframe_generator(csv_path_pattern, chunksize):
        if isinstance(csv_path_pattern, list):
            paths = csv_path_pattern
        elif "**" in csv_path_pattern:
            paths = glob.glob(csv_path_pattern, recursive=True)
        else:
            paths = glob.glob(csv_path_pattern)
        for path in paths:
            if config.DEBUG_DIR not in path:
                # Get the file tag
                file_name = os.path.basename(path)
                file_name_elements = file_name.split("_")
                file_tag = file_name_elements[-1].replace(".csv", "")
                if chunksize != -1:
                    df_reader = pd.read_csv(
                        path,
                        chunksize=chunksize,
                        na_values=config.NA_VALUES,
                        header=0,
                    )
                    for chunk in df_reader:
                        yield chunk, file_tag
                else:
                    yield path, file_tag

    chunk_iterator = _dataframe_generator(csv_path_pattern, chunksize)

    # Truncate iterator for testing
    if test:
        chunk_iterator = test_generator(
            chunk_iterator, test_chunks=get_cln_settings("CLN_TEST_CHUNKS")
        )
    # Map functions to partition dataframes.
    stats_list = []
    # Execute parallelism
    with ProcessPoolExecutor(max_workers=max_workers) as executor, Manager() as manager:
        lock = manager.Lock()
        shared_file_no = manager.Value("i", 0)
        futures = [
            executor.submit(
                _parallel_map_partitions_cln,
                function=function,
                df=chunk,
                temp_file_path=temp_file_path,
                file_tag=file_tag,
                single_file=single_file,
                lock=lock,
                shared_file_no=shared_file_no,
                header=header,
                index=index,
                single_stat_file=single_stat_file,
                file_tag_as_arg=file_tag_as_arg,
                pid_as_arg=pid_as_arg,
                dob_map_as_arg=dob_map_as_arg,
                dob_map=dob_map_stock.get(file_tag),
                **kwargs,
            )
            for chunk, file_tag in chunk_iterator
        ]

        for future in tqdm(
            as_completed(futures), total=len(futures), desc="Processing tasks"
        ):
            stats = future.result()
            if stats is not None:
                stats_list.append(stats)

    # Clear old files
    if output_csv_path is not None:
        if "*" in output_csv_path:
            old_file_name_pattern = output_csv_path
        else:
            old_file_name_pattern = os.path.basename(output_csv_path).replace(
                ".csv", "*.csv"
            )
        old_file_dir = os.path.dirname(output_csv_path)
        old_file_pattern = os.path.join(old_file_dir, old_file_name_pattern)
        old_files = glob.glob(old_file_pattern)
        if old_files:
            # The test mode creates a directory, and move old files into it instead of deleting them.
            if test:
                final_output_dir = get_cln_settings("CLN_OUTPUT_DIR")
                init_time = get_cln_settings("CLN_INIT_TIME")
                debug_dir = os.path.join(final_output_dir, config.DEBUG_DIR)
                if not os.path.exists(debug_dir):
                    os.mkdir(debug_dir)
                time_dir = os.path.join(debug_dir, init_time)
                if not os.path.exists(time_dir):
                    os.mkdir(time_dir)
                subdir_name = f"before_{function.__name__}"
                subdir = os.path.join(time_dir, subdir_name)
                if not os.path.exists(subdir):
                    os.mkdir(subdir)
                for old_file in old_files:
                    file_name = os.path.basename(old_file)
                    debug_dst = os.path.join(subdir, file_name)
                    shutil.move(old_file, debug_dst)

            # Delete old files
            else:
                for old_file in old_files:
                    os.remove(old_file)

        # Move processed files to the output directory
        if "*" in temp_file_path:
            created_files = glob.glob(temp_file_path)
        else:
            created_files = glob.glob(temp_file_path.replace(".csv", "*.csv"))
        dst_dir = os.path.dirname(output_csv_path)
        for temp_file in created_files:
            temp_file_name = os.path.basename(temp_file)
            dst = os.path.join(dst_dir, temp_file_name)
            shutil.move(temp_file, dst)
    return stats_list


def remove_method_from_jlac10(jlac10_codes: pd.Series) -> pd.Series:
    """Replaces the methodology segment of JLAC10 codes with bars ('---')"""
    new_jlac10_codes = jlac10_codes.str.replace(
        r"(\w{12})\w{3}(\w{2})", r"\1---\2", regex=True
    )
    return new_jlac10_codes


def clean_drug_names(drug_names: pd.Series) -> pd.Series:
    """Crop drug names.

    This process is intended to enhance the performance of text-to-code mapping processes.

    This cleans drug product names like the example shown below:
        'テスト薬剤 100mg (メーカー名)' -> 'テスト薬剤'

    Args:
        drug_names (pd.Series): Series of drug names
    Returns:
        cropped (pd.Series): Cleaned drug names.
    """
    # Fill nan with empty strings for string operations
    cropped = drug_names.fillna("").copy()
    # Remove white spaces from product names
    cropped = cropped.str.replace(r"\s+", "", regex=True)
    # Remove other unnecessary characters
    cropped = cropped.str.replace(config.R_UNNECESSARY_CHARACTERS, "", regex=True)
    # Remove bracketed parts (e.g, '(麻)', '「メーカー」 etc.) from product names
    cropped = cropped.str.replace(config.R_BRACKETED, "", regex=True)
    # Remove common units from product names
    cropped = cropped.str.replace(config.R_COMMON_UNITS, "", regex=True)
    # Remove unnecessary trail characters
    cropped = cropped.str.replace(config.R_UNNECESSARY_TAILS, "", regex=True)
    # Validate drug name length after cropping
    name_lengths = cropped.str.len()
    too_short = name_lengths < config.MIN_CROPPED_DRUG_NAME_LENGTH
    # Reset drug names that are too short after cropping back to the originals
    cropped = cropped.mask(too_short, drug_names)
    # Replace empty strings with null
    cropped = cropped.replace("", None)

    return cropped


def load_mapping_table(
    original_code_system: str,
    target_code_system: str,
    prefix: str = None,
    original_col_idx: int = 0,
    target_col_idx: int = 1,
    preprocess_drug_names: bool = False,
) -> pd.DataFrame:
    """Loads a code-mapping table.

    CSV files are searched with the pattern of '<original_code_system>_to_<target_code_system>.csv.
    Ensure that you have named mappingtable CSV files properly.
    The table must have a header.
    The loaded table is supposed to have two columns. The first column contains the original codes, and the second contains the target codes.
    The first and second columns are named as 'original' and 'target' respectively.
    You can explicitly control the index of both original and target columns by original_col_idx and target_col_idx.

    Args:
        orignal_code_system (str): Original coding system to be mapped to the target code system.
        target_code_system (str): Name of the target code system, such as ATC or ICD10.
        prefix (str, optional): Prefix to be prepended to the file name.
            This is expected to be either 'optional' or 'generic'.
        original_col_idx (int, optional): Index of the column that contains the values to be mapped.
        target_col_idx (int, optional): Index of the column that contains the values to be mapped to.
        preprocess_drug_names (bool): If true, the drug names in the first column are preprocessed by 'clean_drug_names()'.
        header (int, optional): Index of the header row. Default is none, and no row is used as the header.
            (This is an argument of pd.read_csv().)
    Returns:
        original_to_target (pd.DataFrame): Loaded mapping table.
    """
    # Load params
    reference_dir = get_cln_settings("CLN_REFERENCE_DIR")
    # Load mapping table
    map_csv_name = f"{original_code_system}_to_{target_code_system}.csv"
    if isinstance(prefix, str):
        map_csv_name = f"{prefix}_{map_csv_name}"
    map_csv_path = os.path.join(reference_dir, map_csv_name)
    if not os.path.exists(map_csv_path):
        created_ref_dir = get_cln_settings("CLN_CREATED_REF_DIR")
        created_map_path = os.path.join(created_ref_dir, map_csv_name)
        if os.path.exists(created_map_path):
            map_csv_path = created_map_path
        else:
            raise FileNotFoundError(f"{map_csv_path} not found.")

    original_to_target = pd.read_csv(
        map_csv_path,
        na_values=config.NA_VALUES,
        dtype=str,
        usecols=[original_col_idx, target_col_idx],
        # NOTE: All tables are supposed to have a header.
        header=0,
    )
    original_to_target.columns = [config.COL_ORIGINAL, config.COL_TARGET]
    original_to_target = original_to_target.fillna("")

    # Remove white spaces
    for col in original_to_target.columns:
        original_to_target[col] = original_to_target[col].str.strip()
    # Clean drug product names
    if preprocess_drug_names:
        # NOTE: Preprocessing texts may result in OneToMany relationships. Ensure no unintended mapping occurs because of this process.
        original_to_target[config.COL_ORIGINAL] = clean_drug_names(
            original_to_target[config.COL_ORIGINAL]
        )
    # Filling empty strings with nan
    original_to_target = original_to_target.replace("", None)
    # Drop rows with missing original values
    missing_original = original_to_target[config.COL_ORIGINAL].isna()
    original_to_target = original_to_target.loc[~missing_original, :]
    # Drop duplicates
    original_to_target["code_length"] = original_to_target[config.COL_TARGET].str.len()
    original_to_target = original_to_target.sort_values(
        by=["code_length", config.COL_TARGET], ascending=[False, True]
    )
    original_to_target = original_to_target.drop("code_length", axis=1)
    original_to_target = original_to_target.drop_duplicates(
        keep="first", subset=[config.COL_ORIGINAL]
    )

    return original_to_target


def map_icd10_to_text(
    icd10_codes: pd.Series, icd10_to_text: pd.DataFrame = None
) -> np.ndarray:
    """Maps ICD-10 codes to texts.

    Args:
        icd10_codes (pd.Series): Series of ICD-10 codes.
        icd10_to_text (pd.DataFrame): Table to map ICD-10 to texts. If not given, this function
            tries to load it from its CSV source file.
    Returns:
        translated (np.ndarray): Series of ICD-10 names.
    """
    # Load mapping table
    if icd10_to_text is None:
        icd10_to_text = load_mapping_table(config.ICD10, "text", target_col_idx=1)
        icd10_to_text = icd10_to_text.rename(
            columns={
                config.COL_ORIGINAL: config.ICD10,
                config.COL_TARGET: "text",
            }
        )
    else:
        icd10_to_text.columns = [config.ICD10, "text"]
    # Make the input series as a dataframe for merging operation
    icd10_codes = pd.DataFrame(icd10_codes)
    icd10_codes.columns = [config.ICD10]

    # Map codes to texts
    icd10_codes = icd10_codes.merge(icd10_to_text, how="left", on=config.ICD10)
    translated = icd10_codes["text"].values

    return translated


def map_atc_to_text(
    atc_codes: pd.Series, atc_to_text: pd.DataFrame = None
) -> np.ndarray:
    """Map ATC codes to texts.

    Args:
        atc_codes (pd.Series): Series of ATC codes.
        atc_to_text (pd.DataFrame): Table to map ATC to texts. If not given, this function
            tries to load it from its CSV source file.
    Returns:
        translated (np.ndarray): Series of ATC names.
    """
    # Load mapping table
    if atc_to_text is None:
        atc_to_text = load_mapping_table(config.ATC, "text", target_col_idx=1)
        atc_to_text = atc_to_text.rename(
            columns={
                config.COL_ORIGINAL: config.ATC,
                config.COL_TARGET: "text",
            }
        )
    else:
        atc_to_text.columns = [config.ATC, "text"]
    # Make the input series as a dataframe for merging operation
    atc_codes = pd.DataFrame(atc_codes)
    atc_codes.columns = [config.ATC]

    # Map codes to texts
    atc_codes = atc_codes.merge(atc_to_text, how="left", on=config.ATC)
    translated = atc_codes["text"].values

    return translated


def map_jlac10_to_text(
    jlac10_codes: pd.Series,
    readable: bool = False,
    japanese: bool = False,
    segments_to_text: pd.DataFrame = None,
) -> np.ndarray:
    """Creates a series of text expressions of given JLAC10 codes.

    Args:
        jlac10_codes (pd.Series): Series of JLAC10 codes
        readable (bool): If true, codes are translated without methodology part in a readable format.
        japanese (bool): If true, the codes are translated into Japanese instead of English.
            This argument is ignored if the argument 'segments_to_text' is given.
        segments_to_text (pd.DataFrame): Table to map JLAC10 segments to texts. If not given, this function
            tries to load it from its CSV source file.
    Returns:
        translated (np.ndarray): Series of text expressions of JLAC10 codes
    """
    # Load mapping table
    target_col_idx = 2 if japanese else 1
    if segments_to_text is None:
        segments_to_text = load_mapping_table(
            "JLAC10_segments", "text", target_col_idx=target_col_idx
        )
        segments_to_text = segments_to_text.rename(
            columns={config.COL_ORIGINAL: "segment", config.COL_TARGET: "text"}
        )
    else:
        segments_to_text.columns = ["segment", "text"]

    # Make the input series as a dataframe for merging operation
    jlac10_codes = pd.DataFrame(jlac10_codes)
    jlac10_codes.columns = ["code"]

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
        jlac10_codes["segment"] = (
            "*" * start + jlac10_codes["code"].str.slice(start, end) + "*" * (17 - end)
        )
        jlac10_codes = jlac10_codes.merge(segments_to_text, how="left", on="segment")
        jlac10_codes["text"] = jlac10_codes["text"].fillna("")
        jlac10_codes = jlac10_codes.rename(columns={"text": description})
    # Additionally, mapping the JLCC10 codes with unique result identifiers
    description = "result_identifier"
    jlac10_codes["segment"] = (
        jlac10_codes["code"].str.slice(0, 9)
        + "*" * 6
        + jlac10_codes["code"].str.slice(15, 17)
    )
    jlac10_codes = jlac10_codes.merge(segments_to_text, how="left", on="segment")
    jlac10_codes["text"] = jlac10_codes["text"].fillna("")
    jlac10_codes[description] = jlac10_codes["text"].mask(
        jlac10_codes["text"] == "", jlac10_codes[description]
    )
    jlac10_codes = jlac10_codes.drop(["text", "segment"], axis=1)

    # Reorder columns
    if readable:
        text_order = [
            "specimen",
            "analyte",
            "result_identifier",
            "identification",
        ]
    else:
        text_order = descriptions

    # Concatenate all the texts expressions of the segments
    jlac10_codes["text"] = ""
    for i, col in enumerate(text_order):
        # Cleaning before concatenation
        jlac10_codes[col] = jlac10_codes[col].str.strip()
        # Remove commas
        jlac10_codes[col] = jlac10_codes[col].str.replace(", ", " ")
        jlac10_codes[col] = jlac10_codes[col].str.replace(",", " ")
        # Separate with commas ','
        if i != 0:
            jlac10_codes.loc[:, "text"] = jlac10_codes["text"] + ","

        jlac10_codes.loc[:, "text"] = jlac10_codes["text"] + jlac10_codes[col]

    # Clean texts
    if readable:
        jlac10_codes["text"] = jlac10_codes["text"].str.replace(
            r"\s*\(complete blood count\)\s*", "", regex=True
        )
        jlac10_codes["text"] = jlac10_codes["text"].str.replace(
            r"\s*\(including others\)\s*", "", regex=True
        )
    jlac10_codes["text"] = jlac10_codes["text"].str.strip()
    translated = jlac10_codes["text"].values
    return translated


def convert_timedelta_to_timestamp(
    df: pd.DataFrame, timestamp_cols: list, dob_map: pd.DataFrame
) -> pd.DataFrame:
    """Converts timedelta values into actual timestamps by adding patients' DOBs.

    Args:
        df (pd.DataFrame): Dataframe to be processed.
        timestamp_cols (list): List of name of columns that store timedelta values.
        dob_map (pd.DataFrame): Table containing a column of patient IDs and another column of DOBs.
    Returns:
        df (pd.DataFrame): Processed dataframe
    """
    # Add a column of DOB
    df = pd.merge(left=df, right=dob_map, on=config.COL_PID, how="left")

    # Add timedelta values to DOBs
    df[config.COL_DOB] = pd.to_datetime(df[config.COL_DOB], format="%Y%m%d")
    for col in timestamp_cols:
        df[col] = df[config.COL_DOB] + pd.to_timedelta(df[col])

    # Drop DOB column
    df = df.drop(config.COL_DOB, axis=1)

    return df


def assign_unique_record_numbers(
    df: pd.DataFrame, data_type_tag: str, file_tag: str, pid: int
):
    """Assigns unique IDs to all records.

    Each record ID is composed of some components like this:
        <successive number><child process ID><data-type tag><file identity tag>

    The successive number starts from zero and increases by one inside each child process.
    A child process ID is appended after the number to avoid overlaps among processes.
    A data-type tag is appended to avoid overlaps among data types, and a file identity tag to avoid overlaps among
    different data sources (i.e., hospitals, health care systems, etc).

    Args:
        df (pd.DataFrame): Dataframe to be processed
        data_type_tag (str): This tag can be any arbitrary strings; however, because this tag is used to avoid ID overlaps
            among data types, tag should be designed to identify data types, such as 'adt22'.
        file_tag (str): File identity tag. This is passed by 'parallel_map_partitions'.
        pid (int): Child process ID.
    Returns:
        df (pd.DataFrame): Processed dataframe
    """
    # Try to get the latest number from the  environment variable
    start_number = int(os.environ.get(f"LATEST_RECORD_ID_NO_{pid}", "0"))
    latest_number = int(start_number) + len(df)

    # Assign unique numbers to each record
    df[config.COL_RECORD_ID] = np.arange(start_number, latest_number)

    # Append a tag and process ID to ensure that all signed IDs are unique
    df[config.COL_RECORD_ID] = (
        df[config.COL_RECORD_ID].astype(str) + str(pid) + data_type_tag + file_tag
    )

    # Update the environment variable
    # NOTE: This environment variable is not shared among processes, this is only valid in a single child process.
    #   Do not modify this script in a way that it tries to share environment variables among processes.
    os.environ[f"LATEST_RECORD_ID_NO_{pid}"] = str(latest_number)

    return df


def validate_code(
    df: pd.DataFrame,
    code_col: str,
    code_pattern: str = None,
    system_col: str = None,
    system_pattern: str = None,
) -> pd.Series:
    """Validates coded data and their coding system using regular expressions.

    This is used by 'map_by_merge' function before applying merging operation
    to map original codes to another coding system.

    Args:
        df (pd.DataFrame): Dataframe to be validated.
        code_col (str): Name of column that stores coded data.
        code_pattern (str, optional): Coded data in 'code_col' are validated by checking if values
            match this pattern.
            Default is None, and if nothing is passed, no validation is performed to 'code_col'.
        system_col (str, optional): Name of column that stores the name of standardized coding system such as
            ICD-10 or ATC.
        system_pattern (str, optional): String value or a regular expression used to validate the coding system
            used. The default value is None, and if nothing is given, no validation is performed to
            'system_col'.
    Returns:
        valid_mask (pd.Series): Mask where true indicates validity. If neither 'code_col' nor 'system_col'
            is passed, None is returned instead of a mask, therefore this step is essentially skipped.
    """
    valid_mask = None
    if system_col and system_pattern:
        valid_mask = df[system_col].str.contains(system_pattern, na=False)
    if code_pattern:
        code_match = df[code_col].str.contains(code_pattern, na=False)
        if valid_mask is not None:
            valid_mask = valid_mask & code_match
        else:
            valid_mask = code_match

    return valid_mask


def map_by_merge(
    df: pd.DataFrame,
    mapping_table: pd.DataFrame,
    original_code_col: str,
    new_col_name: str,
    original_system_col: str = None,
    original_code_pattern: str = None,
    original_system_pattern: str = None,
    original_cropped_length: str = None,
    target_cropped_length: str = None,
    mapping_table_original_col: str = config.COL_ORIGINAL,
    mapping_table_target_col: str = config.COL_TARGET,
) -> pd.DataFrame:
    """Maps coded data in a column to another coding system.

    Args:
        df (pd.DataFrame): Dataframe to be processed.
        mapping_table (pd.DataFrame): Code-mapping table. This table is loaded by 'load_mapping_table'.
        original_code_col (str): Name of column that stores the coded values to be mapped.
        new_col_name (str): Name of the new column created by this mapping operation.
        original_system_col (str): See 'validate_code'.
        original_code_pattern (str): See 'validate_code'.
        original_system_pattern (str): See 'validate_code'.
        original_cropped_length (int): Length of the original codes used for mapping.
            The original codes are clopped to this length before mapping.
        target_cropped_length (int): Length of the target codes.
            The target codes are clopped to this length after mapping.
        mapping_table_original_col (str, optional): Name of column that stores the codes
             coded by the original coding system. Default is 'original'.
        mapping_table_target_col (str, optional): Name of column that stores the codes
             coded by the target coding system. Default is 'target'.
    Returns:
        df (pd.DataFrame): Dataframe with a new column of the values coded by the target
            coding system. Values in other columns are left intact.
    """
    # Set the key column for merge operation. Because this column is manipulated throughout this
    # process, a copy of the key column is created first.
    key_col = "key column"
    df[key_col] = df[original_code_col].copy()

    # Validate original codes before mapping if necessary.
    valid_mask = validate_code(
        df,
        original_code_col,
        original_code_pattern,
        original_system_col,
        original_system_pattern,
    )
    if isinstance(valid_mask, pd.Series):
        # pylint:disable=invalid-unary-operand-type
        df[key_col] = df[key_col].mask(~valid_mask, "")
    else:
        df[key_col] = df[key_col].fillna("")

    # Crop original codes for mapping if necessary.
    if original_cropped_length:
        df[key_col] = df[key_col].str.slice(0, original_cropped_length)

    # Mapping original codes to targets code by left-join.
    df = df.merge(
        mapping_table, left_on=key_col, right_on=mapping_table_original_col, how="left"
    )

    # Rename the mapped target code column
    df = df.rename(columns={mapping_table_target_col: new_col_name})

    # Crop target codes if necessary
    if target_cropped_length:
        df[new_col_name] = (
            df[new_col_name].fillna("").str.slice(0, target_cropped_length)
        )

    # Drop key columns, because this column was only needed for the merging operation
    df = df.drop([key_col, mapping_table_original_col], axis=1)

    # Replace empty strings with None for consistency.
    df[new_col_name] = df[new_col_name].replace("", None)

    return df


def backup_fill_from_secondary_code(
    df: pd.DataFrame,
    target_col: str,
    secondary_code_col: str,
    secondary_coding_system_col: str = None,
    standardized_code_pattern: str = None,
    standardized_code_system_pattern: str = None,
    secondary_cropped_length: str = None,
) -> pd.Series:
    """Fills missing codes with values from a secondary column.

    Args:
        df (pd.DataFrame): Dataframe to be processed.
        target_col (str): Name of the column to be filled.
        secondary_code_col: (str): Name of the secondary column from which values
            in 'target_col' are filled
        secondary_coding_system_col (str): Name of the column where the coding system names
            are stored.
        standardized_code_pattern (str): Regular expression to validate codes in the secondary column.
            See 'validate_code'.
        standardized_code_system_pattern (str): Regular expression to validate coding system names
            in the secondary column. See 'validate_code'.
        secondary_cropped_length (int): Maximum length to which the filled codes from the
            secondary column are cropped.
    Returns:
        filled (pd.Series): Column filled with the secondary column.
    """
    # Create a copy of the secondary column, because this column is subject to modifications throughout this process
    backups = df[secondary_code_col].copy()

    # Validate codes if necessary
    valid_mask = validate_code(
        df,
        secondary_code_col,
        standardized_code_pattern,
        secondary_coding_system_col,
        standardized_code_system_pattern,
    )

    # Filter by code validation
    if isinstance(valid_mask, pd.Series):
        # pylint:disable=invalid-unary-operand-type
        backups = backups.mask(~valid_mask, "")
    else:
        backups = backups.fillna("")

    # Crop codes
    if secondary_cropped_length:
        backups = backups.str.slice(0, secondary_cropped_length).replace("", None)

    # Replace empty strings with None for consistency.
    backups = backups.fillna("").replace(
        "", None
    )  # <- without fillna(""), an error may occur

    # FIll missing values
    filled = df[target_col].fillna(backups)

    return filled


def map_text_to_atc(df: pd.DataFrame, text_to_atc: pd.DataFrame) -> tuple:
    """Maps drug names to ATC codes.

    This is designed for text-to-ATC mapping using generic or optional text-to-ATC mapping tables,
    because similar steps are repeated in these processes.

    Args:
        df(pd.DataFrame): Table to be processed
        text_to_atc(pd.DataFrame): Text-to-ATC mapping table
    Returns:
        df(pd.DataFrame): Processed dataframe
        process_analytics(dict): Dictionary that contain analytic results of ATC mapping.
    """
    # Initialize
    process_analytics = {}
    atc_existing_before_mapping = ~(df[config.COL_ITEM_CODE].isna())
    irregular_atc_before_mapping = ~(
        df[config.COL_ITEM_CODE].str.contains(config.R_ATC_CODE, na=True)
    )

    # Preprocess
    df["cropped_text"] = clean_drug_names(df[config.COL_ITEM_NAME])

    # Create a new column 'generic ATC' by mapping text to ATC
    df = map_by_merge(
        df,
        text_to_atc,
        original_code_col="cropped_text",
        new_col_name="generic_atc",
    )

    # Filling missing 'ATC' column values with 'generic ATC'.
    df[config.COL_ITEM_CODE] = backup_fill_from_secondary_code(
        df,
        target_col=config.COL_ITEM_CODE,
        secondary_code_col="generic_atc",
    )
    df = df.drop("generic_atc", axis=1)

    # Inspect data
    missing_atc_mask = df[config.COL_ITEM_CODE].isna()
    atc_existing_after_mapping = ~(missing_atc_mask)
    irregular_atc_after_mapping = (
        ~(df[config.COL_ITEM_CODE].str.contains(config.R_ATC_CODE, na=True))
        & atc_existing_after_mapping
    )
    total_rows = len(df)
    n_missing_atc_after_mapping = int(missing_atc_mask.sum())
    n_atc_before_mapping = int(atc_existing_before_mapping.sum())
    n_atc_after_mapping = int(atc_existing_after_mapping.sum())
    n_irregular_atc_before_mapping = int(irregular_atc_before_mapping.sum())
    n_irregular_atc_after_mapping = int(irregular_atc_after_mapping.sum())
    missing_atc_counts = all_values_to_int(
        df[missing_atc_mask]["cropped_text"].value_counts().to_dict()
    )

    # Saving analytics to the dictionary
    process_analytics["records before mapping"] = total_rows
    process_analytics["all ATC codes before mapping"] = n_atc_before_mapping
    process_analytics["irregular ATC codes before mapping"] = (
        n_irregular_atc_before_mapping
    )
    process_analytics["all ATC codes after mapping"] = n_atc_after_mapping
    process_analytics["irregular ATC codes after mapping"] = (
        n_irregular_atc_after_mapping
    )
    process_analytics["missing ATC codes after mapping"] = n_missing_atc_after_mapping
    process_analytics["drug_names_with_missing_ATC_codes"] = missing_atc_counts
    # Drop cropped text col
    df = df.drop("cropped_text", axis=1)

    return df, process_analytics
