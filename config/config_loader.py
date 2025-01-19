import os
import yaml
from pathlib import Path
from typing import Dict, Any
import re
from dotenv import load_dotenv

class ConfigLoader:
    def __init__(self, config_path: str = "config/config.yaml"):
        # Load environment variables from .env file
        env_path = Path(__file__).parent.parent / '.env'
        load_dotenv(dotenv_path=env_path)
        
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
            
        with open(self.config_path) as f:
            config = yaml.safe_load(f)
            
        return self._resolve_env_vars(config)
    
    def _resolve_env_vars(self, config: Dict) -> Dict:
        """Recursively resolve environment variables in config values"""
        def _resolve(value):
            if isinstance(value, str):
                # Find all ${VAR} patterns
                env_vars = re.findall(r'\${([^}]+)}', value)
                for var in env_vars:
                    env_value = os.getenv(var)
                    if env_value is None:
                        raise ValueError(f"Environment variable not set: {var}. Check .env file.")
                    value = value.replace(f"${{{var}}}", env_value)
                return value
            elif isinstance(value, dict):
                return {k: _resolve(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [_resolve(item) for item in value]
            return value
            
        return _resolve(config)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get config value using dot notation (e.g., 'tools.web_search.timeout')"""
        try:
            value = self.config
            for k in key.split('.'):
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def validate(self) -> bool:
        """Validate required configurations"""
        required_keys = [
            'api_keys.serper',
            'api_keys.gemini',
            'agent.max_steps',
            'agent.timeout'
        ]
        
        for key in required_keys:
            if not self.get(key):
                raise ValueError(f"Missing required config: {key}")
                
        return True