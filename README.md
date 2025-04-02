# Bash.ai 2.0 🤖⚡

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Windows/Linux](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey)](https://github.com/Nullmega15/bash.ai)

**The self-healing CLI assistant** that fixes errors automatically and finds solutions online when stuck.

![Demo](https://github.com/Nullmega15/bash.ai/blob/main/docs/retry-demo.gif?raw=true)

## 🚀 Features

- **Auto-Retry System**: Attempts commands up to 3 times with AI-suggested fixes
- **Web Search Integration**: Finds solutions on Stack Overflow/Microsoft Docs when errors persist
- **OS-Aware Execution**: Uses native commands for Windows (`cmd`) and Linux (`bash`)
- **Smart Error Recovery**: Analyzes errors and suggests corrected commands
- **Interactive Chat**: Natural language interface with context awareness

## 📦 Installation

### Windows (PowerShell)
```powershell
# Clone repository
git clone https://github.com/Nullmega15/bash.ai.git
cd bash.ai

# Install dependencies
python -m pip install anthropic webbrowser

# Run interactive mode
python src\bashai.py
```

### Linux/macOS
```bash
# Install dependencies
sudo apt-get install python3 python3-pip git  # Debian/Ubuntu

# Clone and run
git clone https://github.com/Nullmega15/bash.ai.git
cd bash.ai
pip3 install -r requirements.txt
./src/bashai.py
```

## 🛠️ Usage Examples

### Basic Command Execution
```bash
bash.ai> create log files
✅ Executing: touch log1.txt log2.txt
```

### Auto-Retry Demonstration
```bash
bash.ai> delete protected folder
⚠️ Attempt 1: rm -rf /protected → Permission denied
🔄 Retry 2: sudo rm -rf /protected → Success
```

### Web Search Integration
```bash
bash.ai> mount encrypted drive
❌ Error: mount: unknown filesystem type 'crypto_LUKS'
🔍 Opening: https://stackoverflow.com/search?q=mount+crypto_LUKS...
```

## 🌟 New in 2.0

| Feature     | Example                                  |
|-------------|------------------------------------------|
| Auto-Retry  | Fixes permission/typo errors automatically |
| Web Search  | [y/N] prompt to search error solutions   |
| Smart Fixes | Suggests sudo when needed on Linux       |
| Execution Log | Shows all retry attempts clearly       |

## ⚙️ Configuration

First run creates `~/.bashai_config.json`:

```json
{
  "api_key": "your_anthropic_key",
  "auto_retry": true,
  "max_retries": 3,
  "enable_web_search": true
}
```

## 📚 Documentation

- [Command Reference](docs/command_reference.md)
- [Troubleshooting Guide](docs/troubleshooting.md)
- [API Key Setup](docs/api_key_setup.md)

## 🐛 Reporting Issues

Open a GitHub Issue with:

- The command you tried
- Full error output
- OS version

💡 Pro Tip: Use `bashai --debug` for detailed error logs when troubleshooting.
