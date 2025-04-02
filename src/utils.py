import platform
from typing import List

def is_windows() -> bool:
    return platform.system().lower() == 'windows'

def format_commands(cmds: List[str]) -> str:
    """Format commands for display"""
    return "\n".join(f"{i+1}. {cmd}" for i, cmd in enumerate(cmds))
