# Bash.ai 🤖💻

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platforms](https://img.shields.io/badge/Windows%20%26%20Linux-Supported-green.svg)](https://github.com/Nullmega15/bash.ai)

**AI-powered command-line assistant** that understands natural language and executes commands on both Windows and Linux.

![Demo](docs/demo.gif)

## 🚀 Installation

### Linux (Debian/Ubuntu)
```bash
# 1. Install dependencies
sudo apt update && sudo apt install -y python3 python3-pip git

# 2. Clone repository
git clone https://github.com/Nullmega15/bash.ai.git
cd bash.ai

# 3. Install Python packages
pip3 install -r requirements.txt --user

# 4. Run it (use python3 explicitly)
python3 src/bashai.py
```

### Windows (PowerShell)
```powershell
# 1. Clone repository
git clone https://github.com/Nullmega15/bash.ai.git
cd bash.ai

# 2. Install dependencies
python -m pip install -r requirements.txt

# 3. Run it
python src\bashai.py
```

### macOS
```bash
# 1. Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Install dependencies
brew install python git

# 3. Follow Linux instructions from step 2 onward
```

## 🔑 First-Time Setup
1. Get your Anthropic API key
2. Paste it when prompted during first run

Configuration saved to:
- Linux/macOS: `~/.bashai_config.json`
- Windows: `%USERPROFILE%\.bashai_config.json`

## 💡 Usage Examples

### Basic Commands
```bash
bash.ai> list all python files in this folder
bash.ai> create a new directory called projects
bash.ai> show disk usage
```

### Code Generation
```bash
bash.ai> make a python calculator
bash.ai> create a bash script to backup my home directory
```

## 🛠️ Troubleshooting

### Linux Errors
```bash
# If you see "import: command not found":
python3 src/bashai.py  # Use python3 explicitly

# If missing dependencies:
sudo apt install python3-venv  # For Ubuntu/Debian
```

### Windows Errors
```powershell
# If Python not found:
winget install Python.Python.3

# If permission denied:
Start-Process PowerShell -Verb RunAs  # Run as admin
```

### Common Fixes

#### Python path issues:
```bash
which python3  # Verify Python installation
```

#### Reset configuration:
```bash
rm ~/.bashai_config.json  # Linux/macOS
del %USERPROFILE%\.bashai_config.json  # Windows
```

## 🌟 Features
- Natural language understanding - "Delete all temp files" → `rm -rf /tmp/*`
- Auto-complete suggestions - Press Tab for command ideas
- Cross-platform - Works on Windows, Linux, and macOS
- Code generation - Creates ready-to-run scripts

## 📜 License
MIT © Nullmega_
