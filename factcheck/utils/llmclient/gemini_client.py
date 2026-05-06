import time
import google.generativeai as genai
from .base import BaseClient


class GeminiClient(BaseClient):
    def __init__(
        self,
        model: str = "gemini-3-pro-preview",
        api_config: dict = None,
        max_requests_per_minute=15,  # Gemini has lower rate limits
        request_window=60,
    ):
        super().__init__(model, api_config, max_requests_per_minute, request_window)
        genai.configure(api_key=self.api_config["GEMINI_API_KEY"])
        # Handle 'models/' prefix internally if provided
        safe_model_name = self.model.replace("models/", "")
        self.client = genai.GenerativeModel(model_name=safe_model_name)

    def _call(self, messages: str, **kwargs):
        seed = kwargs.get("seed", 42)  # default seed is 42
        assert type(seed) is int, "Seed must be an integer."

        # Extract the user message content from the messages list
        if isinstance(messages, list):
            # Find the user message
            user_content = ""
            for message in messages:
                if message.get("role") == "user":
                    user_content = message.get("content", "")
                    break
        else:
            user_content = str(messages)

        # Configure generation parameters
        generation_config = genai.types.GenerationConfig(
            temperature=0.1,  # Low temperature for consistent fact-checking
            candidate_count=1,
        )

        try:
            response = self.client.generate_content(
                user_content,
                generation_config=generation_config
            )
            
            # Extract text from response
            if hasattr(response, 'text'):
                result = response.text
            elif hasattr(response, 'candidates') and response.candidates:
                result = response.candidates[0].content.parts[0].text
            else:
                raise ValueError("No valid response from Gemini API")
            
            # Clean up markdown code blocks if present
            result = self._clean_json_response(result)
                
            # Log usage if available
            if hasattr(response, 'usage_metadata'):
                self._log_usage(response.usage_metadata)
            
            return result
            
        except Exception as e:
            if "429" in str(e) or "ResourceExhausted" in type(e).__name__:
                import re
                print(f"Gemini API Rate Limit Exceeded on model {self.model}: {e}")
                
                # If it's a daily quota exhaustion, DO NOT retry, raise immediately
                if "GenerateRequestsPerDayPerProjectPerModel" in str(e) or "limit: 0" in str(e) or "limit: 20" in str(e):
                    print("Daily quota exhausted for this model. Failing request to avoid infinite loop.")
                    raise ValueError(f"Daily API quota exhausted for model {self.model}. Please use a different model or wait until tomorrow.") from e

                # Otherwise, it's a Minute Quota, handle with backoff
                match = re.search(r"Please retry in (\d+\.?\d*)s", str(e))
                if match:
                    sleep_time = float(match.group(1)) + 1.0 # Add 1s buffer
                else:
                    sleep_time = 60.0 # Default fallback
                print(f"Sleeping for {sleep_time} seconds before retrying...")
                time.sleep(sleep_time)
                # Retry once after sleeping
                return self._call(messages, **kwargs)
            else:
                print(f"Gemini API Error: {e}")
                raise e

    def _clean_json_response(self, response_text):
        """Clean up Gemini response by removing markdown code blocks"""
        import re
        
        # Remove markdown code blocks
        # Pattern matches ```json ... ``` or ``` ... ```
        cleaned = re.sub(r'```(?:json)?\s*([\s\S]*?)\s*```', r'\1', response_text.strip())
        
        # Remove any leading/trailing whitespace
        cleaned = cleaned.strip()
        
        return cleaned

    def _log_usage(self, usage_metadata):
        try:
            if hasattr(usage_metadata, 'prompt_token_count'):
                self.usage.prompt_tokens += usage_metadata.prompt_token_count
            if hasattr(usage_metadata, 'candidates_token_count'):
                self.usage.completion_tokens += usage_metadata.candidates_token_count
        except Exception as e:
            print(f"Warning: Could not log Gemini usage: {e}")

    def get_request_length(self, messages):
        return 1

    def construct_message_list(
        self,
        prompt_list: list[str],
        system_role: str = "You are a helpful assistant designed to output JSON.",
    ):
        messages_list = list()
        for prompt in prompt_list:
            # Gemini doesn't use separate system/user roles in the same way
            # Include system instruction as part of the prompt
            full_prompt = f"{system_role}\n\n{prompt}"
            messages = [
                {"role": "user", "content": full_prompt},
            ]
            messages_list.append(messages)
        return messages_list