#!/usr/bin/env python3
"""
Bash.ai - AI-powered terminal assistant with remote DeepSeek Coder support
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
import re # Import regex module for parsing markdown code blocks

# Supabase imports
# Ensure you have 'supabase' installed: pip install supabase
from supabase import create_client, Client
from gotrue.errors import AuthApiError # Import specific Supabase auth error

# Cross-platform imports for readline (for command history and editing)
try:
    if platform.system() == "Windows":
        import pyreadline3 as readline
    else:
        import readline
except ImportError:
    readline = None # Fallback if readline is not available

# Configuration paths and defaults
# This configuration file will store the server URL, Supabase URL, and other settings
CONFIG_PATH = Path.home() / ".bashai_config.json"
DEFAULT_SERVER_URL = "http://localhost:8000" # Default server URL

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
        """
        Disable ANSI colors on older Windows versions that don't support them.
        Newer Windows 10/11 terminals support ANSI colors by default.
        """
        if platform.system() == "Windows":
            try:
                # Try to enable ANSI colors. This might fail on older cmd.exe.
                os.system('') # This command can initialize ANSI escape sequence processing
            except:
                # Fallback: disable colors by setting all color attributes to empty strings
                for attr in dir(cls):
                    if not attr.startswith('_') and attr != 'disable_on_windows' and attr != 'wrap_for_readline':
                        setattr(cls, attr, '')

    @staticmethod
    def wrap_for_readline(text_with_ansi: str) -> str:
        """
        Wraps ANSI escape codes with \001 (start) and \002 (end) markers
        for readline to correctly calculate string width, preventing wrapping issues.
        Only applies if readline is available.
        """
        if readline:
            # This regex finds ANSI escape sequences (e.g., \x1b[...m)
            # and wraps them with readline's non-printable markers.
            return re.sub(r'\x1b\[[0-9;]*m', r'\001\g<0>\002', text_with_ansi)
        return text_with_ansi

# Initialize colors (disable if necessary for compatibility)
Colors.disable_on_windows()

class Spinner:
    """
    Cross-platform animated spinner to indicate background processes (e.g., AI thinking).
    Now with explicit start/stop methods for better control around input prompts.
    """
    def __init__(self, message="Working"):
        self.message = message
        self.spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏" # Unicode spinner characters
        self.stop_running = True # Start in stopped state
        self.thread = None
        self._lock = Lock() # To protect stop_running and thread access

    def _spin_task(self):
        """
        The main spinning logic, run in a separate thread.
        Continuously updates the console line with spinner characters.
        """
        i = 0
        while True:
            with self._lock:
                if self.stop_running:
                    break # Exit the loop if stop is requested

            char = self.spinner_chars[i % len(self.spinner_chars)]
            # Use carriage return '\r' to overwrite the current line
            sys.stdout.write(f"\r{Colors.CYAN}{char}{Colors.END} {self.message}... ")
            sys.stdout.flush() # Ensure the output is immediately visible
            time.sleep(0.1) # Control the speed of the spinner
            i += 1
        # Clear the spinner line once stopped
        sys.stdout.write("\r" + " " * (len(self.message) + 10) + "\r")
        sys.stdout.flush()

    def start(self, message: str = None):
        """
        Starts the spinner. If already running, updates message.
        """
        with self._lock:
            if message:
                self.message = message
            if self.thread and self.thread.is_alive():
                return # Already running, just updated message
            
            self.stop_running = False
            self.thread = Thread(target=self._spin_task, daemon=True)
            self.thread.start()

    def stop(self):
        """
        Stops the spinner and waits for its thread to finish, clearing the line.
        """
        self.stop_running = True
        if self.thread:
            self.thread.join(timeout=0.5) # Give a short time for the thread to clean up

class BashAI:
    """
    Main class for the Bash.ai terminal assistant.
    Handles user input, communicates with the AI server, and executes commands.
    """
    def __init__(self, server_url: str = None):
        # Load or create configuration
        self.config = self._load_or_create_config()
        # Use provided server_url (from args) or fallback to config/default
        self.server_url = server_url or self.config.get('server_url', DEFAULT_SERVER_URL)
        self.current_dir = os.getcwd() # Get the current working directory
        
        # OS detection for platform-specific behavior
        self.is_windows = platform.system() == "Windows"
        self.is_macos = platform.system() == "Darwin"
        self.is_linux = platform.system() == "Linux"
        
        self.history = [] # Command history for interactive mode
        
        # Set up signal handlers for graceful exit (e.g., Ctrl+C)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        # Check server connection status on startup
        if not self._check_server_connection():
            print(f"{Colors.YELLOW}⚠️  Warning: Cannot connect to AI server at {self.server_url}{Colors.END}")
            print(f"{Colors.YELLOW}   Make sure the server is running and accessible.{Colors.END}")
            print(f"{Colors.YELLOW}   You can try configuring the server URL using 'bashai --configure' or 'bashai --server <URL>'{Colors.END}")

    def _signal_handler(self, signum, frame):
        """
        Handles Ctrl+C (SIGINT) gracefully, preventing abrupt exit.
        """
        self.spinner.stop() # Ensure spinner is stopped on Ctrl+C
        print(f"\n{Colors.YELLOW}Use 'exit' or 'quit' to exit properly{Colors.END}")

    def _load_or_create_config(self) -> Dict:
        """
        Loads configuration from a JSON file. If the file doesn't exist or is invalid,
        it uses default values. This is not an interactive prompt for base config.
        """
        # Define default config structure including the public Supabase details
        default_config_structure = {
            "server_url": DEFAULT_SERVER_URL,
            "max_history": 100,
            "auto_execute": False,
            "safe_mode": True,
            "jwt_token": None, # JWT will be stored here after successful login
            # Public Supabase details are now hardcoded in the script, not in the config file by default
            # "supabase_url_public": SUPABASE_URL_PUBLIC,
            # "supabase_anon_key_public": SUPABASE_ANON_KEY_PUBLIC
        }

        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, 'r') as f:
                    loaded_config = json.load(f)
                    # Merge loaded config with default settings to ensure all keys are present
                    # and allow new defaults to be introduced.
                    merged_config = {**default_config_structure, **loaded_config}
                    return merged_config
            except (json.JSONDecodeError, IOError) as e:
                print(f"{Colors.YELLOW}Warning: Could not load config from {CONFIG_PATH}. Error: {e}{Colors.END}")
                print(f"{Colors.YELLOW}Using default configuration settings.{Colors.END}")
                return default_config_structure
        else:
            # If config file doesn't exist, just return the default structure
            return default_config_structure

    def _save_config(self, config_data: Dict):
        """
        Prompts the user for initial configuration settings and saves them.
        """
        print(f"{Colors.BOLD}┌──────────────────────────────────────────────┐{Colors.END}")
        print(f"{Colors.BOLD}│          Bash.ai First-Time Setup            │{Colors.END}")
        print(f"{Colors.BOLD}└──────────────────────────────────────────────┘{Colors.END}")
        
        # Prompt for server URL
        server_url = input(f"Enter AI server URL [{DEFAULT_SERVER_URL}]: ").strip()
        if not server_url:
            server_url = DEFAULT_SERVER_URL
            
        # Prompt for auto-execute
        auto_execute_input = input("Automatically execute suggested commands? (y/N): ").strip().lower()
        auto_execute = auto_execute_input == 'y'

        # Prompt for safe mode
        safe_mode_input = input("Enable safe mode (blocks dangerous commands)? (Y/n): ").strip().lower()
        safe_mode = safe_mode_input != 'n'
            
        config = {
            "server_url": server_url,
            "max_history": 100, # Default history size
            "auto_execute": auto_execute,
            "safe_mode": safe_mode
        }
        
        try:
            with open(CONFIG_PATH, 'w') as f:
                json.dump(config, f, indent=2)
            print(f"{Colors.GREEN}Configuration saved to {CONFIG_PATH}{Colors.END}")
        except IOError as e:
            print(f"{Colors.RED}Warning: Could not save config to {CONFIG_PATH}: {e}{Colors.END}")
            
        return config

    def _check_server_connection(self) -> bool:
        """
        Checks if the AI server is accessible by making a request to its health endpoint.
        """
        try:
            response = requests.get(f"{self.server_url}/health", timeout=3)
            return response.status_code == 200 and response.json().get("status") == "healthy"
        except requests.exceptions.ConnectionError:
            return False
        except requests.exceptions.Timeout:
            return False
        except requests.RequestException: # Catch other request errors
            return False
        except json.JSONDecodeError: # If health check doesn't return JSON
            return False

    def _query_ai(self, message: str, system_prompt: str = None) -> Tuple[str, bool]:
        """
        Sends a query to the AI server and retrieves the response.
        """
        try:
            with Spinner("Thinking"): # Show spinner while waiting for AI response
                payload = {
                    "message": message,
                    "system_prompt": system_prompt,
                    "max_tokens": 1000, # Max tokens for AI response
                    "temperature": 0.7 # Creativity of AI response
                }
                
                response = requests.post(
                    f"{self.server_url}/chat",
                    json=payload,
                    timeout=60 # Increased timeout for potentially long AI generations
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("response", ""), data.get("success", False)
                else:
                    # Handle server-side errors
                    error_detail = response.json().get("detail", "Unknown server error")
                    return f"Server error: {response.status_code} - {error_detail}", False
                    
        except requests.exceptions.ConnectionError:
            return f"Connection error: Could not reach AI server at {self.server_url}. Is it running and accessible?", False
        except requests.exceptions.Timeout:
            return f"Timeout error: AI server at {self.server_url} took too long to respond. It might be overloaded or slow.", False
        except requests.RequestException as e:
            return f"Request error: {str(e)}", False
        except json.JSONDecodeError:
            return f"Invalid response from server: Could not decode JSON.", False

    def _execute_command(self, cmd: str, show_command: bool = True) -> Tuple[str, bool]:
        """
        Executes a system command safely. This function is for short-lived commands
        where the full output is expected at once. Includes AI-powered debugging on failure.
        """
        if show_command:
            print(f"{Colors.BLUE}Executing:{Colors.END} {cmd}")
            
        # Determine the actual command to run based on the detected shell
        full_cmd = cmd
        os_info = self._get_os_and_shell_info()
        if os_info['shell'] == 'powershell':
            # For PowerShell, explicitly invoke powershell.exe -Command
            # This ensures the command is parsed by PowerShell, not cmd.exe
            full_cmd = f"powershell.exe -NoProfile -Command \"{cmd}\"" # Added -NoProfile for faster startup
        elif os_info['shell'] == 'cmd' and self.is_windows:
            # For Cmd.exe, no special prefix needed, but ensure it's run via cmd.exe
            full_cmd = f"cmd.exe /c \"{cmd}\""


        # Basic safety check for dangerous commands
        dangerous_commands = ['rm -rf /', 'del /f /s /q C:\\', 'format', 'fdisk', 'mkfs']
        if self.config.get('safe_mode', True):
            # Check if any dangerous command substring is present in the command
            if any(danger in cmd.lower() for danger in dangerous_commands):
                print(f"{Colors.RED}Blocked dangerous command for safety: {cmd}{Colors.END}")
                return f"{Colors.RED}Command blocked by safe mode.{Colors.END}", False

        process = None
        try:
            with Spinner("Running"): # Show spinner while command executes
                # Use appropriate shell based on OS for subprocess execution
                shell = True # Let the OS shell interpret the command
                
                if self.is_windows:
                    # Use cmd.exe on Windows. CREATE_NO_WINDOW prevents a new console window from popping up.
                    result = subprocess.run(
                        cmd, shell=shell, capture_output=True, text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                    )
                else:
                    # Use bash/sh on Unix-like systems (Linux, macOS)
                    result = subprocess.run(
                        cmd, shell=shell, capture_output=True, text=True
                    )
                
                if result.returncode == 0:
                    # Command succeeded
                    output = result.stdout.strip() if result.stdout else "✓ Command completed successfully"
                    return output, True
                else:
                    # Command failed
                    error = result.stderr.strip() if result.stderr else f"Command failed with exit code {result.returncode}"
                    return f"{Colors.RED}Error: {error}{Colors.END}", False
                    
        except FileNotFoundError:
            return f"{Colors.RED}Error: Command not found. Make sure it's in your PATH.{Colors.END}", False
        except Exception as e:
            return f"{Colors.RED}Execution error: {str(e)}{Colors.END}", False
        finally:
            self.spinner.stop() # Final ensure spinner is stopped


    def _create_file(self, filename: str, content: str) -> bool:
        """
        Creates a file with the given content.
        """
        try:
            # Ensure parent directories exist
            Path(filename).parent.mkdir(parents=True, exist_ok=True)
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"{Colors.GREEN}✓ Created {filename}{Colors.END}")
            return True
        except Exception as e:
            print(f"{Colors.RED}Error creating {filename}: {str(e)}{Colors.END}")
            return False

    def _get_system_prompt(self) -> str:
        """
        Generates a system prompt that provides context to the AI model,
        including the current operating system, active shell, directory,
        and its contents.
        """
        os_info = self._get_os_and_shell_info()
        dir_listing = self._get_current_directory_listing()
        
        return f"""You are Bash.ai, an expert terminal assistant and code generator.
