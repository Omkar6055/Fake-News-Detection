from factcheck.utils.logger import CustomLogger
from factcheck.utils.utils import extract_json_and_parse
import json
import re
import nltk

logger = CustomLogger(__name__).getlog()

class Decompose:
    def __init__(self, llm_client, prompt):
        """Initialize the Decompose class

        Args:
            llm_client (BaseClient): The LLM client used for decomposing documents into claims.
            prompt (BasePrompt): The prompt used for fact checking.
        """
        self.llm_client = llm_client
        self.prompt = prompt
        self.doc2sent = self._nltk_doc2sent

    def _nltk_doc2sent(self, text: str):
        """Split the document into sentences using nltk

        Args:
            text (str): the document to be split into sentences

        Returns:
            list: a list of sentences
        """

        sentences = nltk.sent_tokenize(text)
        sentence_list = [s.strip() for s in sentences if len(s.strip()) >= 3]
        return sentence_list

    def getclaims(self, doc: str, num_retries: int = 3, prompt: str = None) -> list[str]:
        """Use GPT to decompose a document into claims

        Args:
            doc (str): the document to be decomposed into claims
            num_retries (int, optional): maximum attempts for GPT to decompose the document into claims. Defaults to 3.

        Returns:
            list: a list of claims
        """
        if prompt is None:
            user_input = self.prompt.decompose_prompt.format(doc=doc).strip()
        else:
            user_input = prompt.format(doc=doc).strip()

        claims = None
        messages = self.llm_client.construct_message_list([user_input])
        for i in range(num_retries):
            response = self.llm_client.call(
                messages=messages,
                num_retries=1,
                seed=42 + i,
            )
            try:
                parsed_response = extract_json_and_parse(response)
                claims = parsed_response.get("claims", [])
                if isinstance(claims, list) and len(claims) > 0:
                    break
            except Exception as e:
                logger.error(f"Parse LLM response error {e}, response is: {response}")
                logger.error(f"Parse LLM response error, prompt is: {messages}")
        if isinstance(claims, list):
            return claims
        else:
            logger.info("It does not output a list of sentences correctly, return self.doc2sent_tool split results.")
            claims = self.doc2sent(doc)
        return claims

    def restore_claims(self, doc: str, claims: list, num_retries: int = 3, prompt: str = None) -> dict[str, dict]:
        """Use GPT to map claims back to the document

        Args:
            doc (str): the document to be decomposed into claims
            claims (list[str]): a list of claims to be mapped back to the document
            num_retries (int, optional): maximum attempts for GPT to decompose the document into claims. Defaults to 3.

        Returns:
            dict: a dictionary of claims and their corresponding text spans and start/end indices.
        """

        def restore(claim2doc):
            claim2doc_detail = {}
            flag = True
            for claim, sent in claim2doc.items():
                # Handle empty or None text spans
                if not sent or sent.strip() == "":
                    # Try to find a reasonable text span for the claim
                    # Look for key words from the claim in the document
                    claim_words = claim.lower().split()
                    best_match = ""
                    best_score = 0
                    
                    # Simple keyword matching to find relevant text
                    for i in range(len(doc) - 10):
                        text_chunk = doc[i:i+50].lower()
                        score = sum(1 for word in claim_words if word in text_chunk)
                        if score > best_score:
                            best_score = score
                            # Find sentence boundaries
                            start = max(0, doc.rfind('\n', 0, i))
                            end = doc.find('\n', i+50)
                            if end == -1:
                                end = min(len(doc), i+100)
                            best_match = doc[start:end].strip()
                    
                    if best_match:
                        sent = best_match
                        logger.warning(f"Empty text span for claim '{claim}', using fallback: '{sent[:50]}...'")
                    else:
                        # Last resort: use the claim itself as text
                        sent = claim
                        logger.warning(f"No text span found for claim '{claim}', using claim as text")
                        flag = False
                
                st = doc.find(sent)
                if st != -1:
                    claim2doc_detail[claim] = {"text": sent, "start": st, "end": st + len(sent)}
                else:
                    # If exact match fails, try to find the best position
                    # Use the claim text and position it appropriately
                    claim2doc_detail[claim] = {"text": sent, "start": 0, "end": len(sent)}
                    flag = False
                    logger.warning(f"Text span '{sent[:30]}...' not found in document for claim '{claim[:30]}...'")

            cur_pos = -1
            texts = []
            for k, v in claim2doc_detail.items():
                if v["start"] < cur_pos + 1 and v["end"] > cur_pos:
                    v["start"] = cur_pos + 1
                    flag = False
                elif v["start"] < cur_pos + 1 and v["end"] <= cur_pos:
                    v["start"] = v["end"]  # temporarily ignore this span
                    flag = False
                elif v["start"] > cur_pos + 1:
                    v["start"] = cur_pos + 1
                    flag = False
                v["text"] = doc[v["start"] : v["end"]]
                texts.append(v["text"])
                claim2doc_detail[k] = v
                cur_pos = v["end"]

            return claim2doc_detail, flag

        if prompt is None:
            user_input = self.prompt.restore_prompt.format(doc=doc, claims=claims).strip()
        else:
            user_input = prompt.format(doc=doc, claims=claims).strip()

        messages = self.llm_client.construct_message_list([user_input])

        tmp_restore = {}
        for i in range(num_retries):
            response = self.llm_client.call(
                messages=messages,
                num_retries=1,
                seed=42 + i,
            )
            try:
                claim2doc = extract_json_and_parse(response)
                
                assert len(claim2doc) == len(claims)
                claim2doc_detail, flag = restore(claim2doc)
                if flag:
                    return claim2doc_detail
                else:
                    tmp_restore = claim2doc_detail
                    # Instead of raising exception, log warning and continue with partial results
                    logger.warning(f"Restore claims partially satisfied. Using available mappings. Retry {i+1}/{num_retries}")
                    if i == num_retries - 1:  # Last retry
                        logger.info("Using partial claim restoration results due to text span mapping issues")
                        return tmp_restore
                    # Continue to next retry
                    continue
            except Exception as e:
                logger.error(f"Parse LLM response error {e}, response is: {response}")
                logger.error(f"Parse LLM response error, prompt is: {messages}")

        # --- Fallback: build claim2doc directly from string search ---
        # This runs when ALL retries failed (JSON parse errors), leaving tmp_restore as {}.
        # Without this, _merge_claim_details loops over nothing and factuality stays at 0.
        if not tmp_restore:
            logger.warning(
                "All restore_claims retries failed (JSON parse errors). "
                "Building fallback claim2doc by searching claims in document text."
            )
            cur_pos = 0
            for claim in claims:
                # Try to find the exact claim string in the document
                idx = doc.find(claim, cur_pos)
                if idx == -1:
                    # Try without position constraint
                    idx = doc.find(claim)
                if idx != -1:
                    tmp_restore[claim] = {
                        "text": claim,
                        "start": idx,
                        "end": idx + len(claim),
                    }
                    cur_pos = idx + len(claim)
                else:
                    # Last resort: use a sequential slice of the document
                    # (approximate — still better than returning {})
                    slice_start = min(cur_pos, len(doc) - 1)
                    slice_end = min(slice_start + len(claim) + 50, len(doc))
                    tmp_restore[claim] = {
                        "text": doc[slice_start:slice_end],
                        "start": slice_start,
                        "end": slice_end,
                    }
                    cur_pos = slice_end
            logger.info(f"Fallback produced {len(tmp_restore)} claim-to-doc mappings.")

        return tmp_restore
