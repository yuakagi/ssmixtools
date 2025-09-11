"""General utils"""

import os
import re
import gc
import sys
import json
from typing import Callable, Iterator, Any
from datetime import datetime
import shutil
import psutil
import numpy as np
from . import general_config as config


class LogRedirector:
    """Context manager to redirect standard output and error logs to a text file."""

    def __init__(self, log_dir: str = None, file_name: str = None) -> None:
        """
        Initializes the LogRedirector with an optional log file path.

        Args:
            log_dir (str, optional): Path to the directory where the log file will be saved.
                If None, no redirection occurs.
            file_name (str, optional): Name of the log file.
                If not specified, the file name will be 'logfile_<current time>.txt'.
        """
        self.redirect = log_dir is not None
        if self.redirect:
            if file_name is None:
                # Generate a file name based on the current time if not provided
                dt_str = datetime.now().strftime("%Y%m%d%H%M%S")
                file_name = f"logfile_{dt_str}.txt"

            # If file_name is an absolute path, skip joining it with log_dir
            if not os.path.isabs(file_name):
                log_file = os.path.join(log_dir, file_name)
            else:
                log_file = file_name

            self.log_file = os.path.abspath(log_file)
        else:
            self.log_file = None
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        self.writer = None

    def __enter__(self):
        """Enters the context manager, redirecting stdout and stderr to the log file."""
        if self.redirect:
            try:
                print(f"Standard outputs and errors are redirected to {self.log_file}")
                print("See the file for details.")
                self.writer = open(self.log_file, "a", encoding="utf-8")
                sys.stdout = self.writer
                sys.stderr = self.writer
            except Exception as e:
                # Restore the original stdout and stderr in case of failure
                sys.stdout = self.original_stdout
                sys.stderr = self.original_stderr
                print(f"Failed to redirect logs: {e}")
                raise

    def __exit__(self, exception_type, exception_value, traceback):
        """
        Exits the context manager, restoring stdout and stderr.

        Args:
            exception_type, exception_value, traceback: Exception information if raised during the block.
        """
        if self.redirect:
            try:
                sys.stdout = self.original_stdout
                sys.stderr = self.original_stderr
            finally:
                # Ensure the file is closed properly even if an exception occurs
                if self.writer:
                    self.writer.close()


def define_max_workers() -> int:
    """Determines the number of workers for multiprocessing.
    Returns:
        max_workers (int): Maximum number of workers to be involved in the multiprocessing.
    """
    max_workers = psutil.cpu_count(logical=config.LOGICAL_CPU) - config.CPU_MARGIN
    return max_workers


def all_values_to_int(dictionary: dict) -> dict:
    """Converts all values in the dictionary to integers.

    Args:
        dictionary (dict): Input dictionary whose values need to be converted.

    Returns:
        dict: Dictionary with all values converted to integers.
    """
    for key, val in dictionary.items():
        if isinstance(val, dict):
            dictionary[key] = all_values_to_int(val)
        else:
            dictionary[key] = int(val)
    return dictionary


def _pythonize(data: Any) -> Any:
    """Converts data into Python's built-in data types.
    Args:
        data : Data to be converted.
    Returns:
        data: Converted data.
    """
    if isinstance(data, dict):
        return {key: _pythonize(value) for key, value in data.items()}

    if isinstance(data, list):
        return [_pythonize(item) for item in data]

    if isinstance(data, np.integer):
        return int(data)

    if isinstance(data, np.floating):
        return float(data)

    if isinstance(data, np.ndarray):
        return data.tolist()

    return data


def tally_stats(stats_list: list[dict], pythonize: bool = True) -> dict:
    """Tallies stats saved in separate dictionaries, and makes them into a single dictionary.
    This function is supposed to take a list of dictionaries returned by 'parallel_map_partitions_ext'.
    when necessary.
    Args:
        stats_list (list): List of dictionaries that store statistics.
        pythonize (bool): If true, this function converts all dictionary values into Python's built-in data types.
    Returns:
        final_stats (dict): Aggregated dictionary.
    """

    def _tally_stats(d, final_d):
        for key, val in d.items():
            if isinstance(val, (int, float, np.number)):
                final_d[key] = final_d.get(key, 0) + val

            elif isinstance(val, list):
                final_d[key] = final_d.get(key, []) + val

            elif isinstance(val, dict):
                if key not in final_d:
                    final_d[key] = {}
                final_d[key] = _tally_stats(val, final_d[key])

        return final_d

    final_stats = {}
    for stats in stats_list:
        final_stats = _tally_stats(stats, final_stats)

    if pythonize:
        final_stats = _pythonize(final_stats)

    return final_stats


