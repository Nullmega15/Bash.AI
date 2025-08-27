#!/bin/bash
# install_linux.sh - Installation script for Bash.ai on Linux/macOS

echo "Starting Bash.ai installation for Linux/macOS..."

# Check for Python 3
if ! command -v python3 &> /dev/null
then
    echo "Error: Python 3 could not be found. Please install it first."
    echo "Example: sudo apt install python3 python3-pip (for Debian/Ubuntu)"
    exit 1
fi

# Check for pip3
if ! command -v pip3 &> /dev/null
then
    echo "Error: pip3 (Python 3 package installer) not found. Installing it now..."
    sudo apt install python3-pip || sudo yum install python3-pip || sudo dnf install python3-pip || echo "Could not install pip3 automatically. Please install it manually."
    if ! command -v pip3 &> /dev/null; then
        echo "Error: pip3 still not found. Please install pip3 manually and re-run this script."
        exit 1
    fi
fi

# Install client dependencies
echo "Installing client dependencies from requirements.txt..."
pip3 install -r requirements.txt --user || { echo "Error: Failed to install client dependencies. Check your internet connection or pip3 setup."; exit 1; }
echo "Client dependencies installed."

# Create a symlink or a wrapper script for easy execution
# This script will call the main bashai.py script
INSTALL_DIR="/usr/local/bin" # Common directory for user-installed executables
SCRIPT_NAME="bashai"
SOURCE_SCRIPT="$(dirname "$0")/src/bashai.py"

echo "Creating executable wrapper script in $INSTALL_DIR..."
# Create a simple bash script that executes the python script
echo '#!/bin/bash
python3 "'"$SOURCE_SCRIPT"'" "$@"' | sudo tee "$INSTALL_DIR/$SCRIPT_NAME" > /dev/null

# Make the wrapper script executable
sudo chmod +x "$INSTALL_DIR/$SCRIPT_NAME"

echo "Bash.ai client installed successfully!"
echo "You can now run it from any terminal by typing: $SCRIPT_NAME"
echo "To start the AI server, navigate to the bash.ai directory and run: ./start_server.sh"
echo "First-time setup for Bash.ai client: bashai --configure"
