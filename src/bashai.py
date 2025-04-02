import os
import subprocess
import json
import webbrowser
import anthropic
from pathlib import Path
from typing import Tuple
import time

CONFIG_PATH = Path.home() / ".bashai_config.json"
MAX_RETRIES = 3

class BashAI:
    def __init__(self):
        self.config = self.load_or_create_config()  # Fixed method name
        self.client = anthropic.Anthropic(api_key=self.config['api_key'])
        self.current_dir = os.getcwd()
        self.is_windows = os.name == 'nt'

    def load_or_create_config(self) -> dict:  # Renamed method
        """Load or create configuration file"""
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH) as f:
                return json.load(f)
        
        print("┌──────────────────────────────────────────────┐")
        print("│          Bash.ai First-Time Setup            │")
        print("└──────────────────────────────────────────────┘")
        api_key = input("Enter your Anthropic API key: ").strip()
        config = {"api_key": api_key}
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f)
        return config

    def execute_command(self, cmd: str) -> Tuple[str, bool]:
        """Execute command with auto-retry"""
        for attempt in range(MAX_RETRIES + 1):
            try:
                if self.is_windows:
                    cmd = f'cmd /c "{cmd}"' if ' ' in cmd else f'cmd /c {cmd}'
                
                result = subprocess.run(
                    cmd,
                    shell=True,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                return (result.stdout or "Command executed successfully", True)
                
            except subprocess.CalledProcessError as e:
                if attempt < MAX_RETRIES:
                    print(f"⚠️ Attempt {attempt + 1} failed. Retrying...")
                    time.sleep(1)
                    continue
                return (f"Error: {e.stderr}", False)
            except Exception as e:
                return (f"System Error: {str(e)}", False)

    def web_search(self, error: str):
        """Search the web for solutions"""
        query = f"{error} site:stackoverflow.com OR site:github.com"
        webbrowser.open(f"https://google.com/search?q={query.replace(' ', '+')}")
        print(f"🔍 Searching for solutions to: {error}")

    def start_interactive(self):
        """Start interactive session"""
        print(f"\n💻 Bash.ai [Auto-Retry Mode] (dir: {self.current_dir})")
        print("Type requests naturally. I'll execute and retry automatically.\n")
        
        while True:
            try:
                user_input = input("bash.ai> ").strip()
                if user_input.lower() in ['exit', 'quit']:
                    break

                # Get AI response
                response = self.client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=1000,
                    messages=[{
                        "role": "user", 
                        "content": f"Current dir: {self.current_dir}\nRequest: {user_input}"
                    }],
                    system=f"""You are Bash.ai. Respond with commands in <execute> tags for {"Windows" if self.is_windows else "Linux"}"""
                )

                ai_response = response.content[0].text
                
                # Execute if command found
                if "<execute>" in ai_response:
                    cmd = ai_response.split("<execute>")[1].split("</execute>")[0].strip()
                    print(f"\n⚙️ Executing: {cmd}")
                    output, success = self.execute_command(cmd)
                    print(output)
                    
                    if not success:
                        if input("Search web for solutions? [y/N] ").lower() == 'y':
                            self.web_search(output)
                else:
                    print(ai_response)

            except KeyboardInterrupt:
                print("\nUse 'exit' to quit")
            except Exception as e:
                print(f"🚨 Error: {str(e)}")

if __name__ == "__main__":
    ai = BashAI()
    ai.start_interactive()
