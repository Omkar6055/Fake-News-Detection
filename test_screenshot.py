#!/usr/bin/env python3
"""
Test script to debug what's being extracted from the screenshot
"""

import tempfile
import base64
from PIL import Image
import io
from factcheck.utils.multimodal import modal_normalization
from factcheck.utils.utils import load_yaml

def test_screenshot_processing():
    """Test what content is being extracted from screenshot"""
    
    # Load API config
    try:
        api_config = load_yaml("api_config.yaml")
    except:
        api_config = {}
    
    # Create a simple test image with text
    print("Creating test image with text...")
    
    # Create a simple image with text content
    img = Image.new('RGB', (800, 600), color='white')
    
    # For now, let's test with a base64 encoded image that simulates a screenshot
    # This would normally come from the actual screen capture
    
    # Save to temporary file
    temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    img.save(temp_file.name)
    
    print(f"Test image saved to: {temp_file.name}")
    
    # Process with multimodal
    print("Processing with multimodal...")
    try:
        result = modal_normalization(
            modal="image",
            input=temp_file.name,
            gemini_api_key=api_config.get('GEMINI_API_KEY'),
            api_config=api_config
        )
        
        print("Extracted content:")
        print(f"Length: {len(result)} characters")
        print(f"Content: {repr(result)}")
        
        if len(result) < 50:
            print("⚠️  Very short content extracted - this might be the issue!")
        
    except Exception as e:
        print(f"❌ Error during processing: {e}")
    
    # Clean up
    import os
    try:
        os.unlink(temp_file.name)
    except:
        pass

if __name__ == "__main__":
    test_screenshot_processing()