Current environment: {os_info['system']} {os_info['release']} ({os_info['machine']})
Current directory: {os_info['current_dir']}

Guidelines:
1. For terminal commands: Provide the exact command to run. Do not include explanations.
2. For code requests: Generate complete, runnable code with proper syntax. Do not include explanations.
3. Always consider the current OS when suggesting commands or generating code.
4. If asked to create files, provide the complete file content.

Respond in one of these strict formats:
- For commands: <execute>command_here</execute>
- For code: <filename>name.ext</filename><code>full_code_here</code>
- For explanations or conversational responses: Just provide the explanation text directly. Do not use any tags.

Current OS-specific command syntax:
- Windows: Use PowerShell/CMD syntax (e.g., dir, copy, del, Get-Process).
- Linux/macOS: Use bash syntax (e.g., ls, cp, rm, ps aux)."""

    def _parse_ai_response(self, response: str) -> Dict[str, Any]:
        """
        Parses the AI's response to extract all structured components.
        Returns a dictionary with 'command', 'new_files', 'edited_file', 'dependencies', 'explanation' keys.
        """
        parsed_components: Dict[str, Any] = {
            'command': None,
            'filename': None,
            'code': None
        }
        
        # Check for command tag
        if '<execute>' in response and '</execute>' in response:
            start = response.find('<execute>') + len('<execute>')
            end = response.find('</execute>')
            if start < end: # Ensure tags are correctly ordered
                result['type'] = 'command'
                result['command'] = response[start:end].strip()
                result['content'] = response # Keep full response for debugging/display if needed
            
        # Check for code tags
        elif '<filename>' in response and '<code>' in response:
            filename_start = response.find('<filename>') + len('<filename>')
            filename_end = response.find('</filename>')
            code_start = response.find('<code>') + len('<code>')
            code_end = response.find('</code>')

            if filename_start < filename_end and code_start < code_end:
                result['type'] = 'code'
                result['filename'] = response[filename_start:filename_end].strip()
                result['code'] = response[code_start:code_end].strip()
                result['content'] = response # Keep full response for debugging/display if needed
            
        return result

    def _interactive_mode(self):
        """
        Starts the interactive terminal session for Bash.ai.
        """
        os_info = self._get_os_and_shell_info()
        print(f"\n{Colors.BOLD}{Colors.CYAN}💻 Bash.ai - AI Terminal Assistant{Colors.END}")
        print(f"{Colors.CYAN}Platform: {os_info['os']} / Shell: {os_info['shell']}{Colors.END}")
        print(f"{Colors.CYAN}Directory: {self.current_dir}{Colors.END}")
        print(f"{Colors.CYAN}AI Server: {self.server_url}{Colors.END}")
        if self.jwt_token:
            print(f"{Colors.GREEN}Auth Status: Authenticated{Colors.END}")
        else:
            print(f"{Colors.YELLOW}Auth Status: Not authenticated (Limited functionality for anonymous users. Type 'login' to sign in).{Colors.END}")
        print(f"{Colors.YELLOW}Type 'help' for commands, 'exit' to quit{Colors.END}\n")

        while True:
            try:
                # Construct the prompt for the user
                prompt = f"{Colors.GREEN}bash.ai{Colors.END} {Colors.BLUE}{os.path.basename(self.current_dir)}{Colors.END}> "
                
                # Get user input using readline for history and editing if available
                if readline:
                    user_input = readline.get_line_buffer() # Get current buffer if any
                    readline.set_history_length(self.config.get('max_history', 100))
                    user_input = input(prompt).strip()
                else:
                    user_input = input(prompt).strip()
                
                if not user_input:
                    continue # Skip empty input

                # Handle built-in client commands
                if user_input.lower() in ['exit', 'quit']:
                    print(f"{Colors.CYAN}Goodbye!{Colors.END}")
                    break # Exit the loop and program
                    
                elif user_input.lower() == 'help':
                    self._show_help()
                    continue
                    
                elif user_input.lower() == 'clear':
                    os.system('cls' if self.is_windows else 'clear') # Clear screen
                    continue
                
                # Handle 'ls' for Linux/macOS and 'dir' for Windows directly
                elif user_input.lower() == 'ls' and (self.is_linux or self.is_macos):
                    output, success = self._execute_command("ls -F", show_command=False) # -F to show type
                    print(output)
                    continue
                elif user_input.lower() == 'dir' and self.is_windows:
                    output, success = self._execute_command("dir", show_command=False)
                    print(output)
                    continue
                    
                elif user_input.lower() == 'config':
                    self._show_config()
                    continue
                
                elif user_input.lower() == 'login': # New command for logging in
                    self._authenticate_user()
                    continue
                
                elif user_input.lower() == 'list': # New command to list directory contents (AI-powered version)
                    print(f"\n{Colors.CYAN}{self._get_current_directory_listing()}{Colors.END}")
                    continue
                    
                elif user_input.lower().startswith('view '): # New command to view file content
                    filename = user_input[5:].strip()
                    content = self._read_file_content(filename)
                    if content is not None:
                        print(f"\n{Colors.CYAN}Content of '{filename}':{Colors.END}")
                        print("-" * 50)
                        print(content)
                        print("-" * 50)
                    continue

                elif user_input.lower().startswith('open '): # New command to open file with default app
                    filename = user_input[5:].strip()
                    self._open_file_with_default_app(filename)
                    continue
                
                elif user_input.lower().startswith('edit '): # New command to edit a file
                    self._handle_edit(user_input)
                    continue

                elif user_input.startswith('cd '):
                    self._handle_cd(user_input[3:].strip()) # Handle change directory
                    continue
                
                # Add user input to history for readline
                self.history.append(user_input)
                # Trim history if it exceeds max_history
                if len(self.history) > self.config.get('max_history', 100):
                    self.history.pop(0)

                # Add user message to chat history for AI context
                self.chat_history.append({"role": "user", "content": user_input})
                # Trim chat history to MAX_CHAT_HISTORY_LENGTH
                if len(self.chat_history) > MAX_CHAT_HISTORY_LENGTH:
                    self.chat_history = self.chat_history[-MAX_CHAT_HISTORY_LENGTH:]

                # Query the AI server
                ai_response_raw, success = self._query_ai(user_input, self._get_system_prompt())
                
                if not success:
                    print(f"{Colors.RED}AI Error: {ai_response_raw}{Colors.END}")
                    # Add AI error to chat history
                    self.chat_history.append({"role": "assistant", "content": f"AI Error: {ai_response_raw}"})
                    continue

                # Parse the AI's response using the new generalized parser
                parsed = self._parse_ai_response(ai_response_raw)
                
                if parsed['type'] == 'command':
                    # If AI suggests a command
                    if self.config.get('auto_execute', False):
                        output, success = self._execute_command(parsed['command'])
                        print(output)
                    else:
                        # Prompt for confirmation before executing
                        confirm = input(f"\nExecute command? {Colors.YELLOW}{parsed['command']}{Colors.END} [Y/n]: ")
                        if confirm.lower() != 'n':
                            output, success = self._execute_command(parsed['command'])
                            print(output)
                        else:
                            print(f"{Colors.YELLOW}Command execution skipped.{Colors.END}")
                            
                elif parsed['type'] == 'code':
                    # If AI generates code
                    print(f"\n{Colors.PURPLE}Generated code for: {parsed['filename']}{Colors.END}")
                    print(f"{Colors.CYAN}Preview:{Colors.END}")
                    print("-" * 50)
                    # Show a preview of the code (first 500 characters)
                    print(parsed['code'][:500] + ("..." if len(parsed['code']) > 500 else ""))
                    print("-" * 50)
                    
                    confirm = input(f"\nSave to {parsed['filename']}? [Y/n]: ")
                    if confirm.lower() != 'n':
                        if self._create_file(parsed['filename'], parsed['code']):
                            # Offer to run the file after creation, if it's a known executable script type
                            if parsed['filename'].lower().endswith(('.py', '.js', '.sh', '.ps1')):
                                run_confirm = input(f"Run {parsed['filename']}? [y/N]: ")
                                if run_confirm.lower() == 'y':
                                    self._run_code_file(parsed['filename'])
                            else:
                                print(f"{Colors.YELLOW}File saved. Not a recognized executable script type for direct running.{Colors.END}")
                        else:
                            print(f"{Colors.RED}Failed to save file.{Colors.END}")
                else:
                    # If AI provides a regular explanation/conversational response
                    print(f"\n{ai_response_raw}")

            except KeyboardInterrupt:
                # Handle Ctrl+C during input
                self.spinner.stop() # Ensure spinner is stopped on Ctrl+C
                print(f"\n{Colors.YELLOW}Press Ctrl+C again or type 'exit' to quit.{Colors.END}")
            except EOFError:
                # Handle Ctrl+D (End Of File)
                self.spinner.stop() # Ensure spinner is stopped on EOF
                print(f"{Colors.CYAN}Goodbye!{Colors.END}")
                break
            except Exception as e:
                # Catch any unexpected errors
                self.spinner.stop() # Ensure spinner is stopped on unexpected error
                print(f"{Colors.RED}An unexpected error occurred: {str(e)}{Colors.END}")

    def _handle_cd(self, path: str):
        """
        Handles changing the current working directory.
        Supports '~' for home, '..' for parent, and absolute/relative paths.
        """
        try:
            if path == '~':
                path = str(Path.home()) # Expand '~' to home directory
            elif path == '..':
                path = str(Path(self.current_dir).parent) # Go up one directory
            elif not os.path.isabs(path):
                # If path is relative, join it with the current directory
                path = os.path.join(self.current_dir, path)
                
            if os.path.isdir(path):
                os.chdir(path) # Change directory
                self.current_dir = os.getcwd() # Update current_dir to the new path
                print(f"{Colors.GREEN}Changed to: {self.current_dir}{Colors.END}")
            else:
                print(f"{Colors.RED}Directory not found: {path}{Colors.END}")
        except Exception as e:
            print(f"{Colors.RED}Error changing directory: {str(e)}{Colors.END}")

    def _show_help(self):
        """
        Displays help information about Bash.ai commands and usage examples.
        """
        help_text = f"""
{Colors.BOLD}Bash.ai Commands:{Colors.END}
  help                 - Show this help message.
  exit, quit          - Exit the Bash.ai program.
  clear               - Clear the terminal screen.
  config              - Show current Bash.ai configuration.
  cd <path>           - Change the current working directory.

