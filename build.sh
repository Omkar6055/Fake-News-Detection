#!/bin/bash
set -e

echo "Installing system dependencies..."
apt-get update -qq && apt-get install -y -qq tesseract-ocr

echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Downloading spaCy model..."
python -m spacy download en_core_web_sm

echo "Installing Playwright browsers..."
playwright install chromium
playwright install-deps chromium

echo "Build complete!"