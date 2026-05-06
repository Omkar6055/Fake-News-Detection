from factcheck.utils.logger import CustomLogger
from factcheck.utils.utils import extract_json_and_parse
import json
import re
import os

logger = CustomLogger(__name__).getlog()


class Checkworthy:
    def __init__(self, llm_client, prompt):
        """Initialize the Checkworthy class

        Args:
            llm_client (BaseClient): The LLM client used for identifying checkworthiness of claims.
            prompt (BasePrompt): The prompt used for identifying checkworthiness of claims.
        """
        self.llm_client = llm_client
        self.prompt = prompt
        
        # Initialize ML classifier if available
        self.ml_classifier = None
        self.use_ml = False
        try:
            from factcheck.ml_models import ClaimClassifier
            model_path = os.path.join(os.path.dirname(__file__), '..', 'ml_models', 'trained_model')
            if os.path.exists(model_path):
                self.ml_classifier = ClaimClassifier(model_path)
                self.use_ml = True
                logger.info("✅ ML Claim Classifier loaded successfully")
                logger.info("🚀 ML-enhanced checkworthy detection enabled (API fallback available)")
            else:
                logger.warning("⚠️  ML model not found, using LLM-only mode")
        except Exception as e:
            logger.warning(f"⚠️  Could not load ML classifier: {e}")
            logger.info("📡 Using LLM-only mode for checkworthy detection")

    def identify_checkworthiness(self, texts: list[str], num_retries: int = 3, prompt: str = None, 
                                 use_ml: bool = True, ml_confidence_threshold: float = 0.7) -> tuple:
        """Identify whether candidate claims are worth fact checking using ML (with LLM fallback).
        """
        # Try ML Classifier first (FASTEST)
        if self.use_ml and use_ml and self.ml_classifier is not None:
            logger.info(f"🤖 Using ML classifier for {len(texts)} claims (Primary Method)...")
            try:
                # Classify all claims with ML
                results = self.ml_classifier.classify_batch(texts)
                
                checkworthy_claims = []
                claim2checkworthy = {}
                
                for result in results:
                    claim = result['claim']
                    label = result['label']
                    confidence = result['confidence']
                    
                    if label == 'checkworthy':
                        checkworthy_claims.append(claim)
                        claim2checkworthy[claim] = f"Yes - ML (confidence: {confidence:.1%})"
                    else:
                        claim2checkworthy[claim] = f"No - ML: {label} (confidence: {confidence:.1%})"
                
                logger.info(f"✅ ML identified: {len(checkworthy_claims)}/{len(texts)} claims as checkworthy")
                return checkworthy_claims, claim2checkworthy

            except Exception as ml_error:
                logger.warning(f"⚠️  ML classification failed: {ml_error}. Falling back to LLM.")

        # Fallback to LLM
        return self._llm_checkworthy(texts, num_retries, prompt)
    
    def _llm_checkworthy(self, texts: list[str], num_retries: int = 3, prompt: str = None) -> tuple:
        """Original LLM-based checkworthy detection (used as fallback).

        Args:
            texts (list[str]): a list of texts to identify whether they are worth fact checking
            num_retries (int, optional): maximum attempts for LLM. Defaults to 3.
            prompt (str, optional): custom prompt. Defaults to None.

        Returns:
            tuple: (checkworthy_claims, claim2checkworthy)
        """
        checkworthy_claims = texts

        # ✅ FIX: Set safe default values BEFORE the loop
        # This prevents UnboundLocalError if all retries fail
        claim2checkworthy = {text: "Yes" for text in texts}

        joint_texts = "\n".join([str(i + 1) + ". " + j for i, j in enumerate(texts)])

        if prompt is None:
            user_input = self.prompt.checkworthy_prompt.format(texts=joint_texts)
        else:
            user_input = prompt.format(texts=joint_texts)

        messages = self.llm_client.construct_message_list([user_input])
        for i in range(num_retries):
            response = self.llm_client.call(messages, num_retries=1, seed=42 + i)
            try:
                claim2checkworthy = extract_json_and_parse(response)
                valid_answer = list(
                    filter(
                        lambda x: x[1].startswith("Yes") or x[1].startswith("No"),
                        claim2checkworthy.items(),
                    )
                )
                checkworthy_claims = list(filter(lambda x: x[1].startswith("Yes"), claim2checkworthy.items()))
                checkworthy_claims = list(map(lambda x: x[0], checkworthy_claims))
                assert len(valid_answer) == len(claim2checkworthy)
                logger.info("✅ LLM response parsed successfully")
                break
            except (json.JSONDecodeError, ValueError, AssertionError, KeyError, TypeError) as e:
                logger.error(f"====== Error: {e}, the LLM response is: {response}")
                logger.error(f"====== Our input is: {messages}")

        # Warn if all retries failed and we are using default values
        else:
            logger.warning("⚠️ All LLM retries failed! Treating all claims as checkworthy by default.")

        return checkworthy_claims, claim2checkworthy
