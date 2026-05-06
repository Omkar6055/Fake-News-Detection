#!/usr/bin/env python3
"""
Setup script for Fake News Detection with Gemini API
This script installs all dependencies and downloads required models.
"""

import subprocess
import sys
import os

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"Error: {e.stderr}")
        return False

def main():
    print("🚀 Setting up Fake News Detection with Gemini API")
    print("=" * 50)
    
    # Install requirements
    if not run_command("pip install -r requirements.txt", "Installing Python dependencies"):
        sys.exit(1)
    
    # Download spaCy model
    if not run_command("python -m spacy download en_core_web_sm", "Downloading spaCy English model"):
        print("⚠️  Warning: spaCy model download failed. You may need to download it manually:")
        print("   python -m spacy download en_core_web_sm")
    
    # Download NLTK data
    print("🔄 Downloading NLTK data...")
    try:
        import nltk
        nltk.download('punkt', quiet=True)
        nltk.download('punkt_tab', quiet=True)
        print("✅ NLTK data downloaded successfully")
    except Exception as e:
        print(f"⚠️  Warning: NLTK data download failed: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Setup completed!")
    print("\n📋 Next steps:")
    print("1. Add your API keys to api_config.yaml:")
    print("   - GEMINI_API_KEY: Get from https://makersuite.google.com/app/apikey")
    print("   - SERPER_API_KEY: Get from https://serper.dev/")
    print("\n2. Set up Google Cloud Storage (for image/video uploads):")
    print("   - Run: python gcs_setup_guide.py")
    print("\n3. Run the application:")
    print("   python webapp.py --api_config api_config.yaml")
    print("\n4. Or use CLI:")
    print('   python -m factcheck --modal string --input "Your text here" --api_config api_config.yaml')
    print('   python -m factcheck --modal image --input "path/to/image.jpg" --api_config api_config.yaml')
    print('   python -m factcheck --modal video --input "path/to/video.mp4" --api_config api_config.yaml')

if __name__ == "__main__":
    main()