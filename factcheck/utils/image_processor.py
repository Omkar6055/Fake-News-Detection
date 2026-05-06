import pytesseract
from PIL import Image
import io
import base64

# Point to Tesseract installation
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def extract_text_from_image(image_file):
    """
    Extract text from uploaded image using Tesseract OCR
    Returns extracted text string
    """
    try:
        # Open image
        image = Image.open(image_file)
        
        # Extract text using Tesseract
        extracted_text = pytesseract.image_to_string(
            image, 
            config='--psm 3'  # Automatic page segmentation
        )
        
        # Clean extracted text
        cleaned_text = extracted_text.strip()
        
        if not cleaned_text:
            return None, "No text found in image"
            
        return cleaned_text, None
        
    except Exception as e:
        return None, f"Image processing error: {str(e)}"

def extract_text_from_base64(base64_string):
    """
    Extract text from base64 encoded image
    """
    try:
        # Decode base64
        image_data = base64.b64decode(base64_string)
        image = Image.open(io.BytesIO(image_data))
        
        extracted_text = pytesseract.image_to_string(image)
        cleaned_text = extracted_text.strip()
        
        if not cleaned_text:
            return None, "No text found in image"
            
        return cleaned_text, None
        
    except Exception as e:
        return None, f"Image processing error: {str(e)}"
