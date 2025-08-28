Bash.ai

AI-powered terminal assistant that leverages a remote DeepSeek Coder model hosted privately. Natural language to code generation and command execution across Windows, Linux, and macOS.
🌟 Features

    🤖 Remote AI Model: Connects to a powerful AI server hosted by the Bash.ai team
    🗣️ Natural Language: "create a backup script" → Complete working code
    ⚡ Instant Commands: "list python files" → find . -name "*.py"
    🔄 Cross-Platform: Windows PowerShell, Linux/macOS bash support
    💾 Code Generation: Python, JavaScript, Bash, PowerShell scripts
    🛡️ Safe Mode: Prevents dangerous commands
    📚 Smart Context: Understands your OS and current directory

🚀 Quick Start (For End Users)
1. Clone Repository

git clone https://github.com/Nullmega15/bash.ai.git
cd bash.ai

2. Install Client Dependencies & Setup

Linux/macOS:

./install_linux.sh

Windows (PowerShell - run as Administrator if needed for PATH changes):

.\install_windows.ps1

Follow the prompts. These scripts will install client dependencies and add bashai to your system's PATH. You may need to restart your terminal after installation for PATH changes to take effect.
3. Run Bash.ai

# From any terminal
bashai

On first run, you'll be prompted to configure the AI server URL. You will need the URL of the Bash.ai AI server provided by the service administrator.
📋 Manual Client Installation (For End Users)
Linux (Ubuntu/Debian)

# 1. Install dependencies
sudo apt update && sudo apt install -y python3 python3-pip git

# 2. Clone repository
git clone https://github.com/yourusername/bash.ai.git
cd bash.ai

# 3. Install client dependencies
pip3 install -r requirements.txt --user

# 4. Run client
python3 src/bashai.py

Windows (PowerShell)

# 1. Install Python (if needed)
# Download from python.org or use winget: winget install Python.Python.3

# 2. Clone repository
git clone https://github.com/yourusername/bash.ai.git
cd bash.ai

# 3. Install client dependencies
python -m pip install -r requirements.txt

# 4. Run client
python src\bashai.py

macOS

# 1. Install Homebrew (if needed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Install Python
brew install python git

# 3. Follow Linux instructions from step 2 onwards

🔧 Configuration (For End Users)
First Run Setup

On first run of bashai, you'll be prompted to configure:

    Server URL: Crucial! Enter the URL of the Bash.ai AI server (e.g., https://your-bashai-server.com:8000)
    Auto-execute: Whether commands suggested by AI run automatically (default: False)
    Safe mode: Blocks potentially dangerous commands (default: True)

Configuration is saved to: - Linux/macOS: ~/.bashai_config.json - Windows: %USERPROFILE%\.bashai_config.json

You can also force the configuration prompt at any time:

bashai --configure

To view current configuration:

bashai --config

💡 Usage Examples
Terminal Commands

bash.ai> list all python files
# AI suggests and executes: find . -name "*.py" -type f

bash.ai> show disk usage sorted by size  
# AI suggests and executes: du -sh * | sort -hr

bash.ai> find large files over 100MB
# AI suggests and executes: find . -size +100M -type f -exec ls -lh {} \;

Code Generation

bash.ai> make a python web server
# AI creates: server.py with complete Flask/FastAPI code

bash.ai> create backup script for my home directory
# AI creates: backup.sh with rsync/robocopy commands

bash.ai> build a todo app in javascript
# AI creates: todo.html with complete HTML/CSS/JS

Cross-Platform Commands

# Works on all platforms with appropriate syntax
bash.ai> copy all images to backup folder
# Linux: cp *.{jpg,png,gif} backup/
# Windows: copy *.jpg backup\ && copy *.png backup\

bash.ai> check running processes
# Linux: ps aux
# Windows: Get-Process

🖥️ Server Setup (For Bash.ai Service Providers)

This section is for those who are deploying and managing the private Bash.ai AI server.
Server Files

The server-side code is located in server.py, server-requirements.txt, start_server.sh, and start_server.bat. These files are not intended for end-user distribution or local setup. They should be deployed on your private server infrastructure.
System Requirements for Server

    RAM: 8GB minimum, 16GB recommended (for the DeepSeek Coder model)
    Storage: ~15GB free space for model download
    GPU: Highly recommended for performance (NVIDIA GPUs with CUDA support, or Apple Silicon with MPS). CPU inference will be significantly slower.

Server Deployment Steps (Overview)

    Obtain Server Files: Securely transfer server.py, server-requirements.txt, start_server.sh, and start_server.bat to your private server.

    Install Server Dependencies: bash pip install -r server-requirements.txt

    Note: Ensure torch is installed with appropriate CUDA/MPS support if using a GPU. Refer to the PyTorch website for specific installation commands.

    Start the AI Server: ```bash # On Linux/macOS server ./start_server.sh

# On Windows server (in PowerShell) .\start_server.bat ```

    Ensure Continuous Operation: Keep the server running continuously (e.g., using nohup or a process manager like systemd for Linux). The server will typically listen on http://0.0.0.0:8000.

    Configure Network Access: Ensure your server's firewall and network settings allow incoming connections to the chosen port (default 8000) from your clients. If exposing to the internet, use HTTPS and appropriate security measures.

    Distribute Server URL: Provide the public URL of your running AI server to your Bash.ai client users.

GPU Support (Optional but Recommended for Server)

For NVIDIA GPUs with CUDA, ensure you have the correct CUDA toolkit installed and then install PyTorch with CUDA support:

# Example for CUDA 11.8 (check PyTorch website for latest instructions)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

For Apple Silicon (M1/M2/M3 chips), PyTorch can leverage MPS:

pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
# MPS is usually included with CPU wheel

Verify GPU detection on the server:

python -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}'); print(f'MPS Available: {torch.backends.mps.is_available()}')"

