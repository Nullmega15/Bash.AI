#!/usr/bin/env python3
"""
Bash.ai - AI-powered terminal assistant with local DeepSeek Coder support
Cross-platform client for Windows, Linux, and macOS
"""

import os
import sys
import json
import subprocess
import platform
import argparse
import requests
from pathlib import Path
from typing import Tuple, Dict, Optional, List
from threading import Thread
import time
import signal

# Cross-platform imports
try:
    if platform.system() == "Windows":
        import pyreadline3 as readline
    else:
        import readline
except ImportError:
    readline = None

# Configuration
CONFIG_PATH = Path.home() / ".bashai_config.json"
DEFAULT_SERVER_URL = "http://localhost:8000"

class Colors:
    """ANSI color codes for cross-platform terminal colors"""
    RED = '\033[91m'
    GREEN = '\033[92m' 
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'
    
    @classmethod
    def disable_on_windows(cls):
        """Disable colors on older Windows versions"""
        if platform.system() == "Windows":
            try:
                os.system('color')  # Try to enable ANSI colors
            except:
                # Fallback: disable colors
                for attr in dir(cls):
                    if not attr.startswith('_') and attr != 'disable_on_windows':
                        setattr(cls, attr, '')

# Initialize colors
Colors.disable_on_windows()

class Spinner:
    """Cross-platform animated spinner"""
    def __init__(self, message="Working"):
        self.message = message
        self.spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        self.stop_running = False

    def spin(self):
        i = 0
        while not self.stop_running:
            char = self.spinner_chars[i % len(self.spinner_chars)]
            sys.stdout.write(f"\r{Colors.CYAN}{char}{Colors.END} {self.message}... ")
            sys.stdout.flush()
            time.sleep(0.1)
            i += 1
        sys.stdout.write("\r" + " " * (len(self.message) + 10) + "\r")
        sys.stdout.flush()

    def __enter__(self):
        self.stop_running = False
        self.thread = Thread(target=self.spin, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_running = True
        time.sleep(0.2)

class BashAI:
    def __init__(self, server_url: str = None):
        self.config = self._load_or_create_config()
        self.server_url = server_url or self.config.get('server_url', DEFAULT_SERVER_URL)
        self.current_dir = os.getcwd()
        self.is_windows = platform.system() == "Windows"
        self.is_macos = platform.system() == "Darwin"
        self.is_linux = platform.system() == "Linux"
        self.history = []
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        
        # Check server connection
        if not self._check_server_connection():
            print(f"{Colors.YELLOW}⚠️  Warning: Cannot connect to AI server at {self.server_url}{Colors.END}")
            print(f"{Colors.YELLOW}   Make sure the server is running: python server.py{Colors.END}")

    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        print(f"\n{Colors.YELLOW}Use 'exit' or 'quit' to exit properly{Colors.END}")

    def _load_or_create_config(self) -> Dict:
        """Load or create configuration file"""
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

        print(f"{Colors.BOLD}┌──────────────────────────────────────────────┐{Colors.END}")
        print(f"{Colors.BOLD}│          Bash.ai First-Time Setup            │{Colors.END}")
        print(f"{Colors.BOLD}└──────────────────────────────────────────────┘{Colors.END}")
        
        server_url = input(f"Enter AI server URL [{DEFAULT_SERVER_URL}]: ").strip()
        if not server_url:
            server_url = DEFAULT_SERVER_URL
            
        config = {
            "server_url": server_url,
            "max_history": 100,
            "auto_execute": False,
            "safe_mode": True
        }
        
        try:
            with open(CONFIG_PATH, 'w') as f:
                json.dump(config, f, indent=2)
        except IOError as e:
            print(f"{Colors.RED}Warning: Could not save config: {e}{Colors.END}")
            
        return config

    def _check_server_connection(self) -> bool:
        """Check if AI server is accessible"""
        try:
            response = requests.get(f"{self.server_url}/health", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def _query_ai(self, message: str, system_prompt: str = None) -> Tuple[str, bool]:
        """Query the AI server"""
        try:
            with Spinner("Thinking"):
                payload = {
                    "message": message, 
                    "system_prompt": system_prompt,
                    "max_tokens": 1000,
                    "temperature": 0.7
                }
                
                response = requests.post(
                    f"{self.server_url}/chat",
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("response", ""), data.get("success", False)
                else:
                    return f"Server error: {response.status_code}", False
                    
        except requests.RequestException as e:
            return f"Connection error: {str(e)}", False

    def _execute_command(self, cmd: str, show_command: bool = True) -> Tuple[str, bool]:
        """Execute a system command safely"""
        if show_command:
            print(f"{Colors.BLUE}Executing:{Colors.END} {cmd}")
            
        # Safety check
        dangerous_commands = ['rm -rf /', 'del /f /s /q C:\\', 'format', 'fdisk']
        if self.config.get('safe_mode', True):
            if any(danger in cmd.lower() for danger in dangerous_commands):
                return f"{Colors.RED}Blocked dangerous command for safety{Colors.END}", False

        try:
            with Spinner("Running"):
                # Use appropriate shell based on OS
                shell = True
                if self.is_windows:
                    # Use cmd on Windows
                    result = subprocess.run(
                        cmd, shell=shell, capture_output=True, text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                    )
                else:
                    # Use bash/sh on Unix-like systems
                    result = subprocess.run(
                        cmd, shell=shell, capture_output=True, text=True
                    )
                
                if result.returncode == 0:
                    output = result.stdout.strip() if result.stdout else "✓ Command completed successfully"
                    return output, True
                else:
                    error = result.stderr.strip() if result.stderr else f"Command failed with exit code {result.returncode}"
                    return f"{Colors.RED}Error: {error}{Colors.END}", False
                    
        except Exception as e:
            return f"{Colors.RED}Execution error: {str(e)}{Colors.END}", False

    def _create_file(self, filename: str, content: str) -> bool:
        """Create a file with given content"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"{Colors.GREEN}✓ Created {filename}{Colors.END}")
            return True
        except Exception as e:
            print(f"{Colors.RED}Error creating {filename}: {str(e)}{Colors.END}")
            return False

    def _get_system_prompt(self) -> str:
        """Get system prompt based on current OS and context"""
        os_info = {
            'system': platform.system(),
            'release': platform.release(),
            'machine': platform.machine(),
            'current_dir': self.current_dir
        }
        
        return f"""You are Bash.ai, an expert terminal assistant and code generator.
Current environment: {os_info['system']} {os_info['release']} ({os_info['machine']})
Current directory: {os_info['current_dir']}

Guidelines:
1. For terminal commands: Provide the exact command to run
2. For code requests: Generate complete, runnable code with proper syntax
3. Always consider the current OS when suggesting commands
4. Be concise but thorough in explanations
5. If asked to create files, provide the complete file content

Respond in one of these formats:
- For commands: <execute>command_here</execute>
- For code: <filename>name.ext</filename><code>full_code_here</code>
- For explanations: Just provide the explanation

Current OS-specific command syntax:
- Windows: Use PowerShell/CMD syntax (dir, copy, del, etc.)
- Linux/macOS: Use bash syntax (ls, cp, rm, etc.)"""

    def _parse_ai_response(self, response: str) -> Dict:
        """Parse AI response to extract commands or code"""
        result = {
            'type': 'explanation',
            'content': response,
            'command': None,
            'filename': None,
            'code': None
        }
        
        # Check for command
        if '<execute>' in response and '</execute>' in response:
            start = response.find('<execute>') + 9
            end = response.find('</execute>')
            result['type'] = 'command'
            result['command'] = response[start:end].strip()
            
        # Check for code
        elif '<filename>' in response and '<code>' in response:
            # Extract filename
            start = response.find('<filename>') + 10
            end = response.find('</filename>')
            result['filename'] = response[start:end].strip()
            
            # Extract code
            start = response.find('<code>') + 6
            end = response.find('</code>')
            result['code'] = response[start:end].strip()
            result['type'] = 'code'
            
        return result

    def _interactive_mode(self):
        """Start interactive terminal session"""
        print(f"\n{Colors.BOLD}{Colors.CYAN}💻 Bash.ai - AI Terminal Assistant{Colors.END}")
        print(f"{Colors.CYAN}Platform: {platform.system()} {platform.release()}{Colors.END}")
        print(f"{Colors.CYAN}Directory: {self.current_dir}{Colors.END}")
        print(f"{Colors.CYAN}Server: {self.server_url}{Colors.END}")
        print(f"{Colors.YELLOW}Type 'help' for commands, 'exit' to quit{Colors.END}\n")

        while True:
            try:
                # Get user input
                prompt = f"{Colors.GREEN}bash.ai{Colors.END} {Colors.BLUE}{os.path.basename(self.current_dir)}{Colors.END}> "
                user_input = input(prompt).strip()
                
                if not user_input:
                    continue
                    
                # Handle built-in commands
                if user_input.lower() in ['exit', 'quit']:
                    print(f"{Colors.CYAN}Goodbye!{Colors.END}")
                    break
                    
                elif user_input.lower() == 'help':
                    self._show_help()
                    continue
                    
                elif user_input.lower() == 'clear':
                    os.system('cls' if self.is_windows else 'clear')
                    continue
                    
                elif user_input.lower() == 'config':
                    self._show_config()
                    continue
                    
                elif user_input.startswith('cd '):
                    self._handle_cd(user_input[3:].strip())
                    continue

                # Add to history
                self.history.append(user_input)
                if len(self.history) > self.config.get('max_history', 100):
                    self.history.pop(0)

                # Query AI
                ai_response, success = self._query_ai(user_input, self._get_system_prompt())
                
                if not success:
                    print(f"{Colors.RED}AI Error: {ai_response}{Colors.END}")
                    continue

                # Parse and handle response
                parsed = self._parse_ai_response(ai_response)
                
                if parsed['type'] == 'command':
                    # Execute command
                    if self.config.get('auto_execute', False):
                        output, success = self._execute_command(parsed['command'])
                        print(output)
                    else:
                        confirm = input(f"\nExecute command? {Colors.YELLOW}{parsed['command']}{Colors.END} [Y/n]: ")
                        if confirm.lower() != 'n':
                            output, success = self._execute_command(parsed['command'])
                            print(output)
                            
                elif parsed['type'] == 'code':
                    # Create code file
                    print(f"\n{Colors.PURPLE}Generated code for: {parsed['filename']}{Colors.END}")
                    print(f"{Colors.CYAN}Preview:{Colors.END}")
                    print("-" * 50)
                    print(parsed['code'][:500] + ("..." if len(parsed['code']) > 500 else ""))
                    print("-" * 50)
                    
                    confirm = input(f"\nSave to {parsed['filename']}? [Y/n]: ")
                    if confirm.lower() != 'n':
                        if self._create_file(parsed['filename'], parsed['code']):
                            # Offer to run the file
                            if parsed['filename'].endswith(('.py', '.js', '.sh', '.ps1')):
                                run_confirm = input(f"Run {parsed['filename']}? [y/N]: ")
                                if run_confirm.lower() == 'y':
                                    self._run_code_file(parsed['filename'])
                else:
                    # Regular explanation
                    print(f"\n{ai_response}")

            except KeyboardInterrupt:
                print(f"\n{Colors.YELLOW}Use 'exit' to quit{Colors.END}")
            except EOFError:
                print(f"\n{Colors.CYAN}Goodbye!{Colors.END}")
                break
            except Exception as e:
                print(f"{Colors.RED}Error: {str(e)}{Colors.END}")

    def _handle_cd(self, path: str):
        """Handle directory change"""
        try:
            if path == '~':
                path = str(Path.home())
            elif path == '..':
                path = str(Path(self.current_dir).parent)
            elif not os.path.isabs(path):
                path = os.path.join(self.current_dir, path)
                
            if os.path.isdir(path):
                os.chdir(path)
                self.current_dir = os.getcwd()
                print(f"{Colors.GREEN}Changed to: {self.current_dir}{Colors.END}")
            else:
                print(f"{Colors.RED}Directory not found: {path}{Colors.END}")
        except Exception as e:
            print(f"{Colors.RED}Error changing directory: {str(e)}{Colors.END}")

    def _run_code_file(self, filename: str):
        """Run a code file based on extension"""
        runners = {
            '.py': 'python',
            '.js': 'node', 
            '.sh': 'bash',
            '.ps1': 'powershell -ExecutionPolicy Bypass -File'
        }
        
        ext = os.path.splitext(filename)[1]
        runner = runners.get(ext)
        
        if runner:
            command = f"{runner} {filename}"
            output, success = self._execute_command(command)
            print(output)
        else:
            print(f"{Colors.YELLOW}Don't know how to run {filename}{Colors.END}")

    def _show_help(self):
        """Show help information"""
        help_text = f"""
{Colors.BOLD}Bash.ai Commands:{Colors.END}
  help                 - Show this help
  exit, quit          - Exit the program
  clear               - Clear the screen
  config              - Show configuration
  cd <path>           - Change directory

{Colors.BOLD}Usage Examples:{Colors.END}
  {Colors.CYAN}list all python files{Colors.END}
  {Colors.CYAN}create a backup script{Colors.END}
  {Colors.CYAN}make a calculator in python{Colors.END}
  {Colors.CYAN}show disk usage{Colors.END}
  {Colors.CYAN}find large files{Colors.END}

{Colors.BOLD}Code Generation:{Colors.END}
  {Colors.CYAN}make a web server in python{Colors.END}
  {Colors.CYAN}create a bash script to monitor cpu{Colors.END}
  {Colors.CYAN}build a todo app in javascript{Colors.END}
"""
        print(help_text)

    def _show_config(self):
        """Show current configuration"""
        print(f"\n{Colors.BOLD}Current Configuration:{Colors.END}")
        for key, value in self.config.items():
            print(f"  {key}: {value}")
        print(f"  config_path: {CONFIG_PATH}")

def main():
    parser = argparse.ArgumentParser(description="Bash.ai - AI Terminal Assistant")
    parser.add_argument('--server', '-s', help='AI server URL', default=None)
    parser.add_argument('--config', '-c', help='Show configuration', action='store_true')
    parser.add_argument('command', nargs='*', help='Command to execute')
    
    args = parser.parse_args()
    
    # Initialize bash.ai
    ai = BashAI(server_url=args.server)
    
    if args.config:
        ai._show_config()
        return
        
    if args.command:
        # Single command mode
        command = ' '.join(args.command)
        response, success = ai._query_ai(command, ai._get_system_prompt())
        if success:
            parsed = ai._parse_ai_response(response)
            if parsed['type'] == 'command':
                output, _ = ai._execute_command(parsed['command'])
                print(output)
            else:
                print(response)
        else:
            print(f"{Colors.RED}Error: {response}{Colors.END}")
    else:
        # Interactive mode
        ai._interactive_mode()

if __name__ == "__main__":
    main()
