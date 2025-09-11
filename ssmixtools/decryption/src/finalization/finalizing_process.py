"""Module to finalize decrypted files"""

import os
import shutil


def finalize_process():
    """
    Finalizes the decryption process by organizing decrypted files.

    This function performs the following steps:
    1. Deletes all existing files in the output directory.
    2. Organizes and moves new decrypted files from the temporary directory to the output directory.

    Files are categorized into subdirectories based on tags extracted from their filenames.
    """

    # Load parameters
    output_dir = os.environ["DCRYP_OUTPUT_DIR"]
    temp_dir = os.environ["DCRYP_TEMP_DIR"]

    # Delete old files
    for root, _, files in os.walk(output_dir, topdown=False):
        for file in files:
            old_file_path = os.path.join(root, file)
            os.remove(old_file_path)
        if root != output_dir:
            os.rmdir(root)

    # Create subdirectories in the output directory
    tags = []
    for file in os.listdir(temp_dir):
        tag = file.split("_")[-1].replace(".csv", "")
        if tag not in tags:
            tags.append(tag)
    for tag in tags:
        os.mkdir(os.path.join(output_dir, tag))

    # Move new decoded files to the output directory
    for file in os.listdir(temp_dir):
        tag = file.split("_")[-1].replace(".csv", "")
        dst_dir = os.path.join(output_dir, tag)
        src = os.path.join(temp_dir, file)
        dst = os.path.join(dst_dir, file)
        shutil.move(src, dst)
