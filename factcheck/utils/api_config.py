import os

# Define all keys for the API configuration
keys = [
    "SERPER_API_KEY",
    "GROQ_API_KEY",
    "GCS_BUCKET_NAME",
    "GCS_BASE_URL",
    "GOOGLE_APPLICATION_CREDENTIALS",
]


def load_api_config(api_config: dict = None):
    """Load API keys from environment variables or config file, config file take precedence

    Args:
        api_config (dict, optional): _description_. Defaults to None.
    """
    if api_config is None:
        api_config = dict()
    assert type(api_config) is dict, "api_config must be a dictionary."

    merged_config = {}

    for key in keys:
        value = api_config.get(key, None)
        # Treat empty strings as missing so env vars take precedence
        if not value or (isinstance(value, str) and not value.strip()):
            value = os.environ.get(key, None)
        merged_config[key] = value

    for key in api_config.keys():
        if key not in keys:
            merged_config[key] = api_config[key]
    return merged_config
