#!/bin/bash
set -e

# Python dependencies are automatically installed by Nixpacks
# but we can ensure they are installed if this script is run manually
pip install -r requirements.txt

# Download spacy model
python -m spacy download en_core_web_sm

# Install Playwright browsers (requires playwright to be in requirements.txt)
playwright install chromium