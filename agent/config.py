from typing import Dict, Any, Optional
from dataclasses import dataclass
from tools.base import BaseTool
from utils.logger import AgentLogger
from .utils.config import SystemConfig

@dataclass
class AgentConfig:
    """Runtime agent configuration"""
    # Core Components
    tools: Dict[str, BaseTool]
    system_config: Optional[SystemConfig] = None
    
    # Runtime Settings
    max_steps: int = 10
    max_retries: int = 3
    min_confidence: float = 0.7
    timeout: int = 300
    parallel_tasks: bool = True
    memory_size: int = 1000
    confidence_threshold: float = 0.7
    
    # Feature Flags
    learning_enabled: bool = True
    parallel_execution: bool = True
    planning_enabled: bool = True
    pattern_learning_enabled: bool = True
    
    # Paths and Logging
    memory_path: str = "agent_memory.db"
    logger: Optional[AgentLogger] = None
    
    def __post_init__(self):
        if not self.system_config:
            self.system_config = SystemConfig.from_yaml("config/system.yaml")
