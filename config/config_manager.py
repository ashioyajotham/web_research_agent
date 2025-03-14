import os
import json
import logging
from typing import Dict, Any, Optional

# Try to import dotenv for .env file support
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

# Try to import keyring for secure credential storage
try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

# Service name for keyring credentials
KEYRING_SERVICE = "web_research_agent"

class ConfigManager:
    """
    Configuration manager for the web research agent.
    Handles loading configs from .env files, environment variables, and secure keyring.
    """
    
    # Default configuration values
    DEFAULT_CONFIG = {
        "gemini_api_key": "",
        "serper_api_key": "",
        "log_level": "INFO",
        "max_search_results": 5,
        "memory_limit": 100,  # Number of items to keep in memory
        "output_format": "markdown",
        "timeout": 30,  # Default timeout for web requests in seconds
        "use_keyring": True,  # Whether to use keyring for API key storage
    }
    
    # Environment variable mapping
    ENV_MAPPING = {
        "GEMINI_API_KEY": "gemini_api_key",
        "SERPER_API_KEY": "serper_api_key",
        "LOG_LEVEL": "log_level",
        "MAX_SEARCH_RESULTS": "max_search_results",
        "MEMORY_LIMIT": "memory_limit",
        "OUTPUT_FORMAT": "output_format",
        "REQUEST_TIMEOUT": "timeout",
        "USE_KEYRING": "use_keyring",
    }
    
    # Keys that should be stored securely
    SECURE_KEYS = ["gemini_api_key", "serper_api_key"]
    
    def __init__(self, config_path: Optional[str] = None, env_file: Optional[str] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_path (str, optional): Path to the configuration file
            env_file (str, optional): Path to .env file
        """
        self.config = self.DEFAULT_CONFIG.copy()
        self.ENV_MAPPING = self.__class__.ENV_MAPPING
        
        # Load from .env file if available
        self._load_from_dotenv(env_file)
        
        # Load from config file if provided
        if config_path and os.path.exists(config_path):
            self._load_from_file(config_path)
        
        # Override with environment variables
        self._load_from_env()
        
        # Try to load secure keys from keyring
        self._load_from_keyring()
        
        # Validate required settings
        self._validate_config()
    
    def _load_from_dotenv(self, env_file: Optional[str] = None) -> None:
        """
        Load configuration from a .env file.
        
        Args:
            env_file (str, optional): Path to .env file
        """
        if not DOTENV_AVAILABLE:
            logging.debug("python-dotenv is not installed. Skipping .env file loading.")
            return
            
        # Try to load from specified .env file or from default locations
        try:
            loaded = load_dotenv(dotenv_path=env_file)
            if loaded:
                logging.info(f"Loaded environment from {env_file or '.env file'}")
        except Exception as e:
            logging.error(f"Failed to load from .env file: {str(e)}")
    
    def _load_from_file(self, config_path: str) -> None:
        """
        Load configuration from a JSON file.
        
        Args:
            config_path (str): Path to the configuration file
        """
        try:
            with open(config_path, 'r') as f:
                file_config = json.load(f)
                self.config.update(file_config)
                logging.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            logging.error(f"Failed to load configuration from {config_path}: {str(e)}")
    
    def _load_from_env(self) -> None:
        """Load configuration from environment variables."""
        for env_var, config_key in self.ENV_MAPPING.items():
            if env_var in os.environ:
                value = os.environ[env_var]
                
                # Convert numeric values
                if config_key in ["max_search_results", "memory_limit", "timeout"]:
                    try:
                        value = int(value)
                    except ValueError:
                        logging.warning(f"Invalid numeric value for {env_var}: {value}")
                        continue
                
                self.config[config_key] = value
                logging.debug(f"Set {config_key} from environment variable {env_var}")
    
    def _load_from_keyring(self) -> None:
        """Load API keys from system keyring if enabled and available."""
        if not KEYRING_AVAILABLE or not self.config.get("use_keyring", True):
            return
            
        try:
            for key in self.SECURE_KEYS:
                username = key  # Using the key name as username
                password = keyring.get_password(KEYRING_SERVICE, username)
                if password:
                    self.config[key] = password
                    logging.debug(f"Loaded {key} from system keyring")
        except Exception as e:
            logging.warning(f"Failed to load credentials from keyring: {str(e)}")
    
    def _save_to_keyring(self, key: str, value: str) -> bool:
        """
        Save a secure value to the system keyring.
        
        Args:
            key (str): Configuration key
            value (str): Value to store
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not KEYRING_AVAILABLE or not self.config.get("use_keyring", True):
            return False
            
        try:
            username = key  # Using the key name as username
            keyring.set_password(KEYRING_SERVICE, username, value)
            logging.debug(f"Saved {key} to system keyring")
            return True
        except Exception as e:
            logging.warning(f"Failed to save {key} to keyring: {str(e)}")
            return False
    
    def _validate_config(self) -> None:
        """Validate required configuration settings."""
        required_keys = ["gemini_api_key", "serper_api_key"]
        missing_keys = [key for key in required_keys if not self.config.get(key)]
        
        if missing_keys:
            for key in missing_keys:
                env_var = [k for k, v in self.ENV_MAPPING.items() if v == key][0]
                logging.warning(
                    f"Required configuration '{key}' is not set. "
                    f"Set environment variable {env_var} or include it in the config file."
                )
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key (str): Configuration key
            default (any, optional): Default value if key is not found
            
        Returns:
            any: Configuration value or default if not found
        """
        return self.config.get(key, default)
    
    def get_all(self) -> Dict[str, Any]:
        """
        Get all configuration values.
        
        Returns:
            dict: All configuration values
        """
        return self.config.copy()    
    def update(self, key: str, value: Any, store_in_keyring: bool = True) -> bool:
        """
        Update a configuration value.
        
        Args:
            key (str): Configuration key
            value (any): New value
            store_in_keyring (bool): Whether to store in keyring (for secure keys)
            
        Returns:
            bool: True if keyring storage was successful (if applicable), False otherwise
        """
        self.config[key] = value
        keyring_success = False
        
        # Store in keyring if it's a secure key and keyring is enabled
        if key in self.SECURE_KEYS and store_in_keyring:
            keyring_success = self._save_to_keyring(key, value)
        
        logging.debug(f"Updated configuration: {key}={value}")
        return keyring_success
    
    def securely_stored_keys(self) -> Dict[str, bool]:
        """
        Get information about which keys are securely stored.
        
        Returns:
            dict: Dictionary of secure keys and whether they are in keyring
        """
        if not KEYRING_AVAILABLE or not self.config.get("use_keyring", True):
            return {key: False for key in self.SECURE_KEYS}
            
        result = {}
        for key in self.SECURE_KEYS:
            try:
                has_key = keyring.get_password(KEYRING_SERVICE, key) is not None
                result[key] = has_key
            except Exception:
                result[key] = False
        
        return result

# Global instance
_config_instance = None

def init_config(config_path: Optional[str] = None, env_file: Optional[str] = None) -> ConfigManager:
    """
    Initialize the global configuration instance.
    
    Args:
        config_path (str, optional): Path to the configuration file
        env_file (str, optional): Path to .env file
        
    Returns:
        ConfigManager: Configuration manager instance
    """
    global _config_instance
    _config_instance = ConfigManager(config_path, env_file)
    return _config_instance

def get_config() -> ConfigManager:
    """
    Get the global configuration instance.
    
    Returns:
        ConfigManager: Configuration manager instance
    """
    global _config_instance
    if _config_instance is None:
        # Check for .env file in the project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_file = os.path.join(project_root, '.env')
        
        # Default path for config file
        config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "config.json"
        )
        
        # Only use config_path if it exists
        if not os.path.exists(config_path):
            config_path = None
            
        _config_instance = init_config(config_path, env_file)
    return _config_instance
