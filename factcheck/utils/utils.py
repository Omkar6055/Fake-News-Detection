import yaml
import json
import re
import ast
import logging

logger = logging.getLogger(__name__)


def load_yaml(filepath):
    with open(filepath, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def extract_json_and_parse(text):
    """
    Robust JSON parser that cleans LLM output and falls back to ast.literal_eval.
    """
    if not isinstance(text, str):
        return text

    text = text.strip()
    
    # 1. Replace smart/curly apostrophes and quotes with regular ones
    text = text.replace('‘', "'").replace('’', "'").replace('“', '"').replace('”', '"')
    
    # 2. Extract Markdown code block if present
    match = re.search(r'```(?:json|[a-zA-Z]*)\s*([\s\S]*?)\s*```', text)
    if match:
        text = match.group(1).strip()
    
    # 3. Strip text before { or [ and after } or ]
    start_dict = text.find('{')
    start_list = text.find('[')
    
    if start_dict != -1 and (start_list == -1 or start_dict < start_list):
        end_dict = text.rfind('}')
        if end_dict != -1 and end_dict > start_dict:
            text = text[start_dict:end_dict+1]
    elif start_list != -1:
        end_list = text.rfind(']')
        if end_list != -1 and end_list > start_list:
            text = text[start_list:end_list+1]
            
    # 4. Handle trailing commas which break json.loads
    text = re.sub(r',\s*([}\]])', r'\1', text)
            
    # 5. Try standard json.loads
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning(f"json.loads failed: {e}. Attempting ast.literal_eval fallback.")
        
    # 6. Fallback to ast.literal_eval (handles single quotes inside strings natively!)
    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, (dict, list)):
            return parsed
    except Exception as ast_e:
        logger.error(f"ast.literal_eval failed: {ast_e}. Failed to parse: {text}")
        
    raise ValueError(f"Could not parse response into JSON. Cleaned response: {text}")
