#!/usr/bin/env python3

from setuptools import setup, find_packages
from pathlib import Path

# Read the contents of README.md
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="restest",
    version="2.1.0",
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
