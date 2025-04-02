import os
import subprocess
import json
import webbrowser
import requests
from bs4 import BeautifulSoup
import anthropic
from pathlib import Path
from typing import Tuple, Optional
import time

CONFIG_PATH = Path.home() / ".bashai_config.json"
MAX_RETRIES = 3
ERROR_DB = Path.home() / ".bashai_error_db.json"

class BashAI:
    def __init__(self):
        self.config = self._load_or_create_config()
        self.client = anthropic.Anthropic(api_key=self.config['api_key'])
        self.current_dir = os.getcwd()
        self.is_windows = os.name == 'nt'
        self.error_db = self._load_error_db()
        self.session_history = []

    def _load_error_db(self) -> dict:
        """Load historical error solutions"""
        if ERROR_DB.exists():
            with open(ERROR_DB) as f:
                return json.load(f)
        return {"solutions": {}}

    def _save_error_db(self):
        """Save learned solutions"""
        with open(ERROR_DB, 'w') as f:
            json.dump(self.error_db, f)

    def _web_search(self, error: str) -> Optional[str]:
        """Search error solutions and extract top answer"""
        try:
            # 1. Search Stack Overflow
            query = f"{error} site:stackoverflow.com"
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            
            # 2. Fetch and parse results
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(search_url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 3. Extract top solution
            for result in soup.select('.g'):
                link = result.a['href']
                if 'stackoverflow.com/questions' in link:
                    answer_page = requests.get(link, headers=headers)
                    answer_soup = BeautifulSoup(answer_page.text, 'html.parser')
                    accepted_answer = answer_soup.select_one('.accepted-answer')
                    if accepted_answer:
                        code_block = accepted_answer.select_one('pre code')
                        if code_block:
                            return code_block.text.strip()
            
            # 4. Fallback to GitHub search
            query = f"{error} site:github.com"
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            response = requests.get(search_url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for result in soup.select('.g'):
                if 'github.com' in result.a['href']:
                    return f"Potential solution found at: {result.a['href']}"
                    
        except Exception as e:
            print(f"⚠️ Web search failed: {str(e)}")
        return None

    def _analyze_and_fix(self, cmd: str, error: str) -> Tuple[str, bool]:
        """Automatically find and apply fixes"""
        print(f"\n🔍 Analyzing error: {error}")
        
        # 1. Check local error database
        if error in self.error_db["solutions"]:
            fix = self.error_db["solutions"][error]
            print(f"🎯 Known solution: {fix}")
            return fix, True
        
        # 2. Search web for solutions
        web_solution = self._web_search(error)
        if web_solution:
            print(f"🌐 Web solution found:\n{web_solution}")
            
            # 3. Generate fixed command with AI
            prompt = f"""Original command failed:
Command: {cmd}
Error: {error}
Web solution: {web_solution}

Generate fixed command for {"Windows" if self.is_windows else "Linux"}.
Respond ONLY with the command in <execute> tags."""
            
            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            fixed_cmd = response.content[0].text
            if "<execute>" in fixed_cmd:
                fixed_cmd = fixed_cmd.split("<execute>")[1].split("</execute>")[0].strip()
                self.error_db["solutions"][error] = fixed_cmd
                self._save_error_db()
                return fixed_cmd, True
        
        # 4. Fallback to AI-only fix
        print("🤖 Attempting AI-generated fix...")
        prompt = f"""Original command failed:
Command: {cmd}
Error: {error}

Suggest fixed command for {"Windows" if self.is_windows else "Linux"}.
Respond ONLY with the command in <execute> tags."""
        
        response = self.client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        fixed_cmd = response.content[0].text
        if "<execute>" in fixed_cmd:
            return fixed_cmd.split("<execute>")[1].split("</execute>")[0].strip(), True
        
        return cmd, False  # Return original command if no fix found

    def execute_with_retry(self, cmd: str) -> Tuple[str, bool]:
        """Enhanced execution with auto-fixing"""
        last_error = ""
        
        for attempt in range(MAX_RETRIES + 1):
            output, success = self._execute_command(cmd)
            if success:
                return output, True
                
            last_error = output
            print(f"⚠️ Attempt {attempt + 1} failed")
            
            if attempt < MAX_RETRIES:
                fixed_cmd, is_fix = self._analyze_and_fix(cmd, last_error)
                if is_fix:
                    if input(f"Apply fix? [Y/n] '{fixed_cmd}' ").lower() != 'n':
                        cmd = fixed_cmd
                        time.sleep(1)
                        continue
            
        return last_error, False

    def _execute_command(self, cmd: str) -> Tuple[str, bool]:
        """Base command execution"""
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
            return (result.stdout or "Command executed", True)
        except subprocess.CalledProcessError as e:
            return (f"Error: {e.stderr.strip() or 'Unknown error'}", False)
        except Exception as e:
            return (f"System Error: {str(e)}", False)

    def start_interactive(self):
        """Main interactive loop"""
        print(f"\n🛠️  Bash.ai [Auto-Fix Mode] (dir: {self.current_dir})")
        print("I'll automatically find solutions when errors occur\n")
        
        while True:
            try:
                user_input = input("\nbash.ai> ").strip()
                if user_input.lower() in ['exit', 'quit']:
                    break
                if not user_input:
                    continue
                    
                self.session_history.append(user_input)
                
                # Get AI response
                response = self.client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=1000,
                    messages=[{
                        "role": "user",
                        "content": f"Request: {user_input}\nCurrent dir: {self.current_dir}"
                    }],
                    system=f"""Respond with commands in <execute> tags for {"Windows" if self.is_windows else "Linux"}"""
                )
                
                ai_response = response.content[0].text
                
                # Execute if command found
                if "<execute>" in ai_response:
                    cmd = ai_response.split("<execute>")[1].split("</execute>")[0].strip()
                    print(f"\n⚙️ Executing: {cmd}")
                    output, success = self.execute_with_retry(cmd)
                    print(output)
                    
                    if not success:
                        print("\n💡 All automatic fixes failed. Possible solutions:")
                        print(f"1. Manually try: {cmd}")
                        print("2. Check web results above")
                        print("3. Simplify your request")
                else:
                    print(ai_response)
                    
            except KeyboardInterrupt:
                print("\nUse 'exit' to quit")
            except Exception as e:
                print(f"🚨 Critical Error: {str(e)}")

if __name__ == "__main__":
    ai = BashAI()
    ai.start_interactive()
