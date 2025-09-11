"""Utility functions for extraction"""

import os
import re
import gc
import glob
import json
import shutil
from typing import Callable, Union, List, Tuple, Any
from ctypes import c_int
from collections.abc import Generator
import unicodedata
from itertools import islice
from multiprocessing import Manager
from multiprocessing.synchronize import Lock
from concurrent.futures import as_completed, ProcessPoolExecutor
from tqdm import tqdm
import pandas as pd
import numpy as np
from .extraction_settings import get_ext_settings
from ...generals import general_config as config
from ...generals.general_utils import tally_stats, test_generator, all_values_to_int


def copy_intermediate_files() -> None:
    """Copies intermediate files into the output directory.
    This function is designed for debugging, therefore, this is unnecessary outside
    debugging situations.
    """
    print("Copying the intermediate files...")
    internal_dir = get_ext_settings("EXT_INTERNAL_DIR")
    output_dir = get_ext_settings("EXT_OUTPUT_DIR")
    init_time = get_ext_settings("EXT_INIT_TIME")
    debug_dir = os.path.join(output_dir, config.DEBUG_DIR)
    if not os.path.exists(debug_dir):
        os.mkdir(debug_dir)
    time_dir = os.path.join(debug_dir, init_time)
    shutil.copytree(internal_dir, time_dir)


def clear_temp_files() -> None:
    """Clears the temporary directory ('EXTRACTION_TEMP_DIR')."""
    temp_dir = get_ext_settings("EXT_TEMP_DIR")
    for old_file in os.listdir(temp_dir):
        os.remove(os.path.join(temp_dir, old_file))


def _parallel_map_partitions_ext_wrapper(
    function: Callable[
        [pd.DataFrame, Any], Union[tuple[pd.DataFrame, dict], pd.DataFrame]
    ],
    df: pd.DataFrame | str,
    single_file: bool,
    lock,
    shared_file_no: c_int,
    temp_file_path: str,
    header: bool,
    index: bool,
    **kwargs,
) -> dict:
    """This is a helper function for 'parallel_map_partitions_ext'."""
    if isinstance(df, str):
        df = pd.read_csv(df, dtype=str, na_values=config.NA_VALUES, header=0)
    # Apply a custom function to a chunk
    result = function(df, **kwargs)

    # If the result is a tuple, extract df and stats. Otherwise, only df is returned.
    if isinstance(result, tuple) and len(result) == 2:
        df, stats = result
    else:
        df = result
        stats = None

    # Save
    if temp_file_path is not None:
        if not single_file:
            # Count up the file number
            with lock:
                current_file_no = shared_file_no.value
                shared_file_no.value += 1
            if "*" in temp_file_path:
                temp_file_path = temp_file_path.replace("*", f"{current_file_no}")
            else:
                temp_file_path = temp_file_path.replace(
                    ".csv", f"_{current_file_no}.csv"
                )
            df.to_csv(temp_file_path, mode="w", header=header, index=index)
        else:
            if "*" in temp_file_path:
                temp_file_path = temp_file_path.replace("*", "")
            with lock:
                if os.path.exists(temp_file_path):
                    df.to_csv(temp_file_path, mode="a", header=False, index=index)
                else:
                    df.to_csv(temp_file_path, mode="w", header=header, index=index)
    else:
        # If temp_file_path is not given, nothing is saved by this function.
        pass

    return stats


