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

# Cross-platform imports for readline (for command history and editing)
try:
    if platform.system() == "Windows":
        import pyreadline3 as readline
    else:
        import readline
except ImportError:
    readline = None # Fallback if readline is not available

# Configuration paths and defaults
# This configuration file will store the server URL and other settings
CONFIG_PATH = Path.home() / ".bashai_config.json"
DEFAULT_SERVER_URL = "http://localhost:8000/" # Default server URL

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
                    if not attr.startswith('_') and attr != 'disable_on_windows':
                        setattr(cls, attr, '')

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
            sys.stdout.write(f"\r{Colors.CYAN}{char}{Colors.END} {self.message}... ")
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
        # Use provided server_url or fallback to config/default
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
            print(f"{Colors.YELLOW}   You can configure the server URL using 'bashai --configure' or by editing {CONFIG_PATH}{Colors.END}")

    def _signal_handler(self, signum, frame):
        """
        Handles Ctrl+C (SIGINT) gracefully, preventing abrupt exit.
        """
        print(f"\n{Colors.YELLOW}Use 'exit' or 'quit' to exit properly{Colors.END}")

    def _load_or_create_config(self) -> Dict:
        """
        Loads configuration from a JSON file. If the file doesn't exist or is invalid,
        it prompts the user for initial setup and creates a new config file.
        """
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, 'r') as f:
                    # Merge loaded config with defaults to ensure all keys are present
                    loaded_config = json.load(f)
                    # Define default config structure if not already in config.py
                    default_config_structure = {
                        "server_url": DEFAULT_SERVER_URL,
                        "max_history": 100,
                        "auto_execute": False,
                        "safe_mode": True
                    }
                    # Update default_config_structure with loaded values
                    for key, value in loaded_config.items():
                        default_config_structure[key] = value
                    return default_config_structure
            except (json.JSONDecodeError, IOError) as e:
                print(f"{Colors.YELLOW}Warning: Could not load config from {CONFIG_PATH}. Error: {e}{Colors.END}")
                print(f"{Colors.YELLOW}Creating new configuration.{Colors.END}")
                # Fallback to create new config if loading fails
                return self._prompt_for_config()
        else:
            return self._prompt_for_config()

    def _prompt_for_config(self) -> Dict:
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
            # Use a short timeout for health check
            response = requests.get(f"{self.server_url}/health", timeout=3)
            return response.status_code == 200 and response.json().get("status") == "healthy"
        except requests.RequestException:
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
            return f"Connection error: Could not connect to AI server at {self.server_url}. Is it running and accessible?", False
        except requests.exceptions.Timeout:
            return f"Timeout error: AI server at {self.server_url} took too long to respond.", False
        except requests.RequestException as e:
            return f"Request error: {str(e)}", False
        except json.JSONDecodeError:
            return f"Invalid response from server: Could not decode JSON.", False

    def _execute_command(self, cmd: str, show_command: bool = True) -> Tuple[str, bool]:
        """
        Executes a system command safely. This function is for short-lived commands
        where the full output is expected at once.
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
        including the current operating system and directory.
        """
        os_info = {
            'system': platform.system(),
            'release': platform.release(),
            'machine': platform.machine(),
            'current_dir': self.current_dir
        }
        
        return f"""You are Bash.ai, an expert terminal assistant and code generator.
Current environment: {os_info['system']} {os_info['release']} ({os_info['machine']})
Current directory: {os_info['current_dir']}

Guidelines for your responses:
1.  **For Terminal Commands**: If the user asks for a command to execute, **ONLY** provide the exact command wrapped in `<execute>` tags. Do NOT include any other text, explanations, or markdown code blocks around it.
    Example: `<execute>ls -l</execute>`
    Example (Windows): `<execute>dir /w</execute>`
2.  **For Code Generation**: If the user asks for code (e.g., a script, a program), provide the complete, runnable code inside `<filename>name.ext</filename><code>full_code_here</code>` tags. Do NOT include explanations outside these tags.
3.  **For Explanations/Conversational Responses**: If the request is not for a command or code, just provide the explanation text directly. Do NOT use any special tags.

Strictly adhere to these formats. Do not deviate.

Current OS-specific command syntax:
- Windows: Use PowerShell/CMD syntax (e.g., dir, copy, del, Get-Process).
- Linux/macOS: Use bash syntax (e.g., ls, cp, rm, ps aux)."""

    def _parse_ai_response(self, response: str) -> Dict:
        """
        Parses the AI's response to identify if it's a command, code, or an explanation.
        Prioritizes <execute> tags, then markdown code blocks for commands, then code tags.
        """
        result = {
            'type': 'explanation',
            'content': response, # Default to full response as explanation
            'command': None,
            'filename': None,
            'code': None
        }
        
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
        """
        # Readline by readline to ensure real-time output
        for line_bytes in iter(stream.readline, b''):
            try:
                line_str = line_bytes.decode(sys.stdout.encoding, errors='replace').strip()
                output_list.append(line_str)
                sys.stdout.write(line_str + '\n') # Add newline back for proper display
                sys.stdout.flush()
            except Exception as e:
                # Log decoding errors but don't stop the process
                sys.stderr.write(f"Error decoding stream: {e}\n")
                sys.stderr.flush()
        stream.close() # Ensure stream is closed when done

    def _run_code_file(self, filename: str):
        """
        Attempts to run a generated code file based on its extension,
        displaying output in real-time and allowing the user to stop execution.
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
            return

        # Split the runner command string into parts for subprocess.Popen
        # This handles cases like 'powershell.exe -ExecutionPolicy Bypass -File' correctly
        command_parts = runner_command_str.split() + [filename]

        print(f"{Colors.BLUE}Running code: {' '.join(command_parts)}{Colors.END}")
        print(f"{Colors.YELLOW}Output will be displayed below. To halt, type 'stop' and press Enter.{Colors.END}")

        process = None
        stdout_thread = None
        stderr_thread = None

        try:
            # Start the subprocess
            process = subprocess.Popen(
                command_parts,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False, # We will decode manually in the thread
                bufsize=1, # Line-buffered output
                universal_newlines=False, # We handle decoding
                # Prevents a new console window from popping up on Windows
                creationflags=subprocess.CREATE_NO_WINDOW if self.is_windows and hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )

            # Lists to store output (optional, but good for debugging/post-processing)
            stdout_output_lines = []
            stderr_output_lines = []

            # Start threads to read stdout and stderr concurrently
            stdout_thread = Thread(target=self._read_output_stream, args=(process.stdout, stdout_output_lines), daemon=True)
            stdout_thread.start()

            stderr_thread = Thread(target=self._read_output_stream, args=(process.stderr, stderr_output_lines), daemon=True)
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
            return
        except Exception as e:
            print(f"{Colors.RED}An unexpected error occurred while trying to run the code file: {str(e)}{Colors.END}")
            if process and process.poll() is None: # If process is still running, try to terminate
                process.terminate()
            return
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

        # Report final status
        if process and process.returncode == 0:
            print(f"\n{Colors.GREEN}✓ Code execution completed successfully.{Colors.END}")
        elif process and process.returncode is not None: # Process finished with a non-zero exit code
            print(f"\n{Colors.RED}Code execution finished with exit code {process.returncode}.{Colors.END}")
        else: # Process was terminated by user or other means (returncode is None if killed)
            print(f"\n{Colors.YELLOW}Code execution halted by user or external signal.{Colors.END}")

    def _interactive_mode(self):
        """
        Starts the interactive terminal session for Bash.ai.
        """
        print(f"\n{Colors.BOLD}{Colors.CYAN}💻 Bash.ai - AI Terminal Assistant{Colors.END}")
        print(f"{Colors.CYAN}Platform: {platform.system()} {platform.release()}{Colors.END}")
        print(f"{Colors.CYAN}Directory: {self.current_dir}{Colors.END}")
        print(f"{Colors.CYAN}Server: {self.server_url}{Colors.END}")
        print(f"{Colors.YELLOW}Type 'help' for commands, 'exit' to quit{Colors.END}\n")

        while True:
            try:
                # Construct the prompt for the user
                prompt = f"{Colors.GREEN}bash.ai{Colors.END} {Colors.BLUE}{os.path.basename(self.current_dir)}{Colors.END}> "
                
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

    def _run_code_file(self, filename: str):
        """
        Attempts to run a generated code file based on its extension,
        displaying output in real-time and allowing the user to stop execution.
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
            return

        # Split the runner command string into parts for subprocess.Popen
        # This handles cases like 'powershell.exe -ExecutionPolicy Bypass -File' correctly
        command_parts = runner_command_str.split() + [filename]

        print(f"{Colors.BLUE}Running code: {' '.join(command_parts)}{Colors.END}")
        print(f"{Colors.YELLOW}Output will be displayed below. To halt, type 'stop' and press Enter.{Colors.END}")

        process = None
        stdout_thread = None
        stderr_thread = None

        try:
            # Start the subprocess
            process = subprocess.Popen(
                command_parts,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False, # We will decode manually in the thread
                bufsize=1, # Line-buffered output
                universal_newlines=False, # We handle decoding
                # Prevents a new console window from popping up on Windows
                creationflags=subprocess.CREATE_NO_WINDOW if self.is_windows and hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )

            # Lists to store output (optional, but good for debugging/post-processing)
            stdout_output_lines = []
            stderr_output_lines = []

            # Start threads to read stdout and stderr concurrently
            stdout_thread = Thread(target=self._read_output_stream, args=(process.stdout, stdout_output_lines), daemon=True)
            stdout_thread.start()

            stderr_thread = Thread(target=self._read_output_stream, args=(process.stderr, stderr_output_lines), daemon=True)
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
            return
        except Exception as e:
            print(f"{Colors.RED}An unexpected error occurred while trying to run the code file: {str(e)}{Colors.END}")
            if process and process.poll() is None: # If process is still running, try to terminate
                process.terminate()
            return
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

        # Report final status
        if process and process.returncode == 0:
            print(f"\n{Colors.GREEN}✓ Code execution completed successfully.{Colors.END}")
        elif process and process.returncode is not None: # Process finished with a non-zero exit code
            print(f"\n{Colors.RED}Code execution finished with exit code {process.returncode}.{Colors.END}")
        else: # Process was terminated by user or other means (returncode is None if killed)
            print(f"\n{Colors.YELLOW}Code execution halted by user or external signal.{Colors.END}")

    def _interactive_mode(self):
        """
        Starts the interactive terminal session for Bash.ai.
        """
        print(f"\n{Colors.BOLD}{Colors.CYAN}💻 Bash.ai - AI Terminal Assistant{Colors.END}")
        print(f"{Colors.CYAN}Platform: {platform.system()} {platform.release()}{Colors.END}")
        print(f"{Colors.CYAN}Directory: {self.current_dir}{Colors.END}")
        print(f"{Colors.CYAN}Server: {self.server_url}{Colors.END}")
        print(f"{Colors.YELLOW}Type 'help' for commands, 'exit' to quit{Colors.END}\n")

        while True:
            try:
                # Construct the prompt for the user
                prompt = f"{Colors.GREEN}bash.ai{Colors.END} {Colors.BLUE}{os.path.basename(self.current_dir)}{Colors.END}> "
                
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

    def _run_code_file(self, filename: str):
        """
        Attempts to run a generated code file based on its extension,
        displaying output in real-time and allowing the user to stop execution.
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
            return

        # Split the runner command string into parts for subprocess.Popen
        # This handles cases like 'powershell.exe -ExecutionPolicy Bypass -File' correctly
        command_parts = runner_command_str.split() + [filename]

        print(f"{Colors.BLUE}Running code: {' '.join(command_parts)}{Colors.END}")
        print(f"{Colors.YELLOW}Output will be displayed below. To halt, type 'stop' and press Enter.{Colors.END}")

        process = None
        stdout_thread = None
        stderr_thread = None

        try:
            # Start the subprocess
            process = subprocess.Popen(
                command_parts,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False, # We will decode manually in the thread
                bufsize=1, # Line-buffered output
                universal_newlines=False, # We handle decoding
                # Prevents a new console window from popping up on Windows
                creationflags=subprocess.CREATE_NO_WINDOW if self.is_windows and hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )

            # Lists to store output (optional, but good for debugging/post-processing)
            stdout_output_lines = []
            stderr_output_lines = []

            # Start threads to read stdout and stderr concurrently
            stdout_thread = Thread(target=self._read_output_stream, args=(process.stdout, stdout_output_lines), daemon=True)
            stdout_thread.start()

            stderr_thread = Thread(target=self._read_output_stream, args=(process.stderr, stderr_output_lines), daemon=True)
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
            return
        except Exception as e:
            print(f"{Colors.RED}An unexpected error occurred while trying to run the code file: {str(e)}{Colors.END}")
            if process and process.poll() is None: # If process is still running, try to terminate
                process.terminate()
            return
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

        # Report final status
        if process and process.returncode == 0:
            print(f"\n{Colors.GREEN}✓ Code execution completed successfully.{Colors.END}")
        elif process and process.returncode is not None: # Process finished with a non-zero exit code
            print(f"\n{Colors.RED}Code execution finished with exit code {process.returncode}.{Colors.END}")
        else: # Process was terminated by user or other means (returncode is None if killed)
            print(f"\n{Colors.YELLOW}Code execution halted by user or external signal.{Colors.END}")

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
    parser.add_argument('--configure', help='Force interactive configuration prompt', action='store_true')
    # Positional argument for single command execution
    parser.add_argument('command', nargs='*', help='Command to execute directly (e.g., "bashai list files")')
    
    args = parser.parse_args()
    
    # Initialize BashAI. If --configure is used, it will force the config prompt.
    # The server_url from args will take precedence if provided.
    ai = BashAI(server_url=args.server)

    # If --configure is used, force the configuration prompt and exit
    if args.configure:
        ai._prompt_for_config()
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

