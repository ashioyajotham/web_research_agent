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
    def from_yaml(cls, config_path: str) -> 'SystemConfig':
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        return cls(**config_data)
    
    def ensure_directories(self) -> None:
        """Ensure required directories exist"""
        Path(self.cache_dir).mkdir(parents=True, exist_ok=True)
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)
