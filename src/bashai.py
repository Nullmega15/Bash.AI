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
        self.auto_execute = True  # Set to True to execute commands automatically

    def _load_or_create_config(self) -> dict:
        """Load or create configuration file"""
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH) as f:
                return json.load(f)
        
        print("First-time setup: Please enter your Anthropic API key")
        api_key = input("API key: ").strip()
        config = {"api_key": api_key, "auto_execute": True}
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f)
        return config

    def execute_command(self, cmd: str) -> str:
        """Execute a shell command and return output"""
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
            return result.stdout or "Done"
        except subprocess.CalledProcessError as e:
            return f"Error: {e.stderr}"
        except Exception as e:
            return f"System Error: {str(e)}"

    def start_interactive(self):
        """Start interactive session"""
        print(f"\nBash.ai [Auto-Execute Mode] (Current dir: {self.current_dir})")
        print("I'll automatically perform actions you request. Type 'exit' to quit.\n")
        
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
                    system=f"""You are Bash.ai, an AI that executes Windows commands automatically. Rules:
1. When asked to DO something, respond ONLY with the command in <execute> tags
2. For file creation: type nul > filename.txt
3. For directories: mkdir "name" 
4. For listing: dir
5. Always use absolute paths with quotes
6. Current directory: {self.current_dir}"""
                )

                ai_response = response.content[0].text
                
                # Extract and execute command
                if "<execute>" in ai_response:
                    cmd = ai_response.split("<execute>")[1].split("</execute>")[0].strip()
                    print(f"\nExecuting: {cmd}")
                    result = self.execute_command(cmd)
                    print(result)
                else:
                    print(ai_response)

                # Update current directory if cd command was executed
                if "<execute>" in ai_response and "cd " in ai_response.lower():
                    self.current_dir = os.getcwd()

            except KeyboardInterrupt:
                print("\nUse 'exit' to quit")
            except Exception as e:
                print(f"Error: {str(e)}")

if __name__ == "__main__":
    ai = BashAI()
    ai.start_interactive()