🛠️ Troubleshooting (Server-Side)
Common Issues
"Model not found" Error on Server Startup

This usually means the transformers library couldn't download the model or there's a compatibility issue.

# Clear Hugging Face model cache and retry
# Linux/macOS:
rm -rf ~/.cache/huggingface/

# Windows:
Remove-Item -Recurse -Force $env:USERPROFILE\.cache\huggingface\

# Then restart the server
python server.py

Server Connection Issues

    Is the server process running? Check your server's process list
    Firewall? Ensure your server's firewall isn't blocking the chosen port (e.g., 8000)
    Network configuration? Verify network routes and public IP/DNS if clients are external

Performance Optimization (Server-Side)

    Use GPU: Always prioritize running the server on a machine with a compatible GPU
    Model Precision: The server.py uses torch.float16 or torch.bfloat16 by default for faster inference
    Resource Allocation: Ensure the server has sufficient RAM and CPU cores dedicated to the AI process

🏗️ Architecture

┌─────────────────┐    HTTP/JSON    ┌──────────────────┐
│   Bash.ai       │◄───────────────►│   AI Server      │
│   Client        │    Requests     │   (DeepSeek)     │
│  (Public GitHub)│                 │  (Private Server)│
│                 │                 │                  │
│ • Terminal UI   │                 │ • Model Loading  │
│ • Command Exec  │                 │ • Text Generation│
│ • File Creation │                 │ • GPU Support    │
│ • Cross-platform│                 │ • FastAPI        │
└─────────────────┘                 └──────────────────┘

Components

    Client (src/bashai.py): Publicly available terminal interface, handles user input, command execution, and file creation. Communicates with the remote AI server.
    Server (server.py): Private code, deployed on a dedicated server. Hosts the AI model and provides API endpoints for text generation.
    Setup Scripts (install_linux.sh, install_windows.ps1): Automate client installation for end-users.
    Start Scripts (start_server.sh, start_server.bat): For service providers to start the AI server.
    Configuration (.bashai_config.json): Stores client-side settings, including the remote server URL.

📊 Model Information

DeepSeek Coder 6.7B Instruct - Size: ~13GB download - Context: 16K tokens - Languages: Python, JavaScript, Bash, PowerShell, C++, Java, etc. - Specialization: Code generation, debugging, explanation
🔒 Privacy & Security

    Remote Processing: The AI model runs on a server you control, ensuring your users' queries are processed in an environment you manage
    Safe Mode: The client includes a "safe mode" that blocks dangerous commands by default, requiring user confirmation
    Open Source Client: The client-side code is fully transparent, allowing users to inspect how Bash.ai works on their machine

📜 License

MIT License - see LICENSE file for details.
🙏 Acknowledgments

    DeepSeek for the excellent code model
    Hugging Face for model hosting and transformers
    FastAPI for the server framework

Made with ❤️ by the Bash.ai team
