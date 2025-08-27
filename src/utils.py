# src/utils.py
import platform
from typing import List

def is_windows() -> bool:
    """
    Checks if the current operating system is Windows.
    """
    return platform.system().lower() == 'windows'

def is_linux() -> bool:
    """
    Checks if the current operating system is Linux.
    """
    return platform.system().lower() == 'linux'

def is_macos() -> bool:
    """
    Checks if the current operating system is macOS.
    """
    return platform.system().lower() == 'darwin' # macOS is 'Darwin' in platform.system()

def format_commands(cmds: List[str]) -> str:
    """
    Formats a list of commands into a numbered string for display.
    Example:
    1. command_one
    2. command_two
    """
    # Using enumerate to get index and command, then format each line
    return "\n".join(f"{i+1}. {cmd}" for i, cmd in enumerate(cmds))

# You can add more utility functions here as needed,
# for example, functions to check for specific installed tools,
# or to process file paths in a cross-platform way.
