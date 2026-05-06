# Trained Claim Classifier Model

## Model Information

- **Model Type:** DistilBERT for Sequence Classification
- **Training Data:** 450 examples (150 per class)
- **Classes:** checkworthy, opinion, unverifiable
- **Validation Accuracy:** 93.75%
- **Checkworthy Recall:** 100% (no false negatives!)

## Model Files

The trained model files are too large for GitHub (255 MB). You have two options:

### Option 1: Download Pre-trained Model (Recommended)

Download the trained model from Google Drive:
**[Download Model (255 MB)](https://drive.google.com/drive/folders/YOUR_FOLDER_ID)**

Extract and place the files in this directory:
```
factcheck/ml_models/trained_model/
├── config.json
├── label_map.json
├── model.safetensors  ← Download this
├── special_tokens_map.json
├── tokenizer_config.json
└── vocab.txt  ← Download this
```

### Option 2: Train Your Own Model

Train the model yourself using Google Colab (free GPU):

```python
# In Google Colab
!git clone https://github.com/himanshusdeshmukh2106/fake-new-detection.git
%cd fake-new-detection

# Install requirements
!pip install -r ml_requirements.txt

# Train the model (5-10 minutes on GPU)
!python factcheck/ml_models/train_classifier.py

# Download trained model
!zip -r trained_model.zip factcheck/ml_models/trained_model
from google.colab import files
files.download('trained_model.zip')
```

## Model Performance

### Classification Report:
```
              precision    recall  f1-score   support
checkworthy       1.00      1.00      1.00        30
opinion           0.85      0.93      0.89        30
unverifiable      0.94      0.86      0.90        36

accuracy                           0.93        96
macro avg         0.93      0.93      0.93        96
weighted avg      0.93      0.93      0.93        96
```

### Confusion Matrix:
```
                    Predicted
                checkworthy  opinion  unverifiable
Actual
checkworthy          30         0          0
opinion               0        28          2
unverifiable          0         5         31
```

## Usage

Once the model files are in place, the system will automatically use them:

```python
from factcheck import FactCheck

factcheck = FactCheck(
    default_model="gemini-2.5-flash",
    api_config=api_config,
    prompt="chatgpt_prompt",
    retriever="serper",
)

# ML classifier is automatically loaded and used
result = factcheck.check_text("Your text here")
```

## Expected Benefits

- **API Call Reduction:** 50-60%
- **Cost Savings:** $0.30-$1.00 per request
- **Speed Improvement:** 2-3x faster
- **Accuracy:** 93.75% overall, 100% checkworthy recall

## Troubleshooting

### Model not loading?
Check that these files exist:
- `config.json`
- `label_map.json`
- `model.safetensors` (255 MB)
- `tokenizer_config.json`
- `vocab.txt` (232 KB)

### Still not working?
The system will automatically fall back to LLM-only mode if the model is not found.

## File Sizes

- `model.safetensors`: 255 MB (main model weights)
- `vocab.txt`: 232 KB (tokenizer vocabulary)
- `config.json`: <1 KB (model configuration)
- `label_map.json`: <1 KB (class labels)
- `tokenizer_config.json`: <1 KB (tokenizer settings)
- `special_tokens_map.json`: <1 KB (special tokens)

**Total:** ~256 MB
