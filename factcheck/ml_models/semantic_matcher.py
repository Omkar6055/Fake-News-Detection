"""Semantic Similarity Matching using Sentence-BERT"""

from sentence_transformers import SentenceTransformer, util
import numpy as np
from typing import List, Tuple, Union, Dict


class SemanticMatcher:
    """
    Uses Sentence-BERT to compute semantic similarity between claims and evidence.
    Helps rank evidence by relevance and detect duplicate claims.
    """
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize the semantic matcher.
        
        Args:
            model_name: Name of the sentence-transformers model to use.
                       'all-MiniLM-L6-v2' is fast and accurate (default)
                       'all-mpnet-base-v2' is more accurate but slower
        """
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name
    
    def rank_evidence(self, claim: str, evidences: List[Union[str, Dict]], 
                     top_k: int = None) -> List[Tuple[Union[str, Dict], float]]:
        """
        Rank evidences by semantic similarity to the claim.
        
        Args:
            claim: The claim text to match against
            evidences: List of evidence texts or dicts with 'text' key
            top_k: Return only top K results (None = all)
        
        Returns:
            List of (evidence, score) tuples, sorted by score (highest first)
        """
        if not evidences:
            return []
        
        # Extract text from evidence objects
        evidence_texts = []
        for e in evidences:
            if isinstance(e, dict):
                evidence_texts.append(e.get('text', str(e)))
            else:
                evidence_texts.append(str(e))
        
        # Compute embeddings
        claim_emb = self.model.encode(claim, convert_to_tensor=True)
        evidence_embs = self.model.encode(evidence_texts, convert_to_tensor=True)
        
        # Compute cosine similarity
        scores = util.cos_sim(claim_emb, evidence_embs)[0]
        
        # Sort by score (descending)
        ranked_indices = scores.argsort(descending=True)
        
        # Return top K or all
        if top_k:
            ranked_indices = ranked_indices[:top_k]
        
        return [(evidences[i], float(scores[i])) for i in ranked_indices]
    
    def find_similar_claims(self, claim: str, claim_list: List[str], 
                           threshold: float = 0.8) -> List[Tuple[str, float]]:
        """
        Find similar claims in a list (useful for deduplication).
        
        Args:
            claim: The claim to match
            claim_list: List of claims to search
            threshold: Minimum similarity score (0-1)
        
        Returns:
            List of (similar_claim, score) tuples above threshold
        """
        if not claim_list:
            return []
        
        claim_emb = self.model.encode(claim, convert_to_tensor=True)
        list_embs = self.model.encode(claim_list, convert_to_tensor=True)
        
        scores = util.cos_sim(claim_emb, list_embs)[0]
        
        similar = []
        for i, score in enumerate(scores):
            if float(score) >= threshold and claim_list[i] != claim:
                similar.append((claim_list[i], float(score)))
        
        return sorted(similar, key=lambda x: x[1], reverse=True)
    
    def compute_similarity(self, text1: str, text2: str) -> float:
        """
        Compute similarity between two texts.
        
        Args:
            text1: First text
            text2: Second text
        
        Returns:
            Similarity score (0-1)
        """
        emb1 = self.model.encode(text1, convert_to_tensor=True)
        emb2 = self.model.encode(text2, convert_to_tensor=True)
        
        score = util.cos_sim(emb1, emb2)[0][0]
        return float(score)