def parallel_map_partitions_ext(
    csv_path: str,
    function: Callable[
        [pd.DataFrame, Any], Union[tuple[pd.DataFrame, dict], pd.DataFrame]
    ],
    chunksize: int = -1,
    output_csv_path: str = None,
    single_file: bool = True,
    header: bool = True,
    index: bool = False,
    **kwargs,
) -> list[dict]:
    """Maps a custom function to chunks of a csv files using multiprocessing.
    The custom function must take a pd.DataFrame as its first positional arg and
    return a pd.DataFrame, and it can also return an analytics (dictionary) as an additional output.

    That is, the custom function should look like the followings:
        def a_custom_func(df:pd.Dataframe, **kwargs):
            ...
            ...
            return df, analytics  (or,  return df)

    Args:
        csv_path (str): Path to a table that the custom function is applied to.
            If a path pattern with a wildcard '*' is passed, CSV files that matches the pattern are searched and used.
        function (Callable): Custom function that is to be mapped to the CSV table.
            This function is expected to take a pd.DataFrame as its first argument and returns
            a pd.DataFrame with or without an additional dictionary.
        chunksize (int): Chunksize for loading the CSV files.
            If chunksize is -1, then an entire CSV file is read by each child process.
        output_csv_path (str): Output CSV table is saved using this path. Include wildcards such as '*' if necessary.
            If files are saved separately (single_file==False), then files saved by child processes are saved with
            a file number in the name by replacing '.csv' with '_<file number>.csv'.
        single_file: If true, all tables processed at child processes are aggregated and saved as a single file.
        header (bool): If true, the processed tables are saved with header.
        index (bool): If true, the indexes of processed tables are also saved in the product CSV files.
    Returns:
        stats_list (list[dict]): List of dictionaries that store statistics.
    """
    # Define variables.
    max_workers = get_ext_settings("EXT_MAX_WORKERS")
    temp_dir = get_ext_settings("EXT_TEMP_DIR")
    if isinstance(output_csv_path, str):
        temp_file_name = os.path.basename(output_csv_path)
        temp_file_path = os.path.join(temp_dir, temp_file_name)
    else:
        temp_file_name = None
        temp_file_path = None

    # Clear temporary file directory
    clear_temp_files()

    # Create a generator that loads CSV tables in chunks.
    def _dataframe_generator(csv_path, chunksize):
        for path in glob.glob(csv_path):
            if chunksize != -1:
                df_reader = pd.read_csv(
                    path,
                    dtype=str,
                    chunksize=chunksize,
                    na_values=config.NA_VALUES,
                    header=0,
                )
                for chunk in df_reader:
                    yield chunk
            else:
                yield path

    chunk_iterator = _dataframe_generator(csv_path, chunksize)

    # Truncate the iterator for testing
    test_mode = get_ext_settings("EXT_TEST")
    if test_mode:
        chunk_iterator = test_generator(
            chunk_iterator, test_chunks=get_ext_settings("EXT_TEST_CHUNKS")
        )

    # Map the custom function to CSV tables using multiprocessing.
    stats_list = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor, Manager() as manager:
        lock = manager.Lock()
        shared_file_no = manager.Value("i", 0)
        futures = [
            executor.submit(
                _parallel_map_partitions_ext_wrapper,
                function=function,
                df=chunk,
                temp_file_path=temp_file_path,
                single_file=single_file,
                lock=lock,
                shared_file_no=shared_file_no,
                header=header,
                index=index,
                **kwargs,
            )
            for chunk in chunk_iterator
        ]

        for future in tqdm(
            as_completed(futures), total=len(futures), desc="Processing tasks"
        ):
            stats = future.result()
            if stats is not None:
                stats_list.append(future.result())

    # Clear old files
    if output_csv_path:
        if "*" in output_csv_path:
            old_file_pattern = output_csv_path
        else:
            old_file_pattern = output_csv_path.replace(".csv", "*.csv")
        old_files = glob.glob(old_file_pattern)
        for old_file in old_files:
            os.remove(old_file)

        # Move final products
        if "*" in temp_file_path:
            created_files = glob.glob(temp_file_path)
        else:
            created_files = glob.glob(temp_file_path.replace(".csv", "*.csv"))
        dst_dir = os.path.dirname(output_csv_path)
        for temp_file_path in created_files:
            temp_file_name = os.path.basename(temp_file_path)
            dst = os.path.join(dst_dir, temp_file_name)
            shutil.move(temp_file_path, dst)

    return stats_list


def _extraction_fn_wrapper(
    chunk: Union[pd.DataFrame, list, str],
    output_csv_col_names: list[str],
    function: Callable[[Any], list[list[str]]],
    temp_file_path: str,
    single_file: bool,
    postprocess_fn: Callable[[pd.DataFrame], pd.DataFrame],
    shared_file_no: c_int,
    lock: Lock,
    **kwargs,
) -> int:
    """
    Applies a custom function to extraction tasks and saves the results as a CSV table.
    This is a helper function for '_extract_in_parallel'.
    It first iterates over the input chunk, applying the custom function to
    each task to generate rows for a dataframe.
    The resulting dataframe is saved in a temporary file path and later moved to the final destination.

    Args:
        chunk (Union[pd.DataFrame, list, str]): Chunk of tasks to be processed.
            This is typically a list of objects, but can also be a pd.DataFrame or a CSV file path (str).
            If the chunk is a pd.DataFrame, pd.DataFrame.iterrows() is used for iteration.
            If the chunk is a string (path), pd.read_csv() is used to load the CSV file and iterate the rows.
        output_csv_col_names (list[str]): Column names for the final table.
        function (Callable): Custom function to process each task in the chunk.
            This function is expected to take each task as its first argument.
            and return a list of lists (rows for the dataframe).
            If 'chunk' is a pd.DataFrame (or CSV path), the function must take a pandas Series as the first argument ('task').
        temp_file_path (str): Path to the temporary file for saving the results.
        single_file (bool): If True, the resulting dataframes are aggregated into a single table.
        postprocess_fn (Callable): If provided, this function is applied to the product dataframe before saving it as CSV.
        shared_file_no (c_int): Integer shared by workers, used to determine file numbers in multiprocessing.
        lock (Lock): Lock for multiprocessing to ensure file writing is safe.
    Returns:
        int: Total number of rows in the product dataframe.
    """

    rows = []
    # Iterate through the chunk of tasks, and apply the custom function
    if isinstance(chunk, str):
        chunk = pd.read_csv(chunk, dtype=str, na_values=config.NA_VALUES, header=0)
    if isinstance(chunk, pd.DataFrame):
        for _, task in chunk.iterrows():
            # 'new_rows' is expected to be a list of lists.
            new_rows = function(task, **kwargs)
            if new_rows:
                rows += new_rows
    elif isinstance(chunk, list):
        for task in chunk:
            new_rows = function(task, **kwargs)
            if new_rows:
                rows += new_rows

    # Aggregate the results to create a table
    product_df = pd.DataFrame(rows, columns=output_csv_col_names)
    if postprocess_fn is not None:
        product_df = postprocess_fn(product_df)

    # Save as a single file
    if single_file:
        with lock:
            if "*" in temp_file_path:
                temp_file_path = temp_file_path.replace("*", "")
            if os.path.exists(temp_file_path):
                product_df.to_csv(temp_file_path, mode="a", header=False, index=False)
            else:
                product_df.to_csv(temp_file_path, mode="w", header=True, index=False)

    # Save files separately
    else:
        with lock:
            current_file_no = shared_file_no.value
            shared_file_no.value += 1
        if "*" in temp_file_path:
            temp_file_path = temp_file_path.replace("*", f"{current_file_no}")
        else:
            temp_file_path = temp_file_path.replace(".csv", f"_{current_file_no}.csv")
        product_df.to_csv(temp_file_path, mode="w", header=True, index=False)

    return len(product_df)


