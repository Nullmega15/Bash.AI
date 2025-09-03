# src/config.py
import json
from pathlib import Path

# Define the path for the Bash.ai configuration file
# It will be stored in the user's home directory
CONFIG_PATH = Path.home() / ".bashai_config.json"

# Default configuration values. These will be used if a config file doesn't exist
# or if specific keys are missing from an existing file.
DEFAULT_CONFIG = {
    "server_url": "http://84.247.164.54:8000/", # Default AI server URL
    "max_history": 100,                   # Maximum number of commands to keep in history
    "safe_mode": True,                    # Enable/disable blocking of dangerous commands
    "auto_execute": False                 # Enable/disable automatic execution of AI-suggested commands
}

def load_config() -> dict:
    """
    Loads the Bash.ai configuration from the CONFIG_PATH.
    If the file does not exist, or if there's a JSON decoding error,
    it returns the DEFAULT_CONFIG.
    """
    try:
        with open(CONFIG_PATH, 'r') as f:
            # Load existing configuration and merge it with default settings.
            # This ensures that new default settings are added if they weren't in an older config file.
            loaded_config = json.load(f)
            return {**DEFAULT_CONFIG, **loaded_config}
    except FileNotFoundError:
        # If the config file doesn't exist, return the default configuration.
        return DEFAULT_CONFIG
    except json.JSONDecodeError:
        # If the config file is corrupted (invalid JSON), print a warning and return defaults.
        print(f"Warning: Configuration file at {CONFIG_PATH} is corrupted. Using default settings.")
        return DEFAULT_CONFIG
    except Exception as e:
        # Catch any other potential errors during file loading.
        print(f"An unexpected error occurred while loading config: {e}. Using default settings.")
        return DEFAULT_CONFIG

def save_config(config_data: dict):
    """
    Saves the provided configuration dictionary to the CONFIG_PATH.
    """
    try:
        # Ensure the parent directory exists before writing the file
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config_data, f, indent=2) # Use indent for pretty-printing JSON
        print(f"Configuration saved to {CONFIG_PATH}")
    except IOError as e:
        print(f"Error: Could not save configuration to {CONFIG_PATH}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while saving config: {e}")

# Example of how to use this module (for testing or direct execution)
if __name__ == "__main__":
    print("Loading config...")
    current_config = load_config()
    print("Current Config:", current_config)
