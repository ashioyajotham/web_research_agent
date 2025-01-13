from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class StrategyResult:
    success: bool
    output: Dict[str, Any] = None
    error: str = None
    confidence: float = 0.0
    metadata: Dict[str, Any] = None

class Strategy(ABC):
    @abstractmethod
    def execute(self, task: str, context: Dict[str, Any]) -> StrategyResult:
        """Execute the strategy for given task"""
        pass
    
    @abstractmethod
    def can_handle(self, task: str) -> float:
        """Return confidence score (0-1) for handling this task"""
        pass
    
    @abstractmethod
    def get_required_tools(self) -> List[str]:
        """Return list of required tool names"""
        pass

class StrategyError(Exception):
    """Base class for strategy-related errors"""
    pass
