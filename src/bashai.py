import os
import json
import anthropic
from pathlib import Path
from typing import Optional

CONFIG_PATH = Path.home() / ".bashai_config.json"

class BashAI:
    def __init__(self):
        self.config = self._load_or_create_config()
        self.client = anthropic.Anthropic(api_key=self.config['api_key'])
        self.history = []

    def _load_or_create_config(self) -> dict:
        """Load or create configuration file with API key"""
        default_config = {
            "api_key": "",
            "max_history": 10
        }

        try:
            if CONFIG_PATH.exists():
                with open(CONFIG_PATH) as f:
                    loaded_config = json.load(f)
                    if not loaded_config.get("api_key"):
                        raise ValueError("API key missing in config")
                    return {**default_config, **loaded_config}
            
            print("┌──────────────────────────────────────────────┐")
            print("│          Bash.ai First-Time Setup            │")
            print("└──────────────────────────────────────────────┘")
            print("Please enter your Anthropic API key.")
            print("Get it from: https://console.anthropic.com/settings/keys")
            print()
            
            while True:
                api_key = input("Your API key: ").strip()
                if api_key.startswith("sk-") and len(api_key) > 30:
                    break
                print("Invalid key format. Should start with 'sk-' and be >30 chars")
            
            config = {**default_config, "api_key": api_key}
            with open(CONFIG_PATH, 'w') as f:
                json.dump(config, f)
            
            print("\nConfiguration saved! Starting Bash.ai...\n")
            return config

        except Exception as e:
            print(f"Error loading config: {e}")
            return default_config

    def start_interactive(self):
        """Start the interactive session"""
        print("┌──────────────────────────────────────────────┐")
        print("│       Bash.ai Interactive Mode (v1.0)        │")
        print("│   Type 'exit' or 'quit' to end session      │")
        print("└──────────────────────────────────────────────┘")
        
        while True:
            try:
                user_input = input("\nbash.ai> ").strip()
                if user_input.lower() in ['exit', 'quit']:
                    break
                if not user_input:
                    continue
                
                # Get AI response
                response = self.client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=1000,
                    messages=[{"role": "user", "content": user_input}],
                    system="You are Bash.ai, a helpful command line assistant."
                )
                
                print(f"\n{response.content[0].text}")
                
            except KeyboardInterrupt:
                print("\nUse 'exit' or 'quit' to end session")
            except Exception as e:
                print(f"\nError: {str(e)}")

def main():
    print("Starting Bash.ai...")
    ai = BashAI()
    ai.start_interactive()

if __name__ == "__main__":
    main()
