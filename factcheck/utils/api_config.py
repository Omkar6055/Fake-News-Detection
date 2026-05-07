import os
import yaml

# Define all keys for the API configuration
keys = [
    "SERPER_API_KEY",
    "GROQ_API_KEY",
    "GCS_BUCKET_NAME",
    "GCS_BASE_URL",
    "GOOGLE_APPLICATION_CREDENTIALS",
]

def load_api_config(api_config: dict = None):
    if api_config is None:
        api_config = dict()
    assert type(api_config) is dict, "api_config must be a dictionary."

    config = {}
    
    # Step 1: Try multiple yaml file locations
    # (works locally, gracefully skipped on Railway)
    yaml_paths = [
        'api_config.yaml',
        'factcheck/config/api_config.yaml',
        os.path.join(
            os.path.dirname(__file__), 
            '../../api_config.yaml'
        ),
        os.path.join(
            os.path.dirname(__file__), 
            '../../../api_config.yaml'
        )
    ]
    
    for yaml_path in yaml_paths:
        try:
            if os.path.exists(yaml_path):
                with open(yaml_path, 'r') as f:
                    file_config = yaml.safe_load(f)
                    if file_config:
                        config.update(file_config)
                print(f"Loaded config from: {yaml_path}")
                break
        except Exception as e:
            print(f"Could not load {yaml_path}: {e}")
            continue
            
    # Merge passed-in config
    config.update(api_config)
    
    # Step 2: ALWAYS check environment variables
    # These are set in Railway dashboard
    # Environment variables OVERRIDE yaml values
    env_keys = [
        'GROQ_API_KEY',
        'SERPER_API_KEY',
        'GEMINI_API_KEY',
        'GOOGLE_APPLICATION_CREDENTIALS',
        'GCS_BUCKET_NAME',
        'GCS_BASE_URL'
    ]
    
    for key in env_keys:
        env_value = os.environ.get(key)
        if env_value and env_value.strip():
            config[key] = env_value
            
    # Keep any extra keys from api_config
    for key in api_config.keys():
        if key not in config:
            config[key] = api_config[key]
    
    # Step 3: Log what we found (helps debug)
    groq_found = bool(config.get('GROQ_API_KEY'))
    serper_found = bool(config.get('SERPER_API_KEY'))
    print(f"Config loaded - GROQ: {groq_found}, "
          f"SERPER: {serper_found}")
    
    return config
