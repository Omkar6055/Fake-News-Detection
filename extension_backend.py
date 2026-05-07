#!/usr/bin/env python3
"""
OpenFactVerification Chrome Extension Backend Server
A lightweight Flask server that acts as a proxy between the Chrome extension and the FactCheck module.
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from factcheck.utils.llmclient import CLIENTS
from factcheck.utils.multimodal import modal_normalization
from factcheck.utils.utils import load_yaml
from factcheck import FactCheck
import argparse
import json
import os
import tempfile
import threading
import time
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for Chrome extension

# Global variables for the fact check instance
factcheck_instance = None
api_config = {}
extension_config = {
    'max_claims': 10,
    'timeout_seconds': 120,
    'enable_debug': False
}

SERVER_TIMEOUT = 150  # seconds


def run_with_timeout(fn, timeout=SERVER_TIMEOUT):
    """Run fn() in a daemon thread; raise TimeoutError if it exceeds timeout."""
    result = [None]
    error = [None]

    def target():
        try:
            result[0] = fn()
        except Exception as e:
            error[0] = e

    t = threading.Thread(target=target, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        raise TimeoutError(f"Fact-check timed out after {timeout}s.")
    if error[0]:
        raise error[0]
    return result[0]


def initialize_factcheck(config_path="api_config.yaml"):
    """Initialize the FactCheck instance with configuration."""
    global factcheck_instance, api_config
    
    try:
        # Load API config
        if os.path.exists(config_path):
            api_config = load_yaml(config_path)
            logger.info(f"Loaded API config from {config_path}")
        else:
            logger.warning(f"Config file {config_path} not found, using environment variables")
            api_config = {
                'GROQ_API_KEY': os.getenv('GROQ_API_KEY'),
                'SERPER_API_KEY': os.getenv('SERPER_API_KEY')
            }

        # Use faster 8b model for lightweight steps, keep 70b for critical verification
        fast_model = "llama-3.1-8b-instant"
        factcheck_instance = FactCheck(
            default_model="llama-3.3-70b-versatile",
            api_config=api_config,
            prompt="chatgpt_prompt",
            retriever="serper",
            decompose_model=fast_model,
            checkworthy_model=fast_model,
            query_generator_model=fast_model,
            claim_verify_model="llama-3.3-70b-versatile",
            num_seed_retries=1,
        )
        
        logger.info("FactCheck instance initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize FactCheck: {e}")
        return False

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", 
                    "message": "connected"})

@app.route('/api/factcheck', methods=['POST'])
def factcheck_text():
    """Fact-check text content."""
    if not factcheck_instance:
        return jsonify({
            'success': False,
            'error': 'FactCheck service not initialized. Please check server configuration.'
        }), 503

    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({
                'success': False,
                'error': 'No text provided for fact-checking'
            }), 400

        text = data['text'].strip()
        if not text:
            return jsonify({
                'success': False,
                'error': 'Empty text provided'
            }), 400

        # Limit text length to prevent API overload
        max_length = 5000
        if len(text) > max_length:
            text = text[:max_length]
            logger.info(f"Text truncated to {max_length} characters")

        logger.info(f"Processing fact-check request for text of length {len(text)}")
        
        # Process with timeout
        result = run_with_timeout(lambda: factcheck_instance.check_text(text))
        
        # Limit the number of claims if configured
        if result and 'claim_detail' in result:
            max_claims = extension_config.get('max_claims', 10)
            if len(result['claim_detail']) > max_claims:
                result['claim_detail'] = result['claim_detail'][:max_claims]
                logger.info(f"Limited results to {max_claims} claims")

        # DEBUG: print what we're sending to frontend
        summary = result.get('summary', {}) if result else {}
        print(f"SENDING TO FRONTEND: factuality={summary.get('factuality')}, "
              f"num_claims={summary.get('num_claims')}, "
              f"num_verified={summary.get('num_verified_claims')}, "
              f"supported={summary.get('num_supported_claims')}, "
              f"refuted={summary.get('num_refuted_claims')}, "
              f"claim_detail_count={len(result.get('claim_detail', []) if result else [])}")

        # Transform the result to the requested format while preserving old fields
        transformed_result = {
            "overall_score": int(summary.get('factuality', 0) * 100),
            "supported": summary.get('num_supported_claims', 0),
            "refuted": summary.get('num_refuted_claims', 0),
            "controversial": summary.get('num_controversial_claims', 0),
            "claims": result.get('claim_detail', []),
            
            # Keep original fields for popup.js backward compatibility
            "summary": summary,
            "claim_detail": result.get('claim_detail', [])
        }

        return jsonify({
            'success': True,
            'data': transformed_result
        })

    except Exception as e:
        logger.error(f"Error in fact-checking: {e}")
        return jsonify({
            'success': False,
            'error': f'Fact-checking failed: {str(e)}'
        }), 500

@app.route('/api/factcheck-file', methods=['POST'])
def factcheck_file():
    """Fact-check uploaded file (image or video)."""
    if not factcheck_instance:
        return jsonify({
            'success': False,
            'error': 'FactCheck service not initialized. Please check server configuration.'
        }), 503

    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file uploaded'
            }), 400

        file = request.files['file']
        file_type = request.form.get('type', 'image')

        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400

        # Validate file type
        allowed_extensions = {
            'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'],
            'video': ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v']
        }
        
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions.get(file_type, []):
            return jsonify({
                'success': False,
                'error': f'Unsupported file type: {file_ext}'
            }), 400

        # Save file temporarily
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, file.filename)
        file.save(file_path)
        
        # Validate saved file
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': 'Failed to save uploaded file'
            }), 500
            
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return jsonify({
                'success': False,
                'error': 'Uploaded file is empty'
            }), 400
            
        logger.info(f"File saved successfully: {file_path} (size: {file_size} bytes)")
        
        # Debug: Check file content
        try:
            with open(file_path, 'rb') as debug_file:
                first_bytes = debug_file.read(16)
                logger.info(f"First 16 bytes of file: {first_bytes}")
        except Exception as debug_error:
            logger.warning(f"Could not read file for debugging: {debug_error}")

        try:
            logger.info(f"Processing {file_type} file: {file.filename}")
            
            # Additional validation for image files
            if file_type == 'image':
                try:
                    from PIL import Image
                    with Image.open(file_path) as img:
                        logger.info(f"Image validation successful: {img.format} {img.size} {img.mode}")
                except Exception as img_error:
                    logger.error(f"Image validation failed: {img_error}")
                    return jsonify({
                        'success': False,
                        'error': f'Invalid image file: {str(img_error)}'
                    }), 400
            
            # Process the file using multimodal processing
            text_content = modal_normalization(
                modal=file_type,
                input=file_path,
                api_config=api_config
            )

            if not text_content or text_content.strip() == "":
                logger.warning("No text content extracted from file")
                text_content = "No extractable content found in the file"

            # Process with fact-checking (with timeout)
            result = run_with_timeout(lambda: factcheck_instance.check_text(text_content))
            
            # Limit the number of claims if configured
            if result and 'claim_detail' in result:
                max_claims = extension_config.get('max_claims', 10)
                if len(result['claim_detail']) > max_claims:
                    result['claim_detail'] = result['claim_detail'][:max_claims]

            summary = result.get('summary', {}) if result else {}
            transformed_result = {
                "overall_score": int(summary.get('factuality', 0) * 100),
                "supported": summary.get('num_supported_claims', 0),
                "refuted": summary.get('num_refuted_claims', 0),
                "controversial": summary.get('num_controversial_claims', 0),
                "claims": result.get('claim_detail', []),
                "summary": summary,
                "claim_detail": result.get('claim_detail', [])
            }

            return jsonify({
                'success': True,
                'data': transformed_result,
                'extracted_text': text_content[:500] + ('...' if len(text_content) > 500 else '')
            })

        finally:
            # Clean up temporary file
            try:
                os.remove(file_path)
                os.rmdir(temp_dir)
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up temporary files: {cleanup_error}")

    except Exception as e:
        logger.error(f"Error in file fact-checking: {e}")
        return jsonify({
            'success': False,
            'error': f'File processing failed: {str(e)}'
        }), 500

@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    """Handle configuration updates from the extension."""
    global extension_config, api_config, factcheck_instance
    
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'config': {
                **extension_config,
                'api_keys_configured': bool(api_config.get('GROQ_API_KEY'))
            }
        })
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'No configuration data provided'
                }), 400

            # Update extension config
            if 'max_claims' in data:
                extension_config['max_claims'] = max(1, min(50, int(data['max_claims'])))
            if 'timeout_seconds' in data:
                extension_config['timeout_seconds'] = max(30, min(300, int(data['timeout_seconds'])))
            if 'enable_debug' in data:
                extension_config['enable_debug'] = bool(data['enable_debug'])

            # Update API config if keys provided
            if 'groq_api_key' in data and data['groq_api_key'].strip():
                api_config['GROQ_API_KEY'] = data['groq_api_key'].strip()
            if 'serper_api_key' in data and data['serper_api_key'].strip():
                api_config['SERPER_API_KEY'] = data['serper_api_key'].strip()

            # Reinitialize FactCheck if API keys changed
            if 'groq_api_key' in data or 'serper_api_key' in data:
                logger.info("Reinitializing FactCheck with new API keys")
                factcheck_instance = FactCheck(
                    default_model="llama-3.3-70b-versatile",
                    api_config=api_config,
                    prompt="chatgpt_prompt",
                    retriever="serper",
                )

            return jsonify({
                'success': True,
                'message': 'Configuration updated successfully'
            })

        except Exception as e:
            logger.error(f"Error updating configuration: {e}")
            return jsonify({
                'success': False,
                'error': f'Configuration update failed: {str(e)}'
            }), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get server statistics."""
    stats = {
        'server_uptime': time.time() - app._start_time if hasattr(app, '_start_time') else 0,
        'factcheck_ready': factcheck_instance is not None,
        'config': extension_config,
        'api_keys_configured': {
            'groq': bool(api_config.get('GROQ_API_KEY')),
            'serper': bool(api_config.get('SERPER_API_KEY'))
        }
    }
    return jsonify(stats)

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

def run_server(host='127.0.0.1', port=2025, debug=False):
    """Run the Flask server."""
    logger.info(f"Starting OpenFactVerification Extension Backend on {host}:{port}")
    logger.info("Make sure to configure your API keys before using the extension")
    
    app._start_time = time.time()
    app.run(host=host, port=port, debug=debug, threaded=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 2025))
    app.run(host='0.0.0.0', port=port, debug=False)