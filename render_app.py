"""
render_app.py — Production entry point for Render.com deployment.
Gunicorn loads this file via: gunicorn render_app:app
"""
import os
import threading
from flask import Flask, request, render_template, jsonify
from factcheck.utils.llmclient import CLIENTS
from factcheck.utils.multimodal import modal_normalization
from factcheck.utils.web_util import scrape_url
import json
import tempfile
import re
import logging

from factcheck.utils.utils import load_yaml
from factcheck import FactCheck
from factcheck.core import QueryGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SERVER_TIMEOUT = 180  # seconds


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


# ── Jinja2 filters ───────────────────────────────────────────────────────────
def zip_lists(a, b):
    return zip(a, b)

app.jinja_env.filters["zip"] = zip_lists


def count_occurrences(input_dict, target_string, key):
    input_list = [item[key] for item in input_dict]
    return input_list.count(target_string)

app.jinja_env.filters["count_occurrences"] = count_occurrences


def filter_evidences(input_dict, target_string, key):
    return [item for item in input_dict if target_string == item[key]]

app.jinja_env.filters["filter_evidences"] = filter_evidences


def format_percentage(value):
    try:
        return f"{float(value) * 100:.2f}"
    except (ValueError, TypeError):
        return "0.00"

app.jinja_env.filters["format_percentage"] = format_percentage


# ── URL helper ────────────────────────────────────────────────────────────────
def is_url(text):
    url_pattern = re.compile(
        r'^(?:http|ftp)s?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(url_pattern, text) is not None


# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/check", methods=["GET", "POST"])
def check():
    if request.method == "POST":
        config_error = app.config.get('CONFIG_ERROR')
        if config_error:
            return render_template("main_layout.html", error=f"Configuration Error: {config_error}")

        api_config = app.config.get('API_CONFIG', {})
        factcheck_instance = app.config.get('FACTCHECK_INSTANCE')

        if not factcheck_instance:
            return render_template("main_layout.html", error="Fact-check service not available - configuration error")

        response = None

        if 'file' in request.files and request.files['file'].filename != '':
            file = request.files['file']
            temp_dir = tempfile.mkdtemp()
            file_path = os.path.join(temp_dir, file.filename)
            file.save(file_path)

            file_ext = os.path.splitext(file.filename)[1].lower()
            if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
                modal_type = 'image'
            else:
                os.remove(file_path)
                os.rmdir(temp_dir)
                return render_template("main_layout.html", error="Unsupported file type. Please upload an image.")

            try:
                text_content = modal_normalization(
                    modal=modal_type, input=file_path, api_config=api_config
                )
                os.remove(file_path)
                os.rmdir(temp_dir)
                response = run_with_timeout(lambda: factcheck_instance.check_text(text_content))
            except Exception as e:
                if os.path.exists(file_path):
                    os.remove(file_path)
                if os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
                return render_template("main_layout.html", error=f"Error processing file: {str(e)}")

        else:
            text_response = request.form.get("response", "").strip()
            if text_response == "":
                return render_template("main_layout.html", error="Please enter text to fact-check or upload a file.")

            if is_url(text_response):
                try:
                    try:
                        import trafilatura
                        downloaded = trafilatura.fetch_url(text_response)
                        extracted_text = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
                        if not extracted_text:
                            extracted_text, _ = scrape_url(text_response)
                    except ImportError:
                        extracted_text, _ = scrape_url(text_response)

                    if not extracted_text:
                        return render_template("main_layout.html", error="Could not extract text from the provided URL.")

                    MAX_TEXT_LENGTH = 5000
                    if len(extracted_text) > MAX_TEXT_LENGTH:
                        extracted_text = extracted_text[:MAX_TEXT_LENGTH] + "..."

                    response = run_with_timeout(lambda: factcheck_instance.check_text(extracted_text))
                except TimeoutError as e:
                    return render_template("main_layout.html", error=str(e))
                except Exception as e:
                    return render_template("main_layout.html", error=f"Error scraping URL: {str(e)}")
            else:
                try:
                    response = run_with_timeout(lambda: factcheck_instance.check_text(text_response))
                except TimeoutError as e:
                    return render_template("main_layout.html", error=str(e))

        if response:
            os.makedirs("assets", exist_ok=True)
            with open("assets/response.json", "w") as f:
                json.dump(response, f)

            summary = response.get('summary', {})
            logger.info(
                f"SENDING TO FRONTEND: factuality={summary.get('factuality')}, "
                f"num_claims={summary.get('num_claims')}, "
                f"supported={summary.get('num_supported_claims')}, "
                f"refuted={summary.get('num_refuted_claims')}"
            )

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
        extracted_text, error = extract_text_from_image(image_file)
        if error:
            return jsonify({'error': error}), 400
        return jsonify({'success': True, 'extracted_text': extracted_text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route("/shownClaim/<content_id>")
def get_content(content_id):
    with open("assets/response.json") as f:
        response = json.load(f)
    return render_template("main_layout.html", responses=response, shown_claim=(int(content_id) - 1))


# ── App initialisation (runs once when gunicorn imports this module) ──────────
def _init_app():
    """Load config and FactCheck instance into app.config at startup."""
    # Build api_config: prefer environment variables over yaml
    api_config = {}

    # Try production yaml first, then fall back to local one
    for cfg_path in ["api_config_production.yaml", "api_config.yaml"]:
        if os.path.exists(cfg_path):
            try:
                api_config = load_yaml(cfg_path)
                logger.info(f"Loaded API config from {cfg_path}")
                break
            except Exception as e:
                logger.warning(f"Could not load {cfg_path}: {e}")

    # Always override from environment variables (Render sets these via dashboard)
    for key in ['SERPER_API_KEY', 'GROQ_API_KEY', 'GEMINI_API_KEY']:
        env_val = os.environ.get(key)
        if env_val and env_val.strip():
            api_config[key] = env_val.strip()
            logger.info(f"Using {key} from environment variable")

    # Validate critical keys
    missing = []
    for key in ['SERPER_API_KEY', 'GROQ_API_KEY']:
        if not api_config.get(key, '').strip():
            missing.append(key)

    if missing:
        error_msg = f"Missing required API keys: {', '.join(missing)}"
        logger.error(error_msg)
        app.config['CONFIG_ERROR'] = error_msg
        app.config['API_CONFIG'] = api_config
        app.config['FACTCHECK_INSTANCE'] = None
        return

    app.config['API_CONFIG'] = api_config

    try:
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
        # Reduce queries per claim for speed
        factcheck_instance.query_generator = QueryGenerator(
            llm_client=factcheck_instance.query_generator_model,
            prompt=factcheck_instance.prompt,
            max_query_per_claim=2
        )
        app.config['FACTCHECK_INSTANCE'] = factcheck_instance
        logger.info("✅ FactCheck instance initialised successfully")
    except Exception as e:
        logger.error(f"Failed to initialise FactCheck: {e}")
        app.config['CONFIG_ERROR'] = str(e)
        app.config['FACTCHECK_INSTANCE'] = None


# Run initialisation when the module is loaded (gunicorn imports this once)
_init_app()
