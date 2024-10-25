#!/usr/bin/env bash
# exit on error
set -o errexit

# Install wkhtmltopdf
apt-get update
apt-get install -y wkhtmltopdf

# Install Python dependencies
pip install -r requirements.txt

# Add any other build steps here
