import os
import json
from ....generals import general_config as config
from ....generals.general_utils import tally_stats
from ..cleaning_settings import get_cln_settings
from ..cleaning_utils import parallel_map_partitions_cln
from .code_cleaning_functions import (
    clean_icd10_codes,
    clean_atc_codes,
    clean_jlac10_result_codes,
)


def clean_codes_in_records():
    """Cleans standardized codes in clinical records."""
    # Initialize variables
    source_tables_dir = get_cln_settings("CLN_OUTPUT_TABLES_DIR")
    internal_dir = get_cln_settings("CLN_INTERNAL_DIR")
    sheet_pattern = get_cln_settings("CLN_CODE_CLEANING_SHEET_PTN")
    cleaning_params = {
        "PPR-01": {
            "code_type": config.ICD10,
            "file_pattern": config.DIAGNOSIS_TABLE_PATTERN,
            "function": clean_icd10_codes,
        },
        "OMP-01": {
            "code_type": config.ATC,
            "file_pattern": config.PRESCRIPTION_ORDER_TABLE_PATTERN,
            "function": clean_atc_codes,
        },
        "OMP-02": {
            "code_type": config.ATC,
            "file_pattern": config.INJECTION_ORDER_TABLE_PATTERN,
            "function": clean_atc_codes,
        },
        "OML-11": {
            "code_type": config.JLAC10,
            "file_pattern": config.LAB_RESULT_TABLE_PATTERN,
            "function": clean_jlac10_result_codes,
        },
    }
    for data_type, p in cleaning_params.items():
        code_type = p["code_type"]
        file_pattern = p["file_pattern"]
        cleaning_fn = p["function"]
        csv_path_pattern = os.path.join(source_tables_dir, "**", file_pattern)
        output_csv_path = os.path.join(internal_dir, file_pattern)
        json_path = sheet_pattern.replace("*", f"{code_type}_in_{data_type}")
        single_file = config.SINGLE_FILE[data_type]

        # Execute the helper function
        stats_list = parallel_map_partitions_cln(
            csv_path_pattern=csv_path_pattern,
            function=cleaning_fn,
            output_csv_path=output_csv_path,
            chunksize=-1,
            single_file=single_file,
            single_stat_file=False,
        )
        process_analytics = tally_stats(stats_list)

        # Save the mapping results as JSON
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(process_analytics, f, indent=2, ensure_ascii=False)
