#!/usr/bin/env python3
"""
Bash.ai Pro - AI-Powered Command Line Assistant
Uses Claude 3 Opus for smarter code generation and problem solving
"""

import os
import subprocess
import json
import webbrowser
import anthropic
from pathlib import Path
from typing import Tuple, Optional
import time

CONFIG_PATH = Path.home() / ".bashai_pro_config.json"
MAX_RETRIES = 3
AI_MODEL = "claude-3-opus-20240229"  # Most capable model

class BashAIPro:
    def __init__(self):
        self.config = self._load_or_create_config()
        self.client = anthropic.Anthropic(api_key=self.config['api_key'])
        self.current_dir = os.getcwd()
        self.os_type = self._detect_os()
        self.shell = os.environ.get('SHELL', 'bash')

    def _detect_os(self) -> str:
        """Enhanced OS detection"""
        if os.name == 'nt':
            return 'windows'
        with open('/etc/os-release') as f:
            if 'ubuntu' in f.read().lower():
                return 'ubuntu'
            if 'debian' in f.read().lower():
                return 'debian'
        return 'linux'

    def _load_or_create_config(self) -> dict:
        """Load or create configuration file"""
        default_config = {
            "api_key": "",
            "model": AI_MODEL,
            "auto_fix": True,
            "max_retries": MAX_RETRIES
        }

        try:
            if CONFIG_PATH.exists():
                with open(CONFIG_PATH) as f:
                    loaded_config = json.load(f)
                    if not loaded_config.get("api_key"):
                        raise ValueError("API key missing in config")
                    return {**default_config, **loaded_config}
            
            print("┌──────────────────────────────────────────────┐")
            print("│          Bash.ai Pro First-Time Setup        │")
            print("└──────────────────────────────────────────────┘")
            print("This version uses Claude 3 Opus for smarter assistance")
            print("Get your API key from: https://console.anthropic.com/settings/keys\n")
            
            while True:
                api_key = input("Enter your Anthropic API key: ").strip()
                if api_key.startswith("sk-") and len(api_key) > 30:
                    break
                print("Invalid key format. Should start with 'sk-' and be >30 characters")
            
            config = {**default_config, "api_key": api_key}
            with open(CONFIG_PATH, 'w') as f:
                json.dump(config, f)
            
            print("\nConfiguration saved! Starting Bash.ai Pro...\n")
            return config

        except Exception as e:
            print(f"Config error: {e}")
            return default_config

    def _get_ai_response(self, prompt: str, system: str = "") -> str:
        """Get response from Claude 3 Opus with error handling"""
        try:
            message = self.client.messages.create(
                model=self.config['model'],
                max_tokens=4000,  # Higher limit for complex tasks
                messages=[{"role": "user", "content": prompt}],
                system=system or f"""You are Bash.ai Pro, an advanced command line assistant. Rules:
1. Current OS: {self.os_type} (shell: {self.shell})
2. Current directory: {self.current_dir}
3. For code generation, provide complete, runnable solutions
4. For commands, use <execute> tags
5. Explain complex operations before executing"""
            )
            return message.content[0].text
        except Exception as e:
            return f"AI Error: {str(e)}"

    def execute_command(self, cmd: str) -> Tuple[str, bool]:
        """Execute command with enhanced error handling"""
        for attempt in range(MAX_RETRIES + 1):
            try:
                if self.os_type == 'windows':
                    cmd = f'cmd /c "{cmd}"' if ' ' in cmd else f'cmd /c {cmd}'
                
                result = subprocess.run(
                    cmd,
                    shell=True,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    executable=self.shell
                )
                return (result.stdout or "Command executed successfully", True)
                
            except subprocess.CalledProcessError as e:
                if attempt < MAX_RETRIES:
                    # Get AI-suggested fix
                    fix_prompt = f"""Command failed:
Command: {cmd}
Error: {e.stderr}
Suggest a fixed version for {self.os_type}"""
                    fixed_cmd = self._get_ai_response(fix_prompt)
                    
                    if "<execute>" in fixed_cmd:
                        cmd = fixed_cmd.split("<execute>")[1].split("</execute>")[0].strip()
                        print(f"🔄 Retry {attempt + 1}: {cmd}")
                        time.sleep(1)
                        continue
                
                return (f"Error: {e.stderr}", False)

    def generate_code(self, request: str) -> Optional[str]:
        """Generate high-quality code using Claude 3 Opus"""
        prompt = f"""Generate complete, production-ready code for:
{request}

Requirements:
1. Full implementation with error handling
2. Appropriate file name
3. Clear documentation
4. Compatible with {self.os_type}
5. Include usage examples

Respond with:
<filename>suggested_filename</filename>
<code>
# Complete code here
</code>"""
        
        response = self._get_ai_response(prompt)
        
        if "<filename>" in response and "<code>" in response:
            filename = response.split("<filename>")[1].split("</filename>")[0].strip()
            code = response.split("<code>")[1].split("</code>")[0].strip()
            
            # Validate filename
            if not filename or any(c in filename for c in ' <>:"|?*'):
                filename = f"generated_{int(time.time())}.py"
            
            # Save file
            with open(filename, 'w') as f:
                f.write(code)
            
            # Make executable if script
            if filename.endswith(('.py', '.sh')):
                os.chmod(filename, 0o755)
            
            return filename
        return None

    def start_interactive(self):
        """Enhanced interactive session with smart features"""
        print(f"\n🚀 Bash.ai Pro ({self.os_type} | {self.config['model']})")
        print(f"📂 Current directory: {self.current_dir}\n")
        
        while True:
            try:
                user_input = input("bash.ai> ").strip()
                if user_input.lower() in ['exit', 'quit']:
                    break
                if not user_input:
                    continue

                # Code generation mode
                if any(keyword in user_input.lower() for keyword in ['make', 'create', 'generate', 'write']):
                    print("\n🧠 Generating solution with Claude 3 Opus...")
                    filename = self.generate_code(user_input)
                    if filename:
                        print(f"✅ Created: {filename}")
                        if filename.endswith('.py'):
                            if input("Run this Python script? [y/N] ").lower() == 'y':
                                output, success = self.execute_command(f"python3 {filename}")
                                print(output)
                    continue

                # Normal command execution
                response = self._get_ai_response(
                    prompt=f"User request: {user_input}",
                    system=f"Respond with command to execute in <execute> tags for {self.os_type}"
                )
                
                if "<execute>" in response:
                    cmd = response.split("<execute>")[1].split("</execute>")[0].strip()
                    print(f"\n⚡ Executing: {cmd}")
                    output, success = self.execute_command(cmd)
                    print(output)
                    
                    if not success:
                        if input("\n🔍 Search web for solutions? [y/N] ").lower() == 'y':
                            query = f"{self.os_type} {output} site:stackoverflow.com OR site:github.com"
                            webbrowser.open(f"https://google.com/search?q={query.replace(' ', '+')}")
                else:
                    print(response)

            except KeyboardInterrupt:
                print("\nUse 'exit' to quit")
            except Exception as e:
                print(f"🚨 Critical error: {str(e)}")

if __name__ == "__main__":
    ai = BashAIPro()
    ai.start_interactive()
