import re
import time
from groq import Groq
from .base import BaseClient

# Fallback model rotation list — only currently supported Groq production models
FALLBACK_MODELS = [
    "llama-3.3-70b-versatile",   # Primary - best quality
    "llama-3.1-8b-instant",      # Fallback - fast & lightweight
    "gemma2-9b-it",              # Backup - alternative architecture
]

# Track exhausted models globally so all GroqClient instances share the state
_exhausted_models = set()


def reset_exhausted_models():
    """Reset the exhausted models set (e.g., after daily quota resets)."""
    global _exhausted_models
    _exhausted_models.clear()
    print("🔄 Model rotation: All models reset to available.")


def get_available_model(preferred_model: str) -> str:
    """Get the best available model, skipping exhausted ones."""
    # If the preferred model is available, use it
    if preferred_model not in _exhausted_models:
        return preferred_model

    # Otherwise, find the next available model from the fallback list
    for model in FALLBACK_MODELS:
        if model not in _exhausted_models:
            return model

    # All models exhausted — reset and try the first one
    print("⚠️  All models exhausted! Resetting model rotation...")
    reset_exhausted_models()
    return FALLBACK_MODELS[0]


class GroqClient(BaseClient):
    def __init__(
        self,
        model: str = "llama-3.3-70b-versatile",
        api_config: dict = None,
        max_requests_per_minute=60,
        request_window=60,
    ):
        super().__init__(model, api_config, max_requests_per_minute, request_window)
        self.client = Groq(api_key=self.api_config["GROQ_API_KEY"])
        self.original_model = model  # Remember the original model for logging

    def _call(self, messages: str, **kwargs):
        seed = kwargs.get("seed", 42)
        assert type(seed) is int, "Seed must be an integer."

        # Use the best available model (may differ from self.model if quota hit)
        active_model = get_available_model(self.model)
        if active_model != self.model:
            print(f"🔄 Model rotation: {self.model} → {active_model}")

        # Normalise messages into the format Groq expects
        if isinstance(messages, list):
            groq_messages = []
            for message in messages:
                role = message.get("role", "user")
                content = message.get("content", "")
                groq_messages.append({"role": role, "content": content})
        else:
            groq_messages = [{"role": "user", "content": str(messages)}]

        try:
            response = self.client.chat.completions.create(
                model=active_model,
                messages=groq_messages,
                temperature=0.1,   # Low temperature for consistent fact-checking
                seed=seed,
            )

            result = response.choices[0].message.content

            # Clean up markdown code blocks if present (same as original)
            result = self._clean_json_response(result)

            # Log token usage
            if hasattr(response, "usage") and response.usage:
                self._log_usage(response.usage)

            return result

        except Exception as e:
            error_str = str(e)

            # Model decommissioned — mark it and rotate immediately
            if "decommissioned" in error_str.lower() or "model_decommissioned" in error_str:
                _exhausted_models.add(active_model)
                print(f"🚫 Model {active_model} is decommissioned. Removing from rotation.")
                next_model = get_available_model(self.model)
                if next_model != active_model:
                    print(f"🔄 Auto-rotating to: {next_model}")
                    return self._call(messages, **kwargs)
                else:
                    raise ValueError(
                        f"All models unavailable. Decommissioned: {_exhausted_models}"
                    ) from e

            # Daily / hard quota exhausted — mark model and rotate
            if ("daily" in error_str.lower() or "quota" in error_str.lower() or 
                "tokens per day" in error_str.lower() or "TPD" in error_str):
                
                _exhausted_models.add(active_model)
                print(f"🚫 Model {active_model} quota exhausted. Marked as unavailable.")
                print(f"   Exhausted models: {_exhausted_models}")

                # Try the next available model
                next_model = get_available_model(self.model)
                if next_model != active_model:
                    print(f"🔄 Auto-rotating to: {next_model}")
                    return self._call(messages, **kwargs)
                else:
                    raise ValueError(
                        f"All Groq models exhausted their daily quota. "
                        f"Exhausted: {_exhausted_models}. "
                        "Please wait until quotas reset or upgrade your plan."
                    ) from e

            # Handle per-minute rate-limit errors with backoff (max 3 retries)
            if "429" in error_str or "rate_limit" in error_str.lower():
                retry_count = kwargs.get("_retry_count", 0)
                if retry_count >= 3:
                    # After 3 retries on rate limit, try rotating model instead
                    _exhausted_models.add(active_model)
                    print(f"⏳ Model {active_model} rate-limited 3 times. Rotating...")
                    next_model = get_available_model(self.model)
                    if next_model != active_model:
                        print(f"🔄 Auto-rotating to: {next_model}")
                        return self._call(messages, **{k: v for k, v in kwargs.items() if k != '_retry_count'})
                    else:
                        raise ValueError(
                            f"Rate limit exceeded on all models. "
                            "Try again later or upgrade your Groq plan."
                        ) from e

                print(f"Groq API Rate Limit on model {active_model} (retry {retry_count + 1}/3)")

                match = re.search(r"Please try again in ([\d.]+)s", error_str)
                sleep_time = min(float(match.group(1)) + 1.0, 30.0) if match else 10.0
                print(f"Sleeping for {sleep_time:.1f}s before retrying...")
                time.sleep(sleep_time)
                return self._call(messages, _retry_count=retry_count + 1, **{k: v for k, v in kwargs.items() if k != '_retry_count'})

            print(f"Groq API Error: {e}")
            raise e

    def _clean_json_response(self, response_text: str) -> str:
        """Remove markdown code fences from the response (identical to original)."""
        cleaned = re.sub(r"```(?:json)?\s*([\s\S]*?)\s*```", r"\1", response_text.strip())
        return cleaned.strip()

    def _log_usage(self, usage):
        try:
            if hasattr(usage, "prompt_tokens"):
                self.usage.prompt_tokens += usage.prompt_tokens
            if hasattr(usage, "completion_tokens"):
                self.usage.completion_tokens += usage.completion_tokens
        except Exception as e:
            print(f"Warning: Could not log Groq usage: {e}")

    def get_request_length(self, messages):
        return 1

    def construct_message_list(
        self,
        prompt_list: list[str],
        system_role: str = "Output JSON only.",
    ):
        messages_list = []
        for prompt in prompt_list:
            messages = [
                {"role": "system", "content": system_role},
                {"role": "user", "content": prompt},
            ]
            messages_list.append(messages)
        return messages_list
