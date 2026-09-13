from ruamel.yaml import YAML
from typing import Any
import os, sys
import threading

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CONFIG_PATH = 'config.yaml'
config_lock = threading.Lock()

yaml = YAML()
yaml.preserve_quotes = True

def deep_merge(target: dict, source: dict):
    """Recursively merge source dict into target dict in-place."""
    for k, v in source.items():
        if k in target and isinstance(target[k], dict) and isinstance(v, dict):
            deep_merge(target[k], v)
        else:
            target[k] = v

def load_key(key: str) -> Any:
    with config_lock:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as file:
            data = yaml.load(file) or {}
            
        secret_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.secret')
        if os.path.exists(secret_path):
            try:
                with open(secret_path, 'r', encoding='utf-8') as f:
                    secret_data = yaml.load(f)
                    if secret_data and isinstance(secret_data, dict):
                        deep_merge(data, secret_data)
            except Exception as e:
                print(f"Notice loading secret file: {e}")

    keys = key.split('.')
    value = data
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            raise KeyError(f"Key '{k}' not found in configuration")
    return value

SENSITIVE_KEYS = {
    'api.key',
    'sf_fish_tts.api_key',
    'openai_tts.api_key',
    'fish_tts.api_key',
    'azure_tts.api_key',
}

def is_sensitive_key(key: str) -> bool:
    """Check if a config key is sensitive and should be kept in .secret only."""
    return key in SENSITIVE_KEYS or key.endswith('.key') or key.endswith('.api_key') or 'token' in key.lower()

def update_key(key: str, new_value: Any) -> bool:
    with config_lock:
        keys = key.split('.')
        secret_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.secret')
        
        # 1. Sensitive Keys: ALWAYS write to .secret, NEVER to config.yaml
        if is_sensitive_key(key):
            secret_data = {}
            if os.path.exists(secret_path):
                try:
                    with open(secret_path, 'r', encoding='utf-8') as file:
                        secret_data = yaml.load(file) or {}
                except Exception:
                    secret_data = {}
            
            # Deep set in secret_data
            current_secret = secret_data
            for k in keys[:-1]:
                if k not in current_secret or not isinstance(current_secret[k], dict):
                    current_secret[k] = {}
                current_secret = current_secret[k]
            current_secret[keys[-1]] = new_value

            with open(secret_path, 'w', encoding='utf-8') as file:
                yaml.dump(secret_data, file)

            # Ensure config.yaml only has a placeholder for this sensitive key
            try:
                with open(CONFIG_PATH, 'r', encoding='utf-8') as file:
                    config_data = yaml.load(file) or {}
                current_c = config_data
                for k in keys[:-1]:
                    if isinstance(current_c, dict) and k in current_c:
                        current_c = current_c[k]
                    else:
                        break
                else:
                    if isinstance(current_c, dict) and keys[-1] in current_c:
                        current_c[keys[-1]] = 'not here'
                        with open(CONFIG_PATH, 'w', encoding='utf-8') as file:
                            yaml.dump(config_data, file)
            except Exception as e:
                print(f"Notice cleaning config placeholder: {e}")
            return True

        # 2. Non-sensitive Keys: update config.yaml
        with open(CONFIG_PATH, 'r', encoding='utf-8') as file:
            data = yaml.load(file) or {}

        current = data
        for k in keys[:-1]:
            if k not in current or not isinstance(current[k], dict):
                current[k] = {}
            current = current[k]

        current[keys[-1]] = new_value
        with open(CONFIG_PATH, 'w', encoding='utf-8') as file:
            yaml.dump(data, file)
        return True
