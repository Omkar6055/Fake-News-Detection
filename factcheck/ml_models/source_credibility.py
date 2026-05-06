"""Source Credibility Scoring for Evidence URLs"""

import re
from urllib.parse import urlparse
from typing import Dict, List
from datetime import datetime


class SourceCredibilityScorer:
    """
    Scores the credibility of evidence sources based on domain reputation,
    security, and other factors.
    """
    
    def __init__(self):
        # High credibility sources (score 0.85-0.95)
        self.trusted_domains = {
            # News agencies
            'reuters.com': 0.95,
            'apnews.com': 0.95,
            'afp.com': 0.95,
            
            # Major newspapers
            'nytimes.com': 0.90,
            'washingtonpost.com': 0.90,
            'wsj.com': 0.90,
            'theguardian.com': 0.90,
            'bbc.com': 0.90,
            'bbc.co.uk': 0.90,
            
            # Academic/Research
            'nature.com': 0.95,
            'science.org': 0.95,
            'sciencedirect.com': 0.90,
            'pubmed.ncbi.nlm.nih.gov': 0.95,
            'arxiv.org': 0.85,
            
            # Government
            'gov': 0.90,  # Any .gov domain
            'cdc.gov': 0.95,
            'who.int': 0.95,
            'nasa.gov': 0.95,
            
            # Fact-checking
            'snopes.com': 0.90,
            'factcheck.org': 0.90,
            'politifact.com': 0.90,
            
            # Reference
            'wikipedia.org': 0.80,
            'britannica.com': 0.85,
        }
        
        # Medium credibility (score 0.60-0.75)
        self.medium_domains = {
            'forbes.com': 0.70,
            'businessinsider.com': 0.70,
            'huffpost.com': 0.65,
            'buzzfeed.com': 0.60,
            'medium.com': 0.60,
        }
        
        # Low credibility patterns
        self.suspicious_patterns = [
            r'\.blogspot\.',
            r'\.wordpress\.com',
            r'fake',
            r'hoax',
            r'satire',
            r'parody',
            r'clickbait',
            r'viral',
            r'shocking',
        ]
        
        # Known unreliable domains
        self.unreliable_domains = {
            'infowars.com': 0.10,
            'naturalnews.com': 0.15,
            'beforeitsnews.com': 0.20,
        }
    
    def score_url(self, url: str) -> Dict:
        """
        Score a URL's credibility.
        
        Args:
            url: The URL to score
        
        Returns:
            Dict with keys: score (0-1), reason, category, factors
        """
        if not url or not isinstance(url, str):
            return self._create_score(0.3, 'Invalid URL', 'low', {})
        
        try:
            parsed = urlparse(url.lower())
            domain = parsed.netloc.replace('www.', '')
            
            factors = {}
            
            # Check unreliable list first
            for unreliable, score in self.unreliable_domains.items():
                if unreliable in domain:
                    return self._create_score(
                        score, 
                        f'Known unreliable source: {unreliable}',
                        'very_low',
                        {'unreliable_match': unreliable}
                    )
            
            # Check trusted domains
            for trusted, score in self.trusted_domains.items():
                if trusted in domain or domain.endswith(f'.{trusted}'):
                    factors['trusted_match'] = trusted
                    return self._create_score(
                        score,
                        f'Trusted source: {trusted}',
                        'high',
                        factors
                    )
            
            # Check medium credibility
            for medium, score in self.medium_domains.items():
                if medium in domain:
                    factors['medium_match'] = medium
                    return self._create_score(
                        score,
                        f'Medium credibility source: {medium}',
                        'medium',
                        factors
                    )
            
            # Check suspicious patterns
            for pattern in self.suspicious_patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    factors['suspicious_pattern'] = pattern
                    return self._create_score(
                        0.30,
                        f'Suspicious pattern detected: {pattern}',
                        'low',
                        factors
                    )
            
            # Calculate score based on various factors
            score = 0.50  # Base score for unknown sources
            
            # HTTPS bonus
            if parsed.scheme == 'https':
                score += 0.10
                factors['https'] = True
            else:
                factors['https'] = False
            
            # .gov or .edu bonus
            if domain.endswith('.gov'):
                score += 0.30
                factors['gov_domain'] = True
            elif domain.endswith('.edu'):
                score += 0.20
                factors['edu_domain'] = True
            
            # Domain length (shorter usually better)
            if len(domain) < 15:
                score += 0.05
                factors['short_domain'] = True
            elif len(domain) > 40:
                score -= 0.05
                factors['long_domain'] = True
            
            # Has path (not just homepage)
            if len(parsed.path) > 1:
                score += 0.05
                factors['has_path'] = True
            
            score = min(max(score, 0.0), 1.0)  # Clamp to 0-1
            
            category = self._score_to_category(score)
            reason = f'Unknown source (score based on URL characteristics)'
            
            return self._create_score(score, reason, category, factors)
            
        except Exception as e:
            return self._create_score(
                0.30,
                f'Error parsing URL: {str(e)}',
                'low',
                {'error': str(e)}
            )
    
    def score_multiple(self, urls: List[str]) -> List[Dict]:
        """Score multiple URLs at once."""
        return [self.score_url(url) for url in urls]
    
    def filter_by_threshold(self, url_scores: List[Dict], 
                           threshold: float = 0.60) -> List[Dict]:
        """Filter URL scores by minimum threshold."""
        return [s for s in url_scores if s['score'] >= threshold]
    
    def _create_score(self, score: float, reason: str, 
                     category: str, factors: Dict) -> Dict:
        """Create a standardized score dictionary."""
        return {
            'score': round(score, 2),
            'reason': reason,
            'category': category,
            'factors': factors,
            'timestamp': datetime.now().isoformat()
        }
    
    def _score_to_category(self, score: float) -> str:
        """Convert numeric score to category."""
        if score >= 0.85:
            return 'very_high'
        elif score >= 0.70:
            return 'high'
        elif score >= 0.50:
            return 'medium'
        elif score >= 0.30:
            return 'low'
        else:
            return 'very_low'
