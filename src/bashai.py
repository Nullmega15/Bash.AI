import os
import subprocess
import json
import anthropic
from pathlib import Path
from typing import Tuple, Dict
from threading import Thread
import sys
import time

CONFIG_PATH = Path.home() / ".bashai_config.json"

class Spinner:
    """Animated spinner for operations"""
    def __init__(self):
        self.spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        self.stop_running = False

    def spin(self, message="Working"):
        i = 0
        while not self.stop_running:
            sys.stdout.write(f"\r{self.spinner_chars[i]} {message}... ")
            sys.stdout.flush()
            time.sleep(0.1)
            i = (i + 1) % len(self.spinner_chars)
        sys.stdout.write("\r" + " " * (len(message) + 10) + "\r")

    def __enter__(self):
        self.stop_running = False
        Thread(target=self.spin, daemon=True).start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_running = True
        time.sleep(0.2)
        sys.stdout.write("\r" + " " * 50 + "\r")

class BashAI:
    def __init__(self):
        self.config = self._load_or_create_config()
        self.client = anthropic.Anthropic(api_key=self.config['api_key'])
        self.current_dir = os.getcwd()
        self.is_windows = os.name == 'nt'

    def _load_or_create_config(self) -> Dict:
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

    def _generate_code(self, request: str) -> Tuple[str, str]:
        """Generate complete code files for any language"""
        with Spinner():
            response = self.client.messages.create(
                model="claude-3-5-haiku-20241022",  # Updated to the new model
                max_tokens=4000,
                messages=[{
                    "role": "user",
                    "content": f"""Create complete, runnable code for: {request}
                    Requirements:
                    1. Full implementation with all imports/dependencies
                    2. Comments explaining key sections
                    3. Proper file extension (.py, .js, etc.)
                    4. No placeholder comments"""
                }],
                system="""Respond with:
                <filename>filename.ext</filename>
                <code>
                // Complete code here
                </code>
                <dependencies>
                package1 package2
                </dependencies>"""
            )
            content = response.content[0].text
            filename = content.split("<filename>")[1].split("</filename>")[0].strip()
            code = content.split("<code>")[1].split("</code>")[0].strip()
            deps = content.split("<dependencies>")[1].split("</dependencies>")[0].strip() if "<dependencies>" in content else ""
            return filename, code, deps

    def _install_dependencies(self, deps: str):
        """Install required packages"""
        if not deps:
            return

        print(f"📦 Installing dependencies: {deps}")
        for manager in ['pip', 'npm', 'cargo']:
            if manager in deps.lower():
                cmd = f"{manager} install {deps}"
                output, success = self._execute_command(cmd)
                print(output)
                if not success:
                    print(f"⚠️ Failed to install some dependencies")

    def _execute_command(self, cmd: str) -> Tuple[str, bool]:
        """Execute a command with proper shell handling"""
        with Spinner():
            try:
                result = subprocess.run(
                    cmd,
                    shell=True,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                return (result.stdout or "✓ Done", True)
            except subprocess.CalledProcessError as e:
                return (f"✗ Error: {e.stderr}", False)

    def start_interactive(self):
        """Start interactive coding and terminal session"""
        print(f"\n💻 Bash.ai Multi-Language Coder and Terminal Helper (dir: {self.current_dir})")
        print("Request any code or terminal command: 'make python API', 'create react component', 'ls', 'cd', etc.\n")

        while True:
            try:
                user_input = input("bash.ai> ").strip()
                if user_input.lower() in ['exit', 'quit']:
                    break

                # Recognize terminal commands
                terminal_commands = ['ls', 'pwd', 'cd', 'cat', 'echo', 'mkdir', 'rm', 'touch', 'whoami', 'history']
                if any(user_input.startswith(cmd) for cmd in terminal_commands):
                    print(f"Executing command: {user_input}")
                    output, success = self._execute_command(user_input)
                    print(output)
                    continue

                # Code generation mode
                if any(word in user_input.lower() for word in ['code', 'make', 'create', 'build']):
                    filename, code, deps = self._generate_code(user_input)

                    print(f"\n📄 Creating: {filename}")
                    with open(filename, 'w') as f:
                        f.write(code)
                    print(f"✓ Successfully created {filename}")

                    # Install dependencies if any
                    self._install_dependencies(deps)

                    # Offer to run the code
                    if filename.endswith(('.py', '.js', '.sh')):
                        run = input(f"\nRun {filename}? [y/N] ").lower()
                        if run == 'y':
                            runner = {
                                '.py': 'python',
                                '.js': 'node',
                                '.sh': 'bash'
                            }.get(filename[filename.rfind('.'):], '')
                            if runner:
                                print(f"\n🚀 Executing: {runner} {filename}")
                                output, _ = self._execute_command(f"{runner} {filename}")
                                print(output)

                    continue

                # Command execution mode
                response = self.client.messages.create(
                    model="claude-3-5-haiku-20241022",  # Updated to the new model
                    max_tokens=1000,
                    messages=[{
                        "role": "user", 
                        "content": f"Request: {user_input}\nCurrent dir: {self.current_dir}"
                    }],
                    system="""Respond with:
                    1. For coding requests: <filename> and <code>
                    2. For commands: <execute>command</execute>"""
                )

                ai_response = response.content[0].text
                print(ai_response)

                # Extract and execute command
                if "<execute>" in ai_response and "</execute>" in ai_response:
                    command = ai_response.split("<execute>")[1].split("</execute>")[0].strip()
                    print(f"Executing command: {command}")
                    output, success = self._execute_command(command)
                    print(output)
                else:
                    print(ai_response)

            except KeyboardInterrupt:
                print("\nUse 'exit' to quit")
            except Exception as e:
                print(f"🚨 Error: {str(e)}")

if __name__ == "__main__":
    ai = BashAI()
    ai.start_interactive()
