"""Module to create a table to map real patient IDs to deidentified IDs"""

import numpy as np
import pandas as pd
from ...extraction_settings import get_ext_settings
from .....generals import general_config as config


def create_deidentified_patient_id_map() -> dict:
    """Creates a table to map original patient IDs to deidentified ones.

    The deidentified IDs are successive numbers starting from one.
    The file identity tag is appended to the deidentified IDs so that you can identify the source of the patient records when mixed with data from other sites.

    Returns:
        process_analytics(dict): Dictionary contains analytics of this process.
    """
    selected_ids_path = get_ext_settings("EXT_SELECTED_IDS_PTH")
    df = pd.read_csv(selected_ids_path, header=0, na_values=config.NA_VALUES)
    unique_ids = df[config.COL_PID].dropna().unique()
    deidentified_ids = np.arange(1, unique_ids.size + 1)
    np.random.seed(seed=0)
    np.random.shuffle(deidentified_ids)

    # Create a dataframe
    id_df = pd.DataFrame(
        {
            config.COL_PID: unique_ids,
            config.COL_DID: deidentified_ids,
        }
    )

    # Add an identity tag
    identity_tag = get_ext_settings("IDENTITY_TAG")
    id_map_path = get_ext_settings("EXT_ID_MAP_PTH")
    id_df[config.COL_DID] = id_df[config.COL_DID].astype(str)
    id_df[config.COL_DID] = id_df[config.COL_DID] + identity_tag

    # Save
    id_df.to_csv(id_map_path, mode="w", header=True, index=False)
    n_patients = len(id_df)
    process_analytics = {"number of deidentified patient IDs": n_patients}

    return process_analytics
