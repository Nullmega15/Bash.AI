import os
import anthropic
from typing import Optional
import json
from pathlib import Path

CONFIG_PATH = Path.home() / ".bashai_config.json"

class BashAI:
    def __init__(self):
        self.config = self._load_or_create_config()
        self.client = anthropic.Anthropic(api_key=self.config['api_key'])
        self.history = []

    def _load_or_create_config(self) -> dict:
        """Load or create configuration file"""
        default_config = {
            "api_key": "",
            "max_history": 100,
            "safe_mode": True
        }

        try:
            if CONFIG_PATH.exists():
                with open(CONFIG_PATH) as f:
                    return {**default_config, **json.load(f)}
            else:
                print("Welcome to Bash.ai! Let's configure your API key.")
                api_key = input("Enter your Anthropic API key: ").strip()
                config = {**default_config, "api_key": api_key}
                with open(CONFIG_PATH, 'w') as f:
                    json.dump(config, f)
                return config
        except Exception as e:
            print(f"Error loading config: {e}")
            return default_config

def main():
    print("Bash.ai v1.0 - AI Command Line Assistant")
    ai = BashAI()

    # Your main interactive code here
    print("Configuration successful! Ready to use Bash.ai.")

if __name__ == "__main__":
    main()
