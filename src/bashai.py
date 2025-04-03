import os
import subprocess
import json
import webbrowser
import anthropic
from pathlib import Path
from typing import Tuple, Dict, List
from threading import Thread
import sys
import time

CONFIG_PATH = Path.home() / ".bashai_config.json"
MAX_RETRIES = 3

class Spinner:
    """Animated spinner for operations"""
    def __init__(self):
        self.spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        self.stop_running = False

    def spin(self, message="Working"):
        """Show spinner animation"""
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
        self.shell_commands = self._load_shell_commands()
        self.shell_type = self._detect_shell()

    def _detect_shell(self) -> str:
        """Detect the current shell type"""
        if self.is_windows:
            if 'powershell' in os.environ.get('SHELL', '').lower():
                return 'powershell'
            return 'cmd'
        return 'bash'

    def _load_shell_commands(self) -> Dict[str, List[str]]:
        """Predefined commands for CMD, PowerShell and Bash"""
        return {
            'cmd': [
                'dir', 'cd', 'copy', 'del', 'mkdir', 'rmdir', 
                'type', 'find', 'findstr', 'tasklist', 'taskkill',
                'systeminfo', 'ipconfig', 'ping', 'tracert', 'netstat',
                'xcopy', 'robocopy', 'sfc', 'chkdsk', 'diskpart'
            ],
            'powershell': [
                'Get-ChildItem', 'Set-Location', 'Copy-Item',
                'Remove-Item', 'New-Item', 'Get-Content',
                'Get-Process', 'Stop-Process', 'Get-Service',
                'Start-Service', 'Test-NetConnection',
                'Get-NetIPConfiguration', 'Invoke-WebRequest'
            ],
            'bash': [
                'ls', 'cd', 'cp', 'rm', 'mkdir', 'rmdir',
                'cat', 'grep', 'find', 'ps', 'kill', 'top',
                'ifconfig', 'ping', 'traceroute', 'netstat',
                'curl', 'wget', 'chmod', 'chown', 'df', 'du'
            ]
        }

    def _load_or_create_config(self) -> Dict:
        """Load or create configuration file"""
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

    def _search_web(self, error: str):
        """Search error solutions online"""
        query = f"{error} site:stackoverflow.com OR site:learn.microsoft.com"
        webbrowser.open(f"https://google.com/search?q={query.replace(' ', '+')}")
        print(f"\n🔍 Searching web for solutions...")

    def execute_command(self, cmd: str) -> Tuple[str, bool]:
        """Execute command with auto-retry and spinner"""
        last_error = ""
        
        with Spinner():
            for attempt in range(MAX_RETRIES + 1):
                try:
                    if self.is_windows:
                        if ' ' in cmd and not cmd.startswith('"'):
                            cmd = f'"{cmd}"'
                        full_cmd = f'cmd /c {cmd}' if self.shell_type == 'cmd' else cmd
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
                    return (result.stdout or "✓ Command executed", True)
                    
                except subprocess.CalledProcessError as e:
                    last_error = e.stderr.strip()
                    if attempt < MAX_RETRIES:
                        time.sleep(1)
                        continue
                    return (f"✗ Error: {last_error}", False)

    def _generate_code(self, request: str) -> str:
        """Generate code based on request"""
        with Spinner("Generating code"):
            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=2000,
                messages=[{
                    "role": "user", 
                    "content": f"""Create complete code for: {request}
                    Requirements:
                    1. Include all necessary code
                    2. Add brief comments
                    3. Save to appropriate filename
                    4. Format for {self.shell_type.upper()}"""
                }],
                system="""Respond with:
                <filename>filename.ext</filename>
                <code>
                # Complete code here
                </code>"""
            )
            return response.content[0].text

    def _show_help(self):
        """Show available commands for current shell"""
        print(f"\nAvailable {self.shell_type.upper()} commands:")
        for cmd in self.shell_commands[self.shell_type]:
            print(f"- {cmd}")
        print("\nTry: 'list files', 'show processes', 'make python script'")

    def start_interactive(self):
        """Start interactive session with enhanced command knowledge"""
        print(f"\n💻 Bash.ai [{self.shell_type.upper()} Mode] (dir: {self.current_dir})")
        print("Type commands naturally or 'help' for examples\n")
        
        while True:
            try:
                user_input = input("bash.ai> ").strip()
                if user_input.lower() in ['exit', 'quit']:
                    break
                if user_input.lower() == 'help':
                    self._show_help()
                    continue

                # Handle code generation requests
                if any(word in user_input.lower() for word in ['make', 'create', 'generate']):
                    code_response = self._generate_code(user_input)
                    
                    if "<filename>" in code_response:
                        filename = code_response.split("<filename>")[1].split("</filename>")[0].strip()
                        code = code_response.split("<code>")[1].split("</code>")[0].strip()
                        
                        print(f"\n📄 Creating: {filename}")
                        with open(filename, 'w') as f:
                            f.write(code)
                        
                        print(f"✓ Successfully created {filename}")
                        if filename.endswith('.py'):
                            run = input(f"Run {filename}? [y/N] ").lower()
                            if run == 'y':
                                output, success = self.execute_command(f"python {filename}")
                                print(output)
                    else:
                        print(code_response)
                    continue

                # Get AI response with command knowledge
                response = self.client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=1000,
                    messages=[{
                        "role": "user", 
                        "content": f"""Request: {user_input}
                        Current shell: {self.shell_type}
                        Current dir: {self.current_dir}
                        Available commands: {self.shell_commands[self.shell_type]}"""
                    }],
                    system=f"""You are Bash.ai, an expert {self.shell_type} assistant. Rules:
1. For actions: respond ONLY with command in <execute> tags
2. For PowerShell: Use full cmdlets
3. For CMD: Use traditional commands
4. For Bash: Use standard Unix commands
5. Current directory: {self.current_dir}"""
                )

                ai_response = response.content[0].text
                
                if "<execute>" in ai_response:
                    cmd = ai_response.split("<execute>")[1].split("</execute>")[0].strip()
                    print(f"\n⚙️ Executing: {cmd}")
                    output, success = self.execute_command(cmd)
                    print(output)
                    
                    if not success and input("\nSearch web for solutions? [y/N] ").lower() == 'y':
                        self._search_web(output)
                else:
                    print(ai_response)

                # Update current directory if changed
                if "<execute>" in ai_response and ("cd " in ai_response.lower() or "Set-Location" in ai_response):
                    self.current_dir = os.getcwd()

            except KeyboardInterrupt:
                print("\nUse 'exit' to quit")
            except Exception as e:
                print(f"🚨 Error: {str(e)}")

if __name__ == "__main__":
    ai = BashAI()
    ai.start_interactive()
