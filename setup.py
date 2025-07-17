#!/usr/bin/env python3

from setuptools import setup, find_packages
from pathlib import Path

# Read the contents of README.md
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

# Read the VERSION line from restest.py
version_file = this_directory / "restest.py"
with open(version_file, "r") as f:
    for line in f:
        if line.startswith("VERSION ="):
            VERSION = line.split('"')[1]  # Extract the version number
            break

print("=== VERSION: %s ===" % VERSION)

if VERSION.endswith("-dev"):
    print(
        "ERROR: You are installing a development version of restest. "
        "This version may not be stable and could contain bugs."
    )
    exit(1)

setup(
    name="restest",
    version=VERSION,
    description="Scriptable REST calls test software written in Python",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Fabio Rotondo",
    author_email="fsoft.devel@gmail.com",
    url="https://github.com/fsoft72/restest",
    license="GPLv3",
    packages=find_packages(),
    py_modules=["restest"],
    entry_points={
        "console_scripts": [
            "restest=restest:main",
        ],
    },
    install_requires=[
        "termcolor",
        "requests",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)
