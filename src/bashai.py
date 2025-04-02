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
        self.is_windows = os.name == 'nt'

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
            # For Windows, we need to run through cmd.exe with proper formatting
            if self.is_windows:
                # Handle paths with spaces by adding quotes
                if ' ' in cmd and not cmd.startswith('"'):
                    cmd = f'"{cmd}"'
                # Force command through cmd.exe
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
            return result.stdout or "Command executed successfully"
        except subprocess.CalledProcessError as e:
            return f"Error: {e.stderr}"
        except Exception as e:
            return f"System Error: {str(e)}"

    def start_interactive(self):
        """Start interactive session"""
        print(f"Bash.ai ready (Current dir: {self.current_dir})")
        print("Type commands naturally. I'll execute them when needed.")
        
        while True:
            try:
                user_input = input("\nbash.ai> ").strip()
                if user_input.lower() in ['exit', 'quit']:
                    break

                # Get AI response with current directory context
                response = self.client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=1000,
                    messages=[{
                        "role": "user", 
                        "content": f"Current directory: {self.current_dir}\nUser request: {user_input}"
                    }],
                    system=f"""You are Bash.ai, an AI that executes command line tasks on Windows. Rules:
1. Always provide Windows commands
2. For file creation: type nul > filename.txt
3. For directories: mkdir "dirname"
4. For listing: dir
5. Always use absolute paths with double quotes if spaces exist
6. Current directory: {self.current_dir}"""
                )

                ai_response = response.content[0].text
                print(f"\n{ai_response}")

                # Execute commands found in response
                if "<execute>" in ai_response:
                    cmd = ai_response.split("<execute>")[1].split("</execute>")[0].strip()
                    if input(f"\nExecute this command? [y/N] '{cmd}' ").lower() == 'y':
                        result = self.execute_command(cmd)
                        print(f"\n{result}")
                        # Update current directory if cd command was executed
                        if cmd.startswith('cd '):
                            self.current_dir = os.getcwd()

            except KeyboardInterrupt:
                print("\nUse 'exit' to quit")
            except Exception as e:
                print(f"Error: {str(e)}")

if __name__ == "__main__":
    ai = BashAI()
    ai.start_interactive()
