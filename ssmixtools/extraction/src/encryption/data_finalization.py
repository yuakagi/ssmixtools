"""The main module for file encryption"""

from .encryption_functions import encrypt_csv
from ..extraction_settings import get_ext_settings
from ....generals.general_utils import function_wrapper


def encrypt_outputs():
    """Encrypts files"""
    functions = [
        encrypt_csv,
    ]
    descriptions = [
        "encrypt product files",
    ]
    # Final step: encrypt the files
    for function, description in zip(functions, descriptions):
        function_wrapper(
            function=function,
            section_description="Finalization",
            step_description=description,
            file_path=get_ext_settings("EXT_PERFORMANCE_PTH"),
        )
