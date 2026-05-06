import cv2
import os
import uuid
from google.cloud import storage
import google.generativeai as genai
from .logger import CustomLogger

logger = CustomLogger(__name__).getlog()

# Google Cloud Storage configuration
GCS_BUCKET_NAME = "my-media-storage-12345"
GCS_BASE_URL = "https://storage.googleapis.com/my-media-storage-12345"


def upload_to_gcs(file_path: str, api_config: dict = None) -> str:
    """
    Upload file to Google Cloud Storage and return public URL
    
    Args:
        file_path (str): Local path to the file
        api_config (dict): API configuration containing GCS settings
    
    Returns:
        str: Public URL of uploaded file
    """
    try:
        # Get GCS configuration from API config
        if api_config:
            bucket_name = api_config.get('GCS_BUCKET_NAME', GCS_BUCKET_NAME)
            base_url = api_config.get('GCS_BASE_URL', GCS_BASE_URL)
            credentials_path = api_config.get('GOOGLE_APPLICATION_CREDENTIALS')
        else:
            bucket_name = GCS_BUCKET_NAME
            base_url = GCS_BASE_URL
            credentials_path = None
        
        # Generate unique filename
        file_extension = os.path.splitext(file_path)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        
        # Initialize Google Cloud Storage client with credentials if provided
        if credentials_path:
            if credentials_path.startswith('{') and credentials_path.endswith('}'):
                # Credentials provided as JSON string in config
                try:
                    import json
                    import tempfile
                    credentials_dict = json.loads(credentials_path)
                    
                    # Create temporary file with credentials
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                        json.dump(credentials_dict, temp_file)
                        temp_credentials_path = temp_file.name
                    
                    client = storage.Client.from_service_account_json(temp_credentials_path)
                    logger.info("Using GCS credentials from inline JSON in config")
                    
                    # Clean up temporary file
                    os.remove(temp_credentials_path)
                    
                except Exception as json_error:
                    logger.error(f"Failed to parse inline JSON credentials: {json_error}")
                    return file_path
            elif os.path.exists(credentials_path):
                # Use service account key file
                client = storage.Client.from_service_account_json(credentials_path)
                logger.info(f"Using GCS credentials from file: {credentials_path}")
            else:
                logger.warning(f"Credentials file not found: {credentials_path}")
                logger.warning("Falling back to local file path")
                return file_path
        else:
            # Try using Application Default Credentials
            try:
                client = storage.Client()
                logger.info("Using Application Default Credentials for GCS")
            except Exception as cred_error:
                logger.warning(f"GCS authentication failed: {cred_error}")
                logger.warning("Falling back to local file path")
                return file_path
        
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(unique_filename)
        
        # Upload file
        logger.info(f"Uploading {file_path} to GCS bucket '{bucket_name}' as {unique_filename}")
        blob.upload_from_filename(file_path)
        
        # Since bucket has public access configured, files should be accessible
        # Try to make individual blob public as additional measure
        try:
            blob.make_public()
            logger.info("File made publicly accessible via blob-level permissions")
        except Exception as public_error:
            # This is expected with uniform bucket-level access - bucket-level permissions apply
            logger.info(f"Using bucket-level public access (uniform access enabled): {public_error}")
        
        # Return public URL - should work due to bucket-level public access
        public_url = f"{base_url}/{unique_filename}"
        logger.info(f"File uploaded successfully to public bucket: {public_url}")
        return public_url
        
    except Exception as e:
        logger.error(f"Failed to upload file to GCS: {e}")
        # Fallback: return local file path (for development)
        logger.warning("Using local file path as fallback")
        return file_path


