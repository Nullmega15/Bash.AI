import json
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "bashai.json"

DEFAULT_CONFIG = {
    "api_key": "",
    "max_history": 100,
    "safe_mode": True
}

def load_config() -> dict:
    """Load or create config file"""
    try:
        with open(CONFIG_PATH) as f:
            return {**DEFAULT_CONFIG, **json.load(f)}
    except FileNotFoundError:
        return DEFAULT_CONFIG
