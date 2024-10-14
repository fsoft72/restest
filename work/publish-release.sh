#!/bin/bash

if [ ! -e restest.py ]
then
    echo "Run this script from the main directory"
    exit 1
fi

rm -Rf dist

# Step 1: Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Step 2: Install build package
pip3 install build twine

python3 -m build

twine upload dist/*

# Deactivate the virtual environment
deactivate

# Remove the virtual environment
rm -Rf venv

# Remove the dist directory and build directory
rm -Rf dist build *.egg-info