def image2text(input_path: str, gemini_api_key: str, api_config: dict = None) -> str:
    """
    Convert image to text using Gemini 2.5 Pro Vision
    
    Args:
        input_path (str): Path to image file
        gemini_api_key (str): Gemini API key
    
    Returns:
        str: Description of the image
    """
    try:
        # Configure Gemini
        genai.configure(api_key=gemini_api_key)
        
        # Upload image to Google Cloud Storage
        image_url = upload_to_gcs(input_path, api_config)
        
        # Use Gemini 3 Pro Preview model for vision
        model = genai.GenerativeModel('gemini-3-pro-preview')
        
        # If image is uploaded to GCS, use URL; otherwise use local file
        if image_url.startswith('http'):
            # Use image URL with enhanced factual focus
            prompt = [
                """Analyze this image and extract ONLY verifiable factual information.
                
                FOCUS ONLY ON:
                ✅ Text content visible in the image (signs, captions, titles, labels)
                ✅ Names of people, places, organizations visible or mentioned
                ✅ Specific dates, numbers, statistics, measurements shown
                ✅ Historical events, scientific facts, or documented phenomena
                ✅ Verifiable statements about real-world entities or events
                
                IGNORE:
                ❌ Visual descriptions (colors, lighting, composition, backgrounds)
                ❌ Aesthetic opinions (beautiful, stunning, nice)
                ❌ General observations about appearance or setting
                ❌ Spatial relationships and positioning details
                ❌ Scene descriptions and visual elements
                
                Provide ONLY the factual, verifiable information visible in this image.""",
                {
                    "mime_type": "image/jpeg",
                    "data": image_url
                }
            ]
        else:
            # Use local file
            with open(input_path, 'rb') as image_file:
                image_data = image_file.read()
            
            # Use local file with enhanced factual focus
            prompt = [
                """Analyze this image and extract ONLY verifiable factual information.
                
                FOCUS ONLY ON:
                ✅ Text content visible in the image (signs, captions, titles, labels)
                ✅ Names of people, places, organizations visible or mentioned
                ✅ Specific dates, numbers, statistics, measurements shown
                ✅ Historical events, scientific facts, or documented phenomena
                ✅ Verifiable statements about real-world entities or events
                
                IGNORE:
                ❌ Visual descriptions (colors, lighting, composition, backgrounds)
                ❌ Aesthetic opinions (beautiful, stunning, nice)
                ❌ General observations about appearance or setting
                ❌ Spatial relationships and positioning details
                ❌ Scene descriptions and visual elements
                
                Provide ONLY the factual, verifiable information visible in this image.""",
                {
                    "mime_type": "image/jpeg",
                    "data": image_data
                }
            ]
        
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        logger.error(f"Error processing image with Gemini Vision: {e}")
        return f"Error processing image: {str(e)}"


def video2text(input_path: str, gemini_api_key: str, api_config: dict = None) -> str:
    """
    Convert video to text using Gemini 2.5 Pro Vision
    
    Args:
        input_path (str): Path to video file
        gemini_api_key (str): Gemini API key
    
    Returns:
        str: Description of the video content
    """
    try:
        # Configure Gemini
        genai.configure(api_key=gemini_api_key)
        
        # Upload video to Google Cloud Storage
        video_url = upload_to_gcs(input_path, api_config)
        
        # Use Gemini 3 Pro Preview model
        model = genai.GenerativeModel('gemini-3-pro-preview')
        
        # If video is uploaded to GCS, use URL; otherwise extract frames
        if video_url.startswith('http'):
            # Use video URL directly with Gemini - Enhanced prompt for factual extraction
            prompt = [
                """Analyze this video and extract ONLY verifiable factual information. 
                
                FOCUS ONLY ON:
                ✅ Text content visible in the video (signs, captions, titles, labels)
                ✅ Names of people, places, organizations mentioned or visible
                ✅ Specific dates, numbers, statistics, measurements shown
                ✅ Historical events, scientific facts, or documented phenomena
                ✅ Verifiable statements about real-world entities or events
                ✅ Audio content with factual claims (if any)
                
                IGNORE:
                ❌ Visual descriptions (colors, lighting, composition)
                ❌ Aesthetic opinions (beautiful, stunning, nice)
                ❌ General observations about appearance
                ❌ Spatial relationships and positioning
                ❌ Background descriptions and scene setting
                
                Provide a chronological list of ONLY the factual, verifiable information visible or mentioned in the video.""",
                {
                    "mime_type": "video/mp4",
                    "data": video_url
                }
            ]
        else:
            # Fallback: Extract frames and analyze
            frames = extract_video_frames(input_path)
            if not frames:
                return "Error: Could not extract frames from video"
            
            # Analyze multiple frames with enhanced factual focus and chronological processing
            prompt = [
                """These are frames from a video extracted in chronological order (1 frame per second). Analyze the sequence and extract ONLY verifiable factual information.
                
                FOCUS ONLY ON:
                ✅ Text content visible across frames (signs, captions, titles, labels)
                ✅ Names of people, places, organizations that appear
                ✅ Specific dates, numbers, statistics, measurements shown
                ✅ Historical events, scientific facts, or documented phenomena
                ✅ Verifiable statements about real-world entities or events
                ✅ Sequential factual information that develops across frames
                ✅ Chronological progression of facts throughout the video
                
                IGNORE:
                ❌ Visual descriptions (colors, lighting, composition, backgrounds)
                ❌ Aesthetic opinions (beautiful, stunning, nice)
                ❌ General observations about appearance or setting
                ❌ Spatial relationships and positioning details
                ❌ Scene descriptions and visual elements
                
                IMPORTANT: Process frames in chronological order and maintain temporal context. 
                Provide a chronological list of ONLY the factual, verifiable information visible across these video frames with approximate timestamps."""
            ]
            
            # Add frame data with timestamp information for chronological processing
            for i, frame_data in enumerate(frames[:120]):  # Limit to 120 frames (2 minutes) for API limits
                timestamp_seconds = i  # Since we extract 1 frame per second
                prompt.append({
                    "mime_type": "image/jpeg",
                    "data": frame_data
                })
        
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        logger.error(f"Error processing video with Gemini Vision: {e}")
        return f"Error processing video: {str(e)}"


