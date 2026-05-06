"""Lightweight Claim Classification Model"""

import torch
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification
from typing import Dict, List
import os
import json


class ClaimClassifier:
    """
    Lightweight claim classifier to pre-filter claims before expensive LLM calls.
    Uses DistilBERT (66M parameters) - much smaller than BERT (110M).
    """
    
    def __init__(self, model_path: str = None):
        """
        Initialize the claim classifier.
        
        Args:
            model_path: Path to saved model. If None, uses pre-trained base model.
        """
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        if model_path and os.path.exists(model_path):
            # Load fine-tuned model
            self.tokenizer = DistilBertTokenizer.from_pretrained(model_path)
            self.model = DistilBertForSequenceClassification.from_pretrained(model_path)
            
            # Load label mapping
            with open(os.path.join(model_path, 'label_map.json'), 'r') as f:
                label_map_loaded = json.load(f)
                # Convert string keys to integers
                self.label_map = {int(k): v for k, v in label_map_loaded.items()}
        else:
            # Use base model with default labels
            self.tokenizer = DistilBertTokenizer.from_pretrained('distilbert-base-uncased')
            self.model = DistilBertForSequenceClassification.from_pretrained(
                'distilbert-base-uncased',
                num_labels=3  # checkworthy, opinion, unverifiable
            )
            self.label_map = {
                0: 'checkworthy',
                1: 'opinion',
                2: 'unverifiable'
            }
        
        self.model.to(self.device)
        self.model.eval()
        
        # Reverse mapping
        self.label_to_id = {v: k for k, v in self.label_map.items()}
    
    def classify(self, claim: str) -> Dict:
        """
        Classify a single claim.
        
        Args:
            claim: The claim text to classify
        
        Returns:
            Dict with keys: label, confidence, all_scores
        """
        # Tokenize
        inputs = self.tokenizer(
            claim,
            return_tensors='pt',
            truncation=True,
            max_length=128,
            padding=True
        ).to(self.device)
        
        # Predict
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probs = torch.softmax(logits, dim=1)[0]
        
        # Get prediction
        pred_id = torch.argmax(probs).item()
        confidence = probs[pred_id].item()
        label = self.label_map[pred_id]
        
        # All scores
        all_scores = {
            self.label_map[i]: float(probs[i])
            for i in range(len(self.label_map))
        }
        
        return {
            'label': label,
            'confidence': round(confidence, 3),
            'all_scores': all_scores,
            'is_checkworthy': label == 'checkworthy' and confidence > 0.6
        }
    
    def classify_batch(self, claims: List[str], batch_size: int = 8) -> List[Dict]:
        """
        Classify multiple claims efficiently.
        
        Args:
            claims: List of claim texts
            batch_size: Number of claims to process at once
        
        Returns:
            List of classification results
        """
        results = []
        
        for i in range(0, len(claims), batch_size):
            batch = claims[i:i + batch_size]
            
            # Tokenize batch
            inputs = self.tokenizer(
                batch,
                return_tensors='pt',
                truncation=True,
                max_length=128,
                padding=True
            ).to(self.device)
            
            # Predict
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probs = torch.softmax(logits, dim=1)
            
            # Process results
            for j, prob in enumerate(probs):
                pred_id = torch.argmax(prob).item()
                confidence = prob[pred_id].item()
                label = self.label_map[pred_id]
                
                all_scores = {
                    self.label_map[k]: float(prob[k])
                    for k in range(len(self.label_map))
                }
                
                results.append({
                    'claim': batch[j],
                    'label': label,
                    'confidence': round(confidence, 3),
                    'all_scores': all_scores,
                    'is_checkworthy': label == 'checkworthy' and confidence > 0.6
                })
        
        return results
    
    def filter_checkworthy(self, claims: List[str], 
                          threshold: float = 0.6) -> List[str]:
        """
        Filter claims to only checkworthy ones.
        
        Args:
            claims: List of claims
            threshold: Minimum confidence for checkworthy classification
        
        Returns:
            List of checkworthy claims
        """
        results = self.classify_batch(claims)
        return [
            r['claim'] for r in results
            if r['label'] == 'checkworthy' and r['confidence'] >= threshold
        ]