def archive_file(existing_file: str):
    """Archive an existing file to avoid overwriting.

    Args:
        existing_file (str): Path to the file to be archived.
    """
    now = datetime.now().strftime("%Y%m%d%H%M%S")
    file_name = os.path.basename(existing_file)
    dst_file = re.sub(r"(\.\w+)$", rf"_{now}\1", file_name)
    dst_dir = os.path.dirname(existing_file)
    archive_dir = os.path.join(dst_dir, "archive")
    os.makedirs(archive_dir, exist_ok=True)
    shutil.move(existing_file, os.path.join(archive_dir, dst_file))


def test_generator(generator: Iterator, test_chunks: int) -> Iterator:
    """Truncates a generator for testing.
        Generator iteration is terminated at the given number of iterations.
    Args:
        generator (Iterator[Any]): The generator to truncate.
        test_chunks (int): The maximum number of chunks to yield.

    Yields:
        Any: Object yielded by the original generator.
    """
    n_iter = 0
    exhausted = False
    while not exhausted:
        try:
            chunk = next(generator)
            yield chunk
            n_iter += 1
            if n_iter == test_chunks:
                exhausted = True
        except StopIteration:
            exhausted = True


def write_history(key: str, file_path: str, value: Any = "now") -> None:
    """Writes analytics to a JSON file to record process details.
    Args:
        key (str): Dictionary key.
        file_path (str): Path to a JSON file for saving the data.
        value (any): Value paired with the key.
            If "now" is passed, the current time is recorded.
    """
    if value == "now":
        now = datetime.now()
        value = now.strftime("%Y/%m/%d %H:%M:%S")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            dct = json.load(f)
            dct[key] = value
    else:
        dct = {key: value}

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(dct, f, indent=2)


def function_wrapper(
    function: Callable,
    section_description: str,
    step_description: str,
    file_path: str,
    **kwargs,
) -> None:
    """Wrapper function for data processing steps.
    This function performs:
        - 1. Displays step descriptions for CLI.
        - 2. Executes a custom function
        - 3. Records step details in a JSON file.
    Args:
        function (Callable): Function to be executed.
            This function is expected to return None, or any values that can be serialized as JSON data.
        section_description (str): Short description of the current section.
        step_description (str): Description of the current step in the section.
            These descriptions are displayed on the terminal.
        file_path (str): Path to a JSON file for saving the data.
        kwargs: Additional arguments passed to the function.
    """
    # Print the current step description on the terminal
    displayed_text = f"|| {section_description}: {step_description} ||"
    text_length = len(displayed_text)
    print("*" * (text_length))
    print("||" + "*" * (text_length - 4) + "||")
    print(displayed_text)
    print("||" + "*" * (text_length - 4) + "||")
    print("*" * (text_length))

    # Record the time of initiation
    log_key = f"{step_description} initiated"
    start_dt = datetime.now()
    start = start_dt.strftime("%Y/%m/%d %H:%M:%S")
    write_history(log_key, file_path, value=start)

    # Execute function
    analytics = function(**kwargs)
    gc.collect()

    # Write the time of completion
    log_key = f"{step_description} finished"
    end_dt = datetime.now()
    end = end_dt.strftime("%Y/%m/%d %H:%M:%S")
    write_history(log_key, file_path, value=end)

    # Record the step duration
    log_key = f"{step_description} duration"
    duration = (end_dt - start_dt).total_seconds()
    duration_hr = int(duration // 60**2)
    duration_min = int((duration % 60**2) // 60)
    duration_str = f"{duration_hr} hours {duration_min} min"
    write_history(log_key, file_path, value=duration_str)

    # Write the process analytics
    if analytics is not None:
        write_history(
            f"process details ({step_description})", file_path, value=analytics
        )
