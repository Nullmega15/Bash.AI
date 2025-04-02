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
        self.config = self._load_or_create_config()
        self.client = anthropic.Anthropic(api_key=self.config['api_key'])
        self.current_dir = os.getcwd()
        self.is_windows = os.name == 'nt'

    def _load_or_create_config(self) -> dict:
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

    def _search_web(self, error: str):
        """Search error solutions online"""
        query = f"{error} site:stackoverflow.com OR site:github.com"
        webbrowser.open(f"https://google.com/search?q={query.replace(' ', '+')}")
        print(f"🔍 Searching web for: {error}")

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
                return (result.stdout or "Command executed", True)
                
            except subprocess.CalledProcessError as e:
                if attempt < MAX_RETRIES:
                    print(f"⚠️ Retry {attempt + 1}/{MAX_RETRIES}...")
                    time.sleep(1)
                    continue
                return (f"Error: {e.stderr}", False)

    def generate_code_file(self, request: str) -> str:
        """Generate code files based on requests"""
        response = self.client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": f"""Create complete code for: {request}
                - Include all necessary code
                - Add brief comments
                - Save to appropriate filename
                - Format for {"Windows" if self.is_windows else "Linux"}"""
            }],
            system="""You are a code generator. Respond with:
            <filename>filename.ext</filename>
            <code>
            # Complete code here
            </code>"""
        )
        return response.content[0].text

    def start_interactive(self):
        """Interactive session with code generation"""
        print(f"\n💻 Bash.ai Code Generator (dir: {self.current_dir})")
        print("Request code files naturally like: 'make a Python calculator'\n")
        
        while True:
            try:
                user_input = input("\nbash.ai> ").strip()
                if user_input.lower() in ['exit', 'quit']:
                    break

                # Code generation mode
                if any(word in user_input.lower() for word in ['make', 'create', 'generate']):
                    code_response = self.generate_code_file(user_input)
                    
                    if "<filename>" in code_response:
                        filename = code_response.split("<filename>")[1].split("</filename>")[0].strip()
                        code = code_response.split("<code>")[1].split("</code>")[0].strip()
                        
                        print(f"\n📁 Creating: {filename}")
                        with open(filename, 'w') as f:
                            f.write(code)
                        
                        print(f"✅ Successfully created {filename}")
                        if filename.endswith('.py'):
                            run = input(f"Run {filename}? [y/N] ").lower()
                            if run == 'y':
                                output, success = self.execute_command(f"python {filename}")
                                print(output)
                    else:
                        print(code_response)
                
                # Normal command execution
                else:
                    response = self.client.messages.create(
                        model="claude-3-haiku-20240307",
                        max_tokens=1000,
                        messages=[{
                            "role": "user", 
                            "content": f"Request: {user_input}\nCurrent dir: {self.current_dir}"
                        }],
                        system=f"""Respond with commands in <execute> tags for {"Windows" if self.is_windows else "Linux"}"""
                    )
                    ai_response = response.content[0].text
                    
                    if "<execute>" in ai_response:
                        cmd = ai_response.split("<execute>")[1].split("</execute>")[0].strip()
                        print(f"\n⚙️ Executing: {cmd}")
                        output, success = self.execute_command(cmd)
                        print(output)
                        
                        if not success and input("Search web for solutions? [y/N] ").lower() == 'y':
                            self._search_web(output)
                    else:
                        print(ai_response)

            except KeyboardInterrupt:
                print("\nUse 'exit' to quit")
            except Exception as e:
                print(f"🚨 Error: {str(e)}")

if __name__ == "__main__":
    ai = BashAI()
    ai.start_interactive()
