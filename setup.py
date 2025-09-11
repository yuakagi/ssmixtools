"""setup.py"""

from setuptools import setup, find_packages


def _get_requirements(file: str) -> list[str]:
    """Load required libraries from requirements.txt"""
    return open(file, encoding="utf-8").read().splitlines()


setup(
    name="ssmixtools",
    version="0.0.0",
    description="A collection of tools for creating large clinical datasets using SS-MIX2",
    author="Yu Akagi, MD",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=_get_requirements("requirements.txt"),
    license="MIT",
)
