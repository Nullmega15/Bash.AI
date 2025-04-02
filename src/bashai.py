import os
import anthropic
import readline  # For Linux/Mac, use pyreadline3 for Windows
from typing import Optional

class BashAI:
    def __init__(self):
        self.config = self._load_config()
        self.client = anthropic.Anthropic(api_key=self.config['api_key'])
        self.history = []
    
    def _load_config(self):
        """Load configuration from file"""
        config_path = os.path.expanduser("~/.bashai_config.json")
        if not os.path.exists(config_path):
            print("Welcome to Bash.ai! Let's configure your API key.")
            api_key = input("Enter your Anthropic API key: ").strip()
            with open(config_path, 'w') as f:
                f.write(f'{{"api_key": "{api_key}"}}')
            return {"api_key": api_key}
        
        with open(config_path) as f:
            return {"api_key": f.read().strip()}

    def start_interactive(self):
        """Start the interactive shell"""
        print("\n=== Bash.ai Interactive Mode ===")
        print("Type 'exit' or 'quit' to end the session\n")
        
        while True:
            try:
                user_input = input("bash.ai> ").strip()
                if user_input.lower() in ['exit', 'quit']:
                    break
                
                # Get response from AI
                response = self.client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=1024,
                    messages=[{"role": "user", "content": user_input}]
                )
                
                print(f"\n{response.content[0].text}\n")
                
            except KeyboardInterrupt:
                print("\nUse 'exit' or 'quit' to end the session")
            except Exception as e:
                print(f"Error: {str(e)}")

def main():
    print("Bash.ai v1.0 - AI Command Line Assistant")
    ai = BashAI()
    ai.start_interactive()  # This launches the interactive mode

if __name__ == "__main__":
    main()
