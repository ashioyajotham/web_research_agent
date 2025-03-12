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

# Fix the update function to properly handle two arguments
def update(key, value=None):
    """
    Update a configuration value.
    
    This function handles both the old API (update(key, value)) 
    and the new method-style API from ConfigManager (used as config.update(key, value)).
    """
    # Check if this is being called as a method on a dict-like object
    if value is None and hasattr(key, 'items'):
        # Being used as object.update(dict) - not supported in our case
        raise TypeError("Dictionary update not supported, use key-value pairs")
        
    # Otherwise use the normal update_config function
    return update_config(key, value)

# Add ConfigManager class for backwards compatibility
class ConfigManager(dict):
    """Compatibility class that behaves like both the new ConfigManager and the old config dict."""
    
    def __init__(self, config_dict=None):
        dict.__init__(self, config_dict or {})
        
    def update(self, key, value, store_in_keyring=False):
        """Update method that matches the new ConfigManager.update() signature."""
        update_config(key, value)
        return False  # No keyring support in this fallback
        
    def get(self, key, default=None):
        """Get a configuration value."""
        config = get_config()
        return config.get(key, default)
        
    def items(self):
        """Get all items in the configuration."""
        return get_config().items()
        
    def securely_stored_keys(self):
        """Compatibility method for secure key storage."""
        return {}  # No keys are securely stored in this fallback

# Re-export for backwards compatibility
__all__ = ['get_config', 'init_config', 'ConfigManager', 'update', 'update_config']