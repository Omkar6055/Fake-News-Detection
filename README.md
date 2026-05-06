# OpenFactVerification

An open-source tool for automated fact verification that provides a comprehensive pipeline for analyzing texts, extracting claims, searching for evidence, and verifying claims.

## Installation

1. **Clone the repository:**
```bash
git clone https://github.com/himanshusdeshmukh2106/fake-new-detection.git
cd fake-new-detection
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Download spaCy language model:**
```bash
python -m spacy download en_core_web_sm
```

## Configuration

1. **Rename the configuration file:**
```bash
cp api_config_production.yaml api_config.yaml
```

2. **Add your API keys** to `api_config.yaml`:
```yaml
SERPER_API_KEY: "your_serper_api_key_here"
GEMINI_API_KEY: "your_gemini_api_key_here"
```

## Usage

### Web Application

1. **Start the main web application:**
```bash
python webapp.py --api_config api_config.yaml
```
   The web application will be available at: `http://localhost:5000`

2. **Start the Chrome extension backend** (in a separate terminal):
```bash
python extension_backend.py 
```
   The extension backend will run on: `http://localhost:2024`

### Chrome Extension

1. **Load the extension in Chrome:**
   - Open Chrome and go to `chrome://extensions/`
   - Enable "Developer mode"
   - Click "Load unpacked" and select the `chrome-extension` folder
   - Pin the extension to your toolbar

2. **Use the extension:**
   - Make sure the extension backend is running (`python extension_backend.py`)
   - Click the extension icon in your browser toolbar
   - Use the fact-checking features directly in your browser

## API Keys Required

- **SERPER_API_KEY**: Get from [Serper.dev](https://serper.dev) for web search functionality
- **GEMINI_API_KEY**: Get from [Google AI Studio](https://aistudio.google.com) for AI processing

## Features

- **ML-Enhanced Claim Classification** - 60% API call reduction with 93.75% accuracy
- Text analysis and claim extraction
- Evidence retrieval from web sources
- Automated claim verification
- Chrome extension for browser integration
- Multimodal input support (text, images, videos)
- Semantic similarity matching for better evidence ranking
- Source credibility scoring

## ML Enhancements (NEW!)

This project now includes machine learning models to optimize performance:

### Claim Classifier
- **Accuracy:** 93.75% (100% checkworthy recall)
- **API Call Reduction:** 50-60%
- **Cost Savings:** $0.30-$1.00 per request
- **Speed:** 2-3x faster processing

### Setup ML Model

**Option 1: Download Pre-trained Model**
1. Download the model files from [Google Drive](YOUR_LINK_HERE)
2. Extract to `factcheck/ml_models/trained_model/`
3. The system will automatically use the ML classifier

**Option 2: Train Your Own (Google Colab)**
```bash
# See ML_ENHANCEMENTS_README.md for detailed instructions
python factcheck/ml_models/train_classifier.py
```

The system automatically falls back to LLM-only mode if the ML model is not available.

For more details, see:
- `ML_ENHANCEMENTS_README.md` - Complete ML documentation
- `CLAIM_CLASSIFIER_GUIDE.md` - Classifier usage guide
- `ML_ENHANCEMENT_RESEARCH.md` - Research and recommendations

## Contributing

Welcome contributions! Please feel free to submit issues and pull requests.

## License

This project is open source. Please check the license file for more details.