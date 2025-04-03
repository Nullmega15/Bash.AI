#!/usr/bin/env python3
"""
Bash.ai - Smart & Affordable CLI Assistant
Uses Claude Haiku ($0.25/million tokens) with local execution
"""

import os
import subprocess
import json
import webbrowser
from pathlib import Path
import anthropic

# Configuration
CONFIG_PATH = Path.home() / ".bashai_config.json"
MODEL = "claude-3-haiku-20240307"  # Fast & affordable ($0.25/M tokens)

class BashAI:
    def __init__(self):
        self.config = self._load_config()
        self.client = anthropic.Anthropic(api_key=self.config['api_key'])
        self.current_dir = os.getcwd()
        self.is_windows = os.name == 'nt'

    def _load_config(self):
        """Load or create config with affordable defaults"""
        default_config = {
            "api_key": "",
            "model": MODEL,
            "max_cost": 0.10,  # Max $ per session
        }

        if CONFIG_PATH.exists():
            with open(CONFIG_PATH) as f:
                return {**default_config, **json.load(f)}
        
        print("┌──────────────────────────────────────────────┐")
        print("│          Bash.ai Budget Setup ($0.25/M)      │")
        print("└──────────────────────────────────────────────┘")
        api_key = input("Enter Anthropic API key (get free credits at console.anthropic.com): ").strip()
        config = {**default_config, "api_key": api_key}
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f)
        return config

    def _try_local(self, cmd: str) -> Tuple[str, bool]:
        """Try executing locally before using AI"""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            return (result.stdout, True)
        except subprocess.CalledProcessError as e:
            return (e.stderr, False)

    def smart_execute(self, request: str) -> str:
        """Smart execution pipeline: Local -> AI -> Web Search"""
        # First try local execution if it's a simple command
        if len(request.split()) < 4:  # Simple commands like "ls -l"
            output, success = self._try_local(request)
            if success:
                return output

        # Get AI suggestion (cheap Haiku model)
        response = self.client.messages.create(
            model=MODEL,
            max_tokens=400,
            messages=[{
                "role": "user",
                "content": f"""Request: {request}
                Current dir: {self.current_dir}
                OS: {"Windows" if self.is_windows else "Linux"}"""
            }],
            system="Respond ONLY with the command to execute in <execute> tags"
        )

        if "<execute>" not in response.content[0].text:
            return response.content[0].text

        cmd = response.content[0].text.split("<execute>")[1].split("</execute>")[0].strip()
        output, success = self._try_local(cmd)

        if not success:
            if input(f"Failed: {output}\nSearch web? [y/N] ").lower() == 'y':
                webbrowser.open(f"https://www.google.com/search?q={request.replace(' ', '+')}+site:stackoverflow.com")
        
        return output if success else f"Failed. Try: {cmd}"

    def start_interactive(self):
        """Budget-friendly interactive session"""
        print(f"\n💡 Bash.ai [Haiku Mode] (${MODEL} costs)")
        print("Type requests - I'll try local execution first\n")
        
        while True:
            try:
                user_input = input("bash.ai> ").strip()
                if user_input.lower() in ['exit', 'quit']:
                    break

                print(f"\n{self.smart_execute(user_input)}\n")

            except KeyboardInterrupt:
                print("\nUse 'exit' to quit")
            except Exception as e:
                print(f"Error: {str(e)}")

if __name__ == "__main__":
    ai = BashAI()
    ai.start_interactive()
