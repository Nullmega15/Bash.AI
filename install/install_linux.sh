#!/bin/bash
# install_linux.sh - Installation script for Bash.ai on Linux/macOS

# Ensure script uses Unix line endings (in case it was edited on Windows)
if command -v dos2unix &> /dev/null; then
    dos2unix "$0" &> /dev/null
elif command -v sed &> /dev/null; then
    sed -i 's/\r$//' "$0"
fi

echo "Starting Bash.ai installation for Linux/macOS..."

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 could not be found. Please install it first."
    echo "Example: sudo apt-get install python3 python3-pip (for Debian/Ubuntu)"
    exit 1
fi

# Check for pip3
if ! command -v pip3 &> /dev/null; then
    echo "Error: pip3 (Python 3 package installer) not found. Installing it now..."
    sudo apt-get install python3-pip || sudo yum install python3-pip || sudo dnf install python3-pip || echo "Could not install pip3 automatically. Please install it manually."
    if ! command -v pip3 &> /dev/null; then
        echo "Error: pip3 still not found. Please install pip3 manually and re-run this script."
        exit 1
    fi
fi

# Check if python3-venv is installed by attempting to create a test virtual environment
VENV_TEST_DIR="/tmp/bash_ai_test_venv_$$"
if ! python3 -m venv "$VENV_TEST_DIR" &> /dev/null; then
    echo "Error: python3-venv is not installed. Attempting to install it now..."
    sudo apt-get install -y python3-venv python3.12-venv || sudo yum install python3-venv || sudo dnf install python3-venv || {
        echo "Error: Could not install python3-venv automatically. Please install it manually using: sudo apt-get install python3-venv python3.12-venv (Debian/Ubuntu)"
        exit 1
    }
    # Check again after installation attempt
    if ! python3 -m venv "$VENV_TEST_DIR" &> /dev/null; then
        echo "Error: Failed to create virtual environment after installing python3-venv. Please install python3-venv manually."
        echo "Example: sudo apt-get install python3-venv python3.12-venv (for Debian/Ubuntu)"
        rm -rf "$VENV_TEST_DIR"
        exit 1
    fi
fi
# Clean up test environment
rm -rf "$VENV_TEST_DIR"

# Create a virtual environment for Bash.ai
VENV_DIR="$HOME/.bash_ai_venv"
echo "Creating virtual environment in $VENV_DIR..."
if ! python3 -m venv "$VENV_DIR"; then
    echo "Error: Failed to create virtual environment. Ensure python3-venv is installed."
    echo "Example: sudo apt-get install python3-venv python3.12-venv (for Debian/Ubuntu)"
    exit 1
fi

# Activate the virtual environment
source "$VENV_DIR/bin/activate"

# Upgrade pip in the virtual environment
echo "Upgrading pip in virtual environment..."
pip3 install --upgrade pip || {
    echo "Error: Failed to upgrade pip in virtual environment."
    deactivate
    exit 1
}

# Install dependencies from requirements.txt
if [ -f "requirements.txt" ]; then
    echo "Installing client dependencies from requirements.txt..."
    pip3 install -r requirements.txt || {
        echo "Error: Failed to install client dependencies. Check your internet connection or pip3 setup."
        deactivate
        exit 1
    }
else
    echo "Error: requirements.txt not found in the current directory."
    deactivate
    exit 1
fi

# Deactivate the virtual environment
deactivate

echo "Bash.ai installation completed successfully!"
