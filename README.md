# FactCheck AI — OpenFactVerification

> 🔍 AI-powered fake news detection system that verifies claims in real-time using LLMs, web search evidence, and a machine learning pre-filter.

---

## Features

- **5-Stage Verification Pipeline** — Decomposes text → filters claims → generates queries → retrieves web evidence → LLM verdict
- **ML-Enhanced CheckWorthiness** — Local BERT classifier pre-filters claims (93.75% accuracy, 50-60% fewer API calls)
- **Source Credibility Weighting** — Trusted sources (BBC, Reuters, AP) weighted 2×; blogs/social media 0.5×
- **Multi-Input Support** — Plain text, URLs (auto-scraped), and image uploads (OCR)
- **Chrome Extension** — Right-click → fact-check any selected text directly in your browser
- **Dual Server Architecture** — Web app UI + separate REST API backend for the extension

---

## Architecture

```
Text / URL / Image
       ↓
  [1] Decompose claims         (llama-3.1-8b-instant)
       ↓
  [2] CheckWorthy filter       (ML classifier → LLM fallback)
       ↓
  [3] Generate search queries  (llama-3.1-8b-instant)
       ↓
  [4] Retrieve web evidence    (Serper Search API)
       ↓
  [5] Verify each claim        (llama-3.3-70b-versatile)
       ↓
  Factuality Score + Summary
```

---

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/Omkar6055/Fake-News-Detection.git
cd Fake-News-Detection
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / Mac
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 4. Configure API Keys

Copy the example config and add your keys:

```bash
cp api_config_example.yaml api_config.yaml
```

Edit `api_config.yaml`:

```yaml
SERPER_API_KEY: "your_serper_api_key_here"
GROQ_API_KEY:   "your_groq_api_key_here"
```

| Key | Where to Get |
|---|---|
| `SERPER_API_KEY` | [serper.dev](https://serper.dev) — web search |
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) — LLM inference |

---

## Running Locally

### Web Application (Port 2024)

```bash
python webapp.py
```

Visit: **http://localhost:2024**

### Chrome Extension Backend (Port 2025)

Open a second terminal:

```bash
python extension_backend.py
```

---

## Chrome Extension Setup

1. Open Chrome → `chrome://extensions/`
2. Enable **Developer mode** (top-right toggle)
3. Click **Load unpacked** → select the `chrome-extension/` folder
4. Click the extension icon in your toolbar
5. Make sure `extension_backend.py` is running on port 2025

---

## ML Model Setup (Optional but Recommended)

The ML claim classifier speeds up processing by 2-3× and reduces API costs.

**Option A — Train from scratch:**
```bash
python factcheck/ml_models/train_classifier.py
```

**Option B — Skip it:** The system automatically falls back to LLM-only mode if no trained model is found.

---

## Project Structure

```
├── webapp.py                    # Main Flask web app (port 2024)
├── extension_backend.py         # Extension REST API server (port 2025)
├── api_config_example.yaml      # Template for API keys
├── factcheck/
│   ├── __init__.py              # FactCheck orchestrator class
│   ├── core/
│   │   ├── Decompose.py         # Stage 1: Text → claims
│   │   ├── CheckWorthy.py       # Stage 2: Claim filter
│   │   ├── QueryGenerator.py    # Stage 3: Search queries
│   │   ├── ClaimVerify.py       # Stage 5: LLM verdict
│   │   └── Retriever/           # Stage 4: Web evidence
│   ├── ml_models/               # ML classifier for checkworthiness
│   └── utils/                   # LLM clients, multimodal, prompts
├── chrome-extension/            # Browser extension (MV3)
├── templates/                   # Jinja2 HTML templates
│   ├── landing.html             # Landing page
│   └── main_layout.html         # Fact-check dashboard
└── assets/                      # Static files (CSS, JS, images)
```

---

## API Endpoints (Extension Backend)

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Server health check |
| `/api/factcheck` | POST | Fact-check text |
| `/api/factcheck-file` | POST | Fact-check image/video |
| `/api/config` | GET/POST | Read/update configuration |
| `/api/stats` | GET | Server statistics |

---

## Contributing

Pull requests are welcome! For major changes, please open an issue first.

## License

MIT License — see [LICENSE](LICENSE) for details.