def extract_video_frames(video_path: str, frames_per_second: int = 1, max_frames: int = 300) -> list:
    """
    Extract frames from video for analysis - 1 frame per second for comprehensive coverage
    
    Args:
        video_path (str): Path to video file
        frames_per_second (int): Number of frames to extract per second (default: 1)
        max_frames (int): Maximum total frames to prevent memory issues (default: 300 = 5 minutes)
    
    Returns:
        list: List of frame data as bytes in chronological order
    """
    frames = []
    try:
        video = cv2.VideoCapture(video_path)
        fps = video.get(cv2.CAP_PROP_FPS)
        total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        logger.info(f"Video info: {total_frames} total frames, {fps:.2f} fps, {duration:.2f}s duration")
        
        # Calculate frame interval based on FPS to get 1 frame per second
        frame_interval = int(fps / frames_per_second) if fps > 0 else 1
        frame_interval = max(1, frame_interval)  # Ensure at least 1
        
        # Calculate how many frames we'll extract
        expected_frames = min(int(duration * frames_per_second), max_frames)
        logger.info(f"Extracting ~{expected_frames} frames (1 per {1/frames_per_second:.1f}s, interval: {frame_interval})")
        
        frame_count = 0
        extracted_count = 0
        
        # Sequential processing in chronological order
        while video.isOpened() and extracted_count < max_frames:
            success, frame = video.read()
            if not success:
                break
                
            # Extract frame at specified interval (every second by default)
            if frame_count % frame_interval == 0:
                # Encode frame as JPEG
                _, buffer = cv2.imencode('.jpg', frame)
                frames.append(buffer.tobytes())
                extracted_count += 1
                
                # Log progress for long videos
                if extracted_count % 30 == 0:  # Every 30 frames (30 seconds)
                    logger.info(f"Extracted {extracted_count} frames ({extracted_count/frames_per_second:.1f}s processed)")
            
            frame_count += 1
        
        video.release()
        logger.info(f"Successfully extracted {len(frames)} frames from video in chronological order")
        return frames
        
    except Exception as e:
        logger.error(f"Error extracting frames from video: {e}")
        return []