def _extract_in_parallel(
    function: Callable[[Any], list[list[str]]],
    chunk_iterator: Generator,
    output_csv_path: str,
    output_csv_col_names: list[str],
    single_file: bool,
    postprocess_fn: Callable[[pd.DataFrame], pd.DataFrame],
    **kwargs,
) -> dict:
    """Extracts records from an SS-MIX2 storage using a custom function designed to extract a specific record type.
    This is a helper function used in extract_using_csv, extract_using_generator, extract_using_data_type.
    Args:
        function (Callable): Custom function designed to extract records of a specific record type.
        chunk_iterator (Generator): Generator object that yields tasks.
        output_csv_path (str, optional): Path for saving the output CSV table.
        output_csv_col_names (list): Column names of the output CSV table.
        single_file (bool, optional): If true, tables are saved separately by child processes.
        postprocess_fn (Callable): Function that is applied to the table created by the main function ('function').
            This function must take a pd.DataFrame as its first argument.
            See '_extraction_fn_wrapper' for details.
    Returns:
        analytics (dict): Dictionary containing analytics of the process.
    """
    # Initialize variables.
    test_mode = get_ext_settings("EXT_TEST")
    max_workers = get_ext_settings("EXT_MAX_WORKERS")
    temp_dir = get_ext_settings("EXT_TEMP_DIR")
    # Clear temp dir
    clear_temp_files()
    # Truncate iterator for testing
    if test_mode:
        chunk_iterator = test_generator(
            chunk_iterator, test_chunks=get_ext_settings("EXT_TEST_CHUNKS")
        )
    # Temporary file path
    temp_file_path = os.path.join(temp_dir, os.path.basename(output_csv_path))
    # Execute parallelism
    analytics = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor, Manager() as manager:
        lock = manager.Lock()
        shared_file_no = manager.Value("i", 0)
        futures = [
            executor.submit(
                _extraction_fn_wrapper,
                chunk=chunk,
                output_csv_col_names=output_csv_col_names,
                function=function,
                temp_file_path=temp_file_path,
                single_file=single_file,
                lock=lock,
                shared_file_no=shared_file_no,
                postprocess_fn=postprocess_fn,
                **kwargs,
            )
            for chunk in chunk_iterator
        ]

        for future in tqdm(
            as_completed(futures),
            total=len(futures),
            desc="Extracting data",
        ):
            analytics.append(future.result())

    # Clear old files
    if "*" in output_csv_path:
        old_files = glob.glob(output_csv_path)
    else:
        old_files = glob.glob(output_csv_path.replace(".csv", "*.csv"))
    for old_file in old_files:
        os.remove(old_file)
    # Move final products
    if "*" in temp_file_path:
        created_files = glob.glob(temp_file_path)
    else:
        created_files = glob.glob(temp_file_path.replace(".csv", "*.csv"))
    dst_dir = os.path.dirname(output_csv_path)
    for temp_file_path in created_files:
        temp_file_name = os.path.basename(temp_file_path)
        dst = os.path.join(dst_dir, temp_file_name)
        shutil.move(temp_file_path, dst)
    gc.collect()
    # Analytics
    analytics = {"total csv rows": int(np.array(analytics).sum())}

    return analytics


