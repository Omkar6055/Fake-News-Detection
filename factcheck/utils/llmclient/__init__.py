from .groq_client import GroqClient

# fmt: off
CLIENTS = {
    "groq": GroqClient,
}
# fmt: on


def model2client(model_name: str):
    """Map a model name to the corresponding LLM client class."""
    # All supported Groq models
    groq_prefixes = ("llama", "mixtral", "gemma")
    if model_name.startswith(groq_prefixes):
        return GroqClient
    else:
        raise ValueError(f"Model {model_name} not supported. Add it to model2client() in llmclient/__init__.py.")
