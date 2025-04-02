#!/bin/bash

# Check for Python 3
if ! command -v python3 &> /dev/null
then
    echo "Python 3 could not be found. Please install it first."
    exit 1
fi

# Install dependencies
pip3 install -r requirements.txt

# Create executable
echo '#!/bin/bash
python3 "$(dirname "$0")/src/bashai.py" "$@"' > bashai

# Make executable
chmod +x bashai

# Move to bin directory
sudo mv bashai /usr/local/bin/

echo "Bash.ai installed successfully! Run with 'bashai'"
