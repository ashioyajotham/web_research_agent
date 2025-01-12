from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseTool(ABC):
    @abstractmethod
    def get_description(self) -> str:
        """Return a description of what the tool does"""
        pass
        
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool's main functionality"""
        pass
    
    @property
    def name(self) -> str:
        """Return the tool's name"""
        return self.__class__.__name__.lower()