{Colors.BOLD}Usage Examples (Natural Language Queries):{Colors.END}
  {Colors.CYAN}list all python files in this directory{Colors.END}
  {Colors.CYAN}create a backup script for my documents folder{Colors.END}
  {Colors.CYAN}make a simple calculator in python{Colors.END}
  {Colors.CYAN}show disk usage of my home directory{Colors.END}
  {Colors.CYAN}find large files older than 30 days{Colors.END}
  {Colors.CYAN}how do I install Node.js on Ubuntu?{Colors.END}

{Colors.BOLD}Code Generation Examples:{Colors.END}
  {Colors.CYAN}make a simple web server in python using Flask{Colors.END}
  {Colors.CYAN}create a bash script to monitor CPU usage every 5 seconds{Colors.END}
  {Colors.CYAN}build a simple todo app in javascript with HTML and CSS{Colors.END}
"""
        print(help_text)

    def _show_config(self):
        """Displays the current configuration."""
        print(f"\n{Colors.BOLD}Current Bash.ai Configuration:{Colors.END}")
        for key, value in self.config.items():
            if key == "jwt_token" and value:
                display_value = f"{value[:10]}...[TRUNCATED]"
            else:
                display_value = value
            print(f"  {Colors.GREEN}{key.replace('_', ' ').title()}:{Colors.END} {display_value}")
        print(f"\nConfiguration file located at: {CONFIG_PATH}")
        print(f"\n{Colors.BOLD}Hardcoded Supabase Public Details (in bashai.py):{Colors.END}")
        print(f"  {Colors.GREEN}Supabase URL Public:{Colors.END} {SUPABASE_URL_PUBLIC}")
        print(f"  {Colors.GREEN}Supabase Anon Key Public:{Colors.END} {SUPABASE_ANON_KEY_PUBLIC[:10]}...[TRUNCATED]")


def main():
    """
    Main entry point for the Bash.ai client application.
    Handles command-line arguments and starts the interactive mode or single command execution.
    """
    parser = argparse.ArgumentParser(description="Bash.ai - AI Terminal Assistant")
    # Argument to specify AI server URL, overrides config
    parser.add_argument('--server', '-s', help='AI server URL (e.g., http://localhost:8000)', default=None)
    # Argument to show current configuration
    parser.add_argument('--config', '-c', help='Show current configuration and exit', action='store_true')
    # Argument to force configuration prompt (for first-time setup or re-configuration)
    parser.add_argument('--configure', help='Force interactive configuration prompt (currently just saves existing config)', action='store_true')
    # Positional argument for single command execution
    parser.add_argument('command', nargs='*', help='Command to execute directly (e.g., "bashai list files")')
    
    args = parser.parse_args()
    
    ai = BashAI(server_url=args.server)

    # If --configure is used, just save the current config to disk
    # This acts as a "refresh" or "write defaults if not exist" behavior
    if args.configure:
        ai._save_config(ai.config) 
        print(f"{Colors.GREEN}Configuration refreshed/saved based on defaults and arguments.{Colors.END}")
        return
    
    if args.config:
        ai._show_config()
        return
        
    if args.command:
        # Single command mode: join all arguments into one string and query AI
        command_query = ' '.join(args.command)
        print(f"{Colors.BLUE}Querying AI for: '{command_query}'{Colors.END}")
        ai_response, success = ai._query_ai(command_query, ai._get_system_prompt())
        
        if not success:
            print(f"{Colors.RED}AI Error: {ai_response_raw}{Colors.END}")
            return

        parsed = ai._parse_ai_response(ai_response_raw)

        # In single command mode, we print, but don't save/execute automatically
        if parsed['dependencies']:
            print(f"\n{Colors.YELLOW}Suggested dependencies: {parsed['dependencies']}{Colors.END}")

        if parsed['new_files']:
            print(f"\n{Colors.PURPLE}AI generated the following file(s):{Colors.END}")
            for file_info in parsed['new_files']:
                print(f"\n{Colors.CYAN}--- {file_info['filename']} ---{Colors.END}")
                print(file_info['code'])
                print(f"{Colors.CYAN}--------------------{Colors.END}")
            print(f"{Colors.YELLOW}In single command mode, files are not automatically saved. Use interactive mode (just run 'bashai') to save them.{Colors.END}")
        
        elif parsed['edited_file']:
            print(f"\n{Colors.PURPLE}AI suggests edited code for: {parsed['edited_file']['filename']}{Colors.END}")
            print(f"{Colors.CYAN}Preview:{Colors.END}")
            print("-" * 50)
            print(parsed['edited_file']['code'][:500] + ("..." if len(parsed['edited_file']['code']) > 500 else ""))
            print("-" * 50)
            print(f"{Colors.YELLOW}In single command mode, file changes are not automatically saved. Use interactive mode (just run 'bashai') to apply edits.{Colors.END}")

        elif parsed['command']:
            print(f"\n{Colors.PURPLE}AI suggests command:{Colors.END} {parsed['command']}{Colors.END}")
            # In single command mode, we just print the command, not execute
            print(f"{Colors.YELLOW}In single command mode, commands are not automatically executed.{Colors.END}")
        
        elif parsed['explanation']:
            print(f"\n{parsed['explanation']}")

    else:
        # Interactive mode if no command arguments are provided
        ai._interactive_mode()

if __name__ == "__main__":
    main()
