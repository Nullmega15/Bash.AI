# Bash.ai 🤖💻

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platforms](https://img.shields.io/badge/Windows%20%26%20Linux-Supported-green.svg)](https://github.com/Nullmega15/bash.ai)

**AI-powered command-line assistant** that understands natural language and executes commands on both Windows and Linux.

![Demo](docs/demo.gif)

## 🚀 Installation

### Windows
```powershell
# 1. Clone repository
git clone https://github.com/Nullmega15/bash.ai.git
cd bash.ai

# 2. Install dependencies
python -m pip install -r requirements.txt

# 3. Run (first launch will prompt for API key)
python src\bashai.py
```

### Linux (Debian/Ubuntu)
```bash
# 1. Install dependencies
sudo apt update && sudo apt install -y python3 python3-pip git

# 2. Clone repository
git clone https://github.com/Nullmega15/bash.ai.git
cd bash.ai

# 3. Install Python packages
pip3 install -r requirements.txt

# 4. Make launcher executable
chmod +x src/bashai.py

# 5. Run (first launch will prompt for API key)
./src/bashai.py
```

### Linux (One-Liner)
```bash
bash <(curl -s https://raw.githubusercontent.com/Nullmega15/bash.ai/main/scripts/linux-install.sh)
```

## 🔑 First-Time Setup

1. Get your Anthropic API key.
2. Paste it when prompted during the first run.
3. Keys are saved in `~/.bashai_config.json`.

## 🖥️ Usage Examples

| Request              | Windows Command       | Linux Command               |
|----------------------|-----------------------|-----------------------------|
| Create file          | `type nul > notes.txt`| `touch notes.txt`           |
| List files           | `dir`                 | `ls -l`                     |
| Find Python files    | `dir *.py /s`         | `find . -name "*.py"`       |
| Check disk space     | `wmic logicaldisk get`| `df -h`                     |

## 🌟 Features

- **OS-aware commands** - Auto-detects Windows/Linux.
- **Natural language** - "Show me big files" → executes proper find/dir command.
- **Interactive mode** - Chat-like interface.
- **Safe execution** - Asks confirmation for dangerous commands.

## 🐧 Linux-Specific Notes

- Requires Python 3.8+.
- Uses standard Unix commands (ls, grep, find, etc.).
- For global access:
  ```bash
  sudo ln -s $(pwd)/src/bashai.py /usr/local/bin/bashai
  ```

## 📜 License

MIT © Nullmega_