def extract_using_csv(
    function: Callable[[Any], list[list[str]]],
    chunksize: int,
    loaded_csv_path: str,
    output_csv_path: str,
    output_csv_col_names: list,
    single_file: bool = True,
    postprocess_fn: Callable[[pd.DataFrame], pd.DataFrame] = None,
    **kwargs,
) -> dict:
    """Extracts clinical records using a CSV file.
    The CSV file is expected to contain a task for extraction in each row. That is, the table is iterated row
    by row, and each row is treated as a task of record extraction.
    For example, each table row may contain a path to HL7 message file with some metadata. Child processes will receive
    this task, and execute data extraction.

    Args:
        function (Callable): Custom function for extraction.
        chunksize (int): Size of a task chunk passed to a child process.
        loaded_csv_path (str): CSV file path to be loaded.
            If wildcards are in the path, all files that match this pattern are loaded.
            This function loads the CSV file in chunks, and each chunk is further iterated row by row in child processes.
            The yielded rows are passed to the custom function.
        output_csv_path (str): Path for saving the output CSV table.
        output_csv_col_names (list): Column names of the output CSV table.
        single_file (bool, optional): If true, tables are saved separately by child processes. Default is true.
        postprocess_fn (Callable): Function that is applied to the table created by the main function ('function').
            This function must take a pd.DataFrame as its first argument.
    Returns:
        analytics (dict): Dictionary containing analytics of the process.
    """
    if "*" in loaded_csv_path:
        files = glob.glob(loaded_csv_path, recursive="**" in loaded_csv_path)
    else:
        files = [loaded_csv_path]

    def _df_chunk_generator(files, chunksize):
        for file in files:
            if chunksize != -1:
                reader = pd.read_csv(
                    file,
                    dtype=str,
                    na_values=config.NA_VALUES,
                    chunksize=chunksize,
                    header=0,
                )
                for chunk in reader:
                    yield chunk
            else:
                yield file

    chunk_iterator = _df_chunk_generator(files, chunksize)
    analytics = _extract_in_parallel(
        function=function,
        chunk_iterator=chunk_iterator,
        output_csv_path=output_csv_path,
        output_csv_col_names=output_csv_col_names,
        single_file=single_file,
        postprocess_fn=postprocess_fn,
        **kwargs,
    )
    return analytics


def extract_using_data_type(
    function: Callable[[Any], list[list[str]]],
    chunksize: int,
    data_type: str,
    single_file: bool = True,
    postprocess_fn: Callable[[pd.DataFrame], pd.DataFrame] = None,
    **kwargs,
) -> dict:
    """Extracts records by specifying a record type and a custom function.

    Args:
        function (Callable): Custom function for extraction.
        chunksize (int): Size of a task chunk passed to a child process.
        data_type (str): Record type defined by SS-MIX2.
        single_file (bool): If true, tables are saved separately by child processes.
        postprocess_fn (Callable): Function that is applied to the table created by the main function ('function').
            This function must take a pd.DataFrame as its first argument.
    Returns:
        analytics (dict): Dictionary containing analytics of the process.
    """
    file_paths_dir = get_ext_settings("EXT_FILE_PATHS_DIR")
    raw_table_dir = get_ext_settings("EXT_RAW_TABLE_DIR")
    loaded_csv_name = config.DATA_TYPE_PATH_PATTERN.replace("*", f"{data_type}_*")
    loaded_csv_pattern = os.path.join(file_paths_dir, loaded_csv_name)
    output_csv_name = config.TIME_SERIES_DATA_PATTERN.replace("*", f"{data_type}_*")
    output_csv_path = os.path.join(raw_table_dir, output_csv_name)
    output_csv_col_names = config.RECORD_TABLE_PARAMS[data_type]["all"]

    analytics = extract_using_csv(
        function=function,
        chunksize=chunksize,
        loaded_csv_path=loaded_csv_pattern,
        output_csv_path=output_csv_path,
        output_csv_col_names=output_csv_col_names,
        single_file=single_file,
        postprocess_fn=postprocess_fn,
        **kwargs,
    )
    return analytics


def extract_using_generator(
    function: Callable[[Any], list[list[str]]],
    chunksize: int,
    generator: Generator,
    output_csv_path: str,
    output_csv_col_names: list[str],
    single_file: bool = True,
    **kwargs,
) -> dict:
    """Extracts records by specifying a task generator and a custom function.
    Args:
        function (Callable): Custom function for extraction.
        chunksize (int): Size of a task chunk passed to a child process.
        generator (Generator, optional): Generator object that yield a single task for the custom function.
        output_csv_path (str): Path for saving the output CSV table.
        output_csv_col_names (list): Column names of the output CSV table.
        single_file (bool, optional): If true, tables are saved separately by child processes. Default is true.
    Returns:
        analytics (dict): Dictionary containing analytics of the process.
    """

    def _wrapper_generator(generator: Generator, chunksize: int) -> Generator[list]:
        """Yieds tasks in chunks using the original generator"""
        chunk = list(islice(generator, chunksize))
        while chunk:
            yield chunk
            chunk = list(islice(generator, chunksize))

    chunk_iterator = _wrapper_generator(generator, chunksize)
    analytics = _extract_in_parallel(
        function=function,
        chunk_iterator=chunk_iterator,
        output_csv_path=output_csv_path,
        output_csv_col_names=output_csv_col_names,
        single_file=single_file,
        postprocess_fn=None,
        **kwargs,
    )
    return analytics


