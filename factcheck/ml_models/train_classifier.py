"""Training script for claim classifier using expanded dataset"""

import torch
from torch.utils.data import Dataset, DataLoader
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import json
import os
from tqdm import tqdm
import numpy as np

# Import expanded training data
from training_data import TRAINING_DATA

# Use torch.optim.AdamW instead of transformers.AdamW
from torch.optim import AdamW


class ClaimDataset(Dataset):
    """Dataset for claim classification"""
    
    def __init__(self, texts, labels, tokenizer, max_length=128):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, idx):
        text = self.texts[idx]
        label = self.labels[idx]
        
        encoding = self.tokenizer(
            text,
            truncation=True,
            max_length=self.max_length,
            padding='max_length',
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.long)
        }


def train_classifier(output_dir='factcheck/ml_models/trained_model', 
                    epochs=20, batch_size=32, learning_rate=2e-5):
    """
    Train the claim classifier on synthetic data.
    
    Args:
        output_dir: Directory to save the trained model
        epochs: Number of training epochs
        batch_size: Batch size for training
        learning_rate: Learning rate
    """
    print("🚀 Starting claim classifier training...")
    
    # Prepare data
    texts = [item[0] for item in TRAINING_DATA]
    labels_text = [item[1] for item in TRAINING_DATA]
    
    # Create label mapping
    label_map = {
        'checkworthy': 0,
        'opinion': 1,
        'unverifiable': 2
    }
    labels = [label_map[l] for l in labels_text]
    
    # Split data
    train_texts, val_texts, train_labels, val_labels = train_test_split(
        texts, labels, test_size=0.2, random_state=42, stratify=labels
    )
    
    print(f"📊 Training samples: {len(train_texts)}")
    print(f"📊 Validation samples: {len(val_texts)}")
    
    # Initialize tokenizer and model
    tokenizer = DistilBertTokenizer.from_pretrained('distilbert-base-uncased')
    model = DistilBertForSequenceClassification.from_pretrained(
        'distilbert-base-uncased',
        num_labels=len(label_map)
    )
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model.to(device)
    print(f"💻 Using device: {device}")
    
    if torch.cuda.is_available():
        print(f"🚀 GPU: {torch.cuda.get_device_name(0)}")
        print(f"💾 GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
    
    # Create datasets
    train_dataset = ClaimDataset(train_texts, train_labels, tokenizer)
    val_dataset = ClaimDataset(val_texts, val_labels, tokenizer)
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size)
    
    # Optimizer
    optimizer = AdamW(model.parameters(), lr=learning_rate)
    
    # Training loop
    best_val_acc = 0
    for epoch in range(epochs):
        # Training
        model.train()
        train_loss = 0
        train_correct = 0
        train_total = 0
        
        for batch in tqdm(train_loader, desc=f"Epoch {epoch+1}/{epochs}"):
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels = batch['labels'].to(device)
            
            optimizer.zero_grad()
            
            outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
            loss = outputs.loss
            
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
            
            # Calculate accuracy
            predictions = torch.argmax(outputs.logits, dim=1)
            train_correct += (predictions == labels).sum().item()
            train_total += labels.size(0)
        
        train_acc = train_correct / train_total
        avg_train_loss = train_loss / len(train_loader)
        
        # Validation
        model.eval()
        val_correct = 0
        val_total = 0
        
        with torch.no_grad():
            for batch in val_loader:
                input_ids = batch['input_ids'].to(device)
                attention_mask = batch['attention_mask'].to(device)
                labels = batch['labels'].to(device)
                
                outputs = model(input_ids=input_ids, attention_mask=attention_mask)
                predictions = torch.argmax(outputs.logits, dim=1)
                
                val_correct += (predictions == labels).sum().item()
                val_total += labels.size(0)
        
        val_acc = val_correct / val_total
        
        print(f"Epoch {epoch+1}: Train Loss={avg_train_loss:.4f}, Train Acc={train_acc:.4f}, Val Acc={val_acc:.4f}")
        
        # Save best model
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            os.makedirs(output_dir, exist_ok=True)
            model.save_pretrained(output_dir)
            tokenizer.save_pretrained(output_dir)
            
            # Save label mapping
            with open(os.path.join(output_dir, 'label_map.json'), 'w') as f:
                json.dump({v: k for k, v in label_map.items()}, f)
            
            print(f"✅ Saved best model (val_acc={val_acc:.4f})")
    
    print(f"\n🎉 Training complete! Best validation accuracy: {best_val_acc:.4f}")
    print(f"📁 Model saved to: {output_dir}")
    
    # Final evaluation with detailed metrics
    print("\n" + "="*60)
    print("📊 Final Evaluation on Validation Set")
    print("="*60)
    
    model.eval()
    all_preds = []
    all_labels = []
    
    with torch.no_grad():
        for batch in val_loader:
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels = batch['labels'].to(device)
            
            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            predictions = torch.argmax(outputs.logits, dim=1)
            
            all_preds.extend(predictions.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
    
    # Classification report
    label_names = ['checkworthy', 'opinion', 'unverifiable']
    print("\nClassification Report:")
    print(classification_report(all_labels, all_preds, target_names=label_names))
    
    # Confusion matrix
    print("\nConfusion Matrix:")
    cm = confusion_matrix(all_labels, all_preds)
    print(f"{'':15} {'Predicted':^45}")
    print(f"{'':15} {'checkworthy':^15} {'opinion':^15} {'unverifiable':^15}")
    print(f"{'Actual':15}")
    for i, label in enumerate(label_names):
        print(f"{label:15} {cm[i][0]:^15} {cm[i][1]:^15} {cm[i][2]:^15}")
    
    print("\n" + "="*60)
    
    return model, tokenizer


if __name__ == '__main__':
    train_classifier()
