import os
from typing import Dict, Any, Optional
from pathlib import Path
import yaml
from dataclasses import dataclass

@dataclass
class AgentConfiguration:
    """Enhanced configuration management"""
    # API Settings
    api_keys: Dict[str, str]
    
    # Performance Settings
    max_retries: int = 3
    timeout: int = 30
    parallel_requests: int = 5
    
    # Storage Settings
    cache_dir: str = "cache"
    log_dir: str = "logs"
    
    # Feature Flags
    enable_caching: bool = True
    debug_mode: bool = False
    
    @classmethod
    def from_yaml(cls, config_path: str) -> 'AgentConfiguration':
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        return cls(**config_data)

@dataclass
class SystemConfig:
    """System-level configuration"""
    # API Settings
    api_keys: Dict[str, str]
    
    # System Settings
    cache_dir: str = "cache"
    log_dir: str = "logs"
    max_retries: int = 3
    timeout: int = 30
    parallel_requests: int = 5
    
    # Feature Flags
    enable_caching: bool = True
    debug_mode: bool = False
    
    @classmethod
    def create_default_config(cls) -> Dict[str, Any]:
        """Create default configuration"""
        return {
            "api_keys": {
                "serper": os.getenv("SERPER_API_KEY", ""),
                "gemini": os.getenv("GEMINI_API_KEY", "")
            },
            "max_retries": 3,
            "timeout": 30,
            "parallel_requests": 5,
            "cache_dir": "cache",
            "log_dir": "logs",
            "enable_caching": True,
            "debug_mode": False
        }

    @classmethod
    def from_yaml(cls, config_path: str) -> 'SystemConfig':
        """Load configuration from YAML file with fallback to defaults"""
        config_data = {}
        
        try:
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
        except FileNotFoundError:
            # Create default config file if it doesn't exist
            config_data = cls.create_default_config()
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False)
        
        # Resolve environment variables in api_keys
        if 'api_keys' in config_data:
            for key, value in config_data['api_keys'].items():
                if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                    env_var = value[2:-1]
                    config_data['api_keys'][key] = os.getenv(env_var, '')
        
        return cls(**config_data)

    def ensure_directories(self) -> None:
        """Ensure required directories exist"""
        Path(self.cache_dir).mkdir(parents=True, exist_ok=True)
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)
