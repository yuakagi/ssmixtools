"""The modle for file decryption"""

import os
from concurrent.futures import as_completed, ProcessPoolExecutor
from tqdm import tqdm
import chardet
from Crypto.PublicKey import RSA
from Crypto.Cipher import AES, PKCS1_OAEP


def _decrypt_data(original_data_path: str, private_key: str):
    """Decrypts an encrypted file.

    Args:
        original_data_path (str): Path to the encrypted file to be decrypted.
        private_key (str): RSA private key used to decrypt the AES key.

    Raises:
        ValueError: If decryption or file writing fails.
    """

    # Load params
    temp_dir = os.environ["DCRYP_TEMP_DIR"]

    # Read the encrypted file
    private_key = RSA.import_key(private_key)
    with open(original_data_path, "rb") as f:
        enc_symmetric_key = f.read(private_key.size_in_bytes())
        nonce = f.read(16)  # AES block size is 16 bytes
        tag = f.read(16)
        ciphertext = f.read()

        # Decrypt the symmetric key
        cipher_rsa = PKCS1_OAEP.new(private_key)
        symmetric_key = cipher_rsa.decrypt(enc_symmetric_key)

        # Decrypt the data
        cipher_aes = AES.new(symmetric_key, AES.MODE_EAX, nonce)
        data = cipher_aes.decrypt_and_verify(ciphertext, tag)

    # Define a temporary path to save the encrypted data
    temp_file_name = os.path.basename(original_data_path).replace(".bin", ".csv")
    temp_file_path = os.path.join(temp_dir, temp_file_name)
    if os.path.exists(temp_file_path):
        # In rare cases where files with the same file name are found,
        # This function tries to avoid overwriting by appending a number to the file name.
        print("!!! CAUTION !!!")
        print("A child process is trying to overwrite a file.")
        print(
            "It seems that multiple files with the same file name exist in the source directory"
        )
        print("File names are modified in order not to overwrite files.")
        n = 1
        while True:
            rename_candidate = temp_file_path.replace(".csv", f"{n}.csv")
            if not os.path.exists(rename_candidate):
                temp_file_path = rename_candidate
                break
            else:
                n += 1

    # Save the decrypted date
    with open(temp_file_path, "w", encoding="utf-8") as f:
        f.write(data.decode())


def decrypt_data():
    """
    This function decrypts encrypted files, and save them in the temporary file directory.
    Encrypted files are parsed and they are concurrently decrypted in multiple child processes.

    Args:
        original_data_path (str): Path to the file to be decrypted.
        private_key: RSA private key used for decryption of the AES key.

    Returns:
        None
    """
    # Load parameters
    private_key_path = os.environ["DCRYP_PRIVATE_KEY_PTH"]
    src_dir = os.environ["DCRYP_SOURCE_DIR"]
    # Detect the private-key's encoding
    with open(private_key_path, "rb") as f:
        binary_pub_key = f.read()
        encoding_params = chardet.detect(binary_pub_key)
    key_encoding = encoding_params["encoding"]
    # Load private key
    with open(private_key_path, "r", encoding=key_encoding) as f:
        private_key = f.read()

    # Create a generator
    def _task_generator():
        for root, _, files in os.walk(src_dir):
            for file in files:
                # Only yield file paths of binary files
                if file.endswith(".bin"):
                    file_abs_path = os.path.join(root, file)
                    yield file_abs_path

    task_generator = _task_generator()

    max_workers = int(os.environ["DCRYP_MAX_WORKERS"])
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                _decrypt_data,
                original_data_path=original_data_path,
                private_key=private_key,
            )
            for original_data_path in task_generator
        ]

        for future in tqdm(
            as_completed(futures), total=len(futures), desc="Decrypting files"
        ):
            _ = future.result()
