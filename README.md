# Bash.ai 🤖💻

AI-powered terminal assistant that leverages a remote DeepSeek Coder model. Bash.ai brings natural language to code generation and command execution across Windows, Linux, and macOS—right from your terminal.

---

## 🌟 Features

- 🗣️ **Natural Language**: "create a backup script" → Complete working code
- ⚡ **Instant Commands**: "list python files" → `find . -name "*.py"`
- 🔄 **Cross-Platform**: Windows PowerShell, Linux/macOS bash support
- 💾 **Code Generation**: Python, JavaScript, Bash, PowerShell scripts
- 🛡️ **Safe Mode**: Blocks dangerous commands
- 📚 **Smart Context**: Understands your OS and current directory

---

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Nullmega15/bash.ai.git
cd bash.ai
```

### 2. Install Client Dependencies & Setup

#### Linux/macOS

If you get a "Permission denied" error, make the script executable:

```bash
chmod +x install_linux.sh
```

Then run:

```bash
./install_linux.sh
```

#### Windows (PowerShell)

Open PowerShell (as Administrator if you want to add to PATH):

```powershell
.\install_windows.ps1
```

Follow the prompts. These scripts will install dependencies and add `bashai` to your system PATH. You may need to restart your terminal after installation.

---

## 📋 Manual Installation

If you prefer not to use the install scripts, follow these steps:

### Linux (Ubuntu/Debian)

```bash
# Install dependencies
sudo apt update && sudo apt install -y python3 python3-pip git

# Clone repository & install Python dependencies
git clone https://github.com/Nullmega15/bash.ai.git
cd bash.ai
pip3 install -r requirements.txt --user

# Run client
python3 src/bashai.py
```

### Windows (PowerShell)

```powershell
# Install Python if needed (winget install Python.Python.3)
git clone https://github.com/Nullmega15/bash.ai.git
cd bash.ai
python -m pip install -r requirements.txt
python src\bashai.py
```

### macOS

```bash
# Install Homebrew if needed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

brew install python git

# Follow Linux instructions from clone step onwards
```

---

## 🔧 Configuration

On first run, you'll be prompted to configure:

- **Server URL**: Enter the Bash.ai server URL (ask your Bash.ai admin)
- **Auto-execute**: Whether commands suggested by AI run automatically (default: False)
- **Safe mode**: Blocks potentially dangerous commands (default: True)

Configuration is saved to:

- **Linux/macOS**: `~/.bashai_config.json`
- **Windows**: `%USERPROFILE%\.bashai_config.json`

You can force reconfiguration any time:

```bash
bashai --configure
```

To view current configuration:

```bash
bashai --config
```

---

## 🏁 Getting Started

Start Bash.ai from any terminal:

```bash
bashai
```

On first run, you’ll be prompted for configuration. You will need the server URL provided by the Bash.ai admin.

---

## 💡 Usage Examples

### Terminal Commands

```bash
bash.ai> list all python files
# AI executes: find . -name "*.py" -type f

bash.ai> show disk usage sorted by size
# AI executes: du -sh * | sort -hr

bash.ai> find large files over 100MB
# AI executes: find . -size +100M -type f -exec ls -lh {} \;
```

### Code Generation

```bash
bash.ai> make a python web server
# AI creates: server.py with Flask/FastAPI code

bash.ai> create backup script for my home directory
# AI creates: backup.sh with rsync/robocopy commands

bash.ai> build a todo app in javascript
# AI creates: todo.html with HTML/CSS/JS
```

### Cross-Platform Commands

```bash
bash.ai> copy all images to backup folder
# Linux: cp *.{jpg,png,gif} backup/
# Windows: copy *.jpg backup\ && copy *.png backup\

bash.ai> check running processes
# Linux: ps aux
# Windows: Get-Process
```

---

## 🔒 Privacy & Security

- **Remote Processing**: The AI model runs on a server you control (ask your admin for details)
- **Safe Mode**: Blocks dangerous commands by default
- **Open Source Client**: Inspect the code any time!

---

## 📜 License

MIT License – see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- [DeepSeek](https://deepseek.com) for the code model
- [Hugging Face](https://huggingface.co) for model hosting and transformers
- [FastAPI](https://fastapi.tiangolo.com) for the server framework

---

Made with ❤️ by the Bash.ai team
