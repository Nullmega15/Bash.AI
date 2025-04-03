import sys
import time
from threading import Thread
from queue import Queue

# Add to imports at the top of the file
class Spinner:
    """Animated spinner for command execution"""
    def __init__(self):
        self.spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        self.stop_running = False
        self.queue = Queue()

    def spin(self):
        """Show spinner animation"""
        i = 0
        while not self.stop_running:
            sys.stdout.write(f"\r{self.spinner_chars[i]} Working... ")
            sys.stdout.flush()
            time.sleep(0.1)
            i = (i + 1) % len(self.spinner_chars)
        sys.stdout.write("\r" + " " * 20 + "\r")  # Clear line

    def __enter__(self):
        """Start spinner in context manager"""
        self.stop_running = False
        Thread(target=self.spin, daemon=True).start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop spinner"""
        self.stop_running = True
        time.sleep(0.2)  # Let last spin finish
        sys.stdout.write("\r" + " " * 20 + "\r")  # Clear line

# Modify the execute_command method:
def execute_command(self, cmd: str) -> Tuple[str, bool]:
    """Execute command with progress spinner"""
    with Spinner():
        try:
            if self.is_windows:
                cmd = f'cmd /c "{cmd}"' if ' ' in cmd else f'cmd /c {cmd}'
            
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

# Modify the generate_code_file method:
def generate_code_file(self, request: str) -> str:
    """Show progress while generating code"""
    with Spinner():
        response = self.client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=2000,
            messages=[{"role": "user", "content": request}]
        )
        return response.content[0].text