def _parse_tree(
    current_level: int, target_level: int, abs_path: bool, current_path: str
) -> Generator[str]:
    """Helper function for 'parse_tree'.

    This function recursively yields all paths in the target level.
    """
    if current_level > target_level:
        return

    with os.scandir(current_path) as it:
        for entry in it:
            new_path = os.path.join(current_path, entry.name)
            if current_level == target_level:
                yield new_path if abs_path else entry.name
            else:
                yield from _parse_tree(
                    current_level + 1, target_level, abs_path, new_path
                )


def parse_tree(
    start_dir: str,
    target_level: int,
    abs_path: bool = False,
) -> Generator[str]:
    """Yields paths existing in the given directory tree level in an SS-MIX2 storage.

    The tree levels:
    1: 1st to 3rd characters of patient IDs.
    2: 4th to 6th characters of patient IDs.
    3: Full patient IDs. (If you want to extract patient IDs, this is the level.)
    4: Date folders or "-" folders. (Date folders store time-variable data, whereas "-" folders store static data.)
    5: Data type folders.
    6: Data files.

    Args:
        start_dir (str): Directory to start parsing the directory tree from.
            This path must be an absolute path.
        target_level(int, from 1 to 6): Level of interest.

        abs_path (bool): If true, this function returns absolute paths. If false, it returns only the base names.
    Yields:
            str : Path in the target level.
    """
    if not 1 <= target_level <= 6:
        raise ValueError("target_level must be an integer between 1 and 6.")
    # Ensure paths are absolute
    ssmixroot = os.path.abspath(get_ext_settings("SS-MIX_ROOT"))
    start_dir = os.path.abspath(start_dir)
    # Determine the current level
    start_level = start_dir.count("/") - ssmixroot.count("/")

    return _parse_tree(start_level + 1, target_level, abs_path, start_dir)


def patient_id_to_path(patient_id: str) -> str:
    """Converts a patient ID into the path to the patient's directory in an SS-MIX2 storage."""
    ssmixroot = get_ext_settings("SS-MIX_ROOT")
    patient_path = os.path.join(
        ssmixroot,
        patient_id[0:3],
        patient_id[3:6],
        patient_id,
    )
    return patient_path


def extract_element(segment: List, index: int, default_value: str = "") -> str:
    """Extracts a list element by indexing.
    If the index is out of range, the default value is returned.
    """
    return segment[index] if len(segment) > index else default_value


def get_code_from_segment(
    segment: list,
    index: int,
    code_system_pattern: str,
    code_relative_position: int = -2,
    text_relative_position: int = -1,
    separator: str = "^",
    default_value: str = "",
    force_output=True,
) -> tuple[str, str, str, bool]:
    """Extracts standardized medical codes from an HL7 message segment.

    The function parses strings containing medical codes separated by the separators ('^' by default)
    to extract the medical code and its paird text name.
    It also checks if the data was coded by the desired standardized coding system.

    According to the SS-MIX2 guideline ver 1.2h, there are six possible string patterns:
        '<local code>^<local name>^<local coding system>'
        '<standardized code>^<standardized name>^<standardized coding system>'
        '^^^<local code>^<local name>^<local coding system>'
        '^^^<standardized code>^<standardized name>^<standardized coding system>'
        '<local code>^<local name>^<local coding system>^<standardized code>^<standardized name>^<standardized coding system>'
        '<standardized code>^<standardized name>^<standardized coding system>^<local code>^<local name>^<local coding system>'

    The standard coding system name appears only at the index of 2 or 5 when the elements are separated by separators.

    Args:
        segment (list): HL7 message segment.
        index (int): Index of the segment part where the coded data exist. Elements in this part are expected to be separated by separators.
        code_system_pattern (str): Desired standardized coding system name in a string or regular expression pattern to find matches.
        code_relative_position (int, optional): Index of codes relative to that of the coding system name. Defaults to -2.
        text_relative_position (int, optional): Index of text names relative to that of the coding system name within the given data. Defaults to -1.
        separator (str, optional): Symbol used as a separator in the given data. Defaults to '^'.
        default_value (str, optional): Value used to fill in for missing values. Defaults to an empty string.
        force_output (bool, optional): If true, the function try to return values even if the code system does not match.
            If false, default values are returned.

    Returns:
        tuple (tuple[str, str, str, bool]): The code, text name, coding system, and
            a boolean flag indicating if the desired coding system was matched.
    """
    # Initialize variables
    code, text, system, code_system_matched = (
        default_value,
        default_value,
        default_value,
        False,
    )

    # Ensure that the given index is not out-of-range.
    if len(segment) > index:
        # Search for the desired standardized coding system name
        elements = segment[index].split(separator)
        code_system_idx = None

        try:
            for idx in [2, 5]:
                if re.match(code_system_pattern, elements[idx]):
                    code_system_idx = idx
                    code_system_matched = True
                    break
        except IndexError:
            pass

        # Extract the code and its text name if the coding system name is matched.
        if code_system_matched:
            code_idx = code_system_idx + code_relative_position
            text_idx = code_system_idx + text_relative_position
            code = elements[code_idx] if code_idx >= 0 else default_value
            text = elements[text_idx] if text_idx >= 0 else default_value
            system = elements[code_system_idx]

        # If the record is not encoded by the standardized coding system, try to return the raw data.
        elif force_output:
            # Search for available plain text data first.
            # According to the SS-MIX2 guideline ver 1.2h, plain text data are placed at either index 1 or 4.
            for idx in [1, 4]:
                if idx < len(elements):
                    if elements[idx]:
                        text = elements[idx]
                        code = elements[idx - 1]
                        if len(elements) > idx + 1:
                            system = elements[idx + 1]
                        break

            # If plain text data is not available, then search for encoded data next.
            else:
                for idx in [2, 5]:
                    if idx < len(elements):
                        if elements[idx]:
                            code = elements[idx]
                            if len(elements) > idx + 1:
                                text = elements[idx + 1]
                            if len(elements) > idx + 2:
                                system = elements[idx + 2]
                            break

        # If neither plain text nor code data is available, or if 'force_output == False',  all values are returned as default values.

    return code, text, system, code_system_matched


