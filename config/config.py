import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Global configuration
_config = {}

def init_config():
    """Initialize the configuration."""
    global _config
    
    # Set up config directory
    config_dir = Path.home() / ".web_research_agent"
    config_file = config_dir / "config.json"
    
    # Create config directory if it doesn't exist
    config_dir.mkdir(exist_ok=True)
    
    # Load configuration from file if it exists
    if config_file.exists():
        try:
            with open(config_file, "r") as f:
                _config = json.load(f)
        except json.JSONDecodeError:
            # If the config file is invalid, start with empty config
            _config = {}
    
    # Load API keys from environment variables, overriding file config
    if os.environ.get("GEMINI_API_KEY"):
        _config["gemini_api_key"] = os.environ.get("GEMINI_API_KEY")
    
    if os.environ.get("SERPER_API_KEY"):
        _config["serper_api_key"] = os.environ.get("SERPER_API_KEY")
    
    # Set default values if not already set
    _config.setdefault("timeout", 30)
    _config.setdefault("max_search_results", 5)
    _config.setdefault("output_format", "markdown")
    _config.setdefault("log_level", "INFO")
    
    return _config

def get_config():
    """Get the current configuration."""
    global _config
    if not _config:
        return init_config()
    return _config

def update_config(key, value):
    """Update configuration and save to file."""
    global _config
    
    # Initialize if not already initialized
    if not _config:
        init_config()
    
    # Update the value
    _config[key] = value
    
    # Save to file
    config_dir = Path.home() / ".web_research_agent"
    config_file = config_dir / "config.json"
    
    with open(config_file, "w") as f:
        json.dump(_config, f, indent=2)
    
    return _config

# Alias for update_config for a cleaner API
def update(key, value):
    """Update a configuration value."""
    return update_config(key, value)

# Re-export for backwards compatibility
__all__ = ['get_config', 'init_config', 'ConfigManager', 'update', 'update_config']