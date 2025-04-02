import os
import subprocess
import json
import anthropic
from pathlib import Path

CONFIG_PATH = Path.home() / ".bashai_config.json"

class BashAI:
    def __init__(self):
        self.config = self._load_or_create_config()
        self.client = anthropic.Anthropic(api_key=self.config['api_key'])
        self.current_dir = os.getcwd()

    def _load_or_create_config(self) -> dict:
        """Load or create configuration file"""
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH) as f:
                return json.load(f)
        
        print("First-time setup: Please enter your Anthropic API key")
        api_key = input("API key: ").strip()
        config = {"api_key": api_key}
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f)
        return config

    def execute_command(self, cmd: str) -> str:
        """Execute a shell command and return output"""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                executable="cmd.exe" if os.name == 'nt' else None
            )
            return result.stdout or "Command executed successfully"
        except subprocess.CalledProcessError as e:
            return f"Error: {e.stderr}"

    def start_interactive(self):
        """Start interactive session"""
        print(f"Bash.ai ready (Current dir: {self.current_dir})")
        print("Type commands naturally. I'll execute them when needed.")
        
        while True:
            try:
                user_input = input("\nbash.ai> ").strip()
                if user_input.lower() in ['exit', 'quit']:
                    break

                # Get AI response
                response = self.client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=1000,
                    messages=[{
                        "role": "user", 
                        "content": f"Current directory: {self.current_dir}\nUser request: {user_input}"
                    }],
                    system="""You are Bash.ai, an AI that helps with command line tasks. 
                    When asked to perform actions, respond with the exact command to execute enclosed in <execute> tags.
                    For Windows, use these commands:
                    - Create file: type nul > filename.txt
                    - List files: dir
                    - Make dir: mkdir name
                    Example: <execute>type nul > test.txt</execute>"""
                )

                ai_response = response.content[0].text
                print(f"\n{ai_response}")

                # Execute commands found in response
                if "<execute>" in ai_response:
                    cmd = ai_response.split("<execute>")[1].split("</execute>")[0].strip()
                    if input(f"\nExecute this command? [y/N] '{cmd}' ").lower() == 'y':
                        print(f"\n{self.execute_command(cmd)}")

            except KeyboardInterrupt:
                print("\nUse 'exit' to quit")
            except Exception as e:
                print(f"Error: {str(e)}")

if __name__ == "__main__":
    ai = BashAI()
    ai.start_interactive()
