#!/bin/bash
# Render Build Script
# This runs during deployment to set up the environment
set -e  # Exit on any error

echo "🔧 Installing system dependencies (Tesseract OCR + OpenCV libs)..."
apt-get update -y
apt-get install -y tesseract-ocr libglib2.0-0 libsm6 libxext6 libxrender-dev

echo "🔧 Installing Python dependencies..."
pip install -r requirements.txt

echo "📦 Downloading spaCy English model..."
python -m spacy download en_core_web_sm

echo "🔧 Installing Playwright browsers..."
playwright install chromium
playwright install-deps chromium

echo "✅ Build completed successfully!"