"""Module for file encryption"""

import os
import glob
from concurrent.futures import as_completed, ProcessPoolExecutor
import chardet
from tqdm import tqdm
from Crypto.PublicKey import RSA
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.Random import get_random_bytes
from .....generals import general_config as config
from ...extraction_settings import get_ext_settings


def _encrypt_csv(original_path: str, output_path: str, pubkey: str):
    """Encrypts a CSV file.

    This encryption is performed with a hybrid cryptosystem (RSA + AES).
    Args:
        original_path (str): Path to the CSV file to be encrypted.
        output_path (str): Path the encrypted file is saved to.
        pubkey (str): RSA public key.
    """
    # Convert pubkey
    pubkey = RSA.importKey(pubkey)
    # Generate an AES key
    symmetric_key = get_random_bytes(16)
    # Encrypt the symmetric key using the RSA public key
    cipher_rsa = PKCS1_OAEP.new(pubkey)
    encrypted_symmetric_key = cipher_rsa.encrypt(symmetric_key)

    # Encrypt the CSV data
    cipher_aes = AES.new(symmetric_key, AES.MODE_EAX)
    with open(original_path, "rb") as f:
        data = f.read()
    nonce = cipher_aes.nonce
    ciphertext, tag = cipher_aes.encrypt_and_digest(data)

    # Write the encrypted data to a binary file
    with open(output_path, "wb") as f:
        for x in [encrypted_symmetric_key, nonce, tag, ciphertext]:
            f.write(x)


def encrypt_csv():
    """Encrypt output files with RSA + AES"""
    # Load params
    pubkey_path = get_ext_settings("EXT_PUBKEY_PATH")
    identity_tag = get_ext_settings("IDENTITY_TAG")
    output_tables_dir = get_ext_settings("EXT_OUTPUT_TABLES_DIR")
    deidentified_tables_dir = get_ext_settings("EXT_DEIDENTIFIED_TABLES_DIR")
    deidentified_metadata_path = get_ext_settings("EXT_DEIDENTIFIED_METADATA_PTH")
    dob_map_path = get_ext_settings("EXT_DOB_MAP_PTH")
    id_map_path = get_ext_settings("EXT_ID_MAP_PTH")

    # Detect the pubkey's encoding
    with open(pubkey_path, "rb") as f:
        binary_pub_key = f.read()
        encoding_params = chardet.detect(binary_pub_key)
    pubkey_encoding = encoding_params["encoding"]
    # Load pubkey
    with open(pubkey_path, "r", encoding=pubkey_encoding) as f:
        pubkey = f.read()

    def _task_generator():
        """
        Yields:
            original_path (str): Path to the file to be encrypted
            output_path (str): Path for saving the encrypted file
        """
        for data_type in [
            "ADT-12",
            "ADT-22",
            "ADT-52",
            "PPR-01",
            "OMP-01",
            "OMP-02",
            "OML-11",
        ]:
            file_name_pattern = config.TIME_SERIES_DATA_PATTERN.replace(
                "*", f"{data_type}_*"
            )
            deidentified_files = glob.glob(
                os.path.join(deidentified_tables_dir, file_name_pattern)
            )
            for i, original_path in enumerate(deidentified_files):
                output_file_name = f"{data_type}_{i}_{identity_tag}.bin"
                output_path = os.path.join(output_tables_dir, output_file_name)

                yield original_path, output_path

    task_generator = _task_generator()

    # Step 1: Encrypt record table
    max_workers = get_ext_settings("EXT_MAX_WORKERS")
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                _encrypt_csv,
                original_path=original_path,
                output_path=output_path,
                pubkey=pubkey,
            )
            for original_path, output_path in task_generator
        ]

        for future in tqdm(
            as_completed(futures),
            total=len(futures),
            desc="Encrypting CSV files",
        ):
            _ = future.result()

    # Step 2: Encrypt metadata, and mapping tables
    enc_metadata_path = os.path.join(
        output_tables_dir,
        f"patient_metadata_{identity_tag}.bin",
    )
    enc_dob_path = os.path.join(output_tables_dir, f"DOB_{identity_tag}.bin")
    enc_id_path = os.path.join(output_tables_dir, f"patient_id_{identity_tag}.bin")
    _encrypt_csv(deidentified_metadata_path, enc_metadata_path, pubkey)
    _encrypt_csv(dob_map_path, enc_dob_path, pubkey)
    _encrypt_csv(id_map_path, enc_id_path, pubkey)
