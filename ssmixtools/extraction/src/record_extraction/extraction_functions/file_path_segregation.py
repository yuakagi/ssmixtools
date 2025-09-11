"""Module to separate file paths by record types"""

import os
from datetime import datetime
from multiprocessing import Manager
from concurrent.futures import as_completed, ProcessPoolExecutor
from tqdm import tqdm
import numpy as np
import pandas as pd
from ...extraction_settings import get_ext_settings
from ...extraction_utils import patient_id_to_path, clear_temp_files
from .....generals import general_config as config
from .....generals.general_utils import test_generator


def _segregate_file_path(chunk: pd.DataFrame, lock, shared_file_numbers) -> int:
    """Collects file paths and save them as csv files separately by data types.
    Args:
        chunk (pd.Dataframe): Series of patient IDs with metadata.
            This function iterates over patient IDs to collect file paths.
    Returns:
        rows_saved(int): Number of rows (file paths) saved in total.
    """
    file_paths_dir = get_ext_settings("EXT_FILE_PATHS_DIR")
    start = get_ext_settings("EXT_PERIOD_START")
    end = get_ext_settings("EXT_PERIOD_END")
    target_types = config.TARGET_DATA_TYPES
    lst = []
    for _, row in chunk.iterrows():
        patient_id = row[0]
        patient_path = patient_id_to_path(patient_id)
        date_folders = os.listdir(patient_path)
        for date_folder in date_folders:
            # Check if the files are within the target period
            if date_folder == "-":
                # NOTE: in the "-" folders, diagnosis records outside the specified period can be included!
                date_valid = True
            else:
                # NOTE: Diagnosis records outside the specified period can still be included if they are updated later!
                date = datetime.strptime(date_folder, "%Y%m%d")
                date_valid = start <= date <= end

            if date_valid:
                path_to_date = os.path.join(patient_path, date_folder)
                data_type_folders = os.listdir(path_to_date)
                for data_type in data_type_folders:
                    # Add the file path only if it is of the target data types
                    if data_type in target_types:
                        path_to_type = os.path.join(path_to_date, data_type)
                        for file in os.listdir(path_to_type):
                            file_parts = file.strip().split("_")
                            condition_flag = file_parts[-1].strip()
                            file_path = os.path.join(path_to_type, file)
                            lst.append(
                                [
                                    patient_id,
                                    data_type,
                                    condition_flag,
                                    file_path,
                                ]
                            )

    # Create a dataframe from the lists
    df = pd.DataFrame(data=lst)
    columns = [
        config.COL_PID,
        "data_type",
        "condition_flag",
        "file_path",
    ]
    df.columns = columns

    rows_saved = 0
    for i, data_type in enumerate(target_types):
        # Count up file numbers
        with lock:
            current_file_no = shared_file_numbers[i]
            shared_file_numbers[i] += 1
        # Save file
        file_name = config.DATA_TYPE_PATH_PATTERN.replace(
            "*", f"{data_type}_{current_file_no}"
        )
        file_path = os.path.join(file_paths_dir, file_name)
        saved_df = df[df.iloc[:, 1] == data_type].copy()
        saved_df = saved_df.drop("data_type", axis=1)
        if len(saved_df) > 0:
            saved_df.to_csv(file_path, header=True, index=False)
        rows_saved += len(saved_df)

    return rows_saved


def segregate_paths_by_data_types() -> dict:
    """Creates lists of file paths by data types, and save them as individual CSV files.

    Returns:
        process_analytics (dict): Dictionary containing analytic data of this entire process.
    """
    selected_ids_path = get_ext_settings("EXT_SELECTED_IDS_PTH")
    patient_id_chunk_iterator = pd.read_csv(
        selected_ids_path,
        dtype=str,
        na_values=config.NA_VALUES,
        header=0,
        chunksize=config.CHUNKSIZES["file_path_segregation"],
    )
    # Load params
    test_mode = get_ext_settings("EXT_TEST")
    max_workers = get_ext_settings("EXT_MAX_WORKERS")

    # Truncate the iterator for testing
    if test_mode:
        patient_id_chunk_iterator = test_generator(
            patient_id_chunk_iterator, test_chunks=get_ext_settings("EXT_TEST_CHUNKS")
        )

    # Initialize
    process_analytics = {}

    # Ensure nothing is in the temporary file directory
    clear_temp_files()

    # Segregate and save paths by each child process separately
    saved_rows_list = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor, Manager() as manager:
        lock = manager.Lock()
        shared_file_numbers = manager.Array(
            "i", [0 for _ in range(len(config.TARGET_DATA_TYPES))]
        )
        futures = [
            executor.submit(_segregate_file_path, chunk, lock, shared_file_numbers)
            for chunk in patient_id_chunk_iterator
        ]

        for future in tqdm(
            as_completed(futures),
            total=len(futures),
            desc="Collecting file paths",
        ):
            saved_rows_list.append(future.result())

    # Sum up rows added
    total_rows_saved = int(np.array(saved_rows_list).sum())

    # Write analytics
    process_analytics["total_file_paths_saved"] = total_rows_saved
    return process_analytics
