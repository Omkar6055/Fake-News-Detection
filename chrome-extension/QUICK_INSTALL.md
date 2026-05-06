# Chrome Extension Installation Guide

## Quick Start (5 Minutes)

### 1. Install Dependencies
```bash
pip install flask flask-cors
```

### 2. Set Your API Key
```bash
export GEMINI_API_KEY="your_api_key_here"
```

### 3. Start Backend Server
```bash
python extension_backend.py
```
Keep this running! The extension needs it to work.

### 4. Install Extension in Chrome
1. Open Chrome → `chrome://extensions/`
2. Turn on "Developer mode" (top-right toggle)
3. Click "Load unpacked"
4. Select the `chrome-extension` folder
5. Done! 🎉

### 5. Configure Extension
1. Click the extension icon in Chrome
2. Click "Settings" at the bottom
3. Enter your Gemini API key
4. Click "Test Connection" to verify

## Now You Can:
- **Double-click any text** on websites to fact-check
- **Upload images/videos** via the extension popup
- **📷 Capture screen areas** and analyze them like Google Lens
- **Analyze entire web pages** for factual content
- **See claims highlighted** directly on pages

## Need Help?
- Backend not connecting? Make sure `python extension_backend.py` is running
- No API key? Get one at [Google AI Studio](https://makersuite.google.com/app/apikey)
- Extension not loading? Make sure you selected the `chrome-extension` folder, not the whole project

That's it! You now have AI-powered fact-checking in your browser! 🚀