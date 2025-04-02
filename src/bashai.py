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
SEARCH_DOMAINS = {
    'windows': ['microsoft.com', 'superuser.com', 'stackoverflow.com'],
    'linux': ['askubuntu.com', 'serverfault.com', 'stackoverflow.com']
}

class BashAI:
    def __init__(self):
        self.config = self._load_or_create_config()
        self.client = anthropic.Anthropic(api_key=self.config['api_key'])
        self.current_dir = os.getcwd()
        self.is_windows = os.name == 'nt'
        self.retry_count = 0

    def _load_or_create_config(self) -> dict:
        """Load or create configuration file with API key"""
        default_config = {
            "api_key": "",
            "auto_retry": True,
            "max_retries": MAX_RETRIES
        }

        if CONFIG_PATH.exists():
            with open(CONFIG_PATH) as f:
                return {**default_config, **json.load(f)}
        
        print("┌──────────────────────────────────────────────┐")
        print("│          Bash.ai First-Time Setup            │")
        print("└──────────────────────────────────────────────┘")
        api_key = input("Enter your Anthropic API key: ").strip()
        config = {**default_config, "api_key": api_key}
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f)
        return config

    def _search_web(self, error: str) -> bool:
        """Open browser with search results for the error"""
        domain = SEARCH_DOMAINS['windows' if self.is_windows else 'linux']
        query = f"{error} site:{' OR site:'.join(domain)}"
        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        print(f"\n🔍 Searching web for solutions: {error}")
        webbrowser.open(search_url)
        return input("\nPress Enter to continue after reviewing solutions...") == ''

    def _get_command_fix(self, cmd: str, error: str) -> str:
        """Get AI-suggested fix for failed command"""
        prompt = f"""Original command failed:
Command: {cmd}
Error: {error}

Suggest a corrected version for {"Windows" if self.is_windows else "Linux"}.
ONLY respond with the fixed command in <execute> tags."""
        
        response = self.client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    def execute_command(self, cmd: str) -> Tuple[str, bool]:
        """Execute command with auto-retry and web search"""
        last_error = ""
        
        for attempt in range(MAX_RETRIES + 1):
            try:
                if self.is_windows:
                    if ' ' in cmd and not cmd.startswith('"'):
                        cmd = f'"{cmd}"'
                    full_cmd = f'cmd /c {cmd}'
                else:
                    full_cmd = cmd

                result = subprocess.run(
                    full_cmd,
                    shell=True,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                return (result.stdout or "Command executed successfully", True)
                
            except subprocess.CalledProcessError as e:
                last_error = e.stderr.strip()
                print(f"\n⚠️ Attempt {attempt + 1} failed: {last_error}")
                
                if attempt < MAX_RETRIES:
                    # Get AI-suggested fix
                    fixed_cmd = self._get_command_fix(cmd, last_error)
                    if "<execute>" in fixed_cmd:
                        cmd = fixed_cmd.split("<execute>")[1].split("</execute>")[0].strip()
                        print(f"🔄 Retrying with: {cmd}")
                        time.sleep(1)
                    else:
                        break
                else:
                    break
                    
        return (f"Failed after {MAX_RETRIES} attempts: {last_error}", False)

    def start_interactive(self):
        """Start interactive session with enhanced error recovery"""
        print(f"\n⚡ Bash.ai [Auto-Retry Mode] (dir: {self.current_dir})")
        print("Type requests naturally. I'll execute and retry automatically.\n")
        
        while True:
            try:
                user_input = input("bash.ai> ").strip()
                if user_input.lower() in ['exit', 'quit']:
                    break
                if not user_input:
                    continue

                # Get AI response
                response = self.client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=1000,
                    messages=[{
                        "role": "user", 
                        "content": f"Current dir: {self.current_dir}\nRequest: {user_input}"
                    }],
                    system=f"""You are Bash.ai. Rules:
1. When asked to DO something, respond ONLY with the command in <execute> tags
2. For {"Windows" if self.is_windows else "Linux"} systems
3. Current directory: {self.current_dir}"""
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
                            self._search_web(output)
                else:
                    print(ai_response)

                # Update current directory if changed
                if "<execute>" in ai_response and "cd " in ai_response.lower():
                    self.current_dir = os.getcwd()

            except KeyboardInterrupt:
                print("\nUse 'exit' to quit")
            except Exception as e:
                print(f"🚨 Error: {str(e)}")

if __name__ == "__main__":
    ai = BashAI()
    ai.start_interactive()