def get_values_with_unit(
    segment: list,
    segment_index: int,
    value_index: int = 0,
    unit_index: int = 1,
    separator: str = "^",
    joint: str = "",
    default_value: str = "",
) -> str:
    """Extracts a value and its paired unit from the given segment of an HL7 message.
    The value and unit are assumed to be separated by the '^' character.
    The function is intended for extracting data such as the number of prescription days from the OML-01 segment of an HL7 message.

    Args:
        segment (list): HL7 message segment containing the data to be extracted.
        segment_index (int): Index of the segment part where the value data exists.
        value_index (int, optional): Index of the hat-separated ('^') elements where the value data exists. Defaults to 0.
        unit_index (int, optional): Index for the unit. This is usually the index following the value. Defaults to 1.
        separator (str, optional): Character used to separate elements within the segment. Defaults to '^'.
        joint (str, optional): String used to join the value and unit.
            By default, the value and unit are directly concatenated with no additional characters (i.e., empty string).
        default_value (str, optional): Default value returned if the intended values are not found.
    Returns:
        str: Value and unit joined by the specified 'joint' string, or the 'default_value' if the intended values are not found.
    """
    try:
        segment_part = segment[segment_index]
        if separator in segment_part:
            subparts = segment_part.split(separator)
            return joint.join([subparts[value_index], subparts[unit_index]])
    except IndexError:
        pass  # Pass here to handle the error silently and proceed to return default_value
    return default_value


def _fix_jp_diacritics(text: str) -> str:
    """Concatenates Japanese characters with separated diacritics (゛or ゜).
    This operation joins characters with their respective diacritics, as shown below:
        ミトメス゛ -> ミトメズ
        ハ゜クリタキセル -> パクリタキセル
    Args:
        text (str): Input Japanese text that may contain separated diacritics.

    Returns:
        str: Cleaned text with concatenated diacritics.
    """
    # Encode
    encoded_text = text.encode(encoding="utf-8")

    for param in [
        # Params for joining Japanese 'dakuten' (full-width and half-width)
        (b"\xe3\x82\x9b", b"\xe3\x82\x99"),  # ゛(full)
        (b"\xef\xbe\x9e", b"\xe3\x82\x99"),  # ゛(half)
        # Params for joining Japanese 'handakuten' (full-width and half-width)
        (b"\xe3\x82\x9c", b"\xe3\x82\x9a"),  # ゜(full)
        (b"\xef\xbe\x9f", b"\xe3\x82\x9a"),  # ゜(half)
    ]:
        encoded_text = re.sub(*param, encoded_text)

    # Decode
    text = encoded_text.decode(encoding="utf-8")

    return text


def normalize_line(line: str) -> str:
    """Performs minium cleaing to a line of strings."""
    # Clean diacritics
    line = _fix_jp_diacritics(line)
    # Unicodedata normalization
    line = unicodedata.normalize("NFKC", line)
    # Normalize dashes
    line = re.sub(config.R_DASHES, "-", line)
    # Normalize white spaces
    line = line.strip()
    line = re.sub(r"\s+", " ", line)
    # Remove spaces adjacent to separators
    line = re.sub(r"\s*([\||\^|\~|\-|\.|\/|\_]{1})\s*", r"\1", line)

    return line


