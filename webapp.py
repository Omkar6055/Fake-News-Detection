from flask import Flask, request, render_template, jsonify
from factcheck.utils.llmclient import CLIENTS
from factcheck.utils.multimodal import modal_normalization
from factcheck.utils.web_util import scrape_url
import argparse
import json
import os
import tempfile
import re
import threading

from factcheck.utils.utils import load_yaml
from factcheck import FactCheck

SERVER_TIMEOUT = 180  # seconds before returning a timeout error to the user


def run_with_timeout(fn, timeout=SERVER_TIMEOUT):
    """Run fn() in a background thread; raise TimeoutError if it takes too long."""
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
        raise TimeoutError(
            f"Fact-check timed out after {timeout}s. "
            "Try using shorter text (under 500 words)."
        )
    if error[0]:
        raise error[0]
    return result[0]


app = Flask(__name__, static_folder="assets")



# Define the custom filter
def zip_lists(a, b):
    return zip(a, b)


# Register the filter with the Jinja2 environment
app.jinja_env.filters["zip"] = zip_lists


# Occurrences count filter
def count_occurrences(input_dict, target_string, key):
    input_list = [item[key] for item in input_dict]
    return input_list.count(target_string)


app.jinja_env.filters["count_occurrences"] = count_occurrences


# Occurrences count filter
def filter_evidences(input_dict, target_string, key):
    return [item for item in input_dict if target_string == item[key]]


app.jinja_env.filters["filter_evidences"] = filter_evidences


# Format percentage to 2 decimal places
def format_percentage(value):
    """Format a decimal value as a percentage with exactly 2 decimal places."""
    try:
        percentage = float(value) * 100
        return f"{percentage:.2f}"
    except (ValueError, TypeError):
        return "0.00"


app.jinja_env.filters["format_percentage"] = format_percentage


