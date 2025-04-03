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
        self.shell_type = self._detect_shell()
        self.shell_commands = self._load_shell_commands()

    def _detect_shell(self) -> str:
        """Accurately detect the current shell type"""
        try:
            # Method 1: Check environment variables
            shell = os.environ.get('SHELL', '').lower()
            if 'powershell' in shell or 'pwsh' in shell:
                return 'powershell'
            
            # Method 2: Check parent process (Windows)
            if self.is_windows:
                import psutil
                parent = psutil.Process(os.getppid()).name().lower()
                if 'powershell' in parent:
                    return 'powershell'
                if 'cmd' in parent:
                    return 'cmd'
            
            # Method 3: Check process name (Linux/Mac)
            if not self.is_windows:
                import psutil
                proc = psutil.Process(os.getpid())
                for parent in proc.parents():
                    if 'bash' in parent.name().lower():
                        return 'bash'
                    if 'zsh' in parent.name().lower():
                        return 'bash'  # Treat zsh as bash for compatibility
            
            # Fallback methods
            if self.is_windows:
                # Check if PowerShell-specific vars exist
                if 'PSModulePath' in os.environ:
                    return 'powershell'
                return 'cmd'
            return 'bash'
        
        except Exception:
            # Ultimate fallback
            return 'cmd' if self.is_windows else 'bash'

    def _load_shell_commands(self) -> Dict[str, List[str]]:
        """Shell-specific command knowledge base"""
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
                'Get-NetIPConfiguration', 'Invoke-WebRequest',
                'Write-Output', 'Select-String', 'ForEach-Object'
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

    def _get_shell_prefix(self) -> str:
        """Get the appropriate command prefix for the shell"""
        return {
            'cmd': 'cmd /c',
            'powershell': 'powershell -Command',
            'bash': ''
        }.get(self.shell_type, '')

    def execute_command(self, cmd: str) -> Tuple[str, bool]:
        """Execute command with shell-specific handling"""
        last_error = ""
        
        with Spinner():
            for attempt in range(MAX_RETRIES + 1):
                try:
                    # Add shell-specific prefixes
                    if self.shell_type == 'powershell' and not cmd.startswith('powershell'):
                        cmd = f'powershell -Command "{cmd}"'
                    elif self.shell_type == 'cmd' and not cmd.startswith(('cmd', 'powershell')):
                        cmd = f'cmd /c "{cmd}"'

                    result = subprocess.run(
                        cmd,
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

    def _generate_response(self, user_input: str) -> str:
        """Get AI response with shell context"""
        return self.client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1000,
            messages=[{
                "role": "user", 
                "content": f"""Request: {user_input}
                Current shell: {self.shell_type}
                Current dir: {self.current_dir}
                Available commands: {self.shell_commands[self.shell_type]}"""
            }],
            system=f"""You are Bash.ai, a {self.shell_type} expert. Rules:
1. For actions: respond ONLY with command in <execute> tags
2. Use {self.shell_type}-specific commands:
   - CMD: dir, copy, del
   - PowerShell: Get-ChildItem, Copy-Item, Remove-Item
   - Bash: ls, cp, rm
3. Current directory: {self.current_dir}
4. Never suggest commands from other shells"""
        ).content[0].text

    def start_interactive(self):
        """Start interactive session with proper shell detection"""
        print(f"\n💻 Bash.ai [{self.shell_type.upper()} Mode] (dir: {self.current_dir})")
        print(f"Detected shell: {self._get_shell_name()}\n")
        
        while True:
            try:
                user_input = input("bash.ai> ").strip()
                if user_input.lower() in ['exit', 'quit']:
                    break
                if user_input.lower() == 'help':
                    self._show_help()
                    continue

                response = self._generate_response(user_input)
                
                if "<execute>" in response:
                    cmd = response.split("<execute>")[1].split("</execute>")[0].strip()
                    print(f"\n⚙️ Executing [{self.shell_type}]: {cmd}")
                    output, success = self.execute_command(cmd)
                    print(output)
                    
                    if not success and input("\nSearch web for solutions? [y/N] ").lower() == 'y':
                        webbrowser.open(f"https://stackoverflow.com/search?q={cmd}+error+{last_error}")
                else:
                    print(response)

                # Update current directory
                if any(cmd in response.lower() for cmd in ['cd ', 'set-location']):
                    self.current_dir = os.getcwd()

            except KeyboardInterrupt:
                print("\nUse 'exit' to quit")
            except Exception as e:
                print(f"🚨 Error: {str(e)}")

    def _get_shell_name(self) -> str:
        """Get friendly shell name"""
        return {
            'cmd': 'Windows Command Prompt',
            'powershell': 'Windows PowerShell',
            'bash': 'Unix Bash Shell'
        }.get(self.shell_type, 'Unknown Shell')

    def _show_help(self):
        """Show shell-specific help"""
        print(f"\n{self._get_shell_name()} Commands:")
        for cmd in self.shell_commands[self.shell_type]:
            print(f"- {cmd}")
        print(f"\nExamples:")
        if self.shell_type == 'cmd':
            print("  list files: dir\n  copy file: copy src.txt dst.txt")
        elif self.shell_type == 'powershell':
            print("  list files: Get-ChildItem\n  copy file: Copy-Item src.txt dst.txt")
        else:
            print("  list files: ls -l\n  copy file: cp src.txt dst.txt")

if __name__ == "__main__":
    ai = BashAI()
    ai.start_interactive()