def extract_factual_claims(description_text: str, gemini_api_key: str) -> str:
    """
    Extract only factual claims from image/video description text,
    filtering out visual descriptions, colors, layouts, and aesthetic opinions.
    
    Args:
        description_text (str): The text description from image/video processing
        gemini_api_key (str): Gemini API key
    
    Returns:
        str: Extracted factual claims only
    """
    try:
        # Configure Gemini
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel('gemini-3-pro-preview')
        
        prompt = f"""
You are a fact-checking assistant tasked with extracting ONLY verifiable factual claims from image/video descriptions.

Your task is to analyze the following description and extract ONLY statements that can be fact-checked and verified through external sources.

=== STRICT INCLUSION CRITERIA ===
Extract ONLY these types of verifiable claims:
✅ Specific numerical facts, statistics, measurements, dates, years
✅ Names of real people, organizations, institutions, companies
✅ Geographic locations, addresses, place names
✅ Historical events, scientific facts, documented phenomena
✅ Verifiable text content that appears in the image/video (signs, labels, captions)
✅ Factual statements about real-world entities, products, or services
✅ Claims about relationships, affiliations, or associations between entities
✅ Statements about achievements, awards, records, or accomplishments

=== STRICT EXCLUSION CRITERIA ===
DO NOT extract any of the following:
❌ Visual descriptions (colors, shapes, sizes, positioning)
❌ Background descriptions ("white background", "blue sky", "green grass")
❌ Aesthetic opinions ("beautiful", "stunning", "attractive", "nice")
❌ Visual composition details ("in the center", "on the left", "at the top")
❌ Object appearances ("red car", "tall building", "large window")
❌ General observations ("there is", "shows", "depicts", "contains")
❌ Subjective assessments ("seems", "appears to be", "looks like")
❌ Spatial relationships ("next to", "behind", "in front of")
❌ Visual qualities ("bright", "dark", "clear", "blurry")
❌ Descriptive adjectives about appearance ("modern", "old", "new")
❌ Weather conditions visible in image ("sunny", "cloudy", "rainy")
❌ Lighting conditions ("well-lit", "shadowy", "dimly lit")

=== EXAMPLES ===

Example 1:
Input: "The image shows a red brick building with a white background. There's a sign that reads 'New York Public Library - Main Branch'. The building has beautiful architecture with tall columns. The library was established in 1895 and serves over 50 million visitors annually."
Output: 
New York Public Library - Main Branch
The library was established in 1895
Serves over 50 million visitors annually

Example 2:
Input: "The image has a white background showing a person in a blue shirt. The text says 'Einstein won the Nobel Prize in Physics in 1921'. The person appears to be in a laboratory setting with various equipment."
Output:
Einstein won the Nobel Prize in Physics in 1921

Example 3:
Input: "A beautiful landscape with green trees and blue sky. The scene appears peaceful and serene with mountains in the background."
Output:
No verifiable factual claims found.

=== YOUR TASK ===
Analyze this description and extract ONLY the verifiable factual claims:

{description_text}

=== RESPONSE FORMAT ===
Provide ONLY the factual claims, one per line. If no verifiable claims exist, respond with "No verifiable factual claims found."

Extracted factual claims:
"""
        
        response = model.generate_content(prompt)
        extracted_claims = response.text.strip()
        
        # If no claims were found, return a message indicating this
        if not extracted_claims or extracted_claims.lower() in ["no verifiable factual claims found", "no verifiable claims found", "none", "no claims"]:
            return "No verifiable factual claims found in the uploaded content."
        
        logger.info(f"Extracted factual claims from description: {extracted_claims}")
        return extracted_claims
        
    except Exception as e:
        logger.error(f"Error extracting factual claims: {e}")
        # Fallback to original description if extraction fails
        return description_text


def modal_normalization(modal="text", input=None, gemini_api_key=None, api_config=None):
    """
    Process different input modalities and convert to text
    
    Args:
        modal (str): Input type - 'string', 'text', 'image', 'video'
        input: Input content or path to file
        gemini_api_key (str): Gemini API key for vision processing
    
    Returns:
        str: Processed text content
    """
    logger.info(f"== Processing: Modal: {modal}, Input: {input}")
    
    if modal == "string":
        response = str(input)
    elif modal == "text":
        with open(input, "r", encoding="utf-8") as f:
            response = f.read()
    elif modal == "image":
        if not gemini_api_key:
            raise ValueError("Gemini API key required for image processing")
        # Step 1: Extract factual content from image (enhanced prompt)
        description = image2text(input, gemini_api_key, api_config)
        # Step 2: Additional factual claim filtering for any remaining visual content
        response = extract_factual_claims(description, gemini_api_key)
    elif modal == "video":
        if not gemini_api_key:
            raise ValueError("Gemini API key required for video processing")
        # Step 1: Extract factual content from video frames/analysis (enhanced prompt)
        description = video2text(input, gemini_api_key, api_config)
        # Step 2: Additional factual claim filtering for any remaining visual content
        response = extract_factual_claims(description, gemini_api_key)
    elif modal == "speech":
        raise NotImplementedError("Speech processing has been removed. Please use text, image, or video input.")
    else:
        raise NotImplementedError(f"Modal type '{modal}' is not supported. Supported types: string, text, image, video")
    
    logger.info(f"== Processed: Modal: {modal}, Input: {input}")
    return response