def hl7_to_list(
    file_path: str, segments_parsed: Union[List[str], Tuple[str, ...]] = None
) -> List[List[str]]:
    """Converts an HL7 v2.5 message into a list of lists, with each sublist corresponding to a segment.

    Args:
        file_path (str): Path to the HL7 message text file.
        segments_parsed (list or tuple, optional): List of segment IDs to be parsed,
            such as "MSH", "RXE". If not specified, all segments are parsed.

    Returns:
        List[List[str]]: List of lists, with each sublist containing elements of a segment.
            All strings are normalized with 'unicodedata.normalize()'.
    """
    encoding = get_ext_settings("HL7_ENCODING")
    # If no specific segments are passed, parse all segments.
    if segments_parsed is None:
        segments_parsed = ()

    # Convert segments_parsed to a tuple for faster lookups in startswith().
    if not isinstance(segments_parsed, tuple):
        segments_parsed = tuple(segments_parsed)

    hl7_message = []
    with open(file_path, encoding=encoding) as f:
        for line in f:
            # Normalize the line.
            line = normalize_line(line)
            # If no segments are specified, parse everything, otherwise parse selectively.
            if not segments_parsed or line.startswith(segments_parsed):
                hl7_message.append(line.split("|"))

    return hl7_message


def group_segments(
    hl7_message: List[List[str]], sequence_pattern: str
) -> List[List[str]]:
    """Groups HL7 message segments based on a specified sequence pattern.

    This function is primarily used to create practical segment groups such as
    a prescription order, an injection order, or a set of test results.

    Args:
        hl7_message (list): List of segments created by 'hl7_to_list'.
        sequence_pattern (str): Regular expression pattern representing the segment ID sequence.
            Segment IDs must be separated by commas.
            Example:
                sequence_pattern = r"SPM(,OBR(,OBX)+)+"
            Ensure that this pattern always starts with a valid HL7 segment ID (e.g., SPM, ORC, etc.), as the first
            three characters of the pattern are used for segment parsing.

    Returns:
        list: A list of lists, with each sublist containing segments that compose a valid group.
    """

    # Determine the first segment Id
    first_segment_id = sequence_pattern[:3]
    # Identify the indices of group beginnings and ends
    group_beginnings_and_ends = [
        idx for idx, segment in enumerate(hl7_message) if segment[0] == first_segment_id
    ]
    group_beginnings_and_ends.append(len(hl7_message))

    # Validate the segment sequence pattern for each group
    groups = []
    for idx in range(len(group_beginnings_and_ends) - 1):
        group = hl7_message[
            group_beginnings_and_ends[idx] : group_beginnings_and_ends[idx + 1]
        ]
        segment_sequence = ",".join([segment[0] for segment in group])
        # Add group to the list if it matches the sequence pattern
        if re.fullmatch(sequence_pattern, segment_sequence):
            groups.append(group)

    return groups


def inspect_csv(
    data_type: str,
    function: Callable[
        [pd.DataFrame, Any], Union[tuple[pd.DataFrame, dict], pd.DataFrame]
    ],
    chunksize: int,
) -> None:
    """Inspect CSV tables with the given function"""
    # Define variables
    raw_table_dir = get_ext_settings("EXT_RAW_TABLE_DIR")
    csv_name = config.TIME_SERIES_DATA_PATTERN.replace("*", f"{data_type}_*")
    csv_path_pattern = os.path.join(raw_table_dir, csv_name)
    # Execute the helper function
    stats_list = parallel_map_partitions_ext(
        csv_path=csv_path_pattern,
        function=function,
        chunksize=chunksize,
    )
    final_stats = tally_stats(stats_list)

    # Save the inspection results as JSON
    sheet_pattern = get_ext_settings("EXT_INSPECTION_SHEET_PTN")
    json_path = sheet_pattern.replace("*", data_type)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(final_stats, f, indent=2, ensure_ascii=False)


def multiindex_dict_to_nested_dict(multiindex_dict: dict) -> dict:
    """Converts a multi-indexed dictionary into a nested dictionary.
    A 'multi-indexed dictionary' has tuples as keys, often produced by
    pandas DataFrameGroupBy objects after applying `.to_dict()`. This function
    transforms those dictionaries into a nested dictionary format.

    Args:
        multiindex_dict (dict): Multi-indexed dictionary with tuples as keys.
    Returns:
        dict: Nested dictionary.
    """

    def _next_level(dictionary, idx):
        if idx not in dictionary:
            dictionary[idx] = {}
        return dictionary[idx]

    nested_dict = {}
    for keys, val in multiindex_dict.items():
        current_dict = nested_dict
        for key in keys[:-1]:
            current_dict = _next_level(current_dict, key)
        current_dict[keys[-1]] = val

    return nested_dict


