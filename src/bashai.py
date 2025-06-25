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

# --- Hardcoded Defaults (User-Friendly) ---
# These are the *default* values. Users can still override the server URL with --server.
# The Supabase public URL and Anon Key are safe to be in client code.
DEFAULT_SERVER_URL = "http://84.247.164.54:8000/" # Default AI server URL

# IMPORTANT: Replace these with your actual Supabase Project URL and Anon Key.
# It's recommended to set them as environment variables (e.g., in your shell profile)
# for easier management, but hardcoding here is also acceptable as they are public keys.
SUPABASE_URL_PUBLIC = os.getenv("SUPABASE_URL_PUBLIC", "https://modualolzuqetjpfigsq.supabase.co")
SUPABASE_ANON_KEY_PUBLIC = os.getenv("SUPABASE_ANON_KEY_PUBLIC", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1vZHVhbG9senVxZXRqcGZpZ3NxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDkxNDg2MDIsImV4cCI6MjA2NDcyNDYwMn0.lWKw1dgbJsKvo8aGXofNIsN7iAi6uFn1G8FgeSbGu2s")

# Max file size to display in 'view' command or send to AI for analysis (in bytes)
MAX_FILE_CONTENT_SIZE = 10 * 1024 # 10 KB

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
    """
    def __init__(self, message="Working"):
        self.message = message
        self.spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏" # Unicode spinner characters
        self.stop_running = False
        self.thread = None

    def spin(self):
        """
        The main spinning logic, run in a separate thread.
        Continuously updates the console line with spinner characters.
        """
        i = 0
        while not self.stop_running:
            char = self.spinner_chars[i % len(self.spinner_chars)]
            # Use carriage return '\r' to overwrite the current line
            # Ensure the output uses readline-compatible wrapping if readline is active
            display_text = Colors.wrap_for_readline(f"\r{Colors.CYAN}{char}{Colors.END} {self.message}... ")
            sys.stdout.write(display_text)
            sys.stdout.flush() # Ensure the output is immediately visible
            time.sleep(0.1) # Control the speed of the spinner
            i += 1
        # Clear the spinner line once stopped
        sys.stdout.write("\r" + " " * (len(self.message) + 10) + "\r")
        sys.stdout.flush()

    def __enter__(self):
        """
        Context manager entry point. Starts the spinner thread.
        """
        self.stop_running = False
        self.thread = Thread(target=self.spin, daemon=True) # Daemon thread exits with main program
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit point. Stops the spinner thread and waits for it to finish.
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
        self.supabase_client: Optional[Client] = None # Supabase client instance
        self.jwt_token: Optional[str] = None # User's JWT token

        # Initialize Supabase client and attempt to authenticate
        self._init_supabase()
        
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
        print(f"\n{Colors.YELLOW}Use 'exit' or 'quit' to exit properly{Colors.END}")

    def _init_supabase(self):
        """
        Initializes the Supabase client and attempts to authenticate the user.
        """
        if SUPABASE_URL_PUBLIC == "YOUR_SUPABASE_URL_PUBLIC_HERE" or SUPABASE_ANON_KEY_PUBLIC == "YOUR_SUPABASE_ANON_KEY_PUBLIC_HERE":
            print(f"{Colors.RED}Error: Supabase public URL or anon key is not configured in bashai.py.{Colors.END}")
            print(f"{Colors.YELLOW}Please replace 'YOUR_SUPABASE_URL_PUBLIC_HERE' and 'YOUR_SUPABASE_ANON_KEY_PUBLIC_HERE' in bashai.py.{Colors.END}")
            self.supabase_client = None
            self.jwt_token = None
            return

        try:
            self.supabase_client = create_client(SUPABASE_URL_PUBLIC, SUPABASE_ANON_KEY_PUBLIC)
            
            # Attempt to retrieve token from config first
            stored_jwt = self.config.get("jwt_token")
            if stored_jwt:
                self.jwt_token = stored_jwt
            else:
                # If no token stored, try anonymous sign-in or prompt for login
                self._authenticate_user()
                
        except Exception as e:
            print(f"{Colors.RED}Error initializing Supabase client: {e}{Colors.END}")
            self.supabase_client = None
            self.jwt_token = None

    def _authenticate_user(self):
        """
        Prompts the user to log in or sign up with Supabase, or sign in anonymously.
        Stores the JWT token upon successful authentication.
        """
        if not self.supabase_client:
            print(f"{Colors.RED}Supabase client not initialized. Cannot authenticate.{Colors.END}")
            return

        print(f"\n{Colors.BOLD}┌──────────────────────────────────────────────┐{Colors.END}")
        print(f"{Colors.BOLD}│         Supabase User Authentication         │{Colors.END}")
        print(f"{Colors.BOLD}└──────────────────────────────────────────────┘{Colors.END}")
        print(f"To unlock full features, log in or sign up with Supabase.")
        print(f"Anonymous usage will have message limits.")

        auth_choice = input("Authenticate (L)ogin, (S)ign Up, or (A)nonymously? [L/S/A]: ").strip().lower()

        try:
            session = None
            if auth_choice == 'l':
                email = input("Email: ").strip()
                password = input("Password: ").strip()
                response = self.supabase_client.auth.sign_in_with_password({"email": email, "password": password})
                session = response.session
                if session:
                    print(f"{Colors.GREEN}Successfully logged in as {email}!{Colors.END}")
                else: # Response might have an error even if session is None
                    print(f"{Colors.RED}Login failed: {response.user.email if response.user else 'Invalid credentials'}{Colors.END}")

            elif auth_choice == 's':
                email = input("Email: ").strip()
                password = input("Password: ").strip()
                response = self.supabase_client.auth.sign_up({"email": email, "password": password})
                session = response.session
                if session:
                    print(f"{Colors.GREEN}Successfully signed up! Please check your email for verification to complete your registration.{Colors.END}")
                else: # Response might have an error even if session is None
                    print(f"{Colors.RED}Sign up failed: {response.user.email if response.user else 'Could not create user'}{Colors.END}")
                    
            elif auth_choice == 'a':
                response = self.supabase_client.auth.sign_in_anonymously()
                session = response.session
                if session:
                    print(f"{Colors.GREEN}Signed in anonymously (limited features apply).{Colors.END}")
                else:
                    print(f"{Colors.RED}Anonymous sign-in failed: {response.user.email if response.user else 'Could not sign in anonymously'}{Colors.END}")
            else:
                print(f"{Colors.YELLOW}Authentication cancelled. Proceeding without full authentication.{Colors.END}")


            if session and session.access_token:
                self.jwt_token = session.access_token
                self.config["jwt_token"] = self.jwt_token # Store token in config
                self._save_config(self.config)
            else:
                self.jwt_token = None
                print(f"{Colors.YELLOW}No JWT token obtained. You may have limited access.{Colors.END}")

        except AuthApiError as e: # Catch specific Supabase auth errors
            print(f"{Colors.RED}Authentication failed: {e.message}{Colors.END}")
            self.jwt_token = None
        except Exception as e:
            print(f"{Colors.RED}An unexpected authentication error occurred: {e}{Colors.END}")
            self.jwt_token = None


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
        Saves the provided configuration dictionary to the CONFIG_PATH.
        """
        try:
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_PATH, 'w') as f:
                json.dump(config_data, f, indent=2)
            # print(f"{Colors.GREEN}Configuration saved to {CONFIG_PATH}{Colors.END}") # Too verbose
        except IOError as e:
            print(f"{Colors.RED}Warning: Could not save config to {CONFIG_PATH}: {e}{Colors.END}")
        except Exception as e:
            print(f"{Colors.RED}An unexpected error occurred while saving config: {e}{Colors.END}")

    def _get_os_and_shell_info(self) -> Dict[str, str]:
        """
        Detects the current operating system and the active shell.
        Returns a dictionary with 'os' and 'shell' keys.
        """
        os_type = platform.system()
        shell_type = "unknown"

        if os_type == "Windows":
            # Check for PowerShell by looking for PowerShell-specific env vars or process names
            if os.getenv("PSModulePath"):
                shell_type = "powershell"
            elif os.getenv("ComSpec") and "cmd.exe" in os.getenv("ComSpec").lower():
                shell_type = "cmd"
            else:
                shell_type = "cmd" # Default to cmd if not clearly PowerShell
        elif os_type == "Linux" or os_type == "Darwin": # Darwin is macOS
            shell_path = os.getenv("SHELL")
            if shell_path:
                shell_type = Path(shell_path).name # e.g., 'bash', 'zsh', 'sh'
            else:
                # Try to get parent process name, or default
                try:
                    # This is a bit more involved and OS-specific,
                    # but for basic shell detection, SHELL env var is usually enough.
                    # For more robust, would need 'psutil' or similar.
                    parent_process_name = subprocess.check_output(
                        ["ps", "-p", str(os.getppid()), "-o", "comm="], text=True
                    ).strip()
                    shell_type = parent_process_name.split('/')[-1] # e.g., 'bash', 'zsh'
                except Exception:
                    shell_type = "bash" # Fallback
        
        return {"os": os_type, "shell": shell_type}

    def _get_current_directory_listing(self) -> str:
        """
        Gets a formatted string of the current directory's contents.
        Lists files and directories separately.
        """
        try:
            items = os.listdir(self.current_dir)
            files = []
            dirs = []
            for item in items:
                item_path = Path(self.current_dir) / item
                if item_path.is_file():
                    files.append(item)
                elif item_path.is_dir():
                    dirs.append(item)
            
            listing = []
            if dirs:
                listing.append("Directories: " + ", ".join(sorted(dirs)))
            if files:
                listing.append("Files: " + ", ".join(sorted(files)))
            
            if not listing:
                return "Current directory is empty."
            
            return "Current directory contents:\n" + "\n".join(listing)
        except Exception as e:
            return f"Error getting directory contents: {e}"

    def _read_file_content(self, filepath: str) -> Optional[str]:
        """
        Reads the content of a file, handling errors and truncating if too large.
        Returns the content or None if an error occurs.
        """
        full_path = Path(self.current_dir) / filepath
        if not full_path.is_file():
            print(f"{Colors.RED}Error: File not found or not a file: {filepath}{Colors.END}")
            return None
        
        try:
            file_size = full_path.stat().st_size
            if file_size > MAX_FILE_CONTENT_SIZE:
                print(f"{Colors.YELLOW}Warning: File '{filepath}' is too large ({file_size} bytes). Displaying only the first {MAX_FILE_CONTENT_SIZE} bytes.{Colors.END}")
            
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(MAX_FILE_CONTENT_SIZE)
            
            return content
        except FileNotFoundError:
            print(f"{Colors.RED}Error: File not found: {filepath}{Colors.END}")
            return None
        except PermissionError:
            print(f"{Colors.RED}Error: Permission denied to read file: {filepath}{Colors.END}")
            return None
        except Exception as e:
            print(f"{Colors.RED}Error reading file {filepath}: {str(e)}{Colors.END}")
            return None

    def _open_file_with_default_app(self, filepath: str):
        """
        Opens a file using the operating system's default application.
        """
        full_path = Path(self.current_dir) / filepath
        if not full_path.exists():
            print(f"{Colors.RED}Error: File or directory not found: {filepath}{Colors.END}")
            return
        
        try:
            if self.is_windows:
                os.startfile(str(full_path))
            elif self.is_macos:
                subprocess.run(['open', str(full_path)], check=True)
            elif self.is_linux:
                subprocess.run(['xdg-open', str(full_path)], check=True)
            else:
                print(f"{Colors.RED}Error: 'open' command not supported on this OS: {platform.system()}{Colors.END}")
                return
            print(f"{Colors.GREEN}Opened {filepath} with default application.{Colors.END}")
        except FileNotFoundError:
            print(f"{Colors.RED}Error: Default application not found for this file type or 'open' command not available.{Colors.END}")
        except subprocess.CalledProcessError as e:
            print(f"{Colors.RED}Error opening file {filepath}: {e}{Colors.END}")
        except Exception as e:
            print(f"{Colors.RED}An unexpected error occurred while opening {filepath}: {str(e)}{Colors.END}")


    def _check_server_connection(self) -> bool:
        """
        Checks if the AI server is accessible by making a request to its health endpoint.
        """
        try:
            # Use a short timeout for health check
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
        Sends a query to the AI server and retrieves the response, including JWT.
        """
        headers = {
            "Content-Type": "application/json",
        }
        if self.jwt_token:
            headers["Authorization"] = f"Bearer {self.jwt_token}"

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
                    headers=headers, # Include headers with JWT
                    timeout=60 # Increased timeout for potentially long AI generations
                )
                
                # Check for non-200 status codes first
                if response.status_code != 200:
                    try:
                        # Attempt to parse error detail from JSON response if available
                        error_data = response.json()
                        error_detail = error_data.get("detail", f"Server responded with status {response.status_code}.")
                    except json.JSONDecodeError:
                        # If response is not JSON, use raw text (first 100 chars)
                        error_detail = f"Server responded with status {response.status_code} and non-JSON content: '{response.text[:100]}...'"
                    return f"AI Server Error ({response.status_code}): {error_detail}", False

                # If status code is 200, attempt to parse JSON
                try:
                    data = response.json()
                    return data.get("response", ""), data.get("success", False)
                except json.JSONDecodeError:
                    return f"Invalid response from AI server: Expected JSON, but got non-parseable content. Raw response: '{response.text[:100]}...'. Please check server logs.", False
                    
        except requests.exceptions.ConnectionError:
            return f"Connection error: Could not reach AI server at {self.server_url}. Is it running and accessible?", False
        except requests.exceptions.Timeout:
            return f"Timeout error: AI server at {self.server_url} took too long to respond. It might be overloaded or slow.", False
        except requests.RequestException as e:
            return f"Request error: An unexpected network error occurred: {str(e)}", False
        except Exception as e:
            return f"An unexpected error occurred during AI query: {str(e)}", False


    def _execute_command(self, cmd: str, show_command: bool = True) -> Tuple[str, bool]:
        """
        Executes a system command safely. This function is for short-lived commands
        where the full output is expected at once. Includes AI-powered debugging on failure.
        """
        if show_command:
            print(f"{Colors.BLUE}Executing:{Colors.END} {cmd}")
            
        # Basic safety check for dangerous commands
        dangerous_commands = ['rm -rf /', 'del /f /s /q C:\\', 'format', 'fdisk', 'mkfs']
        if self.config.get('safe_mode', True):
            # Check if any dangerous command substring is present in the command
            if any(danger in cmd.lower() for danger in dangerous_commands):
                print(f"{Colors.RED}Blocked dangerous command for safety: {cmd}{Colors.END}")
                return f"{Colors.RED}Command blocked by safe mode.{Colors.END}", False

        try:
            with Spinner("Running"): # Show spinner while command executes
                # Use appropriate shell based on OS for subprocess execution
                # Use text=True and universal_newlines=True to handle text streams directly
                result = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                
                if result.returncode == 0:
                    output = result.stdout.strip() if result.stdout else "✓ Command completed successfully"
                    return output, True
                else:
                    error = result.stderr.strip() if result.stderr else f"Command failed with exit code {result.returncode}"
                    print(f"{Colors.RED}Command failed (Exit Code: {result.returncode}).{Colors.END}")
                    if error:
                        print(f"{Colors.RED}Stderr:\n{error}{Colors.END}")
                    
                    debug_choice = input(f"{Colors.YELLOW}Attempt to debug this command with AI? [y/N]: ").strip().lower()
                    if debug_choice == 'y':
                        return self._debug_command_error(cmd, error)
                    else:
                        print(f"{Colors.YELLOW}Command debugging skipped.{Colors.END}")
                        return f"{Colors.RED}Command failed and debugging skipped.{Colors.END}", False
                    
        except FileNotFoundError:
            print(f"{Colors.RED}Error: Command not found. Make sure it's in your PATH.{Colors.END}")
            return f"{Colors.RED}Error: Command not found.{Colors.END}", False
        except Exception as e:
            print(f"{Colors.RED}Execution error: {str(e)}{Colors.END}")
            return f"{Colors.RED}Execution error: {str(e)}{Colors.END}", False

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
Current OS: {os_info['os']}
Current Shell: {os_info['shell']}
Current directory: {self.current_dir}
{dir_listing}

Strict Guidelines for your responses:
1.  **For Terminal Commands**: If the user asks for a command to execute, **ONLY** provide the exact command wrapped in `<execute>` tags. Do NOT include any other text, explanations, or markdown code blocks around it. **Ensure the command is perfectly tailored for the detected Current OS and Current Shell.**
    Example (for Linux/bash): `<execute>ls -l</execute>`
    Example (for Windows/powershell): `<execute>Get-ChildItem -Force</execute>`
    Example (for Windows/cmd): `<execute>dir /w</execute>`
2.  **For Code Generation (Scripts, Programs, etc.)**: If the user asks for code, you **MUST** provide the complete, runnable code inside `<filename>name.ext</filename><code>full_code_here</code>` tags. **DO NOT** provide code outside these tags, as the client will not be able to process it as a file. The `name.ext` should be a sensible filename including the appropriate extension (e.g., `script.py`, `my_app.js`, `backup.sh`).
    **IMPORTANT**: If the generated code has external dependencies (e.g., Python packages like 'flask', Node.js modules like 'express'), you **MUST** also include an `<dependencies>` tag *before* the `<filename><code>` tags. This tag should contain the exact command to install these dependencies (e.g., `pip install flask requests`, `npm install express`). If there are multiple commands, separate them with `&&`. If there are no dependencies, omit this tag.
    Example with dependencies: `<dependencies>pip install flask</dependencies><filename>website.py</filename><code>from flask import Flask\n...</code>`
    Example without dependencies: `<filename>hello.py</filename><code>print("Hello, world!")</code>`
3.  **For Debugging Code Errors**: If you are provided with code and an error message, provide EITHER:
    * An `<execute>` command to fix it (e.g., install a missing package).
    * The corrected code within `<filename>...</filename><code>...</code>` tags.
    * An explanation if no direct fix can be provided (without special tags).
    **CRITICAL**: If your suggested fix involves code, it MUST be inside `<filename><code>` tags.
4.  **For Debugging Command Errors**: If you are provided with a command and its error message (from stderr), provide EITHER:
    * A corrected `<execute>` command.
    * An `<execute>` command to install a missing tool.
    * An explanation if no direct fix can be provided (without special tags).
    **CRITICAL**: If your suggested fix is a command, it MUST be inside `<execute>` tags.
5.  **For Explanations/Conversational Responses**: If the request is not for a command or code, just provide the explanation text directly. Do NOT use any special tags.

**Failure to follow these formatting rules for commands and code (including dependencies) will result in the client not being able to understand and process your response correctly.**
"""

    def _parse_ai_response(self, response: str) -> Dict:
        """
        Parses the AI's response to identify if it's a command, code, or an explanation.
        Prioritizes <execute> tags, then markdown code blocks for commands, then code tags.
        Also extracts <dependencies> tags.
        """
        result = {
            'type': 'explanation',
            'content': response, # Default to full response as explanation
            'command': None,
            'filename': None,
            'code': None,
            'dependencies': None # New field for dependencies
        }
        
        # --- 0. Check for <dependencies> tags first (can be present with code) ---
        dependencies_pattern = re.compile(r'<dependencies>(.*?)</dependencies>', re.DOTALL)
        deps_match = dependencies_pattern.search(response)
        if deps_match:
            result['dependencies'] = deps_match.group(1).strip()
            # Remove dependencies tag from response so it doesn't interfere with other parsing
            response = dependencies_pattern.sub('', response)

        # --- 1. Check for <execute> tags (Highest Priority for commands) ---
        if '<execute>' in response and '</execute>' in response:
            start = response.find('<execute>') + len('<execute>')
            end = response.find('</execute>')
            if start < end:
                result['type'] = 'command'
                result['command'] = response[start:end].strip()
                return result # Return immediately if explicit execute tag found

        # --- 2. Check for Markdown Code Blocks (Fallback for commands) ---
        # This regex looks for ```[language]\n[content]\n```
        # It's non-greedy (.*?) and uses re.DOTALL to match across newlines
        markdown_code_block_pattern = re.compile(r'```(?:\w+)?\n(.*?)\n```', re.DOTALL)
        match = markdown_code_block_pattern.search(response)
        if match:
            extracted_command = match.group(1).strip()
            # If a markdown code block is found, treat it as a command
            result['type'] = 'command'
            result['command'] = extracted_command
            return result # Return if a markdown code block is found and treated as command

        # --- 3. Check for <filename> and <code> tags (for code generation) ---
        if '<filename>' in response and '<code>' in response:
            filename_start = response.find('<filename>') + len('<filename>')
            filename_end = response.find('</filename>')
            code_start = response.find('<code>') + len('<code>')
            code_end = response.find('</code>')

            if filename_start < filename_end and code_start < code_end:
                result['type'] = 'code'
                result['filename'] = response[filename_start:filename_end].strip()
                result['code'] = response[code_start:code_end].strip()
                # Keep full response as content for debugging/display if needed,
                # but the primary parsed elements are filename and code.
                return result

        # --- 4. Default to Explanation ---
        # If none of the above formats are matched, it's a plain explanation.
        return result

    def _read_output_stream(self, stream, output_list):
        """
        Helper function to read lines from a subprocess stream (stdout/stderr)
        and print them in real-time, also collecting them into a list.
        Reads as bytes and decodes to avoid buffering warnings.
        """
        for line_bytes in iter(stream.readline, b''):
            try:
                # Decode the bytes to string using the system's preferred encoding
                line_str = line_bytes.decode(sys.stdout.encoding, errors='replace').strip()
                output_list.append(line_str)
                # Write to stdout buffer directly to avoid issues with Python's text buffering
                sys.stdout.buffer.write((line_str + '\n').encode(sys.stdout.encoding, errors='replace'))
                sys.stdout.buffer.flush()
            except Exception as e:
                sys.stderr.buffer.write(f"Error decoding stream: {e}\n".encode(sys.stderr.encoding, errors='replace'))
                sys.stderr.buffer.flush()
        stream.close() # Ensure stream is closed when done

    def _run_code_file(self, filename: str, code_content: str, dependencies_cmd: Optional[str] = None) -> bool:
        """
        Attempts to run a generated code file based on its extension,
        displaying output in real-time and allowing the user to stop execution.
        Includes AI-powered debugging on failure.
        Now also handles proactive dependency installation.
        """
        runners = {
            '.py': 'python',
            '.js': 'node',
            '.sh': 'bash',
            '.ps1': 'powershell.exe -ExecutionPolicy Bypass -File' # Full command for PowerShell
        }
        
        ext = os.path.splitext(filename)[1].lower()
        runner_command_str = runners.get(ext)
        
        if not runner_command_str:
            print(f"{Colors.YELLOW}Don't know how to run files with extension '{ext}'.{Colors.END}")
            print(f"{Colors.YELLOW}You may need to run it manually.{Colors.END}")
            return False

        # --- Proactive Dependency Installation ---
        if dependencies_cmd:
            print(f"\n{Colors.BLUE}Dependencies suggested: {dependencies_cmd}{Colors.END}")
            confirm_install = input(f"Install these dependencies before running '{filename}'? [Y/n]: ").strip().lower()
            if confirm_install != 'n':
                print(f"{Colors.CYAN}Attempting to install dependencies...{Colors.END}")
                install_output, install_success = self._execute_command(dependencies_cmd, show_command=True)
                print(install_output)
                if not install_success:
                    print(f"{Colors.RED}Dependency installation failed. Attempting to run code anyway, but it might fail.{Colors.END}")
                    confirm_proceed = input("Proceed to run code despite dependency installation failure? [y/N]: ").strip().lower()
                    if confirm_proceed != 'y':
                        print(f"{Colors.YELLOW}Code execution aborted due to failed dependency installation.{Colors.END}")
                        return False
                else:
                    print(f"{Colors.GREEN}Dependencies installed successfully.{Colors.END}")
            else:
                print(f"{Colors.YELLOW}Dependency installation skipped. Proceeding to run code (may fail).{Colors.END}")


        # Split the runner command string into parts for subprocess.Popen
        # This handles cases like 'powershell.exe -ExecutionPolicy Bypass -File' correctly
        command_parts = runner_command_str.split() + [filename]

        print(f"{Colors.BLUE}Running code: {' '.join(command_parts)}{Colors.END}")
        print(f"{Colors.YELLOW}Output will be displayed below. To halt, type 'stop' and press Enter.{Colors.END}")

        process = None
        stdout_thread = None
        stderr_thread = None
        
        stdout_lines = []
        stderr_lines = []

        try:
            # Popen with text=False to read as bytes, then decode in threads
            process = subprocess.Popen(
                command_parts,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False, # Important: Set to False to read binary streams
                bufsize=1, # Line-buffered for performance with binary streams (Python decodes lines)
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )

            # Start threads to read stdout and stderr concurrently
            stdout_thread = Thread(target=self._read_output_stream, args=(process.stdout, stdout_lines), daemon=True)
            stdout_thread.start()

            stderr_thread = Thread(target=self._read_output_stream, args=(process.stderr, stderr_lines), daemon=True)
            stderr_thread.start()

            # Main thread waits for user input to stop or process to finish
            while process.poll() is None: # While the child process is still running
                try:
                    # Prompt for user input to stop the process
                    user_input = input(f"{Colors.CYAN} (Type 'stop' and press Enter to halt) > {Colors.END}").strip().lower()
                    if user_input == 'stop':
                        print(f"{Colors.YELLOW}Attempting to stop process...{Colors.END}")
                        process.terminate() # Send SIGTERM (or equivalent on Windows)
                        break # Exit the loop
                except EOFError: # Catch Ctrl+D
                    print(f"\n{Colors.YELLOW}EOF detected. Attempting to stop process...{Colors.END}")
                    process.terminate()
                    break
                except KeyboardInterrupt: # Catch Ctrl+C
                    print(f"\n{Colors.YELLOW}KeyboardInterrupt detected. Attempting to stop process...{Colors.END}")
                    process.terminate()
                    break
                time.sleep(0.1) # Small delay to prevent busy-waiting

        except FileNotFoundError:
            print(f"{Colors.RED}Error: The runner program ('{command_parts[0]}') for '{ext}' files was not found. Make sure it's installed and in your PATH.{Colors.END}")
            return False
        except Exception as e:
            print(f"{Colors.RED}An unexpected error occurred while trying to run the code file: {str(e)}{Colors.END}")
            if process and process.poll() is None: # If process is still running, try to terminate
                process.terminate()
            return False
        finally:
            # Ensure the process is fully terminated and resources are cleaned up
            if process:
                try:
                    # Wait for the process to terminate, with a timeout
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print(f"{Colors.RED}Process did not terminate gracefully within timeout. Killing...{Colors.END}")
                    process.kill() # Force kill if terminate fails
                
                # Ensure output reading threads are joined (wait for them to finish reading)
                if stdout_thread and stdout_thread.is_alive():
                    stdout_thread.join(timeout=1)
                if stderr_thread and stderr_thread.is_alive():
                    stderr_thread.join(timeout=1)

                # Close pipes explicitly if they are not already closed by join
                if process.stdout:
                    process.stdout.close()
                if process.stderr:
                    process.stderr.close()

        # After execution (or termination), check return code and potentially debug
        full_stdout = "\n".join(stdout_lines)
        full_stderr = "\n".join(stderr_lines)

        if process and process.returncode == 0:
            print(f"\n{Colors.GREEN}✓ Code execution completed successfully.{Colors.END}")
            if full_stdout:
                print(f"{Colors.CYAN}Output:{Colors.END}\n{full_stdout}")
            return True
        elif process and process.returncode is not None:
            print(f"\n{Colors.RED}Code execution failed (Exit Code: {process.returncode}).{Colors.END}")
            if full_stderr:
                print(f"{Colors.RED}Stderr:\n{full_stderr}{Colors.END}")

            debug_choice = input(f"{Colors.YELLOW}Attempt to debug with AI? [y/N]: ").strip().lower()
            if debug_choice == 'y':
                return self._debug_code_error(filename, code_content, full_stderr)
            else:
                print(f"{Colors.YELLOW}Code execution failed. Debugging skipped.{Colors.END}")
                return False
        else: # Process was terminated or other non-zero exit scenario
            print(f"\n{Colors.YELLOW}Code execution halted or encountered unhandled error.{Colors.END}")
            if full_stderr:
                print(f"{Colors.RED}Stderr:\n{full_stderr}{Colors.END}")
            return False

    def _debug_code_error(self, filename: str, code_content: str, error_message: str) -> bool:
        """
        Interacts with the AI to debug a code execution error.
        Returns True if fixed and successfully re-run, False otherwise.
        """
        DEBUG_ATTEMPTS = 2 # Limit debugging attempts

        print(f"\n{Colors.BOLD}{Colors.YELLOW}Attempting AI-powered debugging for {filename}...{Colors.END}")

        for attempt in range(1, DEBUG_ATTEMPTS + 1):
            print(f"\n{Colors.CYAN}--- Debugging Attempt {attempt}/{DEBUG_ATTEMPTS} ---{Colors.END}")
            
            debug_prompt = (
                f"The following code file '{filename}' was executed and failed with this error:\n"
                f"```error\n{error_message}\n```\n\n"
                f"The code content is:\n"
                f"```{os.path.splitext(filename)[1].lstrip('.')}\n{code_content}\n```\n\n"
                f"Please analyze the error. If it's a missing dependency, provide an `<execute>` command to install it. "
                f"If it's a code error, provide the corrected code within `<filename>...</filename><code>...</code>` tags. "
                f"If you cannot provide a fix, explain why (without special tags). Prioritize simple installation commands for missing dependencies."
                f"Ensure the command or code is suitable for my current OS ({self._get_os_and_shell_info()['os']}) and shell ({self._get_os_and_shell_info()['shell']})."
            )

            ai_response_raw, success = self._query_ai(debug_prompt, self._get_system_prompt())

            if not success:
                print(f"{Colors.RED}AI Debugging Error: {ai_response_raw}{Colors.END}")
                continue

            parsed_debug_response = self._parse_ai_response(ai_response_raw)

            if parsed_debug_response['type'] == 'command' and parsed_debug_response['command']:
                fix_command = parsed_debug_response['command']
                print(f"\n{Colors.BLUE}AI suggests a fix command:{Colors.END} {fix_command}")
                confirm_fix = input("Execute this fix? [y/N]: ").strip().lower()
                if confirm_fix == 'y':
                    fix_output, fix_success = self._execute_command(fix_command, show_command=True) # Show execution
                    print(fix_output)
                    if fix_success:
                        print(f"{Colors.GREEN}Fix command executed successfully.{Colors.END}")
                        # Offer to re-run the original code after the fix
                        rerun_choice = input(f"Attempt to re-run '{filename}' after applying fix? [y/N]: ").strip().lower()
                        if rerun_choice == 'y':
                            print(f"{Colors.CYAN}Re-running original code after fix...{Colors.END}")
                            # Correctly call _run_code_file (not _execute_code_after_fix)
                            # Pass original code_content as that's what we're fixing for
                            if self._run_code_file(filename, code_content): # No deps needed on rerun as they should be installed
                                return True # Successfully fixed and re-ran
                            else:
                                print(f"{Colors.YELLOW}Re-run failed even after fix. Trying next debug attempt if available.{Colors.END}")
                        else:
                            print(f"{Colors.YELLOW}Fix applied, but re-run skipped by user.{Colors.END}")
                            return False # User chose not to re-run
                    else:
                        print(f"{Colors.RED}Fix command failed to execute successfully.{Colors.END}")
                else:
                    print(f"{Colors.YELLOW}Fix execution skipped by user.{Colors.END}")
                    return False # User opted out of fix

            elif parsed_debug_response['type'] == 'code' and parsed_debug_response['code']:
                fixed_code = parsed_debug_response['code']
                print(f"\n{Colors.BLUE}AI suggests corrected code for {filename}:{Colors.END}")
                print("-" * 50)
                print(fixed_code[:500] + ("..." if len(fixed_code) > 500 else ""))
                print("-" * 50)
                
                confirm_save = input("Save corrected code to file? [y/N]: ").strip().lower()
                if confirm_save == 'y':
                    if self._create_file(filename, fixed_code):
                        print(f"{Colors.GREEN}Corrected code saved to {filename}.{Colors.END}")
                        rerun_choice = input(f"Attempt to re-run '{filename}' with corrected code? [y/N]: ").strip().lower()
                        if rerun_choice == 'y':
                            print(f"{Colors.CYAN}Re-running code with AI-suggested corrections...{Colors.END}")
                            if self._run_code_file(filename, fixed_code): # Re-run with new content
                                return True # Successfully fixed and re-ran
                            else:
                                print(f"{Colors.YELLOW}Re-run failed even with corrected code. Trying next debug attempt if available.{Colors.END}")
                        else:
                            print(f"{Colors.YELLOW}Corrected code saved, but re-run skipped by user.{Colors.END}")
                            return False # User chose not to re-run
                    else:
                        print(f"{Colors.RED}Failed to save corrected code.{Colors.END}")
                else:
                    print(f"{Colors.YELLOW}Saving corrected code skipped by user.{Colors.END}")
                    return False

            else:
                # AI provided an explanation or couldn't provide a direct fix
                print(f"\n{Colors.YELLOW}AI Debugging Suggestion:{Colors.END}")
                print(ai_response_raw)
                if attempt < DEBUG_ATTEMPTS:
                    retry_choice = input("Attempt another AI debugging pass? [y/N]: ").strip().lower()
                    if retry_choice != 'y':
                        print(f"{Colors.YELLOW}Debugging aborted by user.{Colors.END}")
                        return False
                else:
                    print(f"{Colors.RED}AI could not provide a suitable fix after {DEBUG_ATTEMPTS} attempts.{Colors.END}")
                    print(f"{Colors.RED}Manual intervention may be required.{Colors.END}")
                    return False

        return False # If loop finishes without a successful fix and re-run


    def _debug_command_error(self, command: str, error_message: str) -> Tuple[str, bool]:
        """
        Interacts with the AI to debug a failed command.
        Returns the new command and success status, or original error and False.
        """
        DEBUG_ATTEMPTS = 2 # Limit debugging attempts for commands

        print(f"\n{Colors.BOLD}{Colors.YELLOW}Attempting AI-powered debugging for command...{Colors.END}")

        for attempt in range(1, DEBUG_ATTEMPTS + 1):
            print(f"\n{Colors.CYAN}--- Debugging Attempt {attempt}/{DEBUG_ATTEMPTS} ---{Colors.END}")
            
            debug_prompt = (
                f"The command '{command}' was executed and failed with this error:\n"
                f"```error\n{error_message}\n```\n\n"
                f"Please analyze the error. Provide EITHER:\n"
                f"1. A corrected command to execute within `<execute>` tags (e.g., if syntax was wrong or arguments were missing).\n"
                f"2. A command to install a missing tool within `<execute>` tags (e.g., `sudo apt install tool-name`, `pip install package-name`).\n"
                f"3. An explanation if you cannot provide a direct command fix (without special tags).\n"
                f"Ensure the command is suitable for my current OS ({self._get_os_and_shell_info()['os']}) and shell ({self._get_os_and_shell_info()['shell']})."
                f"**CRITICAL**: If your suggested fix is a command, it MUST be inside `<execute>` tags."
            )

            ai_response_raw, success = self._query_ai(debug_prompt, self._get_system_prompt())

            if not success:
                print(f"{Colors.RED}AI Debugging Error: {ai_response_raw}{Colors.END}")
                continue # Try next attempt

            parsed_debug_response = self._parse_ai_response(ai_response_raw)

            if parsed_debug_response['type'] == 'command' and parsed_debug_response['command']:
                suggested_command = parsed_debug_response['command']
                print(f"\n{Colors.BLUE}AI suggests a new command:{Colors.END} {suggested_command}")
                confirm_exec = input("Execute this suggested command? [y/N]: ").strip().lower()
                if confirm_exec == 'y':
                    output, exec_success = self._execute_command(suggested_command, show_command=True)
                    # Note: We do not recursively call _debug_command_error here,
                    # the _execute_command call itself can trigger its own debug prompt if it fails.
                    return output, exec_success # Return the result of the new command execution
                else:
                    print(f"{Colors.YELLOW}Suggested command execution skipped by user.{Colors.END}")
                    return f"{Colors.YELLOW}Command debugging skipped by user.{Colors.END}", False # User opted out
            else:
                # AI provided an explanation or couldn't provide a direct command fix
                print(f"\n{Colors.YELLOW}AI Debugging Suggestion:{Colors.END}")
                print(ai_response_raw)
                if attempt < DEBUG_ATTEMPTS:
                    retry_choice = input("Attempt another AI debugging pass? [y/N]: ").strip().lower()
                    if retry_choice != 'y':
                        print(f"{Colors.YELLOW}Command debugging aborted by user.{Colors.END}")
                        return f"{Colors.YELLOW}Command debugging aborted by user.{Colors.END}", False
                else:
                    print(f"{Colors.RED}AI could not provide a suitable fix for the command after {DEBUG_ATTEMPTS} attempts.{Colors.END}")
                    print(f"{Colors.RED}Manual intervention may be required.{Colors.END}")
                    return f"{Colors.RED}Command failed and AI could not debug.{Colors.END}", False

        return f"{Colors.RED}Command failed and AI could not debug after multiple attempts.{Colors.END}", False # Fallback if all attempts fail

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
                # Apply readline-specific wrapping to the prompt string
                prompt = Colors.wrap_for_readline(
                    f"{Colors.GREEN}bash.ai{Colors.END} {Colors.BLUE}{os.path.basename(self.current_dir)}{Colors.END}> "
                )
                
                # Get user input. input() itself handles the readline integration if available.
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
                    
                elif user_input.lower() == 'config':
                    self._show_config()
                    continue
                
                elif user_input.lower() == 'login': # New command for logging in
                    self._authenticate_user()
                    continue
                
                elif user_input.lower() == 'list': # New command to list directory contents
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

                elif user_input.startswith('cd '):
                    self._handle_cd(user_input[3:].strip()) # Handle change directory
                    continue

                # Add user input to history
                self.history.append(user_input)
                # Trim history if it exceeds max_history
                if len(self.history) > self.config.get('max_history', 100):
                    self.history.pop(0)

                # Query the AI server
                ai_response_raw, success = self._query_ai(user_input, self._get_system_prompt())
                
                if not success:
                    print(f"{Colors.RED}AI Error: {ai_response_raw}{Colors.END}")
                    continue

                # Parse the AI's response
                parsed = self._parse_ai_response(ai_response_raw)
                
                if parsed['type'] == 'command':
                    # If AI suggests a command
                    if self.config.get('auto_execute', False):
                        # Auto-execute if enabled in config
                        output, success = self._execute_command(parsed['command'])
                        print(output) # Print output directly here
                    else:
                        # Prompt for confirmation before executing
                        confirm = input(f"\nExecute command? {Colors.YELLOW}{parsed['command']}{Colors.END} [Y/n]: ")
                        if confirm.lower() != 'n':
                            output, success = self._execute_command(parsed['command'])
                            print(output) # Print output directly here
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
                                    # Pass code_content and new dependencies to _run_code_file for proactive install
                                    self._run_code_file(parsed['filename'], parsed['code'], parsed['dependencies'])
                            else:
                                print(f"{Colors.YELLOW}File saved. Not a recognized executable script type for direct running.{Colors.END}")
                        else:
                            print(f"{Colors.RED}Failed to save file.{Colors.END}")
                else:
                    # If AI provides a regular explanation/conversational response
                    print(f"\n{ai_response_raw}")

            except KeyboardInterrupt:
                # Handle Ctrl+C during input
                print(f"\n{Colors.YELLOW}Press Ctrl+C again or type 'exit' to quit.{Colors.END}")
            except EOFError:
                # Handle Ctrl+D (End Of File)
                print(f"\n{Colors.CYAN}Goodbye!{Colors.END}")
                break
            except Exception as e:
                # Catch any unexpected errors
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
        """Displays help message for the Bash.ai client."""
        print(f"\n{Colors.BOLD}Bash.ai Client Commands:{Colors.END}")
        print(f"  {Colors.GREEN}exit / quit{Colors.END} - Exit the Bash.ai assistant.")
        print(f"  {Colors.GREEN}clear{Colors.END}     - Clear the terminal screen.")
        print(f"  {Colors.GREEN}cd <path>{Colors.END} - Change the current working directory.")
        print(f"  {Colors.GREEN}list{Colors.END}      - List contents of the current directory.")
        print(f"  {Colors.GREEN}view <file>{Colors.END} - Display content of a specified file.")
        print(f"  {Colors.GREEN}open <file/dir>{Colors.END} - Open a file or directory with its default application.")
        print(f"  {Colors.GREEN}config{Colors.END}    - Show current configuration settings.")
        print(f"  {Colors.GREEN}login{Colors.END}     - Authenticate with Supabase (for full features).")
        print(f"\n{Colors.BOLD}AI Interaction:{Colors.END}")
        print(f"  Type any natural language query, e.g.:")
        print(f"  - \"list all python files\"")
        print(f"  - \"create a backup script for my documents\"")
        print(f"  - \"how to check disk usage?\"")
        print(f"\n{Colors.YELLOW}Note: Commands suggested by AI will prompt for confirmation unless auto-execute is enabled.{Colors.END}")
        print(f"{Colors.YELLOW}New: If generated code or commands fail, Bash.ai can attempt to debug it with AI assistance.{Colors.END}")
        print(f"{Colors.YELLOW}New: Bash.ai can now proactively offer to install dependencies for generated code.{Colors.END}")


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
        
        if success:
            parsed = ai._parse_ai_response(ai_response)
            if parsed['type'] == 'command':
                # Execute the command directly in single command mode
                output, _ = ai._execute_command(parsed['command'])
                print(output)
            elif parsed['type'] == 'code':
                # In single command mode, just print code, don't save/run automatically
                print(f"\n{Colors.PURPLE}Generated code for: {parsed['filename']}{Colors.END}")
                print(parsed['code'])
                # If there are dependencies in single command mode, also print them
                if parsed['dependencies']:
                    print(f"\n{Colors.YELLOW}Suggested dependencies: {parsed['dependencies']}{Colors.END}")
            else:
                # Print explanation
                print(ai_response)
        else:
            print(f"{Colors.RED}Error: {ai_response}{Colors.END}")
    else:
        # Interactive mode if no command arguments are provided
        ai._interactive_mode()

if __name__ == "__main__":
    main()
