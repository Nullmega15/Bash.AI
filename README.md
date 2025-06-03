# Bash.ai 🤖💻

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platforms](https://img.shields.io/badge/Windows%20%7C%20Linux%20%7C%20macOS-Supported-green.svg)](#installation)

**AI-powered terminal assistant** with local DeepSeek Coder model support. Natural language to code generation and command execution across Windows, Linux, and macOS.

![Demo](docs/demo.gif)

## 🌟 Features

- **🤖 Local AI Model**: Runs DeepSeek Coder locally for privacy and offline use
- **🗣️ Natural Language**: "create a backup script" → Complete working code
- **⚡ Instant Commands**: "list python files" → `find . -name "*.py"`
- **🔄 Cross-Platform**: Windows PowerShell, Linux/macOS bash support
- **💾 Code Generation**: Python, JavaScript, Bash, PowerShell scripts
- **🛡️ Safe Mode**: Prevents dangerous commands
- **📚 Smart Context**: Understands your OS and current directory

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/bash.ai.git
cd bash.ai
```

### 2. Run Setup
```bash
# All platforms
python setup.py

# Follow the prompts to:
# - Install dependencies
# - Set up AI server (optional)
# - Configure system PATH
```

### 3. Start AI Server (First Time)
```bash
# Linux/macOS
./start_server.sh

# Windows
start_server.bat

# Or manually
python server.py
```

### 4. Run Bash.ai
```bash
# Linux/macOS
./bashai

# Windows
bashai.bat

# If installed to PATH
bashai
```

## 📋 Manual Installation

### Linux (Ubuntu/Debian)
```bash
# 1. Install dependencies
sudo apt update && sudo apt install -y python3 python3-pip git

# 2. Clone and setup
git clone https://github.com/yourusername/bash.ai.git
cd bash.ai
pip3 install -r requirements.txt --user

# 3. Server dependencies (optional - for local AI)
pip3 install -r server-requirements.txt --user

# 4. Run
python3 src/bashai.py
```

### Windows (PowerShell)
```powershell
# 1. Install Python (if needed)
winget install Python.Python.3

# 2. Clone repository
git clone https://github.com/yourusername/bash.ai.git
cd bash.ai

# 3. Install dependencies
python -m pip install -r requirements.txt

# 4. Server dependencies (optional)
python -m pip install -r server-requirements.txt

# 5. Run
python src\bashai.py
```

### macOS
```bash
# 1. Install Homebrew (if needed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Install Python
brew install python git

# 3. Follow Linux instructions from step 2
```

## 🔧 Configuration

### First Run Setup
On first run, you'll be prompted to configure:
- **Server URL**: Default `http://localhost:8000` for local AI
- **Auto-execute**: Whether commands run automatically
- **Safe mode**: Blocks dangerous commands

Configuration is saved to:
- **Linux/macOS**: `~/.bashai_config.json`
- **Windows**: `%USERPROFILE%\.bashai_config.json`

### Server-Only Mode
To use without local AI server:
```bash
# Connect to remote server
bashai --server http://your-server:8000

# Or modify config file
{
  "server_url": "http://your-server:8000",
  "auto_execute": false,
  "safe_mode": true
}
```

## 💡 Usage Examples

### Terminal Commands
```bash
bash.ai> list all python files
# Executes: find . -name "*.py" -type f

bash.ai> show disk usage sorted by size  
# Executes: du -sh * | sort -hr

bash.ai> find large files over 100MB
# Executes: find . -size +100M -type f -exec ls -lh {} \;
```

### Code Generation
```bash
bash.ai> make a python web server
# Creates: server.py with complete Flask/FastAPI code

bash.ai> create backup script for my home directory
# Creates: backup.sh with rsync/robocopy commands

bash.ai> build a todo app in javascript
# Creates: todo.html with complete HTML/CSS/JS
```

### Cross-Platform Commands
```bash
# Works on all platforms with appropriate syntax
bash.ai> copy all images to backup folder
# Linux: cp *.{jpg,png,gif} backup/
# Windows: copy *.jpg backup\ && copy *.png backup\

bash.ai> check running processes
# Linux: ps aux
# Windows: Get-Process
```

## 🖥️ Server Setup

The AI server runs DeepSeek Coder locally for privacy and offline use.

### System Requirements
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 15GB free space for model
- **GPU**: Optional but recommended (CUDA support)

### Server Commands
```bash
# Start server
python server.py

# Check server status
curl http://localhost:8000/health

# View available models
curl http://localhost:8000/models
```

### GPU Support (Optional)
```bash
# For NVIDIA GPUs with CUDA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Verify GPU detection
python -c "import torch; print(f'GPU Available: {torch.cuda.is_available()}')"
```

## 🛠️ Troubleshooting

### Common Issues

#### "Model not found" Error
```bash
# Clear model cache and retry
rm -rf ~/.cache/huggingface/
python server.py
```

#### Connection Refused
```bash
# Check if server is running
curl http://localhost:8000/health

# Start server in background
nohup python server.py &

# Check server logs
tail -f server.log
```

#### Permission Denied (Linux/macOS)
```bash
# Make scripts executable
chmod +x bashai start_server.sh

# Install to user directory
pip3 install -r requirements.txt --user
```

#### Python Not Found (Windows)
```powershell
# Install Python
winget install Python.Python.3

# Or use Microsoft Store version
python3 src\bashai.py
```

### Performance Optimization

#### Server Performance
```bash
# Use GPU if available
export CUDA_VISIBLE_DEVICES=0
python server.py

# Reduce model precision for speed
export TORCH_DTYPE=float16
python server.py
```

#### Client Performance
```bash
# Reduce AI response time
# In config: {"max_tokens": 500, "temperature": 0.5}

# Enable auto-execute for faster workflow
# In config: {"auto_execute": true}
```

## 🏗️ Architecture

```
┌─────────────────┐    HTTP/JSON    ┌──────────────────┐
│   Bash.ai       │◄───────────────►│   AI Server      │
│   Client        │    Requests     │   (DeepSeek)     │
│                 │                 │                  │
│ • Terminal UI   │                 │ • Model Loading  │
│ • Command Exec  │                 │ • Text Generation│
│ • File Creation │                 │ • GPU Support    │
│ • Cross-platform│                 │ • FastAPI        │
└─────────────────┘                 └──────────────────┘
```

### Components
- **Client (`src/bashai.py`)**: Terminal interface, command execution
- **Server (`server.py`)**: AI model hosting, API endpoints
- **Setup (`setup.py`)**: Cross-platform installation
- **Config**: JSON-based configuration management

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup
```bash
# Clone for development
git clone https://github.com/yourusername/bash.ai.git
cd bash.ai

# Install in development mode
pip install -e .

# Run tests
python -m pytest tests/

# Format code
black src/ server.py
```

## 📊 Model Information

**DeepSeek Coder 6.7B Instruct**
- **Size**: ~13GB download
- **Context**: 16K tokens
- **Languages**: Python, JavaScript, Bash, PowerShell, C++, Java, etc.
- **Specialization**: Code generation, debugging, explanation

## 🔒 Privacy & Security

- **Local Processing**: AI runs entirely on your machine
- **No Data Transmission**: Code never leaves your system
- **Safe Mode**: Blocks dangerous commands by default
- **Open Source**: Full code transparency

## 📜 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [DeepSeek](https://github.com/deepseek-ai) for the excellent code model
- [Hugging Face](https://huggingface.co/) for model hosting and transformers
- [FastAPI](https://fastapi.tiangolo.com/) for the server framework

---

**Made with ❤️ by the Bash.ai team**

[![Star on GitHub](https://img.shields.io/github/stars/yourusername/bash.ai?style=social)](https://github.com/yourusername/bash.ai)