def inspect_timestamps(df: pd.DataFrame, timestamp_cols: list[str]) -> dict:
    """Inspects timestamp columns in the dataframe for format consistency and irregular values.

    Args:
        df (pd.DataFrame): DataFrame containing timestamp columns.
        timestamp_cols (list): List of column names to examine.
    Returns:
        dict: A dictionary containing counts of timestamp formats and irregular values.
    """
    # Initialize results
    inspection_results = {"formats": {}, "irregular values": {}}
    # Counting timestamp columns
    for col in timestamp_cols:
        # Checking for timestamp formats.
        match_yyyymmdd = df[col].str.contains(config.R_YYYYMMDD, na=False)
        match_yyyymmddhhmm = df[col].str.contains(config.R_YYYYMMDDHHMM, na=False)
        match_yyyymmddhhmmss = df[col].str.contains(config.R_YYYYMMDDHHMMSS, na=False)
        match_yyyymmddhhmmssfff = df[col].str.contains(
            config.R_YYYYMMDDHHMMSSFFF, na=False
        )
        match_yyyymmddhhmmssfff_dot = df[col].str.contains(
            config.R_YYYYMMDDHHMMSSFFF_DOT, na=False
        )
        hours_over_23 = df[col].str.contains(config.R_HOURS_24_TO_47, na=False)
        missings = df[col].isnull()

        # Irregular patterns.
        irregular_timestamps = ~(
            match_yyyymmdd
            | match_yyyymmddhhmm
            | match_yyyymmddhhmmss
            | match_yyyymmddhhmmssfff
            | match_yyyymmddhhmmssfff_dot
            | missings
        )

        # Checking for 'zero-fill' patterns.
        zeros_below_dates = df[col].str.contains(config.R_ZEROS_BELOW_DATE, na=False)
        match_yyyymmdd0000 = match_yyyymmddhhmm & zeros_below_dates
        match_yyyymmdd000000 = match_yyyymmddhhmmss & zeros_below_dates
        match_yyyymmdd000000000 = match_yyyymmddhhmmssfff & zeros_below_dates
        match_yyyymmdd000000000_dot = match_yyyymmddhhmmssfff_dot & zeros_below_dates

        counts = {
            "YYYYMMDD": int(match_yyyymmdd.sum()),
            "YYYYMMDDHHMM": int(match_yyyymmddhhmm.sum()),
            "YYYYMMDD0000": int(match_yyyymmdd0000.sum()),
            "YYYYMMDDHHMMSS": int(match_yyyymmddhhmmss.sum()),
            "YYYYMMDD000000": int(match_yyyymmdd000000.sum()),
            "YYYYMMDDHHMMSSFFF": int(match_yyyymmddhhmmssfff.sum()),
            "YYYYMMDD000000000": int(match_yyyymmdd000000000.sum()),
            "YYYYMMDDHHMMSS.FFF": int(match_yyyymmddhhmmssfff_dot.sum()),
            "YYYYMMDD000000.000": int(match_yyyymmdd000000000_dot.sum()),
            "hours 24-47 (irregular, but fixed by the extraction protocol)": int(
                hours_over_23.sum()
            ),
            "irregular": int(irregular_timestamps.sum()),
        }

        # Checking for irregular datetime patterns
        irregular_uniques = df.loc[irregular_timestamps, col].value_counts().to_dict()
        irregular_uniques = all_values_to_int(irregular_uniques)

        # Finalize the dictionary to return
        inspection_results["formats"][col] = counts
        inspection_results["irregular values"][col] = irregular_uniques

    return inspection_results


def count_unique_values(df: pd.DataFrame, counting_params: list):
    """Counts irregular values in the DataFrame based on given masks.

    Args:
        df (pd.DataFrame): DataFrame containing data to inspect.
        counting_params (list): List of dictionaries containing the mask and columns to count irregularities.
            Each dictionary should have:
            - 'mask': pd.Series where True indicates an irregular value.
            - 'value_cols': List of columns from which irregular unique values are collected.
    Returns:
        dict: Nested dictionary containing unique irregular values and their counts.
        dict: Dictionary containing total irregular value counts.
    """
    # Initialize
    unique_counts = {}
    total_irregular_counts = {}

    # Loop
    for key, param in counting_params.items():
        mask = param["mask"]
        cols = param["value_cols"]

        # If only one column is given, then unique calues are collected from it.
        if len(cols) == 1:
            irregular_uniques = df.loc[mask, cols[0]].value_counts().to_dict()

        # Concatenate values from both columns to create code-text pairs
        elif len(cols) == 2:
            code_text_pairs = df.loc[mask, cols[0]] + "(" + df.loc[mask, cols[1]] + ")"
            irregular_uniques = code_text_pairs.value_counts().to_dict()
        else:
            raise ValueError("The length of value_cols must be either one or two.")

        unique_counts[key] = all_values_to_int(irregular_uniques)

        # Count the number of total irregular records, and add it to the dictionary.
        total_irregular_counts[key] = sum(v for v in irregular_uniques.values())

    return unique_counts, total_irregular_counts