def is_url(text):
    """Check if the text is a valid URL."""
    url_pattern = re.compile(
        r'^(?:http|ftp)s?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(url_pattern, text) is not None


@app.route("/")
def landing():
    return render_template("landing.html")

@app.route("/check", methods=["GET", "POST"])
def check():
    if request.method == "POST":
        # Check if there's a configuration error
        config_error = app.config.get('CONFIG_ERROR')
        if config_error:
            return render_template("main_layout.html", error=f"Configuration Error: {config_error}")
        
        # Get global config and factcheck instance
        api_config = app.config.get('API_CONFIG', {})
        factcheck_instance = app.config.get('FACTCHECK_INSTANCE')
        
        if not factcheck_instance:
            return render_template("main_layout.html", error="Fact-check service not available - configuration error")
        
        response = None
        
        # Check if it's file upload first
        if 'file' in request.files and request.files['file'].filename != '':
            # Handle file upload (image or video)
            file = request.files['file']
            
            # Save file temporarily
            temp_dir = tempfile.mkdtemp()
            file_path = os.path.join(temp_dir, file.filename)
            file.save(file_path)
            
            # Determine modal type from file extension
            file_ext = os.path.splitext(file.filename)[1].lower()
            if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
                modal_type = 'image'
            else:
                # Clean up and return error
                os.remove(file_path)
                os.rmdir(temp_dir)
                return render_template("main_layout.html", error="Unsupported file type. Please upload an image.")
            
            try:
                # Process the file using multimodal processing
                text_content = modal_normalization(
                    modal=modal_type,
                    input=file_path,
                    api_config=api_config
                )
                
                # Clean up temporary file
                os.remove(file_path)
                os.rmdir(temp_dir)
                
                # Process with fact-checking (with server-side timeout)
                response = run_with_timeout(lambda: factcheck_instance.check_text(text_content))
                
            except Exception as e:
                # Clean up on error
                if os.path.exists(file_path):
                    os.remove(file_path)
                if os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
                return render_template("main_layout.html", error=f"Error processing file: {str(e)}")
                
        else:
            # Handle text input
            text_response = request.form.get("response", "").strip()
            if text_response == "":
                return render_template("main_layout.html", error="Please enter text to fact-check or upload a file.")
            
            # Check if input is a URL
            if is_url(text_response):
                try:
                    # Try to extract main article content using trafilatura for better extraction
                    try:
                        import trafilatura
                        downloaded = trafilatura.fetch_url(text_response)
                        extracted_text = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
                        if not extracted_text:
                            # Fallback to basic scraper
                            extracted_text, _ = scrape_url(text_response)
                    except ImportError:
                        # If trafilatura not available, use basic scraper
                        extracted_text, _ = scrape_url(text_response)
                    
                    if not extracted_text:
                        return render_template("main_layout.html", error="Could not extract text from the provided URL.")
                    
                    # Limit text length to improve processing speed (first 5000 chars ~ 3-5 paragraphs)
                    MAX_TEXT_LENGTH = 5000
                    if len(extracted_text) > MAX_TEXT_LENGTH:
                        extracted_text = extracted_text[:MAX_TEXT_LENGTH] + "..."
                    
                    # Use the extracted text for fact-checking (with server-side timeout)
                    response = run_with_timeout(lambda: factcheck_instance.check_text(extracted_text))
                except TimeoutError as e:
                    return render_template("main_layout.html", error=str(e))
                except Exception as e:
                    return render_template("main_layout.html", error=f"Error scraping URL: {str(e)}")
            else:
                # Process as regular text (with server-side timeout)
                response = run_with_timeout(lambda: factcheck_instance.check_text(text_response))

        # If we have a response, save it and return results
        if response:
            # Save the response json file
            os.makedirs("assets", exist_ok=True)
            with open("assets/response.json", "w") as f:
                json.dump(response, f)

            # DEBUG: print what we're sending to frontend
            summary = response.get('summary', {})
            print(f"SENDING TO FRONTEND: factuality={summary.get('factuality')}, "
                  f"num_claims={summary.get('num_claims')}, "
                  f"num_verified={summary.get('num_verified_claims')}, "
                  f"supported={summary.get('num_supported_claims')}, "
                  f"refuted={summary.get('num_refuted_claims')}, "
                  f"claim_detail_count={len(response.get('claim_detail', []))}")

            return render_template("main_layout.html", responses=response, shown_claim=0)
        else:
            return render_template("main_layout.html", error="No response generated. Please try again.")

    return render_template("main_layout.html")


@app.route('/extract-image-text', methods=['POST'])
def extract_image_text():
    try:
        from factcheck.utils.image_processor import extract_text_from_image
        
        if 'image' not in request.files:
            return jsonify({'error': 'No image uploaded'}), 400
            
        image_file = request.files['image']
        
        if image_file.filename == '':
            return jsonify({'error': 'No image selected'}), 400
        
        # Extract text from image
        extracted_text, error = extract_text_from_image(image_file)
        
        if error:
            return jsonify({'error': error}), 400
            
        return jsonify({
            'success': True,
            'extracted_text': extracted_text
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route("/shownClaim/<content_id>")
def get_content(content_id):
    # load the response json file
    import json

    with open("assets/response.json") as f:
        response = json.load(f)

    return render_template("main_layout.html", responses=response, shown_claim=(int(content_id) - 1))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default="llama-3.3-70b-versatile")
    parser.add_argument("--client", type=str, default=None, choices=CLIENTS.keys())
    parser.add_argument("--prompt", type=str, default="chatgpt_prompt")
    parser.add_argument("--retriever", type=str, default="serper")
    parser.add_argument("--modal", type=str, default="text")
    parser.add_argument("--input", type=str, default="demo_data/text.txt")
    parser.add_argument("--api_config", type=str, default="api_config.yaml")
    args = parser.parse_args()

    # Load API config from yaml file
    try:
        api_config = load_yaml(args.api_config)
    except Exception as e:
        print(f"Error loading api config: {e}")
        api_config = {}

    # Override with environment variables if YAML values are empty
    for key in ['SERPER_API_KEY', 'GROQ_API_KEY']:
        env_val = os.environ.get(key)
        if env_val and (not api_config.get(key) or not api_config.get(key).strip()):
            api_config[key] = env_val

    # Make api_config globally available
    app.config['API_CONFIG'] = api_config

    # Use faster 8b model for lightweight steps, keep 70b for critical verification
    fast_model = "llama-3.1-8b-instant"
    factcheck_instance = FactCheck(
        default_model=args.model,
        api_config=api_config,
        prompt=args.prompt,
        retriever=args.retriever,
        decompose_model=fast_model,
        checkworthy_model=fast_model,
        query_generator_model=fast_model,
        claim_verify_model=args.model,  # Keep 70b for accuracy on verification
        num_seed_retries=1,  # Reduced from 3 to 1 for faster processing
    )
    
    # Override QueryGenerator to use fewer queries per claim for speed
    from factcheck.core import QueryGenerator
    factcheck_instance.query_generator = QueryGenerator(
        llm_client=factcheck_instance.query_generator_model,
        prompt=factcheck_instance.prompt,
        max_query_per_claim=2  # Reduced from 5 to 2 for faster processing
    )

    # Make factcheck_instance globally available
    app.config['FACTCHECK_INSTANCE'] = factcheck_instance

    app.run(host="0.0.0.0", port=2024, debug=True)
