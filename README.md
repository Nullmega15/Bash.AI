Bash.ai 🤖💻AI-powered terminal assistant that leverages a remote DeepSeek Coder model. Natural language to code generation and command execution across Windows, Linux, and macOS.🌟 Features🤖 Remote AI Model: Connects to a server running DeepSeek Coder for powerful AI capabilities.🗣️ Natural Language: "create a backup script" → Complete working code.⚡ Instant Commands: "list python files" → find . -name "*.py".🔄 Cross-Platform: Windows PowerShell, Linux/macOS bash support.💾 Code Generation: Python, JavaScript, Bash, PowerShell scripts.🛡️ Safe Mode: Prevents dangerous commands.📚 Smart Context: Understands your OS and current directory.🚀 Quick Start1. Clone Repositorygit clone [https://github.com/yourusername/bash.ai.git](https://github.com/yourusername/bash.ai.git)
cd bash.ai
2. Install Server Dependencies (First Time)This is for the AI server that runs the DeepSeek Coder model.# Ensure you have Python 3 and pip installed
# Install server-side Python dependencies
pip install -r server-requirements.txt
Note: Depending on your system and GPU, you might need specific torch versions (e.g., pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118 for CUDA 11.8).3. Start AI ServerThe server must be running for the Bash.ai client to work.# Linux/macOS
./start_server.sh

# Windows (in PowerShell)
.\start_server.bat

# Or manually
python server.py
The server will typically run on http://localhost:8000.4. Install Client Dependencies & Setup# Linux/macOS
./install_linux.sh

# Windows (in PowerShell, run as Administrator if needed for PATH changes)
.\install_windows.ps1
Follow the prompts. These scripts will install client dependencies and add bashai to your system's PATH. You may need to restart your terminal after installation for PATH changes to take effect.5. Run Bash.ai# From any terminal
bashai
On first run, you'll be prompted to configure the server URL and other settings.📋 Manual InstallationLinux (Ubuntu/Debian)# 1. Install dependencies
sudo apt update && sudo apt install -y python3 python3-pip git

# 2. Clone repository
git clone [https://github.com/yourusername/bash.ai.git](https://github.com/yourusername/bash.ai.git)
cd bash.ai

# 3. Install server dependencies (for running the AI model)
pip3 install -r server-requirements.txt --user

# 4. Install client dependencies
pip3 install -r requirements.txt --user

# 5. Start server
python3 server.py & # Run in background

# 6. Run client
python3 src/bashai.py
Windows (PowerShell)# 1. Install Python (if needed)
# Download from python.org or use winget: winget install Python.Python.3

# 2. Clone repository
git clone [https://github.com/yourusername/bash.ai.git](https://github.com/yourusername/bash.ai.git)
cd bash.ai

# 3. Install server dependencies
python -m pip install -r server-requirements.txt

# 4. Install client dependencies
python -m pip install -r requirements.txt

# 5. Start server
Start-Process python -ArgumentList "server.py" # Run in background

# 6. Run client
python src\bashai.py
macOS# 1. Install Homebrew (if needed)
/bin/bash -c "$(curl -fsSL [https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh](https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh))"

# 2. Install Python
brew install python git

# 3. Follow Linux instructions from step 2 onwards
🔧 ConfigurationFirst Run SetupOn first run of bashai, you'll be prompted to configure:Server URL: Default http://localhost:8000. Change this if your AI server is running elsewhere.Auto-execute: Whether commands suggested by AI run automatically (default: False).Safe mode: Blocks potentially dangerous commands (default: True).Configuration is saved to:Linux/macOS: ~/.bashai_config.jsonWindows: %USERPROFILE%\.bashai_config.jsonYou can also force the configuration prompt at any time:bashai --configure
To view current configuration:bashai --config
💡 Usage ExamplesTerminal Commandsbash.ai> list all python files
# AI suggests and executes: find . -name "*.py" -type f

bash.ai> show disk usage sorted by size  
# AI suggests and executes: du -sh * | sort -hr

bash.ai> find large files over 100MB
# AI suggests and executes: find . -size +100M -type f -exec ls -lh {} \;
Code Generationbash.ai> make a python web server
# AI creates: server.py with complete Flask/FastAPI code

bash.ai> create backup script for my home directory
# AI creates: backup.sh with rsync/robocopy commands

bash.ai> build a todo app in javascript
# AI creates: todo.html with complete HTML/CSS/JS
Cross-Platform Commands# Works on all platforms with appropriate syntax
bash.ai> copy all images to backup folder
# Linux: cp *.{jpg,png,gif} backup/
# Windows: copy *.jpg backup\ && copy *.png backup\

bash.ai> check running processes
# Linux: ps aux
# Windows: Get-Process
🖥️ Server Setup DetailsThe AI server runs DeepSeek Coder locally (or on a designated machine) for privacy and offline use.System Requirements for ServerRAM: 8GB minimum, 16GB recommended (for the model)Storage: ~15GB free space for model downloadGPU: Optional but highly recommended for performance (NVIDIA GPUs with CUDA support, or Apple Silicon with MPS). If no GPU, CPU inference will be much slower.GPU Support (Optional but Recommended)For NVIDIA GPUs with CUDA, ensure you have the correct CUDA toolkit installed and then install PyTorch with CUDA support:# Example for CUDA 11.8 (check PyTorch website for latest instructions)
pip install torch torchvision torchaudio --index-url [https://download.pytorch.org/whl/cu118](https://download.pytorch.org/whl/cu118)
For Apple Silicon (M1/M2/M3 chips), PyTorch can leverage MPS:pip install torch torchvision torchaudio --index-url [https://download.pytorch.org/whl/cpu](https://download.pytorch.org/whl/cpu) # MPS is usually included with CPU wheel
Verify GPU detection:python -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}'); print(f'MPS Available: {torch.backends.mps.is_available()}')"
🛠️ TroubleshootingCommon Issues"Model not found" Error on Server StartupThis usually means the transformers library couldn't download the model.# Clear Hugging Face model cache and retry
# Linux/macOS:
rm -rf ~/.cache/huggingface/
# Windows:
Remove-Item -Recurse -Force $env:USERPROFILE\.cache\huggingface\

# Then restart the server
python server.py
Connection Refused / Cannot Connect to ServerIs the server running? Open a separate terminal and run python server.py (or start_server.sh/start_server.bat).Is the server URL correct? Check ~/.bashai_config.json or run bashai --config. Ensure the client's server_url matches where your server is actually listening.Firewall? Ensure your firewall isn't blocking port 8000 (or whatever port you're using).Network issues? If the server is on a different machine, ensure network connectivity.Permission Denied (Linux/macOS)# Make installation scripts executable
chmod +x install_linux.sh start_server.sh
# If you encounter permission issues when running bashai after installation,
# it might be due to /usr/local/bin not being in your PATH, or permissions.
# Try running `python3 src/bashai.py` directly.
Python Not Found (Windows)Ensure Python 3 is installed and added to your system's PATH. You might need to reinstall Python and select the "Add Python to PATH" option during installation.Performance OptimizationServer PerformanceUse GPU: Always prioritize running the server on a machine with a compatible GPU (NVIDIA with CUDA or Apple Silicon with MPS).Model Precision: The server.py uses torch.float16 or torch.bfloat16 by default for faster inference.Reduce max_tokens: In bashai.py, you can reduce the max_tokens sent in the payload to the server for shorter, faster responses (e.g., max_tokens=500).Client PerformanceDisable Auto-Execute: If auto_execute is True, the client will run commands without confirmation, which is faster but less safe. You can change this in ~/.bashai_config.json or via bashai --configure.🏗️ Architecture┌─────────────────┐    HTTP/JSON    ┌──────────────────┐
│   Bash.ai       │◄───────────────►│   AI Server      │
│   Client        │    Requests     │   (DeepSeek)     │
│                 │                 │                  │
│ • Terminal UI   │                 │ • Model Loading  │
│ • Text Generation│
│ • GPU Support    │
│ • FastAPI        │
└─────────────────┘                 └──────────────────┘
ComponentsClient (src/bashai.py): Terminal interface, command execution, file creation.Server (server.py): AI model hosting, API endpoints for chat and health checks.Setup Scripts (install_linux.sh, install_windows.ps1): Automate client installation.Start Scripts (start_server.sh, start_server.bat): Automate server startup.Configuration (.bashai_config.json): JSON-based configuration management.📊 Model InformationDeepSeek Coder 6.7B InstructSize: ~13GB downloadContext: 16K tokensLanguages: Python, JavaScript, Bash, PowerShell, C++, Java, etc.Specialization: Code generation, debugging, explanation🔒 Privacy & SecurityLocal/Self-Hosted Processing: The AI model runs on your machine (or a machine you control), ensuring your queries and data do not leave your local network unless you configure the client to connect to a remote, external server.No Data Transmission: With a local server setup, your code and commands never leave your system.Safe Mode: The client includes a "safe mode" that blocks dangerous commands by default, requiring user confirmation.Open Source: Full code transparency allows you to inspect how Bash.ai works.📜 LicenseMIT License - see LICENSE file for details.🙏 AcknowledgmentsDeepSeek for the excellent code modelHugging Face for model hosting and transformersFastAPI for the server frameworkMade with ❤️ by the Bash.ai team
